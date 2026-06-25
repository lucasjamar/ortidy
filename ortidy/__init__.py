"""ortidy — operations research on tidy dataframes.

A backend-agnostic (Narwhals) dataframe façade over Google OR-Tools. Solvers
accept native frames (pandas, Polars, …), return the same backend, and hand back
a :class:`~ortidy.result.SolveResult` carrying the result frame, a status enum,
the objective, and solve metadata.
"""

from __future__ import annotations

from ortidy import accessor, data
from ortidy.assignment.assignment import assignment
from ortidy.binning.bin_packing import bin_packing
from ortidy.binning.knapsack import knapsack
from ortidy.binning.multi_knapsack import multi_knapsack
from ortidy.flow.flow import max_flow, min_cost_flow, shortest_path
from ortidy.result import SolveResult, SolveStatus
from ortidy.routing.distance import distance_matrix
from ortidy.routing.routing import solve_routing

__version__ = "0.2.0"

# Register the ``.or_`` accessor on every importable backend.
accessor.register()

__all__ = [
    "knapsack",
    "multi_knapsack",
    "bin_packing",
    "assignment",
    "max_flow",
    "min_cost_flow",
    "shortest_path",
    "solve_routing",
    "distance_matrix",
    "data",
    "SolveResult",
    "SolveStatus",
    "__version__",
]
