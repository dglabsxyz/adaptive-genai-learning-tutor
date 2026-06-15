import React, { useState } from 'react';
import SkillStateBadge from '../components/SkillStateBadge';
import SourceRef from '../components/SourceRef';

const modules = [
  {
    id: 1,
    title: 'LLM Foundations',
    subtitle: 'Understanding transformer architecture, tokenization, and inference',
    status: 'mastered',
    duration: '2 weeks',
    progress: 100,
    courses: ['DeepLearning.AI LLM Fundamentals', 'Hugging Face NLP Course'],
    sources: [
      { title: 'LLM Fundamentals (Topic)', record_type: 'topic', path: 'topics/llm_fundamentals', citation_url: null },
    ],
    prerequisites: [],
  },
  {
    id: 2,
    title: 'Prompt Engineering',
    subtitle: 'Zero-shot, few-shot, chain-of-thought, and structured prompting',
    status: 'proficient',
    duration: '1.5 weeks',
    progress: 85,
    courses: ['Prompt Engineering for Developers', 'Anthropic Prompt Engineering Guide'],
    sources: [
      { title: 'Prompt Engineering (Topic)', record_type: 'topic', path: 'topics/prompt_engineering', citation_url: null },
    ],
    prerequisites: [1],
  },
  {
    id: 3,
    title: 'Context Engineering',
    subtitle: 'Window management, long-context strategies, and compression',
    status: 'developing',
    duration: '1 week',
    progress: 60,
    courses: ['Advanced Context Engineering', 'LangChain Context Modules'],
    sources: [
      { title: 'Context Engineering (Topic)', record_type: 'topic', path: 'topics/context_engineering', citation_url: null },
    ],
    prerequisites: [2],
  },
  {
    id: 4,
    title: 'Retrieval-Augmented Generation',
    subtitle: 'Vector stores, embeddings, chunking, and hybrid retrieval',
    status: 'developing',
    duration: '2 weeks',
    progress: 45,
    courses: ['RAG from Scratch', 'Weaviate Vector Search Course'],
    sources: [
      { title: 'RAG Architecture (Topic)', record_type: 'topic', path: 'topics/rag_architecture', citation_url: null },
    ],
    prerequisites: [3],
  },
  {
    id: 5,
    title: 'Agentic RAG',
    subtitle: 'Self-correcting retrieval, tool use, and multi-step reasoning',
    status: 'exposure',
    duration: '2 weeks',
    progress: 15,
    courses: ['LangGraph Agentic RAG', 'LlamaIndex Agent Courses'],
    sources: [
      { title: 'Agentic RAG (Topic)', record_type: 'topic', path: 'topics/agentic_rag', citation_url: null },
    ],
    prerequisites: [4],
  },
  {
    id: 6,
    title: 'MCP & Tool Integration',
    subtitle: 'Model Context Protocol, tool definition, and client integration',
    status: 'exposure',
    duration: '1 week',
    progress: 10,
    courses: ['MCP Protocol Deep Dive', 'Claude Desktop Integration'],
    sources: [
      { title: 'MCP Integration (Topic)', record_type: 'topic', path: 'topics/mcp_integration', citation_url: null },
    ],
    prerequisites: [5],
  },
  {
    id: 7,
    title: 'AI Safety & Evaluation',
    subtitle: 'Red-teaming, evals, and production readiness checks',
    status: 'developing',
    duration: '1.5 weeks',
    progress: 55,
    courses: ['AI Safety Fundamentals', 'Evals for Production Systems'],
    sources: [
      { title: 'AI Safety & Evaluation (Topic)', record_type: 'topic', path: 'topics/ai_safety_evaluation', citation_url: null },
    ],
    prerequisites: [1],
  },
];

const statusColors = {
  exposure: 'var(--mastery-exposure)',
  developing: 'var(--mastery-developing)',
  proficient: 'var(--mastery-proficient)',
  mastered: 'var(--mastery-mastered)',
  review: 'var(--mastery-review)',
};

