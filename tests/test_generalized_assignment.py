"""Generalized assignment problem (GAP) tests (long edge-list form)."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _edges(backend: str):
    df = pd.DataFrame(
        {
            "task": ["t0", "t0", "t1", "t1", "t2", "t2"],
            "agent": ["a0", "a1", "a0", "a1", "a0", "a1"],
            "value": [10, 6, 8, 9, 5, 7],
            "size": [3, 2, 4, 3, 2, 4],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def test_maximizes_value_within_capacity(backend):
    result = ortidy.generalized_assignment(_edges(backend), {"a0": 5, "a1": 6})
    assert result.status is SolveStatus.OPTIMAL
    assert result.objective == 24  # t0->a0(10), t1->a1(9), t2->a0(5)

    out = as_pandas(result.frame)
    chosen = out[out["selected"]]
    # Each task assigned at most once.
    assert chosen.groupby("task").size().le(1).all()
    # Per-agent consumed size within capacity.
    used = chosen.groupby("agent")["size"].sum()
    assert used.get("a0", 0) <= 5 and used.get("a1", 0) <= 6


def test_capacities_as_frame():
    caps = pd.DataFrame({"agent": ["a0", "a1"], "cap": [5, 6]})
    assert ortidy.generalized_assignment(_edges("pandas"), caps).objective == 24


def test_sparse_tasks_can_go_unassigned():
    # t1 only reachable by a0, whose capacity is exhausted by t0.
    edges = pd.DataFrame(
        {
            "task": ["t0", "t1"],
            "agent": ["a0", "a0"],
            "value": [10, 10],
            "size": [4, 4],
        }
    )
    result = ortidy.generalized_assignment(edges, {"a0": 5})
    assert result.status.is_success
    assert as_pandas(result.frame)["selected"].sum() == 1


def test_require_all_infeasible():
    edges = pd.DataFrame(
        {
            "task": ["t0", "t1"],
            "agent": ["a0", "a0"],
            "value": [10, 10],
            "size": [4, 4],
        }
    )
    result = ortidy.generalized_assignment(edges, {"a0": 5}, require_all=True)
    assert result.status is SolveStatus.INFEASIBLE


def test_missing_capacity_raises():
    edges = pd.DataFrame(
        {
            "task": ["t0"],
            "agent": ["a1"],
            "value": [1],
            "size": [1],
        }
    )
    with pytest.raises(KeyError, match="a1"):
        ortidy.generalized_assignment(edges, {"a0": 5})


def test_backend_parity():
    pdf = ortidy.generalized_assignment(_edges("pandas"), {"a0": 5, "a1": 6})
    pol = ortidy.generalized_assignment(_edges("polars"), {"a0": 5, "a1": 6})
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective
