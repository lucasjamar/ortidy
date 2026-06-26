"""Uncapacitated facility location — long (edge-list) form.

Open facilities (paying a per-facility setup cost) and assign each customer to one
open facility, minimizing setup + assignment cost. Input is a tidy edge table —
one row per allowed ``(customer, facility)`` pair with its assignment cost — plus a
``setup_costs`` lookup. Returns the edge frame with a ``selected`` boolean column;
the opened facilities are in ``metadata["opened"]``.

Built on CP-SAT.

Link:
    https://en.wikipedia.org/wiki/Facility_location_problem
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import narwhals.stable.v1 as nw
from ortools.sat.python import cp_model

from ortidy import _narwhals as _nw
from ortidy import _scaling, result, schema
from ortidy.result import SolveResult


def facility_location(
    edges: Any,
    setup_costs: Mapping[Any, float] | Any,
    *,
    customer: str = "customer",
    facility: str = "facility",
    cost: str = "cost",
    selected_column: str = "selected",
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Solve an uncapacitated facility-location problem from a tidy edge list.

    Parameters:
        edges: One row per allowed ``(customer, facility)`` pair with its cost.
        setup_costs: Per-facility opening cost, as a ``{facility: cost}`` mapping or
            a two-column ``(facility, cost)`` frame.
        customer, facility, cost: Column names within ``edges``.
        selected_column: Name of the added boolean column.
        time_limit: Optional wall-clock limit in seconds.
        random_seed: Solver seed for determinism.

    Returns:
        SolveResult whose ``frame`` is the edge frame (same backend) plus a boolean
        ``selected_column``; objective is total setup + assignment cost, and
        metadata lists the opened facilities.
    """
    frame = _nw.to_nw(edges)
    schema.require_nonempty(frame, frame_name="edges")
    schema.require_columns(frame, {customer, facility, cost}, frame_name="edges")
    schema.require_numeric(frame, {cost}, frame_name="edges")

    customers = _nw.column_to_list(frame, customer)
    facilities = _nw.column_to_list(frame, facility)
    costs = _nw.column_to_list(frame, cost)
    n = len(customers)

    setup_map = _nw.to_mapping(setup_costs)
    facility_ids = _nw.unique_in_order(facilities)
    missing = set(facility_ids) - set(setup_map)
    if missing:
        raise KeyError(f"setup_costs is missing facility(ies) {sorted(missing)}.")

    factor = _scaling.choose_factor(list(costs) + list(setup_map.values()))
    int_costs, _ = _scaling.scale_to_int(costs, factor=factor)
    int_setup = {f: round(setup_map[f] * factor) for f in facility_ids}

    rows_by_customer: dict[Any, list[int]] = {}
    for i in range(n):
        rows_by_customer.setdefault(customers[i], []).append(i)

    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x_{i}") for i in range(n)]
    is_open = {f: model.new_bool_var(f"open_{f}") for f in facility_ids}
    for rows in rows_by_customer.values():
        model.add_exactly_one(x[i] for i in rows)
    for i in range(n):
        model.add(x[i] <= is_open[facilities[i]])
    model.minimize(
        sum(x[i] * int_costs[i] for i in range(n))
        + sum(is_open[f] * int_setup[f] for f in facility_ids)
    )

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = random_seed
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = time_limit
    status = solver.solve(model)
    solve_status = result.from_cp_sat(status)

    if not solve_status.is_success:
        return SolveResult(
            frame=_nw.to_native(frame),
            status=solve_status,
            objective=None,
            metadata={"solver": "CP-SAT"},
        )

    selected = [bool(solver.value(x[i])) for i in range(n)]
    opened = [f for f in facility_ids if solver.value(is_open[f]) == 1]
    objective = sum(c for c, keep in zip(costs, selected, strict=True) if keep) + sum(
        setup_map[f] for f in opened
    )
    frame = frame.with_columns(
        nw.new_series(selected_column, selected, backend=frame.implementation)
    )
    return SolveResult(
        frame=_nw.to_native(frame),
        status=solve_status,
        objective=objective,
        metadata={"solver": "CP-SAT", "opened": opened, "wall_time": solver.wall_time},
    )
