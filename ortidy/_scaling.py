"""Unit-scaling layer for integer-only solvers.

OR-Tools' knapsack solver (and CP-SAT) require integer coefficients, but real
data has floats. We scale floats to ints, solve, and unscale, rather than
silently truncating floats at the solver boundary.
"""

from __future__ import annotations

from collections.abc import Sequence

# Default precision: 6 significant fractional digits. Chosen to stay well within
# 63-bit integer range for realistically-sized coefficients.
_DEFAULT_MAX_FACTOR = 10**6


def _all_integral(values: Sequence[float]) -> bool:
    return all(float(v).is_integer() for v in values)


def choose_factor(
    values: Sequence[float], *, max_factor: int = _DEFAULT_MAX_FACTOR
) -> int:
    """Pick an integer scale factor (a power of ten) for ``values``.

    Returns ``1`` when every value is already integral, otherwise the smallest
    power of ten (capped at ``max_factor``) that renders the values integral.
    """
    if not values or _all_integral(values):
        return 1
    factor = 1
    while factor < max_factor:
        factor *= 10
        if _all_integral([v * factor for v in values]):
            return factor
    return max_factor


def scale_to_int(
    values: Sequence[float], *, factor: int | None = None
) -> tuple[list[int], int]:
    """Scale floats to ints.

    Args:
        values: The float (or int) sequence to scale.
        factor: An explicit scale factor; if ``None`` it is chosen automatically.

    Returns:
        ``(scaled_ints, factor)`` where ``scaled_ints[i] == round(values[i] * factor)``.
    """
    if factor is None:
        factor = choose_factor(values)
    return [round(v * factor) for v in values], factor


def unscale(value: float, factor: int) -> float:
    """Invert :func:`scale_to_int` for a single (objective) value."""
    return value / factor if factor != 1 else value
