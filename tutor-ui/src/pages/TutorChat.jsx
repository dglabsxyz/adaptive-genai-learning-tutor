import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
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

// Cross-links so the chat-vs-structured-tools model is clear.
const TOOL_LINKS = [
  { to: '/diagnostic', label: 'Diagnostic' },
  { to: '/study-plan', label: 'Study Plan' },
  { to: '/exercise', label: 'Practice' },
  { to: '/progress', label: 'Progress' },
];

const newThread = (learnerId) => `tutor-${learnerId}-${Date.now().toString(36)}`;

function actionLabel(req) {
  return req?.name || req?.action || req?.tool || 'action';
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
  const [steps, setSteps] = useState([]);
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    setThreadId(newThread(learnerId));
    setMessages([]);
  }, [learnerId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, steps]);

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
    const itp = result?.needs_clarification ? result.interrupt || {} : null;
    setMessages((prev) => {
      let node;
      if (itp && itp.type === 'clarification') {
        node = { id: nextId(), role: 'assistant', clarify: itp.question || 'Could you add a bit more detail?' };
      } else if (itp && (itp.action_requests || []).length) {
        node = { id: nextId(), role: 'assistant', interrupt: itp.action_requests };
      } else {
        node = {
          id: nextId(),
          role: 'assistant',
          text: result?.message || '(no response)',
          sources: toSourceCards(result?.source_refs),
          // Attach deterministic grade data from grade_answer tool — never trust LLM prose for mastery numbers.
          grade: result?.grade || null,
        };
      }
      return [...prev, node];
    });
  }, []);

  const send = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', text: msg }]);
    setInput('');
    setBusy(true);
    setSteps([]);
    startTimer();
    try {
      let final;
      try {
        // Preferred: streamed step-progress.
        final = await api.postChatStream(
          { message: msg, threadId },
          { onStep: (label) => setSteps((prev) => (prev.includes(label) ? prev : [...prev, label])) },
        );
      } catch {
        // Graceful fallback to the non-streaming endpoint.
        final = await api.postChat({ message: msg, threadId });
      }
      applyResult(final);
    } catch (err) {
      addToast(err.message || 'Chat failed', 'error');
      setMessages((prev) => [...prev, { id: nextId(), role: 'assistant', error: err.message || 'Request failed' }]);
    } finally {
      stopTimer();
      setBusy(false);
      setSteps([]);
    }
  };

  const resume = async (resumePayload, msgId, resolvedLabel) => {
    if (busy) return;
    setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...m, resolved: resolvedLabel } : m)));
    setBusy(true);
    setSteps([]);
    startTimer();
    try {
      const final = await api.postChatResume({ threadId, resume: resumePayload });
      applyResult(final);
    } catch (err) {
      addToast(err.message || 'Resume failed', 'error');
      setMessages((prev) => [...prev, { id: nextId(), role: 'assistant', error: err.message || 'Resume failed' }]);
    } finally {
      stopTimer();
      setBusy(false);
    }
  };

  const decide = (decisionType, msgId) => resume({ decisions: [{ type: decisionType }] }, msgId, decisionType);

  const answerClarification = (answer, msgId) => {
    const text = (answer || '').trim();
    if (!text || busy) return;
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', text }]);
    resume(text, msgId, 'answered');
  };

  const resetConversation = () => {
    stopTimer();
    setMessages([]);
    setSteps([]);
    setThreadId(newThread(learnerId));
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-8 pt-6 pb-4 flex items-end justify-between gap-4 flex-wrap">
        <div>
          <p className="text-overline text-[var(--text-muted)] mb-1">Your AI Tutor</p>
          <h2 className="text-display text-[var(--text-primary)]">Tutor Chat</h2>
          <p className="text-caption text-[var(--text-muted)] mt-1 max-w-2xl">
            The conversational way to learn — the deep agent plans, delegates to specialists, and grounds answers in
            the course corpus. Prefer to click instead?{' '}
            {TOOL_LINKS.map((l, i) => (
              <React.Fragment key={l.to}>
                <Link to={l.to} className="text-[var(--c-primary)] hover:underline">
                  {l.label}
                </Link>
                {i < TOOL_LINKS.length - 1 ? ' · ' : ''}
              </React.Fragment>
            ))}
          </p>
        </div>
        <button onClick={resetConversation} className="btn-secondary text-sm" disabled={busy}>
          ＋ New conversation
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 pb-4 space-y-4">
        {messages.length === 0 && !busy && (
          <div className="max-w-2xl mx-auto mt-8 animate-fade-in">
            <div className="card p-6 text-center">
              <div className="text-3xl mb-2">💬</div>
              <h3 className="text-title text-[var(--text-primary)] mb-1">Ask your tutor anything</h3>
              <p className="text-sm text-[var(--text-secondary)] mb-5">
                Diagnose your level, plan a path, practice, or save your progress — all grounded in real course
                sources.
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
          <MessageBubble key={m.id} message={m} onDecide={decide} onAnswer={answerClarification} busy={busy} />
        ))}

        {busy && (
          <div className="flex items-start gap-3 max-w-3xl animate-fade-in">
            <Avatar role="assistant" />
            <div className="card px-4 py-3 flex-1">
              <div className="flex items-center gap-3 text-sm text-[var(--text-secondary)] mb-1">
                <span className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-[var(--c-primary)] animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 rounded-full bg-[var(--c-primary)] animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 rounded-full bg-[var(--c-primary)] animate-bounce" style={{ animationDelay: '300ms' }} />
                </span>
                Tutor is working… {elapsed}s
                <span className="text-[var(--text-muted)]">· a full turn can take ~30–60s</span>
              </div>
              {steps.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {steps.map((s, i) => {
                    const last = i === steps.length - 1;
                    return (
                      <li key={`${s}-${i}`} className="flex items-center gap-2 text-xs">
                        <span style={{ color: last ? 'var(--c-primary)' : 'var(--c-success)' }}>{last ? '◐' : '✓'}</span>
                        <span className={last ? 'text-[var(--text-primary)]' : 'text-[var(--text-muted)]'}>{s}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
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

function MessageBubble({ message, onDecide, onAnswer, busy }) {
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

  return (
    <div className="flex items-start gap-3 max-w-3xl animate-fade-in">
      <Avatar role="assistant" />
      <div className="flex-1 min-w-0">
        {message.error ? (
          <div className="card px-4 py-3 text-sm text-[var(--c-danger)]" style={{ borderColor: 'var(--c-danger)' }}>
            ⚠️ {message.error}
          </div>
        ) : message.interrupt ? (
          <ApprovalCard
            requests={message.interrupt}
            resolved={message.resolved}
            onDecide={(t) => onDecide(t, message.id)}
            busy={busy}
          />
        ) : message.clarify ? (
          <ClarifyCard question={message.clarify} resolved={message.resolved} onAnswer={(t) => onAnswer(t, message.id)} busy={busy} />
        ) : (
          <div className="card px-4 py-3">
            <p className="text-sm text-[var(--text-primary)] whitespace-pre-wrap leading-relaxed">{message.text}</p>
            {message.grade?.mastery_update && <MasteryBar grade={message.grade} />}
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

/** Deterministic mastery bar — source of truth from grade_answer tool, not LLM prose. */
function MasteryBar({ grade }) {
  const mu = grade?.mastery_update;
  if (!mu) return null;
  const before = typeof mu.proficiency_before === 'number' ? mu.proficiency_before : null;
  const after = typeof mu.proficiency_after === 'number' ? mu.proficiency_after : null;
  const delta = before !== null && after !== null ? after - before : null;
  const deltaSign = delta !== null && delta > 0 ? '+' : '';
  return (
    <div className="mt-3 pt-3 border-t border-[var(--border)] text-xs">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[var(--text-muted)]">📊</span>
        <span className="font-medium text-[var(--text-primary)]">{grade.skill || 'Skill'} Mastery</span>
        {mu.new_status && <span className="tag text-[10px]">{mu.new_status}</span>}
      </div>
      {before !== null && after !== null ? (
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-[var(--bg-surface)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--c-primary)] transition-all"
              style={{ width: `${Math.round(after * 100)}%` }}
            />
          </div>
          <span className="text-[var(--text-primary)] font-mono">
            {Math.round(before * 100)}% → {Math.round(after * 100)}%
            {delta !== null && delta !== 0 && (
              <span style={{ color: delta > 0 ? 'var(--c-success)' : 'var(--c-danger)', marginLeft: '4px' }}>
                ({deltaSign}{Math.round(delta * 100)}%)
              </span>
            )}
          </span>
        </div>
      ) : (
        <p className="text-[var(--text-muted)]">Mastery updated.</p>
      )}
      {mu.status_reason && <p className="mt-1 text-[var(--text-muted)]">{mu.status_reason}</p>}
    </div>
  );
}

function ClarifyCard({ question, resolved, onAnswer, busy }) {
  const [text, setText] = useState('');
  if (resolved) {
    return (
      <div className="card px-5 py-4 border" style={{ borderColor: 'var(--c-accent)' }}>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-lg">❓</span>
          <p className="text-sm font-semibold text-[var(--text-primary)]">Quick question</p>
        </div>
        <p className="text-sm text-[var(--text-secondary)]">{question}</p>
        <p className="text-sm mt-2 font-medium" style={{ color: 'var(--c-success)' }}>✓ Answered</p>
      </div>
    );
  }
  return (
    <div className="card px-5 py-4 border" style={{ borderColor: 'var(--c-accent)' }}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">❓</span>
        <p className="text-sm font-semibold text-[var(--text-primary)]">The tutor needs one detail</p>
      </div>
      <p className="text-sm text-[var(--text-secondary)] mb-3">{question}</p>
      <div className="flex items-end gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onAnswer(text)}
          placeholder="Type your answer…"
          disabled={busy}
          className="input flex-1"
          autoFocus
        />
        <button onClick={() => onAnswer(text)} disabled={busy || !text.trim()} className="btn-primary text-sm">
          Answer
        </button>
      </div>
    </div>
  );
}
