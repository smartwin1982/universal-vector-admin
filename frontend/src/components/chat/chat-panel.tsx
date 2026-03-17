'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChatMessage } from './chat-message';
import { ChatInput } from './chat-input';
import { useStreamingRAG } from '@/lib/hooks/use-streaming-rag';
import { sessionsApi } from '@/lib/api';
import { useChatStore } from '@/lib/stores/chat-store';

interface ChatPanelProps {
  connectionId: string;
  collectionName: string;
}

export function ChatPanel({ connectionId, collectionName }: ChatPanelProps) {
  const [selectedProvider, setSelectedProvider] = useState('gemini');
  const [project, setProject] = useState('');
  const prevProjectRef = useRef(project);
  const sessionId = useChatStore((s) => s.sessionId);
  const setSessionId = useChatStore((s) => s.setSessionId);
  const clearChat = useChatStore((s) => s.clearChat);
  const scrollRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    streamingState,
    isStreaming,
    autoDetectedProject,
    sendMessage,
    stopStreaming,
  } = useStreamingRAG({
    connectionId,
    collectionName,
    topK: 5,
    llmProvider: selectedProvider,
    sessionId,
    project: project || undefined,
  });

  // Auto-create session on mount (only if no existing session)
  useEffect(() => {
    if (!sessionId) {
      sessionsApi.create().then(({ data }) => {
        setSessionId(data.session_id);
      }).catch(() => {});
    }
  }, [sessionId, setSessionId]);

  // 專案篩選改變時，自動重建 session（避免舊對話記憶污染新查詢）
  useEffect(() => {
    if (prevProjectRef.current !== project && messages.length > 0) {
      clearChat();
      sessionsApi.create().then(({ data }) => {
        setSessionId(data.session_id);
      }).catch(() => {});
    }
    prevProjectRef.current = project;
  }, [project, messages.length, clearChat, setSessionId]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingState]);

  const handleNewChat = useCallback(() => {
    clearChat();
    sessionsApi.create().then(({ data }) => {
      setSessionId(data.session_id);
    }).catch(() => {});
  }, [clearChat, setSessionId]);

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="flex-shrink-0 pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>AI Chat (RAG)</CardTitle>
            <CardDescription>
              Streaming conversation with your documents
              {autoDetectedProject && !project && (
                <span className="ml-2 inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                  Auto: {autoDetectedProject}
                </span>
              )}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              className="w-36 rounded-md border border-zinc-300 bg-white px-2 py-1 text-xs shadow-sm placeholder:text-zinc-400 focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-500"
              placeholder="專案篩選（選填）"
              value={project}
              onChange={(e) => setProject(e.target.value)}
              disabled={isStreaming}
            />
            <select
              className="rounded-md border border-zinc-300 bg-white px-2 py-1 text-xs shadow-sm focus:border-zinc-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              disabled={isStreaming}
            >
              <option value="gemini">Gemini</option>
              <option value="ollama">Ollama</option>
            </select>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleNewChat}
              disabled={isStreaming}
              className="text-xs"
            >
              New Chat
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col overflow-hidden p-0">
        {/* Messages area */}
        <div
          ref={scrollRef}
          className="flex-1 space-y-4 overflow-y-auto px-6 py-4"
        >
          {messages.length === 0 && (
            <div className="flex h-full items-center justify-center">
              <p className="text-sm text-zinc-400">
                Ask a question about your documents...
              </p>
            </div>
          )}
          {messages.map((msg, idx) => (
            <ChatMessage
              key={idx}
              message={msg}
              isStreaming={
                isStreaming &&
                idx === messages.length - 1 &&
                msg.role === 'assistant'
              }
            />
          ))}
          {streamingState === 'loading' && messages[messages.length - 1]?.role === 'user' && (
            <div className="flex justify-start">
              <div className="rounded-2xl bg-zinc-100 px-4 py-3 dark:bg-zinc-800">
                <div className="flex items-center gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:0ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:150ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="flex-shrink-0 border-t border-zinc-200 px-6 py-4 dark:border-zinc-800">
          <ChatInput
            onSend={sendMessage}
            onStop={stopStreaming}
            isStreaming={isStreaming}
          />
        </div>
      </CardContent>
    </Card>
  );
}
