"""Bin-packing tests: correctness, golden-file, infeasible, backend parity."""

from __future__ import annotations

import pandas as pd

import ortidy
from ortidy import data
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name

# items_bin_packing.csv with capacity=100 packs optimally into 4 bins.
GOLDEN_BINS = 4


def _items(backend):
    return as_pandas(data.items_bin_packing(backend)).assign(
        itemId=lambda d: range(len(d))
    )


def test_every_item_assigned_and_capacity_respected(backend):
    items = _items(backend)
    res = ortidy.bin_packing(items, capacity=100, item_id="itemId")
    assert res.status is SolveStatus.OPTIMAL

    out = as_pandas(res.frame)
    assert len(out) == len(items)  # every item present
    assert out["binId"].notna().all()  # every item assigned
    for _, grp in out.groupby("binId"):
        assert grp["weight"].sum() <= 100


def test_golden_objective_is_min_bins(backend):
    items = _items(backend)
    res = ortidy.bin_packing(items, capacity=100, item_id="itemId")
    out = as_pandas(res.frame)
    assert res.objective == GOLDEN_BINS
    assert out["binId"].nunique() == GOLDEN_BINS


def test_infeasible_when_item_exceeds_capacity():
    items = pd.DataFrame({"itemId": [0, 1], "weight": [5, 200]})
    res = ortidy.bin_packing(items, capacity=10, item_id="itemId")
    assert res.status is SolveStatus.INFEASIBLE
    assert res.objective is None


def test_backend_parity():
    pd_res = ortidy.bin_packing(_items("pandas"), capacity=100, item_id="itemId")
    pol_res = ortidy.bin_packing(
        data.items_bin_packing("polars").with_row_index("itemId"),
        capacity=100,
        item_id="itemId",
    )
    assert native_type_name(pd_res.frame) == "pandas"
    assert native_type_name(pol_res.frame) == "polars"
    assert pd_res.objective == pol_res.objective
