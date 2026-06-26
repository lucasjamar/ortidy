# Assignment & packing

Solvers in the **selection** shape annotate your input table with what was chosen —
an item, a bin, or an edge — so the answer lands right back in the dataframe you
started with. Several take a tidy **edge list** (one row per allowed pairing), which
makes sparse problems natural: just omit the rows that can't happen.

## Knapsack

*What it is:* choose a subset of items of maximum total value that fits a capacity.
*When to use it:* budget allocation, cargo loading, "pick the best subset that fits".

```python
import pandas as pd
import ortidy

items = pd.DataFrame({"value": [60, 100, 120], "weight": [10, 20, 30]})
result = ortidy.knapsack(items, capacity=50)

result.status      # SolveStatus.OPTIMAL
result.objective   # 220
result.frame       # items + isIncluded
```

**Multidimensional knapsack** — constrain by several quantities at once (e.g. weight
*and* volume) by passing a list of weight columns and capacities:

```python
items = pd.DataFrame({
    "value": [60, 100, 120, 40],
    "weight": [10, 20, 30, 15],
    "volume": [2, 3, 4, 1],
})
ortidy.knapsack(items, capacity=[50, 6], weight=["weight", "volume"])
```

Floats are scaled to integers internally, so values/weights may be fractional.

## Multiple knapsack

Pack items into several bins of differing capacities, maximizing total packed value.
Each item gets the assigned `binId`, or null if left unpacked.

```python
items = pd.DataFrame({"itemId": [0, 1, 2], "value": [10, 30, 25], "weight": [5, 8, 6]})
bins = pd.DataFrame({"binId": [0, 1], "capacity": [10, 10]})

ortidy.multi_knapsack(items, bins, item_id="itemId")  # items + binId
```

## Bin packing

Pack **every** item into equal-capacity bins, minimizing the number of bins used.
The objective is the bin count.

```python
items = pd.DataFrame({"itemId": range(4), "weight": [48, 30, 19, 36]})

result = ortidy.bin_packing(items, capacity=100, item_id="itemId")
result.objective                 # number of bins used
result.frame["binId"].nunique()  # == objective
```

## Assignment

Assign each agent to one task, minimizing total cost (or `maximize=True`). Input is a
tidy **edge list** — one row per allowed `(agent, task)` pair with its cost — so a
sparse problem (an agent can only do *some* tasks) is just fewer rows. Adds a
`selected` boolean column.

```python
edges = pd.DataFrame({
    "agent": ["a0", "a0", "a1", "a1", "a2"],
    "task":  ["t0", "t1", "t0", "t1", "t2"],
    "cost":  [4,    2,    1,    5,    3],
})
result = ortidy.assignment(edges)
result.objective                       # total cost of the matching
result.frame[result.frame["selected"]]  # the chosen (agent, task) rows
```

Column names default to `agent` / `task` / `cost`; override with `left=` / `right=` /
`value=`.

**Team caps** — group agents into teams and limit how many each may use (a CP-SAT
model kicks in automatically):

```python
ortidy.assignment(edges, teams={"a0": "A", "a1": "A", "a2": "B"}, team_capacity=2)
```

**Allowed groups** — restrict which combinations of agents may be active together,
via an `(group, pattern, agent, active)` table enumerating allowed patterns:

```python
allowed = pd.DataFrame({
    "group":   ["G", "G"],
    "pattern": ["p0", "p0"],
    "agent":   ["a0", "a1"],
    "active":  [1, 0],          # pattern p0 allows a0 active, a1 inactive
})
ortidy.assignment(edges, allowed_groups=allowed)
```

## Generalized assignment (GAP)

*What it is:* assign tasks to **capacity-limited** agents to maximize value, where each
task consumes a *size* on its agent. *When to use it:* workforce/job allocation, cloud
bin-packing, anything where agents have a budget and tasks have a cost and a payoff.

An **edge list** with a `value` and a `size` per `(task, agent)` pair, plus per-agent
capacities (a mapping or a `(agent, capacity)` frame):

```python
edges = pd.DataFrame({
    "task":  ["t0", "t0", "t1", "t1", "t2", "t2"],
    "agent": ["a0", "a1", "a0", "a1", "a0", "a1"],
    "value": [10,   6,    8,    9,    5,    7],
    "size":  [3,    2,    4,    3,    2,    4],
})
result = ortidy.generalized_assignment(edges, capacities={"a0": 5, "a1": 6})
result.objective                       # 24
result.frame[result.frame["selected"]]
```

Pass `require_all=True` to force every task to be assigned (infeasible if capacity is
too small), or leave it `False` to allow tasks to go unassigned.

## Facility location

From an **edge list** of `(customer, facility, cost)` plus a per-facility opening cost,
decide which facilities to open and assign each customer to one — minimizing opening +
assignment cost. Adds `selected`; opened facilities are in `metadata["opened"]`.

```python
edges = pd.DataFrame({
    "customer": [0, 0, 1, 1, 2, 2],
    "facility": ["f0", "f1", "f0", "f1", "f0", "f1"],
    "cost":     [1, 9, 1, 9, 9, 1],
})
setup = pd.DataFrame({"facility": ["f0", "f1"], "setupCost": [2, 100]})

result = ortidy.facility_location(edges, setup)
result.metadata["opened"]   # ['f0']  — the second facility is too expensive to open
```

## Set cover

*What it is:* pick the cheapest collection of subsets so every element is covered.
*When to use it:* crew/shift coverage, sensor/feature selection, "smallest set that
covers everything". Input is a tidy **membership list** — one row per `(subset, element)`
pair the subset covers — plus a per-subset cost. Returns one row per subset with an
`isSelected` column.

```python
membership = pd.DataFrame({
    "subset":  ["A", "A", "B", "B", "B", "C", "C"],
    "element": ["e0", "e1", "e1", "e2", "e3", "e0", "e2"],
})
costs = pd.DataFrame({"subset": ["A", "B", "C"], "cost": [3, 2, 2]})

result = ortidy.set_cover(membership, costs)
result.objective                       # 4  (subsets B + C)
result.frame[result.frame["isSelected"]]
```

Pass `partition=True` to require each element covered *exactly* once (set partition).

## Blending / diet (LP)

*What it is:* choose a continuous quantity of each item to minimize cost while meeting
per-attribute requirements — the classic diet / blending linear program. *When to use
it:* nutrition planning, feed/fuel/material blending, any "cheapest mix that meets
specs". `items` has a `cost` column and one column per attribute; `requirements` is a
tidy `(attribute, min[, max])` table. Adds a continuous `quantity` column.

```python
items = pd.DataFrame({
    "food":     ["bread", "milk", "cheese"],
    "cost":     [1.0, 2.0, 3.0],
    "protein":  [4.0, 8.0, 7.0],
    "calories": [90.0, 120.0, 100.0],
})
requirements = pd.DataFrame({"attribute": ["protein", "calories"], "min": [10.0, 150.0]})

result = ortidy.blend(items, requirements)
result.objective                 # minimum total cost
result.frame[["food", "quantity"]]
```

Add a `max` column to `requirements` for upper bounds (null = no upper bound).
