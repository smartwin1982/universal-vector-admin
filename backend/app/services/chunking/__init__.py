"""
分塊策略模組
"""
from app.services.chunking.base import BaseChunker, TextChunk
from app.services.chunking.character_chunker import CharacterChunker
from app.services.chunking.recursive_chunker import RecursiveChunker
from app.services.chunking.semantic_chunker import SemanticChunker


def get_chunker(strategy: str = "recursive") -> BaseChunker:
    """根據策略名稱取得分塊器"""
    chunkers = {
        "character": CharacterChunker,
        "recursive": RecursiveChunker,
        "semantic": SemanticChunker,
    }
    cls = chunkers.get(strategy.lower())
    if not cls:
        raise ValueError(f"不支援的分塊策略: {strategy}，可選: {list(chunkers.keys())}")
    return cls()


__all__ = [
    "BaseChunker",
    "TextChunk",
    "CharacterChunker",
    "RecursiveChunker",
    "SemanticChunker",
    "get_chunker",
]
