"""Uncapacitated facility location — assignment-matrix shape.

Given an assignment-cost matrix (customers × candidate facilities) and a per-
facility opening cost, decide which facilities to open and assign each customer
to one open facility, minimizing total opening + assignment cost. Returns the
customer cost-matrix frame with an ``assignedTo`` column added.

Built on CP-SAT.

Link:
    https://en.wikipedia.org/wiki/Facility_location_problem
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw

from ortidy import _narwhals as _nw
from ortidy import _scaling, result, schema
from ortidy.result import SolveResult


def facility_location(
    costs: Any,
    setup_costs: Any,
    *,
    id_column: str | None = None,
    facility_column: str = "facility",
    setup_cost_column: str = "setupCost",
    assigned_column: str = "assignedTo",
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Solve an uncapacitated facility-location problem.

    Parameters:
        costs: Customer×facility assignment-cost matrix. Each non-id column is a
            candidate facility; each row a customer.
        setup_costs: Frame of ``(facility, setupCost)`` opening costs. Facility
            labels must match the facility (column) labels in ``costs``.
        id_column: Optional customer-id column in ``costs`` (not a facility).
        facility_column: Facility-label column within ``setup_costs``.
        setup_cost_column: Opening-cost column within ``setup_costs``.
        assigned_column: Name of the added column holding each customer's facility.
        time_limit: Optional wall-clock limit in seconds.
        random_seed: Solver seed for determinism.

    Returns:
        SolveResult whose ``frame`` is the cost matrix (same backend) plus an
        ``assigned_column``; objective is total opening + assignment cost, and
        metadata lists the opened facilities.
    """
    from ortools.sat.python import cp_model

    frame = _nw.to_nw(costs)
    setup = _nw.to_nw(setup_costs)
    schema.require_nonempty(frame, frame_name="costs")
    schema.require_columns(
        setup, {facility_column, setup_cost_column}, frame_name="setup_costs"
    )

    facilities = [c for c in frame.columns if c != id_column]
    if not facilities:
        raise ValueError("costs must have at least one facility column.")
    schema.require_numeric(frame, set(facilities), frame_name="costs")

    setup_map = dict(
        zip(
            [str(v) for v in _nw.column_to_list(setup, facility_column)],
            _nw.column_to_list(setup, setup_cost_column),
            strict=True,
        )
    )
    missing = set(facilities) - set(setup_map)
    if missing:
        raise KeyError(f"setup_costs is missing opening cost for {sorted(missing)}.")

    n_customers = frame.shape[0]
    cost_cols = {f: _nw.column_to_list(frame, f) for f in facilities}

    # Shared integer scale across assignment and setup costs.
    flat = [cost_cols[f][i] for i in range(n_customers) for f in facilities]
    flat += [setup_map[f] for f in facilities]
    _, factor = _scaling.scale_to_int(flat)

    model = cp_model.CpModel()
    open_var = {f: model.new_bool_var(f"open_{f}") for f in facilities}
    assign = {
        (i, f): model.new_bool_var(f"assign_{i}_{f}")
        for i in range(n_customers)
        for f in facilities
    }
    for i in range(n_customers):
        model.add_exactly_one(assign[i, f] for f in facilities)
        for f in facilities:
            model.add(assign[i, f] <= open_var[f])

    model.minimize(
        sum(
            assign[i, f] * round(cost_cols[f][i] * factor)
            for i in range(n_customers)
            for f in facilities
        )
        + sum(open_var[f] * round(setup_map[f] * factor) for f in facilities)
    )

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

    assigned = []
    for i in range(n_customers):
        for f in facilities:
            if solver.value(assign[i, f]) == 1:
                assigned.append(f)
                break
    opened = [f for f in facilities if solver.value(open_var[f]) == 1]

    frame = frame.with_columns(
        nw.new_series(assigned_column, assigned, backend=frame.implementation)
    )
    return SolveResult(
        frame=_nw.to_native(frame),
        status=solve_status,
        objective=_scaling.unscale(solver.objective_value, factor),
        metadata={"solver": "CP-SAT", "opened": opened, "wall_time": solver.wall_time},
    )
