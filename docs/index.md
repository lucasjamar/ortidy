# ortidy

**OR** (operations research) on **tidy** dataframes — a backend-agnostic dataframe
façade over [Google OR-Tools](https://developers.google.com/optimization).

`ortidy` bridges operations research and the data ecosystem: pass a dataframe in,
get a dataframe back, ready for analysis, plotting, and dashboards. It is built on
[Narwhals](https://narwhals-dev.github.io/narwhals/), so **pandas in → pandas out,
Polars in → Polars out**.

## Install

```bash
pip install ortidy
```

## Hello, knapsack

```python
import pandas as pd
import ortidy

items = pd.DataFrame({"value": [60, 100, 120], "weight": [10, 20, 30]})
result = ortidy.knapsack(items, capacity=50)

result.status       # SolveStatus.OPTIMAL
result.objective    # 220
result.frame        # items + an `isIncluded` column
```

Every solver is a plain function: pass a native frame, get a `SolveResult` back
in the same backend.

## The conceptual spine

Two ideas hold the library together:

- **[Three result shapes](result-shapes.md)** — every solver returns one of
  *assignment-matrix*, *edge-flow*, or *interval-schedule*.
- **[One result object](result-shapes.md#the-result-object)** — every solver
  returns a `SolveResult` (frame, status, objective, metadata). A `FEASIBLE`
  solution is a success.

See [Solvers](solvers.md) for the full catalogue and the [API reference](api.md)
for signatures.

!!! note "Migrating from `pandas-or`"
    `ortidy` is `pandas-or` renamed and rebuilt. Install `ortidy` and
    `import ortidy`; the old `pandas-or` 0.1.3 on PyPI is unmaintained.
