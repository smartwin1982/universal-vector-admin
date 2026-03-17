import { useCallback, useRef } from 'react';
import type { RAGSourceDocument } from '@/lib/api';
import { useChatStore } from '@/lib/stores/chat-store';
import type { ChatMessage } from '@/lib/stores/chat-store';

export type { ChatMessage };

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface UseStreamingRAGOptions {
  connectionId: string;
  collectionName: string;
  topK?: number;
  llmProvider?: string;
  sessionId?: string | null;
  project?: string;
}

export function useStreamingRAG(options: UseStreamingRAGOptions) {
  const { connectionId, collectionName, topK = 5, llmProvider, sessionId, project } = options;

  const messages = useChatStore((s) => s.messages);
  const streamingState = useChatStore((s) => s.streamingState);
  const currentSources = useChatStore((s) => s.currentSources);
  const autoDetectedProject = useChatStore((s) => s.autoDetectedProject);
  const setMessages = useChatStore((s) => s.setMessages);
  const setStreamingState = useChatStore((s) => s.setStreamingState);
  const setCurrentSources = useChatStore((s) => s.setCurrentSources);
  const setAutoDetectedProject = useChatStore((s) => s.setAutoDetectedProject);

  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim()) return;

      // Add user message
      const userMsg: ChatMessage = {
        role: 'user',
        content: question.trim(),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setStreamingState('loading');
      setCurrentSources([]);
      setAutoDetectedProject(null);

      // Prepare assistant placeholder
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      };

      const abortController = new AbortController();
      abortRef.current = abortController;

      try {
        const body = {
          question: question.trim(),
          connection_id: connectionId,
          collection_name: collectionName,
          top_k: topK,
          llm_provider: llmProvider || undefined,
          session_id: sessionId || undefined,
          project: project || undefined,
        };

        const resp = await fetch(`${API_BASE_URL}/api/rag/ask/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
          signal: abortController.signal,
        });

        if (!resp.ok) {
          const errText = await resp.text();
          throw new Error(errText || `HTTP ${resp.status}`);
        }

        const reader = resp.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';
        let accumulatedContent = '';
        let sources: RAGSourceDocument[] = [];
        let llmProv = '';

        setMessages((prev) => [...prev, assistantMsg]);
        setStreamingState('streaming');

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const events = buffer.split('\n\n');
          buffer = events.pop() || ''; // Keep incomplete event in buffer

          for (const eventBlock of events) {
            if (!eventBlock.trim()) continue;

            const lines = eventBlock.split('\n');
            let eventType = '';
            let eventData = '';

            for (const line of lines) {
              if (line.startsWith('event: ')) {
                eventType = line.slice(7);
              } else if (line.startsWith('data: ')) {
                eventData = line.slice(6);
              }
            }

            if (eventType === 'sources') {
              sources = JSON.parse(eventData);
              setCurrentSources(sources);
            } else if (eventType === 'auto_project') {
              setAutoDetectedProject(JSON.parse(eventData));
            } else if (eventType === 'chunk') {
              const chunk = JSON.parse(eventData);
              accumulatedContent += chunk;
              // Update the last message (assistant) in place
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === 'assistant') {
                  updated[updated.length - 1] = {
                    ...last,
                    content: accumulatedContent,
                    sources,
                  };
                }
                return updated;
              });
            } else if (eventType === 'done') {
              const doneData = JSON.parse(eventData);
              llmProv = doneData.llm_provider || '';
            }
          }
        }

        // Finalize assistant message
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === 'assistant') {
            updated[updated.length - 1] = {
              ...last,
              content: accumulatedContent,
              sources,
              llmProvider: llmProv,
            };
          }
          return updated;
        });

        setStreamingState('done');
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          setStreamingState('idle');
          return;
        }
        // Add error as assistant message
        const errorMsg =
          err instanceof Error ? err.message : String(err);
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === 'assistant') {
            updated[updated.length - 1] = {
              ...last,
              content: `Error: ${errorMsg}`,
            };
          } else {
            updated.push({
              role: 'assistant',
              content: `Error: ${errorMsg}`,
              timestamp: new Date(),
            });
          }
          return updated;
        });
        setStreamingState('done');
      } finally {
        abortRef.current = null;
      }
    },
    [connectionId, collectionName, topK, llmProvider, sessionId, project, setMessages, setStreamingState, setCurrentSources, setAutoDetectedProject],
  );

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentSources([]);
    setStreamingState('idle');
  }, [setMessages, setCurrentSources, setStreamingState]);

  return {
    messages,
    streamingState,
    isStreaming: streamingState === 'streaming' || streamingState === 'loading',
    currentSources,
    autoDetectedProject,
    sendMessage,
    stopStreaming,
    clearMessages,
  };
}
