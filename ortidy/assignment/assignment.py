"""Linear sum assignment — long (edge-list) form.

Assign each agent to exactly one task at minimum total cost. Input is a tidy edge
table — one row per allowed ``(agent, task)`` pair with its cost — so sparse
problems (an agent can only do *some* tasks) are expressed by simply omitting
rows. Returns the edge frame with a ``selected`` boolean column marking the chosen
assignments.

Link:
    https://developers.google.com/optimization/assignment/linear_assignment
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.graph.python import linear_sum_assignment

from ortidy import _narwhals as _nw
from ortidy import _scaling, schema
from ortidy.result import SolveResult, SolveStatus


def assignment(
    edges: Any,
    *,
    left: str = "agent",
    right: str = "task",
    value: str = "cost",
    maximize: bool = False,
    selected_column: str = "selected",
) -> SolveResult:
    """Solve a linear assignment from a tidy edge list.

    Parameters:
        edges: One row per allowed ``(agent, task)`` pair with its cost/value.
        left: The agent (left-node) column.
        right: The task (right-node) column.
        value: The cost column (or value, with ``maximize=True``).
        maximize: Maximize total value instead of minimizing cost.
        selected_column: Name of the added boolean column.

    Returns:
        SolveResult whose ``frame`` is the edge frame (same backend) plus a boolean
        ``selected_column``; objective is the total cost/value of the matching.
        ``INFEASIBLE`` if no perfect assignment of agents exists.
    """
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
