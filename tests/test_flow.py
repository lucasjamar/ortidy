"""Network-flow and shortest-path tests."""

from __future__ import annotations

import pandas as pd

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _maxflow_edges(backend: str):
    # Max-flow network (source=0, sink=4); max flow = 17 (source out-cap bound).
    df = pd.DataFrame(
        {
            "from": [0, 0, 0, 1, 1, 2, 2, 3, 3],
            "to": [1, 2, 3, 2, 4, 3, 4, 2, 4],
            "capacity": [5, 8, 5, 4, 6, 3, 4, 5, 10],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


def test_max_flow(backend):
    res = ortidy.max_flow(_maxflow_edges(backend), source=0, sink=4)
    assert res.status is SolveStatus.OPTIMAL
    assert res.objective == 17
    out = as_pandas(res.frame)
    assert "flow" in out.columns
    # Flow conservation at the source: out-flow equals the objective.
    assert out[out["from"] == 0]["flow"].sum() == 17
    # No arc carries more than its capacity.
    assert (out["flow"] <= out["capacity"]).all()


def test_max_flow_backend_parity():
    pdf = ortidy.max_flow(_maxflow_edges("pandas"), source=0, sink=4)
    pol = ortidy.max_flow(_maxflow_edges("polars"), source=0, sink=4)
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective


def test_min_cost_flow():
    edges = pd.DataFrame(
        {
            "from": [0, 0, 1, 2],
            "to": [1, 2, 2, 3],
            "capacity": [10, 10, 10, 10],
            "cost": [4, 1, 1, 1],
        }
    )
    supplies = pd.DataFrame({"node": [0, 3], "supply": [5, -5]})
    res = ortidy.min_cost_flow(edges, supplies)
    assert res.status is SolveStatus.OPTIMAL
    # Cheapest route 0→2→3 costs (1+1)*5 = 10.
    assert res.objective == 10
    assert "flow" in as_pandas(res.frame).columns


def test_shortest_path():
    edges = pd.DataFrame(
        {
            "from": [0, 0, 1, 2],
            "to": [1, 2, 3, 3],
            "weight": [1, 4, 1, 1],
        }
    )
    res = ortidy.shortest_path(edges, source=0, sink=3)
    assert res.status is SolveStatus.OPTIMAL
    assert res.objective == 2  # 0→1→3
    out = as_pandas(res.frame)
    on_path = out[out["onPath"] == 1]
    assert set(zip(on_path["from"], on_path["to"], strict=True)) == {(0, 1), (1, 3)}
