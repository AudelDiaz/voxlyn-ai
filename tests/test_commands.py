"""Tests for voice_assistant.commands."""

from unittest.mock import MagicMock

import pytest

from voice_assistant.commands import handle_session_command


@pytest.fixture
def session():
    s = MagicMock()
    s.session_id = "test-123"
    return s


@pytest.fixture
def server():
    return MagicMock()


class TestHandleSessionCommand:
    def test_nueva_conversacion(self, session, server):
        result = handle_session_command(
            "nueva conversacion", session, server
        )
        assert result == "Listo, nueva conversación creada."
        session.delete.assert_called_once()
        session.create.assert_called_once()

    def test_nuevo_chat(self, session, server):
        result = handle_session_command("nuevo chat", session, server)
        assert result == "Listo, nueva conversación creada."

    def test_unknown_command_returns_none(self, session, server):
        result = handle_session_command(
            "hola como estas", session, server
        )
        assert result is None

    def test_salir_returns_exit(self, session, server):
        result = handle_session_command("salir", session, server)
        assert result == "__EXIT__"

    def test_quit_returns_exit(self, session, server):
        result = handle_session_command("quit", session, server)
        assert result == "__EXIT__"

    def test_guarda_como(self, session, server):
        result = handle_session_command(
            "guarda como mis notas", session, server
        )
        assert result == "Sesión guardada como 'mis notas'."
        session.rename.assert_called_once_with("mis notas")
