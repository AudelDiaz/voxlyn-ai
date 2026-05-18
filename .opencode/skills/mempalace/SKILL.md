---
name: mempalace
description: >
  Proactive conversation memory. Analyze every user interaction for
  memory-worthy content and file it into the right wing/room/hall so
  you become smarter over time. Uses MemPalace v3 semantic search.
---

## Core principle

Every conversation is an opportunity to grow your knowledge base.
The automatic pipeline saves raw turns — you file **structured memories**
that make future responses more informed.

When the user says something, ask yourself:
1. Is this a **decision** or **fact** worth remembering?
2. Is this a **user preference** or **habit**?
3. Is this a **discovery** or **insight**?
4. Is this a **cross-project connection**?
5. Is this a **new entity relationship**?

If yes → file it immediately using the helper.

## How to file memories

```bash
# Decisions / facts
uv run python mempalace_helper.py add --room <topic> --hall hall_facts --content "<what was decided>"

# User preferences (habits, likes, opinions)
uv run python mempalace_helper.py add --room <topic> --hall hall_preferences --content "<the preference>"

# Breakthroughs / discoveries
uv run python mempalace_helper.py add --room <topic> --hall hall_discoveries --content "<the insight>"

# Events / milestones / debugging sessions
uv run python mempalace_helper.py add --room <topic> --hall hall_events --content "<what happened>"

# Advice / solutions (with rationale)
uv run python mempalace_helper.py add --room <topic> --hall hall_advice --content "<the solution>"
```

The content string should be a **self-contained summary** so future
you can understand it without re-reading the full conversation.

## When to create a new room

- A topic comes up 2+ times in a session → create a room for it
- The user asks "remember that thing about X" → create a room if missing
- A discussion produces a clear decision or output
- Room names: kebab-case, short (`tts-switch`, `api-rate-limits`)

## When to create a new wing

- A new project, repo, or app appears in conversation
- A person is mentioned with substantive context 3+ times
- A topic is clearly independent of existing wings

A wing is created implicitly on the first drawer filed there:
```bash
uv run python mempalace_helper.py add --wing <new-wing> --room <topic> ...
```

## How to retrieve past memories

Before answering a question, proactively search your memory:

```bash
uv run python mempalace_helper.py search "<key terms>" -n 5
```

If the answer requires specific topic context:

```bash
uv run python mempalace_helper.py search "<query>" --room <topic>
```

## Cross-wing connections (tunnels)

When you file the same room name in different wings, MemPalace
automatically treats that as a cross-wing connection. File with
consistent room names to enable this.

Example — filing "auth" in two projects:
```
wing voxlyn_ai   → room auth/hall_events  → "added HTTP basic auth to opencode_client.py"
wing website     → room auth/hall_facts   → "elegí Clerk para auth de usuarios"
```

These will be linked automatically. Future search in either wing
finds relevant results from both.

## Conversation flow

During every interaction:

1. **Listen** for memory-worthy content (decisions, preferences, discoveries)
2. **Retrieve** relevant past memories to inform your response
3. **Respond** as usual (concise, 1-3 sentences)
4. **File** what you learned via the helper

Over time your memory grows richer and your answers become more
contextual. A user shouldn't need to repeat themselves.

## Handling memory queries from the user

When the user asks about what you remember, what wings or rooms exist,
or to list stored information:

```bash
# List all wings and rooms with drawer counts
uv run python mempalace_helper.py status

# Filter to a specific wing
uv run python mempalace_helper.py status --wing <wing>

# Search for something specific
uv run python mempalace_helper.py search "<query>" -n 5
```

The `status` command returns the number of drawers, all wings, and all
rooms. Report them back naturally (don't read raw output).

## Architecture reference

| Concept | What it is | Example |
|---------|-----------|---------|
| Wing | Person or project | `voxlyn-ai`, `website-redesign` |
| Room | Specific topic | `tts-switch`, `auth`, `deploy` |
| Hall | Category of memory | `hall_facts`, `hall_events`, `hall_discoveries`, `hall_preferences`, `hall_advice` |
| Tunnel | Same room in multiple wings (auto-linked) | `voxlyn_ai/auth` ↔ `website/auth` |
| Drawer | A stored content chunk | A single filed memory |
