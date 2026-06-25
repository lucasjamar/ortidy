"""0/1 knapsack — assignment-matrix shape.

Selects the subset of items maximizing total value subject to a weight capacity.
Returns the original frame with an ``isIncluded`` boolean column added.

Link:
    https://developers.google.com/optimization/bin/knapsack
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.algorithms.python import knapsack_solver

from ortidy import _narwhals as _nw
from ortidy import _scaling, schema
from ortidy.result import SolveResult, SolveStatus


def knapsack(
    items: Any,
    capacity: float,
    *,
    value: str = "value",
    weight: str = "weight",
    item_id: str | None = None,
    assignment_column: str = "isIncluded",
) -> SolveResult:
    """Solve a 0/1 knapsack.

    Parameters:
        items: A dataframe (pandas, Polars, …) with a value and a weight column.
        capacity: The maximum total weight of the knapsack.
        value: Name of the value column. Default ``"value"``.
        weight: Name of the weight column. Default ``"weight"``.
        item_id: Optional explicit row-id column. If ``None``, identity is handled
            internally without mutating the returned frame.
        assignment_column: Name of the added boolean column. Default ``"isIncluded"``.

    Returns:
        SolveResult whose ``frame`` is the input frame (same backend) plus a
        boolean ``assignment_column``, with status and total selected value.
    """
    frame = _nw.to_nw(items)
    schema.require_nonempty(frame, frame_name="items")
    schema.require_columns(frame, {value, weight}, frame_name="items")
    schema.require_numeric(frame, {value, weight}, frame_name="items")

    frame, id_col, synthesized = _nw.ensure_id_column(frame, item_id)

    raw_values = _nw.column_to_list(frame, value)
    raw_weights = _nw.column_to_list(frame, weight)

    int_values, _ = _scaling.scale_to_int(raw_values)
    int_weights, weight_factor = _scaling.scale_to_int(raw_weights)
    int_capacity = round(capacity * weight_factor)

    solver = knapsack_solver.KnapsackSolver(
        knapsack_solver.SolverType.KNAPSACK_MULTIDIMENSION_BRANCH_AND_BOUND_SOLVER,
        "ortidy_knapsack",
    )
    solver.init(int_values, [int_weights], [int_capacity])
    solver.solve()

    included = [solver.best_solution_contains(i) for i in range(len(int_values))]
    objective = sum(v for v, keep in zip(raw_values, included, strict=False) if keep)

    frame = frame.with_columns(
        nw.new_series(assignment_column, included, backend=frame.implementation)
    )
    frame = _nw.drop_if_synthesized(frame, id_col, synthesized)

    return SolveResult(
        frame=_nw.to_native(frame),
        status=SolveStatus.OPTIMAL,  # branch-and-bound returns the optimum
        objective=objective,
        metadata={"solver": "KNAPSACK_MULTIDIMENSION_BRANCH_AND_BOUND"},
    )
