# Network flow & routing

Solvers in the **edge-flow** shape put values on an edge list. Flow solvers return
your edge frame with a flow column; routing returns an edge list of trips.

## Max flow

Maximum flow from a source to a sink over a capacitated edge list. Adds a `flow`
column; the objective is the max flow value.

```python
import pandas as pd
import ortidy

edges = pd.DataFrame({
    "from": [0, 0, 1, 2],
    "to":   [1, 2, 2, 3],
    "capacity": [3, 2, 2, 4],
})
result = ortidy.max_flow(edges, source=0, sink=3)
result.objective       # max flow
result.frame["flow"]   # flow on each edge
```

## Min-cost flow

Cheapest way to route node supplies through a capacitated, costed network.
`supplies` is a `(node, supply)` frame (positive = source, negative = sink).

```python
edges = pd.DataFrame({
    "from": [0, 0, 1, 2],
    "to":   [1, 2, 2, 3],
    "capacity": [10, 10, 10, 10],
    "cost": [4, 1, 1, 1],
})
supplies = pd.DataFrame({"node": [0, 3], "supply": [5, -5]})

result = ortidy.min_cost_flow(edges, supplies)
result.objective   # minimum total cost
```

## Shortest path

Shortest path from source to sink, solved as a unit min-cost flow. Adds an
`onPath` column (1 on the chosen path); the objective is the path length.

```python
edges = pd.DataFrame({
    "from": [0, 0, 1, 2],
    "to":   [1, 2, 3, 3],
    "weight": [1, 4, 1, 1],
})
result = ortidy.shortest_path(edges, source=0, sink=3)
result.objective                          # 2  (0 -> 1 -> 3)
result.frame[result.frame["onPath"] == 1]
```

## Distance matrix

Routing needs a square distance matrix. Build one from `x`/`y` (euclidean) or
`lat`/`lon` (haversine, kilometres) — so you can pass the *locations* you have.

```python
locations = pd.DataFrame({"x": [0, 3, 0], "y": [0, 0, 4]})
matrix = ortidy.distance_matrix(locations, method="euclidean")
# matrix.iloc[1, 2] == 5.0   (the 3-4-5 triangle)
```

Use `id_column=` to label the rows/columns by a location id.

## Routing

`solve_routing` takes a distance matrix and returns an edge list of trips, with
route feature-engineering (`tripsSinceStart`, `distanceSinceStart`, …).

### TSP (single vehicle)

```python
result = ortidy.solve_routing(matrix, vehicles=1)
result.frame  # departure -> destination, distance, route features
```

### Vehicle routing (multiple vehicles)

```python
result = ortidy.solve_routing(matrix, vehicles=4)
result.frame["vehicleId"]  # one route per vehicle
```

### Capacitated (CVRP)

Pass a `vehicles` frame with capacities and a `locations` frame with `demand`;
the result gains a `load` column.

```python
vehicles = pd.DataFrame({"vehicleId": [0, 1], "capacity": [15, 15]})
ortidy.solve_routing(matrix, vehicles=vehicles, locations=locations)
```

### Time windows (VRPTW) and pickups & deliveries

```python
windows = pd.DataFrame({"node": [0, 1, 2], "open": [0, 0, 0], "close": [100, 50, 80]})
ortidy.solve_routing(matrix, vehicles=2, time_windows=windows, service_time=5)

pairs = pd.DataFrame({"pickup": [1], "delivery": [2]})
ortidy.solve_routing(matrix, vehicles=2, pickups_deliveries=pairs)
```

Solver controls are parameters, not magic numbers: `max_distance`,
`span_cost_coefficient`, `time_limit`, `time_horizon`, `service_time`.
