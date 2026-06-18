"""Shared service singletons."""

from __future__ import annotations

from typing import Any

from .settings import get_settings
from .vector_store import LocalVectorIndex

_index: Any | None = None


def get_vector_index(rebuild: bool = False) -> Any:
    global _index
    if _index is None:
        settings = get_settings()
        if settings.vector_provider == "pgvector":
            from .pgvector_store import PGVectorIndex

            _index = PGVectorIndex()
        elif settings.vector_provider == "qwen":
            from .qwen_vector_store import QwenVectorIndex

            _index = QwenVectorIndex()
        else:
            _index = LocalVectorIndex()
    _index.ensure(rebuild=rebuild)
    return _index
