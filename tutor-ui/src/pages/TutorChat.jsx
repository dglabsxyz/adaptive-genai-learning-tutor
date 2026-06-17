import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useApi } from '../api/useApi';
import { useSession } from '../context/SessionContext';
import { useToast } from '../context/ToastContext';
import SourceRef from '../components/SourceRef';
import { toSourceCards } from '../api/mappers';

let _msgId = 0;
const nextId = () => `m${++_msgId}`;

const SUGGESTIONS = [
  'I want to learn RAG and AI agents. Diagnose me and plan a study path.',
  'Give me one exercise on prompt engineering.',
  'How does MCP relate to AI agents? Cite sources.',
  'This was helpful — save my progress for this session.',
];

const newThread = (learnerId) => `tutor-${learnerId}-${Date.now().toString(36)}`;

function actionLabel(req) {
  const name = req?.name || req?.action || req?.tool || 'action';
  return name;
}
function actionSummary(req) {
  const args = req?.args || req?.arguments || req?.action_request?.args || {};
  return args.summary || args.text || null;
}

export default function TutorChat() {
  const api = useApi();
  const { learnerId } = useSession();
  const { addToast } = useToast();

  const [threadId, setThreadId] = useState(() => newThread(learnerId));
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const scrollRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    setThreadId(newThread(learnerId));
    setMessages([]);
  }, [learnerId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const startTimer = () => {
    setElapsed(0);
    const t0 = Date.now();
    timerRef.current = setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 1000);
  };
  const stopTimer = () => {
    clearInterval(timerRef.current);
    timerRef.current = null;
  };
  useEffect(() => () => stopTimer(), []);

  const applyResult = useCallback((result) => {
    const reqs = result?.needs_clarification ? result.interrupt?.action_requests || [] : null;
    setMessages((prev) => [
      ...prev,
      reqs && reqs.length
        ? { id: nextId(), role: 'assistant', interrupt: reqs }
        : {
            id: nextId(),
            role: 'assistant',
            text: result?.message || '(no response)',
            sources: toSourceCards(result?.source_refs),
          },
    ]);
  }, []);

  const chat = useMutation({
    mutationFn: (message) => api.postChat({ message, threadId }),
    onMutate: startTimer,
    onSettled: stopTimer,
    onSuccess: applyResult,
    onError: (err) => {
      addToast(err.message || 'Chat failed', 'error');
      setMessages((prev) => [...prev, { id: nextId(), role: 'assistant', error: err.message || 'Request failed' }]);
    },
  });

  const resume = useMutation({
    mutationFn: (decisionType) =>
      api.postChatResume({ threadId, resume: { decisions: [{ type: decisionType }] } }),
    onMutate: startTimer,
    onSettled: stopTimer,
    onSuccess: applyResult,
    onError: (err) => addToast(err.message || 'Resume failed', 'error'),
  });

  const busy = chat.isPending || resume.isPending;

  const send = (text) => {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', text: msg }]);
    setInput('');
    chat.mutate(msg);
  };

  const decide = (decisionType, msgId) => {
    if (busy) return;
    setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...m, resolved: decisionType } : m)));
    resume.mutate(decisionType);
  };

  const resetConversation = () => {
    stopTimer();
    setMessages([]);
    setThreadId(newThread(learnerId));
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-8 pt-6 pb-4 flex items-end justify-between">
        <div>
          <p className="text-overline text-[var(--text-muted)] mb-1">Your AI Tutor</p>
          <h2 className="text-display text-[var(--text-primary)]">Tutor Chat</h2>
          <p className="text-caption text-[var(--text-muted)] mt-1">
            The deep agent plans, delegates to specialists, and grounds answers in the course corpus.
          </p>
        </div>
        <button onClick={resetConversation} className="btn-secondary text-sm" disabled={busy}>
          ＋ New conversation
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 pb-4 space-y-4">
        {messages.length === 0 && (
          <div className="max-w-2xl mx-auto mt-8 animate-fade-in">
            <div className="card p-6 text-center">
              <div className="text-3xl mb-2">💬</div>
              <h3 className="text-title text-[var(--text-primary)] mb-1">Ask your tutor anything</h3>
              <p className="text-sm text-[var(--text-secondary)] mb-5">
                Diagnose your level, plan a path, practice, or save your progress — all grounded in real
                course sources.
              </p>
              <div className="grid sm:grid-cols-2 gap-2 text-left">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="p-3 rounded-[var(--r-md)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-hover)] border border-[var(--border)] hover:border-[var(--c-primary)]/30 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-all"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} onDecide={decide} busy={busy} />
        ))}

        {busy && (
          <div className="flex items-start gap-3 max-w-3xl animate-fade-in">
            <Avatar role="assistant" />
            <div className="card px-4 py-3">
              <div className="flex items-center gap-3 text-sm text-[var(--text-secondary)]">
                <span className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-[var(--c-primary)] animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 rounded-full bg-[var(--c-primary)] animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 rounded-full bg-[var(--c-primary)] animate-bounce" style={{ animationDelay: '300ms' }} />
                </span>
                Tutor is working… {elapsed}s
                <span className="text-[var(--text-muted)]">· a full turn can take ~30–60s</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="px-8 py-4 border-t border-[var(--border)]">
        <div className="max-w-4xl mx-auto flex items-end gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            rows={1}
            placeholder="Message your tutor…  (Enter to send, Shift+Enter for newline)"
            disabled={busy}
            className="input flex-1 resize-none max-h-40"
            style={{ minHeight: '46px' }}
          />
          <button onClick={() => send()} disabled={busy || !input.trim()} className="btn-primary px-5 h-[46px]">
            Send
          </button>
        </div>
        <p className="max-w-4xl mx-auto text-[11px] text-[var(--text-muted)] mt-2">
          Thread <span className="font-mono">{threadId}</span> · the tutor remembers this conversation.
        </p>
      </div>
    </div>
  );
}

