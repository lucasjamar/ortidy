"""Shared test fixtures and helpers.

Tests run against every supported backend so the Narwhals promise — pandas in →
pandas out, Polars in → Polars out, equivalent results — is verified directly.
"""

from __future__ import annotations

from typing import Any

import narwhals.stable.v1 as nw
import pytest

BACKENDS = ["pandas", "polars"]


@pytest.fixture(params=BACKENDS)
def backend(request: pytest.FixtureRequest) -> str:
    """Parametrized backend name: each test runs once per backend."""
    return request.param


def as_pandas(frame: Any):
    """Convert any native result frame to pandas for backend-agnostic assertions."""
    return nw.from_native(frame, eager_only=True).to_pandas()


def native_type_name(frame: Any) -> str:
    return type(frame).__module__.split(".")[0]
