"""Aegis-Memory Agent module."""

from . import queries
from .agent import AegisMemoryAgent
from .storage import AnalysisStorage

try:
    from .vector_store import VectorStore
except ImportError:  # optional dependency in slim production images
    VectorStore = None  # type: ignore[assignment]

__all__ = [
    "AegisMemoryAgent",
    "AnalysisStorage",
    "VectorStore",
    "queries"
]
