"""Bundled sample datasets for examples, docs, and golden-file tests.

Each loader returns a native dataframe in the requested ``backend`` (``"pandas"``
by default, ``"polars"`` also supported), so the same fixtures drive the
backend-parity tests.
"""

from __future__ import annotations

import os
from typing import Any

_DATA_DIR = os.path.dirname(__file__)


def bins(backend: str = "pandas") -> Any:
    return _get_dataset("binning/bins", backend)


def items_knapsack(backend: str = "pandas") -> Any:
    return _get_dataset("binning/items_knapsack", backend)


def items_multi(backend: str = "pandas") -> Any:
    return _get_dataset("binning/items_multi", backend)


def items_bin_packing(backend: str = "pandas") -> Any:
    return _get_dataset("binning/items_bin_packing", backend)


def locations(backend: str = "pandas") -> Any:
    return _get_dataset("routing/locations", backend)


def vehicles(with_capacity: bool = True, backend: str = "pandas") -> Any:
    data = _get_dataset("routing/vehicles", "pandas")
    if not with_capacity:
        data = data.drop(columns=["capacity"])
    return _to_backend(data, backend)


def pickups_and_deliveries(backend: str = "pandas") -> Any:
    return _get_dataset("routing/pickups_and_deliveries", backend)


def _get_dataset(name: str, backend: str) -> Any:
    import pandas as pd

    df = pd.read_csv(os.path.join(_DATA_DIR, f"{name}.csv"))
    return _to_backend(df, backend)


def _to_backend(df: Any, backend: str) -> Any:
    if backend == "pandas":
        return df
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    raise ValueError(f"Unknown backend {backend!r}; expected 'pandas' or 'polars'.")
