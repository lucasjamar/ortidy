"""Transportation problem — long (edge-list) form.

Ship goods from sources to sinks at minimum total cost, respecting each source's
supply and each sink's demand. Input is a tidy edge table — one row per allowed
``(source, sink)`` lane with its unit cost — plus per-source ``supply`` and
per-sink ``demand``. Forbidden lanes are simply omitted. Returns the edge frame
with a ``quantity`` column.

Built on the dedicated min-cost-flow solver. Quantities are treated as integers.

Link:
    https://en.wikipedia.org/wiki/Transportation_theory_(mathematics)
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import narwhals.stable.v1 as nw
from ortools.graph.python import min_cost_flow as _mcf

from ortidy import _narwhals as _nw
from ortidy import _scaling, schema
from ortidy.result import SolveResult, SolveStatus


def transportation(
    edges: Any,
    supply: Mapping[Any, float] | Any,
    demand: Mapping[Any, float] | Any,
    *,
    source: str = "source",
    sink: str = "sink",
    cost: str = "cost",
    quantity_column: str = "quantity",
) -> SolveResult:
    """Solve a (balanced) transportation problem from a tidy edge list.

    Parameters:
        edges: One row per allowed ``(source, sink)`` lane with its unit cost.
        supply: Per-source supply, as a ``{source: qty}`` mapping or a two-column
            ``(source, qty)`` frame.
        demand: Per-sink demand, as a ``{sink: qty}`` mapping or a two-column
            ``(sink, qty)`` frame.
        source, sink, cost: Column names within ``edges``.
        quantity_column: Name of the added shipped-quantity column.

    Returns:
        SolveResult whose ``frame`` is the edge frame (same backend) plus a
        ``quantity`` column; objective is the total shipping cost. Total supply must
        equal total demand (raises ``ValueError`` otherwise).
    """
    frame = _nw.to_nw(edges)
    schema.require_nonempty(frame, frame_name="edges")
    schema.require_columns(frame, {source, sink, cost}, frame_name="edges")
    schema.require_numeric(frame, {cost}, frame_name="edges")

    sources = _nw.column_to_list(frame, source)
    sinks = _nw.column_to_list(frame, sink)
    costs = _nw.column_to_list(frame, cost)
    n = len(sources)

    supply_map = {k: round(v) for k, v in _nw.to_mapping(supply).items()}
    demand_map = {k: round(v) for k, v in _nw.to_mapping(demand).items()}
    if any(v < 0 for v in (*supply_map.values(), *demand_map.values())):
        raise ValueError("supply and demand quantities must be non-negative.")
    if sum(supply_map.values()) != sum(demand_map.values()):
        raise ValueError(
            f"unbalanced transportation problem: total supply "
            f"{sum(supply_map.values())} != total demand {sum(demand_map.values())}."
        )

    node_index: dict[Any, int] = {}
    for node in [*supply_map, *demand_map]:
        node_index.setdefault(node, len(node_index))

    _, factor = _scaling.scale_to_int(costs)
    solver = _mcf.SimpleMinCostFlow()
    arc_ids = [
        solver.add_arc_with_capacity_and_unit_cost(
            node_index[sources[i]],
            node_index[sinks[i]],
            supply_map.get(sources[i], 0),
            round(costs[i] * factor),
        )
        for i in range(n)
    ]
    for node, qty in supply_map.items():
        solver.set_node_supply(node_index[node], qty)
    for node, qty in demand_map.items():
        solver.set_node_supply(node_index[node], -qty)

    status = solver.solve()
    if status not in (solver.OPTIMAL, solver.FEASIBLE):
        return SolveResult(
            frame=None,
            status=SolveStatus.INFEASIBLE,
            objective=None,
            metadata={"solver": "MinCostFlow", "raw_status": int(status)},
        )

    quantities = [solver.flow(arc_ids[i]) for i in range(n)]
    frame = frame.with_columns(
        nw.new_series(quantity_column, quantities, backend=frame.implementation)
    )
    return SolveResult(
        frame=_nw.to_native(frame),
        status=(
            SolveStatus.OPTIMAL if status == solver.OPTIMAL else SolveStatus.FEASIBLE
        ),
        objective=_scaling.unscale(solver.optimal_cost(), factor),
        metadata={"solver": "MinCostFlow"},
    )
