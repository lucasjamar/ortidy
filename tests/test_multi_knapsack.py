"""Multiple-knapsack tests: correctness, backend parity, infeasible, errors."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy import data
from tests.conftest import as_pandas, native_type_name


def _with_ids(backend):
    items = as_pandas(data.items_multi(backend)).assign(itemId=lambda d: range(len(d)))
    bins = as_pandas(data.bins(backend)).assign(binId=lambda d: range(len(d)))
    return items, bins


def test_correctness_constraints_hold(backend):
    items, bins = _with_ids(backend)
    res = ortidy.multi_knapsack(items, bins, item_id="itemId")
    assert res.status.is_success

    out = as_pandas(res.frame)
    # Each item is assigned to at most one bin (one binId value or null).
    assert len(out) == len(items)
    # Per-bin packed weight never exceeds capacity.
    cap = bins.set_index("binId")["capacity"]
    packed = out.dropna(subset=["binId"])
    for bin_id, grp in packed.groupby("binId"):
        assert grp["weight"].sum() <= cap.loc[bin_id]


def test_objective_matches_packed_value(backend):
    items, bins = _with_ids(backend)
    res = ortidy.multi_knapsack(items, bins, item_id="itemId")
    out = as_pandas(res.frame)
    packed_value = out.dropna(subset=["binId"])["value"].sum()
    assert res.objective == pytest.approx(packed_value)


def test_backend_parity():
    ip, bp = _with_ids("pandas")
    pol_res = ortidy.multi_knapsack(
        data.items_multi("polars").with_row_index("itemId"),
        data.bins("polars").with_row_index("binId"),
        item_id="itemId",
    )
    pd_res = ortidy.multi_knapsack(ip, bp, item_id="itemId")
    assert native_type_name(pd_res.frame) == "pandas"
    assert native_type_name(pol_res.frame) == "polars"
    assert pd_res.objective == pol_res.objective


def test_infeasible_returns_status_not_exception():
    # Item too heavy for every bin → no feasible packing of it, but the model is
    # still solvable (it just stays unpacked) → success with it left out.
    items = pd.DataFrame({"itemId": [0, 1], "weight": [5, 999], "value": [1, 100]})
    bins = pd.DataFrame({"binId": [0], "capacity": [10]})
    res = ortidy.multi_knapsack(items, bins, item_id="itemId")
    assert res.status.is_success
    out = as_pandas(res.frame)
    assert pd.isna(out.loc[out["itemId"] == 1, "binId"]).all()  # heavy item unpacked


def test_missing_bin_column_raises():
    items = pd.DataFrame({"itemId": [0], "weight": [1], "value": [1]})
    bins = pd.DataFrame({"binId": [0]})  # missing capacity
    with pytest.raises(KeyError, match="capacity"):
        ortidy.multi_knapsack(items, bins, item_id="itemId")
