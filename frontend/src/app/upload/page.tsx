'use client';

import { useEffect } from 'react';
import { PDFUpload } from '@/components/pdf-upload';
import { BatchImport } from '@/components/batch-import';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useConnectionStore } from '@/lib/stores/connection-store';

export default function UploadPage() {
  const { connection, ready, initializing, initError, initialize, activeCollectionName } =
    useConnectionStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  if (initializing) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-zinc-500">Connecting...</p>
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
    <div className="p-8">
      <div className="mx-auto max-w-2xl space-y-6">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
          Upload Documents
        </h1>
        <Tabs defaultValue="upload">
          <TabsList>
            <TabsTrigger value="upload">Upload Files</TabsTrigger>
            <TabsTrigger value="batch">Batch Import</TabsTrigger>
          </TabsList>
          <TabsContent value="upload">
            <PDFUpload
              connectionId={connection.id}
              collectionName={activeCollectionName}
            />
          </TabsContent>
          <TabsContent value="batch">
            <BatchImport
              connectionId={connection.id}
              collectionName={activeCollectionName}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
