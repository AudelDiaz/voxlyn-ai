# voxlyn-ai

Hands-free AI voice assistant for Linux. Press a key, speak, get an AI
voice response — entirely local.

**Whisper** → STT · **OpenCode** → LLM agent · **Piper** → TTS

## Architecture

```
Trigger (keyboard shortcut)
  │  sends "record" via Unix socket
  ▼
Daemon (persistent systemd service)
  ├── Whisper (faster-whisper, int8)  ← speech-to-text
  ├── OpenCode agent                  ← LLM with skills + memory
  ├── Piper TTS                       ← text-to-speech
  └── Mempalace                       ← conversational memory
```

## Quick start

### Prerequisites

- Python ≥ 3.13 ([uv](https://docs.astral.sh/uv/))
- [OpenCode](https://opencode.ai) server running on `localhost:4096`

### Install

```bash
git clone https://github.com/AudelDiaz/voxlyn-ai.git
cd voxlyn-ai
uv sync
```

### Run the daemon

```bash
systemctl --user enable --now voxlyn-ai
```

### Keyboard shortcut (Gnome)

**Settings → Keyboard → Keyboard Shortcuts → Custom Shortcuts → +**

| Field | Value |
|-------|-------|
| Name | voxlyn-ai |
| Command | ``` uv run --project /home/audeldiaz/voxlyn-ai /home/audeldiaz/voxlyn-ai/trigger.py ``` |
| Shortcut | e.g. `Alt+Z` |

Press the shortcut, speak, hear the response.

## Project structure

```
voxlyn-ai/
├── voice_assistant/           # Python package
│   ├── config.py              # Environment variables and constants
│   ├── audio.py               # Recording, TTS, tone
│   ├── transcription.py       # Whisper STT
│   ├── llm.py                 # OpenCode API interaction
│   ├── commands.py            # In-session voice commands
│   ├── memory.py              # Mempalace persistence
│   └── utils.py               # Markdown cleaning, notifications
├── daemon.py                  # Persistent daemon entry point
├── trigger.py                 # Keyboard-shortcut client
├── tests/                     # pytest suite
│   ├── test_utils.py
│   ├── test_transcription.py
│   └── test_commands.py
├── .opencode/
│   └── skills/                # Agent skills (5 built-in)
│       ├── web-search/
│       ├── control-sistema/
│       ├── recordatorios/
│       ├── notas-rapidas/
│       └── info-sistema/
├── voices/                    # Piper voices (downloaded on first run)
├── opencode_client.py         # OpenCode REST client
├── mempalace_memory.py        # Mempalace integration
├── voxlyn-ai.service          # systemd user unit
├── pyproject.toml
└── README.md
```

## Skills

The OpenCode agent ships with these built-in skills:

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
journalctl --user -u voxlyn-ai -f

# Rotated log files
tail -f ~/.voice-assistant/voxlyn-ai.log
tail -f ~/.voice-assistant/voxlyn-ai.err
```
