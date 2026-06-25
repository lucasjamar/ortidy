"""Vehicle routing — edge-flow shape.

Solves a (capacitated) vehicle-routing problem over a precomputed distance matrix
and returns the traversed routes as an edge list: one row per visited stop with
the trip distance, plus the original route feature-engineering
(``tripsSinceStart``, ``tripsTillEnd``, ``distanceSinceStart``,
``distanceTillEnd``) reimplemented on Narwhals window expressions.

Note: this P0 migration keeps the legacy contract of taking a *precomputed
distance matrix*. Building the matrix from locations (haversine / euclidean) and
the VRPTW / pickups-and-deliveries variants are P1 work.

Link:
    https://developers.google.com/optimization/routing
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from ortidy import _narwhals as _nw
from ortidy.result import SolveResult, SolveStatus


def _extract_vehicle_route(
    routing: Any,
    manager: Any,
    solution: Any,
    vehicle_id: int,
    demand: list[float] | None,
) -> dict[str, list]:
    """Walk one vehicle's route into column lists (no phantom final row).

    The route ends with the final (depot) node carrying a trip distance of 0 —
    fixing the old out-of-range duplicate-append bug.
    """
    nodes: list[int] = []
    index = routing.Start(vehicle_id)
    while not routing.IsEnd(index):
        nodes.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    nodes.append(manager.IndexToNode(index))  # end node

    departures: list[int] = []
    distances: list[float] = []
    for k, node in enumerate(nodes):
        departures.append(node)
        if k < len(nodes) - 1:
            from_index = manager.NodeToIndex(node)
            to_index = manager.NodeToIndex(nodes[k + 1])
            distances.append(
                routing.GetArcCostForVehicle(from_index, to_index, vehicle_id)
            )
        else:
            distances.append(0)

    route: dict[str, list] = {
        "vehicleId": [vehicle_id] * len(nodes),
        "departure": departures,
        "distance": distances,
    }
    if demand is not None:
        route["load"] = [demand[node] for node in nodes]
    return route


def _add_features(frame: nw.DataFrame) -> nw.DataFrame:
    """Add route feature-engineering using grouped Narwhals window expressions."""
    frame = frame.with_columns(_ones=nw.lit(1))
    frame = frame.with_columns(
        destination=nw.col("departure").shift(-1).over("vehicleId"),
        tripsSinceStart=(nw.col("_ones").cum_sum().over("vehicleId") - 1),
        distanceSinceStart=(
            nw.col("distance").cum_sum().over("vehicleId") - nw.col("distance")
        ),
    )
    frame = frame.with_columns(
        tripsTillEnd=(
            nw.col("tripsSinceStart").max().over("vehicleId")
            - nw.col("tripsSinceStart")
        ),
        distanceTillEnd=(
            nw.col("distanceSinceStart").max().over("vehicleId")
            - nw.col("distanceSinceStart")
        ),
    )
    return frame.drop("_ones")


def _routing_status(solved: bool) -> SolveStatus:
    """Map routing outcome to a status.

    The routing solver's metaheuristics return a feasible (not proven-optimal)
    tour, so a found solution maps to ``FEASIBLE``. We key off whether a solution
    object exists rather than the ``routing.status()`` integer, whose named enum
    constants are not stably exposed across OR-Tools bindings.
    """
    return SolveStatus.FEASIBLE if solved else SolveStatus.INFEASIBLE


def solve_routing(
    df: Any,
    vehicles: int | Any = 1,
    *,
    locations: Any = None,
    starting_point: str | int = 0,
    max_distance: int = 3000,
    span_cost_coefficient: int = 100,
    time_limit: float = 1.0,
    vehicle_id_column: str = "vehicleId",
    capacity_column: str = "capacity",
    demand_column: str = "demand",
) -> SolveResult:
    """Solve a vehicle-routing problem over a distance matrix.

    Parameters:
        df: A square distance matrix (a row/column per location).
        vehicles: Number of vehicles, or a frame with a vehicle-id column (and an
            optional capacity column for the capacitated variant).
        locations: Optional frame with a ``demand`` column (capacitated routing).
        starting_point: Depot node — a column name or positional node index.
        max_distance: Per-vehicle max travel distance (distance dimension).
        span_cost_coefficient: Global span cost coefficient (load balancing).
        time_limit: Solver wall-clock limit in seconds.
        vehicle_id_column, capacity_column, demand_column: Column-name overrides.

    Returns:
        SolveResult whose ``frame`` (same backend as ``df``) is an edge list of
        trips with route features, plus status and objective (total distance).
    """
    matrix_nw = _nw.to_nw(df)
    impl = matrix_nw.implementation
    column_names = matrix_nw.columns
    matrix = [[int(round(v)) for v in row] for row in matrix_nw.to_numpy().tolist()]

    if isinstance(vehicles, int):
        num_vehicles = vehicles
        vehicle_ids = list(range(num_vehicles))
        vehicle_capacities = None
    else:
        vehicles_nw = _nw.to_nw(vehicles)
        if vehicle_id_column not in vehicles_nw.columns:
            raise KeyError(
                f"vehicles frame must have a {vehicle_id_column!r} column; "
                f"got {vehicles_nw.columns}."
            )
        vehicle_ids = _nw.column_to_list(vehicles_nw, vehicle_id_column)
        num_vehicles = len(vehicle_ids)
        vehicle_capacities = (
            [int(c) for c in _nw.column_to_list(vehicles_nw, capacity_column)]
            if capacity_column in vehicles_nw.columns
            else None
        )

    if isinstance(starting_point, str):
        starting_point = column_names.index(starting_point)

    manager = pywrapcp.RoutingIndexManager(
        len(column_names), num_vehicles, starting_point
    )
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        return matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    demand: list[float] | None = None
    if vehicle_capacities is not None and locations is not None:
        locations_nw = _nw.to_nw(locations)
        demand = [int(d) for d in _nw.column_to_list(locations_nw, demand_column)]

        def demand_callback(from_index: int) -> int:
            return demand[manager.IndexToNode(from_index)]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            vehicle_capacities,
            True,  # start cumul to zero
            "Capacity",
        )
    elif num_vehicles > 1:
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            max_distance,
            True,  # start cumul to zero
            "Distance",
        )
        routing.GetDimensionOrDie("Distance").SetGlobalSpanCostCoefficient(
            span_cost_coefficient
        )

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    if demand is not None:
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
    search_parameters.time_limit.FromSeconds(int(time_limit))

    solution = routing.SolveWithParameters(search_parameters)
    if solution is None:
        return SolveResult(
            frame=None,
            status=_routing_status(solved=False),
            objective=None,
            metadata={"solver": "ROUTING"},
        )

    node_to_name = {i: name for i, name in enumerate(column_names)}
    routes: dict[str, list] = {}
    for vehicle_id in vehicle_ids:
        part = _extract_vehicle_route(routing, manager, solution, vehicle_id, demand)
        for key, values in part.items():
            routes.setdefault(key, []).extend(values)

    # Map node indices to location names before computing features, so the
    # shifted ``destination`` column carries names too.
    routes["departure"] = [node_to_name[n] for n in routes["departure"]]
    frame = nw.from_dict(routes, backend=impl)
    frame = _add_features(frame)

    return SolveResult(
        frame=_nw.to_native(frame),
        status=_routing_status(solved=True),
        objective=solution.ObjectiveValue(),
        metadata={"solver": "ROUTING", "num_vehicles": num_vehicles},
    )
