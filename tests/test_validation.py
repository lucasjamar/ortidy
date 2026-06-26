"""Input-validation tests for the strengthened schema checks."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import ortidy


def test_null_in_required_column_raises():
    items = pd.DataFrame({"value": [1.0, np.nan], "weight": [1.0, 2.0]})
    with pytest.raises(ValueError, match="null"):
        ortidy.knapsack(items, capacity=10)


def test_negative_weight_raises():
    items = pd.DataFrame({"value": [1, 2], "weight": [1, -3]})
    with pytest.raises(ValueError, match="non-negative"):
        ortidy.knapsack(items, capacity=10)


def test_negative_size_raises_gap():
    edges = pd.DataFrame(
        {
            "task": ["t0"],
            "agent": ["a0"],
            "value": [5],
            "size": [-1],
        }
    )
    with pytest.raises(ValueError, match="non-negative"):
        ortidy.generalized_assignment(edges, {"a0": 5})


def test_duplicate_id_column_raises():
    items = pd.DataFrame({"itemId": [0, 0], "weight": [1, 2]})  # duplicate itemId
    with pytest.raises(ValueError, match="unique"):
        ortidy.bin_packing(items, capacity=10, item_id="itemId")


def test_duplicate_bin_id_raises():
    items = pd.DataFrame({"itemId": [0], "value": [1], "weight": [1]})
    bins = pd.DataFrame({"binId": [0, 0], "capacity": [10, 10]})  # duplicate binId
    with pytest.raises(ValueError, match="unique"):
        ortidy.multi_knapsack(items, bins, item_id="itemId")


def test_duplicate_lookup_key_raises():
    edges = pd.DataFrame(
        {
            "source": ["S0"],
            "sink": ["k0"],
            "cost": [1],
        }
    )
    supply = pd.DataFrame({"node": ["S0", "S0"], "qty": [5, 5]})  # duplicate node
    with pytest.raises(ValueError, match="duplicate"):
        ortidy.transportation(edges, supply, {"k0": 5})


def test_negative_supply_raises():
    edges = pd.DataFrame({"source": ["S0"], "sink": ["k0"], "cost": [1]})
    with pytest.raises(ValueError, match="non-negative"):
        ortidy.transportation(edges, {"S0": -5}, {"k0": -5})
