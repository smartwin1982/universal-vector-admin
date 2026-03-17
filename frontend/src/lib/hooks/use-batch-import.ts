import { useState, useCallback, useRef } from 'react';
import type { BatchImportRequest } from '@/lib/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type FileStatus = 'pending' | 'processing' | 'done' | 'error';

export interface FileProgress {
  index: number;
  filename: string;
  collection: string;
  status: FileStatus;
  pages?: number;
  chunksInserted?: number;
  error?: string;
}

export interface ImportSummary {
  totalFiles: number;
  success: number;
  failed: number;
  totalChunks: number;
}

type ImportState = 'idle' | 'importing' | 'done';

export function useBatchImport() {
  const [state, setState] = useState<ImportState>('idle');
  const [fileProgress, setFileProgress] = useState<FileProgress[]>([]);
  const [summary, setSummary] = useState<ImportSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createdCollections, setCreatedCollections] = useState<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const progressPercent = useCallback(() => {
    if (fileProgress.length === 0) return 0;
    const done = fileProgress.filter(
      (f) => f.status === 'done' || f.status === 'error',
    ).length;
    return Math.round((done / fileProgress.length) * 100);
  }, [fileProgress]);

  const startImport = useCallback(async (req: BatchImportRequest) => {
    setState('importing');
    setFileProgress([]);
    setSummary(null);
    setError(null);
    setCreatedCollections([]);

    const abortController = new AbortController();
    abortRef.current = abortController;

    try {
      const resp = await fetch(`${API_BASE_URL}/api/documents/batch/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
        signal: abortController.signal,
      });

      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(errText || `HTTP ${resp.status}`);
      }

      const reader = resp.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue;

          const lines = eventBlock.split('\n');
          let eventType = '';
          let eventData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7);
            } else if (line.startsWith('data: ')) {
              eventData = line.slice(6);
            }
          }

          if (!eventType || !eventData) continue;

          const data = JSON.parse(eventData);

          switch (eventType) {
            case 'scan_complete':
              // Initialize file progress array
              setFileProgress(
                Array.from({ length: data.total_files }, (_, i) => ({
                  index: i,
                  filename: '',
                  collection: '',
                  status: 'pending' as FileStatus,
                })),
              );
              break;

            case 'collection_created':
              setCreatedCollections((prev) => [...prev, data.name]);
              break;

            case 'file_start':
              setFileProgress((prev) => {
                const updated = [...prev];
                if (updated[data.index]) {
                  updated[data.index] = {
                    ...updated[data.index],
                    filename: data.filename,
                    collection: data.collection,
                    status: 'processing',
                  };
                }
                return updated;
              });
              break;

            case 'file_done':
              setFileProgress((prev) => {
                const updated = [...prev];
                if (updated[data.index]) {
                  updated[data.index] = {
                    ...updated[data.index],
                    filename: data.filename,
                    status: 'done',
                    pages: data.pages,
                    chunksInserted: data.chunks_inserted,
                  };
                }
                return updated;
              });
              break;

            case 'file_error':
              setFileProgress((prev) => {
                const updated = [...prev];
                if (updated[data.index]) {
                  updated[data.index] = {
                    ...updated[data.index],
                    filename: data.filename,
                    status: 'error',
                    error: data.error,
                  };
                }
                return updated;
              });
              break;

            case 'done':
              setSummary({
                totalFiles: data.total_files,
                success: data.success,
                failed: data.failed,
                totalChunks: data.total_chunks,
              });
              setState('done');
              break;

            case 'error':
              setError(data.message);
              setState('done');
              break;
          }
        }
      }

      // If state wasn't set to 'done' by SSE event
      setState((s) => (s === 'importing' ? 'done' : s));
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        setState('idle');
        return;
      }
      setError(err instanceof Error ? err.message : String(err));
      setState('done');
    } finally {
      abortRef.current = null;
    }
  }, []);

  const cancelImport = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    setState('idle');
    setFileProgress([]);
    setSummary(null);
    setError(null);
    setCreatedCollections([]);
  }, []);

  return {
    state,
    isImporting: state === 'importing',
    fileProgress,
    progressPercent: progressPercent(),
    summary,
    error,
    createdCollections,
    startImport,
    cancelImport,
    reset,
  };
}
