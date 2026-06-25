"""The ``.or_`` dataframe accessor — the headline "dataframe-native" UX.

Registers an ``or_`` namespace on the native frame the user holds so usage reads
idiomatically::

    df.or_.knapsack(capacity=100)
    items.or_.multi_knapsack(bins=bins)
    distances.or_.route(vehicles=fleet)

Standalone functions remain available; the accessor just forwards to them. Each
backend is registered only if it is importable, so neither pandas nor Polars is a
hard dependency.
"""

from __future__ import annotations

from typing import Any

from ortidy.result import SolveResult


class _OrAccessor:
    """Shared delegating methods; subclasses only supply ``self._df``."""

    _df: Any

    def knapsack(self, capacity: float, **kwargs: Any) -> SolveResult:
        from ortidy.binning.knapsack import knapsack

        return knapsack(self._df, capacity=capacity, **kwargs)

    def multi_knapsack(self, bins: Any, **kwargs: Any) -> SolveResult:
        from ortidy.binning.multi_knapsack import multi_knapsack

        return multi_knapsack(self._df, bins=bins, **kwargs)

    def bin_packing(self, capacity: float, **kwargs: Any) -> SolveResult:
        from ortidy.binning.bin_packing import bin_packing

        return bin_packing(self._df, capacity=capacity, **kwargs)

    def assignment(self, **kwargs: Any) -> SolveResult:
        from ortidy.assignment.assignment import assignment

        return assignment(self._df, **kwargs)

    def max_flow(self, source: Any, sink: Any, **kwargs: Any) -> SolveResult:
        from ortidy.flow.flow import max_flow

        return max_flow(self._df, source, sink, **kwargs)

    def min_cost_flow(self, supplies: Any, **kwargs: Any) -> SolveResult:
        from ortidy.flow.flow import min_cost_flow

        return min_cost_flow(self._df, supplies, **kwargs)

    def shortest_path(self, source: Any, sink: Any, **kwargs: Any) -> SolveResult:
        from ortidy.flow.flow import shortest_path

        return shortest_path(self._df, source, sink, **kwargs)

    def distance_matrix(self, **kwargs: Any) -> Any:
        from ortidy.routing.distance import distance_matrix

        return distance_matrix(self._df, **kwargs)

    def shift_scheduling(self, workers: Any, **kwargs: Any) -> SolveResult:
        from ortidy.scheduling.shift_scheduling import shift_scheduling

        return shift_scheduling(self._df, workers, **kwargs)

    def facility_location(self, setup_costs: Any, **kwargs: Any) -> SolveResult:
        from ortidy.facility.facility_location import facility_location

        return facility_location(self._df, setup_costs, **kwargs)

    def route(self, **kwargs: Any) -> SolveResult:
        from ortidy.routing.routing import solve_routing

        return solve_routing(self._df, **kwargs)


def register() -> None:
    """Register the ``or_`` accessor on every importable backend. Idempotent."""
    _register_pandas()
    _register_polars()


def _register_pandas() -> None:
    try:
        import pandas as pd
    except ImportError:
        return

    @pd.api.extensions.register_dataframe_accessor("or_")
    class _PandasOrAccessor(_OrAccessor):
        def __init__(self, pandas_obj: Any) -> None:
            self._df = pandas_obj


def _register_polars() -> None:
    try:
        import polars as pl
    except ImportError:
        return

    @pl.api.register_dataframe_namespace("or_")
    class _PolarsOrNamespace(_OrAccessor):
        def __init__(self, df: Any) -> None:
            self._df = df
