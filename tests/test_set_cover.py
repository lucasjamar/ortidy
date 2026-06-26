"""Set cover / partition tests."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _subsets(backend: str):
    # 3 subsets over elements e0..e3; optimal cover is B+C (cost 4).
    df = pd.DataFrame(
        {
            "subset": ["A", "B", "C"],
            "e0": [1, 0, 1],
            "e1": [1, 1, 0],
            "e2": [0, 1, 1],
            "e3": [0, 1, 0],
            "cost": [3, 2, 2],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def test_covers_all_elements_at_min_cost(backend):
    result = ortidy.set_cover(_subsets(backend), subset_id="subset")
    assert result.status is SolveStatus.OPTIMAL
    assert result.objective == 4

    out = as_pandas(result.frame)
    chosen = out[out["isSelected"]]
    assert set(chosen["subset"]) == {"B", "C"}
    # Every element is covered by at least one chosen subset.
    for element in ["e0", "e1", "e2", "e3"]:
        assert chosen[element].sum() >= 1


def test_partition_requires_exact_cover():
    # Overlapping subsets: a partition must avoid double-covering e1/e2.
    subsets = pd.DataFrame(
        {
            "subset": ["A", "B", "C"],
            "e0": [1, 0, 0],
            "e1": [1, 1, 0],
            "e2": [0, 1, 1],
            "e3": [0, 0, 1],
            "cost": [1, 1, 1],
        }
    )
    result = ortidy.set_cover(subsets, subset_id="subset", partition=True)
    assert result.status is SolveStatus.OPTIMAL
    out = as_pandas(result.frame)
    chosen = out[out["isSelected"]]
    for element in ["e0", "e1", "e2", "e3"]:
        assert chosen[element].sum() == 1


def test_uncoverable_element_raises():
    subsets = pd.DataFrame({"subset": ["A"], "e0": [1], "e1": [0], "cost": [1]})
    with pytest.raises(ValueError, match="not covered by any subset"):
        ortidy.set_cover(subsets, subset_id="subset")


def test_backend_parity():
    pdf = ortidy.set_cover(_subsets("pandas"), subset_id="subset")
    pol = ortidy.set_cover(_subsets("polars"), subset_id="subset")
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective
