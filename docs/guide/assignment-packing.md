# Assignment & packing

Solvers in the **assignment-matrix** shape map rows to columns / bins / resources.
Each returns your input frame with an assignment column added — so the answer lands
right back in the dataframe you started with.

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

A cost matrix *is* a dataframe: rows are agents, columns are tasks. Assign each agent
to one task, minimizing total cost (or `maximize=True`). Adds `assignedTo` and `cost`.

```python
costs = pd.DataFrame({"t0": [4, 1, 3], "t1": [2, 5, 2], "t2": [8, 4, 1]})

result = ortidy.assignment(costs)
result.objective                  # 4
list(result.frame["assignedTo"])  # ['t1', 't0', 't2']
```

Use `id_column="agent"` if a column labels the agents (it won't be treated as a task).

## Generalized assignment (GAP)

*What it is:* assign tasks to **capacity-limited** agents to maximize value, where each
task consumes a *size* on its agent. *When to use it:* workforce/job allocation, cloud
bin-packing, anything where agents have a budget and tasks have a cost and a payoff.

```python
values = pd.DataFrame({"a0": [10, 8, 5], "a1": [6, 9, 7]})   # value of task t on agent a
sizes = pd.DataFrame({"a0": [3, 4, 2], "a1": [2, 3, 4]})     # size consumed
result = ortidy.generalized_assignment(values, sizes, capacities={"a0": 5, "a1": 6})

result.objective              # 24
list(result.frame["assignedTo"])
```

Pass `require_all=True` to force every task to be assigned (infeasible if capacity is
too small), or leave it `False` to allow tasks to go unassigned.

## Facility location

Given a customer×facility cost matrix and a per-facility opening cost, decide which
facilities to open and assign each customer to one — minimizing opening + assignment
cost. Adds `assignedTo`; opened facilities are in `metadata["opened"]`.

```python
costs = pd.DataFrame({"f0": [1, 1, 9], "f1": [9, 9, 1]})       # 3 customers
setup = pd.DataFrame({"facility": ["f0", "f1"], "setupCost": [2, 100]})

result = ortidy.facility_location(costs, setup)
result.metadata["opened"]   # ['f0']  — the second facility is too expensive to open
```

## Set cover

*What it is:* pick the cheapest collection of subsets so every element is covered.
*When to use it:* crew/shift coverage, sensor/feature selection, "smallest set that
covers everything". Input is a membership matrix (one row per subset, a boolean column
per element) plus a `cost` column. Adds `isSelected`.

```python
subsets = pd.DataFrame({
    "subset": ["A", "B", "C"],
    "e0": [1, 0, 1], "e1": [1, 1, 0], "e2": [0, 1, 1], "e3": [0, 1, 0],
    "cost": [3, 2, 2],
})
result = ortidy.set_cover(subsets, subset_id="subset")
result.objective                       # 4  (subsets B + C)
result.frame[result.frame["isSelected"]]
```

Pass `partition=True` to require each element covered *exactly* once (set partition).
