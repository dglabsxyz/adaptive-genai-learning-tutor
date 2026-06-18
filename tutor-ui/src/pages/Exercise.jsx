import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import SourceRef from '../components/SourceRef';
import SkillStateBadge from '../components/SkillStateBadge';
import NextStep from '../components/NextStep';
import { ErrorState, Spinner } from '../components/PageStates';
import { useApi } from '../api/useApi';
import { useSession } from '../context/SessionContext';
import { useToast } from '../context/ToastContext';
import { toSourceCards } from '../api/mappers';

const VERDICT_COLOR = { strong: 'var(--c-success)', partial: 'var(--c-accent)', needs_review: 'var(--c-danger)', weak: 'var(--c-danger)' };

export default function Exercise() {
  const api = useApi();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { learnerId } = useSession();
  const { addToast } = useToast();

  const [skill, setSkill] = useState('');
  const [exerciseType, setExerciseType] = useState('');
  const [answer, setAnswer] = useState('');
  const [exercise, setExercise] = useState(null);
  const [grade, setGrade] = useState(null);
  const [showHints, setShowHints] = useState(false);

  const progressQ = useQuery({ queryKey: ['progress', learnerId], queryFn: () => api.getProgress() });
  const skills = Object.keys(progressQ.data?.progress || {});

  const getExercise = useMutation({
    mutationFn: () => api.postExercise({ skill: skill || undefined, exerciseType: exerciseType || undefined }),
    onSuccess: (data) => {
      setExercise(data.exercise);
      setGrade(null);
      setAnswer('');
      setShowHints(false);
    },
    onError: (e) => addToast(e.message || 'Could not load an exercise', 'error'),
  });

  const submit = useMutation({
    mutationFn: () => api.postAnswer({ exerciseId: exercise.id, answer }),
    onSuccess: (data) => {
      setGrade(data);
      qc.invalidateQueries({ queryKey: ['progress', learnerId] });
      if (!data.needs_clarification) {
        addToast(`Graded: ${data.verdict || 'done'} (${Math.round((data.score || 0) * 100)}%)`, data.score >= 0.7 ? 'success' : 'info');
      }
    },
    onError: (e) => addToast(e.message || 'Could not grade your answer', 'error'),
  });

  const isMC = exercise?.exercise_type === 'multiple_choice' && Array.isArray(exercise?.choices);

  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      <div className="mb-6">
        <p className="text-overline text-[var(--text-muted)] mb-1">Practice</p>
        <h2 className="text-display text-[var(--text-primary)]">Exercise</h2>
        <p className="text-body text-[var(--text-secondary)]">Source-backed practice, graded deterministically against a rubric.</p>
      </div>

      {/* Controls */}
      <div className="card p-5 mb-6 flex flex-wrap items-end gap-3">
        <label className="text-sm text-[var(--text-secondary)]">
          <span className="block text-xs text-[var(--text-muted)] mb-1">Skill</span>
          <select value={skill} onChange={(e) => setSkill(e.target.value)} className="input min-w-[200px]">
            <option value="">Let the tutor choose</option>
            {skills.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <label className="text-sm text-[var(--text-secondary)]">
          <span className="block text-xs text-[var(--text-muted)] mb-1">Type</span>
          <select value={exerciseType} onChange={(e) => setExerciseType(e.target.value)} className="input min-w-[160px]">
            <option value="">Adaptive</option>
            <option value="multiple_choice">Multiple choice</option>
            <option value="short_answer">Short answer</option>
          </select>
        </label>
        <button onClick={() => getExercise.mutate()} disabled={getExercise.isPending} className="btn-primary">
          {getExercise.isPending ? <Spinner /> : exercise ? 'New exercise' : 'Get exercise'}
        </button>
      </div>

      {getExercise.isError && <ErrorState error={getExercise.error} onRetry={() => getExercise.mutate()} />}

      {!exercise && !getExercise.isPending && (
        <div className="card p-10 text-center text-[var(--text-muted)]">
          <div className="text-3xl mb-2">✏️</div>
          <p className="text-sm">Pick a skill (or let the tutor choose) and generate your first exercise.</p>
        </div>
      )}

      {exercise && (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Exercise + answer */}
          <div className="lg:col-span-3 card p-6">
            <div className="flex items-center gap-2 mb-3">
              <SkillStateBadge status={exercise.difficulty || 'developing'} />
              <span className="tag text-[11px]">{exercise.skill}</span>
              <span className="tag text-[11px]">{(exercise.exercise_type || '').replace('_', ' ')}</span>
            </div>
            <p className="text-[var(--text-primary)] font-medium mb-4 leading-relaxed">{exercise.prompt}</p>

            {isMC ? (
              <div className="space-y-2 mb-4">
                {exercise.choices.map((c, i) => {
                  const text = typeof c === 'string' ? c : c.text || c.label || JSON.stringify(c);
                  const selected = answer === text;
                  return (
                    <button
                      key={i}
                      onClick={() => setAnswer(text)}
                      disabled={submit.isPending}
                      className={`w-full text-left p-3 rounded-[var(--r-md)] border text-sm transition-all ${
                        selected
                          ? 'bg-[var(--c-primary-dim)] border-[var(--c-primary)] text-[var(--text-primary)]'
                          : 'bg-[var(--bg-surface)] border-[var(--border)] text-[var(--text-secondary)] hover:border-[var(--c-primary)]/30'
                      }`}
                    >
                      <span className="font-mono text-xs text-[var(--text-muted)] mr-2">{String.fromCharCode(65 + i)}</span>
                      {text}
                    </button>
                  );
                })}
              </div>
            ) : (
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Write your answer…"
                rows={5}
                disabled={submit.isPending}
                className="input w-full resize-none mb-4"
              />
            )}

            {Array.isArray(exercise.hints) && exercise.hints.length > 0 && (
              <div className="mb-4">
                <button onClick={() => setShowHints((v) => !v)} className="text-xs text-[var(--c-primary)] hover:underline">
                  {showHints ? 'Hide hints' : `Show hints (${exercise.hints.length})`}
                </button>
                {showHints && (
                  <ul className="mt-2 space-y-1 text-xs text-[var(--text-muted)] list-disc pl-5">
                    {exercise.hints.map((h, i) => (
                      <li key={i}>{h}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <div className="flex items-center gap-3">
              <button onClick={() => submit.mutate()} disabled={!answer.trim() || submit.isPending} className="btn-primary">
                {submit.isPending ? <Spinner /> : 'Submit answer'}
              </button>
              {grade && (
                <button onClick={() => getExercise.mutate()} className="btn-secondary">Next exercise</button>
              )}
            </div>

            {exercise.source_refs?.length > 0 && (
              <div className="mt-5 pt-4 border-t border-[var(--border)]">
                <p className="text-overline text-[var(--text-muted)] mb-2">Grounded in</p>
                <SourceRef sources={toSourceCards(exercise.source_refs)} />
              </div>
            )}
          </div>

          {/* Grade panel */}
          <div className="lg:col-span-2">
            {grade ? (
              <GradeCard grade={grade} />
            ) : (
              <div className="card p-6 text-center text-[var(--text-muted)] h-full flex flex-col items-center justify-center">
                <div className="text-2xl mb-2">🧮</div>
                <p className="text-sm">Submit your answer to see a rubric-based grade, covered points, and what to study next.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {grade && !grade.needs_clarification && (
        <NextStep
          title="Keep going"
          items={[
            { to: '/progress', label: 'See my progress →', primary: true },
            { to: '/study-plan', label: 'Study plan' },
            { to: '/tutor', label: 'Ask the tutor' },
          ]}
        />
      )}
    </div>
  );
}

function GradeCard({ grade }) {
  if (grade.needs_clarification) {
    return (
      <div className="card p-6" style={{ borderColor: 'var(--c-accent)' }}>
        <h3 className="text-title text-[var(--text-primary)] mb-2">Needs more detail</h3>
        <p className="text-sm text-[var(--text-secondary)]">{grade.message || 'Your answer was too vague to grade. Add specifics and resubmit.'}</p>
      </div>
    );
  }
  const pct = Math.round((grade.score || 0) * 100);
  const color = VERDICT_COLOR[grade.verdict] || 'var(--c-primary)';
  return (
    <div className="card p-6 animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-title text-[var(--text-primary)]">Result</h3>
        <span className="text-sm font-semibold px-3 py-1 rounded-full capitalize" style={{ color, background: `${color}20` }}>
          {grade.verdict} · {pct}%
        </span>
      </div>

      {grade.explanation && <p className="text-sm text-[var(--text-secondary)] mb-4">{grade.explanation}</p>}

      {grade.covered_points?.length > 0 && (
        <div className="mb-3">
          <p className="text-overline text-[var(--c-success)] mb-1">Covered</p>
          <ul className="space-y-1 text-sm text-[var(--text-secondary)]">
            {grade.covered_points.map((p, i) => (
              <li key={i} className="flex gap-2"><span className="text-[var(--c-success)]">✓</span>{p}</li>
            ))}
          </ul>
        </div>
      )}

      {grade.missed_points?.length > 0 && (
        <div className="mb-3">
          <p className="text-overline text-[var(--c-danger)] mb-1">Missed</p>
          <ul className="space-y-1 text-sm text-[var(--text-secondary)]">
            {grade.missed_points.map((p, i) => (
              <li key={i} className="flex gap-2"><span className="text-[var(--c-danger)]">○</span>{p}</li>
            ))}
          </ul>
        </div>
      )}

      {grade.mastery_update && (
        <div className="mt-4 pt-4 border-t border-[var(--border)] text-xs text-[var(--text-muted)]">
          {typeof grade.mastery_update.proficiency_before === 'number' && typeof grade.mastery_update.proficiency_after === 'number' ? (
            <p>
              Mastery: {Math.round(grade.mastery_update.proficiency_before * 100)}% →{' '}
              <span className="text-[var(--text-primary)] font-medium">{Math.round(grade.mastery_update.proficiency_after * 100)}%</span>
            </p>
          ) : (
            <p>Mastery updated.</p>
          )}
          <p className="mt-1">
            {grade.mastery_update.status_reason ||
              `Proficiency only moves on graded evidence — a “${grade.verdict}” answer ${
                (grade.score ?? 0) >= 0.45 ? 'nudged it up' : 'nudged it down'
              }.`}
          </p>
        </div>
      )}

      {grade.source_refs?.length > 0 && <SourceRef sources={toSourceCards(grade.source_refs)} />}
    </div>
  );
}
