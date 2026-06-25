# The `.or_` accessor

The headline "dataframe-native" UX. Importing `ortidy` registers an `or_`
namespace on the frame you already hold — on **both** pandas and Polars — so OR
calls read idiomatically.

```python
import ortidy  # registers the accessor

items.or_.knapsack(capacity=50)
items.or_.multi_knapsack(bins=bins)
costs.or_.assignment()
edges.or_.max_flow(source="a", sink="z")
locations.or_.distance_matrix(method="haversine")
distances.or_.route(vehicles=4)
requirements.or_.shift_scheduling(workers=team)
```

Each accessor method forwards to the matching standalone function, passing the
frame as the first argument, and returns the same
[`SolveResult`](result-shapes.md#the-result-object). The standalone functions
remain fully supported — the accessor is sugar, not a separate API.

The backend you call on is the backend you get back:

```python
import polars as pl

pl_items = pl.DataFrame({"value": [60, 100], "weight": [10, 20]})
result = pl_items.or_.knapsack(capacity=25)
type(result.frame)   # polars.DataFrame
```
