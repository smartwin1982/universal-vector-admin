'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ragApi } from '@/lib/api';
import { useConnectionStore } from '@/lib/stores/connection-store';

export default function SettingsPage() {
  const { connection, ready, initialize } = useConnectionStore();
  const [llmHealth, setLlmHealth] = useState<{
    status: string;
    llm_provider: string;
    healthy: boolean;
  } | null>(null);

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    ragApi.health().then(({ data }) => setLlmHealth(data)).catch(() => {});
  }, []);

  return (
    <div className="p-8">
      <div className="mx-auto max-w-3xl space-y-6">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
          Settings
        </h1>

        {/* Connection info */}
        <Card>
          <CardHeader>
            <CardTitle>Vector Database</CardTitle>
            <CardDescription>Current connection information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Status</span>
              <Badge variant={connection?.is_connected ? 'default' : 'destructive'}>
                {connection?.is_connected ? 'Connected' : 'Disconnected'}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Type</span>
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {connection?.db_type || 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Name</span>
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {connection?.name || 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">ID</span>
              <span className="font-mono text-xs text-zinc-500">
                {connection?.id || 'N/A'}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* LLM info */}
        <Card>
          <CardHeader>
            <CardTitle>LLM Provider</CardTitle>
            <CardDescription>Language model configuration</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Provider</span>
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                {llmHealth?.llm_provider || 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Health</span>
              <Badge variant={llmHealth?.healthy ? 'default' : 'destructive'}>
                {llmHealth?.status || 'Unknown'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Embedding info */}
        <Card>
          <CardHeader>
            <CardTitle>Embedding Model</CardTitle>
            <CardDescription>Text embedding configuration</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Model</span>
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                paraphrase-multilingual-MiniLM-L12-v2
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-zinc-600 dark:text-zinc-400">Dimension</span>
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                384
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
