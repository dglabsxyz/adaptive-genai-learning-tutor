import React from 'react';

const config = {
  exposure:   { color: '#ef4444', bg: 'var(--mastery-exposure-bg)', icon: '○' },
  developing: { color: '#f59e0b', bg: 'var(--mastery-developing-bg)', icon: '◐' },
  proficient: { color: '#10b981', bg: 'var(--mastery-proficient-bg)', icon: '◑' },
  mastered:   { color: '#F15B2A', bg: 'var(--mastery-mastered-bg)', icon: '●' },
  review:     { color: '#EC008C', bg: 'var(--mastery-review-bg)', icon: '↻' },
};

export default function SkillStateBadge({ status, showIcon = true }) {
  const c = config[status] || config.exposure;
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full"
      style={{ color: c.color, background: c.bg }}
    >
      {showIcon && <span className="text-[10px]">{c.icon}</span>}
      <span className="capitalize">{status}</span>
    </span>
  );
}
