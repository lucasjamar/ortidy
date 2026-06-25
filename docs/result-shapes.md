# Result shapes

Every `ortidy` solver produces one of exactly **three** result shapes. Designing
around these keeps the library a coherent whole rather than a bag of functions.

## assignment-matrix

Rows mapped to columns / bins / resources. The solver returns your frame with an
assignment column added.

| Solver | Assignment column |
| --- | --- |
| `knapsack` | `isIncluded` (boolean) |
| `multi_knapsack` | `binId` (assigned bin, or null) |
| `bin_packing` | `binId` |
| `assignment` | `assignedTo` (+ `cost`) |
| `facility_location` | `assignedTo` |

## edge-flow

Values on an edge list. The solver returns your edge frame with a flow column.

| Solver | Flow column |
| --- | --- |
| `max_flow` | `flow` |
| `min_cost_flow` | `flow` |
| `shortest_path` | `onPath` |
| `solve_routing` | edge list of trips (`departure → destination`, `distance`, …) |

## interval-schedule

Intervals placed on a timeline.

| Solver | Result |
| --- | --- |
| `shift_scheduling` | one row per assigned `(workerId, day, shift)` |

!!! warning "Don't invent a fourth shape"
    If a new feature doesn't fit one of these three, that's a design discussion
    before it's an implementation.

## The result object

Every solver returns a `SolveResult`:

```python
result.frame       # native dataframe, same backend as the input (None if no solution)
result.status      # OPTIMAL / FEASIBLE / INFEASIBLE / UNBOUNDED / MODEL_INVALID
result.objective   # objective value (None when no solution)
result.metadata    # solver name, wall time, bounds, …
bool(result)       # True when OPTIMAL or FEASIBLE
```

A **`FEASIBLE` solution is a success**, not a failure — `bool(result)` and
`result.status.is_success` both treat it as one.
