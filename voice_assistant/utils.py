"""Utility functions shared across the application."""

import re
import shutil
import subprocess
import time
from pathlib import Path

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


def copy_to_clipboard(text: str) -> None:
    """Copy *text* to the system clipboard via wl-copy (Wayland) or xclip."""
    for cmd in ("wl-copy", "xclip", "xsel"):
        try:
            subprocess.run(
                [cmd],
                input=text.encode(),
                capture_output=True,
                timeout=5,
            )
            return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue


def save_and_open(text: str) -> str:
    """Write *text* to a temp markdown file and open it in a terminal.

    Tries kitty → ghostty with nvim, falls back to cat, then xdg-open.
    Returns the path to the created file.
    """
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = Path(f"/tmp/voxlyn-{ts}.md")
    path.write_text(text, encoding="utf-8")
    _open_in_terminal(str(path))
    return str(path)


def _open_in_terminal(path: str) -> None:
    for term in ("kitty", "ghostty"):
        if not shutil.which(term):
            continue
        if shutil.which("nvim"):
            cmd = [term, "nvim", path]
        else:
            cmd = [term, "sh", "-c", f"cat {path}; echo; echo 'Presiona Enter para cerrar'; read"]
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            continue
        return
    try:
        subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def summarize(text: str, max_len: int = 150) -> str:
    """Return the first sentence or meaningful fragment up to *max_len* chars."""
    clean = clean_markdown(text).strip()
    if not clean:
        return ""
    for sep in (". ", ".\n", "\n\n", "!", "?"):
        idx = clean.find(sep)
        if 10 < idx < max_len:
            return clean[: idx + 1]
    if len(clean) <= max_len:
        return clean
    break_idx = clean.rfind(" ", 0, max_len)
    return clean[:break_idx] + "…" if break_idx > 0 else clean[:max_len] + "…"


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
