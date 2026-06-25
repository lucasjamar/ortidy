"""Distance-matrix helper tests."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from tests.conftest import as_pandas, native_type_name


def test_euclidean_matrix(backend):
    locs = pd.DataFrame({"x": [0, 3, 0], "y": [0, 0, 4]})
    if backend == "polars":
        import polars as pl

        locs = pl.from_pandas(locs)
    mat = as_pandas(ortidy.distance_matrix(locs, method="euclidean"))
    assert mat.shape == (3, 3)
    assert mat.iloc[0, 0] == 0
    assert mat.iloc[0, 1] == pytest.approx(3.0)  # (0,0)->(3,0)
    assert mat.iloc[1, 2] == pytest.approx(5.0)  # (3,0)->(0,4), 3-4-5 triangle


def test_haversine_matrix():
    # Paris ↔ London ≈ 343 km.
    locs = pd.DataFrame({"lat": [48.8566, 51.5074], "lon": [2.3522, -0.1278]})
    mat = as_pandas(ortidy.distance_matrix(locs, method="haversine"))
    assert mat.iloc[0, 1] == pytest.approx(343, abs=5)


def test_id_column_labels():
    locs = pd.DataFrame({"city": ["a", "b"], "x": [0, 1], "y": [0, 0]})
    mat = as_pandas(ortidy.distance_matrix(locs, id_column="city"))
    assert list(mat.columns) == ["a", "b"]


def test_backend_preserved():
    import polars as pl

    locs = pl.DataFrame({"x": [0.0, 1.0], "y": [0.0, 0.0]})
    mat = ortidy.distance_matrix(locs)
    assert native_type_name(mat) == "polars"


def test_unknown_method_raises():
    locs = pd.DataFrame({"x": [0], "y": [0]})
    with pytest.raises(ValueError, match="Unknown method"):
        ortidy.distance_matrix(locs, method="manhattan")
