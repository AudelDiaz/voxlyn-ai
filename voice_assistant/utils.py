"""Utility functions shared across the application."""

import re
import subprocess

CODE_BLOCK_RE = re.compile(r"```[\w]*\n.*?```", re.DOTALL)


def has_code_block(text: str) -> bool:
    """Return True when the text contains a Markdown code fence."""
    return bool(CODE_BLOCK_RE.search(text))


def strip_code_blocks(text: str) -> str:
    """Remove code fences from *text* and return the remaining prose."""
    return CODE_BLOCK_RE.sub("", text).strip()


def notify(title: str, body: str) -> None:
    """Show a desktop notification via notify-send (Gnome)."""
    try:
        subprocess.run(
            ["notify-send", title, body],
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def clean_markdown(text: str) -> str:
    """Remove common Markdown formatting from a string.

    Strips bold, italic, code blocks, inline code, links, headers,
    lists, and horizontal rules, returning plain text suitable for TTS.
    """
    text = re.sub(r"```.+?```", "", text, flags=re.DOTALL)
    text = re.sub(r"``(.+?)``", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Strip horizontal rules before inline formatting to avoid
    # ``*`` / ``_`` patterns incorrectly matching ``***`` / ``___``.
    text = re.sub(r"^[-_*]{3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+[\.\)]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text
