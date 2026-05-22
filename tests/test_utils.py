"""Tests for voice_assistant.utils."""

from voice_assistant.utils import clean_markdown, summarize


def test_clean_markdown_removes_bold():
    result = clean_markdown("**bold** text")
    assert result == "bold text"


def test_clean_markdown_removes_italic():
    result = clean_markdown("*italic* and _italic_")
    assert result == "italic and italic"


def test_clean_markdown_removes_inline_code():
    result = clean_markdown("`code` here")
    assert result == "code here"


def test_clean_markdown_removes_links():
    result = clean_markdown("[text](https://example.com)")
    assert result == "text"


def test_clean_markdown_removes_headers():
    result = clean_markdown("# Header\n## Sub")
    assert result == "Header\nSub"


def test_clean_markdown_removes_code_blocks():
    result = clean_markdown("```python\nprint('hi')\n```")
    assert result.strip() == ""


def test_clean_markdown_removes_lists():
    result = clean_markdown("- item 1\n- item 2")
    assert result == "item 1\nitem 2"


def test_clean_markdown_removes_horizontal_rules():
    result = clean_markdown("---\n***\n___")
    assert result == ""


def test_clean_markdown_collapses_newlines():
    result = clean_markdown("a\n\n\n\nb")
    assert result == "a\n\nb"


def test_clean_markdown_plain_text_unchanged():
    result = clean_markdown("Hola, ¿cómo estás?")
    assert result == "Hola, ¿cómo estás?"


class TestSummarize:
    def test_short_text_unchanged(self):
        assert summarize("Hola mundo") == "Hola mundo"

    def test_truncates_at_sentence_boundary(self):
        long = "Primera oración. Segunda oración. Tercera oración."
        result = summarize(long, max_len=30)
        assert result == "Primera oración."

    def test_truncates_at_word_boundary(self):
        long = " ".join(["word"] * 50)
        result = summarize(long, max_len=50)
        assert len(result) <= 53  # may add ellipsis

    def test_empty_returns_empty(self):
        assert summarize("") == ""
