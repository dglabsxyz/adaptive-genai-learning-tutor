import React from 'react';

const helpSections = [
  {
    title: 'What is Adaptive Tutor?',
    body: 'An AI-powered GenAI learning companion that diagnoses your skills, builds a personalized study path, and adapts exercises in real time — all grounded in a curated research corpus.',
  },
  {
    title: '1. Diagnostic Interview',
    body: 'An 8-question adaptive interview figures out what you already know. The tutor asks follow-up questions based on your answers. It evaluates proficiency across LLMs, RAG, Agents, MCP, Fine-Tuning, Multimodal AI, and Safety/Evaluation.',
  },
  {
    title: '2. Study Plan',
    body: 'Your personalized roadmap with 7 sequenced modules. Each module lists prerequisites, recommended courses, and estimated time. You are currently on the module shown in your Dashboard.',
  },
  {
    title: '3. Practice Exercises',
    body: 'Exercises adapt to your current level. The tutor grades open-ended answers with rubrics, detects misconceptions, and adjusts difficulty. You can reveal hints or the full solution before submitting.',
  },
  {
    title: '4. Progress Tracking',
    body: 'Visualize your skill radar, weekly activity charts, and spaced-repetition schedule. The tutor reminds you when review sessions are due to keep your skills sharp.',
  },
  {
    title: 'Key Concepts',
    body: 'Proficiency: 0–1 score per skill.\nMastery states: Exposure → Developing → Proficient → Mastered → Review.\nSpaced Repetition: Reviews triggered at optimal intervals to maximize retention.\nSource Refs: Every recommendation and exercise is grounded in the genai_research corpus.',
  },
];

export default function HelpBlade({ isOpen, onToggle }) {
  return (
    <>
      {/* Toggle tab */}
      <button
        onClick={onToggle}
        className={`fixed right-0 top-1/2 -translate-y-1/2 z-40 flex items-center gap-1 px-2 py-3 rounded-l-[var(--r-md)] text-xs font-bold uppercase tracking-wider transition-all duration-300
          ${isOpen ? 'bg-[var(--bg-card)] text-[var(--text-muted)] border border-r-0 border-[var(--border)]' : 'bg-[var(--c-primary)] text-white shadow-[var(--shadow-glow)] hover:brightness-110'}`}
        style={{ writingMode: isOpen ? 'horizontal-tb' : 'vertical-rl' }}
        title={isOpen ? 'Close help' : 'Open help'}
      >
        {isOpen ? '✕ Close' : '❔ Help'}
      </button>

      {/* Slide-in panel */}
      <div
        className={`fixed top-0 right-0 h-full z-30 transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
        style={{ width: '320px' }}
      >
        <div className="h-full glass-sidebar border-l border-[var(--border)] flex flex-col">
          <div className="p-5 border-b border-[var(--border)]">
            <h3 className="text-lg font-bold text-[var(--text-primary)]">Quick Reference</h3>
            <p className="text-xs text-[var(--text-muted)] mt-1">How to use Adaptive Tutor</p>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {helpSections.map((section, i) => (
              <details key={i} className="group">
                <summary className="flex items-center justify-between cursor-pointer p-3 rounded-[var(--r-md)] bg-[var(--bg-surface)] border border-[var(--border)] hover:border-[var(--c-primary)]/30 transition-colors text-sm font-medium text-[var(--text-primary)]">
                  {section.title}
                  <span className="text-[var(--text-muted)] group-open:rotate-180 transition-transform duration-200">▼</span>
                </summary>
                <div className="p-3 text-xs text-[var(--text-secondary)] leading-relaxed whitespace-pre-line">
                  {section.body}
                </div>
              </details>
            ))}
          </div>

          <div className="p-4 border-t border-[var(--border)]">
            <p className="text-[10px] text-[var(--text-muted)] text-center">
              Need more help? Check the Course Catalog for curriculum details.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
