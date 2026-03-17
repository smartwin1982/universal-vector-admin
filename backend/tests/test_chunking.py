"""
Chunking strategy tests
"""
import pytest
from app.services.chunking import get_chunker, CharacterChunker, RecursiveChunker


def test_character_chunker():
    chunker = CharacterChunker()
    text = "This is a test. " * 50  # ~800 chars
    chunks = chunker.chunk(text, chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 250  # Allow some slack for sentence boundaries


def test_recursive_chunker():
    chunker = RecursiveChunker()
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three is longer with more content. " * 10
    chunks = chunker.chunk(text, chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1


def test_empty_text():
    chunker = CharacterChunker()
    assert chunker.chunk("", 500, 50) == []
    assert chunker.chunk("   ", 500, 50) == []


def test_get_chunker():
    assert get_chunker("character").strategy_name == "character"
    assert get_chunker("recursive").strategy_name == "recursive"
    assert get_chunker("semantic").strategy_name == "semantic"
    with pytest.raises(ValueError):
        get_chunker("invalid")
