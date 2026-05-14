"""Memory persistence layer backed by mempalace.

Re-exports the public API from ``mempalace_memory`` for convenience.
"""

# Re-export public API for callers that import from voice_assistant
from mempalace_memory import save_turn, search_context, format_context  # noqa: F401

__all__ = ["save_turn", "search_context", "format_context"]
