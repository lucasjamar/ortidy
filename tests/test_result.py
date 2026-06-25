"""Tests for the result contract itself."""

from __future__ import annotations

from ortidy.result import SolveResult, SolveStatus, from_cp_sat, from_mip


def test_feasible_is_success():
    assert SolveStatus.OPTIMAL.is_success
    assert SolveStatus.FEASIBLE.is_success  # a feasible solution is a success
    assert not SolveStatus.INFEASIBLE.is_success
    assert not SolveStatus.UNBOUNDED.is_success
    assert not SolveStatus.MODEL_INVALID.is_success


def test_result_bool_and_success():
    ok = SolveResult(frame=None, status=SolveStatus.FEASIBLE, objective=1.0)
    bad = SolveResult(frame=None, status=SolveStatus.INFEASIBLE)
    assert ok and ok.is_success
    assert not bad and not bad.is_success


def test_status_mappers():
    from ortools.sat.python import cp_model

    assert from_cp_sat(cp_model.OPTIMAL) is SolveStatus.OPTIMAL
    assert from_cp_sat(cp_model.INFEASIBLE) is SolveStatus.INFEASIBLE

    from ortools.linear_solver import pywraplp

    assert from_mip(pywraplp.Solver.OPTIMAL) is SolveStatus.OPTIMAL
    assert from_mip(pywraplp.Solver.INFEASIBLE) is SolveStatus.INFEASIBLE
