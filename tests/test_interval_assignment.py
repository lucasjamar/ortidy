"""interval_assignment tests — the four regimes on airline fixtures."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name

# 9 Dublin out-and-back blocks (dep, arr minutes); min_gap=25 → 3 resources.
_BLOCKS = [
    (385, 580),
    (400, 725),
    (420, 870),
    (615, 810),
    (835, 1090),
    (840, 1035),
    (900, 1305),
    (1065, 1260),
    (1120, 1290),
]
# 6 flights (start_loc, end_loc, start, end); min_gap=25 → 2 resources.
_FLIGHTS = [
    ("A", "B", 600, 700),
    ("B", "C", 730, 830),
    ("C", "A", 900, 1000),
    ("A", "C", 620, 750),
    ("C", "B", 800, 900),
    ("B", "A", 930, 1030),
]


def _blocks(backend: str):
    df = pd.DataFrame(
        {
            "taskId": [f"b{i}" for i in range(9)],
            "start": [b[0] for b in _BLOCKS],
            "end": [b[1] for b in _BLOCKS],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def _flights(backend: str):
    df = pd.DataFrame(
        {
            "taskId": [f"f{i}" for i in range(6)],
            "start_loc": [f[0] for f in _FLIGHTS],
            "end_loc": [f[1] for f in _FLIGHTS],
            "start": [f[2] for f in _FLIGHTS],
            "end": [f[3] for f in _FLIGHTS],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def _resources(backend: str, counts, costs):
    df = pd.DataFrame(
        {
            "resourceType": ["SR", "LR"],
            "count": counts,
            "fixed_cost": costs,
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


# --- Regime 1: single fleet, single base ---------------------------------- #


def test_regime1_three_resources(backend):
    result = ortidy.interval_assignment(_blocks(backend), min_gap=25)
    assert result.status is SolveStatus.OPTIMAL
    assert result.objective == 3

    out = as_pandas(result.frame)
    assert "resourceId" in out.columns
    assert sorted(out["resourceId"].unique()) == [0, 1, 2]  # dense
    # No two tasks on the same resource overlap within the gap.
    for _, grp in out.groupby("resourceId"):
        g = grp.sort_values("start")
        assert (g["start"].values[1:] >= g["end"].values[:-1] + 25).all()


# --- Regime 2: single fleet, no base (locations) -------------------------- #


def test_regime2_two_resources(backend):
    result = ortidy.interval_assignment(
        _flights(backend),
        start_location_column="start_loc",
        end_location_column="end_loc",
        min_gap=25,
    )
    assert result.status is SolveStatus.OPTIMAL
    assert result.objective == 2

    out = as_pandas(result.frame)
    # Consecutive tasks on a resource must connect by place and time.
    for _, grp in out.groupby("resourceId"):
        g = grp.sort_values("start").reset_index(drop=True)
        for k in range(len(g) - 1):
            assert g.loc[k, "end_loc"] == g.loc[k + 1, "start_loc"]
            assert g.loc[k, "end"] + 25 <= g.loc[k + 1, "start"]


# --- Regime 3: mixed fleet, single base ----------------------------------- #


def test_regime3_typed_eligibility(backend):
    resources = _resources(backend, [8, 2], [1, 3])
    elig = pd.DataFrame({"taskId": ["b2", "b6"], "resourceType": ["LR", "LR"]})
    if backend == "polars":
        import polars as pl

        elig = pl.from_pandas(elig)
    result = ortidy.interval_assignment(
        _blocks(backend), resources=resources, eligibility=elig, min_gap=25
    )
    assert result.status is SolveStatus.OPTIMAL
    assert result.objective == 5  # 1 LR (b2→b6) + 2 SR

    out = as_pandas(result.frame).set_index("taskId")
    assert out.loc["b2", "resourceType"] == "LR"
    assert out.loc["b6", "resourceType"] == "LR"


# --- Regime 4: mixed fleet, free network ---------------------------------- #


def test_regime4_typed_flow(backend):
    resources = _resources(backend, [3, 1], [1, 3])
    elig = pd.DataFrame({"taskId": ["f3"], "resourceType": ["LR"]})
    if backend == "polars":
        import polars as pl

        elig = pl.from_pandas(elig)
    result = ortidy.interval_assignment(
        _flights(backend),
        start_location_column="start_loc",
        end_location_column="end_loc",
        resources=resources,
        eligibility=elig,
        min_gap=25,
    )
    assert result.status is SolveStatus.OPTIMAL
    assert result.objective == 4  # one LR chain + one SR chain
    out = as_pandas(result.frame).set_index("taskId")
    assert out.loc["f3", "resourceType"] == "LR"


# --- edge cases ----------------------------------------------------------- #


def test_single_task():
    tasks = pd.DataFrame({"taskId": ["only"], "start": [0], "end": [10]})
    result = ortidy.interval_assignment(tasks)
    assert result.objective == 1
    assert as_pandas(result.frame)["resourceId"].tolist() == [0]


def test_min_gap_zero_back_to_back():
    # Two tasks that touch (end == start); min_gap=0 lets them share one resource.
    tasks = pd.DataFrame({"taskId": ["a", "b"], "start": [0, 10], "end": [10, 20]})
    result = ortidy.interval_assignment(tasks, min_gap=0)
    assert result.objective == 1


def test_count_cap_infeasible():
    resources = pd.DataFrame({"resourceType": ["SR"], "count": [2], "fixed_cost": [1]})
    result = ortidy.interval_assignment(
        _blocks("pandas"), resources=resources, min_gap=25
    )
    assert result.status is SolveStatus.INFEASIBLE
    assert result.objective is None


def test_custom_column_names():
    tasks = pd.DataFrame({"flight": ["x", "y"], "dep": [0, 5], "arr": [10, 15]})
    result = ortidy.interval_assignment(
        tasks, task_column="flight", start_column="dep", end_column="arr"
    )
    assert result.objective == 2  # they overlap → two resources


def test_determinism():
    a = ortidy.interval_assignment(_blocks("pandas"), min_gap=25)
    b = ortidy.interval_assignment(_blocks("pandas"), min_gap=25)
    assert (
        as_pandas(a.frame)["resourceId"].tolist()
        == as_pandas(b.frame)["resourceId"].tolist()
    )


def test_backend_parity():
    pdf = ortidy.interval_assignment(_blocks("pandas"), min_gap=25)
    pol = ortidy.interval_assignment(_blocks("polars"), min_gap=25)
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective


# --- validation ----------------------------------------------------------- #


def test_end_before_start_raises():
    tasks = pd.DataFrame({"taskId": ["a"], "start": [10], "end": [5]})
    with pytest.raises(ValueError, match="end > start"):
        ortidy.interval_assignment(tasks)


def test_negative_gap_raises():
    with pytest.raises(ValueError, match="min_gap"):
        ortidy.interval_assignment(_blocks("pandas"), min_gap=-1)


def test_one_location_column_raises():
    with pytest.raises(ValueError, match="set together"):
        ortidy.interval_assignment(
            _flights("pandas"), start_location_column="start_loc"
        )


def test_eligibility_without_resources_raises():
    elig = pd.DataFrame({"taskId": ["b0"], "resourceType": ["LR"]})
    with pytest.raises(ValueError, match="eligibility requires resources"):
        ortidy.interval_assignment(_blocks("pandas"), eligibility=elig, min_gap=25)


def test_eligibility_unknown_type_raises():
    resources = _resources("pandas", [8, 2], [1, 3])
    elig = pd.DataFrame({"taskId": ["b0"], "resourceType": ["JUMBO"]})
    with pytest.raises(KeyError, match="JUMBO"):
        ortidy.interval_assignment(
            _blocks("pandas"), resources=resources, eligibility=elig, min_gap=25
        )
