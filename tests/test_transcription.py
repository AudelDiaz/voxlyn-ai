"""Tests for voice_assistant.transcription."""

from voice_assistant.transcription import _is_hallucination


class TestIsHallucination:
    def test_empty_text(self):
        assert _is_hallucination("")

    def test_whitespace_only(self):
        assert _is_hallucination("   ")

    def test_single_hotword(self):
        assert _is_hallucination("DeepSeek")

    def test_hotwords_comma_separated(self):
        assert _is_hallucination("DeepSeek, Whisper, asistente")

    def test_single_char_is_hallucination(self):
        assert _is_hallucination("S")

    def test_two_char_is_speech(self):
        assert _is_hallucination("no") is False
        assert _is_hallucination("sí") is False
        assert _is_hallucination("ok") is False

    def test_real_word_passes(self):
        assert _is_hallucination("Hola") is False

    def test_real_speech(self):
        assert _is_hallucination("¿Cuál es el clima hoy?") is False

    def test_mixed_hotword_and_speech(self):
        assert _is_hallucination("DeepSeek dime el clima") is False

    def test_subscribe_hallucination(self):
        assert _is_hallucination("Subscribe")

    def test_thanks_for_watching(self):
        assert _is_hallucination("Thanks for watching")

    def test_hotwords_with_period(self):
        assert _is_hallucination("DeepSeek. Whisper.")
