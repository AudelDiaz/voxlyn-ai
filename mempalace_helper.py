"""Helper script for the agent to read/write structured memories.

Called via bash by the agent during conversation.  Wraps common
MemPalace operations for wings, rooms, halls, and knowledge graph.
"""

import argparse
import hashlib
from datetime import datetime

from mempalace.config import MempalaceConfig
from mempalace.palace import get_collection as _get_collection
from mempalace.searcher import search_memories as _search

PALACE_PATH = str(MempalaceConfig().palace_path)
WING = "voxlyn_ai"


def _col():
    return _get_collection(PALACE_PATH, create=True)


def _drawer_id(wing: str, room: str, content: str) -> str:
    raw = f"{wing}{room}{content}"
    return f"drawer_{wing}_{room}_" + hashlib.sha256(raw.encode()).hexdigest()[:24]


def add(wing: str, room: str, content: str, hall: str = "") -> None:
    col = _col()
    full_room = f"{room}/{hall}" if hall else room
    did = _drawer_id(wing, full_room, content)
    existing = col.get(ids=[did], include=[])
    if existing.ids:
        return
    col.upsert(
        ids=[did],
        documents=[content],
        metadatas=[{
            "wing": wing,
            "room": full_room,
            "source_file": "voxlyn_agent",
            "chunk_index": 0,
            "added_by": "voxlyn",
            "filed_at": datetime.now().isoformat(),
        }],
    )
    print(f"OK  → {wing} / {full_room}")


def search(query: str, wing: str = "", room: str = "", n: int = 5) -> None:
    kwargs = {"palace_path": PALACE_PATH, "n_results": n}
    if wing:
        kwargs["wing"] = wing
    if room:
        kwargs["room"] = room
    results = _search(query, **kwargs)
    hits = results.get("results", [])
    if not hits:
        print("No results.")
        return
    for r in hits:
        print(f"[{r.get('wing','?')} / {r.get('room','?')}]"
              f"  {r.get('text','')[:200]}")


def status(wing: str = "") -> None:
    col = _col()
    where = {"wing": wing} if wing else None
    result = col.get(where=where, include=["metadatas"]) if where else col.get(include=["metadatas"])
    wings = set()
    rooms = set()
    for m in result.metadatas:
        wings.add(m.get("wing", "?"))
        rooms.add(f"{m.get('wing','?')} / {m.get('room','?')}")
    print(f"Drawers: {len(result.ids)}")
    print(f"Wings:   {', '.join(sorted(wings))}")
    print(f"Rooms:   {', '.join(sorted(rooms))}")


def main() -> None:
    parser = argparse.ArgumentParser(description="MemPalace helper for the agent")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="File a structured memory")
    p_add.add_argument("--wing", default=WING)
    p_add.add_argument("--room", required=True)
    p_add.add_argument("--hall", default="", choices=["hall_facts", "hall_events", "hall_discoveries", "hall_preferences", "hall_advice"])
    p_add.add_argument("--content", required=True)

    p_search = sub.add_parser("search", help="Search memory")
    p_search.add_argument("query")
    p_search.add_argument("--wing", default="")
    p_search.add_argument("--room", default="")
    p_search.add_argument("-n", type=int, default=5)

    p_status = sub.add_parser("status", help="View palace status")
    p_status.add_argument("--wing", default="")

    args = parser.parse_args()

    if args.command == "add":
        add(args.wing, args.room, args.content, args.hall)
    elif args.command == "search":
        search(args.query, args.wing, args.room, args.n)
    elif args.command == "status":
        status(args.wing)


if __name__ == "__main__":
    main()
