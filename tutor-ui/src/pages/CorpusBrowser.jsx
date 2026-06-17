import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import SourceResultList from '../components/SourceResultList';
import { ErrorState, Spinner } from '../components/PageStates';
import { useApi } from '../api/useApi';
import { useToast } from '../context/ToastContext';

const TYPE_LABEL = { topic: 'Topics', course: 'Courses', instructor: 'Instructors', coverage: 'Coverage', research_index: 'Index' };

export default function CorpusBrowser() {
  const api = useApi();
  const { addToast } = useToast();
  const [q, setQ] = useState('');

  const healthQ = useQuery({ queryKey: ['health-corpus'], queryFn: () => api.getHealth(), retry: 0 });
  const byType = healthQ.data?.corpus?.by_type || {};
  const total = healthQ.data?.corpus?.document_count;

  const search = useMutation({
    mutationFn: (query) => api.searchSources(query, 12),
    onError: (e) => addToast(e.message || 'Search failed', 'error'),
  });

  const submit = (query) => {
    const value = (query ?? q).trim();
    if (!value) return;
    setQ(value);
    search.mutate(value);
  };

  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      <div className="mb-6">
        <p className="text-overline text-[var(--text-muted)] mb-1">Catalog</p>
        <h2 className="text-display text-[var(--text-primary)]">Course Catalog</h2>
        <p className="text-body text-[var(--text-secondary)]">
          Search the GenAI research corpus{total ? ` — ${total} source records` : ''}. Every result links to its real citation.
        </p>
      </div>

      <div className="flex flex-wrap gap-3 mb-6">
        {Object.entries(byType).map(([type, count]) => (
          <div key={type} className="card px-4 py-3 flex items-center gap-3">
            <span className="text-lg font-bold text-[var(--c-primary)]">{count}</span>
            <span className="text-xs text-[var(--text-muted)] uppercase tracking-wide">{TYPE_LABEL[type] || type}</span>
          </div>
        ))}
      </div>

      <div className="card p-5 mb-6 flex gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder="Search topics, courses, instructors… e.g. retrieval augmented generation"
          className="input flex-1"
        />
        <button onClick={() => submit()} disabled={search.isPending || !q.trim()} className="btn-primary px-5">
          {search.isPending ? <Spinner /> : 'Search'}
        </button>
      </div>

      {search.isError && <ErrorState error={search.error} onRetry={() => submit()} />}

      {search.data && (
        <div className="animate-fade-in">
          <p className="text-caption text-[var(--text-muted)] mb-3">
            {search.data.results?.length || 0} results for “{search.data.query}”
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
          <p className="text-sm">Search the corpus to see source-backed courses, topics, and instructors.</p>
        </div>
      )}
    </div>
  );
}
