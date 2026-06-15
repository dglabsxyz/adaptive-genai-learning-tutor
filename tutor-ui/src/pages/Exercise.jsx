import React, { useState } from 'react';
import SourceRef from '../components/SourceRef';
import Skeleton from '../components/Skeleton';
import EmptyState from '../components/EmptyState';
import { useToast } from '../context/ToastContext';

const exerciseMock = {
  exercise_id: 'ex-rag-042',
  skill_id: 'rag_architecture',
  topic_slug: 'rag_architecture',
  difficulty: 7,
  question: 'You are building a RAG-based customer support assistant. The current system retrieves top-3 chunks from a single vector store and injects them into the prompt. Users report that answers are sometimes incomplete when a question spans multiple product manuals.\n\n**Design a better retrieval strategy.** Describe:\n1. How you would chunk and index the manuals.\n2. What retrieval approach you would use beyond simple top-k.\n3. How you would evaluate whether the retrieved context actually answers the question.',
  format: 'architecture_scenario',
  options: null,
  rubric: 'Strong answers mention: (a) semantic + hybrid retrieval, (b) multi-document chunking with parent/child or hierarchical indexing, (c) re-ranking or cross-encoder scoring, (d) query decomposition for multi-part questions, (e) an evaluation loop (e.g., LLM-as-judge or answer-grounded metrics).',
  hints: [
    'Think about what happens when a user asks about "return policy and warranty coverage together".',
    'Consider whether all chunks are equally relevant — can you re-rank them?',
    'How do you know if the retrieved context actually contains the answer?',
  ],
  solution: '1. **Chunking**: Use parent-child chunks with overlap, where small semantic chunks are linked to larger parent chunks for context. Index by product and manual section.\n2. **Retrieval**: Hybrid search (BM25 + dense) with query decomposition. For multi-part questions, break into sub-queries, retrieve per sub-query, then re-rank with a cross-encoder.\n3. **Evaluation**: Use LLM-as-judge to score "context sufficiency" before generation, plus answer-relevance metrics post-generation.',
  explanation: 'This tests understanding of advanced RAG patterns beyond naive vector retrieval. Many learners stop at top-k semantic search; the key differentiator is combining hybrid retrieval, query decomposition, and re-ranking.',
  source_refs: [
    { title: 'RAG Architecture (Topic)', record_type: 'topic', path: 'topics/rag_architecture', citation_url: null },
    { title: 'Advanced RAG Patterns (Course)', record_type: 'course', path: 'courses/advanced_rag_patterns', citation_url: 'https://www.deeplearning.ai/short-courses/advanced-retrieval-for-ai/' },
  ],
};

const gradingMock = {
  score: 0.65,
  is_correct: false,
  feedback: 'Good start on chunking, but you missed hybrid retrieval and query decomposition. Your evaluation approach is too vague — "check if it looks right" is not a systematic metric.',
  explanation: 'You correctly identified that multi-document questions are a problem and suggested better chunking. However, the answer lacks specific techniques for handling multi-part queries (query decomposition) and does not mention re-ranking or cross-encoders. The evaluation section is hand-wavy rather than grounded in a specific metric or judge pipeline.',
  skill_state_transition: 'same',
  next_action: 'retry',
  cited_evidence: [
    { title: 'RAG Architecture (Topic)', record_type: 'topic', path: 'topics/rag_architecture', citation_url: null },
  ],
  misconception_tags: ['Confusing top-k with optimal retrieval', 'Vague evaluation criteria'],
};

