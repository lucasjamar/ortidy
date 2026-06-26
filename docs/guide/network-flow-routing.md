# Network flow & routing

Solvers in the **edge-flow** shape put values on an edge list. Flow solvers return
your edge frame with a flow column; transportation and routing return a tidy edge
list of shipments / trips.

## Max flow

Maximum flow from a source to a sink over a capacitated edge list. Adds a `flow`
column; the objective is the max flow value.

```python
import pandas as pd
import ortidy

edges = pd.DataFrame({"from": [0, 0, 1, 2], "to": [1, 2, 2, 3], "capacity": [3, 2, 2, 4]})
result = ortidy.max_flow(edges, source=0, sink=3)
result.objective       # max flow
result.frame["flow"]   # flow on each edge
```

## Min-cost flow

Cheapest way to route node supplies through a capacitated, costed network. `supplies`
is a `(node, supply)` frame (positive = source, negative = sink).

```python
edges = pd.DataFrame({
    "from": [0, 0, 1, 2], "to": [1, 2, 2, 3],
    "capacity": [10, 10, 10, 10], "cost": [4, 1, 1, 1],
})
supplies = pd.DataFrame({"node": [0, 3], "supply": [5, -5]})
ortidy.min_cost_flow(edges, supplies).objective   # 10
```

## Shortest path

Shortest path from source to sink, solved as a unit min-cost flow. Adds an `onPath`
column (1 on the chosen path); the objective is the path length.

```python
edges = pd.DataFrame({"from": [0, 0, 1, 2], "to": [1, 2, 3, 3], "weight": [1, 4, 1, 1]})
result = ortidy.shortest_path(edges, source=0, sink=3)
result.objective                          # 2  (0 -> 1 -> 3)
result.frame[result.frame["onPath"] == 1]
```

## Transportation

*What it is:* ship goods from sources to sinks at minimum total cost, respecting each
source's supply and each sink's demand. *When to use it:* logistics, distribution,
matching production to consumption. Input is a tidy **edge list** of `(source, sink, cost)`
lanes (omit forbidden lanes) plus supply and demand; total supply must equal total demand.

```python
edges = pd.DataFrame({
    "source": ["S0", "S0", "S0", "S1", "S1", "S1"],
    "sink":   ["k0", "k1", "k2", "k0", "k1", "k2"],
    "cost":   [4,    3,    1,    5,    2,    3],
})
result = ortidy.transportation(
    edges, supply={"S0": 10, "S1": 15}, demand={"k0": 8, "k1": 9, "k2": 8},
)
result.objective                            # total shipping cost
result.frame[result.frame["quantity"] > 0]  # the shipments
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

`solve_routing` takes a distance matrix and returns an edge list of trips, with route
feature-engineering (`tripsSinceStart`, `distanceSinceStart`, …).

```python
ortidy.solve_routing(matrix, vehicles=1)   # TSP — one route
ortidy.solve_routing(matrix, vehicles=4)   # VRP — one route per vehicle
```

**Capacitated (CVRP)** — a `vehicles` frame with capacities and a `locations` frame
with `demand`; the result gains a `load` column:

```python
vehicles = pd.DataFrame({"vehicleId": [0, 1], "capacity": [15, 15]})
ortidy.solve_routing(matrix, vehicles=vehicles, locations=locations)
```

**Time windows (VRPTW)** and **pickups & deliveries**:

```python
windows = pd.DataFrame({"node": [0, 1, 2], "open": [0, 0, 0], "close": [100, 50, 80]})
ortidy.solve_routing(matrix, vehicles=2, time_windows=windows, service_time=5)

pairs = pd.DataFrame({"pickup": [1], "delivery": [2]})
ortidy.solve_routing(matrix, vehicles=2, pickups_deliveries=pairs)
```

**Optional visits (prize-collecting)** — make stops droppable at a penalty, so the
solver skips ones too costly to serve. Dropped nodes are in `metadata["dropped"]`:

```python
penalties = pd.DataFrame({"node": [4], "penalty": [10]})
result = ortidy.solve_routing(matrix, vehicles=1, penalties=penalties)
result.metadata["dropped"]   # nodes left unserved
```

**Fleet sizing** — charge a fixed cost per vehicle used so the solver minimizes how
many vehicles it dispatches:

```python
ortidy.solve_routing(matrix, vehicles=5, vehicle_fixed_cost=1000)
```

Solver controls are parameters, not magic numbers: `max_distance`,
`span_cost_coefficient`, `time_limit`, `time_horizon`, `service_time`.
