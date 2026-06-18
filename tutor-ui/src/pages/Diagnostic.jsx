import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import SkillStateBadge from '../components/SkillStateBadge';
import SourceRef from '../components/SourceRef';
import NextStep from '../components/NextStep';
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
  const [answers, setAnswers] = useState({}); // { [questionIndex]: text }

  const run = useMutation({
    mutationFn: ({ goalText, answerList }) => api.postDiagnostic({ goal: goalText, answers: answerList }),
    onError: (e) => addToast(e.message || 'Diagnostic failed', 'error'),
  });

  const start = (g) => {
    const value = (g ?? goal).trim();
    if (!value) return;
    setGoal(value);
    setAnswers({});
    run.mutate({ goalText: value });
  };

  const refine = () => {
    const answerList = Object.values(answers).map((a) => (a || '').trim()).filter(Boolean);
    if (!answerList.length) {
      addToast('Answer at least one probe question to refine.', 'info');
      return;
    }
    run.mutate({ goalText: goal, answerList });
  };

  const data = run.data;
  const questions = Array.isArray(data?.diagnostic_questions) ? data.diagnostic_questions : [];
  const refined = run.isSuccess && (run.variables?.answerList?.length || 0) > 0;

  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      <div className="mb-6">
        <p className="text-overline text-[var(--text-muted)] mb-1">Assessment</p>
        <h2 className="text-display text-[var(--text-primary)]">Diagnostic</h2>
        <p className="text-body text-[var(--text-secondary)]">
          Tell the tutor your goal; it estimates where you stand, then sharpens the estimate from your answers to a
          few probe questions.
        </p>
      </div>

      <div className="card p-6 mb-6">
        <label className="block text-sm text-[var(--text-secondary)] mb-2">Your learning goal</label>
        <div className="flex gap-3">
          <input
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && start()}
            placeholder="e.g. I want to build production RAG systems with agents"
            className="input flex-1"
          />
          <button onClick={() => start()} disabled={run.isPending || !goal.trim()} className="btn-primary px-5">
            {run.isPending ? <Spinner /> : 'Run diagnostic'}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {GOAL_PRESETS.map((g) => (
            <button key={g} onClick={() => start(g)} disabled={run.isPending} className="tag hover:text-[var(--c-primary)] transition-colors text-xs">
              {g}
            </button>
          ))}
        </div>
      </div>

      {run.isError && <ErrorState error={run.error} onRetry={() => start()} />}

      {data && (
        <div className="space-y-6 animate-fade-in">
          <div className="card p-6">
            <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
              <h3 className="text-title text-[var(--text-primary)]">Summary</h3>
              {refined && <span className="tag text-[11px]" style={{ color: 'var(--c-success)' }}>↑ refined from your answers</span>}
            </div>
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

          {questions.length > 0 && (
            <div className="card p-6">
              <h3 className="text-title text-[var(--text-primary)] mb-1">Sharpen the estimate</h3>
              <p className="text-caption text-[var(--text-muted)] mb-4">
                Answer what you can — the tutor folds your answers into a more accurate read. Skip any you're unsure of.
              </p>
              <div className="space-y-3">
                {questions.map((qn, i) => (
                  <div key={i}>
                    <label className="block text-sm text-[var(--text-secondary)] mb-1">
                      <span className="text-[var(--text-muted)] mr-1">{i + 1}.</span>
                      {qn}
                    </label>
                    <textarea
                      value={answers[i] || ''}
                      onChange={(e) => setAnswers((prev) => ({ ...prev, [i]: e.target.value }))}
                      rows={2}
                      placeholder="Your answer…"
                      disabled={run.isPending}
                      className="input w-full resize-none"
                    />
                  </div>
                ))}
              </div>
              <button onClick={refine} disabled={run.isPending} className="btn-primary text-sm mt-4">
                {run.isPending ? <Spinner /> : 'Refine my assessment'}
              </button>
            </div>
          )}

          <NextStep
            title="Where to next"
            items={[
              { to: '/study-plan', label: 'Build my study plan →', primary: true },
              { to: '/exercise', label: 'Practice now' },
              { to: '/tutor', label: 'Ask the tutor' },
            ]}
          />
        </div>
      )}
    </div>
  );
}
