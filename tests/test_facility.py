"""Facility-location tests (long edge-list form)."""

from __future__ import annotations

import pandas as pd

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _edges(backend: str):
    df = pd.DataFrame(
        {
            "customer": [0, 0, 1, 1, 2, 2],
            "facility": ["f0", "f1", "f0", "f1", "f0", "f1"],
            "cost": [1, 9, 1, 9, 9, 1],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def _setup(backend: str, second=2):
    df = pd.DataFrame({"facility": ["f0", "f1"], "setupCost": [2, second]})
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def test_opens_facilities_and_assigns(backend):
    result = ortidy.facility_location(_edges(backend), _setup(backend))
    assert result.status is SolveStatus.OPTIMAL
    out = as_pandas(result.frame)
    chosen = out[out["selected"]]
    # Every customer assigned exactly once, to an opened facility.
    assert chosen.groupby("customer").size().eq(1).all()
    assert set(chosen["facility"]).issubset(set(result.metadata["opened"]))


def test_open_both_when_cheap():
    # Both setups cheap (2 each): open both, serve everyone at cost 1 → 2+2+1+1+1 = 7.
    result = ortidy.facility_location(_edges("pandas"), _setup("pandas"))
    assert result.objective == 7
    assert set(result.metadata["opened"]) == {"f0", "f1"}


def test_high_setup_consolidates():
    # f1 expensive → serve everyone from f0: open(2) + 1 + 1 + 9 = 13.
    result = ortidy.facility_location(_edges("pandas"), _setup("pandas", second=100))
    assert result.metadata["opened"] == ["f0"]
    assert result.objective == 13


def test_backend_parity():
    pdf = ortidy.facility_location(_edges("pandas"), _setup("pandas"))
    pol = ortidy.facility_location(_edges("polars"), _setup("polars"))
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective
