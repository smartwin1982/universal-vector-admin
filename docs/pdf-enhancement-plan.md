# PDF 多檔管理 + 精確檢索來源 — 需求與實作規畫

## 需求背景

目前 PDF 上傳僅支援單次單檔，RAG 回答時不會標示答案來自哪份 PDF。
使用者希望能多次上傳 PDF，系統記錄每次上傳的資料，且問答時能精確標示來源。

---

## 功能需求

### 1. PDF 上傳記錄
- 每次上傳 PDF 時，在向量 metadata 中記錄**上傳時間**（ISO 格式）
- 提供 API 查詢所有已上傳的 PDF 清單
- 清單包含：檔名、上傳日期、總頁數、chunk 數量

### 2. PDF 清單顯示（前端）
- 在 PDF 上傳區塊下方顯示已上傳的 PDF 歷史記錄
- 格式範例：
  ```
  已上傳的 PDF (3)
  ├── report.pdf        2026-02-01  12頁 / 45 chunks
  ├── manual.pdf        2026-02-10   8頁 / 30 chunks
  └── notes.pdf         2026-02-13   3頁 / 10 chunks
  ```

### 3. RAG 精確來源標示
- RAG 回答時，參考來源顯示 **PDF 檔名 + 頁碼**
- 格式範例：
  ```
  參考來源 (3)
  #1  report.pdf (p.3)    相似度: 92.1%
      "根據報告指出..."
  #2  manual.pdf (p.7)    相似度: 85.3%
      "操作手冊中提到..."
  ```
- 送給 LLM 的 prompt 中也包含來源資訊，讓 AI 在回答中引用

---

## 技術實作

### Backend 變更

#### 1. `backend/app/services/pdf_service.py`
- `chunks_to_vectors()` — metadata 加入 `uploaded_at` 欄位
```python
metadata={
    "source": chunk.source_filename,
    "page": chunk.page_number,
    "chunk_index": chunk.chunk_index,
    "type": "pdf",
    "uploaded_at": datetime.now().isoformat(),  # 新增
}
```

#### 2. `backend/app/models/rag.py`
- `RAGSourceDocument` 新增 metadata 欄位
```python
class RAGSourceDocument(BaseModel):
    id: str
    document: str
    score: float
    metadata: Optional[Dict[str, Any]] = None  # 新增
```

#### 3. `backend/app/services/rag_service.py`
- 建構 `RAGSourceDocument` 時傳入 `metadata=r.metadata`
- prompt 組裝改為包含來源資訊：
  ```
  [文件 1 — report.pdf 第3頁] 內容...
  ```
- 改善 system prompt，要求 LLM 引用來源

#### 4. `backend/app/models/pdf.py` — 新增模型
```python
class PDFSourceInfo(BaseModel):
    filename: str
    uploaded_at: str
    chunk_count: int
    page_count: int

class PDFSourcesResponse(BaseModel):
    sources: List[PDFSourceInfo]
    total_files: int
    total_chunks: int
```

#### 5. `backend/app/routers/pdf.py` — 新增端點
- `GET /api/pdf/sources?connection_id=xxx&collection_name=xxx`
- 查詢所有向量 metadata，過濾 `type=pdf`，按檔名分組彙整

---

### Frontend 變更

#### 6. `frontend/src/lib/api.ts`
- `RAGSourceDocument` 加 `metadata?: Record<string, unknown>`
- 新增 `PDFSourceInfo`、`PDFSourcesResponse` 類型
- `pdfApi` 加 `sources(connectionId, collectionName)` 方法

#### 7. `frontend/src/components/pdf-upload.tsx`
- 上傳成功後自動刷新 PDF 清單
- 底部顯示已上傳 PDF 清單（檔名、日期、頁數/chunk 數）

#### 8. `frontend/src/app/page.tsx`
- RAG「參考來源」每筆顯示 PDF 檔名 + 頁碼
- 格式：`report.pdf (p.3)` | 相似度 | 內容摘要

---

## 實作順序

| 步驟 | 檔案 | 變更內容 |
|------|------|----------|
| 1 | `pdf_service.py` | metadata 加 `uploaded_at` |
| 2 | `rag.py` (model) | `RAGSourceDocument` 加 `metadata` |
| 3 | `rag_service.py` | 傳遞 metadata + 改善 prompt |
| 4 | `pdf.py` (model + router) | `PDFSourceInfo` + `GET /sources` |
| 5 | `api.ts` | 前端 API 類型更新 |
| 6 | `pdf-upload.tsx` | PDF 清單顯示 |
| 7 | `page.tsx` | RAG 來源顯示增強 |

---

## PDF 重複上傳檢查

### 需求
上傳 PDF 前檢查是否已有同檔名的 PDF 記錄，避免重複存入向量 DB。

### 實作方式

#### Backend — `backend/app/routers/pdf.py`
- 上傳前查詢向量 DB，過濾 metadata 中 `source == 檔名` 且 `type == "pdf"` 的記錄
- 若已存在，回傳 **409 Conflict**，detail 包含已有的 chunk 數與上傳時間
```python
# 檢查重複
vectors = await client.list_vectors(collection_name, limit=1, offset=0)
# 遍歷找 metadata.source == filename and metadata.type == "pdf"
# 若找到 → raise HTTPException(409, "此 PDF 已上傳過（XX chunks，上傳於 YYYY-MM-DD）")
```

#### Frontend — `frontend/src/components/pdf-upload.tsx`
- 捕捉 409 回應，顯示提示訊息：「此 PDF 已上傳過，如需重新上傳請先刪除舊資料」
- 與一般錯誤區分，用警告色（橘/黃）而非錯誤色（紅）

---

## 驗證方式

1. 上傳 PDF → 確認向量 metadata 含 `uploaded_at` 時間戳
2. `GET /api/pdf/sources` → 回傳正確的 PDF 清單與統計
3. RAG 問答 → 前端顯示每筆來源的 PDF 檔名 + 頁碼
4. 多次上傳不同 PDF → 清單正確顯示所有記錄
