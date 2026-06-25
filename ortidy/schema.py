"""Input validation with precise, actionable errors.

Formalizes the old ad-hoc ``if not {"value","weight"}.issubset(...)`` instinct.
Errors name the missing column (and, where relevant, the expected dtype), and we
raise ``ValueError`` / ``KeyError`` rather than the old ``AttributeError``.
"""

from __future__ import annotations

import narwhals.stable.v1 as nw


def require_columns(frame: nw.DataFrame, columns: set[str], *, frame_name: str) -> None:
    """Raise ``KeyError`` if any required column is missing, naming the gaps."""
    missing = columns - set(frame.columns)
    if missing:
        raise KeyError(
            f"{frame_name} is missing required column(s) "
            f"{sorted(missing)}; got {frame.columns}."
        )


def require_numeric(frame: nw.DataFrame, columns: set[str], *, frame_name: str) -> None:
    """Raise ``ValueError`` if any named column is non-numeric."""
    schema = frame.schema
    bad = {
        col: str(schema[col])
        for col in columns
        if col in schema and not schema[col].is_numeric()
    }
    if bad:
        raise ValueError(
            f"{frame_name} column(s) must be numeric, but got non-numeric dtypes: "
            f"{bad}."
        )


def require_nonempty(frame: nw.DataFrame, *, frame_name: str) -> None:
    """Raise ``ValueError`` if the frame has no rows."""
    if frame.shape[0] == 0:
        raise ValueError(f"{frame_name} must have at least one row.")
