import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import SkillStateBadge from '../components/SkillStateBadge';
import SourceRef from '../components/SourceRef';
import { ErrorState, Spinner } from '../components/PageStates';
import { useApi } from '../api/useApi';
import { useToast } from '../context/ToastContext';
import { toSourceCards } from '../api/mappers';

const GOAL_PRESETS = [
  'Become production-ready with RAG and AI agents',
  'Learn prompt engineering and context engineering',
  'Understand MCP and tool-using agents',
  'Get strong at AI safety and evaluation',
];

export default function Diagnostic() {
  const api = useApi();
  const { addToast } = useToast();
  const [goal, setGoal] = useState('');

  const run = useMutation({
    mutationFn: (g) => api.postDiagnostic({ goal: g }),
    onError: (e) => addToast(e.message || 'Diagnostic failed', 'error'),
  });

  const submit = (g) => {
    const value = (g ?? goal).trim();
    if (!value) return;
    setGoal(value);
    run.mutate(value);
  };

  const data = run.data;

  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      <div className="mb-6">
        <p className="text-overline text-[var(--text-muted)] mb-1">Assessment</p>
        <h2 className="text-display text-[var(--text-primary)]">Diagnostic</h2>
        <p className="text-body text-[var(--text-secondary)]">Tell the tutor your goal; it estimates where you stand and what to shore up first.</p>
      </div>

      <div className="card p-6 mb-6">
        <label className="block text-sm text-[var(--text-secondary)] mb-2">Your learning goal</label>
        <div className="flex gap-3">
          <input
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
            placeholder="e.g. I want to build production RAG systems with agents"
            className="input flex-1"
          />
          <button onClick={() => submit()} disabled={run.isPending || !goal.trim()} className="btn-primary px-5">
            {run.isPending ? <Spinner /> : 'Run diagnostic'}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {GOAL_PRESETS.map((g) => (
            <button key={g} onClick={() => submit(g)} disabled={run.isPending} className="tag hover:text-[var(--c-primary)] transition-colors text-xs">
              {g}
            </button>
          ))}
        </div>
      </div>

      {run.isError && <ErrorState error={run.error} onRetry={() => submit()} />}

      {data && (
        <div className="space-y-6 animate-fade-in">
          <div className="card p-6">
            <h3 className="text-title text-[var(--text-primary)] mb-2">Summary</h3>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{data.summary}</p>
            {data.source_refs?.length > 0 && <SourceRef sources={toSourceCards(data.source_refs)} />}
          </div>

          {Array.isArray(data.assessment) && data.assessment.length > 0 && (
            <div className="card p-6">
              <h3 className="text-title text-[var(--text-primary)] mb-4">Skill estimate</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {data.assessment.map((a, i) => (
                  <div key={i} className="p-4 rounded-[var(--r-md)] bg-[var(--bg-surface)] border border-[var(--border)]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-[var(--text-primary)]">{a.skill}</span>
                      <SkillStateBadge status={a.status || 'exposure'} />
                    </div>
                    <div className="h-2 rounded-full bg-[var(--bg)] overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${Math.round((a.proficiency || 0) * 100)}%`, background: 'var(--c-primary)' }} />
                    </div>
                    <p className="text-xs text-[var(--text-muted)] mt-1">{Math.round((a.proficiency || 0) * 100)}% proficiency</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Array.isArray(data.diagnostic_questions) && data.diagnostic_questions.length > 0 && (
            <div className="card p-6">
              <h3 className="text-title text-[var(--text-primary)] mb-3">Probe questions</h3>
              <ul className="space-y-2 text-sm text-[var(--text-secondary)] list-decimal pl-5">
                {data.diagnostic_questions.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
