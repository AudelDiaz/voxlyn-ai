"""Extended tests for voice_assistant.utils."""

from voice_assistant.utils import has_code_block, strip_code_blocks


class TestHasCodeBlock:
    def test_no_code(self):
        assert has_code_block("Hola, ¿cómo estás?") is False

    def test_inline_code_not_fence(self):
        assert has_code_block("Usa `print()` aquí") is False

    def test_code_block(self):
        text = "Aquí tienes:\n```python\nprint('hi')\n```"
        assert has_code_block(text) is True

    def test_code_block_without_lang(self):
        text = "Ejemplo:\n```\necho hello\n```"
        assert has_code_block(text) is True


class TestStripCodeBlocks:
    def test_strip_removes_fence(self):
        result = strip_code_blocks("Antes\n```python\ncode\n```\nDespués")
        assert "Antes" in result
        assert "Después" in result
        assert "code" not in result

    def test_no_code_unchanged(self):
        result = strip_code_blocks("Hola mundo")
        assert result == "Hola mundo"

    def test_only_code_returns_empty(self):
        result = strip_code_blocks("```\ncode\n```")
        assert result == ""
