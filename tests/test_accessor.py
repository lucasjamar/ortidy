"""Tests for the ``.or_`` dataframe accessor (the dataframe-native UX)."""

from __future__ import annotations

import ortidy  # noqa: F401  (registers the accessor on import)
from ortidy import data


def test_pandas_accessor_matches_function():
    items = data.items_knapsack("pandas")
    via_accessor = items.or_.knapsack(capacity=850)
    via_function = ortidy.knapsack(items, capacity=850)
    assert via_accessor.objective == via_function.objective


def test_polars_namespace_matches_function():
    items = data.items_knapsack("polars")
    via_accessor = items.or_.knapsack(capacity=850)
    via_function = ortidy.knapsack(items, capacity=850)
    assert via_accessor.objective == via_function.objective
    assert type(via_accessor.frame).__module__.split(".")[0] == "polars"
