"""Microphone recording, tone generation, and TTS playback."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from voice_assistant.config import (
    KOKORO_LANG_EN,
    KOKORO_LANG_ES,
    KOKORO_VOICE_EN,
    KOKORO_VOICE_ES,
    MAX_RECORD_SECONDS,
    MIN_RECORD_SECONDS,
    SAMPLE_RATE,
    SILENCE_DURATION,
    SILENCE_THRESHOLD,
)

_pipelines: dict[str, object] = {}


def _detect_language(text: str) -> str:
    """Return ``'es'`` or ``'en'`` based on text content."""
    if any(c in text for c in "ñáéíóúü¿¡"):
        return "es"
    es_words = {"el", "la", "los", "las", "un", "una", "y", "e", "o", "u",
                "de", "del", "en", "por", "para", "con", "sin", "es", "son",
                "que", "como", "muy", "más", "pero", "todo", "este", "esta",
                "eres", "tiene", "puede", "hace", "dice", "sabe", "quiere",
                "gracias", "hola", "adiós", "adios", "se", "le", "lo", "la"}
    en_words = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
                "of", "with", "is", "are", "was", "were", "it", "its", "this",
                "that", "these", "those", "very", "more", "but", "not", "you",
                "your", "will", "can", "have", "has", "had", "do", "does", "did"}
    words = set(text.lower().split())
    es_score = len(words & es_words)
    en_score = len(words & en_words)
    if es_score > en_score:
        return "es"
    return "en"


def _get_pipeline(lang: str):
    """Return a cached Kokoro pipeline for the given language code."""
    if lang not in _pipelines:
        from kokoro import KPipeline
        _pipelines[lang] = KPipeline(lang_code=lang)
    return _pipelines[lang]


def get_piper_voice():
    """Initialize Kokoro pipelines at startup (alias for daemon compat)."""
    _get_pipeline(KOKORO_LANG_EN)
    _get_pipeline(KOKORO_LANG_ES)


def record_audio() -> np.ndarray:
    """Record audio from the microphone until silence is detected.

    Uses VAD-like silence detection: recording stops after 2 seconds of
    silence, or after a minimum of 2 seconds and a maximum of 60 seconds.
    Leading and trailing silence is trimmed from the returned array.
    """
    audio_chunks: list[np.ndarray] = []
    silent_chunks = 0
    max_silent = int(SILENCE_DURATION * SAMPLE_RATE / 1024)
    min_chunks = int(MIN_RECORD_SECONDS * SAMPLE_RATE / 1024)
    max_chunks = int(MAX_RECORD_SECONDS * SAMPLE_RATE / 1024)

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, blocksize=1024, dtype="float32"
    )
    print("[Listening...]", file=sys.stderr)
    with stream:
        while len(audio_chunks) < max_chunks:
            chunk, _ = stream.read(1024)
            audio_chunks.append(chunk)
            if np.max(np.abs(chunk)) < SILENCE_THRESHOLD:
                silent_chunks += 1
            else:
                silent_chunks = 0
            elapsed = len(audio_chunks) * 1024 / SAMPLE_RATE
            print(f"\r[Recording... {elapsed:.0f}s]", file=sys.stderr, end="")
            if len(audio_chunks) > min_chunks and silent_chunks > max_silent:
                break

    print("\r[Transcribing...        ]", file=sys.stderr)
    audio = np.concatenate(audio_chunks).flatten()
    indices = np.where(np.abs(audio) > SILENCE_THRESHOLD)[0]
    if len(indices) > 0:
        audio = audio[indices[0] : indices[-1] + 1]
    return audio


def speak(text: str, user_text: str = "") -> None:
    """Synthesize *text* with Kokoro and play it through the speakers.

    Selects language based on *user_text* (the LLM mirrors the user's
    language per system prompt). Falls back to detecting from *text*.

    If the response contains a Markdown code block the code is sent to a
    desktop notification instead of being read aloud.
    """
    from voice_assistant.utils import clean_markdown, has_code_block, notify, strip_code_blocks

    if has_code_block(text):
        prose = strip_code_blocks(text)
        summary = prose if len(prose) > 10 else "La respuesta incluye código."
        notify("Asistente - Respuesta con código", text)
        tts_text = summary
        print(f"Asistente (notif.): {summary}", file=sys.stderr)
    else:
        tts_text = text

    tts_text = clean_markdown(tts_text)
    print(f"Asistente: {tts_text}", file=sys.stderr)

    source = tts_text or user_text
    lang = _detect_language(source)
    if lang == "es":
        pipeline = _get_pipeline(KOKORO_LANG_ES)
        voice = KOKORO_VOICE_ES
    else:
        pipeline = _get_pipeline(KOKORO_LANG_EN)
        voice = KOKORO_VOICE_EN

    for result in pipeline(tts_text, voice=voice):
        sd.play(result.audio, 24000)
        sd.wait()


def play_listen_tone() -> None:
    """Play a short beep to indicate the assistant is listening."""
    duration = 0.2
    freq = 440
    sr = 22050
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = (np.sin(2 * np.pi * freq * t) * 0.5).astype(np.float32)
    for cmd in ("paplay", "aplay"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, tone, sr)
            subprocess.run([cmd, f.name], capture_output=True, timeout=3)
            os.unlink(f.name)
            return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            try:
                os.unlink(f.name)
            except OSError:
                pass
    sd.play(tone, sr)
    sd.wait()
