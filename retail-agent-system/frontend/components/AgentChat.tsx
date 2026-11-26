'use client';

import { useState, useRef, useEffect } from 'react';
import { runAgentTask, getChatHistory, saveChatMessage } from '@/lib/api';
import s from './agentUi.module.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  error?: boolean;
}

const SUGGESTIONS = [
  'Show me all low stock products',
  'What is the revenue this month?',
  'List top 5 selling products',
  'Summarize complaints this week',
  'What is our total profit this week?',
];

function UserAvatar() {
  return (
    <span className={`${s.avatar} ${s.avatarUser}`} aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="rgb(var(--brand-700))" strokeWidth="1.6" strokeLinecap="round">
        <circle cx="12" cy="8" r="3.4" />
        <path d="M4.8 20a7.2 7.2 0 0 1 14.4 0" />
      </svg>
    </span>
  );
}

function AiAvatar() {
  return <span className={`${s.avatar} ${s.avatarAi}`} aria-hidden="true" />;
}

export default function AgentChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        'Hello! I am the Retail AI Agent. I can help you with inventory management, accounting, customer service, and marketing. How can I assist you today?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Shrink the box back to one line after a message is sent.
  useEffect(() => {
    if (!input && inputRef.current) inputRef.current.style.height = 'auto';
  }, [input]);

  useEffect(() => {
    getChatHistory()
      .then((res) => {
        if (res.data.length > 0) {
          setMessages(
            res.data.map((m: { role: 'user' | 'assistant'; content: string; created_at: string }) => ({
              role: m.role,
              content: m.content,
              timestamp: new Date(m.created_at),
            }))
          );
        }
      })
      .catch(() => {});
  }, []);

  const send = async (query: string) => {
    if (!query.trim() || loading) return;

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: query, timestamp: new Date() },
    ]);
    saveChatMessage('user', query).catch(() => {});
    setInput('');
    setLoading(true);

    try {
      const res = await runAgentTask(query);
      const data = res.data;
      const assistantContent = data.response || data.message || JSON.stringify(data);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: assistantContent,
          timestamp: new Date(),
          error: !data.success,
        },
      ]);
      if (data.success) {
        saveChatMessage('assistant', assistantContent).catch(() => {});
      }
    } catch (err: unknown) {
      const errorMessage =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
            'Something went wrong. Please try again.'
          : 'Something went wrong. Please try again.';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: errorMessage,
          timestamp: new Date(),
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const submit = () => send(input);

  // Enter sends, Shift+Enter makes a new line.
  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const autoGrow = (el: HTMLTextAreaElement) => {
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  };

  return (
    <div className={s.body}>
      {/* Messages */}
      <div className={s.stream}>
        <div className={s.inner}>
          {messages.map((msg, i) => {
            const isUser = msg.role === 'user';
            return (
              <div key={i} className={`${s.msg} ${isUser ? s.msgUser : s.msgAi}`}>
                {!isUser && <AiAvatar />}
                <div className={`${s.bubble} ${msg.error ? s.bubbleError : ''}`}>
                  {msg.content}
                  <div className={`${s.stamp} ${isUser ? s.stampUser : ''}`}>
                    {msg.timestamp.toLocaleTimeString()}
                  </div>
                </div>
                {isUser && <UserAvatar />}
              </div>
            );
          })}

          {loading && (
            <div className={`${s.msg} ${s.msgAi}`}>
              <AiAvatar />
              <div className={s.bubble}>
                <svg className={s.spinner} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-label="Thinking">
                  <path d="M21 12a9 9 0 1 1-6.2-8.6" />
                </svg>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Suggestions */}
      {messages.length <= 1 && (
        <div className={s.suggestions}>
          {SUGGESTIONS.map((text) => (
            <button
              key={text}
              type="button"
              className={s.suggestion}
              onClick={() => send(text)}
              disabled={loading}
            >
              {text}
            </button>
          ))}
        </div>
      )}

      {/* Composer: a plain text box and a send button. */}
      <div className={`${s.composerWrap} ${s.enterComposer}`}>
        <form
          className={s.composer}
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <textarea
            ref={inputRef}
            className={s.input}
            rows={1}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              autoGrow(e.target);
            }}
            onKeyDown={onKeyDown}
            placeholder="Ask the retail AI agent…"
            aria-label="Message the retail AI agent"
            disabled={loading}
          />
          <button
            type="submit"
            className={s.send}
            aria-label="Send"
            disabled={loading || !input.trim()}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </form>
        <p className={s.hint}>Press Enter to send · Shift + Enter for a new line</p>
      </div>
    </div>
  );
}
