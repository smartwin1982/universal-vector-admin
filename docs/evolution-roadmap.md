# Universal Vector Admin - Evolution Roadmap

## Context

專案目前已具備核心功能（PDF 上傳、向量搜尋、RAG 問答、LLM 整合），但存在幾個明顯瓶頸：
- RAG 回應為一次性返回（無串流），體驗差
- 僅支援單輪問答，無對話記憶
- 僅支援 PDF 一種文件格式
- 前端為單頁面 2x2 格局，無導航、無 Collection 管理
- 無 Docker 部署、無認證機制

本計畫將專案從「功能原型」進化為「可部署的生產級 RAG 管理平台」。

---

## Phase 1: Streaming RAG + 對話記憶

> 影響最直接的 UX 提升，也是後續功能的基礎

### 1.1 Backend — LLM Streaming

**修改** `backend/app/services/llm/base.py`
- 新增 `stream_generate()` async generator 方法到 `BaseLLMService`

**修改** `backend/app/services/llm/ollama_service.py`
- 將 `stream: False` 改為 `stream: True`
- 實作 `stream_generate()`：逐行讀取 httpx streaming response，yield 每個 chunk

**修改** `backend/app/services/llm/gemini_service.py`
- 實作 `stream_generate()`：使用 `generate_content(stream=True)`，yield 每個 chunk

### 1.2 Backend — SSE Streaming Endpoint

**修改** `backend/app/routers/rag.py`
- 新增 `POST /api/rag/ask/stream` — 使用 FastAPI `StreamingResponse` + SSE 格式
- SSE 事件類型：`sources`（先送檢索結果）、`chunk`（串流文字）、`done`（結束信號）
- 保留原有 `POST /api/rag/ask` 非串流端點

**修改** `backend/app/services/rag_service.py`
- 新增 `ask_stream()` async generator 方法
- 先 yield sources，再 yield LLM streaming chunks

### 1.3 Backend — 對話記憶

**新建** `backend/app/models/session.py`
- `ConversationMessage(role, content, timestamp)`
- `ConversationSession(session_id, messages, created_at, updated_at)`

**新建** `backend/app/services/session_service.py`
- In-memory session store（`Dict[str, ConversationSession]`）
- Singleton pattern，與現有服務一致
- `create_session()`, `get_session()`, `add_message()`, `delete_session()`
- TTL 自動清理（預設 1 小時過期）

**修改** `backend/app/models/rag.py`
- `RAGAskRequest` 新增 `session_id: Optional[str]` 欄位

**修改** `backend/app/services/rag_service.py`
- 若有 session_id，將歷史對話注入 LLM prompt
- 將新的 Q&A 存入 session

**修改** `backend/app/routers/rag.py`
- 新增 `POST /api/rag/sessions`（建立）
- 新增 `GET /api/rag/sessions/{id}`（取得歷史）
- 新增 `DELETE /api/rag/sessions/{id}`（刪除）

### 1.4 Frontend — Chat UI

**新建** `frontend/src/components/chat/` 目錄
- `chat-message.tsx` — 訊息氣泡（使用者 / AI）
- `chat-input.tsx` — 輸入框 + 送出按鈕
- `chat-panel.tsx` — 整合元件，管理串流狀態

**新建** `frontend/src/lib/hooks/use-streaming-rag.ts`
- 使用 `fetch` + `ReadableStream` 消費 SSE
- 管理串流狀態：idle → loading → streaming → done
- 暴露 `{ messages, isStreaming, sendMessage, sources }`

**修改** `frontend/src/lib/api.ts`
- 新增 session CRUD API methods
- 新增 streaming endpoint URL

**修改** `frontend/src/app/page.tsx`
- 將 RAG Q&A 區塊替換為 Chat UI 元件

### Phase 1 驗證
- 使用 Ollama 和 Gemini 分別測試串流回應，確認逐字顯示
- 連續問 3+ 個相關問題，確認對話上下文被正確引用
- 關閉頁面後重開，確認 session 可恢復（在 TTL 內）

---

## Phase 2: 多文件格式 + 進階分塊

### 2.1 Backend — 文件處理器抽象

**新建** `backend/app/services/document_processors/base.py`
- `BaseDocumentProcessor` ABC：`extract_text(file_bytes) -> List[PageText]`
- `ProcessedDocument(text_pages, metadata)`

**新建** `backend/app/services/document_processors/`
- `pdf_processor.py` — 重構現有 PDF 邏輯
- `docx_processor.py` — 使用 `python-docx` 解析 Word
- `text_processor.py` — 處理 .txt / .md
- `csv_processor.py` — 使用 `pandas` 逐行/逐區塊處理
- `web_processor.py` — 使用 `httpx` + `beautifulsoup4` 抓取網頁
- `__init__.py` — Factory：依副檔名自動選擇 processor

**修改** `backend/requirements.txt`
- 新增：`python-docx`, `beautifulsoup4`, `pandas`, `openpyxl`

### 2.2 Backend — 進階分塊策略

**新建** `backend/app/services/chunking/`
- `base.py` — `BaseChunker` ABC
- `character_chunker.py` — 重構現有分塊邏輯
- `recursive_chunker.py` — 遞迴分割（段落 → 句子 → 字元）
- `semantic_chunker.py` — 基於 embedding 相似度分組（進階）

**修改** `backend/app/models/pdf.py` → 重命名為 `backend/app/models/document.py`
- 統一 `DocumentUploadResponse`，支援所有格式
- 新增 `ChunkingStrategy` enum：`character`, `recursive`, `semantic`

### 2.3 Backend — 統一上傳端點 + Reranker

