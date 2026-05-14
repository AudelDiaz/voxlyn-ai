#!/usr/bin/env python3
import io
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import piper
import piper.download_voices
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel

from opencode_client import OpencodeServer, OpencodeSession, OpencodeError
from mempalace_memory import save_turn, search_context, format_context

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.02
SILENCE_DURATION = 2.0
MIN_RECORD_SECONDS = 2
MAX_RECORD_SECONDS = 60

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a helpful voice assistant. Respond concisely in 1-3 sentences in the same language as the user. Do not use markdown formatting like bold, italic, code blocks, headers, or lists.",
)

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_LANG = os.getenv("WHISPER_LANG", "")
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8")
HOTWORDS = os.getenv("HOTWORDS", "DeepSeek,Whisper,solución,asistente,open source,API")

VOICES_DIR = Path(__file__).parent / "voices"
TTS_VOICE = os.getenv("TTS_VOICE", "es_ES-davefx-medium")


_t0: float = 0.0


def mark(label: str):
    global _t0
    now = time.perf_counter()
    if _t0:
        print(f"[{now - _t0:.2f}s] {label}", file=sys.stderr)
    else:
        print(f"[0.00s] {label}", file=sys.stderr)
    _t0 = now


def get_piper_voice(name: str = TTS_VOICE) -> piper.PiperVoice:
    model_path = VOICES_DIR / f"{name}.onnx"
    if not model_path.exists():
        print(f"Downloading voice {name}...", file=sys.stderr)
        piper.download_voices.download_voice(name, download_dir=VOICES_DIR)
    return piper.PiperVoice.load(model_path)


def record_audio() -> np.ndarray:
    audio_chunks = []
    silent_chunks = 0
    max_silent = int(SILENCE_DURATION * SAMPLE_RATE / 1024)
    min_chunks = int(MIN_RECORD_SECONDS * SAMPLE_RATE / 1024)
    max_chunks = int(MAX_RECORD_SECONDS * SAMPLE_RATE / 1024)

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, blocksize=1024, dtype="float32"
    )
    print("[Escuchando...]", file=sys.stderr)
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

    print("\r[Transcribiendo...        ]", file=sys.stderr)
    audio = np.concatenate(audio_chunks).flatten()
    indices = np.where(np.abs(audio) > SILENCE_THRESHOLD)[0]
    if len(indices) > 0:
        audio = audio[indices[0] : indices[-1] + 1]
    return audio


def transcribe(model: WhisperModel, audio: np.ndarray) -> str:
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.95
    audio = audio.astype(np.float32)

    lang = WHISPER_LANG if WHISPER_LANG else None
    segments, info = model.transcribe(
        audio,
        language=lang,
        beam_size=5,
        vad_filter=False,
        initial_prompt="DeepSeek, Whisper, inteligencia artificial, solucion, asistente, "
        + HOTWORDS,
    )
    text = " ".join(seg.text for seg in segments).strip()
    print(f"\nTú: {text}", file=sys.stderr)
    return text


def handle_session_command(
    text: str, session: OpencodeSession, server: OpencodeServer
) -> str | None:
    t = text.lower().strip()

    if t in ("nueva conversacion", "nuevo chat", "reiniciar", "nueva conversación"):
        session.delete()
        session.create()
        return "Listo, nueva conversación creada."

    if t in ("lista sesiones", "listar sesiones", "muestra las sesiones"):
        sessions = OpencodeSession.list_all(server)
        if not sessions:
            return "No tienes sesiones guardadas."
        recent = sessions[-5:]
        titles = [s.get("title", "sin título") for s in recent]
        return "Tus sesiones: " + ", ".join(titles)

    if t.startswith("carga ") or t.startswith("abre "):
        query = t
        for prefix in ("carga ", "abre "):
            if t.startswith(prefix):
                query = t[len(prefix) :].strip()
                break
        found = OpencodeSession.find_by_title(server, query)
        if found:
            session.session_id = found["id"]
            session._msg_count = 0
            title = found.get("title", "sin título")
            return f"Sesión '{title}' cargada."
        return f"No encontré una sesión con ese nombre."

    if t.startswith("guarda como "):
        title = t[len("guarda como ") :].strip()
        session.rename(title)
        return f"Sesión guardada como '{title}'."

    if t in ("borra esta sesion", "borra esta sesión", "elimina sesion", "elimina sesión"):
        session.delete()
        session.create()
        return "Sesión eliminada. Nueva sesión creada."

    if any(palabra in t for palabra in ("salir", "exit", "quit", "adiós", "adios")):
        return "__EXIT__"

    return None


def clean_markdown(text: str) -> str:
    text = re.sub(r"```.+?```", "", text, flags=re.DOTALL)
    text = re.sub(r"``(.+?)``", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+[\.\)]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-_*]{3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def speak(text: str, voice: piper.PiperVoice):
    text = clean_markdown(text)
    print(f"Asistente: {text}", file=sys.stderr)
    buf = io.BytesIO()
    with sf.SoundFile(
        buf,
        mode="w",
        samplerate=voice.config.sample_rate,
        channels=1,
        format="WAV",
        subtype="PCM_16",
    ) as wav:
        for chunk in voice.synthesize(text):
            wav.write(chunk.audio_int16_array)
    buf.seek(0)
    data, sr = sf.read(buf)
    sd.play(data, sr)
    sd.wait()


def get_response(
    text: str,
    server: OpencodeServer | None = None,
    session: OpencodeSession | None = None,
) -> str:
    if server is None:
        server = OpencodeServer()
        server.ensure_running()
    if session is None:
        session = OpencodeSession(server, system_prompt=SYSTEM_PROMPT)

    cmd_result = handle_session_command(text, session, server)
    if cmd_result is not None:
        if cmd_result == "__EXIT__":
            sys.exit(0)
        return cmd_result

    mark("Buscando contexto en mempalace...")
    context = format_context(search_context(text))
    mark(f"Contexto: {'encontrado' if context else 'vacío'}")
    full_text = f"{context}\n\n{text}" if context else text

    mark("Enviando a LLM...")
    response = session.send(full_text)
    mark("Respuesta recibida")

    mark("Guardando en mempalace...")
    save_turn(text, response)
    mark("Guardado")
    return response


def play_listen_tone():
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


def main():
    global _t0
    _t0 = 0.0

    mark("Cargando Whisper...")
    print(f"[Cargando Whisper ({WHISPER_MODEL}, {COMPUTE_TYPE})...]", file=sys.stderr)
    whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type=COMPUTE_TYPE)
    mark("Cargando voz Piper...")
    print(f"[Cargando voz Piper ({TTS_VOICE})...]", file=sys.stderr)
    piper_voice = get_piper_voice()

    mark("Tono de inicio")
    play_listen_tone()

    mark("Grabando audio...")
    audio = record_audio()
    if len(audio) < SAMPLE_RATE * 0.3:
        sys.exit(0)

    server = OpencodeServer()
    server.ensure_running()
    session = OpencodeSession(server, system_prompt=SYSTEM_PROMPT)

    mark("Transcribiendo...")
    user_text = transcribe(whisper, audio)
    if not user_text:
        sys.exit(0)

    ai_response = get_response(user_text, server, session)

    mark("Sintetizando y reproduciendo TTS...")
    speak(ai_response, piper_voice)
    mark("Listo")


if __name__ == "__main__":
    main()
