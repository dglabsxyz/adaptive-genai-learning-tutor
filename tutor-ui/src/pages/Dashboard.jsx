import React from 'react';
import ProgressRing from '../components/ProgressRing';
import SkillMasteryBar from '../components/SkillMasteryBar';
import StatCard from '../components/StatCard';
import QuickStartBanner from '../components/QuickStartBanner';
import SourceRef from '../components/SourceRef';

const mockSkills = [
  { name: 'LLM Fundamentals',       proficiency: 0.85, status: 'proficient',  attempts: 12, streak: 4 },
  { name: 'Prompt Engineering',     proficiency: 0.72, status: 'developing',  attempts: 8,  streak: 2 },
  { name: 'RAG Architecture',       proficiency: 0.45, status: 'developing',  attempts: 5,  streak: 0 },
  { name: 'AI Agents & Tools',      proficiency: 0.20, status: 'exposure',    attempts: 2,  streak: 0 },
  { name: 'MCP Integration',        proficiency: 0.10, status: 'exposure',    attempts: 1,  streak: 0 },
  { name: 'Fine-Tuning',            proficiency: 0.60, status: 'developing',  attempts: 6,  streak: 1 },
  { name: 'Multimodal AI',          proficiency: 0.30, status: 'exposure',    attempts: 3,  streak: 0 },
  { name: 'AI Safety & Evaluation', proficiency: 0.55, status: 'developing',  attempts: 4,  streak: 0 },
];

const mockActivity = [
  { action: 'Completed exercise',   detail: 'RAG vs Fine-Tuning comparison — scored 90%',       time: '2 min ago',   score: 0.90 },
  { action: 'Mastery promoted',     detail: 'Prompt Engineering → Developing',                time: '15 min ago',  score: null },
  { action: 'Started new module',   detail: 'Module 4: RAG Architecture',                      time: '1 hr ago',    score: null },
  { action: 'Completed diagnostic', detail: '8-question adaptive assessment finished',           time: 'Yesterday',   score: null },
];

const mockRecommendations = [
  { title: 'Continue RAG practice',   subtitle: 'Module 4 exercise: Architecture scenario',     type: 'exercise', icon: '✏️', target: 'exercise' },
  { title: 'Review LLM fundamentals', subtitle: 'Spaced repetition due in 2 days',              type: 'review',   icon: '↻', target: 'exercise' },
  { title: 'View your study plan',   subtitle: '7 modules, 11 weeks, currently on Module 4',      type: 'discover', icon: '🗺️', target: 'study-plan' },
];

