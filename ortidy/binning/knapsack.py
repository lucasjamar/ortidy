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
    capacity: float | list[float],
    *,
    value: str = "value",
    weight: str | list[str] = "weight",
    item_id: str | None = None,
    assignment_column: str = "isIncluded",
) -> SolveResult:
    """Solve a 0/1 (optionally multidimensional) knapsack.

    Parameters:
        items: A dataframe (pandas, Polars, …) with a value and weight column(s).
        capacity: The maximum total weight. For a multidimensional knapsack, a
            list of capacities, one per weight column.
        value: Name of the value column. Default ``"value"``.
        weight: Name of the weight column, or a list of weight columns for a
            multidimensional knapsack (e.g. weight *and* volume). Default
            ``"weight"``.
        item_id: Optional explicit row-id column. If ``None``, identity is handled
            internally without mutating the returned frame.
        assignment_column: Name of the added boolean column. Default ``"isIncluded"``.

    Returns:
        SolveResult whose ``frame`` is the input frame (same backend) plus a
        boolean ``assignment_column``, with status and total selected value.
    """
    frame = _nw.to_nw(items)
    weight_columns = [weight] if isinstance(weight, str) else list(weight)
    capacities = (
        [capacity] if not isinstance(capacity, (list, tuple)) else list(capacity)
    )
    if len(weight_columns) != len(capacities):
        raise ValueError(
            f"weight has {len(weight_columns)} column(s) but capacity has "
            f"{len(capacities)} value(s); they must match."
        )
    schema.require_nonempty(frame, frame_name="items")
    schema.require_columns(frame, {value, *weight_columns}, frame_name="items")
    schema.require_numeric(
        frame, {value, *weight_columns}, frame_name="items", non_negative=True
    )

    frame, id_col, synthesized = _nw.ensure_id_column(frame, item_id)

    raw_values = _nw.column_to_list(frame, value)
    int_values, _ = _scaling.scale_to_int(raw_values)

    int_weights_per_dim: list[list[int]] = []
    int_capacities: list[int] = []
    for col, cap in zip(weight_columns, capacities, strict=True):
        int_w, factor = _scaling.scale_to_int(_nw.column_to_list(frame, col))
        int_weights_per_dim.append(int_w)
        int_capacities.append(round(cap * factor))

    solver = knapsack_solver.KnapsackSolver(
        knapsack_solver.SolverType.KNAPSACK_MULTIDIMENSION_BRANCH_AND_BOUND_SOLVER,
        "ortidy_knapsack",
    )
    solver.init(int_values, int_weights_per_dim, int_capacities)
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
