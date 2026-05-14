# Voice Assistant CLI

Two modes:

| Mode | Script | STT | Use case |
|------|--------|-----|----------|
| Built-in mic | `assistant.py` | Whisper (local) | Standalone voice assistant |
| Vibe Typer | `assistant_vibe.py` | Vibe Typer (system-wide) | Dictate into any app, get AI voice replies |

## Setup

```bash
pip install openai pyttsx3 sounddevice numpy openai-whisper
```

For local LLM mode (optional):
```bash
pip install transformers torch
```

## Mode 1: Built-in Mic (assistant.py)

Uses local Whisper for speech-to-text. Speak directly into your mic.

```bash
export DEEPSEEK_API_KEY="sk-..."
python assistant.py
```

## Mode 2: Vibe Typer (assistant_vibe.py)

Uses [Vibe Typer](https://vibetyper.com) (desktop app) for speech-to-text. Press a hotkey, speak, and text appears in the terminal.

### Setup Vibe Typer on Linux

```bash
wget -O VibeTyper.AppImage https://vibetyper.com/download/linux
chmod +x VibeTyper.AppImage
./VibeTyper.AppImage
```

Default hotkey: **Alt+Space**

### Run the script

```bash
export DEEPSEEK_API_KEY="sk-..."
python assistant_vibe.py
```

**Workflow:**
1. Script waits for text input
2. Press **Alt+Space** (Vibe Typer hotkey) and speak your question
3. Vibe Typer types the transcription into the terminal
4. Script sends it to DeepSeek and speaks the response via TTS

## Mode 3: Dictation (dictate.py)

Speak → Whisper transcribes → types into the focused window (like Vibe Typer / Handy).

Requires `wtype` (Wayland) or `xdotool` (X11):

```bash
# CachyOS / Arch
sudo pacman -S wtype
# or for X11
sudo pacman -S xdotool

pip install sounddevice numpy openai-whisper
```

### GNOME shortcut setup (Wayland workaround)

1. `Settings → Keyboard → Keyboard Shortcuts → Custom Shortcuts`
2. Add new shortcut
   - **Name:** `Dictate`
   - **Command:** `python /path/to/dictate.py`
   - **Shortcut:** `Ctrl+Super+Space` (o el que prefieras)
3. Ahora presiona ese atajo, habla, y el texto aparecerá donde tengas el cursor.

### Integrar con DeepSeek (asistente + dictado)

El script `dictate.py` solo dicta texto. Si quieres que el texto se envíe al asistente, combínalo con `assistant_vibe.py`:

1. Enfoca la terminal donde corre `assistant_vibe.py`
2. Presiona el atajo de dictado → habla → Whisper transcribe → `wtype` escribe en la terminal
3. `assistant_vibe.py` recibe el texto, llama a DeepSeek y responde por voz

## DeepSeek API

Free tier available at https://platform.deepseek.com
