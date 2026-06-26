"""ortidy — operations research on tidy dataframes.

A backend-agnostic (Narwhals) dataframe façade over Google OR-Tools. Solvers
accept native frames (pandas, Polars, …), return the same backend, and hand back
a :class:`~ortidy.result.SolveResult` carrying the result frame, a status enum,
the objective, and solve metadata.
"""

from __future__ import annotations

from ortidy import data
from ortidy.assignment.assignment import assignment
from ortidy.assignment.generalized_assignment import generalized_assignment
from ortidy.binning.bin_packing import bin_packing
from ortidy.binning.knapsack import knapsack
from ortidy.binning.multi_knapsack import multi_knapsack
from ortidy.covering.set_cover import set_cover
from ortidy.facility.facility_location import facility_location
from ortidy.flow.flow import max_flow, min_cost_flow, shortest_path
from ortidy.result import SolveResult, SolveStatus
from ortidy.routing.distance import distance_matrix
from ortidy.routing.routing import solve_routing
from ortidy.scheduling.job_shop import job_shop
from ortidy.scheduling.shift_scheduling import shift_scheduling
from ortidy.transportation.transportation import transportation

__version__ = "0.3.0"

__all__ = [
    "knapsack",
    "multi_knapsack",
    "bin_packing",
    "assignment",
    "generalized_assignment",
    "transportation",
    "max_flow",
    "min_cost_flow",
    "shortest_path",
    "solve_routing",
    "distance_matrix",
    "shift_scheduling",
    "job_shop",
    "facility_location",
    "set_cover",
    "data",
    "SolveResult",
    "SolveStatus",
    "__version__",
]
