import React from 'react';

/**
 * Empty state component — theme-aware with icon, message, and optional CTA.
 */
export default function EmptyState({ icon = '📭', title = 'Nothing here yet', description = 'Get started by creating your first item.', actionLabel, onAction }) {
  return (
    <div className="card p-12 text-center flex flex-col items-center">
      <div className="w-16 h-16 rounded-full bg-[var(--bg-surface)] flex items-center justify-center text-3xl mb-4">
        {icon}
      </div>
      <h3 className="text-title text-[var(--text-primary)] mb-1">{title}</h3>
      <p className="text-body text-[var(--text-muted)] max-w-sm mb-5">{description}</p>
      {actionLabel && onAction && (
        <button onClick={onAction} className="btn-primary">
          {actionLabel}
        </button>
      )}
    </div>
  );
}
