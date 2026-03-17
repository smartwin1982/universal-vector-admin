"""
PDF 文件處理器 — 使用 PyMuPDF 提取文字
"""
from typing import List

import fitz

from app.services.document_processors.base import (
    BaseDocumentProcessor,
    PageText,
    ProcessedDocument,
)


class PDFProcessor(BaseDocumentProcessor):
    """PDF 文件處理器"""

    @property
    def supported_extensions(self) -> List[str]:
        return [".pdf"]

    def extract_text(self, file_bytes: bytes, filename: str = "") -> ProcessedDocument:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages: List[PageText] = []

        total_pages = len(doc)
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                pages.append(PageText(page_number=page_num + 1, text=text))

        doc.close()

        return ProcessedDocument(
            text_pages=pages,
            metadata={
                "source": filename,
                "type": "pdf",
                "total_pages": total_pages,
            },
        )
