"""Job shop scheduling — interval-schedule shape.

Schedule a set of jobs, each a fixed sequence of tasks, onto shared machines (each
machine does one task at a time), minimizing the makespan (the time the last task
finishes). Input is a tidy frame of tasks ``(jobId, step, machine, duration)``;
the output places each task on the timeline with a ``start`` and ``end``.

Built on CP-SAT interval variables. Durations are treated as integers.

Link:
    https://developers.google.com/optimization/scheduling/job_shop
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
from ortools.sat.python import cp_model

from ortidy import _narwhals as _nw
from ortidy import result, schema
from ortidy.result import SolveResult


def job_shop(
    tasks: Any,
    *,
    job_column: str = "jobId",
    step_column: str = "step",
    machine_column: str = "machine",
    duration_column: str = "duration",
    start_column: str = "start",
    end_column: str = "end",
    time_limit: float | None = None,
    random_seed: int = 0,
) -> SolveResult:
    """Solve a job-shop scheduling problem.

    Parameters:
        tasks: Tidy frame of tasks with job, step (order within the job), machine,
            and duration columns.
        job_column, step_column, machine_column, duration_column: Input column names.
        start_column, end_column: Names of the added schedule columns.
        time_limit: Optional wall-clock limit in seconds.
        random_seed: Solver seed for determinism.

    Returns:
        SolveResult whose ``frame`` is the input frame (same backend) plus
        ``start`` and ``end`` columns; objective is the makespan.
    """
    frame = _nw.to_nw(tasks)
    schema.require_nonempty(frame, frame_name="tasks")
    schema.require_columns(
        frame,
        {job_column, step_column, machine_column, duration_column},
        frame_name="tasks",
    )
    schema.require_numeric(frame, {step_column, duration_column}, frame_name="tasks")

    jobs = _nw.column_to_list(frame, job_column)
    steps = _nw.column_to_list(frame, step_column)
    machines = _nw.column_to_list(frame, machine_column)
    durations = [round(d) for d in _nw.column_to_list(frame, duration_column)]
    n = len(jobs)
    horizon = sum(durations)

    model = cp_model.CpModel()
    starts, ends, intervals = [], [], []
    for i in range(n):
        s = model.new_int_var(0, horizon, f"s_{i}")
        e = model.new_int_var(0, horizon, f"e_{i}")
        intervals.append(model.new_interval_var(s, durations[i], e, f"iv_{i}"))
        starts.append(s)
        ends.append(e)

    # Precedence: within each job, tasks run in ascending step order.
    by_job: dict[Any, list[int]] = {}
    for i in range(n):
        by_job.setdefault(jobs[i], []).append(i)
    for indices in by_job.values():
        ordered = sorted(indices, key=lambda i: steps[i])
        for a, b in zip(ordered, ordered[1:], strict=False):
            model.add(starts[b] >= ends[a])

    # Each machine processes one task at a time.
    by_machine: dict[Any, list[int]] = {}
    for i in range(n):
        by_machine.setdefault(machines[i], []).append(i)
    for indices in by_machine.values():
        model.add_no_overlap([intervals[i] for i in indices])

    makespan = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(makespan, ends)
    model.minimize(makespan)

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

    frame = frame.with_columns(
        nw.new_series(
            start_column,
            [solver.value(starts[i]) for i in range(n)],
            backend=frame.implementation,
        ),
        nw.new_series(
            end_column,
            [solver.value(ends[i]) for i in range(n)],
            backend=frame.implementation,
        ),
    )
    return SolveResult(
        frame=_nw.to_native(frame),
        status=solve_status,
        objective=round(solver.objective_value),
        metadata={"solver": "CP-SAT", "wall_time": solver.wall_time},
    )
