"""Routing tests: correctness, feature-engineering, backend parity."""

from __future__ import annotations

import numpy as np
import pandas as pd

import ortidy
from ortidy import data
from tests.conftest import as_pandas, native_type_name

FEATURE_COLUMNS = {
    "vehicleId",
    "departure",
    "destination",
    "distance",
    "tripsSinceStart",
    "tripsTillEnd",
    "distanceSinceStart",
    "distanceTillEnd",
}


def _euclidean_matrix(backend: str = "pandas"):
    locs = as_pandas(data.locations())
    coords = locs[["x", "y"]].to_numpy()
    dist = np.round(np.sqrt(((coords[:, None] - coords[None, :]) ** 2).sum(-1))).astype(
        int
    )
    mat = pd.DataFrame(dist, columns=[str(i) for i in range(len(locs))])
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(mat)
    return mat


def test_single_vehicle_route_has_features(backend):
    res = ortidy.solve_routing(_euclidean_matrix(backend), vehicles=1)
    assert res.status.is_success
    assert res.objective > 0

    out = as_pandas(res.frame)
    assert FEATURE_COLUMNS.issubset(out.columns)
    # Route starts at the depot and the final stop has no onward destination.
    assert out["departure"].iloc[0] == "0"
    assert pd.isna(out["destination"].iloc[-1])
    # distanceSinceStart is non-decreasing along the route.
    assert out["distanceSinceStart"].is_monotonic_increasing


def test_multi_vehicle_routes(backend):
    res = ortidy.solve_routing(_euclidean_matrix(backend), vehicles=4)
    assert res.status.is_success
    out = as_pandas(res.frame)
    assert sorted(out["vehicleId"].unique().tolist()) == [0, 1, 2, 3]
    # Each vehicle's own route starts at the depot.
    for _, grp in out.groupby("vehicleId"):
        assert grp["departure"].iloc[0] == "0"


def test_capacitated_routing_with_demand():
    matrix = _euclidean_matrix("pandas")
    vehicles = pd.DataFrame({"vehicleId": [0, 1, 2, 3], "capacity": [15, 15, 15, 15]})
    res = ortidy.solve_routing(matrix, vehicles=vehicles, locations=data.locations())
    assert res.status.is_success
    out = as_pandas(res.frame)
    assert "load" in out.columns


def test_backend_parity():
    pd_res = ortidy.solve_routing(_euclidean_matrix("pandas"), vehicles=1)
    pol_res = ortidy.solve_routing(_euclidean_matrix("polars"), vehicles=1)
    assert native_type_name(pd_res.frame) == "pandas"
    assert native_type_name(pol_res.frame) == "polars"
    assert pd_res.objective == pol_res.objective
