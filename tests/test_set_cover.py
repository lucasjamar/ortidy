"""Set cover / partition tests (long membership-list form)."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _membership(backend: str):
    # A covers e0,e1; B covers e1,e2,e3; C covers e0,e2. Optimal cover B+C (cost 4).
    df = pd.DataFrame(
        {
            "subset": ["A", "A", "B", "B", "B", "C", "C"],
            "element": ["e0", "e1", "e1", "e2", "e3", "e0", "e2"],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def _costs(backend: str):
    df = pd.DataFrame({"subset": ["A", "B", "C"], "cost": [3, 2, 2]})
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def test_covers_all_elements_at_min_cost(backend):
    result = ortidy.set_cover(_membership(backend), _costs(backend))
    assert result.status is SolveStatus.OPTIMAL
    assert result.objective == 4

    out = as_pandas(result.frame)
    chosen = set(out[out["isSelected"]]["subset"])
    assert chosen == {"B", "C"}
    # Sanity: the chosen subsets cover every element.
    mem = as_pandas(_membership(backend))
    covered = set(mem[mem["subset"].isin(chosen)]["element"])
    assert covered == set(mem["element"])


def test_costs_as_mapping():
    result = ortidy.set_cover(_membership("pandas"), {"A": 3, "B": 2, "C": 2})
    assert result.objective == 4


def test_partition_requires_exact_cover():
    membership = pd.DataFrame(
        {
            "subset": ["A", "B", "B", "C"],
            "element": ["e0", "e1", "e2", "e2"],
        }
    )
    costs = {"A": 1, "B": 1, "C": 1}
    result = ortidy.set_cover(membership, costs, partition=True)
    assert result.status is SolveStatus.OPTIMAL
    chosen = set(as_pandas(result.frame).query("isSelected")["subset"])
    assert chosen == {"A", "B"}  # C would double-cover e2


def test_missing_cost_raises():
    membership = pd.DataFrame({"subset": ["A"], "element": ["e0"]})
    with pytest.raises(KeyError, match="A"):
        ortidy.set_cover(membership, {"B": 1})


def test_backend_parity():
    pdf = ortidy.set_cover(_membership("pandas"), _costs("pandas"))
    pol = ortidy.set_cover(_membership("polars"), _costs("polars"))
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective
