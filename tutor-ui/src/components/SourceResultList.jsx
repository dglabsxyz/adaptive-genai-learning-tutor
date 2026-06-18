import React from 'react';

const TYPE_ICON = { course: '🎓', topic: '🧩', instructor: '👤', coverage: '🗂️', research_index: '🔎' };

function hostname(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

export default function SourceResultList({ results = [] }) {
  if (!results.length) return null;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {results.map((r, i) => (
        <div key={i} className="card p-5">
          <div className="flex items-center gap-2 mb-2">
            <span>{TYPE_ICON[r.record_type] || '📄'}</span>
            <span className="tag text-[11px] capitalize">{r.record_type}</span>
            {typeof r.score === 'number' && (
              <span className="ml-auto text-xs text-[var(--text-muted)] font-mono">{Math.round(r.score * 100)}%</span>
            )}
          </div>
          <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-1">{r.title}</h4>
          {r.summary && <p className="text-xs text-[var(--text-muted)] mb-3 line-clamp-3">{r.summary}</p>}
          {Array.isArray(r.citations) && r.citations.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {r.citations.slice(0, 3).map((u, j) => (
                <a
                  key={j}
                  href={u}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] text-[var(--c-primary)] hover:underline truncate max-w-[220px]"
                >
                  ↗ {hostname(u)}
                </a>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
