#!/usr/bin/env python3
import io
import os
import re
import sys
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
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "float32")
HOTWORDS = os.getenv("HOTWORDS", "DeepSeek,Whisper,solución,asistente,open source,API")

VOICES_DIR = Path(__file__).parent / "voices"
TTS_VOICE = os.getenv("TTS_VOICE", "es_ES-davefx-medium")


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


def main():
    print("[Iniciando servidor OpenCode...]", file=sys.stderr)
    server = OpencodeServer()
    try:
        server.ensure_running()
    except OpencodeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[Cargando Whisper ({WHISPER_MODEL}, {COMPUTE_TYPE})...]", file=sys.stderr)
    whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type=COMPUTE_TYPE)

    print(f"[Cargando voz Piper ({TTS_VOICE})...]", file=sys.stderr)
    piper_voice = get_piper_voice()

    print("[Conectando con OpenCode...]", file=sys.stderr)
    session = OpencodeSession(server, system_prompt=SYSTEM_PROMPT)
    sessions_list = OpencodeSession.list_all(server)
    dev_sessions = [s for s in sessions_list if "voice" in s.get("title", "").lower() or "asistente" in s.get("title", "").lower()]
    if dev_sessions:
        last = max(dev_sessions, key=lambda s: s["time"]["updated"])
        session.session_id = last["id"]
        session._msg_count = 0
        title = last.get("title", "sin título")
        print(f"[Reanudando sesión: {title}]", file=sys.stderr)
    else:
        session.create()
        print("[Nueva sesión creada]", file=sys.stderr)
    print("[Asistente listo. Presiona Ctrl+C para salir]", file=sys.stderr)

    try:
        while True:
            audio = record_audio()
            if len(audio) < SAMPLE_RATE * 0.3:
                print("(silencio)", file=sys.stderr)
                continue

            user_text = transcribe(whisper, audio)
            if not user_text:
                continue

            hotwords_set = set(w.strip().lower() for w in HOTWORDS.split(","))
            user_words = set(w.strip(".,¿?¡! ") for w in user_text.lower().split(","))
            if user_words == hotwords_set or all(
                w in hotwords_set for w in user_words - {"open", "source"}
            ):
                print("(hotwords ignoradas)", file=sys.stderr)
                continue

            cmd_result = handle_session_command(user_text, session, server)
            if cmd_result == "__EXIT__":
                print("[Adiós!]", file=sys.stderr)
                break
            if cmd_result is not None:
                speak(cmd_result, piper_voice)
                continue

            context_results = search_context(user_text)
            context_text = format_context(context_results)
            message = user_text
            if context_text:
                message = f"{context_text}\n\nUser query: {user_text}"

            try:
                ai_response = session.send(message)
            except OpencodeError as e:
                print(f"Error: {e}", file=sys.stderr)
                speak("Hubo un error de conexión con OpenCode.", piper_voice)
                continue

            try:
                save_turn(user_text, clean_markdown(ai_response))
            except Exception as e:
                print(f"[MemPalace save error: {e}]", file=sys.stderr)

            speak(ai_response, piper_voice)
    except KeyboardInterrupt:
        print("\n[Adiós!]", file=sys.stderr)
    finally:
        server.stop()


if __name__ == "__main__":
    main()