function Avatar({ role }) {
  if (role === 'user') {
    return (
      <div className="w-8 h-8 rounded-full bg-[var(--bg-surface)] border border-[var(--border)] flex items-center justify-center text-xs flex-shrink-0">
        🧑
      </div>
    );
  }
  return (
    <div className="w-8 h-8 rounded-full gradient-primary flex items-center justify-center text-xs font-bold text-[var(--text-inverse)] flex-shrink-0">
      AI
    </div>
  );
}

function MessageBubble({ message, onDecide, busy }) {
  const { role } = message;

  if (role === 'user') {
    return (
      <div className="flex items-start gap-3 justify-end max-w-3xl ml-auto animate-fade-in">
        <div className="px-4 py-3 rounded-[var(--r-lg)] bg-[var(--c-primary-dim)] border border-[var(--c-primary)]/20 text-[var(--text-primary)] text-sm whitespace-pre-wrap">
          {message.text}
        </div>
        <Avatar role="user" />
      </div>
    );
  }

  // assistant
  return (
    <div className="flex items-start gap-3 max-w-3xl animate-fade-in">
      <Avatar role="assistant" />
      <div className="flex-1 min-w-0">
        {message.error ? (
          <div className="card px-4 py-3 text-sm text-[var(--c-danger)]" style={{ borderColor: 'var(--c-danger)' }}>
            ⚠️ {message.error}
          </div>
        ) : message.interrupt ? (
          <ApprovalCard requests={message.interrupt} resolved={message.resolved} onDecide={(t) => onDecide(t, message.id)} busy={busy} />
        ) : (
          <div className="card px-4 py-3">
            <p className="text-sm text-[var(--text-primary)] whitespace-pre-wrap leading-relaxed">{message.text}</p>
            {message.sources?.length > 0 && <SourceRef sources={message.sources} />}
          </div>
        )}
      </div>
    </div>
  );
}

function ApprovalCard({ requests, resolved, onDecide, busy }) {
  const req = requests[0] || {};
  const name = actionLabel(req);
  const summary = actionSummary(req);
  return (
    <div className="card px-5 py-4 border" style={{ borderColor: 'var(--c-accent)' }}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">✋</span>
        <p className="text-sm font-semibold text-[var(--text-primary)]">Approval needed</p>
        <span className="tag text-[10px]">{name}</span>
      </div>
      <p className="text-sm text-[var(--text-secondary)] mb-1">
        The tutor wants to run a consequential action that needs your sign-off.
      </p>
      {summary && (
        <p className="text-sm text-[var(--text-primary)] bg-[var(--bg-surface)] border border-[var(--border)] rounded-[var(--r-md)] px-3 py-2 my-2">
          “{summary}”
        </p>
      )}
      {resolved ? (
        <p className="text-sm mt-2 font-medium" style={{ color: resolved === 'approve' ? 'var(--c-success)' : 'var(--text-muted)' }}>
          {resolved === 'approve' ? '✓ Approved' : '✕ Declined'}
        </p>
      ) : (
        <div className="flex gap-2 mt-3">
          <button onClick={() => onDecide('approve')} disabled={busy} className="btn-primary text-sm">
            Approve
          </button>
          <button onClick={() => onDecide('reject')} disabled={busy} className="btn-secondary text-sm">
            Decline
          </button>
        </div>
      )}
    </div>
  );
}
