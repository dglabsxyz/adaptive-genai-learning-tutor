import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSession } from '../context/SessionContext';
import { useApi } from '../api/useApi';
import { ROLES, API_URL } from '../config';

export default function TopBar({ onOpenNav }) {
  const { learnerId, role, setLearnerId, setRole } = useSession();
  const api = useApi();
  const [draftLearner, setDraftLearner] = useState(learnerId);

  useEffect(() => setDraftLearner(learnerId), [learnerId]);

  const health = useQuery({
    queryKey: ['health', API_URL],
    queryFn: () => api.getHealth(),
    refetchInterval: 30000,
    retry: 0,
  });

  const online = health.isSuccess && health.data?.ok;
  const docs = health.data?.corpus?.document_count;
  const backend = health.data?.repository_backend;

  const commitLearner = () => {
    const v = draftLearner.trim();
    if (v && v !== learnerId) setLearnerId(v);
  };

  return (
    <header className="h-14 flex items-center gap-3 px-4 sm:px-5 border-b border-[var(--border)] glass-sidebar flex-shrink-0">
      {/* Mobile nav toggle */}
      <button
        onClick={onOpenNav}
        className="lg:hidden -ml-1 p-2 rounded-[var(--r-sm)] hover:bg-[var(--bg-surface-hover)] text-[var(--text-secondary)]"
        aria-label="Open navigation"
      >
        ☰
      </button>

      {/* Backend health */}
      <div className="flex items-center gap-2 text-xs" title={online ? `${API_URL}` : 'Backend not reachable'}>
        <span
          className={`w-2 h-2 rounded-full ${
            online ? 'bg-[var(--c-success)]' : health.isLoading ? 'bg-[var(--c-accent)]' : 'bg-[var(--c-danger)]'
          }`}
        />
        <span className="text-[var(--text-muted)]">
          {health.isLoading
            ? 'Connecting…'
            : online
            ? `Connected${docs ? ` · ${docs} docs` : ''}${backend ? ` · ${backend}` : ''}`
            : 'Backend offline'}
        </span>
      </div>

      <div className="flex-1" />

      {/* Demo identity controls — grouped + labeled so the primary UI reads as a real product.
          A real deployment derives identity from sign-in; these switches are demo-only. */}
      <div
        className="flex items-center gap-2.5 rounded-[var(--r-md)] border border-dashed border-[var(--border)] px-2.5 py-1"
        title="Demo only: switch the active learner and role to explore learner / educator / admin views. A real deployment derives these from sign-in."
      >
        <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-muted)] hidden md:inline">
          Demo · View as
        </span>
        <label className="hidden sm:flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
          <span className="sr-only">Learner</span>
          <input
            value={draftLearner}
            onChange={(e) => setDraftLearner(e.target.value)}
            onBlur={commitLearner}
            onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
            spellCheck={false}
            aria-label="Demo learner id"
            className="w-32 px-2 py-1 rounded-[var(--r-sm)] bg-[var(--bg-surface)] border border-[var(--border)] text-[var(--text-primary)] text-xs focus:outline-none focus:border-[var(--c-primary)]"
          />
        </label>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          aria-label="Demo role"
          className="px-2 py-1 rounded-[var(--r-sm)] bg-[var(--bg-surface)] border border-[var(--border)] text-[var(--text-primary)] text-xs capitalize focus:outline-none focus:border-[var(--c-primary)]"
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>
    </header>
  );
}
