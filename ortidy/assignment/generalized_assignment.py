"""Generalized assignment problem (GAP) — long (edge-list) form.

Assign tasks to capacity-limited agents to maximize total value. Input is a tidy
edge table — one row per allowed ``(task, agent)`` pair with its ``value`` and
``size`` — plus per-agent ``capacities``. Sparse problems (a task can only go to
some agents) are expressed by omitting rows. Returns the edge frame with a
``selected`` boolean column.

Built on CP-SAT.

Link:
    https://developers.google.com/optimization/assignment/assignment_task_sizes
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import narwhals.stable.v1 as nw
from ortools.sat.python import cp_model

from ortidy import _narwhals as _nw
from ortidy import _scaling, result, schema
from ortidy.result import SolveResult


def generalized_assignment(
    edges: Any,
    capacities: Mapping[Any, float] | Any,
    *,
    task: str = "task",
    agent: str = "agent",
    value: str = "value",
    size: str = "size",
    require_all: bool = False,
    selected_column: str = "selected",
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Solve a generalized assignment problem from a tidy edge list.

    Parameters:
        edges: One row per allowed ``(task, agent)`` pair, with a value and a size.
        capacities: Per-agent capacity, as a ``{agent: capacity}`` mapping or a
            two-column ``(agent, capacity)`` frame.
        task, agent, value, size: Column names within ``edges``.
        require_all: If ``True``, every task must be assigned (else infeasible);
            otherwise tasks may be left unassigned.
        selected_column: Name of the added boolean column.
        time_limit: Optional wall-clock limit in seconds.
        random_seed: Solver seed for determinism.

    Returns:
        SolveResult whose ``frame`` is the edge frame (same backend) plus a boolean
        ``selected_column``; objective is the total assigned value.
    """
    frame = _nw.to_nw(edges)
    schema.require_nonempty(frame, frame_name="edges")
    schema.require_columns(frame, {task, agent, value, size}, frame_name="edges")
    schema.require_numeric(frame, {value, size}, frame_name="edges")

    tasks = _nw.column_to_list(frame, task)
    agents = _nw.column_to_list(frame, agent)
    values = _nw.column_to_list(frame, value)
    sizes = _nw.column_to_list(frame, size)
    n = len(tasks)

    cap_map = _nw.to_mapping(capacities)
    agent_ids = _nw.unique_in_order(agents)
    missing = set(agent_ids) - set(cap_map)
    if missing:
        raise KeyError(f"capacities is missing agent(s) {sorted(missing)}.")

    factor = _scaling.choose_factor(list(sizes) + list(cap_map.values()))
    int_sizes, _ = _scaling.scale_to_int(sizes, factor=factor)
    int_caps = {a: round(cap_map[a] * factor) for a in agent_ids}
    _, value_factor = _scaling.scale_to_int(values)

    rows_by_task: dict[Any, list[int]] = {}
    rows_by_agent: dict[Any, list[int]] = {}
    for i in range(n):
        rows_by_task.setdefault(tasks[i], []).append(i)
        rows_by_agent.setdefault(agents[i], []).append(i)

    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x_{i}") for i in range(n)]
    for rows in rows_by_task.values():
        chosen = [x[i] for i in rows]
        if require_all:
            model.add_exactly_one(chosen)
        else:
            model.add_at_most_one(chosen)
    for a, rows in rows_by_agent.items():
        model.add(sum(x[i] * int_sizes[i] for i in rows) <= int_caps[a])
    model.maximize(sum(x[i] * round(values[i] * value_factor) for i in range(n)))

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
    objective = sum(v for v, keep in zip(values, selected, strict=True) if keep)
    frame = frame.with_columns(
        nw.new_series(selected_column, selected, backend=frame.implementation)
    )
    return SolveResult(
        frame=_nw.to_native(frame),
        status=solve_status,
        objective=objective,
        metadata={"solver": "CP-SAT", "wall_time": solver.wall_time},
    )
