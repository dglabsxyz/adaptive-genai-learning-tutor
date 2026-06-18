import React from 'react';

export default function SourceRef({ sources = [] }) {
  if (!sources.length) return null;
  return (
    <div className="flex flex-wrap gap-2 mt-4">
      {sources.map((src, i) => (
        <a
          key={i}
          href={src.citation_url || '#'}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-[var(--r-sm)]
                     bg-[var(--bg-surface)] text-[var(--text-muted)] hover:text-[var(--c-primary)] hover:bg-[var(--bg-surface-hover)]
                     transition-all border border-[var(--border)] hover:border-[var(--c-primary)]/20"
          title={`${src.record_type}: ${src.path}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--c-success)]" />
          <span className="truncate max-w-[200px]">{src.title}</span>
          {src.citation_url && <span className="text-[var(--text-muted)] opacity-60">↗</span>}
        </a>
      ))}
    </div>
  );
}
