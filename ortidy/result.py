"""The result contract shared by every ``ortidy`` solver.

Every solver returns a :class:`SolveResult` carrying the user's frame (with
assignment columns added) plus a structured status, objective value, and solve
metadata. This replaces the old ``print("no optimal solution"); return None``
pattern. A ``FEASIBLE`` solution is a success, not a failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SolveStatus(str, Enum):
    """Backend-neutral solve status.

    The string values are stable and safe to compare against / serialize.
    """

    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNBOUNDED = "UNBOUNDED"
    MODEL_INVALID = "MODEL_INVALID"
    UNKNOWN = "UNKNOWN"

    @property
    def is_success(self) -> bool:
        """``True`` for ``OPTIMAL`` and ``FEASIBLE`` — both are usable answers."""
        return self in (SolveStatus.OPTIMAL, SolveStatus.FEASIBLE)


def from_cp_sat(status: int) -> SolveStatus:
    """Map a CP-SAT ``cp_model`` status code to :class:`SolveStatus`."""
    from ortools.sat.python import cp_model

    return {
        cp_model.OPTIMAL: SolveStatus.OPTIMAL,
        cp_model.FEASIBLE: SolveStatus.FEASIBLE,
        cp_model.INFEASIBLE: SolveStatus.INFEASIBLE,
        cp_model.MODEL_INVALID: SolveStatus.MODEL_INVALID,
        cp_model.UNKNOWN: SolveStatus.UNKNOWN,
    }.get(status, SolveStatus.UNKNOWN)


def from_mip(status: int) -> SolveStatus:
    """Map a ``pywraplp`` linear-solver status code to :class:`SolveStatus`."""
    from ortools.linear_solver import pywraplp

    return {
        pywraplp.Solver.OPTIMAL: SolveStatus.OPTIMAL,
        pywraplp.Solver.FEASIBLE: SolveStatus.FEASIBLE,
        pywraplp.Solver.INFEASIBLE: SolveStatus.INFEASIBLE,
        pywraplp.Solver.UNBOUNDED: SolveStatus.UNBOUNDED,
        pywraplp.Solver.MODEL_INVALID: SolveStatus.MODEL_INVALID,
        pywraplp.Solver.NOT_SOLVED: SolveStatus.UNKNOWN,
    }.get(status, SolveStatus.UNKNOWN)


@dataclass
class SolveResult:
    """Structured solver output.

    Attributes:
        frame: The result dataframe in the *same backend* the user passed in
            (pandas in → pandas out, Polars in → Polars out). ``None`` when no
            solution frame could be produced (e.g. infeasible models).
        status: A :class:`SolveStatus` enum member.
        objective: The objective value, when the solver reports one.
        metadata: Solve metadata — ``wall_time`` (seconds), ``gap``, solver name,
            and any solver-specific extras.
    """

    frame: Any
    status: SolveStatus
    objective: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """``True`` when the solver returned a usable answer (OPTIMAL/FEASIBLE)."""
        return self.status.is_success

    def __bool__(self) -> bool:
        return self.is_success

    def __repr__(self) -> str:
        n = None if self.frame is None else getattr(self.frame, "shape", (None,))[0]
        return (
            f"SolveResult(status={self.status.value}, "
            f"objective={self.objective}, rows={n})"
        )
