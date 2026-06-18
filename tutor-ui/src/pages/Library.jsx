import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import SourceResultList from '../components/SourceResultList';
import { ErrorState, LoadingState, Spinner } from '../components/PageStates';
import { useApi } from '../api/useApi';
import { useToast } from '../context/ToastContext';

// Unified corpus browser: topic chips (quick browse) + free-text search, both backed
// by /sources/search. Replaces the old separate Course Catalog + Resources pages.
const TOPICS = [
  { name: 'LLMs', icon: '🧠' },
  { name: 'prompt engineering', icon: '✍️' },
  { name: 'context engineering', icon: '🧱' },
  { name: 'RAG', icon: '🔎' },
  { name: 'AI agents', icon: '🤖' },
  { name: 'MCP', icon: '🔌' },
  { name: 'AI coding', icon: '💻' },
  { name: 'AI safety and evaluation', icon: '🛡️' },
  { name: 'fine-tuning', icon: '🎚️' },
  { name: 'multimodal AI', icon: '🖼️' },
];

const TYPE_LABEL = { topic: 'Topics', course: 'Courses', instructor: 'Instructors', coverage: 'Coverage', research_index: 'Index' };

export default function Library() {
  const api = useApi();
  const { addToast } = useToast();
  const [q, setQ] = useState('');
  const [active, setActive] = useState(null);

  const healthQ = useQuery({ queryKey: ['health-library'], queryFn: () => api.getHealth(), retry: 0 });
  const byType = healthQ.data?.corpus?.by_type || {};
  const total = healthQ.data?.corpus?.document_count;

  const search = useMutation({
    mutationFn: (query) => api.searchSources(query, 12),
    onError: (e) => addToast(e.message || 'Search failed', 'error'),
  });

  const run = (query) => {
    const value = (query ?? q).trim();
    if (!value) return;
    setActive(value);
    search.mutate(value);
  };

  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      <div className="mb-6">
        <p className="text-overline text-[var(--text-muted)] mb-1">Library</p>
        <h2 className="text-display text-[var(--text-primary)]">Course Library</h2>
        <p className="text-body text-[var(--text-secondary)]">
          Browse or search the GenAI research corpus{total ? ` — ${total} source records` : ''}. Every result links to
          its real citation — the same sources the tutor teaches from.
        </p>
      </div>

      {/* Corpus stats */}
      <div className="flex flex-wrap gap-3 mb-6">
        {Object.entries(byType).map(([type, count]) => (
          <div key={type} className="card px-4 py-3 flex items-center gap-3">
            <span className="text-lg font-bold text-[var(--c-primary)]">{count}</span>
            <span className="text-xs text-[var(--text-muted)] uppercase tracking-wide">{TYPE_LABEL[type] || type}</span>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="card p-5 mb-5 flex gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && run()}
          placeholder="Search topics, courses, instructors… e.g. retrieval augmented generation"
          className="input flex-1"
        />
        <button onClick={() => run()} disabled={search.isPending || !q.trim()} className="btn-primary px-5">
          {search.isPending ? <Spinner /> : 'Search'}
        </button>
      </div>

      {/* Topic quick-browse */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-8">
        {TOPICS.map((t) => (
          <button
            key={t.name}
            onClick={() => {
              setQ(t.name);
              run(t.name);
            }}
            className={`card p-4 text-center transition-all ${active === t.name ? 'border-[var(--c-primary)]' : ''}`}
          >
            <div className="text-2xl mb-1">{t.icon}</div>
            <div className="text-xs font-medium text-[var(--text-secondary)] capitalize">{t.name}</div>
          </button>
        ))}
      </div>

      {/* Results */}
      {search.isPending && <LoadingState label={`Searching “${active}”…`} />}
      {search.isError && <ErrorState error={search.error} onRetry={() => run(active)} />}
      {search.data && !search.isPending && (
        <div className="animate-fade-in">
          <p className="text-caption text-[var(--text-muted)] mb-3">
            {search.data.results?.length || 0} results for “{search.data.query || active}”
          </p>
          {search.data.results?.length ? (
            <SourceResultList results={search.data.results} />
          ) : (
            <div className="card p-8 text-center text-[var(--text-muted)] text-sm">No matches in the corpus for that query.</div>
          )}
        </div>
      )}

      {!search.data && !search.isPending && (
        <div className="card p-10 text-center text-[var(--text-muted)]">
          <div className="text-3xl mb-2">📚</div>
          <p className="text-sm">Pick a topic above or search to see source-backed courses, topics, and instructors.</p>
        </div>
      )}
    </div>
  );
}
