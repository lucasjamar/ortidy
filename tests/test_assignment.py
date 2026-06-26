"""Linear assignment tests (long edge-list form)."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _edges(backend: str):
    # Long form of a 3x3 cost matrix; optimal min-cost matching is 4.
    df = pd.DataFrame(
        {
            "agent": ["a0", "a0", "a0", "a1", "a1", "a1", "a2", "a2", "a2"],
            "task": ["t0", "t1", "t2", "t0", "t1", "t2", "t0", "t1", "t2"],
            "cost": [4, 2, 8, 1, 5, 4, 3, 2, 1],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def test_minimizes_total_cost(backend):
    result = ortidy.assignment(_edges(backend))
    assert result.status is SolveStatus.OPTIMAL
    assert result.objective == 4

    out = as_pandas(result.frame)
    chosen = out[out["selected"]]
    assert set(zip(chosen["agent"], chosen["task"], strict=False)) == {
        ("a0", "t1"),
        ("a1", "t0"),
        ("a2", "t2"),
    }
    # Each agent is assigned exactly one task.
    assert chosen.groupby("agent").size().eq(1).all()
    assert chosen["cost"].sum() == 4


def test_maximize():
    result = ortidy.assignment(_edges("pandas"), maximize=True)
    assert result.objective == 16


def test_sparse_problem():
    # a2 can only do t2 — still a feasible perfect matching.
    edges = pd.DataFrame(
        {
            "agent": ["a0", "a0", "a1", "a1", "a2"],
            "task": ["t0", "t1", "t0", "t1", "t2"],
            "cost": [4, 2, 1, 5, 3],
        }
    )
    result = ortidy.assignment(edges)
    assert result.status is SolveStatus.OPTIMAL
    out = as_pandas(result.frame)
    chosen = out[out["selected"]]
    assert ("a2", "t2") in set(zip(chosen["agent"], chosen["task"], strict=False))


def test_infeasible_when_no_perfect_matching():
    # Two agents both only able to take the same single task.
    edges = pd.DataFrame({"agent": ["a0", "a1"], "task": ["t0", "t0"], "cost": [1, 1]})
    result = ortidy.assignment(edges)
    assert result.status is SolveStatus.INFEASIBLE


def test_custom_column_names():
    edges = pd.DataFrame({"worker": ["w"], "job": ["j"], "price": [5]})
    result = ortidy.assignment(edges, left="worker", right="job", value="price")
    assert result.status is SolveStatus.OPTIMAL
    assert as_pandas(result.frame)["selected"].sum() == 1


def test_missing_column_raises():
    edges = pd.DataFrame({"agent": ["a"], "task": ["t"]})  # no cost
    with pytest.raises(KeyError, match="cost"):
        ortidy.assignment(edges)


def _team_edges():
    # 4 cheap workers in team A, 4 expensive in team B, 4 tasks.
    rows = []
    for w in ["a0", "a1", "a2", "a3"]:
        for t in ["t0", "t1", "t2", "t3"]:
            rows.append({"agent": w, "task": t, "cost": 1})
    for w in ["b0", "b1", "b2", "b3"]:
        for t in ["t0", "t1", "t2", "t3"]:
            rows.append({"agent": w, "task": t, "cost": 9})
    return pd.DataFrame(rows)


def test_teams_cap_limits_agents_per_team(backend):
    edges = _team_edges()
    if backend == "polars":
        import polars as pl

        edges = pl.from_pandas(edges)
    teams = {f"a{i}": "A" for i in range(4)} | {f"b{i}": "B" for i in range(4)}
    result = ortidy.assignment(edges, teams=teams, team_capacity=2)
    assert result.status.is_success

    out = as_pandas(result.frame)
    chosen = out[out["selected"]]
    used_per_team = chosen["agent"].map(teams).value_counts().to_dict()
    assert used_per_team.get("A", 0) <= 2
    assert used_per_team.get("B", 0) <= 2


def test_allowed_groups_restricts_active_set():
    # Group G = {w0, w1}; the only allowed pattern has w0 active, w1 inactive.
    edges = pd.DataFrame(
        {
            "agent": ["w0", "w0", "w1", "w1", "w2", "w2"],
            "task": ["t0", "t1", "t0", "t1", "t0", "t1"],
            "cost": [1, 1, 1, 1, 5, 5],
        }
    )
    allowed = pd.DataFrame(
        {
            "group": ["G", "G"],
            "pattern": ["p0", "p0"],
            "agent": ["w0", "w1"],
            "active": [1, 0],
        }
    )
    result = ortidy.assignment(edges, allowed_groups=allowed)
    assert result.status.is_success
    active = set(as_pandas(result.frame).query("selected")["agent"])
    assert "w1" not in active  # forbidden by the only allowed pattern


def test_allowed_groups_either_or():
    edges = pd.DataFrame(
        {
            "agent": ["w0", "w0", "w1", "w1", "w2", "w2"],
            "task": ["t0", "t1", "t0", "t1", "t0", "t1"],
            "cost": [1, 1, 1, 1, 5, 5],
        }
    )
    allowed = pd.DataFrame(
        {
            "group": ["G", "G", "G", "G"],
            "pattern": ["p0", "p0", "p1", "p1"],
            "agent": ["w0", "w1", "w0", "w1"],
            "active": [1, 0, 0, 1],
        }
    )
    result = ortidy.assignment(edges, allowed_groups=allowed)
    active = set(as_pandas(result.frame).query("selected")["agent"])
    assert not ({"w0", "w1"} <= active)  # at most one of w0/w1 active


def test_backend_parity():
    pdf = ortidy.assignment(_edges("pandas"))
    pol = ortidy.assignment(_edges("polars"))
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective
