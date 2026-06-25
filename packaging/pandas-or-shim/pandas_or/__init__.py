"""Deprecation shim: ``pandas-or`` was renamed to ``ortidy``.

Importing ``pandas_or`` re-exports everything from :mod:`ortidy` and emits a
``DeprecationWarning``. Update your imports to ``import ortidy``.
"""

from __future__ import annotations

import warnings

from ortidy import *  # noqa: F401,F403
from ortidy import __all__ as _ortidy_all

warnings.warn(
    "`pandas-or` has been renamed to `ortidy`. Import `ortidy` instead; "
    "`pandas_or` is a deprecation shim and will not receive updates.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = list(_ortidy_all)
