"""Set cover / set partition — long (membership-list) form.

Pick the lowest-cost collection of subsets so that every element is covered (set
cover), or covered exactly once (set partition). Input is a tidy membership table —
one row per ``(subset, element)`` pair the subset covers — plus a per-subset
``costs`` lookup. Sparse membership is the natural form here. Returns a subset
frame with an ``isSelected`` boolean column.

Built on CP-SAT.

Link:
    https://en.wikipedia.org/wiki/Set_cover_problem
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import narwhals.stable.v1 as nw
from ortools.sat.python import cp_model

from ortidy import _narwhals as _nw
from ortidy import _scaling, result, schema
from ortidy.result import SolveResult


def set_cover(
    membership: Any,
    costs: Mapping[Any, float] | Any,
    *,
    subset: str = "subset",
    element: str = "element",
    cost_column: str = "cost",
    partition: bool = False,
    selected_column: str = "isSelected",
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Solve a set-cover (or set-partition) problem from a tidy membership list.

    Parameters:
        membership: One row per ``(subset, element)`` pair the subset covers.
        costs: Per-subset cost, as a ``{subset: cost}`` mapping or a two-column
            ``(subset, cost)`` frame.
        subset, element: Column names within ``membership``.
        cost_column: Name of the cost column added to the returned subset frame.
        partition: If ``True``, require each element covered *exactly* once.
        selected_column: Name of the added boolean column.
        time_limit: Optional wall-clock limit in seconds.
        random_seed: Solver seed for determinism.

    Returns:
        SolveResult whose ``frame`` (same backend as ``membership``) is one row per
        subset with its cost and a boolean ``selected_column``; objective is the
        total selected cost.
    """
    mem = _nw.to_nw(membership)
    schema.require_nonempty(mem, frame_name="membership")
    schema.require_columns(mem, {subset, element}, frame_name="membership")

    subs = _nw.column_to_list(mem, subset)
    elems = _nw.column_to_list(mem, element)
    cost_map = _nw.to_mapping(costs)

    subset_ids = _nw.unique_in_order(subs)
    missing = set(subset_ids) - set(cost_map)
    if missing:
        raise KeyError(f"costs is missing subset(s) {sorted(missing)}.")

    _, factor = _scaling.scale_to_int([cost_map[s] for s in subset_ids])
    covered_by: dict[Any, list[Any]] = {}
    for s, e in zip(subs, elems, strict=True):
        covered_by.setdefault(e, [])
        if s not in covered_by[e]:
            covered_by[e].append(s)

    model = cp_model.CpModel()
    x = {s: model.new_bool_var(f"x_{s}") for s in subset_ids}
    for covering in covered_by.values():
        chosen = [x[s] for s in covering]
        if partition:
            model.add_exactly_one(chosen)
        else:
            model.add_at_least_one(chosen)
    model.minimize(sum(x[s] * round(cost_map[s] * factor) for s in subset_ids))

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = random_seed
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = time_limit
    status = solver.solve(model)
    solve_status = result.from_cp_sat(status)

    backend = mem.implementation
    if not solve_status.is_success:
        empty = nw.from_dict(
            {subset: [], cost_column: [], selected_column: []}, backend=backend
        )
        return SolveResult(
            frame=_nw.to_native(empty),
            status=solve_status,
            objective=None,
            metadata={"solver": "CP-SAT"},
        )

    selected = [bool(solver.value(x[s])) for s in subset_ids]
    objective = sum(
        cost_map[s] for s, keep in zip(subset_ids, selected, strict=True) if keep
    )
    out = nw.from_dict(
        {
            subset: subset_ids,
            cost_column: [cost_map[s] for s in subset_ids],
            selected_column: selected,
        },
        backend=backend,
    )
    return SolveResult(
        frame=_nw.to_native(out),
        status=solve_status,
        objective=objective,
        metadata={"solver": "CP-SAT", "wall_time": solver.wall_time},
    )
