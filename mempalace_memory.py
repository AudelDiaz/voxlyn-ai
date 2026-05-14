"""Lightweight conversational memory backed by a local JSON file.

Replaces the original mempalace backend which became incompatible
with Python 3.14 and pulled in excessive dependencies (chromadb,
kubernetes, grpcio, protobuf …).
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

_SECRET_PATTERNS: list[re.Pattern] = [
    # API keys
    re.compile(r'\b(sk-[A-Za-z0-9_-]{20,})\b'),
    re.compile(r'\b(pk-[A-Za-z0-9_-]{20,})\b'),
    re.compile(r'\b(ghp_[A-Za-z0-9]{36,})\b'),
    re.compile(r'\b(github_pat_[A-Za-z0-9_]{50,})\b'),
    re.compile(r'\b(AKIA[0-9A-Z]{16})\b'),
    re.compile(r'\b(AKID[0-9A-Za-z]{20,})\b'),
    re.compile(r'\b(xox[abpr]-[A-Za-z0-9-]{20,})\b'),       # Slack tokens
    re.compile(r'\b(rk-[A-Za-z0-9_-]{20,})\b'),              # Replicate API key
    # JWT / bearer tokens
    re.compile(r'\b(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b'),
    re.compile(r'(?:bearer|token|api[_-]?key)\s+[A-Za-z0-9_\-.]{16,}', re.IGNORECASE),
    # Private keys / certificates
    re.compile(r'-----BEGIN\s?(RSA\s)?PRIVATE\s?KEY-----.*?-----END\s?(RSA\s)?PRIVATE\s?KEY-----', re.DOTALL),
    re.compile(r'-----BEGIN\s?CERTIFICATE-----.*?-----END\s?CERTIFICATE-----', re.DOTALL),
    re.compile(r'-----BEGIN\s?SSH2\s?ENCRYPTED\s?PRIVATE\s?KEY-----.*?-----END\s?SSH2\s?ENCRYPTED\s?PRIVATE\s?KEY-----', re.DOTALL),
    # Generic secret patterns
    re.compile(r'(?:contraseña|password|passwd|secret|auth_token|access_token|client_secret)\s*[=:]\s*\S{8,}', re.IGNORECASE),
    re.compile(r'(?:export\s+)?(?:OPENAI|ANTHROPIC|DEEPSEEK|GOOGLE|AWS|AZURE|GITHUB)_(?:API_KEY|SECRET(?:_ACCESS_KEY)?|TOKEN|KEY|SESSION_TOKEN)\s*[=:]\s*\S{8,}'),
    re.compile(r'\b[A-Z][A-Z0-9]+_(?:KEY|TOKEN|SECRET|PASSWORD)\s*[=:]\s*\S{8,}'),
]


def _redact_secrets(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub('[REDACTED]', text)
    return text

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
    """Persist a single conversation turn to the local JSON file.

    Secrets (API keys, tokens, private keys, passwords) are redacted
    before storage.
    """
    data = _load()
    data.append({
        "id": f"turn:{int(time.time())}",
        "user": _redact_secrets(user_text),
        "assistant": _redact_secrets(assistant_text),
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