**新建** `backend/app/routers/documents.py`
- `POST /api/documents/upload` — 統一上傳（自動偵測格式）
- `POST /api/documents/scrape` — URL 網頁擷取
- 保留原 PDF 端點向後相容

**新建** `backend/app/services/reranker_service.py`
- 使用 cross-encoder 模型（如 `cross-encoder/ms-marco-MiniLM-L-6-v2`）
- `rerank(query, results) -> reranked_results`
- 可選啟用，透過 query param `rerank=true`

### 2.4 Frontend — 多格式上傳

**修改** `frontend/src/components/pdf-upload.tsx` → 重構為通用上傳元件
- 拖放區域（drag & drop）
- 支援多檔案
- 格式自動偵測 + 圖示顯示
- 分塊策略選擇器（dropdown）
- 上傳前 chunk 預覽

**修改** `frontend/src/lib/api.ts`
- 新增 documents API methods

### Phase 2 驗證
- 分別上傳 PDF、Word、TXT、CSV，確認正確解析與向量化
- 測試 URL 擷取功能
- 比較不同分塊策略的 RAG 回答品質
- 啟用 Reranker 前後搜尋結果品質對比

---

## Phase 3: 前端 UI 大升級

### 3.1 新增 shadcn/ui 元件

透過 `npx shadcn@latest add` 安裝：
- `dialog`, `tabs`, `select`, `textarea`, `badge`, `progress`
- `skeleton`, `toast`/`sonner`, `sidebar`, `dropdown-menu`
- `sheet`, `separator`, `scroll-area`, `tooltip`, `switch`

### 3.2 佈局重構

**修改** `frontend/src/app/layout.tsx`
- 整合 Sidebar 元件 + 主內容區域
- Dark mode toggle（使用 `next-themes`）

**新建** `frontend/src/components/layout/`
- `app-sidebar.tsx` — 側邊導航（Collections、Chat、Documents、Search、Settings）
- `header.tsx` — 頂部導航列 + dark mode switch
- `breadcrumb.tsx` — 麵包屑導航

### 3.3 多頁面路由（Next.js App Router）

**新建** `frontend/src/app/chat/page.tsx`
- 獨立 Chat 頁面，完整對話介面
- Session 列表 + 建立新對話

**新建** `frontend/src/app/collections/page.tsx`
- Collection 列表卡片，顯示統計資訊（文件數、維度、大小）
- 建立 / 刪除 Collection

**新建** `frontend/src/app/collections/[name]/page.tsx`
- 單一 Collection 詳情：文件瀏覽、搜尋、統計

**新建** `frontend/src/app/search/page.tsx`
- 語意搜尋介面，結果含相似度分數條
- Filter by metadata

**新建** `frontend/src/app/settings/page.tsx`
- LLM Provider 設定、連線管理、Embedding 模型資訊

**修改** `frontend/src/app/page.tsx`
- 改為 Dashboard 總覽頁（統計卡片 + 快速操作）

### 3.4 狀態管理重構

**修改** `frontend/src/lib/stores/connection-store.ts`
- 實際使用 Zustand store 管理全域狀態

**新建** `frontend/src/lib/hooks/use-collections.ts`
- `useCollections()`, `useCollectionStats()`, `useCreateCollection()` 等

**新建** `frontend/src/lib/hooks/use-vectors.ts`
- `useVectors()`, `useSearchVectors()`, `useDeleteVector()` 等

### 3.5 進階視覺化（選配）

**新建** `frontend/src/components/charts/`
- 使用 `recharts` 繪製統計圖表
- Collection 大小趨勢、文件類型分佈

### Phase 3 驗證
- 所有頁面可正常導航，Sidebar 高亮當前頁
- Dark/Light mode 切換正常且持久化
- Collection CRUD 全流程測試
- 搜尋頁面返回正確結果 + 分數顯示
- 響應式佈局：桌面 / 平板 / 手機

---

## Phase 4: 部署與工程化

### 4.1 Docker 容器化

**新建** `backend/Dockerfile`
**新建** `frontend/Dockerfile`
**新建** `docker-compose.yml`
**新建** `.env.docker` — Docker 環境變數模板

### 4.2 使用者認證

**新建** `backend/app/core/security.py` — JWT + bcrypt
**新建** `backend/app/models/user.py`
**新建** `backend/app/routers/auth.py`
**新建** `frontend/src/app/login/page.tsx`
**新建** `frontend/src/lib/stores/auth-store.ts`

### 4.3 更多向量資料庫後端

**新建** `backend/app/services/clients/qdrant_client.py`
**新建** `backend/app/services/clients/milvus_client.py`

### 4.4 工程品質

- Structured logging, rate limiting
- Integration tests

---

## 實作順序建議

```
Phase 1 (Streaming + Memory)     ████████░░  先做
Phase 2 (Multi-format)           ░░████████  Phase 1 完成後
Phase 3 (UI Overhaul)            ░░░░██████  可與 Phase 2 後端並行
Phase 4 (Deploy + Engineering)   ░░░░░░████  最後收尾
```

## 關鍵技術決策

| 決策 | 選擇 | 理由 |
|------|------|------|
| Streaming 協議 | SSE (Server-Sent Events) | 比 WebSocket 簡單，適合單向串流 |
| Session 儲存 | In-memory → 未來 Redis | 先求快，之後可平滑遷移 |
| 分塊策略預設 | Recursive character | 平衡品質與速度 |
| Reranker 模型 | cross-encoder/ms-marco-MiniLM-L-6-v2 | 輕量且效果好 |
| 認證方案 | JWT + bcrypt | 標準做法，無需額外基礎設施 |
| 前端路由 | Next.js App Router | 已在使用，自然擴展 |
| 圖表庫 | Recharts | React 生態最成熟 |
