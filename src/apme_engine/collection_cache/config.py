"""Configuration for the collection cache and session storage."""

import os
from pathlib import Path


def get_cache_root() -> Path:
    """Return the APME data root directory (e.g. ~/.apme-data/collection-cache).

    Used as the default parent for session-scoped venv storage.

    Returns:
        Path to the data root directory.
    """
    base = os.environ.get("APME_COLLECTION_CACHE", "").strip()
    if base:
        return Path(base).expanduser().resolve()
    return Path(os.path.expanduser("~/.apme-data/collection-cache")).resolve()
