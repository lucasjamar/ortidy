"""Multiple knapsack — assignment-matrix shape.

Packs items into capacitated bins to maximize total packed value; each item goes
into at most one bin. Returns the original items frame with a bin-assignment
column added (null where an item was left unpacked).

Built on CP-SAT — no per-row variable construction.

Link:
    https://developers.google.com/optimization/bin/multiple_knapsack
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.sat.python import cp_model

from ortidy import _narwhals as _nw
from ortidy import _scaling, result, schema
from ortidy.result import SolveResult


def multi_knapsack(
    items: Any,
    bins: Any,
    *,
    value: str = "value",
    weight: str = "weight",
    item_id: str | None = None,
    bin_id: str = "binId",
    capacity: str = "capacity",
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Solve a multiple-knapsack assignment.

    Parameters:
        items: Frame with value and weight columns.
        bins: Frame with bin-id and capacity columns.
        value, weight: Item column names.
        item_id: Optional explicit item-id column (synthesized if ``None``).
        bin_id, capacity: Bin column names. ``bin_id`` also names the assignment
            column added to the returned items frame.
        time_limit: Optional wall-clock limit in seconds.
        random_seed: Solver seed for determinism.

    Returns:
        SolveResult whose ``frame`` is the items frame (same backend) plus a
        ``bin_id`` column (the assigned bin, or null), with status and objective.
    """
    items_nw = _nw.to_nw(items)
    bins_nw = _nw.to_nw(bins)
    schema.require_nonempty(items_nw, frame_name="items")
    schema.require_nonempty(bins_nw, frame_name="bins")
    schema.require_columns(items_nw, {value, weight}, frame_name="items")
    schema.require_numeric(items_nw, {value, weight}, frame_name="items")
    schema.require_columns(bins_nw, {bin_id, capacity}, frame_name="bins")
    schema.require_numeric(bins_nw, {capacity}, frame_name="bins")

    items_nw, id_col, synthesized = _nw.ensure_id_column(items_nw, item_id)

    weights = _nw.column_to_list(items_nw, weight)
    values = _nw.column_to_list(items_nw, value)
    capacities = _nw.column_to_list(bins_nw, capacity)
    bin_ids = _nw.column_to_list(bins_nw, bin_id)

    # Common integer scale for weights and capacities so the constraints align.
    factor = _scaling.choose_factor(list(weights) + list(capacities))
    int_weights, _ = _scaling.scale_to_int(weights, factor=factor)
    int_caps, _ = _scaling.scale_to_int(capacities, factor=factor)
    int_values, value_factor = _scaling.scale_to_int(values)

    n, m = len(weights), len(capacities)
    model = cp_model.CpModel()
    x = {(i, j): model.new_bool_var(f"x_{i}_{j}") for i in range(n) for j in range(m)}
    for i in range(n):
        model.add_at_most_one(x[i, j] for j in range(m))
    for j in range(m):
        model.add(sum(x[i, j] * int_weights[i] for i in range(n)) <= int_caps[j])
    model.maximize(sum(x[i, j] * int_values[i] for i in range(n) for j in range(m)))

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = random_seed
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = time_limit
    status = solver.solve(model)
    solve_status = result.from_cp_sat(status)

    if not solve_status.is_success:
        items_nw = _nw.drop_if_synthesized(items_nw, id_col, synthesized)
        return SolveResult(
            frame=_nw.to_native(items_nw),
            status=solve_status,
            objective=None,
            metadata=_metadata(solver),
        )

    assigned: list[Any] = [None] * n
    for i in range(n):
        for j in range(m):
            if solver.value(x[i, j]) == 1:
                assigned[i] = bin_ids[j]
                break

    items_nw = items_nw.with_columns(
        nw.new_series(bin_id, assigned, backend=items_nw.implementation)
    )
    items_nw = _nw.drop_if_synthesized(items_nw, id_col, synthesized)

    return SolveResult(
        frame=_nw.to_native(items_nw),
        status=solve_status,
        objective=_scaling.unscale(solver.objective_value, value_factor),
        metadata=_metadata(solver),
    )


def _metadata(solver: cp_model.CpSolver) -> dict[str, Any]:
    return {
        "solver": "CP-SAT",
        "wall_time": solver.wall_time,
        "best_objective_bound": solver.best_objective_bound,
    }
