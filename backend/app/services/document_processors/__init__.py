"""
文件處理器工廠模組
依副檔名自動選擇適當的處理器
"""
from typing import Optional

from app.services.document_processors.base import BaseDocumentProcessor, ProcessedDocument, PageText

# 處理器映射表
_processor_map: dict[str, type[BaseDocumentProcessor]] = {}
_initialized = False


def _init_processors() -> None:
    """延遲初始化處理器映射"""
    global _initialized
    if _initialized:
        return

    from app.services.document_processors.pdf_processor import PDFProcessor
    from app.services.document_processors.text_processor import TextProcessor

    for proc_cls in [PDFProcessor, TextProcessor]:
        proc = proc_cls()
        for ext in proc.supported_extensions:
            _processor_map[ext.lower()] = proc_cls

    # 可選依賴的處理器
    try:
        from app.services.document_processors.docx_processor import DocxProcessor
        for ext in DocxProcessor().supported_extensions:
            _processor_map[ext.lower()] = DocxProcessor
    except Exception:
        pass

    try:
        from app.services.document_processors.csv_processor import CSVProcessor
        for ext in CSVProcessor().supported_extensions:
            _processor_map[ext.lower()] = CSVProcessor
    except Exception:
        pass

    try:
        from app.services.document_processors.pages_processor import PagesProcessor
        for ext in PagesProcessor().supported_extensions:
            _processor_map[ext.lower()] = PagesProcessor
    except Exception:
        pass

    _initialized = True


def get_processor(filename: str) -> Optional[BaseDocumentProcessor]:
    """根據檔名副檔名取得處理器實例"""
    _init_processors()

    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()

    proc_cls = _processor_map.get(ext)
    if proc_cls:
        return proc_cls()
    return None


def get_supported_extensions() -> list[str]:
    """回傳所有支援的副檔名"""
    _init_processors()
    return list(_processor_map.keys())


__all__ = [
    "BaseDocumentProcessor",
    "ProcessedDocument",
    "PageText",
    "get_processor",
    "get_supported_extensions",
]
