'use client';

import { useState } from 'react';
import { isAxiosError } from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { documentsApi } from '@/lib/api';
import type { BatchScanResponse, CollectionMappingMode } from '@/lib/api';
import { useBatchImport } from '@/lib/hooks/use-batch-import';
import type { FileProgress } from '@/lib/hooks/use-batch-import';

interface BatchImportProps {
  connectionId: string;
  collectionName: string;
}

export function BatchImport({ connectionId, collectionName }: BatchImportProps) {
  // Scan state
  const [directoryPath, setDirectoryPath] = useState('');
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<BatchScanResponse | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);

  // Config state
  const [mappingMode, setMappingMode] = useState<CollectionMappingMode>('single');
  const [defaultCollection, setDefaultCollection] = useState('');
  const [chunkSize, setChunkSize] = useState(500);
  const [chunkOverlap, setChunkOverlap] = useState(50);
  const [strategy, setStrategy] = useState('recursive');
  const [project, setProject] = useState('');

  // Import hook
  const {
    state: importState,
    isImporting,
    fileProgress,
    progressPercent,
    summary,
    error: importError,
    createdCollections,
    startImport,
    cancelImport,
    reset,
  } = useBatchImport();

  async function handleScan() {
    if (!directoryPath.trim()) return;

    setScanning(true);
    setScanResult(null);
    setScanError(null);

    try {
      const { data } = await documentsApi.batchScan({
        directory_path: directoryPath.trim(),
        connection_id: connectionId,
      });
      setScanResult(data);
    } catch (err: unknown) {
      if (isAxiosError(err) && err.response?.data?.detail) {
        setScanError(err.response.data.detail);
      } else {
        setScanError(err instanceof Error ? err.message : String(err));
      }
    } finally {
      setScanning(false);
    }
  }

  function handleImport() {
    if (!scanResult) return;

    const targetCollection =
      mappingMode === 'single' ? collectionName : '';

    startImport({
      directory_path: directoryPath.trim(),
      connection_id: connectionId,
      collection_name: targetCollection,
      mapping_mode: mappingMode,
      default_collection: defaultCollection || collectionName,
      chunk_size: chunkSize,
      chunk_overlap: chunkOverlap,
      strategy,
      project: project || undefined,
    });
  }

  function handleReset() {
    reset();
    setScanResult(null);
    setScanError(null);
  }

  // Compute extension stats from scan result
  function getExtStats() {
    if (!scanResult) return {};
    const stats: Record<string, number> = {};
    for (const f of scanResult.files) {
      stats[f.extension] = (stats[f.extension] || 0) + 1;
    }
    return stats;
  }

  function formatSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function statusIcon(status: FileProgress['status']) {
    switch (status) {
      case 'pending': return '○';
      case 'processing': return '◌';
      case 'done': return '●';
      case 'error': return '✕';
    }
  }

  function statusColor(status: FileProgress['status']) {
    switch (status) {
      case 'pending': return 'text-zinc-400';
      case 'processing': return 'text-blue-500 animate-pulse';
      case 'done': return 'text-green-500';
      case 'error': return 'text-red-500';
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Batch Import</CardTitle>
        <CardDescription>
          Scan a server-side directory and import all supported files into the vector database.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Phase 1: Scan */}
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Directory Path (server-side)
            </label>
            <Input
              className="mt-1"
              placeholder="D:\temp\documents"
              value={directoryPath}
              onChange={(e) => setDirectoryPath(e.target.value)}
              disabled={scanning || isImporting}
            />
          </div>
          <Button
            onClick={handleScan}
            disabled={!directoryPath.trim() || scanning || isImporting}
            variant="outline"
            className="h-9"
          >
            {scanning ? 'Scanning...' : 'Scan'}
          </Button>
        </div>

        {scanError && (
          <p className="text-sm text-red-600">{scanError}</p>
        )}

        {/* Scan Result */}
        {scanResult && importState === 'idle' && (
          <div className="space-y-4">
            <div className="rounded-lg bg-zinc-50 p-4 dark:bg-zinc-900">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Found <span className="font-bold">{scanResult.total_files}</span> files
                </p>
                <div className="flex gap-1.5">
                  {Object.entries(getExtStats()).map(([ext, count]) => (
                    <Badge key={ext} variant="secondary" className="text-xs">
                      {ext} ({count})
                    </Badge>
                  ))}
                </div>
              </div>

              {scanResult.subdirectories.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs text-zinc-500">
                    Subdirectories: {scanResult.subdirectories.join(', ')}
                  </p>
                </div>
              )}

              <p className="mt-1 text-xs text-zinc-400">
                Total size: {formatSize(scanResult.files.reduce((s, f) => s + f.file_size, 0))}
              </p>
            </div>

            {/* Mapping mode */}
            <div>
              <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Collection Mapping
              </label>
              <div className="mt-2 space-y-2">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="mappingMode"
                    value="single"
                    checked={mappingMode === 'single'}
                    onChange={() => setMappingMode('single')}
                    className="accent-zinc-700"
                  />
                  <span className="text-zinc-700 dark:text-zinc-300">
                    All into current collection
                    <span className="ml-1 text-xs text-zinc-400">({collectionName})</span>
                  </span>
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="mappingMode"
                    value="auto"
                    checked={mappingMode === 'auto'}
                    onChange={() => setMappingMode('auto')}
                    className="accent-zinc-700"
                  />
                  <span className="text-zinc-700 dark:text-zinc-300">
                    Auto-map by subdirectory
                  </span>
                </label>
              </div>

              {mappingMode === 'auto' && (
                <div className="mt-2">
                  <label className="text-xs text-zinc-500">
                    Default collection for root-level files
                  </label>
                  <Input
                    className="mt-1"
                    placeholder={collectionName}
                    value={defaultCollection}
                    onChange={(e) => setDefaultCollection(e.target.value)}
                  />
                </div>
              )}
            </div>

            {/* Project tag */}
            <div>
              <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                專案名稱（選填）
              </label>
              <Input
                className="mt-1"
                placeholder="例如：CEO楊的財富教室-13"
                value={project}
                onChange={(e) => setProject(e.target.value)}
              />
            </div>

            {/* Chunking params */}
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Chunk Size
                </label>
                <Input
                  type="number"
                  className="mt-1"
                  min={50}
                  max={5000}
                  value={chunkSize}
                  onChange={(e) => setChunkSize(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Overlap
                </label>
                <Input
                  type="number"
                  className="mt-1"
                  min={0}
                  max={500}
                  value={chunkOverlap}
                  onChange={(e) => setChunkOverlap(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Strategy
                </label>
                <select
                  className="mt-1 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                >
                  <option value="recursive">Recursive</option>
                  <option value="character">Character</option>
                  <option value="semantic">Semantic</option>
                </select>
              </div>
            </div>

            {/* Import button */}
            <Button onClick={handleImport} disabled={scanResult.total_files === 0}>
              Import {scanResult.total_files} files
            </Button>
          </div>
        )}

        {/* Phase 2: Import progress */}
        {(isImporting || importState === 'done') && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                {isImporting ? 'Importing...' : 'Import complete'}
              </p>
              <span className="text-xs text-zinc-500">{progressPercent}%</span>
            </div>

            <Progress value={progressPercent} className="h-2" />

            {createdCollections.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {createdCollections.map((name) => (
                  <Badge key={name} variant="outline" className="text-xs">
                    + {name}
                  </Badge>
                ))}
              </div>
            )}

            {/* File status list */}
            <ScrollArea className="h-64 rounded-md border border-zinc-200 dark:border-zinc-800">
              <div className="p-2 space-y-0.5">
                {fileProgress
                  .filter((f) => f.filename)
                  .map((f) => (
                    <div
                      key={f.index}
                      className="flex items-center gap-2 rounded px-2 py-1 text-xs hover:bg-zinc-50 dark:hover:bg-zinc-900"
                    >
                      <span className={statusColor(f.status)}>
                        {statusIcon(f.status)}
                      </span>
                      <span className="flex-1 truncate text-zinc-700 dark:text-zinc-300">
                        {f.filename}
                      </span>
                      {f.status === 'done' && (
                        <span className="text-zinc-400">
                          {f.chunksInserted} chunks
                        </span>
                      )}
                      {f.status === 'error' && (
                        <span className="text-red-400 truncate max-w-[200px]" title={f.error}>
                          {f.error}
                        </span>
                      )}
                      {f.collection && (
                        <Badge variant="secondary" className="text-[10px] px-1">
                          {f.collection}
                        </Badge>
                      )}
                    </div>
                  ))}
              </div>
            </ScrollArea>

            {/* Summary */}
            {summary && (
              <div className="rounded-lg bg-green-50 p-3 dark:bg-green-950">
                <p className="text-sm font-medium text-green-800 dark:text-green-200">
                  Import finished
                </p>
                <div className="mt-1 text-xs text-green-600 dark:text-green-400 space-y-0.5">
                  <p>Total files: {summary.totalFiles}</p>
                  <p>Success: {summary.success} | Failed: {summary.failed}</p>
                  <p>Total chunks inserted: {summary.totalChunks}</p>
                </div>
              </div>
            )}

            {importError && (
              <p className="text-sm text-red-600">{importError}</p>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              {isImporting && (
                <Button variant="outline" onClick={cancelImport}>
                  Cancel
                </Button>
              )}
              {importState === 'done' && (
                <Button variant="outline" onClick={handleReset}>
                  Reset
                </Button>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
