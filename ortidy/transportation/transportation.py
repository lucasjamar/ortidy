"""Transportation problem — edge-flow shape.

Ship goods from sources to sinks at minimum total cost, respecting each source's
supply and each sink's demand. Inputs are a sources×sinks cost matrix plus
per-source ``supply`` and per-sink ``demand``. Returns a tidy edge list
``(source, sink, cost, quantity)``.

Built on the dedicated min-cost-flow solver (a transportation problem is a
min-cost flow on a bipartite graph). Quantities are treated as integers.

Link:
    https://en.wikipedia.org/wiki/Transportation_theory_(mathematics)
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import narwhals.stable.v1 as nw
from ortools.graph.python import min_cost_flow as _mcf

from ortidy import _narwhals as _nw
from ortidy import _scaling, schema
from ortidy.result import SolveResult, SolveStatus


def _aligned(
    quantities: Mapping[str, float] | Sequence[float], labels: list[str], name: str
) -> list[int]:
    if isinstance(quantities, Mapping):
        missing = set(labels) - set(quantities)
        if missing:
            raise KeyError(f"{name} is missing {sorted(missing)}.")
        return [round(quantities[label]) for label in labels]
    values = list(quantities)
    if len(values) != len(labels):
        raise ValueError(
            f"{name} has {len(values)} value(s) but there are {len(labels)}."
        )
    return [round(v) for v in values]


def transportation(
    costs: Any,
    supply: Mapping[str, float] | Sequence[float],
    demand: Mapping[str, float] | Sequence[float],
    *,
    source_id_column: str | None = None,
    source_column: str = "source",
    sink_column: str = "sink",
    cost_column: str = "cost",
    quantity_column: str = "quantity",
) -> SolveResult:
    """Solve a (balanced) transportation problem.

    Parameters:
        costs: Sources×sinks cost matrix. Each non-id column is a sink; each row a
            source.
        supply: Per-source supply, as a ``{source: qty}`` mapping or a sequence
            aligned to the matrix rows.
        demand: Per-sink demand, as a ``{sink: qty}`` mapping or a sequence aligned
            to the sink columns.
        source_id_column: Optional column labelling sources. If ``None``, sources
            are labelled by position.
        source_column, sink_column, cost_column, quantity_column: Output column names.

    Returns:
        SolveResult whose ``frame`` (same backend as ``costs``) is the edge list of
        shipments; objective is the total shipping cost. Total supply must equal
        total demand (raises ``ValueError`` otherwise).
    """
    frame = _nw.to_nw(costs)
    schema.require_nonempty(frame, frame_name="costs")

    sinks = [c for c in frame.columns if c != source_id_column]
    if not sinks:
        raise ValueError("costs must have at least one sink column.")
    schema.require_numeric(frame, set(sinks), frame_name="costs")

    if source_id_column is not None:
        schema.require_columns(frame, {source_id_column}, frame_name="costs")
        sources = [str(s) for s in _nw.column_to_list(frame, source_id_column)]
    else:
        sources = [str(i) for i in range(frame.shape[0])]

    supplies = _aligned(supply, sources, "supply")
    demands = _aligned(demand, sinks, "demand")
    if sum(supplies) != sum(demands):
        raise ValueError(
            f"unbalanced transportation problem: total supply {sum(supplies)} != "
            f"total demand {sum(demands)}."
        )

    cost_matrix = [_nw.column_to_list(frame, k) for k in sinks]  # cost_matrix[k][s]
    flat = [cost_matrix[k][s] for k in range(len(sinks)) for s in range(len(sources))]
    _, factor = _scaling.scale_to_int(flat)

    n_src, n_snk = len(sources), len(sinks)
    solver = _mcf.SimpleMinCostFlow()
    arc_ids = {}
    for s in range(n_src):
        for k in range(n_snk):
            arc_ids[s, k] = solver.add_arc_with_capacity_and_unit_cost(
                s, n_src + k, supplies[s], round(cost_matrix[k][s] * factor)
            )
    for s in range(n_src):
        solver.set_node_supply(s, supplies[s])
    for k in range(n_snk):
        solver.set_node_supply(n_src + k, -demands[k])

    status = solver.solve()
    if status not in (solver.OPTIMAL, solver.FEASIBLE):
        return SolveResult(
            frame=None,
            status=SolveStatus.INFEASIBLE,
            objective=None,
            metadata={"solver": "MinCostFlow", "raw_status": int(status)},
        )

    edges: dict[str, list[Any]] = {
        source_column: [],
        sink_column: [],
        cost_column: [],
        quantity_column: [],
    }
    for s in range(n_src):
        for k in range(n_snk):
            edges[source_column].append(sources[s])
            edges[sink_column].append(sinks[k])
            edges[cost_column].append(cost_matrix[k][s])
            edges[quantity_column].append(solver.flow(arc_ids[s, k]))

    out = nw.from_dict(edges, backend=frame.implementation)
    return SolveResult(
        frame=_nw.to_native(out),
        status=(
            SolveStatus.OPTIMAL if status == solver.OPTIMAL else SolveStatus.FEASIBLE
        ),
        objective=_scaling.unscale(solver.optimal_cost(), factor),
        metadata={"solver": "MinCostFlow"},
    )
