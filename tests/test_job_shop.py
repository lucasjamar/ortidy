"""Job-shop scheduling tests."""

from __future__ import annotations

import pandas as pd

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _tasks(backend: str):
    # 2 jobs, 2 machines. Optimal makespan is 7.
    df = pd.DataFrame(
        {
            "jobId": [0, 0, 1, 1],
            "step": [0, 1, 0, 1],
            "machine": ["m0", "m1", "m1", "m0"],
            "duration": [3, 2, 2, 4],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def test_valid_schedule_and_makespan(backend):
    result = ortidy.job_shop(_tasks(backend))
    assert result.status is SolveStatus.OPTIMAL
    assert result.objective == 7

    out = as_pandas(result.frame)
    assert {"start", "end"}.issubset(out.columns)
    # Durations honoured.
    assert (out["end"] - out["start"] == out["duration"]).all()
    # Precedence: within a job, later steps start after earlier ones end.
    for _, job in out.groupby("jobId"):
        job = job.sort_values("step")
        assert (job["start"].values[1:] >= job["end"].values[:-1]).all()
    # No machine runs two tasks at once.
    for _, machine in out.groupby("machine"):
        m = machine.sort_values("start")
        assert (m["start"].values[1:] >= m["end"].values[:-1]).all()
    # Makespan is the last end.
    assert out["end"].max() == result.objective


def test_backend_parity():
    pdf = ortidy.job_shop(_tasks("pandas"))
    pol = ortidy.job_shop(_tasks("polars"))
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective
