"""Knapsack solver tests: correctness, golden-file, backend parity, errors."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy import data
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name

# Golden values for items_knapsack.csv at capacity=850 (deterministic optimum).
GOLDEN_OBJECTIVE = 7534
GOLDEN_N_INCLUDED = 32


def test_correctness_respects_capacity_and_value(backend):
    items = data.items_knapsack(backend)
    capacity = 850
    res = ortidy.knapsack(items, capacity=capacity)

    assert res.status is SolveStatus.OPTIMAL
    out = as_pandas(res.frame)
    chosen = out[out["isIncluded"]]
    # Feasibility: total weight within capacity.
    assert chosen["weight"].sum() <= capacity
    # Objective equals the summed value of chosen items.
    assert chosen["value"].sum() == res.objective


def test_golden_file(backend):
    items = data.items_knapsack(backend)
    res = ortidy.knapsack(items, capacity=850)
    out = as_pandas(res.frame)
    assert res.objective == GOLDEN_OBJECTIVE
    assert int(out["isIncluded"].sum()) == GOLDEN_N_INCLUDED


def test_backend_parity():
    pdf = ortidy.knapsack(data.items_knapsack("pandas"), capacity=850)
    pol = ortidy.knapsack(data.items_knapsack("polars"), capacity=850)
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective
    assert as_pandas(pdf.frame)["isIncluded"].tolist() == (
        as_pandas(pol.frame)["isIncluded"].tolist()
    )


def test_float_values_are_scaled():
    items = pd.DataFrame({"value": [0.6, 0.6, 0.6], "weight": [1.0, 1.0, 1.0]})
    res = ortidy.knapsack(items, capacity=2.0)
    assert res.status is SolveStatus.OPTIMAL
    out = as_pandas(res.frame)
    assert int(out["isIncluded"].sum()) == 2  # only two fit
    assert res.objective == pytest.approx(1.2)


def test_multidimensional_knapsack():
    # Two constraints: weight <= 50 AND volume <= 6.
    items = pd.DataFrame(
        {
            "value": [60, 100, 120, 40],
            "weight": [10, 20, 30, 15],
            "volume": [2, 3, 4, 1],
        }
    )
    res = ortidy.knapsack(items, capacity=[50, 6], weight=["weight", "volume"])
    assert res.status is SolveStatus.OPTIMAL
    out = as_pandas(res.frame)
    chosen = out[out["isIncluded"]]
    assert chosen["weight"].sum() <= 50
    assert chosen["volume"].sum() <= 6
    assert chosen["value"].sum() == res.objective == 200


def test_mismatched_weight_capacity_raises():
    items = pd.DataFrame({"value": [1], "weight": [1], "volume": [1]})
    with pytest.raises(ValueError, match="must match"):
        ortidy.knapsack(items, capacity=[10], weight=["weight", "volume"])


def test_missing_column_raises_keyerror():
    items = pd.DataFrame({"value": [1, 2]})  # no weight column
    with pytest.raises(KeyError, match="weight"):
        ortidy.knapsack(items, capacity=10)


def test_empty_frame_raises_valueerror():
    items = pd.DataFrame({"value": [], "weight": []})
    with pytest.raises(ValueError, match="at least one row"):
        ortidy.knapsack(items, capacity=10)
