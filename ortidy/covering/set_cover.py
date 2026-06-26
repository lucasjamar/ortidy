"""Set cover / set partition — assignment-matrix shape.

Pick the lowest-cost collection of subsets so that every element of the universe
is covered (set cover), or covered exactly once (set partition). Input is a
membership matrix: one row per subset, one boolean column per element, plus a
``cost`` column. Returns the subsets frame with an ``isSelected`` boolean column.

Built on CP-SAT.

Link:
    https://en.wikipedia.org/wiki/Set_cover_problem
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.sat.python import cp_model

from ortidy import _narwhals as _nw
from ortidy import _scaling, result, schema
from ortidy.result import SolveResult


def set_cover(
    subsets: Any,
    *,
    cost: str = "cost",
    subset_id: str | None = None,
    element_columns: list[str] | None = None,
    partition: bool = False,
    assignment_column: str = "isSelected",
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Solve a set-cover (or set-partition) problem.

    Parameters:
        subsets: Membership matrix — one row per subset, a boolean column per
            element, and a ``cost`` column.
        cost: Name of the per-subset cost column.
        subset_id: Optional subset-id column (excluded from the element columns).
        element_columns: The element (membership) columns. If ``None``, every
            column except ``cost`` and ``subset_id`` is treated as an element.
        partition: If ``True``, require each element covered *exactly* once
            (set partition) rather than at least once (set cover).
        assignment_column: Name of the added boolean column. Default ``"isSelected"``.
        time_limit: Optional wall-clock limit in seconds.
        random_seed: Solver seed for determinism.

    Returns:
        SolveResult whose ``frame`` is the subsets frame (same backend) plus a
        boolean ``assignment_column``; objective is the total selected cost.
    """
    frame = _nw.to_nw(subsets)
    schema.require_nonempty(frame, frame_name="subsets")
    schema.require_columns(frame, {cost}, frame_name="subsets")
    schema.require_numeric(frame, {cost}, frame_name="subsets")

    reserved = {cost} | ({subset_id} if subset_id else set())
    elements = element_columns or [c for c in frame.columns if c not in reserved]
    if not elements:
        raise ValueError("subsets must have at least one element column.")
    schema.require_columns(frame, set(elements), frame_name="subsets")

    n = frame.shape[0]
    costs = _nw.column_to_list(frame, cost)
    int_costs, factor = _scaling.scale_to_int(costs)
    membership = {e: _nw.column_to_list(frame, e) for e in elements}

    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x_{i}") for i in range(n)]
    for element in elements:
        covering = [x[i] for i in range(n) if membership[element][i]]
        if not covering:
            raise ValueError(
                f"element {element!r} is not covered by any subset — infeasible."
            )
        if partition:
            model.add_exactly_one(covering)
        else:
            model.add_at_least_one(covering)
    model.minimize(sum(x[i] * int_costs[i] for i in range(n)))

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
    frame = frame.with_columns(
        nw.new_series(assignment_column, selected, backend=frame.implementation)
    )
    return SolveResult(
        frame=_nw.to_native(frame),
        status=solve_status,
        objective=_scaling.unscale(solver.objective_value, factor),
        metadata={"solver": "CP-SAT", "wall_time": solver.wall_time},
    )
