'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { connectionsApi, collectionsApi, ragApi } from '@/lib/api';
import type { Connection, CollectionStats } from '@/lib/api';
import { MessageSquare, Database, Search, Upload } from 'lucide-react';
import { useConnectionStore } from '@/lib/stores/connection-store';

export default function DashboardPage() {
  const { connection, ready, initialize } = useConnectionStore();
  const [collectionsCount, setCollectionsCount] = useState(0);
  const [llmStatus, setLlmStatus] = useState<string>('checking...');
  const [llmProvider, setLlmProvider] = useState<string>('');

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (!ready || !connection) return;

    // Load collection count
    collectionsApi.list(connection.id).then(({ data }) => {
      setCollectionsCount(data.length);
    }).catch(() => {});

    // Check LLM health
    ragApi.health().then(({ data }) => {
      setLlmStatus(data.healthy ? 'Connected' : 'Unavailable');
      setLlmProvider(data.llm_provider);
    }).catch(() => {
      setLlmStatus('Error');
    });
  }, [ready, connection]);

  return (
    <div className="p-8">
      <div className="mx-auto max-w-5xl space-y-8">
        {/* Title */}
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            Universal Vector Admin - RAG Management Platform
          </p>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-zinc-100 p-2 dark:bg-zinc-800">
                  <Database className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                    {collectionsCount}
                  </p>
                  <p className="text-xs text-zinc-500">Collections</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-zinc-100 p-2 dark:bg-zinc-800">
                  <MessageSquare className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
                </div>
                <div>
                  <p className="text-sm font-bold text-zinc-900 dark:text-zinc-50">
                    {llmStatus}
                  </p>
                  <p className="text-xs text-zinc-500">LLM ({llmProvider})</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-zinc-100 p-2 dark:bg-zinc-800">
                  <Database className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
                </div>
                <div>
                  <p className="text-sm font-bold text-zinc-900 dark:text-zinc-50">
                    {connection?.is_connected ? 'Connected' : 'Disconnected'}
                  </p>
                  <p className="text-xs text-zinc-500">Vector DB</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-zinc-100 p-2 dark:bg-zinc-800">
                  <Search className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
                </div>
                <div>
                  <p className="text-sm font-bold text-zinc-900 dark:text-zinc-50">
                    384-dim
                  </p>
                  <p className="text-xs text-zinc-500">Embedding</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="mb-4 text-lg font-semibold text-zinc-900 dark:text-zinc-50">
            Quick Actions
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Link href="/chat">
              <Card className="cursor-pointer transition-shadow hover:shadow-md">
                <CardContent className="flex items-center gap-3 pt-6">
                  <MessageSquare className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
                  <div>
                    <p className="font-medium text-zinc-900 dark:text-zinc-50">Chat</p>
                    <p className="text-xs text-zinc-500">Ask questions with RAG</p>
                  </div>
                </CardContent>
              </Card>
            </Link>

            <Link href="/upload">
              <Card className="cursor-pointer transition-shadow hover:shadow-md">
                <CardContent className="flex items-center gap-3 pt-6">
                  <Upload className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
                  <div>
                    <p className="font-medium text-zinc-900 dark:text-zinc-50">Upload</p>
                    <p className="text-xs text-zinc-500">Add documents</p>
                  </div>
                </CardContent>
              </Card>
            </Link>

            <Link href="/collections">
              <Card className="cursor-pointer transition-shadow hover:shadow-md">
                <CardContent className="flex items-center gap-3 pt-6">
                  <Database className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
                  <div>
                    <p className="font-medium text-zinc-900 dark:text-zinc-50">Collections</p>
                    <p className="text-xs text-zinc-500">Manage your data</p>
                  </div>
                </CardContent>
              </Card>
            </Link>

            <Link href="/search">
              <Card className="cursor-pointer transition-shadow hover:shadow-md">
                <CardContent className="flex items-center gap-3 pt-6">
                  <Search className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
                  <div>
                    <p className="font-medium text-zinc-900 dark:text-zinc-50">Search</p>
                    <p className="text-xs text-zinc-500">Semantic search</p>
                  </div>
                </CardContent>
              </Card>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
