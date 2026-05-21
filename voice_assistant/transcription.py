"""Speech-to-text via faster-whisper."""

import sys

import numpy as np
from faster_whisper import WhisperModel

from voice_assistant.config import VAD_THRESHOLD, WHISPER_LANG, HOTWORDS

# Words that Whisper may hallucinate from background noise.
_HALLUCINATED_WORDS = frozenset(
    w.lower()
    for w in (
        "DeepSeek",
        "Whisper",
        "solución",
        "asistente",
        "source",
        "API",
        "gracias",
        "adiós",
        "subscribe",
        "subscribete",
        "like",
        "thanks",
        "watching",
        "don't",
        "forget",
    )
)

# Full phrases that Whisper may hallucinate as a single segment.
_HALLUCINATED_PHRASES = frozenset(
    p.lower()
    for p in (
        "Thanks for watching",
        "Don't forget to subscribe",
        "Subscribe to the channel",
        "Like and subscribe",
    )
)


def _is_hallucination(text: str) -> bool:
    """Return True when the transcribed text appears to be noise, not speech.

    Heuristics:
    - Text matches a known hallucinated phrase.
    - All tokens are known hallucinated words (e.g. hotwords, "subscribe").
    - Text is empty or a single character.
    """
    t = text.strip().lower()
    if not t:
        return True
    if len(t) < 2:
        return True
    if t in _HALLUCINATED_PHRASES:
        return True
    tokens = t.replace(",", " ").replace(".", " ").split()
    if not tokens:
        return True
    return all(w.strip() in _HALLUCINATED_WORDS for w in tokens)


def transcribe(model: WhisperModel, audio: np.ndarray) -> str:
    """Transcribe an audio array to text using the given Whisper model.

    Applies voice-activity detection before inference to discard silence
    and filters out common hallucinations caused by background noise.
    Returns the transcription string, or an empty string if nothing was heard.
    """
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.95
    audio = audio.astype(np.float32)

    lang = WHISPER_LANG if WHISPER_LANG else None
    segments, _ = model.transcribe(
        audio,
        language=lang,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(threshold=VAD_THRESHOLD),
        hotwords=HOTWORDS,
    )
    text = " ".join(seg.text for seg in segments).strip()
    if _is_hallucination(text):
        text = ""
    if text:
        print(f"\nTú: {text}", file=sys.stderr)
    return text
