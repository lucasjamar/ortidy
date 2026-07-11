"""Interval assignment — assign fixed-time tasks to a minimum-cost set of resources.

Unlike job-shop (free-floating durations, minimize makespan), the shape here is:
**tasks with fixed start/end times are assigned to the fewest (or cheapest) resources,
with a minimum gap between consecutive tasks on the same resource, where a resource may
need to be in the right place to take the next task.** Real instances: aircraft
rotations (gap = turnaround), crew lines of flying, gate allocation, vehicle/driver duty
chaining, machine reservations.

One function, optional columns opt into complexity — four regimes:

===  ==========  =========  ===========================  ==========================
 #   locations   resources  example                      model
===  ==========  =========  ===========================  ==========================
 1   no          no         single fleet, single base    pairwise conflict CP-SAT
 2   yes         no         single fleet, no base         min path cover on a DAG
 3   no          yes        mixed fleet, single base      pairwise + typed used-vars
 4   yes         yes        mixed fleet, free network     per-type flow on a DAG
===  ==========  =========  ===========================  ==========================

**The connection condition subsumes the interval condition.** Task ``i`` can precede
``j`` on one resource iff ``end(i) + min_gap <= start(j)`` *and* (no locations *or*
``end_location(i) == start_location(j)``). Regime 1 is regime 2 where every location is
identical — so a single compatibility-arc builder feeds all four models.

Scope: this solves **one** planning period. Multi-day continuity (tonight's end
location = tomorrow's start), maintenance routing, and initial resource positions for
recovery are out of scope — reach for :func:`~ortidy.routing.routing.solve_routing`
(VRPTW with per-vehicle start/end) if you need those.

Built on CP-SAT.

Link:
    https://developers.google.com/optimization/scheduling
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.sat.python import cp_model

from ortidy import _narwhals as _nw
from ortidy import _scaling, result, schema
from ortidy.result import SolveResult, SolveStatus


def interval_assignment(
    tasks: Any,
    *,
    task_column: str = "taskId",
    start_column: str = "start",
    end_column: str = "end",
    start_location_column: str | None = None,
    end_location_column: str | None = None,
    resources: Any | None = None,
    eligibility: Any | None = None,
    min_gap: int = 0,
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Assign fixed-time tasks to a minimum-cost set of resources.

    Parameters:
        tasks: One row per task, with id, start, and end columns.
        task_column, start_column, end_column: Task column names.
        start_location_column, end_location_column: Opt in to location chaining — a
            resource can only take a task that starts where its previous task ended.
            Both must be set together (or neither).
        resources: Opt in to a typed fleet — a frame with ``resourceType``, ``count``
            (>= 1), and ``fixed_cost`` columns. The objective becomes total fixed cost.
        eligibility: Opt in to restrictions — a ``(taskId, resourceType)`` frame listing
            the *allowed* types for a task. Tasks absent from it may use any type.
        min_gap: Minimum gap between consecutive tasks on the same resource.
        time_limit: Optional wall-clock limit in seconds.
        random_seed: Solver seed for determinism.

    Returns:
        SolveResult whose ``frame`` is the input frame (same backend) plus a
        ``resourceId`` column (dense, numbered 0..k-1 by earliest task start) and — when
        ``resources`` is given — a ``resourceType`` column. Objective is the number of
        resources used, or total ``fixed_cost`` when typed. Regimes 3/4 can be
        ``INFEASIBLE`` when ``count`` caps bind.
    """
    frame = _nw.to_nw(tasks)
    schema.require_nonempty(frame, frame_name="tasks")
    schema.require_columns(
        frame, {task_column, start_column, end_column}, frame_name="tasks"
    )
    schema.require_numeric(frame, {start_column, end_column}, frame_name="tasks")
    if min_gap < 0:
        raise ValueError("min_gap must be non-negative.")
    if (start_location_column is None) != (end_location_column is None):
        raise ValueError(
            "start_location_column and end_location_column must be set together."
        )

    task_ids = _nw.column_to_list(frame, task_column)
    starts = _nw.column_to_list(frame, start_column)
    ends = _nw.column_to_list(frame, end_column)
    n = len(starts)
    if any(e <= s for s, e in zip(starts, ends, strict=True)):
        raise ValueError(f"every task must have {end_column} > {start_column}.")

    has_locations = start_location_column is not None
    if start_location_column is not None and end_location_column is not None:
        schema.require_columns(
            frame,
            {start_location_column, end_location_column},
            frame_name="tasks",
        )
        start_locs = _nw.column_to_list(frame, start_location_column)
        end_locs = _nw.column_to_list(frame, end_location_column)

    def can_precede(i: int, j: int) -> bool:
        """Task i may run immediately before task j on the same resource."""
        if ends[i] + min_gap > starts[j]:
            return False
        return not (has_locations and end_locs[i] != start_locs[j])

    # --- resources & eligibility -------------------------------------------- #
    has_resources = resources is not None
    types: list[str] = []
    counts: dict[str, int] = {}
    costs: dict[str, float] = {}
    if has_resources:
        res_nw = _nw.to_nw(resources)
        schema.require_columns(
            res_nw, {"resourceType", "count", "fixed_cost"}, frame_name="resources"
        )
        schema.require_numeric(
            res_nw, {"count", "fixed_cost"}, frame_name="resources", non_negative=True
        )
        schema.require_unique(res_nw, "resourceType", frame_name="resources")
        types = [str(t) for t in _nw.column_to_list(res_nw, "resourceType")]
        counts = {
            t: int(c)
            for t, c in zip(types, _nw.column_to_list(res_nw, "count"), strict=True)
        }
        costs = {
            t: float(c)
            for t, c in zip(
                types, _nw.column_to_list(res_nw, "fixed_cost"), strict=True
            )
        }
        if any(c < 1 for c in counts.values()):
            raise ValueError("resources 'count' must be >= 1.")

    eligible: dict[int, set[str]] = {}
    if eligibility is not None:
        if not has_resources:
            raise ValueError("eligibility requires resources to be given.")
        el_nw = _nw.to_nw(eligibility)
        schema.require_columns(
            el_nw, {task_column, "resourceType"}, frame_name="eligibility"
        )
        allowed: dict[Any, set[str]] = {}
        for tid, ty in zip(
            _nw.column_to_list(el_nw, task_column),
            [str(t) for t in _nw.column_to_list(el_nw, "resourceType")],
            strict=True,
        ):
            if ty not in set(types):
                raise KeyError(
                    f"eligibility resourceType {ty!r} is not in resources "
                    f"{sorted(types)}."
                )
            allowed.setdefault(tid, set()).add(ty)
        for i in range(n):
            eligible[i] = allowed.get(task_ids[i], set(types))
            if not eligible[i]:
                raise ValueError(f"task {task_ids[i]!r} has no eligible resource type.")
    elif has_resources:
        eligible = {i: set(types) for i in range(n)}

    # --- dispatch on the four regimes --------------------------------------- #
    type_of: dict[int, str] | None = None
    if not has_resources and not has_locations:
        groups, status = _pairwise(
            n, can_precede, None, None, None, time_limit, random_seed
        )
    elif not has_resources and has_locations:
        groups, status = _path_cover(n, can_precede, starts, time_limit, random_seed)
    elif has_resources and not has_locations:
        groups, type_of, status = _pairwise_typed(
            n, can_precede, types, counts, costs, eligible, time_limit, random_seed
        )
    else:
        groups, type_of, status = _typed_flow(
            n,
            can_precede,
            types,
            counts,
            costs,
            eligible,
            starts,
            time_limit,
            random_seed,
        )

    if not status.is_success:
        return SolveResult(
            frame=_nw.to_native(frame),
            status=status,
            objective=None,
            metadata={"solver": "CP-SAT"},
        )

    # Dense resourceId numbered by earliest task start (deterministic output).
    first_start: dict[Any, Any] = {}
    for i in range(n):
        g = groups[i]
        first_start[g] = (
            min(first_start[g], starts[i]) if g in first_start else starts[i]
        )
    ordered = sorted(first_start, key=lambda g: (first_start[g], str(g)))
    group_id = {g: k for k, g in enumerate(ordered)}
    resource_id = [group_id[groups[i]] for i in range(n)]

    new_cols = [nw.new_series("resourceId", resource_id, backend=frame.implementation)]
    if has_resources and type_of is not None:
        new_cols.append(
            nw.new_series(
                "resourceType",
                [type_of[i] for i in range(n)],
                backend=frame.implementation,
            )
        )
    frame = frame.with_columns(*new_cols)

    if has_resources and type_of is not None:
        group_type = {groups[i]: type_of[i] for i in range(n)}
        objective: float = sum(costs[group_type[g]] for g in ordered)
    else:
        objective = float(len(ordered))

    return SolveResult(
        frame=_nw.to_native(frame),
        status=status,
        objective=objective,
        metadata={"solver": "CP-SAT", "resources_used": len(ordered)},
    )


