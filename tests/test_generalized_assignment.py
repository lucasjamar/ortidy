"""Generalized assignment problem (GAP) tests."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _problem(backend: str):
    values = pd.DataFrame({"a0": [10, 8, 5], "a1": [6, 9, 7]})
    sizes = pd.DataFrame({"a0": [3, 4, 2], "a1": [2, 3, 4]})
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(values), pl.from_pandas(sizes)
    return values, sizes


def test_maximizes_value_within_capacity(backend):
    values, sizes = _problem(backend)
    result = ortidy.generalized_assignment(values, sizes, {"a0": 5, "a1": 6})
    assert result.status is SolveStatus.OPTIMAL
    assert result.objective == 24  # t0->a0(10), t1->a1(9), t2->a0(5)

    out = as_pandas(result.frame)
    assert list(out["assignedTo"]) == ["a0", "a1", "a0"]
    # Per-agent consumed size never exceeds capacity.
    sizes_pd = as_pandas(sizes)
    used = {"a0": 0, "a1": 0}
    for t, agent in enumerate(out["assignedTo"]):
        used[agent] += sizes_pd.loc[t, agent]
    assert used["a0"] <= 5 and used["a1"] <= 6


def test_capacities_as_sequence(backend):
    values, sizes = _problem(backend)
    result = ortidy.generalized_assignment(values, sizes, [5, 6])
    assert result.objective == 24


def test_tight_capacity_leaves_tasks_unassigned():
    values = pd.DataFrame({"a0": [10, 10]})
    sizes = pd.DataFrame({"a0": [4, 4]})
    result = ortidy.generalized_assignment(values, sizes, {"a0": 5})  # only one fits
    assert result.status.is_success
    out = as_pandas(result.frame)
    assert out["assignedTo"].notna().sum() == 1


def test_require_all_infeasible_when_capacity_too_small():
    values = pd.DataFrame({"a0": [10, 10]})
    sizes = pd.DataFrame({"a0": [4, 4]})
    result = ortidy.generalized_assignment(values, sizes, {"a0": 5}, require_all=True)
    assert result.status is SolveStatus.INFEASIBLE


def test_missing_capacity_raises():
    values = pd.DataFrame({"a0": [1], "a1": [1]})
    sizes = pd.DataFrame({"a0": [1], "a1": [1]})
    with pytest.raises(KeyError, match="a1"):
        ortidy.generalized_assignment(values, sizes, {"a0": 5})


def test_backend_parity():
    vp, sp = _problem("pandas")
    vl, sl = _problem("polars")
    pdf = ortidy.generalized_assignment(vp, sp, {"a0": 5, "a1": 6})
    pol = ortidy.generalized_assignment(vl, sl, {"a0": 5, "a1": 6})
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective
