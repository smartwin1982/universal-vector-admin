/**
 * API 客戶端
 */
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 類型定義
export interface Connection {
  id: string;
  name: string;
  db_type: 'chroma' | 'lancedb' | 'milvus' | 'pinecone' | 'qdrant' | 'weaviate' | 'pgvector';
  host?: string;
  port?: number;
  api_key?: string;
  extra_config?: Record<string, unknown>;
  is_connected: boolean;
  created_at: string;
  updated_at?: string;
}

export interface ConnectionCreate {
  name: string;
  db_type: Connection['db_type'];
  host?: string;
  port?: number;
  api_key?: string;
  extra_config?: Record<string, unknown>;
}

export interface Collection {
  id: string;
  name: string;
  connection_id: string;
  description?: string;
  dimension?: number;
  distance_metric?: string;
  metadata?: Record<string, unknown>;
  stats?: CollectionStats;
  created_at: string;
}

export interface CollectionCreate {
  name: string;
  description?: string;
  dimension?: number;
  distance_metric?: string;
  metadata?: Record<string, unknown>;
}

export interface CollectionStats {
  vector_count: number;
  dimension?: number;
  index_status?: string;
}

export interface Vector {
  id: string;
  collection_id: string;
  embedding: number[];
  metadata?: Record<string, unknown>;
  document?: string;
}

export interface VectorCreate {
  id?: string;
  embedding?: number[];
  document?: string;
  metadata?: Record<string, unknown>;
}

export interface VectorQuery {
  embedding?: number[];
  query_text?: string;
  top_k?: number;
  filter?: Record<string, unknown>;
  include_embeddings?: boolean;
}

export interface VectorSearchResult {
  id: string;
  score: number;
  embedding?: number[];
  metadata?: Record<string, unknown>;
  document?: string;
}

// RAG 類型定義
export interface RAGAskRequest {
  question: string;
  connection_id: string;
  collection_name: string;
  top_k?: number;
  llm_provider?: string;
  session_id?: string;
  project?: string;
}

export interface RAGSourceDocument {
  id: string;
  document: string;
  score: number;
}

export interface RAGAskResponse {
  answer: string;
  sources: RAGSourceDocument[];
  llm_provider: string;
}

export interface RAGHealthResponse {
  status: string;
  llm_provider: string;
  healthy: boolean;
  detail?: string;
}

// PDF 類型定義
export interface PDFUploadResponse {
  filename: string;
  total_pages: number;
  total_chunks: number;
  chunks_inserted: number;
  message: string;
}

// API 函式
export const connectionsApi = {
  list: () => api.get<Connection[]>('/api/connections'),
  create: (data: ConnectionCreate) => api.post<Connection>('/api/connections', data),
  get: (id: string) => api.get<Connection>(`/api/connections/${id}`),
  delete: (id: string) => api.delete(`/api/connections/${id}`),
  connect: (id: string) => api.post(`/api/connections/${id}/connect`),
  disconnect: (id: string) => api.post(`/api/connections/${id}/disconnect`),
  test: (data: Omit<ConnectionCreate, 'name'>) => api.post('/api/connections/test', data),
};

export const collectionsApi = {
  list: (connectionId: string) => 
    api.get<Collection[]>('/api/collections', { params: { connection_id: connectionId } }),
  create: (connectionId: string, data: CollectionCreate) => 
    api.post<Collection>('/api/collections', data, { params: { connection_id: connectionId } }),
  get: (connectionId: string, name: string) => 
    api.get<Collection>(`/api/collections/${name}`, { params: { connection_id: connectionId } }),
  delete: (connectionId: string, name: string) => 
    api.delete(`/api/collections/${name}`, { params: { connection_id: connectionId } }),
  stats: (connectionId: string, name: string) => 
    api.get<CollectionStats>(`/api/collections/${name}/stats`, { params: { connection_id: connectionId } }),
};

export const vectorsApi = {
  list: (connectionId: string, collectionName: string, limit = 100, offset = 0) =>
    api.get<Vector[]>('/api/vectors', { 
      params: { connection_id: connectionId, collection_name: collectionName, limit, offset } 
    }),
  create: (connectionId: string, collectionName: string, data: VectorCreate) =>
    api.post<Vector>('/api/vectors', data, { 
      params: { connection_id: connectionId, collection_name: collectionName } 
    }),
  search: (connectionId: string, collectionName: string, query: VectorQuery) =>
    api.post<VectorSearchResult[]>('/api/vectors/search', query, { 
      params: { connection_id: connectionId, collection_name: collectionName } 
    }),
  get: (connectionId: string, collectionName: string, vectorId: string) =>
    api.get<Vector>(`/api/vectors/${vectorId}`, { 
      params: { connection_id: connectionId, collection_name: collectionName } 
    }),
  delete: (connectionId: string, collectionName: string, vectorId: string) =>
    api.delete(`/api/vectors/${vectorId}`, {
      params: { connection_id: connectionId, collection_name: collectionName }
    }),
};

export const ragApi = {
  ask: (data: RAGAskRequest) =>
    api.post<RAGAskResponse>('/api/rag/ask', data),
  health: () =>
    api.get<RAGHealthResponse>('/api/rag/health'),
};

// Session 類型定義
export interface SessionCreateResponse {
  session_id: string;
  created_at: string;
}

export interface SessionMessage {
  role: string;
  content: string;
  timestamp: string;
}

export interface SessionResponse {
  session_id: string;
  messages: SessionMessage[];
  created_at: string;
  updated_at: string;
}

export const sessionsApi = {
  create: () =>
    api.post<SessionCreateResponse>('/api/rag/sessions'),
  get: (sessionId: string) =>
    api.get<SessionResponse>(`/api/rag/sessions/${sessionId}`),
  delete: (sessionId: string) =>
    api.delete(`/api/rag/sessions/${sessionId}`),
};

export const pdfApi = {
  upload: (
    file: File,
    connectionId: string,
    collectionName: string,
    chunkSize: number,
    chunkOverlap: number,
    onUploadProgress?: (progress: number) => void,
  ) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<PDFUploadResponse>('/api/pdf/upload', formData, {
      params: {
        connection_id: connectionId,
        collection_name: collectionName,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      },
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onUploadProgress && e.total) {
          onUploadProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    });
  },
};

// Document 類型定義
export interface DocumentUploadResponse {
  filename: string;
  file_type: string;
  total_pages: number;
  total_chunks: number;
  chunks_inserted: number;
  chunking_strategy: string;
  message: string;
}

export interface WebScrapeRequest {
  url: string;
  connection_id: string;
  collection_name: string;
  chunk_size?: number;
  chunk_overlap?: number;
  strategy?: string;
  project?: string;
}

// 批次匯入類型定義
export type CollectionMappingMode = 'single' | 'auto';

export interface BatchScanRequest {
  directory_path: string;
  connection_id: string;
}

export interface BatchScanFileInfo {
  relative_path: string;
  filename: string;
  extension: string;
  file_size: number;
  subdirectory: string;
}

export interface BatchScanResponse {
  directory_path: string;
  total_files: number;
  files: BatchScanFileInfo[];
  subdirectories: string[];
  supported_extensions: string[];
}

export interface BatchImportRequest {
  directory_path: string;
  connection_id: string;
  collection_name: string;
  mapping_mode: CollectionMappingMode;
  default_collection?: string;
  chunk_size: number;
  chunk_overlap: number;
  strategy: string;
  project?: string;
}

export interface BatchSSEEvent {
  event: string;
  data: Record<string, unknown>;
}

export const documentsApi = {
  upload: (
    file: File,
    connectionId: string,
    collectionName: string,
    chunkSize: number,
    chunkOverlap: number,
    strategy: string = 'recursive',
    project?: string,
  ) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<DocumentUploadResponse>('/api/documents/upload', formData, {
      params: {
        connection_id: connectionId,
        collection_name: collectionName,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
        strategy,
        ...(project ? { project } : {}),
      },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  scrape: (data: WebScrapeRequest) =>
    api.post<DocumentUploadResponse>('/api/documents/scrape', data),
  supportedFormats: () =>
    api.get<{ formats: string[] }>('/api/documents/supported-formats'),
  batchScan: (data: BatchScanRequest) =>
    api.post<BatchScanResponse>('/api/documents/batch/scan', data),
};
