import React from 'react';
import { Link } from 'react-router-dom';

// Small, consistent "what to do next" CTA row to connect the learner journey
// (diagnose → plan → practice → review) and always offer the conversational tutor.
export default function NextStep({ title = 'Next step', items = [] }) {
  const list = (items || []).filter(Boolean);
  if (!list.length) return null;
  return (
    <div className="card p-5 mt-6">
      <p className="text-overline text-[var(--text-muted)] mb-3">{title}</p>
      <div className="flex flex-wrap gap-2">
        {list.map((it) => (
          <Link
            key={`${it.to}-${it.label}`}
            to={it.to}
            className={`${it.primary ? 'btn-primary' : 'btn-secondary'} text-sm`}
          >
            {it.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