function ModuleCard({ module, index, isExpanded, onToggle }) {
  const color = statusColors[module.status];
  return (
    <div className={`relative animate-fade-in-up`} style={{ animationDelay: `${index * 0.08}s` }}>
      {index > 0 && (
        <div className="absolute -top-6 left-8 w-0.5 h-6 bg-[var(--border)]" />
      )}

      <div
        className={`card transition-all duration-300 overflow-hidden
          ${isExpanded ? 'border-[var(--border-hover)]' : ''}
          ${module.id === 4 ? 'border-l-4 border-l-[var(--c-primary)]' : ''}`}
      >
        <button
          onClick={onToggle}
          className="w-full text-left p-5 flex items-center gap-4"
        >
          <div
            className="w-14 h-14 rounded-[var(--r-md)] flex items-center justify-center text-lg font-bold flex-shrink-0"
            style={{
              background: `${color}18`,
              color: color,
              boxShadow: module.progress === 100 ? `0 0 20px ${color}44` : 'none',
            }}
          >
            {module.progress === 100 ? '✓' : module.id}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold text-[var(--text-primary)] truncate">{module.title}</h3>
              {module.id === 4 && (
                <span className="px-1.5 py-0.5 rounded-[var(--r-xs)] bg-[var(--c-primary)] text-white text-[10px] font-bold uppercase tracking-wider">Current</span>
              )}
              <SkillStateBadge status={module.status} />
            </div>
            <p className="text-xs text-[var(--text-muted)] truncate">{module.subtitle}</p>
          </div>

          <div className="flex items-center gap-4 flex-shrink-0">
            <div className="text-right">
              <p className="text-xs text-[var(--text-muted)]">{module.duration}</p>
              <p className="text-xs font-mono text-[var(--text-secondary)]">{module.progress}%</p>
            </div>
            <div className="w-8 h-8 rounded-full bg-[var(--bg-surface)] flex items-center justify-center text-[var(--text-muted)] transition-transform duration-200"
                 style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
              ▼
            </div>
          </div>
        </button>

        {isExpanded && (
          <div className="px-5 pb-5 border-t border-[var(--border)] animate-fade-in">
            <div className="mt-4">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs text-[var(--text-muted)]">Module Progress</span>
                <span className="text-xs font-mono text-[var(--text-secondary)]">{module.progress}%</span>
              </div>
              <div className="h-2.5 rounded-full bg-[var(--border-subtle)] overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-1000"
                  style={{ width: `${module.progress}%`, background: color, boxShadow: `0 0 12px ${color}66` }}
                />
              </div>
            </div>

            <div className="mt-4">
              <p className="text-overline text-[var(--text-muted)] mb-2">Recommended Courses</p>
              <div className="flex flex-wrap gap-2">
                {module.courses.map((c, i) => (
                  <span key={i} className="text-xs px-3 py-1.5 rounded-[var(--r-sm)] bg-[var(--bg-surface)] text-[var(--text-secondary)] border border-[var(--border)]">
                    {c}
                  </span>
                ))}
              </div>
            </div>

            {module.prerequisites.length > 0 && (
              <div className="mt-4">
                <p className="text-overline text-[var(--text-muted)] mb-2">Prerequisites</p>
                <div className="flex gap-2">
                  {module.prerequisites.map(pid => {
                    const prereq = modules.find(m => m.id === pid);
                    return (
                      <span key={pid} className="text-xs px-2.5 py-1 rounded-[var(--r-sm)] bg-[var(--bg-surface)] text-[var(--text-muted)] border border-[var(--border)]">
                        Module {pid}: {prereq?.title}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}

            <SourceRef sources={module.sources} />

            <div className="mt-5 flex gap-3">
              <button className="btn-primary text-xs px-4 py-2">
                Start Module
              </button>
              <button className="btn-secondary text-xs px-4 py-2">
                View Exercises
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function StudyPlan() {
  const [expandedId, setExpandedId] = useState(4);
  const completedCount = modules.filter(m => m.status === 'mastered').length;
  const totalModules = modules.length;
  const overallProgress = Math.round(modules.reduce((s, m) => s + m.progress, 0) / totalModules);

  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      <div className="mb-8">
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mb-3">
          <span>Dashboard</span>
          <span>→</span>
          <span className="text-[var(--text-primary)] font-medium">Study Plan</span>
          <span className="px-2 py-0.5 rounded-[var(--r-xs)] bg-[var(--c-primary-dim)] text-[var(--c-primary)] font-semibold text-[10px]">Module 4 of 7</span>
        </div>
        <p className="text-overline text-[var(--text-muted)] mb-1">Learning Path</p>
        <h2 className="text-display text-[var(--text-primary)] mb-2">Your Study Plan</h2>
        <p className="text-body text-[var(--text-secondary)]">Personalized GenAI learning path based on your diagnostic profile. You're currently on Module 4.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
        <div className="card p-6 flex items-center gap-4">
          <div className="w-14 h-14 rounded-[var(--r-md)] bg-[var(--c-primary-dim)] flex items-center justify-center text-2xl font-bold text-[var(--c-primary)]">
            {completedCount}/{totalModules}
          </div>
          <div>
            <p className="text-caption text-[var(--text-muted)]">Modules Completed</p>
            <p className="text-lg font-semibold text-[var(--text-primary)]">{completedCount} of {totalModules} done</p>
          </div>
        </div>
        <div className="card p-6 flex items-center gap-4">
          <div className="w-14 h-14 rounded-[var(--r-md)] bg-[var(--c-secondary-dim)] flex items-center justify-center text-2xl font-bold text-[var(--c-secondary)]">
            {overallProgress}%
          </div>
          <div>
            <p className="text-caption text-[var(--text-muted)]">Overall Plan Progress</p>
            <p className="text-lg font-semibold text-[var(--text-primary)]">On track</p>
          </div>
        </div>
        <div className="card p-6 flex items-center gap-4">
          <div className="w-14 h-14 rounded-[var(--r-md)] bg-[var(--c-success-dim)] flex items-center justify-center text-2xl font-bold text-[var(--c-success)]">
            11
          </div>
          <div>
            <p className="text-caption text-[var(--text-muted)]">Estimated Weeks</p>
            <p className="text-lg font-semibold text-[var(--text-primary)]">~3 months at 8 hrs/week</p>
          </div>
        </div>
      </div>

      <div className="card p-6 mb-8 animate-fade-in-up">
        <h3 className="text-title text-[var(--text-primary)] mb-4">Skill Dependency Graph</h3>
        <div className="flex flex-wrap gap-3">
          {modules.map((m, i) => (
            <React.Fragment key={m.id}>
              <div
                className="px-4 py-2.5 rounded-[var(--r-md)] text-xs font-medium border transition-all duration-300 hover:scale-105"
                style={{
                  background: `${statusColors[m.status]}15`,
                  borderColor: `${statusColors[m.status]}30`,
                  color: statusColors[m.status],
                }}
              >
                {m.title}
              </div>
              {i < modules.length - 1 && m.prerequisites.length === 0 && (
                <span className="text-[var(--text-muted)] self-center">→</span>
              )}
              {m.prerequisites.length > 0 && i < modules.length - 1 && (
                <span className="text-[var(--text-muted)] self-center">↳</span>
              )}
            </React.Fragment>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-4 text-xs text-[var(--text-muted)]">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--mastery-mastered)]"/> Mastered</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--mastery-proficient)]"/> Proficient</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--mastery-developing)]"/> Developing</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[var(--mastery-exposure)]"/> Exposure</span>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-title text-[var(--text-primary)] mb-2">Learning Modules</h3>
        {modules.map((module, i) => (
          <ModuleCard
            key={module.id}
            module={module}
            index={i}
            isExpanded={expandedId === module.id}
            onToggle={() => setExpandedId(expandedId === module.id ? null : module.id)}
          />
        ))}
      </div>

      <div className="mt-8 card p-6 border border-[var(--c-accent)]/10 animate-fade-in-up">
        <h3 className="text-title text-[var(--text-primary)] mb-2">Adjust Your Goal</h3>
        <p className="text-sm text-[var(--text-muted)] mb-4">Change your target deadline or weekly study hours to update the plan.</p>
        <div className="flex flex-wrap gap-3">
          <button className="btn-secondary text-xs">
            Exam Cram (4 weeks)
          </button>
          <button className="btn-primary text-xs">
            Deep Mastery (12 weeks)
          </button>
          <button className="btn-secondary text-xs">
            Custom Schedule
          </button>
        </div>
      </div>
    </div>
  );
}
