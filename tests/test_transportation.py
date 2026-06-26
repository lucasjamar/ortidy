"""Transportation problem tests."""

from __future__ import annotations

import pandas as pd
import pytest

import ortidy
from ortidy.result import SolveStatus
from tests.conftest import as_pandas, native_type_name


def _costs(backend: str):
    df = pd.DataFrame({"src": ["S0", "S1"], "k0": [4, 5], "k1": [3, 2], "k2": [1, 3]})
    if backend == "polars":
        import polars as pl

        return pl.from_pandas(df)
    return df


SUPPLY = {"S0": 10, "S1": 15}
DEMAND = {"k0": 8, "k1": 9, "k2": 8}


def test_ships_all_supply_at_min_cost(backend):
    result = ortidy.transportation(
        _costs(backend), SUPPLY, DEMAND, source_id_column="src"
    )
    assert result.status is SolveStatus.OPTIMAL
    out = as_pandas(result.frame)

    # Conservation: total shipped equals total supply (== total demand).
    assert out["quantity"].sum() == sum(SUPPLY.values())
    # Each source ships exactly its supply; each sink receives its demand.
    assert out.groupby("source")["quantity"].sum().to_dict() == SUPPLY
    assert out.groupby("sink")["quantity"].sum().to_dict() == DEMAND
    # Objective equals sum(cost * quantity) over the edges.
    assert result.objective == (out["cost"] * out["quantity"]).sum()


def test_unbalanced_raises():
    with pytest.raises(ValueError, match="unbalanced"):
        ortidy.transportation(
            _costs("pandas"),
            {"S0": 10, "S1": 15},
            {"k0": 8, "k1": 9, "k2": 1},
            source_id_column="src",
        )


def test_supply_demand_as_sequences():
    result = ortidy.transportation(
        _costs("pandas"), [10, 15], [8, 9, 8], source_id_column="src"
    )
    assert result.status is SolveStatus.OPTIMAL


def test_backend_parity():
    pdf = ortidy.transportation(
        _costs("pandas"), SUPPLY, DEMAND, source_id_column="src"
    )
    pol = ortidy.transportation(
        _costs("polars"), SUPPLY, DEMAND, source_id_column="src"
    )
    assert native_type_name(pdf.frame) == "pandas"
    assert native_type_name(pol.frame) == "polars"
    assert pdf.objective == pol.objective
