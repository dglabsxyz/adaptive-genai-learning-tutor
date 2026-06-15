import React from 'react';

const statusConfig = {
  exposure:    { color: '#ef4444', label: 'Exposure',     bg: 'var(--mastery-exposure-bg)' },
  developing:  { color: '#f59e0b', label: 'Developing',   bg: 'var(--mastery-developing-bg)' },
  proficient:  { color: '#10b981', label: 'Proficient',   bg: 'var(--mastery-proficient-bg)' },
  mastered:    { color: '#F15B2A', label: 'Mastered',     bg: 'var(--mastery-mastered-bg)' },
  review:      { color: '#EC008C', label: 'Review Due',   bg: 'var(--mastery-review-bg)' },
};

export default function SkillMasteryBar({
  name,
  proficiency = 0,
  status = 'exposure',
  attempts = 0,
  streak = 0,
  onClick,
}) {
  const config = statusConfig[status] || statusConfig.exposure;
  const pct = Math.round(proficiency * 100);

  return (
    <div
      onClick={onClick}
      className={`group relative rounded-[var(--r-lg)] p-4 transition-all duration-300 cursor-pointer
        ${onClick ? 'hover:scale-[1.02] active:scale-[0.98]' : ''}`}
      style={{ background: config.bg, border: `1px solid ${config.color}22` }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full status-dot"
            style={{ background: config.color, boxShadow: `0 0 8px ${config.color}88` }}
          />
          <span className="font-medium text-sm text-[var(--text-secondary)]">{name}</span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className="text-xs font-semibold px-2 py-0.5 rounded-full"
            style={{ color: config.color, background: `${config.color}18` }}
          >
            {config.label}
          </span>
          {streak > 0 && (
            <span className="text-xs text-[var(--text-muted)]">🔥 {streak}</span>
          )}
        </div>
      </div>

      <div className="relative h-2.5 rounded-full bg-[var(--border-subtle)] overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-1000 ease-out"
          style={{
            width: `${pct}%`,
            background: config.color,
            boxShadow: `0 0 12px ${config.color}66`,
          }}
        />
      </div>

      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-[var(--text-muted)]">{attempts} attempts</span>
        <span className="text-xs font-mono text-[var(--text-secondary)]">{pct}%</span>
      </div>
    </div>
  );
}
