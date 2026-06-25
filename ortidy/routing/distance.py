"""Build a distance matrix from locations.

Separates distance-matrix construction from routing, so the routing API can take
the *locations* users actually have (x/y or lat/long) rather than a precomputed
matrix. Returns a square matrix as a dataframe in the same backend.
"""

from __future__ import annotations

import math
from typing import Any

import narwhals.stable.v1 as nw

from ortidy import _narwhals as _nw

EARTH_RADIUS_KM = 6371.0088


def distance_matrix(
    locations: Any,
    *,
    method: str = "euclidean",
    x: str = "x",
    y: str = "y",
    lat: str = "lat",
    lon: str = "lon",
    id_column: str | None = None,
) -> Any:
    """Build an N×N distance matrix from a locations frame.

    Parameters:
        locations: Frame of locations.
        method: ``"euclidean"`` (uses ``x``/``y``) or ``"haversine"`` (uses
            ``lat``/``lon``, great-circle distance in kilometres).
        x, y: Coordinate columns for the euclidean method.
        lat, lon: Coordinate columns for the haversine method.
        id_column: Optional column whose values label the matrix rows/columns.
            Defaults to positional labels ``"0"…"N-1"``.

    Returns:
        A square distance matrix as a native frame (same backend as ``locations``),
        with one column per location labelled by ``id_column`` (or position).
    """
    frame = _nw.to_nw(locations)
    impl = frame.implementation

    if method == "euclidean":
        coords = list(
            zip(_nw.column_to_list(frame, x), _nw.column_to_list(frame, y), strict=True)
        )
        dist_fn = _euclidean
    elif method == "haversine":
        coords = list(
            zip(
                _nw.column_to_list(frame, lat),
                _nw.column_to_list(frame, lon),
                strict=True,
            )
        )
        dist_fn = _haversine
    else:
        raise ValueError(
            f"Unknown method {method!r}; expected 'euclidean' or 'haversine'."
        )

    if id_column is not None:
        labels = [str(v) for v in _nw.column_to_list(frame, id_column)]
    else:
        labels = [str(i) for i in range(len(coords))]

    matrix = {
        labels[j]: [dist_fn(coords[i], coords[j]) for i in range(len(coords))]
        for j in range(len(coords))
    }
    return _nw.to_native(nw.from_dict(matrix, backend=impl))


def _euclidean(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))
