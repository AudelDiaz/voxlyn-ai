"""Application-wide configuration and environment variables."""

import os

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

# --- Kokoro TTS ---
KOKORO_LANG_EN: str = "a"  # American English
KOKORO_LANG_ES: str = "e"  # Spanish
KOKORO_VOICE_EN: str = os.getenv("KOKORO_VOICE_EN", "af_heart")
KOKORO_VOICE_ES: str = os.getenv("KOKORO_VOICE_ES", "ef_dora")

# --- OpenCode ---
OPENCODE_URL: str = os.getenv("OPENCODE_URL", "http://localhost:4096")

# --- OpenCode variant (reasoning effort) ---
VARIANT: str = os.getenv("VARIANT", "")

VARIANT_NAMES: dict[str, str] = {
    "": "default — sin razonamiento extra, respuesta inmediata",
    "low": "baja — respuestas rápidas, mínimo esfuerzo",
    "medium": "media — razonamiento balanceado, uso general",
    "high": "alta — razonamiento profundo, análisis complejo",
    "max": "máxima — esfuerzo máximo, tareas muy complejas",
}

AUTO_VARIANT_KEYWORDS: tuple[str, ...] = (
    "analiza",
    "explica detalladamente", "explícame",
    "código", "codigo", "programa", "implementa",
    "depura", "debug", "error",
    "compara", "comparación",
    "por qué", "por que", "cómo funciona", "como funciona",
    "arquitectura", "diseña", "diseñar",
    "optimiza", "refactoriza",
    "diagnostica", "investiga",
)

# --- System prompt sent to the LLM ---
SYSTEM_PROMPT: str = os.getenv(
    "SYSTEM_PROMPT",
    (
        "You are voxlyn, a helpful AI voice assistant. Respond concisely in 1-3 sentences "
        "in the same language as the user. Do not use markdown formatting.\n\n"
        "You have the following skills available:\n"
        "- web-search: Search the web for current events, facts, and information.\n"
        "- system-control: Adjust system volume, brightness, open applications, take screenshots.\n"
        "- reminders: Set and manage reminders and timers.\n"
        "- quick-notes: Save quick notes to a file.\n"
        "- system-info: Report system diagnostics (RAM, CPU, disk, uptime, updates).\n"
    ),
)