export default function Dashboard({ onNavigate }) {
  const overallProgress = Math.round(
    mockSkills.reduce((sum, s) => sum + s.proficiency, 0) / mockSkills.length * 100
  );
  const masteredCount = mockSkills.filter(s => s.status === 'mastered').length;
  const developingCount = mockSkills.filter(s => s.status === 'developing').length;
  const proficientCount = mockSkills.filter(s => s.status === 'proficient').length;
  const exposureCount = mockSkills.filter(s => s.status === 'exposure').length;

  const handleQuickStart = () => {
    onNavigate?.('exercise');
  };

  const handleRecClick = (target) => {
    onNavigate?.(target);
  };

  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      {/* Header */}
      <div className="mb-6">
        <p className="text-overline text-[var(--text-muted)] mb-1">Overview</p>
        <h2 className="text-display text-[var(--text-primary)] mb-2">Welcome back, Alex 👋</h2>
        <p className="text-body text-[var(--text-secondary)]">You're on Module 4 of your GenAI study plan. Here's where you stand.</p>
      </div>

      {/* Quick Start Banner — tells user exactly what to do next */}
      <QuickStartBanner stage="has-plan" onAction={handleQuickStart} />

      {/* Top stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <StatCard
          icon="🎯"
          value={`${overallProgress}%`}
          label="Overall Proficiency"
          trend={12}
          color="#EC008C"
        />
        <StatCard
          icon="🏆"
          value={`${proficientCount}`}
          label="Proficient Skills"
          trend={8}
          color="#10b981"
        />
        <StatCard
          icon="📖"
          value={`${developingCount}`}
          label="Developing"
          trend={-2}
          color="#f59e0b"
        />
        <StatCard
          icon="🔥"
          value="4 days"
          label="Current Streak"
          trend={25}
          color="#F15B2A"
        />
      </div>

      {/* Progress ring + skill breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="card p-8 flex flex-col items-center justify-center animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
          <ProgressRing progress={overallProgress} size={140} strokeWidth={8} color="#EC008C" />
          <p className="text-sm font-medium text-[var(--text-secondary)] mt-4">Combined Proficiency</p>
          <p className="text-xs text-[var(--text-muted)] mt-1">{exposureCount} skills at exposure · {developingCount} developing · {proficientCount} proficient</p>
        </div>

        <div className="lg:col-span-2 card p-6 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-title text-[var(--text-primary)]">Skill Breakdown</h3>
            <div className="flex items-center gap-3 text-caption text-[var(--text-muted)]">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--mastery-exposure)]"/> Exposure</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--mastery-developing)]"/> Developing</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--mastery-proficient)]"/> Proficient</span>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {mockSkills.map((skill, i) => (
              <SkillMasteryBar key={i} {...skill} />
            ))}
          </div>
        </div>
      </div>

      {/* Main grid: Activity + Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recommendations */}
        <div className="card p-6 animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
          <h3 className="text-title text-[var(--text-primary)] mb-4">Recommended Next</h3>
          <div className="space-y-3">
            {mockRecommendations.map((rec, i) => (
              <button
                key={i}
                onClick={() => handleRecClick(rec.target)}
                className="w-full text-left p-4 rounded-[var(--r-md)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-hover)]
                           border border-[var(--border)] hover:border-[var(--c-primary)]/20 transition-all duration-200 group"
              >
                <div className="flex items-start gap-3">
                  <span className="text-xl text-[var(--c-primary)] group-hover:scale-110 transition-transform duration-200">{rec.icon}</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-[var(--text-primary)] group-hover:text-[var(--c-primary)] transition-colors">{rec.title}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{rec.subtitle}</p>
                  </div>
                  <span className="text-[var(--text-muted)] group-hover:text-[var(--c-primary)] transition-colors">→</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="lg:col-span-2 card p-6 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
          <h3 className="text-title text-[var(--text-primary)] mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {mockActivity.map((act, i) => (
              <div key={i} className="flex items-center gap-4 p-3 rounded-[var(--r-md)] bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--border-hover)] transition-colors">
                <div className={`w-9 h-9 rounded-[var(--r-md)] flex items-center justify-center flex-shrink-0 text-sm
                  ${act.score !== null
                    ? (act.score >= 0.8
                        ? 'bg-[var(--c-success-dim)] text-[var(--c-success)]'
                        : 'bg-[var(--c-accent-dim)] text-[var(--c-accent)]')
                    : 'bg-[var(--c-primary-dim)] text-[var(--c-primary)]'
                  }`}>
                  {act.score !== null ? (act.score >= 0.8 ? '✓' : '⚡') : '📌'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[var(--text-primary)]">{act.action}</p>
                  <p className="text-xs text-[var(--text-muted)]">{act.detail}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  {act.score !== null && (
                    <span className={`text-xs font-mono font-bold block mb-0.5
                      ${act.score >= 0.8 ? 'text-[var(--c-success)]' : 'text-[var(--c-accent)]'}`}>
                      {Math.round(act.score * 100)}%
                    </span>
                  )}
                  <span className="text-[11px] text-[var(--text-muted)]">{act.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Source refs footer */}
      <div className="mt-8 card p-5 animate-fade-in-up" style={{ animationDelay: '0.25s' }}>
        <p className="text-overline text-[var(--text-muted)] mb-3">Curriculum Grounded In</p>
        <SourceRef sources={[
          { title: 'GenAI Research Corpus v2.4', record_type: 'coverage', path: 'coverage_report.json', citation_url: null },
          { title: 'LLM Fundamentals (Topic)', record_type: 'topic', path: 'topics/llm_fundamentals/topic_summary.json', citation_url: null },
          { title: 'RAG Architecture (Topic)', record_type: 'topic', path: 'topics/rag_architecture/topic_summary.json', citation_url: null },
        ]} />
      </div>
    </div>
  );
}
