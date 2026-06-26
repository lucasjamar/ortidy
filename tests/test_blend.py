"""Diet / blending LP tests."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _items(backend: str):
    df = pd.DataFrame(
        {
            "food": ["bread", "milk", "cheese"],
            "cost": [1.0, 2.0, 3.0],
            "protein": [4.0, 8.0, 7.0],
            "calories": [90.0, 120.0, 100.0],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def _reqs(backend: str):
    df = pd.DataFrame({"attribute": ["protein", "calories"], "min": [10.0, 150.0]})
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def test_meets_requirements_at_min_cost(backend):
    result = ortidy.blend(_items(backend), _reqs(backend))
    assert result.status is SolveStatus.OPTIMAL

    out = as_pandas(result.frame)
    assert "quantity" in out.columns
    assert (out["quantity"] >= -1e-9).all()  # non-negative
    # Each requirement is met.
    assert (out["protein"] * out["quantity"]).sum() >= 10 - 1e-6
    assert (out["calories"] * out["quantity"]).sum() >= 150 - 1e-6
    # Objective equals total cost.
    assert result.objective == pytest.approx((out["cost"] * out["quantity"]).sum())


def test_max_bound():
    items = _items("pandas")
    reqs = pd.DataFrame(
        {
            "attribute": ["protein", "calories"],
            "min": [10.0, 150.0],
            "max": [None, 200.0],
        }
    )
    result = ortidy.blend(items, reqs)
    assert result.status is SolveStatus.OPTIMAL
    out = as_pandas(result.frame)
    assert (out["calories"] * out["quantity"]).sum() <= 200 + 1e-6


def test_infeasible_when_bounds_conflict():
    items = _items("pandas")
    reqs = pd.DataFrame({"attribute": ["protein"], "min": [10.0], "max": [5.0]})
    result = ortidy.blend(items, reqs)
    assert result.status is SolveStatus.INFEASIBLE


def test_backend_parity():
    pdf = ortidy.blend(_items("pandas"), _reqs("pandas"))
    pol = ortidy.blend(_items("polars"), _reqs("polars"))
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pytest.approx(pol.objective)
