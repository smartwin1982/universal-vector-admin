'use client';

import { useEffect } from 'react';
import { ChatPanel } from '@/components/chat/chat-panel';
import { useConnectionStore } from '@/lib/stores/connection-store';

export default function ChatPage() {
  const { connection, ready, initializing, initError, initialize, activeCollectionName } =
    useConnectionStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  if (initializing) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-zinc-500">Connecting to vector database...</p>
      </div>
    );
  }

  if (initError || !connection) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-red-500">{initError || 'No connection'}</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col p-6">
      <h1 className="mb-4 text-xl font-bold text-zinc-900 dark:text-zinc-50">
        AI Chat
      </h1>
      <div className="min-h-0 flex-1">
        <ChatPanel
          connectionId={connection.id}
          collectionName={activeCollectionName}
        />
      </div>
    </div>
  );
}