def _solve(
    model: cp_model.CpModel, time_limit: float | None, random_seed: int
) -> tuple[cp_model.CpSolver, SolveStatus]:
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = random_seed
    solver.parameters.num_search_workers = 1  # deterministic output
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = time_limit
    status = solver.solve(model)
    return solver, result.from_cp_sat(status)


def _conflicts(n: int, can_precede: Any) -> list[tuple[int, int]]:
    """Pairs that can share no resource (neither can precede the other)."""
    return [
        (i, j)
        for i in range(n)
        for j in range(i + 1, n)
        if not can_precede(i, j) and not can_precede(j, i)
    ]


def _pairwise(
    n: int,
    can_precede: Any,
    types: Any,
    counts: Any,
    costs: Any,
    time_limit: float | None,
    random_seed: int,
) -> tuple[dict[int, int], SolveStatus]:
    """Regime 1: graph-colour conflicting tasks, minimize resources used."""
    conflicts = _conflicts(n, can_precede)
    model = cp_model.CpModel()
    x = {(i, r): model.new_bool_var(f"x_{i}_{r}") for i in range(n) for r in range(n)}
    for i in range(n):
        model.add_exactly_one(x[i, r] for r in range(n))
    for i, j in conflicts:
        for r in range(n):
            model.add(x[i, r] + x[j, r] <= 1)
    used = [model.new_bool_var(f"u_{r}") for r in range(n)]
    for i in range(n):
        for r in range(n):
            model.add(x[i, r] <= used[r])
    for r in range(n - 1):
        model.add(used[r] >= used[r + 1])  # symmetry: fill low indices first
    model.minimize(sum(used))

    solver, status = _solve(model, time_limit, random_seed)
    if not status.is_success:
        return {}, status
    groups = {
        i: next(r for r in range(n) if solver.value(x[i, r]) == 1) for i in range(n)
    }
    return groups, status


