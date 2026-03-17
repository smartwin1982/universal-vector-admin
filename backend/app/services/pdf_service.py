"""
PDF 處理服務 — 提取文字、分塊、轉為向量物件
"""
from typing import List, Tuple
import fitz  # PyMuPDF

from app.models.pdf import PDFChunk, PDFChunkingConfig
from app.models.vector import VectorCreate


class PDFService:
    """Singleton PDF 處理服務"""

    _instance: "PDFService | None" = None

    def __new__(cls) -> "PDFService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def extract_text_by_page(self, pdf_bytes: bytes) -> List[Tuple[int, str]]:
        """從 PDF bytes 提取每頁文字，回傳 [(page_number, text), ...]"""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                pages.append((page_num + 1, text))
        doc.close()
        return pages

    def chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """將文字分塊，嘗試在句子邊界切割"""
        if not text.strip():
            return []

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size

            if end >= text_len:
                chunk = text[start:].strip()
                if chunk:
                    chunks.append(chunk)
                break

            # 嘗試在句子邊界切割（往回搜尋）
            best_break = end
            search_start = max(start + chunk_size // 2, start)
            segment = text[search_start:end]

            # 按優先序搜尋斷點
            for delimiter in ["\n\n", "。", ". ", "\n", " "]:
                pos = segment.rfind(delimiter)
                if pos != -1:
                    best_break = search_start + pos + len(delimiter)
                    break

            chunk = text[start:best_break].strip()
            if chunk:
                chunks.append(chunk)

            start = best_break - chunk_overlap

        return chunks

    def parse_and_chunk(
        self,
        pdf_bytes: bytes,
        filename: str,
        config: PDFChunkingConfig | None = None,
    ) -> Tuple[List[PDFChunk], int]:
        """完整流程：PDF bytes → 分塊，回傳 (chunks, total_pages)"""
        if config is None:
            config = PDFChunkingConfig()

        pages = self.extract_text_by_page(pdf_bytes)
        total_pages = len(pages)
        chunks: List[PDFChunk] = []
        chunk_index = 0

        for page_number, page_text in pages:
            page_chunks = self.chunk_text(page_text, config.chunk_size, config.chunk_overlap)
            for text in page_chunks:
                chunks.append(PDFChunk(
                    text=text,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    source_filename=filename,
                ))
                chunk_index += 1

        return chunks, total_pages

    def chunks_to_vectors(
        self,
        chunks: List[PDFChunk],
        embeddings: List[List[float]],
    ) -> List[VectorCreate]:
        """將 PDFChunk + embedding 轉為 VectorCreate 物件"""
        vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            vectors.append(VectorCreate(
                document=chunk.text,
                embedding=embedding,
                metadata={
                    "source": chunk.source_filename,
                    "page": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "type": "pdf",
                },
            ))
        return vectors


# 模組層級 singleton 實例
pdf_service = PDFService()
