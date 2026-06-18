import React from 'react';

export function LoadingState({ label = 'Loading…' }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-[var(--text-muted)] animate-fade-in">
      <div className="w-10 h-10 rounded-full border-2 border-[var(--border)] border-t-[var(--c-primary)] animate-spin mb-4" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  const status = error?.status;
  const isForbidden = status === 403;
  const isNotFound = status === 404;
  const title = isForbidden
    ? 'Not available for this role'
    : isNotFound
    ? 'Nothing here yet'
    : 'Could not load this view';
  const hint = isForbidden
    ? 'Switch to an educator or admin role in the top bar to access this page.'
    : error?.message || 'Something went wrong reaching the backend.';

  return (
    <div className="card p-8 max-w-xl mx-auto mt-10 text-center animate-fade-in" style={{ borderColor: 'var(--c-danger)' }}>
      <div className="text-3xl mb-3">{isForbidden ? '🔒' : isNotFound ? '🗂️' : '⚠️'}</div>
      <h3 className="text-title text-[var(--text-primary)] mb-2">{title}</h3>
      <p className="text-sm text-[var(--text-secondary)] mb-1">{hint}</p>
      {error?.code && <p className="text-xs text-[var(--text-muted)] mb-4">code: {error.code}{error.requestId ? ` · ${error.requestId}` : ''}</p>}
      {onRetry && !isForbidden && (
        <button onClick={onRetry} className="btn-secondary mt-2">
          Try again
        </button>
      )}
    </div>
  );
}

// Small inline spinner for buttons / inline async.
export function Spinner({ className = '' }) {
  return (
    <span
      className={`inline-block w-4 h-4 rounded-full border-2 border-[var(--text-inverse)]/40 border-t-[var(--text-inverse)] animate-spin ${className}`}
    />
  );
}
