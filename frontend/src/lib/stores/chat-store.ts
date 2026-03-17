/**
 * Chat 狀態管理 — 全域 Zustand store
 * 切換頁面時保留對話紀錄，點 New Chat 才清除
 */
import { create } from 'zustand';
import type { RAGSourceDocument } from '@/lib/api';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: RAGSourceDocument[];
  llmProvider?: string;
  timestamp: Date;
}

type StreamingState = 'idle' | 'loading' | 'streaming' | 'done';

interface ChatState {
  messages: ChatMessage[];
  streamingState: StreamingState;
  currentSources: RAGSourceDocument[];
  sessionId: string | null;
  autoDetectedProject: string | null;

  setMessages: (updater: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void;
  setStreamingState: (state: StreamingState) => void;
  setCurrentSources: (sources: RAGSourceDocument[]) => void;
  setSessionId: (id: string | null) => void;
  setAutoDetectedProject: (project: string | null) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  streamingState: 'idle',
  currentSources: [],
  sessionId: null,
  autoDetectedProject: null,

  setMessages: (updater) =>
    set((state) => ({
      messages: typeof updater === 'function' ? updater(state.messages) : updater,
    })),
  setStreamingState: (streamingState) => set({ streamingState }),
  setCurrentSources: (currentSources) => set({ currentSources }),
  setSessionId: (sessionId) => set({ sessionId }),
  setAutoDetectedProject: (autoDetectedProject) => set({ autoDetectedProject }),
  clearChat: () =>
    set({
      messages: [],
      streamingState: 'idle',
      currentSources: [],
      sessionId: null,
      autoDetectedProject: null,
    }),
}));
