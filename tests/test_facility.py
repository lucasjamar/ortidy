"""Facility-location tests (assignment-matrix shape)."""

from __future__ import annotations

import pandas as pd

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _costs(backend: str):
    # 3 customers, 2 candidate facilities (f0 cheap-ish, f1 close to customer 2).
    df = pd.DataFrame({"f0": [1, 1, 9], "f1": [9, 9, 1]})
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def _setup(backend: str):
    df = pd.DataFrame({"facility": ["f0", "f1"], "setupCost": [2, 2]})
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def test_opens_facilities_and_assigns(backend):
    res = ortidy.facility_location(_costs(backend), _setup(backend))
    assert res.status is SolveStatus.OPTIMAL
    out = as_pandas(res.frame)
    assert "assignedTo" in out.columns
    # Every customer assigned to an opened facility.
    opened = set(res.metadata["opened"])
    assert set(out["assignedTo"]).issubset(opened)


def test_objective_is_open_plus_assignment_cost():
    # Single facility f0 serves all: open(2) + 1 + 1 + 9 = 13.
    # Open both: 2+2 + 1 + 1 + 1 = 7  → optimal opens both.
    res = ortidy.facility_location(_costs("pandas"), _setup("pandas"))
    assert res.objective == 7
    assert set(res.metadata["opened"]) == {"f0", "f1"}


def test_high_setup_cost_consolidates():
    # Very expensive to open a second facility → serve everyone from one.
    setup = pd.DataFrame({"facility": ["f0", "f1"], "setupCost": [2, 100]})
    res = ortidy.facility_location(_costs("pandas"), setup)
    assert res.metadata["opened"] == ["f0"]
    # open f0 (2) + assignments 1+1+9 = 13.
    assert res.objective == 13


def test_backend_parity():
    pd_res = ortidy.facility_location(_costs("pandas"), _setup("pandas"))
    pol_res = ortidy.facility_location(_costs("polars"), _setup("polars"))
    assert native_type_name(pd_res.frame) == "pandas"
    assert native_type_name(pol_res.frame) == "polars"
    assert pd_res.objective == pol_res.objective