def _pairwise_typed(
    n: int,
    can_precede: Any,
    types: list[str],
    counts: dict[str, int],
    costs: dict[str, float],
    eligible: dict[int, set[str]],
    time_limit: float | None,
    random_seed: int,
) -> tuple[dict[int, int], dict[int, str], SolveStatus]:
    """Regime 3: pairwise conflicts over a materialized typed fleet."""
    fleet = [t for t in types for _ in range(counts[t])]  # one entry per resource
    r_type = {r: fleet[r] for r in range(len(fleet))}
    _, cost_factor = _scaling.scale_to_int([costs[t] for t in types])
    int_cost = {t: round(costs[t] * cost_factor) for t in types}

    conflicts = _conflicts(n, can_precede)
    model = cp_model.CpModel()
    x = {
        (i, r): model.new_bool_var(f"x_{i}_{r}")
        for i in range(n)
        for r in range(len(fleet))
        if r_type[r] in eligible[i]
    }
    for i in range(n):
        model.add_exactly_one(x[i, r] for r in range(len(fleet)) if (i, r) in x)
    for i, j in conflicts:
        for r in range(len(fleet)):
            if (i, r) in x and (j, r) in x:
                model.add(x[i, r] + x[j, r] <= 1)
    used = [model.new_bool_var(f"u_{r}") for r in range(len(fleet))]
    for (_i, r), var in x.items():
        model.add(var <= used[r])
    # Symmetry only within a type block (types keep distinct costs).
    for r in range(len(fleet) - 1):
        if r_type[r] == r_type[r + 1]:
            model.add(used[r] >= used[r + 1])
    model.minimize(sum(used[r] * int_cost[r_type[r]] for r in range(len(fleet))))

    solver, status = _solve(model, time_limit, random_seed)
    if not status.is_success:
        return {}, {}, status
    groups = {
        i: next(
            r for r in range(len(fleet)) if (i, r) in x and solver.value(x[i, r]) == 1
        )
        for i in range(n)
    }
    type_of = {i: r_type[groups[i]] for i in range(n)}
    return groups, type_of, status


