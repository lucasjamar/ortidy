"""Narwhals boundary helpers.

The library is backend-agnostic: a user who passes pandas gets pandas back, a
user who passes Polars gets Polars back. We accept native frames at the public
boundary, do internal work in Narwhals, and return native frames. At the solver
boundary we extract plain Python lists/ints/floats — OR-Tools does not consume
dataframes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import narwhals.stable.v1 as nw

ID_COLUMN_DEFAULT = "__ortidy_row_id__"


def to_mapping(value: Any) -> dict[Any, Any]:
    """Coerce a per-node input to a ``{node: value}`` dict.

    Accepts a mapping directly, or a native two-column frame whose first column is
    the node id and second is the value (the tidy form of a lookup table).
    """
    if isinstance(value, Mapping):
        return dict(value)
    frame = to_nw(value)
    if len(frame.columns) < 2:
        raise ValueError(
            "expected a mapping or a 2-column (node, value) frame; "
            f"got columns {frame.columns}."
        )
    keys = column_to_list(frame, frame.columns[0])
    vals = column_to_list(frame, frame.columns[1])
    if len(set(keys)) != len(keys):
        raise ValueError(
            f"lookup frame has duplicate keys in column {frame.columns[0]!r}."
        )
    return dict(zip(keys, vals, strict=True))


def unique_in_order(values: list) -> list:
    """Distinct values, preserving first-seen order."""
    seen: dict[Any, None] = {}
    for v in values:
        seen.setdefault(v, None)
    return list(seen)


def to_nw(frame: Any) -> nw.DataFrame:
    """Wrap a native frame in a Narwhals DataFrame at the public boundary."""
    return nw.from_native(frame, eager_only=True)


def to_native(frame: nw.DataFrame) -> Any:
    """Unwrap a Narwhals DataFrame back to the user's native backend."""
    return frame.to_native()


def column_to_list(frame: nw.DataFrame, column: str) -> list:
    """Extract a column as a plain Python list (the solver-boundary handoff)."""
    return frame.get_column(column).to_list()


def ensure_id_column(
    frame: nw.DataFrame, id_column: str | None
) -> tuple[nw.DataFrame, str, bool]:
    """Guarantee an explicit row-identity column (no implicit positional index).

    If ``id_column`` is given it must exist. If ``None`` we synthesize a stable
    integer id column, honoring the index-free model: identity is always an
    explicit column, never a positional index.

    Returns:
        ``(frame, id_column_name, was_synthesized)``.
    """
    if id_column is not None:
        if id_column not in frame.columns:
            raise KeyError(
                f"id column {id_column!r} not found; columns are {frame.columns}"
            )
        if frame.get_column(id_column).n_unique() != frame.shape[0]:
            raise ValueError(f"id column {id_column!r} must have unique values.")
        return frame, id_column, False
    frame = frame.with_row_index(name=ID_COLUMN_DEFAULT)
    return frame, ID_COLUMN_DEFAULT, True


def drop_if_synthesized(
    frame: nw.DataFrame, id_column: str, was_synthesized: bool
) -> nw.DataFrame:
    """Drop the helper id column if we created it ourselves."""
    if was_synthesized and id_column in frame.columns:
        return frame.drop(id_column)
    return frame
