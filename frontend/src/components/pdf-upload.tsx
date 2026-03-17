'use client';

import { useState, useRef, useCallback } from 'react';
import { isAxiosError } from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { documentsApi } from '@/lib/api';
import type { DocumentUploadResponse } from '@/lib/api';

const ACCEPTED_EXTENSIONS = '.pdf,.docx,.txt,.md,.csv,.xlsx';

const FILE_TYPE_ICONS: Record<string, string> = {
  pdf: 'PDF',
  docx: 'DOC',
  txt: 'TXT',
  md: 'MD',
  csv: 'CSV',
  xlsx: 'XLS',
};

interface PDFUploadProps {
  connectionId: string;
  collectionName: string;
  onUploaded?: () => void;
}

export function PDFUpload({ connectionId, collectionName, onUploaded }: PDFUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [chunkSize, setChunkSize] = useState(500);
  const [chunkOverlap, setChunkOverlap] = useState(50);
  const [strategy, setStrategy] = useState('recursive');
  const [project, setProject] = useState('');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<DocumentUploadResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // URL scrape state
  const [scrapeUrl, setScrapeUrl] = useState('');
  const [scraping, setScraping] = useState(false);

  function getFileExtension(name: string): string {
    return name.split('.').pop()?.toLowerCase() || '';
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setSelectedFiles(files);
      setResults([]);
      setError(null);
    }
  }

  // Drag & Drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      setSelectedFiles(files);
      setResults([]);
      setError(null);
    }
  }, []);

  async function handleUpload() {
    if (selectedFiles.length === 0) return;

    setUploading(true);
    setProgress(0);
    setResults([]);
    setError(null);

    const uploadResults: DocumentUploadResponse[] = [];
    const errors: string[] = [];

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      try {
        setProgress(Math.round(((i) / selectedFiles.length) * 100));
        const { data } = await documentsApi.upload(
          file,
          connectionId,
          collectionName,
          chunkSize,
          chunkOverlap,
          strategy,
          project || undefined,
        );
        uploadResults.push(data);
      } catch (err: unknown) {
        if (isAxiosError(err) && err.response?.status === 409) {
          errors.push(`${file.name}: already uploaded`);
        } else {
          const msg = err instanceof Error ? err.message : String(err);
          errors.push(`${file.name}: ${msg}`);
        }
      }
    }

    setResults(uploadResults);
    if (errors.length > 0) {
      setError(errors.join('\n'));
    }
    setSelectedFiles([]);
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (uploadResults.length > 0) onUploaded?.();
    setUploading(false);
    setProgress(0);
  }

  async function handleScrape() {
    if (!scrapeUrl.trim()) return;

    setScraping(true);
    setResults([]);
    setError(null);

    try {
      const { data } = await documentsApi.scrape({
        url: scrapeUrl.trim(),
        connection_id: connectionId,
        collection_name: collectionName,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
        strategy,
        project: project || undefined,
      });
      setResults([data]);
      setScrapeUrl('');
      onUploaded?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Scrape failed: ${msg}`);
    } finally {
      setScraping(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Documents</CardTitle>
        <CardDescription>
          Upload files or scrape web pages. Supports PDF, Word, TXT, Markdown, CSV, Excel.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Drag & Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`cursor-pointer rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
            isDragging
              ? 'border-zinc-500 bg-zinc-100 dark:border-zinc-400 dark:bg-zinc-800'
              : 'border-zinc-300 hover:border-zinc-400 dark:border-zinc-700 dark:hover:border-zinc-600'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS}
            multiple
            onChange={handleFileChange}
            className="hidden"
          />
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {isDragging
              ? 'Drop files here...'
              : 'Click or drag files here'}
          </p>
          <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
            PDF, DOCX, TXT, MD, CSV, XLSX
          </p>
        </div>

        {/* Selected files */}
        {selectedFiles.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {selectedFiles.map((file, idx) => {
              const ext = getFileExtension(file.name);
              return (
                <div
                  key={idx}
                  className="flex items-center gap-1.5 rounded-md bg-zinc-100 px-2 py-1 text-xs dark:bg-zinc-800"
                >
                  <span className="font-mono font-bold text-zinc-600 dark:text-zinc-400">
                    {FILE_TYPE_ICONS[ext] || ext.toUpperCase()}
                  </span>
                  <span className="max-w-[150px] truncate text-zinc-700 dark:text-zinc-300">
                    {file.name}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* Web scrape */}
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Or scrape URL
            </label>
            <Input
              className="mt-1"
              placeholder="https://example.com/article"
              value={scrapeUrl}
              onChange={(e) => setScrapeUrl(e.target.value)}
              disabled={scraping}
            />
          </div>
          <Button
            onClick={handleScrape}
            disabled={!scrapeUrl.trim() || scraping}
            variant="outline"
            className="h-9"
          >
            {scraping ? 'Scraping...' : 'Scrape'}
          </Button>
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

        {/* Upload button + progress */}
        <div className="space-y-2">
          <Button
            onClick={handleUpload}
            disabled={selectedFiles.length === 0 || uploading}
          >
            {uploading ? 'Processing...' : `Upload ${selectedFiles.length > 0 ? `(${selectedFiles.length} files)` : ''}`}
          </Button>

          {uploading && progress > 0 && (
            <div className="w-full rounded-full bg-zinc-200 h-2 dark:bg-zinc-800">
              <div
                className="h-2 rounded-full bg-zinc-600 transition-all dark:bg-zinc-400"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}
        </div>

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-2">
            {results.map((r, idx) => (
              <div key={idx} className="rounded-lg bg-green-50 p-3 dark:bg-green-950">
                <p className="text-sm font-medium text-green-800 dark:text-green-200">
                  {r.message}
                </p>
                <div className="mt-1 space-y-0.5 text-xs text-green-600 dark:text-green-400">
                  <p>File: {r.filename} ({r.file_type})</p>
                  <p>Pages: {r.total_pages} | Chunks: {r.chunks_inserted} | Strategy: {r.chunking_strategy}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <p className="whitespace-pre-wrap text-sm text-red-600">{error}</p>
        )}
      </CardContent>
    </Card>
  );
}
