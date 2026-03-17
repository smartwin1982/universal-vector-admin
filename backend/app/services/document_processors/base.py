"""
文件處理器抽象基類
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class PageText:
    """單頁/單區塊的文字"""
    page_number: int
    text: str


@dataclass
class ProcessedDocument:
    """處理後的文件"""
    text_pages: List[PageText]
    metadata: dict = field(default_factory=dict)


class BaseDocumentProcessor(ABC):
    """文件處理器抽象基類"""

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """支援的副檔名列表，例如 ['.pdf']"""
        ...

    @abstractmethod
    def extract_text(self, file_bytes: bytes, filename: str = "") -> ProcessedDocument:
        """
        從檔案 bytes 提取文字

        Args:
            file_bytes: 檔案二進位內容
            filename: 原始檔名（用於 metadata）

        Returns:
            ProcessedDocument 包含每頁文字與 metadata
        """
        ...
