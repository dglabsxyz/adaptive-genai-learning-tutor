import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import ProgressRing from '../components/ProgressRing';
import SkillMasteryBar from '../components/SkillMasteryBar';
import StatCard from '../components/StatCard';
import SourceRef from '../components/SourceRef';
import { LoadingState, ErrorState } from '../components/PageStates';
import { useApi } from '../api/useApi';
import { useSession } from '../context/SessionContext';
import { toSkillBars, overallProficiency, countByStatus } from '../api/mappers';

export default function Dashboard() {
  const api = useApi();
  const navigate = useNavigate();
  const { learnerId } = useSession();

  const progressQ = useQuery({
    queryKey: ['progress', learnerId],
    queryFn: () => api.getProgress(),
  });
  const healthQ = useQuery({ queryKey: ['health-dash'], queryFn: () => api.getHealth(), retry: 0 });

  if (progressQ.isLoading) return <Shell><LoadingState label="Loading your progress…" /></Shell>;
  if (progressQ.isError) return <Shell><ErrorState error={progressQ.error} onRetry={progressQ.refetch} /></Shell>;

  const skills = toSkillBars(progressQ.data?.progress);
  const overall = overallProficiency(skills);
  const counts = countByStatus(skills);
  const weakest = [...skills].sort((a, b) => a.proficiency - b.proficiency).slice(0, 3);
  const dueReview = skills.filter((s) => s.status === 'review' || s.nextReview);
  const docCount = healthQ.data?.corpus?.document_count;

  const recommendations = [
    { title: 'Practice your weakest skill', subtitle: weakest[0] ? `${weakest[0].name} · ${Math.round((weakest[0].proficiency || 0) * 100)}%` : 'Start practicing', icon: '✏️', to: '/exercise' },
    { title: 'Talk to your tutor', subtitle: 'Diagnose, plan, and practice conversationally', icon: '💬', to: '/tutor' },
    { title: 'View your study plan', subtitle: 'A prerequisite-aware path to production-ready', icon: '🗺️', to: '/study-plan' },
  ];

  return (
    <Shell>
      <div className="mb-6">
        <p className="text-overline text-[var(--text-muted)] mb-1">Overview</p>
        <h2 className="text-display text-[var(--text-primary)] mb-2">Welcome back, {learnerId} 👋</h2>
        <p className="text-body text-[var(--text-secondary)]">
          Here's where you stand across the ten GenAI engineering skills.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <StatCard icon="🎯" value={`${overall}%`} label="Overall Proficiency" color="#EC008C" />
        <StatCard icon="🏆" value={`${counts.proficient + counts.mastered}`} label="Proficient+ Skills" color="#10b981" />
        <StatCard icon="📖" value={`${counts.developing}`} label="Developing" color="#f59e0b" />
        <StatCard icon="↻" value={`${dueReview.length}`} label="Reviews Due" color="#F15B2A" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="card p-8 flex flex-col items-center justify-center">
          <ProgressRing progress={overall} size={140} strokeWidth={8} color="#EC008C" />
          <p className="text-sm font-medium text-[var(--text-secondary)] mt-4">Combined Proficiency</p>
          <p className="text-xs text-[var(--text-muted)] mt-1 text-center">
            {counts.exposure} exposure · {counts.developing} developing · {counts.proficient + counts.mastered} proficient
          </p>
        </div>

        <div className="lg:col-span-2 card p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-title text-[var(--text-primary)]">Skill Breakdown</h3>
            <button onClick={() => navigate('/progress')} className="text-xs text-[var(--c-primary)] hover:underline">
              Full progress →
            </button>
          </div>
          {skills.length ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {skills.map((s) => (
                <SkillMasteryBar key={s.name} {...s} onClick={() => navigate('/progress')} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--text-muted)]">No skills tracked yet. Start with the tutor or a diagnostic.</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card p-6">
          <h3 className="text-title text-[var(--text-primary)] mb-4">Recommended Next</h3>
          <div className="space-y-3">
            {recommendations.map((rec) => (
              <button
                key={rec.title}
                onClick={() => navigate(rec.to)}
                className="w-full text-left p-4 rounded-[var(--r-md)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-hover)] border border-[var(--border)] hover:border-[var(--c-primary)]/20 transition-all group"
              >
                <div className="flex items-start gap-3">
                  <span className="text-xl text-[var(--c-primary)] group-hover:scale-110 transition-transform">{rec.icon}</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-[var(--text-primary)] group-hover:text-[var(--c-primary)]">{rec.title}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{rec.subtitle}</p>
                  </div>
                  <span className="text-[var(--text-muted)] group-hover:text-[var(--c-primary)]">→</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="lg:col-span-2 card p-6">
          <h3 className="text-title text-[var(--text-primary)] mb-1">Focus areas</h3>
          <p className="text-caption text-[var(--text-muted)] mb-4">Your lowest-proficiency skills — good candidates for the next session.</p>
          <div className="space-y-3">
            {weakest.map((s) => (
              <div key={s.name} className="flex items-center gap-4 p-3 rounded-[var(--r-md)] bg-[var(--bg-surface)] border border-[var(--border)]">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[var(--text-primary)]">{s.name}</p>
                  {s.statusReason && <p className="text-xs text-[var(--text-muted)] truncate">{s.statusReason}</p>}
                </div>
                <span className="text-xs font-mono text-[var(--text-secondary)]">{Math.round((s.proficiency || 0) * 100)}%</span>
                <button onClick={() => navigate('/exercise')} className="btn-secondary text-xs">Practice</button>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-8 card p-5">
        <p className="text-overline text-[var(--text-muted)] mb-2">Curriculum grounded in the GenAI research corpus</p>
        <p className="text-sm text-[var(--text-secondary)]">
          {docCount ? `${docCount} source records` : 'Source records'} across topics, courses, and instructors — every
          recommendation and exercise is cited back to them.
        </p>
      </div>
    </Shell>
  );
}

function Shell({ children }) {
  return <div className="h-full overflow-y-auto p-8 animate-fade-in">{children}</div>;
}
