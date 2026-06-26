"""Transportation problem tests (long edge-list form)."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _edges(backend: str):
    df = pd.DataFrame(
        {
            "source": ["S0", "S0", "S0", "S1", "S1", "S1"],
            "sink": ["k0", "k1", "k2", "k0", "k1", "k2"],
            "cost": [4, 3, 1, 5, 2, 3],
        }
    )
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


SUPPLY = {"S0": 10, "S1": 15}
DEMAND = {"k0": 8, "k1": 9, "k2": 8}


def test_ships_all_supply_at_min_cost(backend):
    result = ortidy.transportation(_edges(backend), SUPPLY, DEMAND)
    assert result.status is SolveStatus.OPTIMAL
    out = as_pandas(result.frame)

    assert out["quantity"].sum() == sum(SUPPLY.values())
    assert out.groupby("source")["quantity"].sum().to_dict() == SUPPLY
    assert out.groupby("sink")["quantity"].sum().to_dict() == DEMAND
    assert result.objective == (out["cost"] * out["quantity"]).sum()


def test_supply_demand_as_frames():
    supply = pd.DataFrame({"source": ["S0", "S1"], "qty": [10, 15]})
    demand = pd.DataFrame({"sink": ["k0", "k1", "k2"], "qty": [8, 9, 8]})
    result = ortidy.transportation(_edges("pandas"), supply, demand)
    assert result.status is SolveStatus.OPTIMAL


def test_sparse_lanes():
    # S1 cannot reach k2 (lane omitted); still feasible.
    edges = pd.DataFrame(
        {
            "source": ["S0", "S0", "S0", "S1", "S1"],
            "sink": ["k0", "k1", "k2", "k0", "k1"],
            "cost": [4, 3, 1, 5, 2],
        }
    )
    result = ortidy.transportation(edges, SUPPLY, DEMAND)
    assert result.status.is_success
    out = as_pandas(result.frame)
    assert out["quantity"].sum() == 25


def test_unbalanced_raises():
    with pytest.raises(ValueError, match="unbalanced"):
        ortidy.transportation(_edges("pandas"), SUPPLY, {"k0": 8, "k1": 9, "k2": 1})


def test_backend_parity():
    pdf = ortidy.transportation(_edges("pandas"), SUPPLY, DEMAND)
    pol = ortidy.transportation(_edges("polars"), SUPPLY, DEMAND)
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective
