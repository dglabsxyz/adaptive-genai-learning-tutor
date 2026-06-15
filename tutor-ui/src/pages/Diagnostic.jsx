import React, { useState, useRef, useEffect } from 'react';
import SkillStateBadge from '../components/SkillStateBadge';
import SourceRef from '../components/SourceRef';

const diagnosticFlow = [
  {
    id: 'q1',
    type: 'tutor',
    text: 'Hi! I\'m your Adaptive GenAI Tutor. Before we begin, I\'d like to quickly assess what you already know so I can personalize your learning path. Ready?',
    options: null,
  },
  {
    id: 'q2',
    type: 'tutor',
    text: '**Question 1 of 8** — In a GenAI application, when would you use RAG instead of fine-tuning for a customer-support assistant?',
    options: [
      'RAG is cheaper; fine-tuning is always overkill.',
      'RAG for dynamic knowledge retrieval; fine-tuning for behavior/style alignment.',
      'They are interchangeable — use whichever is faster to implement.',
      'Fine-tuning is deprecated; RAG is the modern standard.',
    ],
  },
  {
    id: 'interrupt',
    type: 'interrupt',
    text: 'Hmm, your answer is a bit ambiguous. Let me clarify: are you familiar with **embeddings and vector retrieval**, or should we start with LLM application basics first?',
    options: ['Yes, I know embeddings', 'Not really — let\'s start with basics'],
  },
  {
    id: 'q3',
    type: 'tutor',
    text: '**Question 3 of 8** — How would you expose a RAG-based course-search assistant\'s capability through MCP?',
    options: [
      'Wrap the retriever as an MCP tool the LLM can call.',
      'MCP is only for client-side IDE integrations, not for retrieval.',
      'Use MCP to stream the vector DB directly to the user.',
      'MCP replaces RAG entirely — no need for both.',
    ],
  },
  {
    id: 'q4',
    type: 'tutor',
    text: '**Question 5 of 8** — Design a multi-agent orchestration flow where one agent grades answers and another adapts difficulty. What inter-agent communication pattern would you use?',
    options: [
      'Direct LLM-to-LLM messages with no schema.',
      'Structured state updates via a shared graph/checkpointer.',
      'REST API calls between agents with JSON payloads.',
      'Shared prompt context only — no explicit state.',
    ],
  },
  {
    id: 'result',
    type: 'result',
    text: 'Diagnostic complete! Here\'s your proficiency profile:',
    profile: [
      { skill: 'LLM Fundamentals',       proficiency: 0.85, status: 'proficient' },
      { skill: 'Prompt Engineering',     proficiency: 0.72, status: 'developing' },
      { skill: 'RAG Architecture',       proficiency: 0.45, status: 'developing' },
      { skill: 'AI Agents & Tools',      proficiency: 0.20, status: 'exposure' },
      { skill: 'MCP Integration',        proficiency: 0.10, status: 'exposure' },
      { skill: 'Fine-Tuning',            proficiency: 0.60, status: 'developing' },
      { skill: 'Multimodal AI',          proficiency: 0.30, status: 'exposure' },
      { skill: 'AI Safety & Evaluation', proficiency: 0.55, status: 'developing' },
    ],
  },
];

function ChatBubble({ message, isUser, isTyping }) {
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} animate-fade-in-up`}>
      <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold
        ${isUser ? 'gradient-primary text-[var(--text-inverse)]' : 'gradient-primary text-[var(--text-inverse)]'}`}>
        {isUser ? 'AL' : 'AI'}
      </div>
      <div className={`max-w-[75%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed
        ${isUser
          ? 'bg-[var(--c-primary-dim)] text-[var(--text-primary)] rounded-tr-sm border border-[var(--c-primary)]/20'
          : 'bg-[var(--bg-surface)] text-[var(--text-secondary)] rounded-tl-sm border border-[var(--border)]'
        }`}>
        {isTyping ? (
          <div className="flex items-center gap-1.5 py-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] animate-[typing_1s_infinite_0ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] animate-[typing_1s_infinite_200ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] animate-[typing_1s_infinite_400ms]" />
          </div>
        ) : (
          <div dangerouslySetInnerHTML={{ __html: message.text.replace(/\*\*(.*?)\*\*/g, '<strong class="text-[var(--text-primary)]">$1</strong>') }} />
        )}
      </div>
    </div>
  );
}

