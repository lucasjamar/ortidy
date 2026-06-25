"""Network flow on edge lists — edge-flow shape.

Max-flow, min-cost-flow, and shortest path over an edge-list frame. Each solver
returns the input edges (same backend) with a ``flow`` column added.

Link:
    https://developers.google.com/optimization/flow
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.graph.python import max_flow as _mf
from ortools.graph.python import min_cost_flow as _mcf

from ortidy import _narwhals as _nw
from ortidy import schema
from ortidy.result import SolveResult, SolveStatus


def _node_index(tails: list, heads: list) -> dict[Any, int]:
    """Map node labels (in first-seen order) to contiguous integer ids."""
    index: dict[Any, int] = {}
    for node in [*tails, *heads]:
        index.setdefault(node, len(index))
    return index


def max_flow(
    edges: Any,
    source: Any,
    sink: Any,
    *,
    tail_column: str = "from",
    head_column: str = "to",
    capacity_column: str = "capacity",
    flow_column: str = "flow",
) -> SolveResult:
    """Maximum flow from ``source`` to ``sink`` over a capacitated edge list.

    Returns the edges (same backend) with a ``flow`` column; objective is the
    maximum flow value.
    """
    frame = _nw.to_nw(edges)
    schema.require_nonempty(frame, frame_name="edges")
    schema.require_columns(
        frame, {tail_column, head_column, capacity_column}, frame_name="edges"
    )
    schema.require_numeric(frame, {capacity_column}, frame_name="edges")

    tails = _nw.column_to_list(frame, tail_column)
    heads = _nw.column_to_list(frame, head_column)
    caps = _nw.column_to_list(frame, capacity_column)
    index = _node_index(tails, heads)
    if source not in index or sink not in index:
        raise KeyError(f"source {source!r} / sink {sink!r} not among edge nodes.")

    solver = _mf.SimpleMaxFlow()
    arc_ids = [
        solver.add_arc_with_capacity(index[t], index[h], int(c))
        for t, h, c in zip(tails, heads, caps, strict=True)
    ]
    status = solver.solve(index[source], index[sink])
    if status != solver.OPTIMAL:
        return SolveResult(
            frame=_nw.to_native(frame),
            status=SolveStatus.INFEASIBLE,
            objective=None,
            metadata={"solver": "MaxFlow"},
        )

    flows = [solver.flow(a) for a in arc_ids]
    frame = frame.with_columns(
        nw.new_series(flow_column, flows, backend=frame.implementation)
    )
    return SolveResult(
        frame=_nw.to_native(frame),
        status=SolveStatus.OPTIMAL,
        objective=solver.optimal_flow(),
        metadata={"solver": "MaxFlow"},
    )


def min_cost_flow(
    edges: Any,
    supplies: Any,
    *,
    tail_column: str = "from",
    head_column: str = "to",
    capacity_column: str = "capacity",
    cost_column: str = "cost",
    node_column: str = "node",
    supply_column: str = "supply",
    flow_column: str = "flow",
) -> SolveResult:
    """Minimum-cost flow over a capacitated, costed edge list with node supplies.

    ``supplies`` is a frame of ``(node, supply)`` (positive = source, negative =
    sink). Returns the edges (same backend) with a ``flow`` column; objective is
    the minimum total cost.
    """
    frame = _nw.to_nw(edges)
    sup = _nw.to_nw(supplies)
    schema.require_nonempty(frame, frame_name="edges")
    schema.require_columns(
        frame,
        {tail_column, head_column, capacity_column, cost_column},
        frame_name="edges",
    )
    schema.require_columns(sup, {node_column, supply_column}, frame_name="supplies")

    tails = _nw.column_to_list(frame, tail_column)
    heads = _nw.column_to_list(frame, head_column)
    caps = _nw.column_to_list(frame, capacity_column)
    costs = _nw.column_to_list(frame, cost_column)
    index = _node_index(tails, heads)

    solver = _mcf.SimpleMinCostFlow()
    arc_ids = [
        solver.add_arc_with_capacity_and_unit_cost(
            index[t], index[h], int(c), int(cost)
        )
        for t, h, c, cost in zip(tails, heads, caps, costs, strict=True)
    ]
    for node, supply in zip(
        _nw.column_to_list(sup, node_column),
        _nw.column_to_list(sup, supply_column),
        strict=True,
    ):
        if node not in index:
            raise KeyError(f"supply node {node!r} not among edge nodes.")
        solver.set_node_supply(index[node], int(supply))

    status = solver.solve()
    if status not in (solver.OPTIMAL, solver.FEASIBLE):
        return SolveResult(
            frame=_nw.to_native(frame),
            status=SolveStatus.INFEASIBLE,
            objective=None,
            metadata={"solver": "MinCostFlow", "raw_status": int(status)},
        )

    flows = [solver.flow(a) for a in arc_ids]
    frame = frame.with_columns(
        nw.new_series(flow_column, flows, backend=frame.implementation)
    )
    mapped = SolveStatus.OPTIMAL if status == solver.OPTIMAL else SolveStatus.FEASIBLE
    return SolveResult(
        frame=_nw.to_native(frame),
        status=mapped,
        objective=solver.optimal_cost(),
        metadata={"solver": "MinCostFlow"},
    )


def shortest_path(
    edges: Any,
    source: Any,
    sink: Any,
    *,
    tail_column: str = "from",
    head_column: str = "to",
    weight_column: str = "weight",
    flow_column: str = "onPath",
) -> SolveResult:
    """Shortest path from ``source`` to ``sink``, solved as a unit min-cost flow.

    Returns the edges (same backend) with a boolean-ish ``onPath`` column (1 on the
    chosen path); objective is the path length.
    """
    frame = _nw.to_nw(edges)
    schema.require_columns(
        frame, {tail_column, head_column, weight_column}, frame_name="edges"
    )
    impl = frame.implementation
    # Push one unit of flow source→sink, unit capacities, weights as unit cost.
    with_cap = frame.with_columns(__cap__=nw.lit(1))
    supplies = nw.from_dict({"node": [source, sink], "supply": [1, -1]}, backend=impl)
    res = min_cost_flow(
        _nw.to_native(with_cap),
        _nw.to_native(supplies),
        tail_column=tail_column,
        head_column=head_column,
        capacity_column="__cap__",
        cost_column=weight_column,
        flow_column=flow_column,
    )
    if not res.is_success:
        return res
    out = _nw.to_nw(res.frame).drop("__cap__")
    return SolveResult(
        frame=_nw.to_native(out),
        status=res.status,
        objective=res.objective,
        metadata={"solver": "ShortestPath(MinCostFlow)"},
    )
