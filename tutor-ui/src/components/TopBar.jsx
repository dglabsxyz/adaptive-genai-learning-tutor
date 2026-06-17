import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSession } from '../context/SessionContext';
import { useApi } from '../api/useApi';
import { ROLES, API_URL } from '../config';

export default function TopBar() {
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
    <header className="h-14 flex items-center gap-3 px-5 border-b border-[var(--border)] glass-sidebar flex-shrink-0">
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

      <label className="hidden sm:flex items-center gap-2 text-xs text-[var(--text-muted)]">
        Learner
        <input
          value={draftLearner}
          onChange={(e) => setDraftLearner(e.target.value)}
          onBlur={commitLearner}
          onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
          spellCheck={false}
          className="w-40 px-2 py-1 rounded-[var(--r-sm)] bg-[var(--bg-surface)] border border-[var(--border)] text-[var(--text-primary)] text-xs focus:outline-none focus:border-[var(--c-primary)]"
        />
      </label>

      <label className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
        Role
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="px-2 py-1 rounded-[var(--r-sm)] bg-[var(--bg-surface)] border border-[var(--border)] text-[var(--text-primary)] text-xs capitalize focus:outline-none focus:border-[var(--c-primary)]"
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </label>
    </header>
  );
}
