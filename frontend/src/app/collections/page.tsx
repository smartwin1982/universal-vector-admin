'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { collectionsApi } from '@/lib/api';
import type { Collection } from '@/lib/api';
import { useConnectionStore } from '@/lib/stores/connection-store';
import { Database, Trash2, Plus } from 'lucide-react';

export default function CollectionsPage() {
  const { connection, ready, initialize } = useConnectionStore();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(false);

  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDimension, setNewDimension] = useState(384);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    initialize();
  }, [initialize]);

  const loadCollections = useCallback(async () => {
    if (!connection) return;
    setLoading(true);
    try {
      const { data } = await collectionsApi.list(connection.id);
      setCollections(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [connection]);

  useEffect(() => {
    if (ready) loadCollections();
  }, [ready, loadCollections]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!connection || !newName.trim()) return;
    setCreating(true);
    try {
      await collectionsApi.create(connection.id, {
        name: newName.trim(),
        dimension: newDimension,
        distance_metric: 'cosine',
      });
      setNewName('');
      setShowCreate(false);
      loadCollections();
    } catch {
      // ignore
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(name: string) {
    if (!connection) return;
    if (!confirm(`Delete collection "${name}"?`)) return;
    try {
      await collectionsApi.delete(connection.id, name);
      loadCollections();
    } catch {
      // ignore
    }
  }

  return (
    <div className="p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
            Collections
          </h1>
          <Button onClick={() => setShowCreate(!showCreate)} size="sm">
            <Plus className="mr-1 h-4 w-4" />
            New Collection
          </Button>
        </div>

        {/* Create form */}
        {showCreate && (
          <Card>
            <CardContent className="pt-6">
              <form onSubmit={handleCreate} className="flex items-end gap-3">
                <div className="flex-1">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Name</label>
                  <Input
                    className="mt-1"
                    placeholder="collection_name"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    required
                  />
                </div>
                <div className="w-32">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Dimension</label>
                  <Input
                    type="number"
                    className="mt-1"
                    value={newDimension}
                    onChange={(e) => setNewDimension(Number(e.target.value))}
                  />
                </div>
                <Button type="submit" disabled={creating || !newName.trim()}>
                  {creating ? 'Creating...' : 'Create'}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Collections list */}
        {loading ? (
          <p className="text-sm text-zinc-500">Loading...</p>
        ) : collections.length === 0 ? (
          <p className="text-sm text-zinc-500">No collections yet.</p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {collections.map((col) => (
              <Card key={col.name}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <Link
                      href={`/collections/${col.name}`}
                      className="flex items-center gap-2 hover:underline"
                    >
                      <Database className="h-4 w-4 text-zinc-500" />
                      <CardTitle className="text-base">{col.name}</CardTitle>
                    </Link>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      onClick={() => handleDelete(col.name)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-4 text-xs text-zinc-500">
                    {col.description && <span>{col.description}</span>}
                    {col.dimension && <span>dim: {col.dimension}</span>}
                    {col.distance_metric && <span>{col.distance_metric}</span>}
                  </div>
                  {col.stats && (
                    <p className="mt-2 text-xs text-zinc-400">
                      {col.stats.vector_count} vectors
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
