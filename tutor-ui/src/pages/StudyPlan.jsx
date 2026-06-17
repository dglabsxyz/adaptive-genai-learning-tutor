import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import SkillStateBadge from '../components/SkillStateBadge';
import SourceRef from '../components/SourceRef';
import { ErrorState, Spinner } from '../components/PageStates';
import { useApi } from '../api/useApi';
import { useToast } from '../context/ToastContext';
import { toSourceCards } from '../api/mappers';

const GOAL_PRESETS = [
  'Become production-ready with RAG and AI agents',
  'Master prompt + context engineering',
  'Ship a tool-using agent with MCP',
];

export default function StudyPlan() {
  const api = useApi();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [goal, setGoal] = useState('');

  const run = useMutation({
    mutationFn: (g) => api.postStudyPlan({ goal: g }),
    onError: (e) => addToast(e.message || 'Could not build a plan', 'error'),
  });

  const submit = (g) => {
    const value = (g ?? goal).trim();
    if (!value) return;
    setGoal(value);
    run.mutate(value);
  };

  const data = run.data;
  const modules = Array.isArray(data?.modules) ? [...data.modules].sort((a, b) => (a.order || 0) - (b.order || 0)) : [];

  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      <div className="mb-6">
        <p className="text-overline text-[var(--text-muted)] mb-1">Path</p>
        <h2 className="text-display text-[var(--text-primary)]">Study Plan</h2>
        <p className="text-body text-[var(--text-secondary)]">A prerequisite-aware, source-grounded path from where you are to production-ready.</p>
      </div>

      <div className="card p-6 mb-6">
        <label className="block text-sm text-[var(--text-secondary)] mb-2">Goal</label>
        <div className="flex gap-3">
          <input
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
            placeholder="e.g. Become production-ready with RAG and agents"
            className="input flex-1"
          />
          <button onClick={() => submit()} disabled={run.isPending || !goal.trim()} className="btn-primary px-5">
            {run.isPending ? <Spinner /> : 'Build plan'}
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
        <div className="animate-fade-in">
          {data.summary && (
            <div className="card p-6 mb-6">
              <h3 className="text-title text-[var(--text-primary)] mb-2">Overview</h3>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{data.summary}</p>
              {data.source_refs?.length > 0 && <SourceRef sources={toSourceCards(data.source_refs)} />}
            </div>
          )}

          <div className="relative pl-6">
            <div className="absolute left-[9px] top-2 bottom-2 w-px bg-[var(--border)]" />
            <div className="space-y-4">
              {modules.map((m, i) => (
                <div key={i} className="relative">
                  <div className="absolute -left-[22px] top-5 w-4 h-4 rounded-full gradient-primary border-2 border-[var(--bg)]" />
                  <div className="card p-5">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="text-xs font-mono text-[var(--text-muted)]">Module {m.order ?? i + 1}</span>
                      <span className="text-sm font-semibold text-[var(--text-primary)]">{m.skill}</span>
                      {m.status && <SkillStateBadge status={m.status} />}
                      {m.estimated_time && <span className="tag text-[11px]">⏱ {m.estimated_time}</span>}
                    </div>
                    {m.milestone && <p className="text-sm text-[var(--text-secondary)] mb-1"><span className="text-[var(--text-muted)]">Milestone:</span> {m.milestone}</p>}
                    {m.why && <p className="text-sm text-[var(--text-secondary)] mb-1"><span className="text-[var(--text-muted)]">Why now:</span> {m.why}</p>}
                    {m.review_checkpoint && <p className="text-xs text-[var(--text-muted)]">↻ {m.review_checkpoint}</p>}
                    {m.source_refs?.length > 0 && <SourceRef sources={toSourceCards(m.source_refs)} />}
                    <button onClick={() => navigate('/exercise')} className="btn-secondary text-xs mt-3">Practice {m.skill} →</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
