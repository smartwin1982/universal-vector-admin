"""
純文字 / Markdown 文件處理器
"""
from typing import List

from app.services.document_processors.base import (
    BaseDocumentProcessor,
    PageText,
    ProcessedDocument,
)


class TextProcessor(BaseDocumentProcessor):
    """TXT / Markdown 文件處理器"""

    @property
    def supported_extensions(self) -> List[str]:
        return [".txt", ".md", ".markdown", ".rst"]

    def extract_text(self, file_bytes: bytes, filename: str = "") -> ProcessedDocument:
        # 嘗試 UTF-8 解碼，fallback 到 latin-1
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")

        # 按雙換行分段
        sections = [s.strip() for s in text.split("\n\n") if s.strip()]

        pages: List[PageText] = []
        # 將 sections 合併成頁（每 ~10 段一頁）
        chunk_size = 10
        for i in range(0, max(len(sections), 1), chunk_size):
            group = sections[i : i + chunk_size]
            if group:
                pages.append(PageText(
                    page_number=i // chunk_size + 1,
                    text="\n\n".join(group),
                ))

        if not pages:
            pages.append(PageText(page_number=1, text=text))

        ext = filename.rsplit(".", 1)[-1] if "." in filename else "txt"
        return ProcessedDocument(
            text_pages=pages,
            metadata={
                "source": filename,
                "type": ext,
            },
        )
