"""
分塊策略抽象基類
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class TextChunk:
    """分塊結果"""
    text: str
    chunk_index: int
    metadata: dict


class BaseChunker(ABC):
    """分塊策略抽象基類"""

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名稱"""
        ...

    @abstractmethod
    def chunk(
        self,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> List[str]:
        """
        將文字分塊

        Args:
            text: 要分塊的文字
            chunk_size: 每個 chunk 的目標字元數
            chunk_overlap: chunk 之間的重疊字元數

        Returns:
            分塊後的文字列表
        """
        ...
