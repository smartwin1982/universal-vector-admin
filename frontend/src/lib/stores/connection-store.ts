/**
 * 連線狀態管理 — 全域 Zustand store
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Connection } from '@/lib/api';
import { connectionsApi, collectionsApi } from '@/lib/api';

const DEFAULT_COLLECTION = 'my_documents';
const VECTOR_DIMENSION = 384;

interface ConnectionState {
  // Connection state
  connection: Connection | null;
  ready: boolean;
  initializing: boolean;
  initError: string | null;

  // Active selection
  activeCollectionName: string;

  // Actions
  initialize: () => Promise<void>;
  setActiveCollectionName: (name: string) => void;
  reset: () => void;
}

export const useConnectionStore = create<ConnectionState>()(
  persist(
    (set, get) => ({
      connection: null,
      ready: false,
      initializing: false,
      initError: null,
      activeCollectionName: DEFAULT_COLLECTION,

      initialize: async () => {
        if (get().ready || get().initializing) return;
        set({ initializing: true, initError: null });

        try {
          // Find or create LanceDB connection
          const { data: connections } = await connectionsApi.list();
          let conn = connections.find(
            (c) => c.db_type === 'lancedb' && c.is_connected
          );

          if (!conn) {
            const existingLance = connections.find((c) => c.db_type === 'lancedb');
            if (existingLance) {
              await connectionsApi.connect(existingLance.id);
              const { data: refreshed } = await connectionsApi.get(existingLance.id);
              conn = refreshed;
            } else {
              const { data: newConn } = await connectionsApi.create({
                name: 'Local LanceDB',
                db_type: 'lancedb' as Connection['db_type'],
                extra_config: { persist_dir: './data/lancedb' },
              });
              await connectionsApi.connect(newConn.id);
              const { data: refreshed } = await connectionsApi.get(newConn.id);
              conn = refreshed;
            }
          }

          // Ensure default collection exists
          try {
            await collectionsApi.get(conn.id, DEFAULT_COLLECTION);
          } catch {
            await collectionsApi.create(conn.id, {
              name: DEFAULT_COLLECTION,
              dimension: VECTOR_DIMENSION,
              distance_metric: 'cosine',
            });
          }

          set({ connection: conn, ready: true, initializing: false });
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          set({
            initError: `Initialization failed: ${msg}`,
            initializing: false,
          });
        }
      },

      setActiveCollectionName: (name) => set({ activeCollectionName: name }),

      reset: () =>
        set({
          connection: null,
          ready: false,
          initializing: false,
          initError: null,
          activeCollectionName: DEFAULT_COLLECTION,
        }),
    }),
    {
      name: 'uva-connection-store',
      partialize: (state) => ({
        activeCollectionName: state.activeCollectionName,
      }),
    }
  )
);
