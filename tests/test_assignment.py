"""Linear assignment tests."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _cost_matrix(backend: str):
    # 3×3 assignment; optimal min-cost matching is 0→t1, 1→t0, 2→t2 = 4.
    data = {"t0": [4, 1, 3], "t1": [2, 5, 2], "t2": [8, 4, 1]}
    df = pd.DataFrame(data)
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def test_minimizes_total_cost(backend):
    res = ortidy.assignment(_cost_matrix(backend))
    assert res.status is SolveStatus.OPTIMAL
    assert res.objective == 4
    out = as_pandas(res.frame)
    assert list(out["assignedTo"]) == ["t1", "t0", "t2"]
    assert out["cost"].sum() == 4


def test_maximize(backend):
    res = ortidy.assignment(_cost_matrix(backend), maximize=True)
    assert res.status is SolveStatus.OPTIMAL
    # Max-value matching: 0→t2(8), 1→t1(5), 2→? remaining t0(3) = 16.
    assert res.objective == 16


def test_backend_parity():
    pd_res = ortidy.assignment(_cost_matrix("pandas"))
    pol_res = ortidy.assignment(_cost_matrix("polars"))
    assert native_type_name(pd_res.frame) == "pandas"
    assert native_type_name(pol_res.frame) == "polars"
    assert pd_res.objective == pol_res.objective


def test_more_agents_than_tasks_raises():
    df = pd.DataFrame({"t0": [1, 2, 3]})  # 3 agents, 1 task
    with pytest.raises(ValueError, match="at least as many tasks"):
        ortidy.assignment(df)


def test_id_column_excluded_from_tasks(backend):
    df = pd.DataFrame({"agent": ["a", "b"], "t0": [1, 9], "t1": [9, 1]})
    res = ortidy.assignment(df, id_column="agent")
    assert res.status is SolveStatus.OPTIMAL
    out = as_pandas(res.frame)
    assert list(out["assignedTo"]) == ["t0", "t1"]
    assert "agent" in out.columns
