"""Bin packing — assignment-matrix shape.

Packs every item into bins of a common capacity, minimizing the number of bins
used. Returns the original items frame with a ``binId`` column (contiguously
numbered from 0) added.

Built on CP-SAT — no per-row variable construction.

Link:
    https://developers.google.com/optimization/bin/bin_packing
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.sat.python import cp_model

from ortidy import _narwhals as _nw
from ortidy import _scaling, result, schema
from ortidy.result import SolveResult


def bin_packing(
    items: Any,
    capacity: float,
    *,
    weight: str = "weight",
    item_id: str | None = None,
    bin_id: str = "binId",
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Solve a bin-packing problem.

    Parameters:
        items: Frame with a weight column.
        capacity: The (shared) capacity of every bin.
        weight: Name of the weight column.
        item_id: Optional explicit item-id column (synthesized if ``None``).
        bin_id: Name of the bin-assignment column added to the result.
        time_limit: Optional wall-clock limit in seconds.
        random_seed: Solver seed for determinism.

    Returns:
        SolveResult whose ``frame`` is the items frame (same backend) plus a
        ``bin_id`` column, with status and objective (number of bins used).
    """
    frame = _nw.to_nw(items)
    schema.require_nonempty(frame, frame_name="items")
    schema.require_columns(frame, {weight}, frame_name="items")
    schema.require_numeric(frame, {weight}, frame_name="items", non_negative=True)

    frame, id_col, synthesized = _nw.ensure_id_column(frame, item_id)
    weights = _nw.column_to_list(frame, weight)

    factor = _scaling.choose_factor(list(weights) + [capacity])
    int_weights, _ = _scaling.scale_to_int(weights, factor=factor)
    int_capacity = round(capacity * factor)

    n = len(weights)  # at most one bin per item is ever needed
    model = cp_model.CpModel()
    x = {(i, j): model.new_bool_var(f"x_{i}_{j}") for i in range(n) for j in range(n)}
    y = [model.new_bool_var(f"y_{j}") for j in range(n)]

    for i in range(n):
        model.add_exactly_one(x[i, j] for j in range(n))
    for j in range(n):
        model.add(
            sum(x[i, j] * int_weights[i] for i in range(n)) <= int_capacity * y[j]
        )
    # Symmetry break: bins fill in order, which also speeds the search.
    for j in range(n - 1):
        model.add(y[j] >= y[j + 1])
    model.minimize(sum(y))

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = random_seed
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = time_limit
    status = solver.solve(model)
    solve_status = result.from_cp_sat(status)

    if not solve_status.is_success:
        frame = _nw.drop_if_synthesized(frame, id_col, synthesized)
        return SolveResult(
            frame=_nw.to_native(frame),
            status=solve_status,
            objective=None,
            metadata=_metadata(solver),
        )

    raw_bin: list[int] = [-1] * n
    for i in range(n):
        for j in range(n):
            if solver.value(x[i, j]) == 1:
                raw_bin[i] = j
                break
    # Renumber used bins contiguously from 0 in order of first appearance.
    remap: dict[int, int] = {}
    contiguous = [remap.setdefault(b, len(remap)) for b in raw_bin]

    frame = frame.with_columns(
        nw.new_series(bin_id, contiguous, backend=frame.implementation)
    )
    frame = _nw.drop_if_synthesized(frame, id_col, synthesized)

    return SolveResult(
        frame=_nw.to_native(frame),
        status=solve_status,
        objective=round(solver.objective_value),
        metadata=_metadata(solver),
    )


def _metadata(solver: cp_model.CpSolver) -> dict[str, Any]:
    return {
        "solver": "CP-SAT",
        "wall_time": solver.wall_time,
        "best_objective_bound": solver.best_objective_bound,
    }
