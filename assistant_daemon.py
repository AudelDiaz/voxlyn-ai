#!/usr/bin/env python3
import logging
import logging.handlers
import os
import signal
import socket
import sys
import threading
from pathlib import Path

import numpy as np
import piper
from faster_whisper import WhisperModel

from opencode_client import OpencodeServer, OpencodeSession
from assistant_local import (
    record_audio,
    transcribe,
    get_response,
    speak,
    play_listen_tone,
    SAMPLE_RATE,
    WHISPER_MODEL,
    COMPUTE_TYPE,
    TTS_VOICE,
    get_piper_voice,
)

DATA_DIR = Path.home() / ".voice-assistant"
SOCKET_PATH = DATA_DIR / "daemon.sock"
LOG_PATH = DATA_DIR / "voice-assistant.log"
ERR_PATH = DATA_DIR / "voice-assistant.err"

_busy = False
_shutdown = False


def setup_logging():
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

    return logging.getLogger(__name__)


log: logging.Logger = setup_logging()


def cleanup():
    global _shutdown
    _shutdown = True
    try:
        SOCKET_PATH.unlink()
    except OSError:
        pass
    log.info("Daemon stopped")


def handle_signal(signum, frame):
    log.info(f"Received signal {signum}, shutting down...")
    cleanup()
    sys.exit(0)


def process_pipeline(
    whisper: WhisperModel,
    piper_voice: piper.PiperVoice,
    server: OpencodeServer,
    session: OpencodeSession,
):
    global _busy
    try:
        _busy = True
        log.info("Pipeline started")

        play_listen_tone()

        audio = record_audio()
        if len(audio) < SAMPLE_RATE * 0.3:
            log.info("Audio too short, discarding")
            return

        user_text = transcribe(whisper, audio)
        if not user_text:
            log.info("No speech detected")
            return

        log.info(f"User: {user_text}")
        ai_response = get_response(user_text, server, session)
        log.info(f"Assistant: {ai_response}")

        speak(ai_response, piper_voice)
        log.info("Pipeline finished")
    except Exception:
        log.exception("Pipeline error")
    finally:
        _busy = False


def handle_client(
    conn: socket.socket,
    whisper: WhisperModel,
    piper_voice: piper.PiperVoice,
    server: OpencodeServer,
    session: OpencodeSession,
):
    try:
        data = conn.recv(1024).decode().strip()
        if data != "record":
            conn.sendall(b"error: unknown command\n")
            return

        if _busy:
            conn.sendall(b"busy\n")
            log.info("Trigger ignored: pipeline busy")
            return

        conn.sendall(b"ok\n")
        conn.close()

        threading.Thread(
            target=process_pipeline,
            args=(whisper, piper_voice, server, session),
            daemon=True,
        ).start()
    except Exception:
        log.exception("Error handling client")


def main():
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    log.info(f"Loading Whisper ({WHISPER_MODEL}, {COMPUTE_TYPE})...")
    whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type=COMPUTE_TYPE)
    log.info("Whisper loaded")

    log.info(f"Loading Piper voice ({TTS_VOICE})...")
    piper_voice = get_piper_voice()
    log.info("Piper loaded")

    log.info("Connecting to OpenCode...")
    server = OpencodeServer()
    server.ensure_running()
    session = OpencodeSession(server, system_prompt="")
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
            handle_client(conn, whisper, piper_voice, server, session)
        except socket.timeout:
            continue
        except OSError:
            if _shutdown:
                break
            log.exception("Socket error")

    cleanup()


if __name__ == "__main__":
    main()
