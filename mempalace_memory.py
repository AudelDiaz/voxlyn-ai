"""Lightweight conversational memory backed by MemPalace (ChromaDB).

Uses the real mempalace library (v3) for semantic search with 96.6% R@5
recall.  Each conversation turn is stored as a verbatim drawer in the
palace under the ``voxlyn_ai`` wing / ``conversations`` room.

Public API (unchanged)
----------------------
save_turn(user_text, assistant_text)
search_context(query, n_results=5)
format_context(results)
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from mempalace.config import MempalaceConfig
from mempalace.palace import get_collection as _get_collection
from mempalace.searcher import search_memories as _search_memories

_SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r'\b(sk-[A-Za-z0-9_-]{20,})\b'),
    re.compile(r'\b(pk-[A-Za-z0-9_-]{20,})\b'),
    re.compile(r'\b(ghp_[A-Za-z0-9]{36,})\b'),
    re.compile(r'\b(github_pat_[A-Za-z0-9_]{50,})\b'),
    re.compile(r'\b(AKIA[0-9A-Z]{16})\b'),
    re.compile(r'\b(AKID[0-9A-Za-z]{20,})\b'),
    re.compile(r'\b(xox[abpr]-[A-Za-z0-9-]{20,})\b'),
    re.compile(r'\b(rk-[A-Za-z0-9_-]{20,})\b'),
    re.compile(r'\b(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b'),
    re.compile(r'(?:bearer|token|api[_-]?key)\s+[A-Za-z0-9_\-.]{16,}', re.IGNORECASE),
    re.compile(r'-----BEGIN\s?(RSA\s)?PRIVATE\s?KEY-----.*?-----END\s?(RSA\s)?PRIVATE\s?KEY-----', re.DOTALL),
    re.compile(r'-----BEGIN\s?CERTIFICATE-----.*?-----END\s?CERTIFICATE-----', re.DOTALL),
    re.compile(r'-----BEGIN\s?SSH2\s?ENCRYPTED\s?PRIVATE\s?KEY-----.*?-----END\s?SSH2\s?ENCRYPTED\s?PRIVATE\s?KEY-----', re.DOTALL),
    re.compile(r'(?:contraseña|password|passwd|secret|auth_token|access_token|client_secret)\s*[=:]\s*\S{8,}', re.IGNORECASE),
    re.compile(r'(?:export\s+)?(?:OPENAI|ANTHROPIC|DEEPSEEK|GOOGLE|AWS|AZURE|GITHUB)_(?:API_KEY|SECRET(?:_ACCESS_KEY)?|TOKEN|KEY|SESSION_TOKEN)\s*[=:]\s*\S{8,}'),
    re.compile(r'\b[A-Z][A-Z0-9]+_(?:KEY|TOKEN|SECRET|PASSWORD)\s*[=:]\s*\S{8,}'),
]


def _redact_secrets(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub('[REDACTED]', text)
    return text


DATA_DIR = Path.home() / ".voice-assistant"
WING = "voxlyn_ai"
ROOM = "conversations"
MAX_HISTORY = 500

_MIGRATION_DONE = False
_PALACE_PATH: str | None = None


def _palace_path() -> str:
    global _PALACE_PATH
    if _PALACE_PATH is None:
        _PALACE_PATH = str(MempalaceConfig().palace_path)
    return _PALACE_PATH


def _collection():
    return _get_collection(_palace_path(), create=True)


def _drawer_id(content: str) -> str:
    return (
        f"drawer_{WING}_{ROOM}_"
        + hashlib.sha256((WING + ROOM + content).encode()).hexdigest()[:24]
    )


def _ensure_migrated() -> None:
    global _MIGRATION_DONE
    if _MIGRATION_DONE:
        return

    json_path = DATA_DIR / "conversations.json"
    if not json_path.exists():
        _MIGRATION_DONE = True
        return

    col = _collection()
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = []

    for entry in data:
        user_text = entry.get("user", "")
        assistant_text = entry.get("assistant", "")
        if not user_text and not assistant_text:
            continue

        content = f"Usuario: {user_text}\nAsistente: {assistant_text}"
        did = _drawer_id(content)
        ts = entry.get("timestamp") or time.time()
        if isinstance(ts, (int, float)):
            filed_at = datetime.fromtimestamp(ts).isoformat()
        else:
            filed_at = datetime.now().isoformat()

        existing = col.get(ids=[did], include=[])
        if existing.ids:
            continue

        col.upsert(
            ids=[did],
            documents=[content],
            metadatas=[{
                "wing": WING,
                "room": ROOM,
                "source_file": "",
                "chunk_index": 0,
                "added_by": "voxlyn_migrate",
                "filed_at": filed_at,
            }],
        )

    json_path.rename(json_path.with_suffix(".json.migrated"))
    _MIGRATION_DONE = True


def _trim() -> None:
    col = _collection()
    where = {"$and": [{"wing": WING}, {"room": ROOM}]}
    result = col.get(where=where, include=["metadatas"])
    ids = result.ids
    if len(ids) <= MAX_HISTORY:
        return

    pairs = sorted(
        ((rid, result.metadatas[i].get("filed_at", "")) for i, rid in enumerate(ids)),
        key=lambda x: x[1],
    )
    to_delete = [p[0] for p in pairs[:-MAX_HISTORY]]
    for i in range(0, len(to_delete), 100):
        col.delete(ids=to_delete[i : i + 100])


def save_turn(user_text: str, assistant_text: str) -> None:
    _ensure_migrated()

    user_redacted = _redact_secrets(user_text)
    assistant_redacted = _redact_secrets(assistant_text)
    content = f"Usuario: {user_redacted}\nAsistente: {assistant_redacted}"

    col = _collection()
    did = _drawer_id(content)

    existing = col.get(ids=[did], include=[])
    if existing.ids:
        return

    col.upsert(
        ids=[did],
        documents=[content],
        metadatas=[{
            "wing": WING,
            "room": ROOM,
            "source_file": "",
            "chunk_index": 0,
            "added_by": "voxlyn",
            "filed_at": datetime.now().isoformat(),
        }],
    )

    _trim()


def search_context(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    _ensure_migrated()

    if not query or len(query.strip()) < 3:
        return _last_n(n_results)

    results = _search_memories(
        query=query,
        palace_path=_palace_path(),
        wing=WING,
        room=ROOM,
        n_results=n_results,
    )

    return [
        {
            "text": hit.get("text", ""),
            "room": hit.get("room", ROOM),
            "wing": hit.get("wing", WING),
            "similarity": hit.get("similarity", 0.0),
        }
        for hit in results.get("results", [])
    ]


def format_context(results: list[dict[str, Any]]) -> str:
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


def _last_n(n: int) -> list[dict[str, Any]]:
    col = _collection()
    where = {"$and": [{"wing": WING}, {"room": ROOM}]}
    result = col.get(where=where, include=["documents", "metadatas"])
    pairs = sorted(
        (
            (result.documents[i], result.metadatas[i])
            for i in range(len(result.ids))
        ),
        key=lambda x: x[1].get("filed_at", ""),
        reverse=True,
    )
    return [
        {
            "text": doc,
            "room": meta.get("room", ROOM),
            "wing": meta.get("wing", WING),
            "similarity": 0.0,
        }
        for doc, meta in pairs[:n]
    ]
