import React, { useState, useEffect } from 'react';
import { useToast } from '../context/ToastContext';

const steps = [
  {
    title: 'Welcome to Adaptive Tutor',
    subtitle: 'Your AI-powered GenAI learning companion',
    body: 'This tutor diagnoses your skills, builds a personalized study path, and adapts exercises in real time — all grounded in a curated research corpus.',
    icon: '🎓',
  },
  {
    title: '1. Take the Diagnostic',
    subtitle: '8-question adaptive interview',
    body: 'The tutor asks targeted questions to figure out what you already know about LLMs, RAG, Agents, MCP, and more. It adapts based on your answers.',
    icon: '🔬',
  },
  {
    title: '2. Get Your Study Plan',
    subtitle: 'Personalized learning roadmap',
    body: 'Based on your diagnostic results, the tutor builds a sequenced plan with modules, prerequisites, and estimated completion times.',
    icon: '🗺️',
  },
  {
    title: '3. Practice & Adapt',
    subtitle: 'Dynamic exercises calibrated to your level',
    body: 'Exercises get harder as you improve. The tutor grades your answers, detects misconceptions, and adjusts difficulty automatically.',
    icon: '✏️',
  },
  {
    title: '4. Track Progress',
    subtitle: 'Skill mastery radar + spaced review',
    body: 'Visualize your skill radar, see weekly activity, and get reminded when spaced-repetition reviews are due.',
    icon: '📈',
  },
];

export default function WelcomeModal({ onComplete, onSkip }) {
  const [step, setStep] = useState(0);
  const { addToast } = useToast();

  const current = steps[step];
  const isFirst = step === 0;
  const isLast = step === steps.length - 1;

  const handleNext = () => {
    if (isLast) {
      localStorage.setItem('tutor-welcomed', 'true');
      onComplete?.();
      addToast('Welcome aboard! Start with the Diagnostic.', 'success');
    } else {
      setStep(s => s + 1);
    }
  };

  const handleBack = () => setStep(s => Math.max(0, s - 1));

  const handleSkip = () => {
    localStorage.setItem('tutor-welcomed', 'true');
    onSkip?.();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center" style={{ background: 'var(--overlay)' }}>
      <div className="card-elevated w-full max-w-lg mx-4 p-8 animate-scale-in relative">
        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {steps.map((_, i) => (
            <div
              key={i}
              className="h-1.5 rounded-full transition-all duration-300"
              style={{
                width: i === step ? '32px' : '8px',
                background: i <= step ? 'var(--c-primary)' : 'var(--border)',
              }}
            />
          ))}
        </div>

        {/* Skip button */}
        <button
          onClick={handleSkip}
          className="absolute top-4 right-4 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
        >
          Skip tour
        </button>

        {/* Content */}
        <div className="text-center mb-6">
          <div className="w-16 h-16 rounded-full gradient-primary flex items-center justify-center text-3xl mx-auto mb-4 shadow-[var(--shadow-glow)]">
            {current.icon}
          </div>
          <h2 className="text-headline text-[var(--text-primary)] mb-1">{current.title}</h2>
          <p className="text-sm text-[var(--c-primary)] font-medium mb-3">{current.subtitle}</p>
          <p className="text-body text-[var(--text-secondary)] max-w-sm mx-auto">{current.body}</p>
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between">
          <button
            onClick={handleBack}
            disabled={isFirst}
            className="btn-secondary text-xs px-4 py-2 disabled:opacity-30"
          >
            Back
          </button>
          <div className="text-xs text-[var(--text-muted)]">
            {step + 1} / {steps.length}
          </div>
          <button
            onClick={handleNext}
            className="btn-primary text-xs px-5 py-2"
          >
            {isLast ? 'Get Started →' : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  );
}