export default function Exercise() {
  const { addToast } = useToast();
  const [showHints, setShowHints] = useState(false);
  const [showSolution, setShowSolution] = useState(false);
  const [answer, setAnswer] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [grading, setGrading] = useState(null);

  const handleSubmit = () => {
    if (!answer.trim()) {
      addToast('Please write an answer before submitting.', 'warning');
      return;
    }
    setSubmitted(true);
    addToast('Answer submitted! Grading in progress...', 'info');
    setTimeout(() => {
      setGrading(gradingMock);
      addToast('Grading complete. Score: 65% — needs work.', 'warning');
    }, 1500);
  };

  const handleRetry = () => {
    setSubmitted(false);
    setGrading(null);
    setAnswer('');
    addToast('Exercise reset. Try again!', 'info');
  };

  const handleNextExercise = () => {
    addToast('Loading next exercise...', 'info');
  };

  const getDifficultyLabel = (d) => {
    if (d <= 3) return 'Beginner';
    if (d <= 6) return 'Intermediate';
    return 'Advanced';
  };

  const getDifficultyColor = (d) => {
    if (d <= 3) return 'var(--c-success)';
    if (d <= 6) return 'var(--c-accent)';
    return 'var(--c-danger)';
  };

  return (
    <div className="h-full overflow-y-auto p-8 animate-fade-in">
      <div className="mb-6">
        {/* Breadcrumb context */}
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] mb-3">
          <span>Study Plan</span>
          <span>→</span>
          <span>Module 4</span>
          <span>→</span>
          <span className="text-[var(--c-primary)] font-medium">RAG Architecture</span>
          <span>→</span>
          <span className="text-[var(--text-primary)]">Exercise 3 of 6</span>
        </div>
        <div className="flex items-center gap-3 mb-2">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Practice Exercise</h2>
          <span
            className="px-2.5 py-1 rounded-[var(--r-sm)] text-xs font-bold border"
            style={{
              color: getDifficultyColor(exerciseMock.difficulty),
              borderColor: `${getDifficultyColor(exerciseMock.difficulty)}40`,
              background: `${getDifficultyColor(exerciseMock.difficulty)}15`,
            }}
          >
            {getDifficultyLabel(exerciseMock.difficulty)} · Difficulty {exerciseMock.difficulty}/10
          </span>
        </div>
        <p className="text-sm text-[var(--text-muted)]">
          Skill: <span className="text-[var(--c-primary)] font-medium">RAG Architecture</span> · Format: <span className="text-[var(--text-secondary)]">Architecture Scenario</span>
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Question panel — 3 cols */}
        <div className="lg:col-span-3 space-y-5">
          <div className="card p-6">
            <div className="text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-line">
              {exerciseMock.question}
            </div>
            <SourceRef sources={exerciseMock.source_refs} />
          </div>

          <div className="card overflow-hidden">
            <button
              onClick={() => setShowHints(!showHints)}
              className="w-full flex items-center justify-between px-6 py-4 text-sm font-medium text-[var(--c-accent)] hover:bg-[var(--bg-surface-hover)] transition-colors"
            >
              <span className="flex items-center gap-2">💡 Hints ({exerciseMock.hints.length})</span>
              <span className="text-[var(--text-muted)] transition-transform duration-200" style={{ transform: showHints ? 'rotate(180deg)' : '' }}>▼</span>
            </button>
            {showHints && (
              <div className="px-6 pb-5 space-y-3 animate-fade-in">
                {exerciseMock.hints.map((hint, i) => (
                  <div key={i} className="flex gap-3 p-3 rounded-[var(--r-md)] bg-[var(--c-accent-dim)] border border-[var(--c-accent)]/10">
                    <span className="text-[var(--c-accent)] font-bold text-xs mt-0.5">{i + 1}.</span>
                    <p className="text-sm text-[var(--text-muted)]">{hint}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card overflow-hidden">
            <button
              onClick={() => setShowSolution(!showSolution)}
              className="w-full flex items-center justify-between px-6 py-4 text-sm font-medium text-[var(--c-success)] hover:bg-[var(--bg-surface-hover)] transition-colors"
            >
              <span className="flex items-center gap-2">📖 Show Solution</span>
              <span className="text-[var(--text-muted)] transition-transform duration-200" style={{ transform: showSolution ? 'rotate(180deg)' : '' }}>▼</span>
            </button>
            {showSolution && (
              <div className="px-6 pb-5 animate-fade-in">
                <div className="p-4 rounded-[var(--r-md)] bg-[var(--c-success-dim)] border border-[var(--c-success)]/10">
                  <p className="text-sm text-[var(--text-secondary)] whitespace-pre-line leading-relaxed">{exerciseMock.solution}</p>
                </div>
                <p className="mt-3 text-xs text-[var(--text-muted)] italic">{exerciseMock.explanation}</p>
              </div>
            )}
          </div>
        </div>

        {/* Answer panel — 2 cols */}
        <div className="lg:col-span-2 space-y-5">
          <div className="card p-6">
            <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Your Answer</h3>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              disabled={submitted}
              placeholder="Type your design response here..."
              className="input h-64"
            />
            <div className="mt-4 flex items-center justify-between">
              <span className="text-xs text-[var(--text-muted)]">{answer.length} chars</span>
              {!submitted ? (
                <button
                  onClick={handleSubmit}
                  disabled={!answer.trim()}
                  className="btn-primary"
                >
                  Submit Answer
                </button>
              ) : !grading ? (
                <div className="flex items-center gap-3 text-sm text-[var(--text-muted)] py-1">
                  <div className="w-5 h-5 border-2 border-[var(--c-primary)]/30 border-t-[var(--c-primary)] rounded-full animate-spin" />
                  <span>Grading your answer...</span>
                </div>
              ) : null}
            </div>
          </div>

          {grading && (
            <div className={`card border animate-scale-in
              ${grading.is_correct ? 'border-[var(--c-success)]/20' : 'border-[var(--c-accent)]/20'}`}>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">Grading Result</h3>
                  <div className="flex items-center gap-2">
                    <span className={`text-2xl font-bold ${grading.is_correct ? 'text-[var(--c-success)]' : 'text-[var(--c-accent)]'}`}>
                      {Math.round(grading.score * 100)}%
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-semibold
                      ${grading.is_correct ? 'bg-[var(--c-success-dim)] text-[var(--c-success)]' : 'bg-[var(--c-accent-dim)] text-[var(--c-accent)]'}`}>
                      {grading.is_correct ? 'Correct' : 'Needs Work'}
                    </span>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <p className="text-overline text-[var(--text-muted)] mb-1">Feedback</p>
                    <p className="text-sm text-[var(--text-secondary)]">{grading.feedback}</p>
                  </div>
                  <div>
                    <p className="text-overline text-[var(--text-muted)] mb-1">Detailed Explanation</p>
                    <p className="text-sm text-[var(--text-secondary)]">{grading.explanation}</p>
                  </div>

                  {grading.misconception_tags.length > 0 && (
                    <div>
                      <p className="text-overline text-[var(--text-muted)] mb-2">Misconceptions Detected</p>
                      <div className="flex flex-wrap gap-2">
                        {grading.misconception_tags.map((tag, i) => (
                          <span key={i} className="text-xs px-2.5 py-1 rounded-[var(--r-sm)] bg-[var(--c-danger-dim)] text-[var(--c-danger)] border border-[var(--c-danger)]/15">
                            ⚠ {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-[var(--text-muted)]">Next:</span>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full
                      ${grading.next_action === 'retry' ? 'bg-[var(--c-accent-dim)] text-[var(--c-accent)]' : 'bg-[var(--c-primary-dim)] text-[var(--c-primary)]'}`}>
                      {grading.next_action === 'retry' ? '↻ Try Again' : '→ Next Exercise'}
                    </span>
                  </div>

                  <SourceRef sources={grading.cited_evidence} />
                </div>

                <div className="mt-5 flex gap-3">
                  {grading.next_action === 'retry' && (
                    <button
                      onClick={handleRetry}
                      className="flex-1 btn-secondary text-xs"
                    >
                      Retry This Exercise
                    </button>
                  )}
                  <button 
                    onClick={handleNextExercise}
                    className="flex-1 btn-primary text-xs"
                  >
                    Next Exercise →
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
