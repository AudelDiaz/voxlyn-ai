"""Tests for mempalace_memory.py (MemPalace v3 backend)."""

from unittest.mock import MagicMock, patch

import pytest

from mempalace_memory import _redact_secrets, format_context, save_turn, search_context


class TestRedactSecrets:
    def test_redacts_api_key(self):
        result = _redact_secrets("my key is sk-abc123def456ghi789jklmno")
        assert "[REDACTED]" in result
        assert "sk-abc123def456ghi789jklmno" not in result

    def test_redacts_github_token(self):
        prefix = "ghp_"
        suffix = "a" * 36
        result = _redact_secrets(f"token {prefix}{suffix}")
        assert "[REDACTED]" in result

    def test_redacts_password(self):
        result = _redact_secrets('client_secret=supersecret123!@#')
        assert "[REDACTED]" in result

    def test_plain_text_unchanged(self):
        text = "Hola, ¿cómo estás?"
        assert _redact_secrets(text) == text

    def test_redacts_aws_key(self):
        result = _redact_secrets("AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE")
        assert "[REDACTED]" in result


class TestFormatContext:
    def test_empty_results(self):
        assert format_context([]) == ""

    def test_single_result(self):
        results = [{"text": "Hola mundo", "room": "conversations"}]
        expected = "Relevant context from your past conversations:\n[conversations] Hola mundo"
        assert format_context(results) == expected

    def test_multiple_results(self):
        results = [
            {"text": "First turn", "room": "general"},
            {"text": "Second turn", "room": "coding"},
        ]
        text = format_context(results)
        assert "[general] First turn" in text
        assert "[coding] Second turn" in text

    def test_truncates_long_text(self):
        results = [{"text": "A" * 500, "room": "conversations"}]
        text = format_context(results)
        # [conversations] = 16 chars + 300 max = 316
        assert len(text.split("\n")[-1]) <= 316

    def test_missing_room_defaults_to_question(self):
        results = [{"text": "some text", "room": None}]
        text = format_context(results)
        assert "[None]" in text


class TestSaveTurn:
    @patch("mempalace_memory._collection")
    @patch("mempalace_memory._ensure_migrated")
    def test_save_turn_calls_upsert(self, mock_migrate, mock_col):
        mock_col.return_value.get.return_value.ids = []
        save_turn("user text", "assistant text")
        mock_col.return_value.upsert.assert_called_once()


class TestSearchContext:
    @patch("mempalace_memory._collection")
    @patch("mempalace_memory._search_memories")
    @patch("mempalace_memory._ensure_migrated")
    def test_short_query_falls_back(self, mock_migrate, mock_search, mock_col):
        mock_col.return_value.get.return_value.ids = []
        mock_col.return_value.get.return_value.documents = []
        mock_col.return_value.get.return_value.metadatas = []
        mock_search.return_value = {"results": []}
        result = search_context("a", n_results=5)
        assert result == []

    @patch("mempalace_memory._last_n")
    @patch("mempalace_memory._ensure_migrated")
    def test_empty_query_uses_last_n(self, mock_migrate, mock_last_n):
        mock_last_n.return_value = [{"text": "last", "room": "conversations"}]
        result = search_context("", n_results=3)
        mock_last_n.assert_called_once_with(3)

    @patch("mempalace_memory._search_memories")
    @patch("mempalace_memory._ensure_migrated")
    def test_meaningful_query_uses_semantic_search(self, mock_migrate, mock_search):
        mock_search.return_value = {
            "results": [{"text": "match", "room": "conversations", "wing": "voxlyn_ai", "similarity": 0.95}]
        }
        result = search_context("meaningful query", n_results=5)
        assert len(result) == 1
        assert result[0]["text"] == "match"
