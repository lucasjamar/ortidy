# ortidy

[![CI](https://github.com/lucasjamar/ortidy/actions/workflows/ci.yml/badge.svg)](https://github.com/lucasjamar/ortidy/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/ortidy.svg)](https://pypi.org/project/ortidy/)
[![Python](https://img.shields.io/badge/python-3.10%20%E2%80%93%203.13-blue.svg)](https://pypi.org/project/ortidy/)
[![Docs](https://img.shields.io/badge/docs-online-blue.svg)](https://lucasjamar.github.io/ortidy/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/lucasjamar/ortidy/blob/main/LICENSE.md)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)

**OR** (operations research) on **tidy** dataframes — a backend-agnostic dataframe
façade over [Google OR-Tools](https://developers.google.com/optimization).

> `ortidy` is the revival of `pandas-or`, rebuilt around [Narwhals](https://narwhals-dev.github.io/narwhals/)
> so it works natively with **pandas, Polars, and more** — pandas in, pandas out;
> Polars in, Polars out. `pandas-or` users: see [Migrating](#migrating-from-pandas-or).

The thesis: bridge operations research and the data ecosystem so solver outputs
come back as tidy dataframes ready for analysis, plotting, and dashboards.

## Installation

```bash
pip install ortidy
```

`ortidy` brings its own OR-Tools. Bring your own dataframe backend (`pandas`,
`polars`, …) — install whichever you already use.

## Quickstart

Every solver accepts a native frame, returns the **same backend**, and hands back
a `SolveResult` carrying the result `frame`, a `status`, the `objective`, and
solve `metadata`.

```python
import pandas as pd
import ortidy

items = pd.DataFrame({"value": [60, 100, 120], "weight": [10, 20, 30]})

result = ortidy.knapsack(items, capacity=50)
print(result.status)        # SolveStatus.OPTIMAL
print(result.objective)     # 220
print(result.frame)         # items + an `isIncluded` boolean column
```

Every solver is a plain function — pass a native frame (pandas, Polars, …) and
get a `SolveResult` back in the same backend.

## Result contract

Three result *shapes* cover every solver:

| Shape | Solvers | Result |
| --- | --- | --- |
| **assignment-matrix** | `knapsack`, `multi_knapsack`, `bin_packing` | rows mapped to bins/resources |
| **edge-flow** | `solve_routing` (more in progress) | values on an edge list |
| **interval-schedule** | scheduling (roadmap) | intervals on a timeline |

Every solver returns a `SolveResult`:

```python
result.frame       # native dataframe, same backend as the input
result.status      # OPTIMAL / FEASIBLE / INFEASIBLE / UNBOUNDED / MODEL_INVALID
result.objective   # objective value (None when no solution)
result.metadata    # solver name, wall time, bounds, …
bool(result)       # True when OPTIMAL or FEASIBLE — a FEASIBLE solution is a success
```

## Solvers

| Function | Problem |
| --- | --- |
| `ortidy.knapsack(items, capacity)` | 0/1 knapsack |
| `ortidy.multi_knapsack(items, bins)` | multiple knapsack |
| `ortidy.bin_packing(items, capacity)` | bin packing (minimize bins) |
| `ortidy.solve_routing(matrix, vehicles=...)` | vehicle routing |

Sample datasets ship with the package:

```python
from ortidy import data
items = data.items_knapsack()            # pandas by default
items = data.items_knapsack("polars")    # or Polars
```

## Migrating from `pandas-or`

`ortidy` is `pandas-or` renamed and rebuilt. Install `ortidy` and `import ortidy`
(the old `pandas-or` 0.1.3 on PyPI is unmaintained). The key changes:

- Solvers return a **`SolveResult`** object, not a bare frame / `None`.
- Rows are identified by **explicit id columns**, never a positional index.
- The backend is **whatever you pass in** (pandas, Polars, …), not just pandas.

## License

Apache-2.0.
