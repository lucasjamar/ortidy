# Examples

Runnable notebooks live in [`examples/`](https://github.com/lucasjamar/ortidy/tree/main/examples).
Launch them interactively on Binder — no install required:

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/lucasjamar/ortidy/main?labpath=examples)

| Notebook | Covers |
| --- | --- |
| `binning.ipynb` | knapsack, multiple knapsack, bin packing, multidimensional knapsack |
| `assignment_and_flow.ipynb` | assignment, generalized assignment, transportation, max flow, min-cost flow, shortest path, facility location, set cover |
| `scheduling.ipynb` | shift scheduling, job shop (with a Gantt chart) |
| `tail_assignment.ipynb` | `interval_assignment` across all four regimes (aircraft tail assignment), plus the `solve_routing` VRPTW escape hatch |
| `travelling_salesperson.ipynb` | a haversine world-tour TSP, plotted on a globe |
| `vehicle_routing.ipynb` | multi-vehicle and capacitated routing |

Every notebook is output-stripped in the repo and verified to execute end-to-end
in CI.
