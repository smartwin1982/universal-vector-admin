# 🎯 Universal Vector Admin

通用向量資料庫管理工具 - 一站式管理多種向量資料庫

## ✨ 功能特色

- 🔌 **多資料庫支援** - Chroma, Milvus, Pinecone, Qdrant, Weaviate...
- 🎨 **現代化 UI** - 基於 Next.js 16 + Shadcn/UI
- ⚡ **高效能後端** - FastAPI + async/await
- 🔍 **向量搜尋** - 視覺化相似度查詢
- 📊 **Collection 管理** - CRUD 操作一鍵完成

## 🏗️ 技術棧

### Frontend
- Next.js 16 (React 19)
- Tailwind CSS 4
- Shadcn/UI (New York style)
- TanStack Query
- Zustand

### Backend
- FastAPI
- Pydantic v2
- ChromaDB / Milvus / Pinecone SDK

## 🚀 快速開始

### 環境需求

- Node.js 18+
- Python 3.10+

### 安裝步驟

#### 1. Clone 專案

```bash
git clone https://github.com/your-repo/universal-vector-admin.git
cd universal-vector-admin
```

#### 2. 啟動 Backend

```bash
cd backend

# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 複製環境變數
cp .env.example .env

# 啟動服務
python run.py
```

後端 API 文件：http://localhost:8000/docs

#### 3. 啟動 Frontend

```bash
cd frontend

# 安裝依賴
npm install

# 啟動開發伺服器
npm run dev
```

前端頁面：http://localhost:3000

## 📁 專案結構

```
universal-vector-admin/
├── backend/
│   ├── app/
│   │   ├── core/           # 核心配置
│   │   ├── models/         # Pydantic 模型
│   │   ├── routers/        # API 路由
│   │   └── services/       # 服務層
│   │       ├── base_client.py      # 抽象基類
│   │       ├── connection_manager.py
│   │       └── clients/            # 各資料庫客戶端
│   ├── requirements.txt
│   └── run.py
│
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js App Router
│   │   ├── components/     # UI 組件
│   │   └── lib/            # 工具函式
│   └── package.json
│
└── README.md
```

## 🔌 支援的向量資料庫

| 資料庫 | 狀態 | 說明 |
|--------|------|------|
| ChromaDB | ✅ 已實現 | 本地/遠端模式 |
| Milvus | 🔜 計劃中 | - |
| Pinecone | 🔜 計劃中 | - |
| Qdrant | 🔜 計劃中 | - |
| Weaviate | 🔜 計劃中 | - |
| pgvector | 🔜 計劃中 | - |

## 📖 API 文檔

啟動後端後訪問：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/connections` | 列出所有連線 |
| POST | `/api/connections` | 建立新連線 |
| POST | `/api/connections/{id}/connect` | 建立實際連線 |
| GET | `/api/collections` | 列出 Collections |
| POST | `/api/collections` | 建立 Collection |
| POST | `/api/vectors/search` | 向量搜尋 |

## 🛠️ 開發

### 新增資料庫支援

1. 在 `backend/app/services/clients/` 建立新的客戶端類
2. 繼承 `BaseVectorDBClient` 並實現所有抽象方法
3. 在 `connection_manager.py` 中註冊新客戶端

```python
# 範例：新增 Milvus 支援
from app.services.base_client import BaseVectorDBClient

class MilvusClient(BaseVectorDBClient):
    async def connect(self) -> bool:
        # 實現連線邏輯
        pass
    
    # ... 實現其他方法
```

## 📄 License

MIT License

---

Made with ❤️ for the Vector Database Community
