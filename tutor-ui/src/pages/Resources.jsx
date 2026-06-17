import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import SourceResultList from '../components/SourceResultList';
import { ErrorState, LoadingState } from '../components/PageStates';
import { useApi } from '../api/useApi';
import { useToast } from '../context/ToastContext';

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

export default function Resources() {
  const api = useApi();
  const { addToast } = useToast();
  const [active, setActive] = useState(null);

  const search = useMutation({
    mutationFn: (topic) => api.searchSources(topic, 10),
    onError: (e) => addToast(e.message || 'Could not load resources', 'error'),
  });

  const open = (topic) => {
    setActive(topic);
    search.mutate(topic);
  };

  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      <div className="mb-6">
        <p className="text-overline text-[var(--text-muted)] mb-1">Resources</p>
        <h2 className="text-display text-[var(--text-primary)]">Resources by topic</h2>
        <p className="text-body text-[var(--text-secondary)]">Pick a skill to pull the real, cited course material the tutor teaches from.</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-8">
        {TOPICS.map((t) => (
          <button
            key={t.name}
            onClick={() => open(t.name)}
            className={`card p-4 text-center transition-all ${active === t.name ? 'border-[var(--c-primary)]' : ''}`}
          >
            <div className="text-2xl mb-1">{t.icon}</div>
            <div className="text-xs font-medium text-[var(--text-secondary)] capitalize">{t.name}</div>
          </button>
        ))}
      </div>

      {active && (
        <div className="animate-fade-in">
          <h3 className="text-title text-[var(--text-primary)] mb-4 capitalize">{active}</h3>
          {search.isPending && <LoadingState label={`Loading ${active} resources…`} />}
          {search.isError && <ErrorState error={search.error} onRetry={() => open(active)} />}
          {search.data && (search.data.results?.length ? (
            <SourceResultList results={search.data.results} />
          ) : (
            <div className="card p-8 text-center text-[var(--text-muted)] text-sm">No corpus resources found for {active}.</div>
          ))}
        </div>
      )}

      {!active && (
        <div className="card p-10 text-center text-[var(--text-muted)]">
          <div className="text-3xl mb-2">📁</div>
          <p className="text-sm">Choose a topic above to browse its cited resources.</p>
        </div>
      )}
    </div>
  );
}
