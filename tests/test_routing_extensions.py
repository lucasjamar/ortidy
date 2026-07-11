"""VRPTW and pickups-&-deliveries routing tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import ortidy
from ortidy import data
from ortidy.result import SolveStatus
from tests.conftest import as_pandas


def _euclidean_matrix():
    locs = as_pandas(data.locations())
    coords = locs[["x", "y"]].to_numpy()
    dist = np.round(np.sqrt(((coords[:, None] - coords[None, :]) ** 2).sum(-1))).astype(
        int
    )
    return pd.DataFrame(dist, columns=[str(i) for i in range(len(locs))])


def _line_matrix():
    # 5 stops on a line; stop 4 sits far away so it's expensive to visit.
    coords = np.array([[0, 0], [1, 0], [2, 0], [3, 0], [100, 0]])
    d = np.round(np.sqrt(((coords[:, None] - coords[None, :]) ** 2).sum(-1))).astype(
        int
    )
    return pd.DataFrame(d, columns=[str(i) for i in range(5)])


def test_penalties_drop_expensive_visit():
    matrix = _line_matrix()
    base = ortidy.solve_routing(matrix, vehicles=1)
    assert base.metadata["dropped"] == []  # all visited without penalties

    penalties = pd.DataFrame({"node": [4], "penalty": [10]})
    result = ortidy.solve_routing(matrix, vehicles=1, penalties=penalties)
    assert result.status.is_success
    assert "4" in result.metadata["dropped"]  # cheaper to drop than detour
    assert result.objective < base.objective


def test_vehicle_fixed_cost_reduces_fleet():
    matrix = _line_matrix()
    result = ortidy.solve_routing(matrix, vehicles=3, vehicle_fixed_cost=10_000)
    out = as_pandas(result.frame)
    used = (out.groupby("vehicleId")["distance"].sum() > 0).sum()
    assert used == 1  # fixed cost makes the solver use a single vehicle
    assert result.metadata["vehicles_used"] == 1


def test_node_names_in_time_windows():
    # Name the matrix columns non-positionally and reference nodes by name.
    matrix = _line_matrix().rename(columns={str(i): f"s{i}" for i in range(5)})
    windows = pd.DataFrame(
        {
            "node": ["s0", "s1", "s2", "s3", "s4"],
            "open": [0] * 5,
            "close": [10_000] * 5,
        }
    )
    result = ortidy.solve_routing(
        matrix, vehicles=1, starting_point="s0", time_windows=windows
    )
    assert result.status.is_success


def test_unknown_node_name_raises():
    matrix = _line_matrix().rename(columns={str(i): f"s{i}" for i in range(5)})
    windows = pd.DataFrame({"node": ["nope"], "open": [0], "close": [1]})
    with pytest.raises(KeyError, match="nope"):
        ortidy.solve_routing(
            matrix, vehicles=1, starting_point="s0", time_windows=windows
        )


def test_isreturn_marks_terminal_leg(backend):
    matrix = _euclidean_matrix()
    if backend == "polars":
        import polars as pl

        matrix = pl.from_pandas(matrix)
    result = ortidy.solve_routing(matrix, vehicles=3)
    out = as_pandas(result.frame)
    assert "isReturn" in out.columns
    # Exactly one terminal (return) row per vehicle, with a null destination.
    assert out.groupby("vehicleId")["isReturn"].sum().eq(1).all()
    assert out[out["isReturn"]]["destination"].isna().all()


def test_span_cost_override_still_works():
    # Explicitly passing a span coefficient with fleet sizing is honored (no crash).
    matrix = _line_matrix()
    result = ortidy.solve_routing(
        matrix, vehicles=3, vehicle_fixed_cost=10_000, span_cost_coefficient=50
    )
    assert result.status.is_success


def test_pickups_and_deliveries_same_vehicle_and_order():
    matrix = _euclidean_matrix()
    pd_pairs = data.pickups_and_deliveries()
    res = ortidy.solve_routing(
        matrix, vehicles=4, pickups_deliveries=pd_pairs, max_distance=100_000
    )
    assert res.status.is_success
    out = as_pandas(res.frame)

    # Build per-node (vehicle, visit-position) lookup.
    pos = {}
    for vehicle_id, grp in out.groupby("vehicleId"):
        for order, node in enumerate(grp["departure"].tolist()):
            pos[(vehicle_id, node)] = order
    node_vehicle = {row["departure"]: row["vehicleId"] for _, row in out.iterrows()}

    for _, pair in pd_pairs.iterrows():
        p, d = str(pair["pickup"]), str(pair["delivery"])
        # Same vehicle serves both, and the pickup precedes the delivery.
        assert node_vehicle[p] == node_vehicle[d]
        v = node_vehicle[p]
        assert pos[(v, p)] < pos[(v, d)]


def test_time_windows_feasible():
    # 4 nodes in a line; generous windows → feasible single-vehicle tour.
    matrix = pd.DataFrame(
        [[0, 10, 20, 30], [10, 0, 10, 20], [20, 10, 0, 10], [30, 20, 10, 0]],
        columns=["0", "1", "2", "3"],
    )
    windows = pd.DataFrame(
        {"node": [0, 1, 2, 3], "open": [0, 0, 0, 0], "close": [100, 100, 100, 100]}
    )
    res = ortidy.solve_routing(matrix, vehicles=1, time_windows=windows)
    assert res.status.is_success


def test_time_windows_infeasible():
    # Node 3 must be reached by t=5, but the nearest approach costs ≥10 → infeasible.
    matrix = pd.DataFrame(
        [[0, 10, 20, 30], [10, 0, 10, 20], [20, 10, 0, 10], [30, 20, 10, 0]],
        columns=["0", "1", "2", "3"],
    )
    windows = pd.DataFrame(
        {"node": [0, 1, 2, 3], "open": [0, 0, 0, 0], "close": [100, 100, 100, 5]}
    )
    res = ortidy.solve_routing(matrix, vehicles=1, time_windows=windows)
    assert res.status is SolveStatus.INFEASIBLE
    assert res.frame is None
