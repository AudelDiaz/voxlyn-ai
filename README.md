# voxlyn-ai

Hands-free AI voice assistant for Linux. Press a key, speak, get an AI
voice response — entirely local.

**Whisper** → STT · **OpenCode** → LLM agent · **Piper** → TTS

Inspired by [Nate Gentile's CachyOS + Omarchy setup video](https://youtu.be/b6uQTR7E9qg).

## Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Speech-to-Text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (int8) | Transcribe mic audio to text |
| Agent / LLM | [OpenCode](https://opencode.ai) + any backend | AI agent with skills and memory |
| Text-to-Speech | [Piper](https://github.com/rhasspy/piper) TTS | Synthesize natural voice responses |
| Memory | Mempalace (JSON ring buffer) | Persistent conversation history |
| Runtime | Python 3.13+ · [uv](https://docs.astral.sh/uv/) · systemd | Dependency management and daemon lifecycle |
| Audio I/O | sounddevice · soundfile · PulseAudio/PipeWire | Capture and playback |

## Architecture

```
Trigger (keyboard shortcut)
  │  sends "record" via Unix socket
  ▼
Daemon (persistent systemd service)
  ├── Whisper (faster-whisper, int8)  ← speech-to-text
  ├── OpenCode agent                  ← LLM with skills + memory
  ├── Piper TTS                       ← text-to-speech
  └── Mempalace (JSON memory)         ← conversational history + rooms
```

## Quick start

### Prerequisites

| Dependency | Notes |
|------------|-------|
| Linux desktop | Tested on CachyOS, Arch, Ubuntu (Gnome / Hyprland) |
| [uv](https://docs.astral.sh/uv/) | Python package manager — `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [OpenCode](https://opencode.ai) | AI agent server — `npm install -g @opencode-ai/cli` |
| PulseAudio / PipeWire | Audio system (pre-installed on most distros) |
| Microphone + speakers | Built-in or USB |

### 1. Clone and install

```bash
git clone https://github.com/AudelDiaz/voxlyn-ai.git
cd voxlyn-ai
uv sync
```

The first run will download Whisper and Piper models (~500 MB total).

### 2. Link the skills globally (optional but recommended)

Skills inside `.opencode/skills/` are only visible if OpenCode runs from
the project directory. To make them available system-wide:

```bash
mkdir -p ~/.config/opencode/skills
ln -s ~/voxlyn-ai/.opencode/skills/* ~/.config/opencode/skills/
```

Then restart the OpenCode server: `pkill opencode && opencode serve`.

### 3. Link the systemd service

```bash
mkdir -p ~/.config/systemd/user
ln -s ~/voxlyn-ai/voxlyn-ai.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now voxlyn-ai
```

The daemon will start automatically on every login.

### 4. Set up the keyboard shortcut (Gnome)

**Settings → Keyboard → Keyboard Shortcuts → Custom Shortcuts → +**

| Field | Value |
|-------|-------|
| Name | voxlyn-ai |
| Command | ``` uv run --project ~/voxlyn-ai ~/voxlyn-ai/trigger.py ``` |
| Shortcut | e.g. `Alt+Z` |

On other desktops (Hyprland, KDE, Sway), bind the same command to a
key combination in your window manager's config.

Press the shortcut, speak, hear the response.

### Verify it works

```bash
journalctl --user -u voxlyn-ai -f
```

Press your shortcut and say something — you should see `[Escuchando...]`
in the logs followed by the transcription and response.

## Project structure

```
voxlyn-ai/
├── voice_assistant/           # Python package
│   ├── config.py              # Environment variables and constants
│   ├── audio.py               # Recording, TTS, tone
│   ├── transcription.py       # Whisper STT
│   ├── llm.py                 # OpenCode API interaction
│   ├── commands.py            # In-session voice commands
│   ├── memory.py              # Conversation memory
│   └── utils.py               # Markdown cleaning, notifications
├── daemon.py                  # Persistent daemon entry point
├── trigger.py                 # Keyboard-shortcut client
├── tests/                     # pytest suite
├── .opencode/skills/          # Agent skills (5 built-in)
├── voices/                    # Piper voices (downloaded on first run)
├── opencode_client.py         # OpenCode REST client
├── mempalace_memory.py        # JSON conversation memory (500-turn ring buffer)
├── mempalace.yaml             # Room definitions for context retrieval
├── voxlyn-ai.service          # systemd user unit
├── pyproject.toml
└── README.md
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WHISPER_MODEL` | `small` | Model size: `tiny`, `base`, `small`, `medium`, `large` |
| `COMPUTE_TYPE` | `int8` | Quantization: `int8`, `float16`, `float32` |
| `WHISPER_LANG` | auto | Force language code (`es`, `en`, …) or empty for auto |
| `TTS_VOICE` | `es_ES-davefx-medium` | Piper voice name |
| `OPENCODE_URL` | `http://localhost:4096` | OpenCode server URL |
| `SYSTEM_PROMPT` | *(built-in)* | Override the LLM system prompt |

## Skills

The OpenCode agent ships with these built-in skills:

| Skill | Purpose |
|-------|---------|
| `web-search` | Real-time web search for facts and news |
| `system-control` | Volume, brightness, apps, screenshots |
| `reminders` | Persistent reminders with systemd timers |
| `quick-notes` | Voice notes saved to `~/Notes/` |
| `system-info` | System diagnostics (RAM, CPU, disk, updates) |

To add your own skill, create a directory under `.opencode/skills/` with a
`SKILL.md` (see [OpenCode skill docs](https://opencode.ai/docs/skills/)).

## Memory (Mempalace)

Every conversation turn is automatically saved to
`~/.voice-assistant/conversations.json` — a lightweight JSON
backend that replaced the original chromadb-based mempalace
(too heavy for a voice assistant).

### How it works

| Layer | File | Role |
|-------|------|------|
| Public API | `voice_assistant/memory.py` | Re-exports `save_turn`, `search_context`, `format_context` |
| Backend | `mempalace_memory.py` | JSON read/write with 500-turn ring buffer |
| Rooms config | `mempalace.yaml` | Keyword-indexed rooms for project context |
| Data file | `~/.voice-assistant/conversations.json` | All conversation history |

When you speak, the daemon:
1. Searches the last 5 turns from memory
2. Prepends them as context to the LLM prompt
3. Saves the new turn after the response

### Inspect memory

```bash
# See all past conversations
cat ~/.voice-assistant/conversations.json

# Tail the last entry
python3 -c "import json; d=json.load(open('$HOME/.voice-assistant/conversations.json')); print(d[-1]['user'], '→', d[-1]['assistant'][:100])"
```

### Rooms

The `mempalace.yaml` organises project knowledge into rooms
for better context retrieval:

| Room | Purpose |
|------|---------|
| `voice_assistant` | Core package docs (STT, LLM, TTS, commands) |
| `skills` | Agent skills reference |
| `daemon` | systemd service and socket protocol |
| `memory` | Conversation backend details |
| `voices` | Piper TTS voice models |
| `tests` | pytest suite metadata |
| `general` | Catch-all |

Add or update rooms as the project grows — the LLM will pick
them up automatically via `search_context`.

## Testing

```bash
uv run pytest
```

## Logs

```bash
# Live daemon logs (systemd journal)
journalctl --user -u voxlyn-ai -f

# Rotated file logs
tail -f ~/.voice-assistant/voxlyn-ai.log
tail -f ~/.voice-assistant/voxlyn-ai.err
```

## Use cases

| Scenario | How voxlyn-ai helps |
|----------|---------------------|
| **Hands-free coding** | Ask questions, search docs, run terminal commands without touching the keyboard |
| **Smart home control** | Adjust volume/brightness, open apps, take screenshots by voice |
| **Quick notes & reminders** | "Recuérdame comprar leche a las 5" or "Guarda esta idea en notas" |
| **System monitoring** | "¿Cuánta RAM tengo libre?", "¿Hay actualizaciones pendientes?" |
| **Research assistant** | "Busca en internet el clima de hoy" — web-search skill fetches live answers |
| **Accessibility** | Full voice interface for users with motor or vision impairments |

## Roadmap

- [ ] **Wake word detection** — activate with "Hey Voxlyn" instead of a key press
- [ ] **Multi-turn voice UI** — chain follow-up questions without re-triggering
- [ ] **Vector memory** — upgrade from last-N to semantic search (sentence embeddings)
- [ ] **Plugin system** — third-party skills loaded from `~/.config/voxlyn/skills/`
- [ ] **GUI dashboard** — view conversation history, manage sessions, test voices
- [ ] **Offline LLM** — bundle a local model via Ollama/Llama.cpp for fully offline use
- [ ] **Multi-language** — seamless switching between languages mid-conversation
- [ ] **Mobile companion** — Flutter/GTK app for push-to-talk from phone

## Uninstall

```bash
systemctl --user stop voxlyn-ai
systemctl --user disable voxlyn-ai
rm ~/.config/systemd/user/voxlyn-ai.service
rm -rf ~/voxlyn-ai ~/.voice-assistant
```
