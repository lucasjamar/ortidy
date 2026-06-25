"""Shift scheduling — interval-schedule shape.

Assigns workers to shift slots over a horizon so each (day, shift) is staffed to
its requirement, no worker works more than one shift per day, and the workload is
balanced. Returns a tidy assignment frame: one row per ``(workerId, day, shift)``
interval placed on the timeline.

Built on CP-SAT.

Link:
    https://developers.google.com/optimization/scheduling/employee_scheduling
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.sat.python import cp_model

from ortidy import _narwhals as _nw
from ortidy import result, schema
from ortidy.result import SolveResult


def shift_scheduling(
    requirements: Any,
    workers: Any,
    *,
    day_column: str = "day",
    shift_column: str = "shift",
    required_column: str = "required",
    worker_id_column: str = "workerId",
    min_shifts: int | None = None,
    max_shifts: int | None = None,
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Build a balanced shift roster.

    Parameters:
        requirements: Frame of ``(day, shift, required)`` — how many workers each
            shift on each day needs.
        workers: Frame with a worker-id column.
        day_column, shift_column, required_column: Columns within ``requirements``.
        worker_id_column: Worker-id column within ``workers`` (and the output).
        min_shifts, max_shifts: Optional per-worker shift-count bounds.
        time_limit: Optional wall-clock limit in seconds.
        random_seed: Solver seed for determinism.

    Returns:
        SolveResult whose ``frame`` (same backend as ``workers``) has one row per
        assigned ``(workerId, day, shift)``. The objective is the maximum number
        of shifts assigned to any single worker (minimized for fairness).
    """
    req = _nw.to_nw(requirements)
    wf = _nw.to_nw(workers)
    schema.require_nonempty(req, frame_name="requirements")
    schema.require_nonempty(wf, frame_name="workers")
    schema.require_columns(
        req, {day_column, shift_column, required_column}, frame_name="requirements"
    )
    schema.require_columns(wf, {worker_id_column}, frame_name="workers")

    days = _nw.column_to_list(req, day_column)
    shifts = _nw.column_to_list(req, shift_column)
    needs = _nw.column_to_list(req, required_column)
    worker_ids = _nw.column_to_list(wf, worker_id_column)

    slots = list(zip(days, shifts, needs, strict=True))
    day_values = sorted(set(days))

    model = cp_model.CpModel()
    x = {
        (w, d, s): model.new_bool_var(f"x_{w}_{d}_{s}")
        for w in range(len(worker_ids))
        for d, s, _ in slots
    }

    # Coverage: each (day, shift) staffed to its requirement.
    for d, s, need in slots:
        model.add(sum(x[w, d, s] for w in range(len(worker_ids))) == int(need))

    # At most one shift per worker per day.
    shifts_by_day: dict[Any, list[Any]] = {}
    for d, s, _ in slots:
        shifts_by_day.setdefault(d, []).append(s)
    for w in range(len(worker_ids)):
        for d in day_values:
            model.add(sum(x[w, d, s] for s in shifts_by_day[d]) <= 1)

    # Per-worker shift-count bounds and a fairness objective.
    loads = []
    for w in range(len(worker_ids)):
        load = sum(x[w, d, s] for d, s, _ in slots)
        if min_shifts is not None:
            model.add(load >= min_shifts)
        if max_shifts is not None:
            model.add(load <= max_shifts)
        loads.append(load)

    peak = model.new_int_var(0, len(slots), "peak_load")
    for load in loads:
        model.add(peak >= load)
    model.minimize(peak)

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = random_seed
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = time_limit
    status = solver.solve(model)
    solve_status = result.from_cp_sat(status)

    backend = wf.implementation
    if not solve_status.is_success:
        empty = nw.from_dict(
            {worker_id_column: [], day_column: [], shift_column: []},
            backend=backend,
        )
        return SolveResult(
            frame=_nw.to_native(empty),
            status=solve_status,
            objective=None,
            metadata={"solver": "CP-SAT"},
        )

    assigned_workers, assigned_days, assigned_shifts = [], [], []
    for w in range(len(worker_ids)):
        for d, s, _ in slots:
            if solver.value(x[w, d, s]) == 1:
                assigned_workers.append(worker_ids[w])
                assigned_days.append(d)
                assigned_shifts.append(s)

    frame = nw.from_dict(
        {
            worker_id_column: assigned_workers,
            day_column: assigned_days,
            shift_column: assigned_shifts,
        },
        backend=backend,
    )

    return SolveResult(
        frame=_nw.to_native(frame),
        status=solve_status,
        objective=round(solver.objective_value),
        metadata={"solver": "CP-SAT", "wall_time": solver.wall_time},
    )