export default function Diagnostic() {
  const [step, setStep] = useState(0);
  const [history, setHistory] = useState([diagnosticFlow[0]]);
  const [isTyping, setIsTyping] = useState(false);
  const [selectedOption, setSelectedOption] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [history, isTyping]);

  const handleOption = (optionIndex) => {
    setSelectedOption(optionIndex);
    const current = diagnosticFlow[step];
    const answerText = current.options ? current.options[optionIndex] : optionIndex === 0 ? 'Yes' : 'No';

    setHistory(prev => [...prev, { type: 'user', text: { text: answerText } }]);
    setIsTyping(true);

    setTimeout(() => {
      setIsTyping(false);
      const nextStep = step + 1;
      if (nextStep < diagnosticFlow.length) {
        setHistory(prev => [...prev, diagnosticFlow[nextStep]]);
        setStep(nextStep);
      }
      setSelectedOption(null);
    }, 1200 + Math.random() * 800);
  };

  const isComplete = history.some(h => h.type === 'result');

  return (
    <div className="h-full flex flex-col animate-fade-in">
      {/* Header */}
      <div className="card border-b border-[var(--border)] px-8 py-5 flex items-center justify-between flex-shrink-0 rounded-none">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)]">Adaptive Diagnostic</h2>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">Multi-turn skill assessment grounded in genai_research corpus</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--text-muted)]">Progress</span>
          <div className="w-32 h-2 rounded-full bg-[var(--border-subtle)] overflow-hidden">
            <div
              className="h-full rounded-full gradient-primary transition-all duration-700"
              style={{ width: `${Math.min((step / (diagnosticFlow.length - 2)) * 100, 100)}%` }}
            />
          </div>
          <span className="text-xs font-mono text-[var(--text-secondary)]">{Math.min(step, diagnosticFlow.length - 2)}/{diagnosticFlow.length - 2}</span>
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto p-8 space-y-5">
        {history.map((msg, i) => (
          <ChatBubble key={i} message={msg.type === 'user' ? msg.text : msg} isUser={msg.type === 'user'} />
        ))}
        {isTyping && <ChatBubble message={{ text: '' }} isUser={false} isTyping />}

        {isComplete && (
          <div className="mt-6 card border border-[var(--c-success)]/20 animate-scale-in">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Your Proficiency Profile</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {history.find(h => h.type === 'result').profile.map((skill, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-[var(--r-md)] bg-[var(--bg-surface)] border border-[var(--border)]">
                    <span className="text-sm text-[var(--text-secondary)]">{skill.skill}</span>
                    <div className="flex items-center gap-3">
                      <div className="w-24 h-2 rounded-full bg-[var(--border-subtle)] overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-1000"
                          style={{
                            width: `${skill.proficiency * 100}%`,
                            background: `var(--mastery-${skill.status})`,
                          }}
                        />
                      </div>
                      <SkillStateBadge status={skill.status} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-5 flex gap-3">
                <button className="btn-primary">
                  Generate Study Plan →
                </button>
                <button className="btn-secondary">
                  Retake Diagnostic
                </button>
              </div>
              <SourceRef sources={[
                { title: 'Diagnostic rubric from genai_research', record_type: 'coverage', path: 'coverage_report.json', citation_url: null },
              ]} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input / Options area */}
      {!isComplete && (
        <div className="card border-t border-[var(--border)] px-8 py-5 flex-shrink-0 rounded-none">
          {history[history.length - 1]?.options ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {history[history.length - 1].options.map((opt, i) => (
                <button
                  key={i}
                  disabled={isTyping || selectedOption !== null}
                  onClick={() => handleOption(i)}
                  className={`text-left p-4 rounded-[var(--r-md)] text-sm border transition-all duration-200
                    ${selectedOption === i
                      ? 'bg-[var(--c-primary-dim)] border-[var(--c-primary)]/40 text-[var(--text-primary)]'
                      : 'bg-[var(--bg-surface)] border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface-hover)] hover:border-[var(--border-hover)]'
                    }
                    ${(isTyping || selectedOption !== null) && selectedOption !== i ? 'opacity-50 cursor-not-allowed' : ''}
                  `}
                >
                  <span className="text-[var(--c-primary)] font-mono mr-2">{String.fromCharCode(65 + i)}.</span>
                  {opt}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="Type your answer or select an option above..."
                className="input flex-1"
                disabled={isTyping}
              />
              <button
                disabled={isTyping}
                className="btn-primary"
              >
                Send
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
