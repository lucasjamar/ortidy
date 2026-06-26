# Result shapes

Every `ortidy` solver produces one of exactly **three** result shapes. Designing
around these keeps the library a coherent whole rather than a bag of functions —
once you know a solver's shape, you know what its output looks like.

## selection

The input table gains a selection / assignment column marking what was chosen — an
item, a bin, or an edge in a tidy edge list.

| Solver | Selection column |
| --- | --- |
| `knapsack` | `isIncluded` (boolean) |
| `multi_knapsack` | `binId` (assigned bin, or null) |
| `bin_packing` | `binId` |
| `assignment` | `selected` (boolean, on `(agent, task)` edges) |
| `generalized_assignment` | `selected` (on `(task, agent)` edges) |
| `facility_location` | `selected` (on `(customer, facility)` edges) |
| `set_cover` | `isSelected` (boolean, per subset) |

## edge-flow

A numeric flow on an edge list. The solver returns the edges with a flow column.

| Solver | Output |
| --- | --- |
| `max_flow` | edges + `flow` |
| `min_cost_flow` | edges + `flow` |
| `shortest_path` | edges + `onPath` |
| `transportation` | `(source, sink, cost)` edges + `quantity` |
| `solve_routing` | edge list of trips with route features |

## interval-schedule

Intervals placed on a timeline.

| Solver | Output |
| --- | --- |
| `shift_scheduling` | one row per assigned `(workerId, day, shift)` |
| `job_shop` | tasks + `start` / `end` |

```{warning}
If a new feature doesn't fit one of these three shapes, that's a design
discussion before it's an implementation.
```

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
`result.status.is_success` both treat it as one. See the
[API reference](../api/result.rst) for the full `SolveResult` and `SolveStatus`.
