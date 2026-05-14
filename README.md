# Voice Assistant

Local voice assistant powered by **Whisper** (STT), **OpenCode** (LLM),
**Piper** (TTS), and **mempalace** (memory).

Triggered via keyboard shortcut — press a key, speak, and get an AI
voice response.

## Architecture

```
Trigger (keyboard shortcut)
  │  sends "record" via Unix socket
  ▼
Daemon (persistent service)
  ├── Whisper (faster-whisper, int8)  ← speech-to-text
  ├── OpenCode REST API               ← LLM inference
  ├── Mempalace                       ← conversational memory
  └── Piper TTS                       ← text-to-speech
```

## Quick start

### Prerequisites

- Python ≥ 3.13 (managed by `uv`)
- [OpenCode](https://opencode.ai) server running on `localhost:4096`

### Install

```bash
uv sync
```

### Run the daemon (systemd user service)

```bash
systemctl --user enable --now voice-assistant
```

### Keyboard shortcut (Gnome)

1. **Settings → Keyboard → Keyboard Shortcuts → Custom Shortcuts**
2. Add a new shortcut:
   - **Name:** Voice Assistant
   - **Command:** ``` uv run python /path/to/voice-assistant/trigger.py ```
   - **Shortcut:** choose a keybinding (e.g. `Alt+Z`)

Press the shortcut, speak, and the assistant responds.

## Project structure

```
voice-assistant/
├── voice_assistant/           # Library package
│   ├── config.py              # Environment variables and constants
│   ├── audio.py               # Recording, TTS, tone
│   ├── transcription.py       # Whisper-based speech-to-text
│   ├── llm.py                 # OpenCode API interaction
│   ├── commands.py            # In-session voice commands
│   ├── memory.py              # Mempalace persistence
│   └── utils.py               # Markdown cleaning
├── daemon.py                  # Daemon entry point
├── trigger.py                 # Trigger entry point (keyboard shortcut)
├── tests/                     # Unit tests (pytest)
│   ├── test_utils.py
│   └── test_commands.py
├── .opencode/
│   └── skills/                # OpenCode agent skills
│       ├── web-search/
│       ├── control-sistema/
│       ├── recordatorios/
│       ├── notas-rapidas/
│       └── info-sistema/
├── voices/                    # Piper TTS voice models
├── opencode_client.py         # OpenCode REST client
├── mempalace_memory.py        # Mempalace integration
├── voice-assistant.service    # systemd user unit
├── pyproject.toml
└── README.md
```

## Skills

The OpenCode agent has access to these built-in skills:

| Skill | Purpose |
|-------|---------|
| `web-search` | Real-time web search for facts and news |
| `control-sistema` | Volume, brightness, apps, screenshots |
| `recordatorios` | Persistent reminders with systemd timers |
| `notas-rapidas` | Voice notes saved to `~/Notas/` |
| `info-sistema` | System diagnostics (RAM, CPU, disk, updates) |

## Testing

```bash
uv run pytest
```

## Logs

```bash
# Live daemon logs
journalctl --user -u voice-assistant -f

# Rotated log files
tail -f ~/.voice-assistant/voice-assistant.log
tail -f ~/.voice-assistant/voice-assistant.err
```
