'use client';

import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  isStreaming: boolean;
  disabled?: boolean;
}

export function ChatInput({ onSend, onStop, isStreaming, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!input.trim() || disabled) return;
      onSend(input.trim());
      setInput('');
    },
    [input, onSend, disabled],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (input.trim() && !disabled && !isStreaming) {
          onSend(input.trim());
          setInput('');
        }
      }
    },
    [input, onSend, disabled, isStreaming],
  );

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2">
      <textarea
        className="flex-1 resize-none rounded-xl border border-zinc-300 bg-white px-4 py-3 text-sm shadow-sm placeholder:text-zinc-400 focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-500"
        rows={1}
        placeholder="Type your question... (Enter to send, Shift+Enter for new line)"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled || isStreaming}
      />
      {isStreaming ? (
        <Button
          type="button"
          variant="destructive"
          onClick={onStop}
          className="h-11 px-4"
        >
          Stop
        </Button>
      ) : (
        <Button
          type="submit"
          disabled={!input.trim() || disabled}
          className="h-11 px-4"
        >
          Send
        </Button>
      )}
    </form>
  );
}
