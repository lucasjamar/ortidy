"""Blending / diet problem — continuous linear program.

Choose how much of each item to use (a continuous quantity ≥ 0) to minimize total
cost while meeting per-attribute requirements — the classic diet / blending LP
(e.g. the Stigler diet). ``items`` is a frame with a ``cost`` column and one column
per attribute (the amount each unit of the item contributes); ``requirements`` is a
tidy ``(attribute, min[, max])`` table. Returns the items frame with a continuous
``quantity`` column.

Built on the Glop linear solver.

Link:
    https://developers.google.com/optimization/lp/stigler_diet
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.linear_solver import pywraplp

from ortidy import _narwhals as _nw
from ortidy import result, schema
from ortidy.result import SolveResult


def blend(
    items: Any,
    requirements: Any,
    *,
    cost: str = "cost",
    attribute: str = "attribute",
    minimum: str = "min",
    maximum: str = "max",
    quantity_column: str = "quantity",
) -> SolveResult:
    """Solve a blending / diet linear program.

    Parameters:
        items: One row per item, with a ``cost`` column and one numeric column per
            attribute (the amount a unit of the item contributes to that attribute).
        requirements: Tidy ``(attribute, min)`` table, optionally with a ``max``
            column (null max = no upper bound). Each attribute names a column of
            ``items``.
        cost: The per-unit cost column in ``items``.
        attribute, minimum, maximum: Column names within ``requirements``.
        quantity_column: Name of the added continuous quantity column.

    Returns:
        SolveResult whose ``frame`` is the items frame (same backend) plus a
        continuous ``quantity_column``; objective is the minimum total cost.
    """
    frame = _nw.to_nw(items)
    reqs = _nw.to_nw(requirements)
    schema.require_nonempty(frame, frame_name="items")
    schema.require_columns(frame, {cost}, frame_name="items")
    schema.require_numeric(frame, {cost}, frame_name="items", non_negative=True)
    schema.require_columns(reqs, {attribute, minimum}, frame_name="requirements")
    schema.require_unique(reqs, attribute, frame_name="requirements")

    attributes = [str(a) for a in _nw.column_to_list(reqs, attribute)]
    mins = _nw.column_to_list(reqs, minimum)
    maxs = (
        _nw.column_to_list(reqs, maximum)
        if maximum in reqs.columns
        else [None] * len(attributes)
    )
    schema.require_columns(frame, set(attributes), frame_name="items")
    schema.require_numeric(frame, set(attributes), frame_name="items")

    costs = _nw.column_to_list(frame, cost)
    contributions = {a: _nw.column_to_list(frame, a) for a in attributes}
    n = len(costs)

    solver = pywraplp.Solver.CreateSolver("GLOP")
    qty = [solver.NumVar(0.0, solver.infinity(), f"q_{i}") for i in range(n)]
    for a, lo, hi in zip(attributes, mins, maxs, strict=True):
        total = solver.Sum([qty[i] * float(contributions[a][i]) for i in range(n)])
        if lo is not None:
            solver.Add(total >= float(lo))
        if hi is not None:
            solver.Add(total <= float(hi))
    solver.Minimize(solver.Sum([qty[i] * float(costs[i]) for i in range(n)]))

    status = solver.Solve()
    solve_status = result.from_mip(status)
    if not solve_status.is_success:
        return SolveResult(
            frame=_nw.to_native(frame),
            status=solve_status,
            objective=None,
            metadata={"solver": "GLOP"},
        )

    quantities = [qty[i].solution_value() for i in range(n)]
    frame = frame.with_columns(
        nw.new_series(quantity_column, quantities, backend=frame.implementation)
    )
    return SolveResult(
        frame=_nw.to_native(frame),
        status=solve_status,
        objective=solver.Objective().Value(),
        metadata={"solver": "GLOP"},
    )
