'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { collectionsApi, vectorsApi } from '@/lib/api';
import type { Vector, CollectionStats } from '@/lib/api';
import { useConnectionStore } from '@/lib/stores/connection-store';
import { ArrowLeft, Trash2 } from 'lucide-react';

export default function CollectionDetailPage() {
  const params = useParams();
  const collectionName = params.name as string;
  const { connection, ready, initialize } = useConnectionStore();

  const [vectors, setVectors] = useState<Vector[]>([]);
  const [stats, setStats] = useState<CollectionStats | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    initialize();
  }, [initialize]);

  const loadData = useCallback(async () => {
    if (!connection) return;
    setLoading(true);
    try {
      const [vectorsRes, statsRes] = await Promise.all([
        vectorsApi.list(connection.id, collectionName, 50, 0),
        collectionsApi.stats(connection.id, collectionName),
      ]);
      setVectors(vectorsRes.data);
      setStats(statsRes.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [connection, collectionName]);

  useEffect(() => {
    if (ready) loadData();
  }, [ready, loadData]);

  async function handleDelete(vectorId: string) {
    if (!connection) return;
    try {
      await vectorsApi.delete(connection.id, collectionName, vectorId);
      loadData();
    } catch {
      // ignore
    }
  }

  return (
    <div className="p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-center gap-3">
          <Link href="/collections">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              {collectionName}
            </h1>
            {stats && (
              <p className="text-sm text-zinc-500">
                {stats.vector_count} vectors | dim: {stats.dimension || 'N/A'}
              </p>
            )}
          </div>
        </div>

        {/* Vectors */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Documents ({vectors.length})</CardTitle>
              <Button variant="ghost" size="sm" onClick={loadData} disabled={loading}>
                {loading ? 'Loading...' : 'Refresh'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {vectors.length === 0 ? (
              <p className="text-sm text-zinc-400">No documents yet.</p>
            ) : (
              <div className="space-y-3">
                {vectors.map((v) => (
                  <div
                    key={v.id}
                    className="flex items-start justify-between rounded-lg border border-zinc-200 p-3 dark:border-zinc-800"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="break-words whitespace-pre-wrap text-sm text-zinc-900 dark:text-zinc-100">
                        {v.document || '(no content)'}
                      </p>
                      {v.metadata && Object.keys(v.metadata).length > 0 && (
                        <p className="mt-1 text-xs text-zinc-500">
                          {Object.entries(v.metadata)
                            .map(([k, val]) => `${k}: ${val}`)
                            .join(', ')}
                        </p>
                      )}
                      <p className="mt-1 font-mono text-xs text-zinc-400">{v.id}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      className="ml-2 text-red-500 hover:text-red-700"
                      onClick={() => handleDelete(v.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
