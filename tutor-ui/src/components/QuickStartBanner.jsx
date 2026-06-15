import React from 'react';

/**
 * QuickStartBanner — Shows the user's current state and the single next step to take.
 * Makes the mock data feel like a real, coherent journey.
 */
export default function QuickStartBanner({ stage, onAction }) {
  const stages = {
    'new': {
      title: '👋 Welcome! Let\'s get started',
      subtitle: 'Take a quick 8-question diagnostic to personalize your learning path.',
      cta: 'Start Diagnostic →',
      ctaColor: 'var(--c-primary)',
    },
    'diagnosed': {
      title: '📊 Your diagnostic is complete',
      subtitle: 'We found your strengths and gaps. View your personalized study plan next.',
      cta: 'View Study Plan →',
      ctaColor: 'var(--c-secondary)',
    },
    'has-plan': {
      title: '🗺️ You\'re on Module 4: RAG Architecture',
      subtitle: 'Continue your study plan or jump into a practice exercise for this module.',
      cta: 'Practice RAG Exercise →',
      ctaColor: 'var(--c-accent)',
    },
    'practicing': {
      title: '✏️ Exercise in progress',
      subtitle: 'You started an architecture-scenario exercise on RAG. Pick up where you left off.',
      cta: 'Continue Exercise →',
      ctaColor: 'var(--c-success)',
    },
    'review-due': {
      title: '↻ Spaced review ready',
      subtitle: 'LLM Fundamentals and Fine-Tuning reviews are due. Keep your skills sharp.',
      cta: 'Start Review Session →',
      ctaColor: 'var(--c-primary)',
    },
  };

  const config = stages[stage] || stages['new'];

  return (
    <div className="card p-6 mb-6 border-l-4 animate-fade-in-up" style={{ borderLeftColor: config.ctaColor }}>
      <div className="flex items-start gap-4">
        <div className="flex-1">
          <h3 className="text-title text-[var(--text-primary)] mb-1">{config.title}</h3>
          <p className="text-body text-[var(--text-secondary)]">{config.subtitle}</p>
        </div>
        <button
          onClick={onAction}
          className="btn-primary flex-shrink-0"
          style={{ 
            background: config.ctaColor,
            boxShadow: `0 0 20px ${config.ctaColor}33`,
          }}
        >
          {config.cta}
        </button>
      </div>
    </div>
  );
}
