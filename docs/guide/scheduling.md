# Scheduling

Solvers in the **interval-schedule** shape place work on a timeline.

## Shift scheduling

*What it is:* staff each (day, shift) to its required headcount, with at most one shift
per worker per day, balancing the load fairly. *When to use it:* rostering, on-call
rotas, staffing under coverage requirements.

```python
import pandas as pd
import ortidy

requirements = pd.DataFrame({
    "day": [0, 0, 1, 1, 2, 2],
    "shift": ["am", "pm", "am", "pm", "am", "pm"],
    "required": [1, 1, 1, 1, 1, 1],
})
workers = pd.DataFrame({"workerId": ["alice", "bob", "carol"]})

result = ortidy.shift_scheduling(requirements, workers)
result.objective   # the peak per-worker shift count (minimized for fairness)
result.frame       # one row per assigned (workerId, day, shift)
```

Optional `min_shifts` / `max_shifts` bound each worker's total shifts.

## Job shop

*What it is:* each job is a fixed sequence of tasks; each task runs on a specific
machine that can do one thing at a time; minimize the **makespan** (when the last task
finishes). *When to use it:* manufacturing, batch processing, any shared-resource
sequencing problem. Input is a tidy `(jobId, step, machine, duration)` frame.

```python
tasks = pd.DataFrame({
    "jobId": [0, 0, 1, 1],
    "step": [0, 1, 0, 1],          # order within the job
    "machine": ["m0", "m1", "m1", "m0"],
    "duration": [3, 2, 2, 4],
})
result = ortidy.job_shop(tasks)
result.objective                   # makespan
result.frame[["jobId", "machine", "start", "end"]]
```

The output adds `start` and `end` to each task — ready to drop into a Gantt chart (see
the `scheduling.ipynb` [example](../examples.md)).

## Interval assignment

*What it is:* the tasks already have **fixed** start/end times — the question is how
few (or how cheap a set of) resources can cover them, given a minimum gap between
consecutive tasks on a resource, and optionally that a resource must be in the right
*place* to take its next task. *When to use it:* aircraft rotations (gap =
turnaround), crew lines, gate/stand allocation, driver duty chaining, machine
reservations. See the [API page](../api/interval-assignment.rst) for the four-regime
table and the full worked walkthrough in `tail_assignment.ipynb`.

```python
tasks = pd.DataFrame({
    "taskId": ["b0", "b1", "b2"],
    "start":  [385, 400, 615],
    "end":    [580, 725, 810],
})
result = ortidy.interval_assignment(tasks, min_gap=25)
result.objective                # number of resources used
result.frame[["taskId", "resourceId"]]
```

Opt into complexity with optional columns: `start_location_column` /
`end_location_column` add place-connection chaining; a `resources` frame
(`resourceType`, `count`, `fixed_cost`) plus an `eligibility` `(taskId, resourceType)`
frame turn it into a minimum-cost typed-fleet assignment (the objective becomes total
`fixed_cost`, and it can be `INFEASIBLE` when `count` caps bind).
