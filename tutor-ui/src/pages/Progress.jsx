import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import ProgressRing from '../components/ProgressRing';
import SkillStateBadge from '../components/SkillStateBadge';
import SourceRef from '../components/SourceRef';

const skillRadarData = [
  { subject: 'LLMs', A: 85, fullMark: 100 },
  { subject: 'Prompt Eng', A: 72, fullMark: 100 },
  { subject: 'RAG', A: 45, fullMark: 100 },
  { subject: 'Agents', A: 20, fullMark: 100 },
  { subject: 'MCP', A: 10, fullMark: 100 },
  { subject: 'Fine-tuning', A: 60, fullMark: 100 },
  { subject: 'Multimodal', A: 30, fullMark: 100 },
  { subject: 'Safety/Eval', A: 55, fullMark: 100 },
];

const historyData = [
  { day: 'Mon', exercises: 3, avgScore: 0.82 },
  { day: 'Tue', exercises: 5, avgScore: 0.75 },
  { day: 'Wed', exercises: 2, avgScore: 0.90 },
  { day: 'Thu', exercises: 4, avgScore: 0.68 },
  { day: 'Fri', exercises: 6, avgScore: 0.85 },
  { day: 'Sat', exercises: 3, avgScore: 0.78 },
  { day: 'Sun', exercises: 4, avgScore: 0.88 },
];

const spacedReview = [
  { skill: 'LLM Fundamentals', dueIn: '2 days', status: 'review', proficiency: 0.85 },
  { skill: 'Prompt Engineering', dueIn: '5 days', status: 'proficient', proficiency: 0.72 },
  { skill: 'Fine-Tuning', dueIn: '1 day', status: 'review', proficiency: 0.60 },
];

const masteryTransitions = [
  { from: 'exposure', to: 'developing', skill: 'Prompt Engineering', date: '2 days ago' },
  { from: 'developing', to: 'proficient', skill: 'LLM Fundamentals', date: '1 week ago' },
  { from: 'exposure', to: 'developing', skill: 'RAG Architecture', date: '3 days ago' },
];

export default function Progress() {
  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      <div className="mb-8">
        <p className="text-overline text-[var(--text-muted)] mb-1">Analytics</p>
        <h2 className="text-display text-[var(--text-primary)] mb-2">My Progress</h2>
        <p className="text-body text-[var(--text-secondary)]">Detailed analytics, skill radar, and spaced-repetition schedule.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
        <div className="card p-6 text-center">
          <ProgressRing progress={72} size={90} strokeWidth={5} color="#EC008C" label="Avg Score" sublabel="Last 30 days" />
        </div>
        <div className="card p-6 text-center">
          <ProgressRing progress={85} size={90} strokeWidth={5} color="#10b981" label="Completion" sublabel="Study plan" />
        </div>
        <div className="card p-6 text-center">
          <ProgressRing progress={45} size={90} strokeWidth={5} color="#F15B2A" label="Retention" sublabel="Spaced reviews" />
        </div>
        <div className="card p-6 flex flex-col justify-center">
          <p className="text-caption text-[var(--text-muted)] mb-1">Total Exercises</p>
          <p className="text-4xl font-bold text-[var(--text-primary)]">127</p>
          <p className="text-caption text-[var(--text-muted)] mt-1">+12 this week</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="card p-6">
          <h3 className="text-title text-[var(--text-primary)] mb-4">Skill Radar</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={skillRadarData}>
                <PolarGrid stroke="var(--border)" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <Radar
                  name="Proficiency"
                  dataKey="A"
                  stroke="var(--c-primary)"
                  strokeWidth={2}
                  fill="var(--c-primary)"
                  fillOpacity={0.2}
                />
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-md)',
                    color: 'var(--text-primary)',
                    fontSize: '13px',
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-title text-[var(--text-primary)] mb-4">Weekly Activity</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historyData}>
                <CartesianGrid stroke="var(--border-subtle)" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} />
                <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} axisLine={{ stroke: 'var(--border)' }} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-md)',
                    color: 'var(--text-primary)',
                    fontSize: '13px',
                  }}
                />
                <Line type="monotone" dataKey="exercises" stroke="var(--c-primary)" strokeWidth={2} dot={{ fill: 'var(--c-primary)', r: 4 }} name="Exercises" />
                <Line type="monotone" dataKey="avgScore" stroke="var(--c-secondary)" strokeWidth={2} dot={{ fill: 'var(--c-secondary)', r: 4 }} name="Avg Score" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="card p-6">
          <h3 className="text-title text-[var(--text-primary)] mb-4">Spaced Repetition Due</h3>
          <div className="space-y-3">
            {spacedReview.map((item, i) => (
              <div key={i} className="flex items-center justify-between p-4 rounded-[var(--r-md)] bg-[var(--bg-surface)] border border-[var(--border)]">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${item.status === 'review' ? 'bg-[var(--c-primary)] animate-pulse' : 'bg-[var(--c-success)]'}`} />
                  <div>
                    <p className="text-sm text-[var(--text-secondary)]">{item.skill}</p>
                    <p className="text-xs text-[var(--text-muted)]">Proficiency: {Math.round(item.proficiency * 100)}%</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-xs font-semibold px-2 py-1 rounded-full
                    ${item.status === 'review' ? 'bg-[var(--c-primary-dim)] text-[var(--c-primary)]' : 'bg-[var(--c-success-dim)] text-[var(--c-success)]'}`}>
                    Due in {item.dueIn}
                  </span>
                </div>
              </div>
            ))}
          </div>
          <button className="mt-4 w-full btn-primary text-xs">
            Start Review Session
          </button>
        </div>

        <div className="card p-6">
          <h3 className="text-title text-[var(--text-primary)] mb-4">Recent Mastery Changes</h3>
          <div className="space-y-3">
            {masteryTransitions.map((tx, i) => (
              <div key={i} className="flex items-center gap-4 p-4 rounded-[var(--r-md)] bg-[var(--bg-surface)] border border-[var(--border)]">
                <div className="flex items-center gap-2">
                  <SkillStateBadge status={tx.from} showIcon={false} />
                  <span className="text-[var(--text-muted)] text-sm">→</span>
                  <SkillStateBadge status={tx.to} showIcon={false} />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-[var(--text-secondary)]">{tx.skill}</p>
                  <p className="text-xs text-[var(--text-muted)]">{tx.date}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <SourceRef sources={[
        { title: 'Learner Profile Store', record_type: 'coverage', path: '/memories/learner_001/profile.json', citation_url: null },
      ]} />
    </div>
  );
}
