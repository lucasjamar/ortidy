"""Linear assignment — long (edge-list) form, with optional team / group constraints.

Assign agents to tasks at minimum total cost from a tidy edge list — one row per
allowed ``(agent, task)`` pair — so sparse problems are expressed by omitting rows.
Returns the edge frame with a ``selected`` boolean column.

By default this is a pure linear assignment (each agent to one task) solved with the
fast specialized solver. Supplying ``teams`` (cap on how many agents each team may
use) or ``allowed_groups`` (the active-agent set must match an allowed pattern)
switches to a CP-SAT model where each *task* is filled by exactly one agent and each
agent does at most one task.

Link:
    https://developers.google.com/optimization/assignment/assignment_groups
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import narwhals.stable.v1 as nw
from ortools.graph.python import linear_sum_assignment
from ortools.sat.python import cp_model

from ortidy import _narwhals as _nw
from ortidy import _scaling, result, schema
from ortidy.result import SolveResult, SolveStatus


def assignment(
    edges: Any,
    *,
    left: str = "agent",
    right: str = "task",
    value: str = "cost",
    maximize: bool = False,
    selected_column: str = "selected",
    teams: Any = None,
    team_capacity: int | Mapping[Any, int] | Any = None,
    allowed_groups: Any = None,
    group_column: str = "group",
    pattern_column: str = "pattern",
    member_column: str = "agent",
    active_column: str = "active",
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Solve an assignment from a tidy edge list, optionally with team/group rules.

    Parameters:
        edges: One row per allowed ``(agent, task)`` pair with its cost/value.
        left, right, value: The agent, task, and cost columns.
        maximize: Maximize total value instead of minimizing cost.
        selected_column: Name of the added boolean column.
        teams: Optional ``{agent: team}`` mapping or ``(agent, team)`` frame.
        team_capacity: Max agents each team may use — an int (all teams) or a
            ``{team: cap}`` mapping / ``(team, cap)`` frame.
        allowed_groups: Optional ``(group, pattern, agent, active)`` frame. For each
            group it enumerates allowed patterns; every group member appears in every
            pattern with ``active`` = 1/0 (whether that agent is active in the pattern).
            The active agents of each group must equal one of its patterns.
        group_column, pattern_column, member_column, active_column: Columns within
            ``allowed_groups``.
        time_limit, random_seed: CP-SAT controls (constrained variants only).

    Returns:
        SolveResult whose ``frame`` is the edge frame (same backend) plus a boolean
        ``selected_column``; objective is the total cost/value.
    """
    if teams is not None or allowed_groups is not None:
        return _constrained(
            edges,
            left,
            right,
            value,
            maximize,
            selected_column,
            teams,
            team_capacity,
            allowed_groups,
            group_column,
            pattern_column,
            member_column,
            active_column,
            time_limit,
            random_seed,
        )
    return _linear(edges, left, right, value, maximize, selected_column)


def _linear(
    edges: Any, left: str, right: str, value: str, maximize: bool, selected_column: str
) -> SolveResult:
    frame = _nw.to_nw(edges)
    schema.require_nonempty(frame, frame_name="edges")
    schema.require_columns(frame, {left, right, value}, frame_name="edges")
    schema.require_numeric(frame, {value}, frame_name="edges")

    lefts = _nw.column_to_list(frame, left)
    rights = _nw.column_to_list(frame, right)
    values = _nw.column_to_list(frame, value)

    left_index: dict[Any, int] = {}
    right_index: dict[Any, int] = {}
    for node in lefts:
        left_index.setdefault(node, len(left_index))
    for node in rights:
        right_index.setdefault(node, len(right_index))

    _, factor = _scaling.scale_to_int(values)
    sign = -1 if maximize else 1

    solver = linear_sum_assignment.SimpleLinearSumAssignment()
    for left_node, right_node, cost in zip(lefts, rights, values, strict=True):
        solver.add_arc_with_cost(
            left_index[left_node], right_index[right_node], sign * round(cost * factor)
        )

    status = solver.solve()
    if status != solver.OPTIMAL:
        mapped = (
            SolveStatus.INFEASIBLE
            if status == solver.INFEASIBLE
            else SolveStatus.MODEL_INVALID
        )
        return SolveResult(
            frame=_nw.to_native(frame),
            status=mapped,
            objective=None,
            metadata={"solver": "LinearSumAssignment"},
        )

    mate = {i: solver.right_mate(i) for i in range(len(left_index))}
    selected = [
        right_index[rights[k]] == mate[left_index[lefts[k]]] for k in range(len(lefts))
    ]
    objective = sum(v for v, keep in zip(values, selected, strict=True) if keep)

    frame = frame.with_columns(
        nw.new_series(selected_column, selected, backend=frame.implementation)
    )
    return SolveResult(
        frame=_nw.to_native(frame),
        status=SolveStatus.OPTIMAL,
        objective=objective,
        metadata={"solver": "LinearSumAssignment"},
    )


