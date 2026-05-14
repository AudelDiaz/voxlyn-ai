"""Microphone recording, tone generation, and TTS playback."""

import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import piper
import piper.download_voices
import sounddevice as sd
import soundfile as sf

from voice_assistant.config import (
    SAMPLE_RATE,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    MIN_RECORD_SECONDS,
    MAX_RECORD_SECONDS,
    TTS_VOICE,
    VOICES_DIR,
)


def get_piper_voice(name: str = TTS_VOICE) -> piper.PiperVoice:
    """Load (or download and load) a Piper TTS voice model."""
    model_path = VOICES_DIR / f"{name}.onnx"
    if not model_path.exists():
        print(f"Downloading voice {name}...", file=sys.stderr)
        piper.download_voices.download_voice(name, download_dir=VOICES_DIR)
    return piper.PiperVoice.load(model_path)


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


def speak(text: str, voice: piper.PiperVoice) -> None:
    """Synthesize *text* with Piper and play it through the speakers.

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

    buf = io.BytesIO()
    with sf.SoundFile(
        buf,
        mode="w",
        samplerate=voice.config.sample_rate,
        channels=1,
        format="WAV",
        subtype="PCM_16",
    ) as wav:
        for chunk in voice.synthesize(tts_text):
            wav.write(chunk.audio_int16_array)
    buf.seek(0)
    data, sr = sf.read(buf)
    sd.play(data, sr)
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
