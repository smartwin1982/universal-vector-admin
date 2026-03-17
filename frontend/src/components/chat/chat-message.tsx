'use client';

import { useState } from 'react';
import type { ChatMessage as ChatMessageType } from '@/lib/hooks/use-streaming-rag';

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [expandedSource, setExpandedSource] = useState<number | null>(null);

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
            : 'bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100'
        }`}
      >
        {/* Role label */}
        <div className="mb-1 flex items-center gap-2">
          <span
            className={`text-xs font-medium ${
              isUser
                ? 'text-zinc-400 dark:text-zinc-500'
                : 'text-zinc-500 dark:text-zinc-400'
            }`}
          >
            {isUser ? 'You' : 'AI'}
          </span>
          {message.llmProvider && (
            <span className="rounded bg-zinc-200 px-1.5 py-0.5 text-[10px] text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300">
              {message.llmProvider}
            </span>
          )}
        </div>

        {/* Content */}
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
          {isStreaming && !isUser && (
            <span className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-current" />
          )}
        </p>

        {/* Sources — compact pills, click to expand */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 border-t border-zinc-200 pt-1.5 dark:border-zinc-700">
            <div className="flex flex-wrap items-center gap-1">
              <span className="text-[10px] text-zinc-400 dark:text-zinc-500">Sources:</span>
              {message.sources.map((src, idx) => (
                <button
                  key={src.id}
                  type="button"
                  onClick={() => setExpandedSource(expandedSource === idx ? null : idx)}
                  className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] transition-colors ${
                    expandedSource === idx
                      ? 'border-zinc-400 bg-zinc-200 dark:border-zinc-500 dark:bg-zinc-700'
                      : 'border-zinc-200 bg-white/50 hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-900/50 dark:hover:border-zinc-600'
                  }`}
                >
                  <span className="text-zinc-500 dark:text-zinc-400">#{idx + 1}</span>
                  <span className="font-mono text-zinc-400">{(src.score * 100).toFixed(1)}%</span>
                </button>
              ))}
            </div>
            {expandedSource !== null && message.sources[expandedSource] && (
              <div className="mt-1.5 rounded border border-zinc-200 bg-white/50 p-2 dark:border-zinc-700 dark:bg-zinc-900/50">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-medium text-zinc-500 dark:text-zinc-400">
                    Source #{expandedSource + 1}
                  </span>
                  <span className="font-mono text-[10px] text-zinc-400">
                    {(message.sources[expandedSource].score * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="mt-1 whitespace-pre-wrap text-xs leading-relaxed text-zinc-600 dark:text-zinc-300">
                  {message.sources[expandedSource].document}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
