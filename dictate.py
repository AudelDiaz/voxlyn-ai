#!/usr/bin/env python3
"""
Voice dictation: speaks → types into focused window.

Usage:
  1. Install deps:   pip install sounddevice numpy openai-whisper
  2. Install wtype:  sudo pacman -S wtype
  3. Configure GNOME shortcut → python /path/to/dictate.py

The script records, transcribes with Whisper, and types the text
into whatever window is focused using wtype (Wayland) or xdotool (X11).
"""
import os
import shutil
import subprocess
import sys

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.02
SILENCE_DURATION = 2.0
MIN_RECORD_SECONDS = 3
MAX_RECORD_SECONDS = 60
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_LANG = os.getenv("WHISPER_LANG", "")
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "float32")
HOTWORDS = os.getenv("HOTWORDS", "DeepSeek,pyttsx3,Whisper,solución,asistente,open source,API,debug")


def detect_display_server():
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return None


def paste_text(text: str):
    subprocess.run(["wl-copy"], input=text.encode(), check=True)
    if shutil.which("ydotool"):
        ret = subprocess.run(["ydotool", "type", "-e", "0", text], capture_output=True)
        if ret.returncode == 0:
            return
    print("\n[Texto copiado al portapapeles — presiona Ctrl+V para pegar]", file=sys.stderr)


def type_text(text: str):
    ds = detect_display_server()
    if ds == "wayland":
        paste_text(text)
    elif ds == "x11":
        subprocess.run(["xdotool", "type", "--", text], check=True)
    else:
        print("No display server detected", file=sys.stderr)
        sys.exit(1)


def record_audio() -> np.ndarray:
    audio_chunks = []
    silent_chunks = 0
    max_silent = int(SILENCE_DURATION * SAMPLE_RATE / 1024)
    min_chunks = int(MIN_RECORD_SECONDS * SAMPLE_RATE / 1024)
    max_chunks = int(MAX_RECORD_SECONDS * SAMPLE_RATE / 1024)

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, blocksize=1024, dtype="float32"
    )
    print("[Escuchando... Habla cuando quieras]", file=sys.stderr)
    with stream:
        while len(audio_chunks) < max_chunks:
            chunk, _ = stream.read(1024)
            audio_chunks.append(chunk)
            if np.max(np.abs(chunk)) < SILENCE_THRESHOLD:
                silent_chunks += 1
            else:
                silent_chunks = 0
            elapsed = len(audio_chunks) * 1024 / SAMPLE_RATE
            print(f"\r[Grabando... {elapsed:.0f}s]", file=sys.stderr, end="")
            if len(audio_chunks) > min_chunks and silent_chunks > max_silent:
                break

    print("\r[Transcribiendo...        ]", file=sys.stderr, end="")
    audio = np.concatenate(audio_chunks).flatten()
    indices = np.where(np.abs(audio) > SILENCE_THRESHOLD)[0]
    if len(indices) > 0:
        audio = audio[indices[0] : indices[-1] + 1]
    return audio


def main():
    print(f"Loading faster-whisper model ({WHISPER_MODEL}, compute={COMPUTE_TYPE})...", file=sys.stderr)
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type=COMPUTE_TYPE)
    audio = record_audio()
    if len(audio) < SAMPLE_RATE * 0.3:  # menos de 0.3s = silencio
        sys.exit(0)
    # Normalizar volumen y convertir a float32
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.95
    audio = audio.astype(np.float32)
    print(f"  Audio: {len(audio)} samples, {len(audio)/SAMPLE_RATE:.1f}s, max={max_val:.4f}", file=sys.stderr)
    lang = WHISPER_LANG if WHISPER_LANG else None
    segments, info = model.transcribe(
        audio,
        language=lang,
        beam_size=5,
        vad_filter=False,
        initial_prompt=f"DeepSeek, pyttsx3, Whisper, inteligencia artificial, tecnología, generación, síntesis, integración, solucion, asistente, open source, {HOTWORDS}",
    )
    text = " ".join(seg.text for seg in segments).strip()
    if text:
        type_text(text)


if __name__ == "__main__":
    main()
