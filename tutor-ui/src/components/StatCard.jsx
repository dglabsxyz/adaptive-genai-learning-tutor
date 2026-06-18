import React from 'react';

/**
 * StatCard — Commercial-grade KPI card with icon, value, label, and trend.
 * Props: icon (string), value (string), label (string), trend (number), color (string)
 */
export default function StatCard({ icon, value, label, trend, color = '#EC008C' }) {
  const isPositive = trend >= 0;
  const trendColor = isPositive ? 'var(--c-success)' : 'var(--c-danger)';
  const trendBg = isPositive ? 'var(--c-success-dim)' : 'var(--c-danger-dim)';

  return (
    <div className="card p-5 flex items-center gap-4">
      <div
        className="w-12 h-12 rounded-[var(--r-md)] flex items-center justify-center text-xl flex-shrink-0"
        style={{ background: `${color}15`, color: color }}
      >
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-xl font-bold text-[var(--text-primary)]">{value}</p>
          {trend !== undefined && (
            <span
              className="text-[11px] font-semibold px-1.5 py-0.5 rounded-[var(--r-xs)]"
              style={{ color: trendColor, background: trendBg }}
            >
              {isPositive ? '+' : ''}{trend}%
            </span>
          )}
        </div>
        <p className="text-caption text-[var(--text-muted)] mt-0.5">{label}</p>
      </div>
    </div>
  );
}
