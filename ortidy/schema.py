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


def require_numeric(
    frame: nw.DataFrame,
    columns: set[str],
    *,
    frame_name: str,
    non_negative: bool = False,
    allow_null: bool = False,
) -> None:
    """Validate that named columns are numeric (and, optionally, clean).

    Raises ``ValueError`` if any column is non-numeric, contains nulls (unless
    ``allow_null``), or — when ``non_negative`` — holds a negative value.
    """
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
    present = [c for c in columns if c in frame.columns]
    if not allow_null:
        null_cols = [c for c in present if frame.get_column(c).is_null().any()]
        if null_cols:
            raise ValueError(
                f"{frame_name} column(s) {sorted(null_cols)} contain null values."
            )
    if non_negative:
        neg_cols = [c for c in present if (frame.get_column(c) < 0).any()]
        if neg_cols:
            raise ValueError(
                f"{frame_name} column(s) {sorted(neg_cols)} must be non-negative."
            )


def require_unique(frame: nw.DataFrame, column: str, *, frame_name: str) -> None:
    """Raise ``ValueError`` if ``column`` has duplicate values (e.g. an id column)."""
    series = frame.get_column(column)
    if series.n_unique() != frame.shape[0]:
        raise ValueError(
            f"{frame_name} column {column!r} must have unique values "
            "(found duplicates)."
        )


def require_nonempty(frame: nw.DataFrame, *, frame_name: str) -> None:
    """Raise ``ValueError`` if the frame has no rows."""
    if frame.shape[0] == 0:
        raise ValueError(f"{frame_name} must have at least one row.")
