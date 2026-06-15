import React, { useState } from 'react';
import SourceRef from '../components/SourceRef';
import EmptyState from '../components/EmptyState';

const mockResults = [
  {
    title: 'RAG from Scratch',
    type: 'course',
    platform: 'DeepLearning.AI',
    instructor: 'Andrew Ng',
    topics: ['RAG', 'Vector Search', 'Embeddings'],
    description: 'Build retrieval-augmented generation systems from the ground up. Covers chunking, embedding models, vector databases, and hybrid search.',
    slug: 'courses/rag_from_scratch',
    citations: ['https://www.deeplearning.ai/short-courses/rag-from-scratch/'],
  },
  {
    title: 'MCP Protocol Deep Dive',
    type: 'course',
    platform: 'Anthropic',
    instructor: 'Anthropic Team',
    topics: ['MCP', 'Tool Integration', 'Agent Protocols'],
    description: 'Comprehensive guide to the Model Context Protocol: tool definitions, server implementation, and client integration patterns.',
    slug: 'courses/mcp_protocol_deep_dive',
    citations: ['https://modelcontextprotocol.io/'],
  },
  {
    title: 'LLM Fundamentals',
    type: 'topic',
    platform: null,
    instructor: null,
    topics: ['LLMs', 'Transformers', 'Tokenization'],
    description: 'Core concepts in large language models: transformer architecture, attention mechanisms, pre-training, and inference optimization.',
    slug: 'topics/llm_fundamentals',
    citations: [],
  },
  {
    title: 'Advanced RAG Patterns',
    type: 'course',
    platform: 'Weaviate',
    instructor: 'Connor Shorten',
    topics: ['RAG', 'Re-ranking', 'Query Decomposition'],
    description: 'Beyond naive vector retrieval: multi-hop reasoning, self-correcting retrieval, and evaluation frameworks for production RAG.',
    slug: 'courses/advanced_rag_patterns',
    citations: ['https://www.deeplearning.ai/short-courses/advanced-retrieval-for-ai/'],
  },
];

const topicFilters = ['All', 'LLMs', 'RAG', 'Agents', 'MCP', 'Prompt Engineering', 'Fine-Tuning', 'Multimodal', 'Safety'];

export default function CorpusBrowser() {
  const [query, setQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('All');
  const [results, setResults] = useState(mockResults);

  const handleSearch = () => {
    const filtered = mockResults.filter(r => {
      const matchesQuery = !query || r.title.toLowerCase().includes(query.toLowerCase()) || r.description.toLowerCase().includes(query.toLowerCase());
      const matchesTopic = activeFilter === 'All' || r.topics.includes(activeFilter);
      return matchesQuery && matchesTopic;
    });
    setResults(filtered);
  };

  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      <div className="mb-8">
        <p className="text-overline text-[var(--text-muted)] mb-1">Catalog</p>
        <h2 className="text-display text-[var(--text-primary)] mb-2">Course Catalog</h2>
        <p className="text-body text-[var(--text-secondary)]">Browse and search the genai_research corpus. All recommendations are grounded in these sources.</p>
      </div>

      <div className="card p-4 mb-6 flex items-center gap-3">
        <span className="text-[var(--text-muted)] text-lg">🔍</span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Search courses, topics, or instructors..."
          className="input flex-1 border-transparent focus:border-[var(--c-primary)]"
        />
        <button
          onClick={handleSearch}
          className="btn-primary"
        >
          Search
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        {topicFilters.map(filter => (
          <button
            key={filter}
            onClick={() => { setActiveFilter(filter); }}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-200
              ${activeFilter === filter
                ? 'bg-[var(--c-primary-dim)] text-[var(--c-primary)] border border-[var(--c-primary)]/30'
                : 'bg-[var(--bg-surface)] text-[var(--text-muted)] border border-[var(--border)] hover:bg-[var(--bg-surface-hover)] hover:text-[var(--text-secondary)]'
              }`}
          >
            {filter}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {results.length === 0 ? (
          <EmptyState
            icon="🔍"
            title="No results found"
            description="Try adjusting your search query or filters to find what you're looking for."
          />
        ) : (
          results.map((result, i) => (
            <div key={i} className="card p-6 hover:border-[var(--border-hover)] transition-all duration-200 animate-fade-in-up" style={{ animationDelay: `${i * 0.05}s` }}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-[var(--r-xs)] uppercase tracking-wider
                      ${result.type === 'course' ? 'bg-[var(--c-secondary-dim)] text-[var(--c-secondary)]' : 'bg-[var(--c-primary-dim)] text-[var(--c-primary)]'}`}>
                      {result.type}
                    </span>
                    {result.platform && (
                      <span className="text-xs text-[var(--text-muted)]">{result.platform}</span>
                    )}
                  </div>
                  <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-1">{result.title}</h3>
                  <p className="text-sm text-[var(--text-secondary)] leading-relaxed mb-3">{result.description}</p>

                  <div className="flex flex-wrap gap-2 mb-3">
                    {result.topics.map((topic, j) => (
                      <span key={j} className="text-xs px-2 py-1 rounded-[var(--r-sm)] bg-[var(--bg-surface)] text-[var(--text-secondary)] border border-[var(--border)]">
                        {topic}
                      </span>
                    ))}
                  </div>

                  {result.instructor && (
                    <p className="text-xs text-[var(--text-muted)] mb-2">Instructor: {result.instructor}</p>
                  )}

                  <SourceRef sources={result.citations.map((url, idx) => ({
                    title: url,
                    record_type: 'source',
                    path: result.slug,
                    citation_url: url,
                  }))} />
                </div>
                <button className="ml-4 px-4 py-2 rounded-[var(--r-md)] bg-[var(--bg-surface)] text-[var(--text-secondary)] text-xs font-medium hover:bg-[var(--bg-surface-hover)] transition-colors border border-[var(--border)] flex-shrink-0">
                  View Details →
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-8 card p-6">
        <p className="text-overline text-[var(--text-muted)] mb-3">Corpus Snapshot</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-[var(--text-primary)]">67</p>
            <p className="text-xs text-[var(--text-muted)]">Courses</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-[var(--text-primary)]">17</p>
            <p className="text-xs text-[var(--text-muted)]">Topics</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-[var(--text-primary)]">72</p>
            <p className="text-xs text-[var(--text-muted)]">Instructors</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-[var(--text-primary)]">81</p>
            <p className="text-xs text-[var(--text-muted)]">Sources</p>
          </div>
        </div>
        <p className="text-xs text-[var(--text-muted)] mt-4 text-center opacity-60">Last updated: 2024-06-15 · genai_research/coverage_report.json</p>
      </div>
    </div>
  );
}
