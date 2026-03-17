'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { vectorsApi } from '@/lib/api';
import type { VectorSearchResult } from '@/lib/api';
import { useConnectionStore } from '@/lib/stores/connection-store';
import { Search as SearchIcon } from 'lucide-react';

export default function SearchPage() {
  const { connection, ready, initialize, activeCollectionName } =
    useConnectionStore();

  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(10);
  const [results, setResults] = useState<VectorSearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    initialize();
  }, [initialize]);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!connection || !query.trim()) return;

    setSearching(true);
    try {
      const { data } = await vectorsApi.search(
        connection.id,
        activeCollectionName,
        { query_text: query.trim(), top_k: topK }
      );
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
          Semantic Search
        </h1>

        {/* Search form */}
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSearch} className="flex items-end gap-3">
              <div className="flex-1">
                <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Search Query
                </label>
                <Input
                  className="mt-1"
                  placeholder="Enter your search query..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  required
                />
              </div>
              <div className="w-24">
                <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Top K
                </label>
                <Input
                  type="number"
                  className="mt-1"
                  min={1}
                  max={100}
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                />
              </div>
              <Button type="submit" disabled={searching || !query.trim()}>
                <SearchIcon className="mr-1 h-4 w-4" />
                {searching ? 'Searching...' : 'Search'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm text-zinc-500">{results.length} results found</p>
            {results.map((r, idx) => {
              const scorePercent = Math.max(0, Math.min(100, r.score * 100));
              return (
                <Card key={r.id}>
                  <CardContent className="pt-4">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs text-zinc-400">#{idx + 1}</span>
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-24 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
                          <div
                            className="h-full rounded-full bg-zinc-600 dark:bg-zinc-400"
                            style={{ width: `${scorePercent}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs text-zinc-500">
                          {scorePercent.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                    <p className="break-words whitespace-pre-wrap text-sm text-zinc-900 dark:text-zinc-100">
                      {r.document || '(no content)'}
                    </p>
                    {r.metadata && Object.keys(r.metadata).length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {Object.entries(r.metadata).map(([k, v]) => (
                          <span
                            key={k}
                            className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
                          >
                            {k}: {String(v)}
                          </span>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
