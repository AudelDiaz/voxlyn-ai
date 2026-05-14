"""Lightweight conversational memory backed by a local JSON file.

Replaces the original mempalace backend which became incompatible
with Python 3.14 and pulled in excessive dependencies (chromadb,
kubernetes, grpcio, protobuf …).
"""

import json
import os
import time
from pathlib import Path
from typing import Any

DATA_DIR = Path.home() / ".voice-assistant"
MEMORY_PATH = DATA_DIR / "conversations.json"
WING = "voxlyn_ai"
MAX_HISTORY = 500


def _ensure_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MEMORY_PATH.exists():
        MEMORY_PATH.write_text("[]", encoding="utf-8")


def _load() -> list[dict[str, Any]]:
    _ensure_file()
    try:
        return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _dump(data: list[dict[str, Any]]) -> None:
    MEMORY_PATH.write_text(json.dumps(data[-MAX_HISTORY:], indent=2, ensure_ascii=False), encoding="utf-8")


def save_turn(user_text: str, assistant_text: str) -> None:
    """Persist a single conversation turn to the local JSON file."""
    data = _load()
    data.append({
        "id": f"turn:{int(time.time())}",
        "user": user_text,
        "assistant": assistant_text,
        "timestamp": time.time(),
        "wing": WING,
        "agent": "voxlyn",
    })
    _dump(data)


def search_context(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Return the most recent *n_results* conversation turns.

    Simple last-N retrieval.  A full vector-search layer can be added
    later if keyword-based recall proves insufficient.
    """
    data = _load()
    results = []
    for entry in reversed(data):
        if len(results) >= n_results:
            break
        results.append({
            "text": f"Usuario: {entry.get('user', '')}\nAsistente: {entry.get('assistant', '')}",
            "room": "conversations",
        })
    return results


def format_context(results: list[dict[str, Any]]) -> str:
    """Format a list of memory results into a plain-text preamble."""
    if not results:
        return ""
    lines = []
    for r in results:
        room = r.get("room", "?")
        text = r.get("text", "")[:300].strip()
        lines.append(f"[{room}] {text}")
    return (
        "Relevant context from your past conversations:\n"
        + "\n".join(lines)
    )
