# Assignment & packing

Solvers in the **assignment-matrix** shape map rows to columns / bins / resources.
Each returns your input frame with an assignment column added.

## Knapsack

Maximize the value of items packed into a single capacity-limited basket. Adds an
`isIncluded` boolean column.

```python
import pandas as pd
import ortidy

items = pd.DataFrame({"value": [60, 100, 120], "weight": [10, 20, 30]})
result = ortidy.knapsack(items, capacity=50)

result.status      # SolveStatus.OPTIMAL
result.objective   # 220
result.frame       # items + isIncluded
```

Floats are scaled to integers internally, so `value`/`weight` may be fractional.

## Multiple knapsack

Pack items into several bins of differing capacities, maximizing total packed
value. Each item gets the assigned `binId`, or null if left unpacked.

```python
items = pd.DataFrame({"itemId": [0, 1, 2], "value": [10, 30, 25], "weight": [5, 8, 6]})
bins = pd.DataFrame({"binId": [0, 1], "capacity": [10, 10]})

result = ortidy.multi_knapsack(items, bins, item_id="itemId")
result.frame   # items + binId (NaN where unpacked)
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

A cost matrix *is* a dataframe: rows are agents, columns are tasks. Assign each
agent to one task, minimizing total cost (or `maximize=True`). Adds `assignedTo`
and `cost`.

```python
costs = pd.DataFrame({"t0": [4, 1, 3], "t1": [2, 5, 2], "t2": [8, 4, 1]})

result = ortidy.assignment(costs)
result.objective              # 4
list(result.frame["assignedTo"])  # ['t1', 't0', 't2']
```

Use `id_column="agent"` if a column labels the agents (it won't be treated as a
task).

## Facility location

Given a customer×facility cost matrix and a per-facility opening cost, decide
which facilities to open and assign each customer to one — minimizing opening +
assignment cost. Adds `assignedTo`; opened facilities are in `metadata["opened"]`.

```python
costs = pd.DataFrame({"f0": [1, 1, 9], "f1": [9, 9, 1]})       # 3 customers
setup = pd.DataFrame({"facility": ["f0", "f1"], "setupCost": [2, 100]})

result = ortidy.facility_location(costs, setup)
result.metadata["opened"]   # ['f0']  — second facility too expensive to open
result.frame["assignedTo"]  # every customer -> an opened facility
```
