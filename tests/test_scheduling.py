"""Shift-scheduling tests (interval-schedule shape)."""

from __future__ import annotations

import pandas as pd

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _requirements(backend: str):
    # 3 days × 2 shifts, each needing 1 worker.
    df = pd.DataFrame(
        {
            "day": [0, 0, 1, 1, 2, 2],
            "shift": ["am", "pm", "am", "pm", "am", "pm"],
            "required": [1, 1, 1, 1, 1, 1],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def _workers(backend: str):
    df = pd.DataFrame({"workerId": ["alice", "bob", "carol"]})
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def test_coverage_and_one_shift_per_day(backend):
    res = ortidy.shift_scheduling(_requirements(backend), _workers(backend))
    assert res.status.is_success
    out = as_pandas(res.frame)

    # Total assignments equals total required (6 slots × 1).
    assert len(out) == 6
    # No worker works two shifts on the same day.
    assert not out.duplicated(subset=["workerId", "day"]).any()
    # Every (day, shift) is covered exactly once.
    assert out.duplicated(subset=["day", "shift"]).sum() == 0


def test_fairness_objective_balances_load(backend):
    res = ortidy.shift_scheduling(_requirements(backend), _workers(backend))
    out = as_pandas(res.frame)
    counts = out["workerId"].value_counts()
    # 6 shifts over 3 workers, balanced → peak load of 2.
    assert counts.max() == 2
    assert res.objective == 2


def test_backend_parity():
    pd_res = ortidy.shift_scheduling(_requirements("pandas"), _workers("pandas"))
    pol_res = ortidy.shift_scheduling(_requirements("polars"), _workers("polars"))
    assert native_type_name(pd_res.frame) == "pandas"
    assert native_type_name(pol_res.frame) == "polars"
    assert pd_res.objective == pol_res.objective


def test_infeasible_when_not_enough_workers():
    # Two shifts on the same day both need a worker, but only one worker exists →
    # cannot staff both without violating one-shift-per-day.
    req = pd.DataFrame({"day": [0, 0], "shift": ["am", "pm"], "required": [1, 1]})
    workers = pd.DataFrame({"workerId": ["solo"]})
    res = ortidy.shift_scheduling(req, workers)
    assert res.status is SolveStatus.INFEASIBLE