def _constrained(
    edges: Any,
    left: str,
    right: str,
    value: str,
    maximize: bool,
    selected_column: str,
    teams: Any,
    team_capacity: Any,
    allowed_groups: Any,
    group_column: str,
    pattern_column: str,
    member_column: str,
    active_column: str,
    time_limit: float | None,
    random_seed: int,
) -> SolveResult:
    frame = _nw.to_nw(edges)
    schema.require_nonempty(frame, frame_name="edges")
    schema.require_columns(frame, {left, right, value}, frame_name="edges")
    schema.require_numeric(frame, {value}, frame_name="edges")

    lefts = _nw.column_to_list(frame, left)
    rights = _nw.column_to_list(frame, right)
    values = _nw.column_to_list(frame, value)
    n = len(lefts)
    _, factor = _scaling.scale_to_int(values)

    rows_by_task: dict[Any, list[int]] = {}
    rows_by_agent: dict[Any, list[int]] = {}
    for i in range(n):
        rows_by_task.setdefault(rights[i], []).append(i)
        rows_by_agent.setdefault(lefts[i], []).append(i)

    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x_{i}") for i in range(n)]
    # Each task filled by exactly one agent.
    for rows in rows_by_task.values():
        model.add_exactly_one(x[i] for i in rows)
    # used[a] == number of tasks agent a does (a bool ⇒ at most one).
    used = {a: model.new_bool_var(f"used_{a}") for a in rows_by_agent}
    for a, rows in rows_by_agent.items():
        model.add(used[a] == sum(x[i] for i in rows))

    if teams is not None:
        team_of = _nw.to_mapping(teams)
        if isinstance(team_capacity, int):
            cap_of: dict[Any, int] = dict.fromkeys(set(team_of.values()), team_capacity)
        elif team_capacity is None:
            raise ValueError("teams given but team_capacity is None.")
        else:
            cap_of = {k: int(v) for k, v in _nw.to_mapping(team_capacity).items()}
        agents_by_team: dict[Any, list[Any]] = {}
        for agent, team in team_of.items():
            if agent in used:
                agents_by_team.setdefault(team, []).append(agent)
        for team, members in agents_by_team.items():
            model.add(sum(used[a] for a in members) <= cap_of[team])

    if allowed_groups is not None:
        ag = _nw.to_nw(allowed_groups)
        schema.require_columns(
            ag,
            {group_column, pattern_column, member_column, active_column},
            frame_name="allowed_groups",
        )
        groups = _nw.column_to_list(ag, group_column)
        patterns = _nw.column_to_list(ag, pattern_column)
        members = _nw.column_to_list(ag, member_column)
        actives = _nw.column_to_list(ag, active_column)
        group_agents: dict[Any, list[Any]] = {}
        active: dict[Any, dict[Any, set]] = {}
        for g, p, a, is_active in zip(groups, patterns, members, actives, strict=True):
            group_agents.setdefault(g, [])
            if a not in group_agents[g]:
                group_agents[g].append(a)
            active.setdefault(g, {}).setdefault(p, set())
            if is_active:
                active[g][p].add(a)
        for g, agents_g in group_agents.items():
            for a in agents_g:
                used.setdefault(a, model.new_bool_var(f"used_{a}"))
                if a not in rows_by_agent:
                    model.add(used[a] == 0)  # no edges → never active
            tuples = [
                tuple(1 if a in active[g][p] else 0 for a in agents_g)
                for p in active[g]
            ]
            model.add_allowed_assignments([used[a] for a in agents_g], tuples)

    objective = sum(x[i] * round(values[i] * factor) for i in range(n))
    model.maximize(objective) if maximize else model.minimize(objective)

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
    obj = sum(v for v, keep in zip(values, selected, strict=True) if keep)
    frame = frame.with_columns(
        nw.new_series(selected_column, selected, backend=frame.implementation)
    )
    return SolveResult(
        frame=_nw.to_native(frame),
        status=solve_status,
        objective=obj,
        metadata={"solver": "CP-SAT", "wall_time": solver.wall_time},
    )
