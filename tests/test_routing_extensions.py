"""VRPTW and pickups-&-deliveries routing tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

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
