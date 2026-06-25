# Solvers

| Function | Shape | Problem |
| --- | --- | --- |
| `knapsack` | assignment-matrix | 0/1 knapsack |
| `multi_knapsack` | assignment-matrix | multiple knapsack |
| `bin_packing` | assignment-matrix | bin packing (minimize bins) |
| `assignment` | assignment-matrix | linear sum assignment |
| `facility_location` | assignment-matrix | uncapacitated facility location |
| `max_flow` | edge-flow | maximum flow |
| `min_cost_flow` | edge-flow | minimum-cost flow |
| `shortest_path` | edge-flow | shortest path |
| `solve_routing` | edge-flow | vehicle routing (+ capacity, VRPTW, pickups & deliveries) |
| `distance_matrix` | — | build a matrix from x/y or lat/long |
| `shift_scheduling` | interval-schedule | employee shift rostering |

## Solver controls

Solvers expose their controls as parameters rather than burying magic numbers:

- `time_limit` — wall-clock budget (seconds).
- `random_seed` — determinism for CP-SAT solvers.
- routing: `max_distance`, `span_cost_coefficient`, `time_horizon`, `service_time`.

## Numeric data

OR-Tools' knapsack and CP-SAT require integer coefficients. `ortidy` scales
floats to integers, solves, and unscales — you can pass floats directly.

See the [API reference](api.md) for full signatures.
