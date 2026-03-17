"""
CSV / Excel 文件處理器 — 使用 pandas
"""
import io
from typing import List

from app.services.document_processors.base import (
    BaseDocumentProcessor,
    PageText,
    ProcessedDocument,
)


class CSVProcessor(BaseDocumentProcessor):
    """CSV / Excel 文件處理器"""

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv", ".xlsx", ".xls"]

    def extract_text(self, file_bytes: bytes, filename: str = "") -> ProcessedDocument:
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required: pip install pandas openpyxl")

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"

        if ext == "csv":
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))

        # 每 50 行為一區塊
        rows_per_chunk = 50
        pages: List[PageText] = []

        for i in range(0, len(df), rows_per_chunk):
            chunk_df = df.iloc[i : i + rows_per_chunk]
            # 將每行轉為 "col1: val1, col2: val2" 格式
            rows_text = []
            for _, row in chunk_df.iterrows():
                row_parts = [f"{col}: {val}" for col, val in row.items() if pd.notna(val)]
                rows_text.append(", ".join(row_parts))
            pages.append(PageText(
                page_number=i // rows_per_chunk + 1,
                text="\n".join(rows_text),
            ))

        return ProcessedDocument(
            text_pages=pages,
            metadata={
                "source": filename,
                "type": ext,
                "total_rows": len(df),
                "columns": list(df.columns),
            },
        )
