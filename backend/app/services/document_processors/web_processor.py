"""
網頁擷取處理器 — 使用 httpx + beautifulsoup4
"""
from typing import List

from app.services.document_processors.base import (
    BaseDocumentProcessor,
    PageText,
    ProcessedDocument,
)


class WebProcessor(BaseDocumentProcessor):
    """網頁擷取處理器"""

    @property
    def supported_extensions(self) -> List[str]:
        return []  # 不透過副檔名觸發

    def extract_text(self, file_bytes: bytes, filename: str = "") -> ProcessedDocument:
        """直接處理 HTML bytes"""
        return self._parse_html(file_bytes, source=filename)

    async def fetch_and_extract(self, url: str) -> ProcessedDocument:
        """從 URL 抓取並提取文字"""
        import httpx
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "UVA-Bot/1.0"})
            resp.raise_for_status()
            return self._parse_html(resp.content, source=url)

    def _parse_html(self, html_bytes: bytes, source: str = "") -> ProcessedDocument:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("beautifulsoup4 is required: pip install beautifulsoup4")

        soup = BeautifulSoup(html_bytes, "html.parser")

        # 移除 script、style 標籤
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.string if soup.title else ""

        # 提取主要文字
        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # 將文字分成段落
        paragraphs = "\n".join(lines)
        sections = [s.strip() for s in paragraphs.split("\n\n") if s.strip()]

        pages: List[PageText] = []
        chunk_size = 10
        for i in range(0, max(len(sections), 1), chunk_size):
            group = sections[i : i + chunk_size]
            if group:
                pages.append(PageText(
                    page_number=i // chunk_size + 1,
                    text="\n\n".join(group),
                ))

        if not pages and lines:
            pages.append(PageText(page_number=1, text="\n".join(lines)))

        return ProcessedDocument(
            text_pages=pages,
            metadata={
                "source": source,
                "type": "web",
                "title": title,
            },
        )
