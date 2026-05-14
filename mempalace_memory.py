import os
import time
from typing import Optional

from mempalace.miner import add_drawer
from mempalace.palace import get_collection
from mempalace.searcher import search_memories

PALACE_PATH = os.path.expanduser("~/.mempalace/palace")
DEFAULT_WING = "voice_assistant"
DEFAULT_ROOM = "conversations"
SEARCH_LIMIT = 5


def save_turn(
    user_text: str,
    assistant_text: str,
    wing: str = DEFAULT_WING,
    room: str = DEFAULT_ROOM,
) -> None:
    content = f"Usuario: {user_text}\nAsistente: {assistant_text}"
    source_file = f"voice:{int(time.time())}"
    collection = get_collection(PALACE_PATH)
    add_drawer(
        collection=collection,
        wing=wing,
        room=room,
        content=content,
        source_file=source_file,
        chunk_index=0,
        agent="voice_assistant",
    )


def search_context(
    query: str,
    wing: Optional[str] = None,
    n_results: int = SEARCH_LIMIT,
) -> list[dict]:
    results = search_memories(
        query=query,
        palace_path=PALACE_PATH,
        wing=wing,
        n_results=n_results,
        max_distance=1.0,
    )
    return results.get("results", [])


def format_context(results: list[dict]) -> str:
    if not results:
        return ""
    lines = []
    for r in results:
        room = r.get("room", "?")
        text = r.get("text", "")[:200].strip()
        lines.append(f"[{room}] {text}")
    return (
        "Relevant context from your past conversations:\n"
        + "\n".join(lines)
    )
