"""Linear sum assignment — assignment-matrix shape.

A cost matrix *is* a dataframe: rows are agents, columns are tasks. We assign each
agent to exactly one task minimizing (or maximizing) total cost, and return the
input matrix frame with ``assignedTo`` and ``cost`` columns added.

Link:
    https://developers.google.com/optimization/assignment/assignment_example
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.graph.python import linear_sum_assignment

from ortidy import _narwhals as _nw
from ortidy import _scaling, schema
from ortidy.result import SolveResult, SolveStatus


def assignment(
    costs: Any,
    *,
    id_column: str | None = None,
    maximize: bool = False,
    assigned_column: str = "assignedTo",
    cost_column: str = "cost",
) -> SolveResult:
    """Solve a balanced/over-supplied linear assignment from a cost matrix.

    Parameters:
        costs: A cost-matrix frame. Each non-id column is a task; each row an agent.
        id_column: Optional column labelling agents (not treated as a task). If
            ``None``, agents are positional and the column is not added back.
        maximize: Maximize total value instead of minimizing cost.
        assigned_column: Name of the added column holding each agent's task label.
        cost_column: Name of the added column holding each agent's assignment cost.

    Returns:
        SolveResult whose ``frame`` is the input matrix (same backend) plus the
        assignment and per-agent cost columns, with status and total objective.
    """
    frame = _nw.to_nw(costs)
    schema.require_nonempty(frame, frame_name="costs")
    if id_column is not None:
        schema.require_columns(frame, {id_column}, frame_name="costs")

    task_columns = [c for c in frame.columns if c != id_column]
    if not task_columns:
        raise ValueError("costs must have at least one task column.")
    schema.require_numeric(frame, set(task_columns), frame_name="costs")

    n_agents = frame.shape[0]
    n_tasks = len(task_columns)
    if n_agents > n_tasks:
        raise ValueError(
            f"assignment needs at least as many tasks as agents; got "
            f"{n_agents} agents and {n_tasks} tasks."
        )

    columns = [_nw.column_to_list(frame, c) for c in task_columns]
    flat = [columns[j][i] for i in range(n_agents) for j in range(n_tasks)]
    _, factor = _scaling.scale_to_int(flat)
    sign = -1 if maximize else 1

    solver = linear_sum_assignment.SimpleLinearSumAssignment()
    for i in range(n_agents):
        for j in range(n_tasks):
            solver.add_arc_with_cost(i, j, sign * round(columns[j][i] * factor))

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

    assigned = [task_columns[solver.right_mate(i)] for i in range(n_agents)]
    per_agent_cost = [columns[solver.right_mate(i)][i] for i in range(n_agents)]
    objective = sum(per_agent_cost)

    frame = frame.with_columns(
        nw.new_series(assigned_column, assigned, backend=frame.implementation),
        nw.new_series(cost_column, per_agent_cost, backend=frame.implementation),
    )

    return SolveResult(
        frame=_nw.to_native(frame),
        status=SolveStatus.OPTIMAL,
        objective=objective,
        metadata={"solver": "LinearSumAssignment"},
    )
