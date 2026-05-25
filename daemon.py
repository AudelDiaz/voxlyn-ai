#!/usr/bin/env python3
"""voxlyn-ai daemon: persistent voice assistant service.

Listens on a Unix socket for "record" commands, processes the full
voice pipeline (STT -> LLM -> TTS), and reloads the socket immediately.
"""

import logging
import logging.handlers
import os
import secrets
import signal
import socket
import sys
import threading
import time
import warnings
from pathlib import Path

import numpy as np
import sounddevice as sd

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

warnings.filterwarnings("ignore", message="dropout option adds dropout.*")
warnings.filterwarnings("ignore", message="`torch.nn.utils.weight_norm` is deprecated.*")

from faster_whisper import WhisperModel

from opencode_client import OpencodeError, OpencodeServer, OpencodeSession
from voice_assistant.audio import (
    play_listen_tone,
    play_process_tone,
    play_stop_tone,
    prewarm_pipelines,
    speak,
)
from voice_assistant.utils import has_code_block, notify, _run_in_terminal
from voice_assistant.config import (
    COMPUTE_TYPE,
    FOLLOWUP_MAX_RETRIES,
    FOLLOWUP_NEGATIVE,
    FOLLOWUP_SILENCE_DURATION,
    FOLLOWUP_SILENT_AFFIRMATIVE,
    FOLLOWUP_TIMEOUT,
    LONG_RESPONSE_THRESHOLD,
    SAMPLE_RATE,
    SILENCE_THRESHOLD,
    WHISPER_MODEL,
    get_system_prompt,
)
from voice_assistant.llm import get_response, shutdown_memory_executor
from voice_assistant.local_cli import run_local
from voice_assistant.router import route
from voice_assistant.transcription import transcribe

DATA_DIR = Path.home() / ".voice-assistant"
SOCKET_PATH = DATA_DIR / "daemon.sock"
LOG_PATH = DATA_DIR / "voxlyn-ai.log"
ERR_PATH = DATA_DIR / "voxlyn-ai.err"

_busy: bool = False
_busy_lock: threading.Lock = threading.Lock()
_cancel_playback: threading.Event = threading.Event()
_capturing: bool = False
_capture_chunks: list[np.ndarray] = []
_capture_stop: threading.Event = threading.Event()
_shutdown: bool = False
_server: OpencodeServer | None = None


def _capture_worker(chunks: list[np.ndarray], stop_event: threading.Event) -> None:
    """Record audio chunks in background until *stop_event* is set."""
    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, blocksize=1024, dtype="float32"
    ) as stream:
        print("[Recording...]", file=sys.stderr)
        while not stop_event.is_set():
            chunk, _ = stream.read(1024)
            chunks.append(chunk)
    print("\r[Processing...         ]", file=sys.stderr)


def _has_question(text: str) -> bool:
    """Return True if the text contains a question mark anywhere."""
    return "?" in text


def _quick_listen(timeout: float) -> np.ndarray | None:
    """Record audio for a follow-up reply (shorter silence, shorter timeout).

    Returns trimmed audio if speech was detected, or None on timeout/cancel.
    Checks ``_cancel_playback`` and ``_capture_stop`` during recording.
    """
    chunks: list[np.ndarray] = []
    silent_chunks = 0
    max_silent = int(FOLLOWUP_SILENCE_DURATION * SAMPLE_RATE / 1024)
    max_chunks = int(timeout * SAMPLE_RATE / 1024)

    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, blocksize=1024, dtype="float32"
    ) as stream:
        while len(chunks) < max_chunks:
            if _cancel_playback.is_set():
                log.info("Quick-listen: cancelled by user")
                return None
            if _capture_stop.is_set():
                log.info("Quick-listen: cancelled by trigger")
                return None
            chunk, _ = stream.read(1024)
            chunks.append(chunk)
            if np.max(np.abs(chunk)) < SILENCE_THRESHOLD:
                silent_chunks += 1
            else:
                silent_chunks = 0
            if silent_chunks > max_silent:
                elapsed = len(chunks) * 1024 / SAMPLE_RATE
                log.info(f"Quick-listen: silence detected after {elapsed:.1f}s")
                break
    audio = np.concatenate(chunks).flatten()
    indices = np.where(np.abs(audio) > SILENCE_THRESHOLD)[0]
    elapsed = len(audio) / SAMPLE_RATE
    if len(indices) == 0:
        log.info(f"Quick-listen: {elapsed:.1f}s captured, all silence — no speech")
        return None
    speech_len = (indices[-1] - indices[0]) / SAMPLE_RATE
    log.info(f"Quick-listen: {elapsed:.1f}s captured, {speech_len:.1f}s speech after trim")
    return audio[indices[0] : indices[-1] + 1]


