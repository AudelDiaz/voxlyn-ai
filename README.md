# voxlyn-ai

Hands-free AI voice assistant for Linux. Press a key, speak, get an AI
voice response — entirely local.

**Whisper** → STT · **OpenCode** → LLM agent · **Piper** → TTS

Inspired by [Nate Gentile's CachyOS + Omarchy setup video](https://youtu.be/b6uQTR7E9qg).

## Architecture

```
Trigger (keyboard shortcut)
  │  sends "record" via Unix socket
  ▼
Daemon (persistent systemd service)
  ├── Whisper (faster-whisper, int8)  ← speech-to-text
  ├── OpenCode agent                  ← LLM with skills + memory
  ├── Piper TTS                       ← text-to-speech
  └── JSON memory                     ← conversational history
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

### 2. Link the systemd service

```bash
mkdir -p ~/.config/systemd/user
ln -s ~/voxlyn-ai/voxlyn-ai.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now voxlyn-ai
```

The daemon will start automatically on every login.

### 3. Set up the keyboard shortcut (Gnome)

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
├── mempalace_memory.py        # JSON-file conversation history
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
| `control-sistema` | Volume, brightness, apps, screenshots |
| `recordatorios` | Persistent reminders with systemd timers |
| `notas-rapidas` | Voice notes saved to `~/Notas/` |
| `info-sistema` | System diagnostics (RAM, CPU, disk, updates) |

To add your own skill, create a directory under `.opencode/skills/` with a
`SKILL.md` (see [OpenCode skill docs](https://opencode.ai/docs/skills/)).

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

## Uninstall

```bash
systemctl --user stop voxlyn-ai
systemctl --user disable voxlyn-ai
rm ~/.config/systemd/user/voxlyn-ai.service
rm -rf ~/voxlyn-ai ~/.voice-assistant
```
