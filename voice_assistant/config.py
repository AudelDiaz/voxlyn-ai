"""Application-wide configuration and environment variables."""

import os
from pathlib import Path

# --- Audio recording ---
SAMPLE_RATE: int = 16000
SILENCE_THRESHOLD: float = 0.02
SILENCE_DURATION: float = 2.0
MIN_RECORD_SECONDS: int = 2
MAX_RECORD_SECONDS: int = 60

# --- Whisper STT ---
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "small")
COMPUTE_TYPE: str = os.getenv("COMPUTE_TYPE", "int8")
WHISPER_LANG: str = os.getenv("WHISPER_LANG", "")
HOTWORDS: str = os.getenv(
    "HOTWORDS", "DeepSeek,Whisper,solución,asistente,open source,API"
)

# --- Piper TTS ---
VOICES_DIR: Path = Path(__file__).resolve().parent.parent / "voices"
TTS_VOICE: str = os.getenv("TTS_VOICE", "es_ES-davefx-medium")

# --- OpenCode ---
OPENCODE_URL: str = os.getenv("OPENCODE_URL", "http://localhost:4096")

# --- System prompt sent to the LLM ---
SYSTEM_PROMPT: str = os.getenv(
    "SYSTEM_PROMPT",
    (
        "You are voxlyn, a helpful AI voice assistant. Respond concisely in 1-3 sentences "
        "in the same language as the user. Do not use markdown formatting.\n\n"
        "You have the following skills available:\n"
        "- web-search: Search the web for current events, facts, and information.\n"
        "- control-sistema: Adjust system volume, brightness, open applications, take screenshots.\n"
        "- recordatorios: Set and manage reminders and timers.\n"
        "- notas-rapidas: Save quick notes to a file.\n"
        "- info-sistema: Report system diagnostics (RAM, CPU, disk, uptime, updates).\n"
    ),
)
