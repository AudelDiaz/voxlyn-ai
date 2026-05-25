from voice_assistant.config import (
    LOCAL_KEYWORDS,
    NEVER_REMOTE_KEYWORDS,
    REMOTE_TRIGGERS,
)


def route(text: str) -> str:
    lower = text.lower()
    if any(kw in lower for kw in NEVER_REMOTE_KEYWORDS):
        return "local"
    has_remote = any(kw in lower for kw in REMOTE_TRIGGERS)
    has_local = any(kw in lower for kw in LOCAL_KEYWORDS)
    if has_remote and has_local:
        return "remote"
    if has_local:
        return "local"
    return "remote"