def setup_logging() -> logging.Logger:
    """Configure rotating file handlers and stderr for the daemon."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    main_handler = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=10_000_000, backupCount=3
    )
    main_handler.setFormatter(formatter)
    main_handler.setLevel(logging.INFO)

    err_handler = logging.handlers.RotatingFileHandler(
        ERR_PATH, maxBytes=10_000_000, backupCount=3
    )
    err_handler.setFormatter(formatter)
    err_handler.setLevel(logging.ERROR)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(main_handler)
    root.addHandler(err_handler)
    root.addHandler(stderr_handler)

    # Suppress ChromaDB HNSW segment corruption warnings (auto-quarantined gracefully)
    class _ChromaFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return "Quarantined corrupt HNSW" not in record.getMessage()
    chroma_logger = logging.getLogger("chromadb")
    chroma_logger.addFilter(_ChromaFilter())

    return logging.getLogger(__name__)


log: logging.Logger = setup_logging()


def cleanup() -> None:
    """Clean up the socket file, stop capture, stop server, and flag shutdown."""
    global _shutdown
    _shutdown = True
    _capture_stop.set()
    _cancel_playback.set()
    shutdown_memory_executor()
    try:
        SOCKET_PATH.unlink()
    except OSError:
        pass
    if _server:
        _server.stop()
    log.info("Daemon stopped")


def handle_signal(signum: int, frame: object) -> None:
    """Graceful shutdown on SIGTERM / SIGINT."""
    log.info(f"Received signal {signum}, shutting down...")
    cleanup()
    sys.exit(0)


def process_pipeline(
    whisper: WhisperModel,
    server: OpencodeServer,
    session: OpencodeSession,
    audio: np.ndarray,
) -> None:
    """Run one full voice cycle: transcribe captured audio → LLM → speak."""
    global _busy
    try:
        log.info("Pipeline started")

        if len(audio) < SAMPLE_RATE * 0.3:
            log.info("Audio too short, discarding")
            return

        user_text = transcribe(whisper, audio)
        if not user_text:
            log.info("No speech detected")
            print("[No speech detected]", file=sys.stderr)
            return

        log.info(f"User: {user_text}")
        play_process_tone()

        if route(user_text) == "local":
            ai_response = run_local(user_text)
        else:
            ai_response = get_response(user_text, server, session)
        log.info(f"Assistant: {ai_response}")

        if ai_response == "__LOGS__":
            notify("Voxlyn", "Opening logs…")
            _run_in_terminal(["sh", "-c", "journalctl --user -u voxlyn-ai -f"])
            speak("Opening logs.", cancel_event=_cancel_playback)
            return

        if not has_code_block(ai_response) and len(ai_response) <= LONG_RESPONSE_THRESHOLD:
            preview = ai_response[:120].replace("\n", " ")
            notify("Voxlyn", f"{preview}{"…" if len(ai_response) > 120 else ""}")

        if _cancel_playback.is_set():
            log.info("Pipeline cancelled before speak")
            return

        with _busy_lock:
            _busy = True
        speak(ai_response, user_text=user_text, cancel_event=_cancel_playback)

        if _has_question(ai_response) and not _capture_stop.is_set():
            log.info("Follow-up: entering AWAITING")
            retries = 0
            affirm_retries = 0
            while not _cancel_playback.is_set() and not _capture_stop.is_set():
                with _busy_lock:
                    _busy = True
                notify("Voxlyn", "Listening…")
                time.sleep(0.3)
                fu_audio = _quick_listen(FOLLOWUP_TIMEOUT)
                if fu_audio is None or len(fu_audio) < SAMPLE_RATE * 0.3:
                    duration = len(fu_audio) / SAMPLE_RATE if fu_audio is not None else 0
                    log.info(f"Follow-up: audio too short ({duration:.1f}s), exiting loop")
                    break
                fu_text = transcribe(whisper, fu_audio)
                log.info(f"Follow-up transcribed: '{fu_text}'")
                if not fu_text:
                    retries += 1
                    if retries >= FOLLOWUP_MAX_RETRIES:
                        log.info("Follow-up: max noise retries reached")
                        break
                    continue
                retries = 0
                lower = fu_text.lower()
                if lower in FOLLOWUP_NEGATIVE:
                    log.info("Follow-up: negative keyword matched, returning to IDLE")
                    break
                if lower in FOLLOWUP_SILENT_AFFIRMATIVE:
                    affirm_retries += 1
                    if affirm_retries >= FOLLOWUP_MAX_RETRIES:
                        log.info("Follow-up: max affirmative retries reached")
                        break
                    log.info("Follow-up: silent affirmative, prompting again")
                    speak("¿Alguna otra pregunta?")
                    continue
                affirm_retries = 0
                log.info(f"Follow-up: routing '{fu_text}'")
                play_process_tone()
                if route(fu_text) == "local":
                    fu_response = run_local(fu_text)
                else:
                    fu_response = get_response(fu_text, server, session)
                log.info(f"Follow-up assistant: {fu_response}")
                if fu_response == "__LOGS__":
                    notify("Voxlyn", "Opening logs…")
                    _run_in_terminal(["sh", "-c", "journalctl --user -u voxlyn-ai -f"])
                    speak("Opening logs.", cancel_event=_cancel_playback)
                    break
                if not has_code_block(fu_response) and len(fu_response) <= LONG_RESPONSE_THRESHOLD:
                    preview = fu_response[:120].replace("\n", " ")
                    notify("Voxlyn", f"{preview}{"…" if len(fu_response) > 120 else ""}")
                speak(fu_response, user_text=fu_text, cancel_event=_cancel_playback)
                if not _has_question(fu_response):
                    log.info("Follow-up: response has no question, exiting loop")
                    break
        log.info("Pipeline finished")
    except Exception:
        log.exception("Pipeline error")
    finally:
        with _busy_lock:
            _busy = False


def handle_client(
    conn: socket.socket,
    whisper: WhisperModel,
    server: OpencodeServer,
    session: OpencodeSession,
) -> None:
    """Handle a trigger command: start capture, stop capture, or interrupt."""
    global _busy, _capturing
    try:
        data = conn.recv(1024).decode().strip()

        if data == "cancel":
            with _busy_lock:
                _cancel_playback.set()
                _capture_stop.set()
                _capturing = False
                _capture_chunks.clear()
            conn.sendall(b"ok\n")
            log.info("Cancel signal received")
            conn.close()
            return

        if data != "record":
            conn.sendall(b"error: unknown command\n")
            return

        with _busy_lock:
            if _busy:
                # Currently processing — stop playback
                _cancel_playback.set()
                _capture_stop.set()
                _capturing = False
                conn.sendall(b"ok\n")
                log.info("Trigger interrupted processing")
                conn.close()
                return

            if _capturing:
                # Stop capture and process
                _capture_stop.set()
                _capturing = False
                _busy = True
                _cancel_playback.clear()
                conn.sendall(b"ok\n")
                conn.close()

                play_stop_tone()
                print("[Stopped]", file=sys.stderr)
                log.info("Capture stopped")

                if not _capture_chunks:
                    log.warning("Empty capture, discarding")
                    _busy = False
                    return
                audio = np.concatenate(_capture_chunks).flatten()
                _capture_chunks.clear()
                _capture_stop.clear()
                notify("Voxlyn", "Processing…")
                log.info(f"Captured {len(audio) / SAMPLE_RATE:.1f}s of audio")

                threading.Thread(
                    target=process_pipeline,
                    args=(whisper, server, session, audio),
                    daemon=True,
                ).start()
                return

            # Start capture
            _capturing = True
            _cancel_playback.set()
            _capture_stop.clear()
            _capture_chunks.clear()
            conn.sendall(b"ok\n")
            play_listen_tone()
            notify("Voxlyn", "Listening…")
            conn.close()

            threading.Thread(
                target=_capture_worker,
                args=(_capture_chunks, _capture_stop),
                daemon=True,
            ).start()
            log.info("Capture started")
    except Exception:
        log.exception("Error handling client")


def main() -> None:
    """Daemon entry point: load models, bind socket, accept commands."""
    global _server

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    log.info(f"Loading Whisper ({WHISPER_MODEL}, {COMPUTE_TYPE})...")
    whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type=COMPUTE_TYPE)
    log.info("Whisper loaded")

    log.info("Loading Kokoro TTS pipelines...")
    prewarm_pipelines()
    log.info("Kokoro loaded")

    if "OPENCODE_SERVER_PASSWORD" not in os.environ:
        os.environ["OPENCODE_SERVER_PASSWORD"] = secrets.token_urlsafe(32)
    if "OPENCODE_SERVER_USERNAME" not in os.environ:
        os.environ["OPENCODE_SERVER_USERNAME"] = "voxlyn"

    log.info("Connecting to OpenCode...")
    server = OpencodeServer()
    _server = server
    try:
        server.ensure_running()
    except OpencodeError as e:
        log.critical(f"Failed to connect to OpenCode: {e}")
        sys.exit(1)
    session = OpencodeSession(server, system_prompt=get_system_prompt())
    log.info("OpenCode connected")

    try:
        SOCKET_PATH.unlink()
    except OSError:
        pass

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(SOCKET_PATH))
    sock.listen(1)
    os.chmod(SOCKET_PATH, 0o600)
    log.info(f"Listening on {SOCKET_PATH}")

    while not _shutdown:
        try:
            conn, _ = sock.accept()
            handle_client(conn, whisper, server, session)
        except socket.timeout:
            continue
        except OSError:
            if _shutdown:
                break
            log.exception("Socket error")

    cleanup()


if __name__ == "__main__":
    main()