def _path_cover(
    n: int,
    can_precede: Any,
    starts: list,
    time_limit: float | None,
    random_seed: int,
) -> tuple[dict[int, int], SolveStatus]:
    """Regime 2: maximum path cover on the compatibility DAG."""
    arcs = [(i, j) for i in range(n) for j in range(n) if i != j and can_precede(i, j)]
    model = cp_model.CpModel()
    x = {(i, j): model.new_bool_var(f"a_{i}_{j}") for i, j in arcs}
    for k in range(n):
        model.add(sum(x[i, j] for i, j in arcs if i == k) <= 1)  # <= 1 successor
        model.add(sum(x[i, j] for i, j in arcs if j == k) <= 1)  # <= 1 predecessor
    model.maximize(sum(x.values()))

    solver, status = _solve(model, time_limit, random_seed)
    if not status.is_success:
        return {}, status
    chosen = [(i, j) for i, j in arcs if solver.value(x[i, j]) == 1]
    return _chains(n, chosen, starts), status


def _typed_flow(
    n: int,
    can_precede: Any,
    types: list[str],
    counts: dict[str, int],
    costs: dict[str, float],
    eligible: dict[int, set[str]],
    starts: list,
    time_limit: float | None,
    random_seed: int,
) -> tuple[dict[int, int], dict[int, str], SolveStatus]:
    """Regime 4: per-type path-cover flow with eligibility and count caps."""
    arcs = [(i, j) for i in range(n) for j in range(n) if i != j and can_precede(i, j)]
    _, cost_factor = _scaling.scale_to_int([costs[t] for t in types])
    int_cost = {t: round(costs[t] * cost_factor) for t in types}

    model = cp_model.CpModel()
    y = {
        (t, i): model.new_bool_var(f"y_{t}_{i}")
        for t in types
        for i in range(n)
        if t in eligible[i]
    }
    xa = {
        (t, i, j): model.new_bool_var(f"xa_{t}_{i}_{j}")
        for t in types
        for i, j in arcs
        if (t, i) in y and (t, j) in y
    }
    for i in range(n):
        model.add(sum(y[t, i] for t in types if (t, i) in y) == 1)  # cover once
    paths = {t: model.new_int_var(0, n, f"p_{t}") for t in types}
    for t in types:
        for k in range(n):
            model.add(
                sum(xa[t, i, j] for i, j in arcs if i == k and (t, i, j) in xa)
                <= (y[t, k] if (t, k) in y else 0)
            )
            model.add(
                sum(xa[t, i, j] for i, j in arcs if j == k and (t, i, j) in xa)
                <= (y[t, k] if (t, k) in y else 0)
            )
        for i, j in arcs:
            if (t, i, j) in xa:
                model.add(xa[t, i, j] <= y[t, i])
                model.add(xa[t, i, j] <= y[t, j])
        model.add(
            paths[t]
            == sum(y[t, i] for i in range(n) if (t, i) in y)
            - sum(xa[t, i, j] for i, j in arcs if (t, i, j) in xa)
        )
        model.add(paths[t] <= counts[t])
    model.minimize(sum(paths[t] * int_cost[t] for t in types))

    solver, status = _solve(model, time_limit, random_seed)
    if not status.is_success:
        return {}, {}, status

    groups: dict[int, int] = {}
    type_of: dict[int, str] = {}
    for t in types:
        chosen = [
            (i, j)
            for i, j in arcs
            if (t, i, j) in xa and solver.value(xa[t, i, j]) == 1
        ]
        members = [i for i in range(n) if (t, i) in y and solver.value(y[t, i]) == 1]
        chains = _chains(n, chosen, starts, restrict=set(members), offset=len(groups))
        groups.update(chains)
        for i in members:
            type_of[i] = t
    return groups, type_of, status


def _chains(
    n: int,
    arcs: list[tuple[int, int]],
    starts: list,
    restrict: set[int] | None = None,
    offset: int = 0,
) -> dict[int, int]:
    """Follow chosen arcs into chains; label each task with a chain id."""
    succ = {i: j for i, j in arcs}
    has_pred = {j for _, j in arcs}
    members = restrict if restrict is not None else set(range(n))
    groups: dict[int, int] = {}
    gid = offset
    for i in sorted(members, key=lambda k: (starts[k], k)):
        if i in has_pred:
            continue  # not a chain head
        node: int | None = i
        while node is not None:
            groups[node] = gid
            node = succ.get(node)
        gid += 1
    return groups
