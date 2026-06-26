"""Generalized assignment problem (GAP) — assignment-matrix shape.

Assign tasks to capacity-limited agents to maximize total value. Each task
consumes a *size* on the agent it's assigned to, and each agent has a capacity.
Inputs are tasks×agents matrices (``values`` and ``sizes``) plus per-agent
``capacities``. Returns the values frame with an ``assignedTo`` column (the agent,
or null if a task is left unassigned).

Built on CP-SAT.

Link:
    https://developers.google.com/optimization/assignment/assignment_task_sizes
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import narwhals.stable.v1 as nw
from ortools.sat.python import cp_model

from ortidy import _narwhals as _nw
from ortidy import _scaling, result, schema
from ortidy.result import SolveResult


def generalized_assignment(
    values: Any,
    sizes: Any,
    capacities: Mapping[str, float] | Sequence[float],
    *,
    id_column: str | None = None,
    agent_columns: list[str] | None = None,
    require_all: bool = False,
    assigned_column: str = "assignedTo",
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Solve a generalized assignment problem.

    Parameters:
        values: Tasks×agents value matrix (each non-id column is an agent).
        sizes: Tasks×agents size matrix (same agent columns) — the resource a task
            consumes on each agent.
        capacities: Per-agent capacity, as a ``{agent: capacity}`` mapping or a
            sequence aligned to ``agent_columns``.
        id_column: Optional task-id column (excluded from the agent columns).
        agent_columns: The agent columns. If ``None``, every column except
            ``id_column`` is treated as an agent.
        require_all: If ``True``, every task must be assigned (else infeasible);
            otherwise tasks may be left unassigned.
        assigned_column: Name of the added column holding each task's agent.
        time_limit: Optional wall-clock limit in seconds.
        random_seed: Solver seed for determinism.

    Returns:
        SolveResult whose ``frame`` is the values frame (same backend) plus an
        ``assigned_column``; objective is the total assigned value.
    """
    values_nw = _nw.to_nw(values)
    sizes_nw = _nw.to_nw(sizes)
    schema.require_nonempty(values_nw, frame_name="values")

    reserved = {id_column} if id_column else set()
    agents = agent_columns or [c for c in values_nw.columns if c not in reserved]
    if not agents:
        raise ValueError("values must have at least one agent column.")
    schema.require_columns(values_nw, set(agents), frame_name="values")
    schema.require_columns(sizes_nw, set(agents), frame_name="sizes")
    schema.require_numeric(values_nw, set(agents), frame_name="values")
    schema.require_numeric(sizes_nw, set(agents), frame_name="sizes")

    if isinstance(capacities, Mapping):
        missing = set(agents) - set(capacities)
        if missing:
            raise KeyError(f"capacities is missing agent(s) {sorted(missing)}.")
        cap_list = [capacities[a] for a in agents]
    else:
        cap_list = list(capacities)
        if len(cap_list) != len(agents):
            raise ValueError(
                f"capacities has {len(cap_list)} value(s) but there are "
                f"{len(agents)} agents."
            )

    n_tasks = values_nw.shape[0]
    value_cols = {a: _nw.column_to_list(values_nw, a) for a in agents}
    size_cols = {a: _nw.column_to_list(sizes_nw, a) for a in agents}

    # Common integer scale across sizes and capacities so the constraints align.
    flat_sizes = [size_cols[a][t] for a in agents for t in range(n_tasks)]
    factor = _scaling.choose_factor(flat_sizes + list(cap_list))
    int_sizes = {
        a: _scaling.scale_to_int(size_cols[a], factor=factor)[0] for a in agents
    }
    int_caps = [round(c * factor) for c in cap_list]
    flat_values = [value_cols[a][t] for a in agents for t in range(n_tasks)]
    _, value_factor = _scaling.scale_to_int(flat_values)

    model = cp_model.CpModel()
    x = {
        (t, a): model.new_bool_var(f"x_{t}_{a}") for t in range(n_tasks) for a in agents
    }
    for t in range(n_tasks):
        task_vars = [x[t, a] for a in agents]
        if require_all:
            model.add_exactly_one(task_vars)
        else:
            model.add_at_most_one(task_vars)
    for ai, a in enumerate(agents):
        model.add(
            sum(x[t, a] * int_sizes[a][t] for t in range(n_tasks)) <= int_caps[ai]
        )
    model.maximize(
        sum(
            x[t, a] * round(value_cols[a][t] * value_factor)
            for t in range(n_tasks)
            for a in agents
        )
    )

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = random_seed
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = time_limit
    status = solver.solve(model)
    solve_status = result.from_cp_sat(status)

    if not solve_status.is_success:
        return SolveResult(
            frame=_nw.to_native(values_nw),
            status=solve_status,
            objective=None,
            metadata={"solver": "CP-SAT"},
        )

    assigned: list[Any] = [None] * n_tasks
    objective = 0.0
    for t in range(n_tasks):
        for a in agents:
            if solver.value(x[t, a]) == 1:
                assigned[t] = a
                objective += value_cols[a][t]
                break

    frame = values_nw.with_columns(
        nw.new_series(assigned_column, assigned, backend=values_nw.implementation)
    )
    return SolveResult(
        frame=_nw.to_native(frame),
        status=solve_status,
        objective=objective,
        metadata={"solver": "CP-SAT", "wall_time": solver.wall_time},
    )
