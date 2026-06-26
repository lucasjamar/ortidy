# Getting started

## Install

```bash
pip install ortidy
```

`ortidy` brings its own OR-Tools. Bring your own dataframe backend (`pandas`,
`polars`, …) — install whichever you already use.

## Your first solve

Every solver is a plain function: pass a native frame, get a `SolveResult` back in
the same backend.

```python
import pandas as pd
import ortidy

items = pd.DataFrame({"value": [60, 100, 120], "weight": [10, 20, 30]})
result = ortidy.knapsack(items, capacity=50)

result.status      # SolveStatus.OPTIMAL
result.objective   # 220
result.frame       # the items frame + an `isIncluded` boolean column
bool(result)       # True — OPTIMAL or FEASIBLE counts as success
```

## Backends are preserved

Pass Polars, get Polars back — same call, same result:

```python
import polars as pl

items = pl.DataFrame({"value": [60, 100, 120], "weight": [10, 20, 30]})
result = ortidy.knapsack(items, capacity=50)
type(result.frame)   # polars.DataFrame
```

This is the whole point of the [Narwhals](https://narwhals-dev.github.io/narwhals/)
layer: `ortidy`'s solver logic never depends on a specific dataframe library.

## What's next

- [Result shapes](concepts/result-shapes.md) — the three shapes every solver fits.
- The solver guide — worked examples for
  [assignment & packing](guide/assignment-packing.md),
  [network flow & routing](guide/network-flow-routing.md), and
  [scheduling](guide/scheduling.md).
- [Examples](examples.md) — runnable notebooks.
