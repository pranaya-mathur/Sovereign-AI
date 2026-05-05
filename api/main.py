"""Deprecated API entrypoint.

Use `api.main_v2:app` for all production and local runtime paths.
"""

import warnings

from api.main_v2 import app

warnings.warn(
    "`api.main:app` is deprecated; switch to `api.main_v2:app`.",
    DeprecationWarning,
    stacklevel=2,
)
