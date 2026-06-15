import { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  BookOpenCheck,
  CheckCircle2,
  ClipboardCheck,
  Database,
  Dumbbell,
  FileSearch,
  Gauge,
  RefreshCcw,
  Search,
  Send,
  ShieldCheck,
  Users,
  WifiOff,
} from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function requestJson(path, options = {}, identity = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      'x-tutor-user-id': identity.userId || 'demo-learner',
      'x-tutor-tenant-id': identity.tenantId || 'local',
      'x-tutor-role': identity.role || 'learner',
      ...(options.headers || {}),
    },
    ...options,
  })
  if (!response.ok) {
    let message = response.statusText
    try {
      const payload = await response.json()
      message = payload.error?.message || payload.detail || message
    } catch {
      message = await response.text()
    }
    throw new Error(message || response.statusText)
  }
  return response.json()
}

function collectSources(payload) {
  if (!payload) return []
  const refs = []
  const visit = (value) => {
    if (!value) return
    if (Array.isArray(value)) {
      value.forEach(visit)
      return
    }
    if (typeof value === 'object') {
      if (value.source_id && value.path) refs.push(value)
      Object.values(value).forEach(visit)
    }
  }
  visit(payload)
  const seen = new Set()
  const typeRank = { topic: 0, course: 1, coverage: 2, research_index: 3, instructor: 4 }
  return refs.filter((ref) => {
    if (seen.has(ref.source_id)) return false
    seen.add(ref.source_id)
    return true
  }).sort((a, b) => (typeRank[a.record_type] ?? 9) - (typeRank[b.record_type] ?? 9))
}

function topProgress(progress) {
  if (!progress?.progress) return []
  return Object.values(progress.progress)
    .sort((a, b) => {
      if (a.status === 'review' && b.status !== 'review') return -1
      if (b.status === 'review' && a.status !== 'review') return 1
      return a.proficiency - b.proficiency
    })
    .slice(0, 10)
}

function pct(value) {
  return `${Math.round((value || 0) * 100)}%`
}

const modeIcons = {
  learner: BookOpenCheck,
  educator: Users,
  admin: ShieldCheck,
  sources: FileSearch,
}

export default function App() {
  const [learnerId, setLearnerId] = useState('demo-learner')
  const [tenantId, setTenantId] = useState('local')
  const [role, setRole] = useState('learner')
  const [mode, setMode] = useState('learner')
  const [identityInfo, setIdentityInfo] = useState(null)
  const [input, setInput] = useState('I want to learn AI agents.')
  const [goal, setGoal] = useState('I want to learn AI agents.')
  const [messages, setMessages] = useState([
    { role: 'tutor', text: 'Ready for a source-backed GenAI study session.' },
  ])
  const [progress, setProgress] = useState(null)
  const [studyPlan, setStudyPlan] = useState([])
  const [exercise, setExercise] = useState(null)
  const [exerciseType, setExerciseType] = useState('architecture_scenario')
  const [answer, setAnswer] = useState('')
  const [grading, setGrading] = useState(null)
  const [sources, setSources] = useState([])
  const [sourceQuery, setSourceQuery] = useState('AI agents RAG MCP')
  const [cohort, setCohort] = useState(null)
  const [interventions, setInterventions] = useState(null)
  const [adminData, setAdminData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [online, setOnline] = useState(() => navigator.onLine)

  const auth = useMemo(() => ({
    userId: role === 'learner' ? learnerId : `${role}-local`,
    tenantId,
    role,
  }), [learnerId, role, tenantId])
  const weakSkills = useMemo(() => topProgress(progress), [progress])
  const modes = role === 'admin'
    ? ['learner', 'educator', 'admin', 'sources']
    : role === 'educator'
      ? ['learner', 'educator', 'sources']
      : ['learner', 'sources']

  async function api(path, options = {}) {
    return requestJson(path, options, auth)
  }

  async function runAction(action) {
    setLoading(true)
    setError('')
    try {
      await action()
    } catch (err) {
      setError(err.message || 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  async function refreshProgress(id = learnerId) {
    const payload = await api(`/progress/${encodeURIComponent(id)}`)
    setProgress(payload)
    if (payload.study_plan?.length) setStudyPlan(payload.study_plan)
    return payload
  }

  useEffect(() => {
    const goOnline = () => setOnline(true)
    const goOffline = () => setOnline(false)
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [])

  useEffect(() => {
    requestJson('/identity', {}, auth)
      .then(setIdentityInfo)
      .catch(() => {})
    refreshProgress().catch(() => {})
  }, [learnerId, tenantId, role])

  useEffect(() => {
    if (!modes.includes(mode)) setMode('learner')
  }, [mode, modes])

  useEffect(() => {
    if (mode !== 'educator') return
    runAction(async () => {
      const [cohortPayload, interventionPayload] = await Promise.all([
        api('/cohort/progress'),
        api('/cohort/interventions'),
      ])
      setCohort(cohortPayload)
      setInterventions(interventionPayload)
    })
  }, [mode, role, tenantId])

  useEffect(() => {
    if (mode !== 'admin') return
    runAction(async () => {
      const [indexStatus, sourceQuality, integrations, auditEvents, retrievalEval] = await Promise.all([
        api('/admin/index-status'),
        api('/admin/source-quality'),
        api('/admin/integrations'),
        api('/admin/audit-events?limit=12'),
        api('/admin/retrieval-evaluation'),
      ])
      setAdminData({ indexStatus, sourceQuality, integrations, auditEvents, retrievalEval })
    })
  }, [mode, role, tenantId])

  async function sendChat() {
    const text = input.trim()
    if (!text) return
    setGoal(text)
    setMessages((items) => [...items, { role: 'learner', text }])
    setInput('')
    await runAction(async () => {
      const payload = await api('/chat', {
        method: 'POST',
        body: JSON.stringify({ learner_id: learnerId, message: text, thread_id: learnerId }),
      })
      const tutorText = payload.needs_clarification
        ? payload.interrupt?.message || 'I need a clarification before continuing.'
        : payload.message
      setMessages((items) => [...items, { role: 'tutor', text: tutorText }])
      if (payload.study_plan?.modules) setStudyPlan(payload.study_plan.modules)
      if (payload.study_plan?.study_plan?.modules) setStudyPlan(payload.study_plan.study_plan.modules)
      if (payload.exercise?.exercise) setExercise(payload.exercise.exercise)
      if (payload.grading) setGrading(payload.grading)
      setSources(collectSources(payload))
      await refreshProgress()
    })
  }

  async function runDiagnostic() {
    await runAction(async () => {
      const payload = await api('/diagnostic', {
        method: 'POST',
        body: JSON.stringify({
          learner_id: learnerId,
          goal,
          answers: ['I know agents can call tools, but I am still unsure about RAG and MCP.'],
        }),
      })
      setMessages((items) => [...items, { role: 'tutor', text: payload.summary }])
      setSources(collectSources(payload))
      await refreshProgress()
    })
  }

  async function recommendPath() {
    await runAction(async () => {
      const payload = await api('/study-plan', {
        method: 'POST',
        body: JSON.stringify({ learner_id: learnerId, goal }),
      })
      setStudyPlan(payload.modules)
      setSources(collectSources(payload))
      setMessages((items) => [...items, { role: 'tutor', text: payload.summary }])
      await refreshProgress()
    })
  }

  async function getExercise() {
    await runAction(async () => {
      const payload = await api('/exercise', {
        method: 'POST',
        body: JSON.stringify({ learner_id: learnerId, goal, exercise_type: exerciseType }),
      })
      setExercise(payload.exercise)
      setGrading(null)
      setSources(collectSources(payload))
      setMessages((items) => [...items, { role: 'tutor', text: `Exercise ready: ${payload.exercise.skill}` }])
      await refreshProgress()
    })
  }

  async function submitAnswer() {
    if (!answer.trim()) return
    await runAction(async () => {
      const payload = await api('/answer', {
        method: 'POST',
        body: JSON.stringify({ learner_id: learnerId, exercise_id: exercise?.id, answer }),
      })
      const text = payload.needs_clarification
        ? payload.message
        : `Score ${Math.round(payload.score * 100)}%. ${payload.explanation}`
      setMessages((items) => [...items, { role: 'learner', text: answer }, { role: 'tutor', text }])
      setGrading(payload)
      setSources(collectSources(payload))
      if (!payload.needs_clarification) setAnswer('')
      await refreshProgress()
    })
  }

  async function searchSources(query = goal) {
    await runAction(async () => {
      const payload = await api(`/sources/search?q=${encodeURIComponent(query)}&k=8`)
      setSources(collectSources(payload))
      setMessages((items) => [...items, { role: 'tutor', text: payload.summary }])
    })
  }

  function renderSources(limit = 8) {
    return (
      <div className="source-list">
        {sources.length ? sources.slice(0, limit).map((source) => (
          <div className="source-row" key={source.source_id}>
            <div>
              <strong>{source.title}</strong>
              <b>{source.record_type}</b>
            </div>
            <span>{source.path}</span>
            {source.citations?.[0] && <a href={source.citations[0]} target="_blank" rel="noreferrer">Citation</a>}
            {source.last_researched_at && <small>Researched: {source.last_researched_at}</small>}
            {source.snippet && <p>{source.snippet}</p>}
          </div>
        )) : <p className="empty">No sources loaded.</p>}
      </div>
    )
  }

  function LearnerView() {
    return (
      <section className="workspace learner-grid">
        <div className="panel chat-panel">
          <div className="panel-heading">
            <BookOpenCheck size={18} />
            <h2>Tutor</h2>
          </div>
          <div className="messages">
            {messages.map((message, index) => (
              <div className={`message ${message.role}`} key={`${message.role}-${index}`}>{message.text}</div>
            ))}
          </div>
          <div className="chat-input">
            <input
              aria-label="Tutor message"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') sendChat()
              }}
            />
            <button title="Send message" onClick={sendChat} disabled={loading}>
              <Send size={17} />
              Send
            </button>
          </div>
          <div className="toolbar">
            <button title="Run diagnostic" onClick={runDiagnostic} disabled={loading}>
              <ClipboardCheck size={16} />
              Diagnostic
            </button>
            <button title="Recommend study path" onClick={recommendPath} disabled={loading}>
              <Activity size={16} />
              Path
            </button>
            <button title="Generate exercise" onClick={getExercise} disabled={loading}>
              <Dumbbell size={16} />
              Exercise
            </button>
            <button title="Search sources" onClick={() => searchSources()} disabled={loading}>
              <Search size={16} />
              Sources
            </button>
            <button title="Refresh progress" onClick={() => refreshProgress()} disabled={loading}>
              <RefreshCcw size={16} />
            </button>
          </div>
        </div>

        <div className="panel exercise-panel">
          <div className="panel-heading">
            <Dumbbell size={18} />
            <h2>Current Exercise</h2>
          </div>
          {exercise ? (
            <>
              <div className="exercise-meta">
                <span>{exercise.skill}</span>
                <span>{exercise.exercise_type?.replaceAll('_', ' ')}</span>
                <span>{exercise.difficulty}</span>
              </div>
              <p className="exercise-prompt">{exercise.prompt}</p>
              {exercise.choices?.length ? (
                <ol className="choice-list">
                  {exercise.choices.map((choice) => <li key={choice}>{choice}</li>)}
                </ol>
              ) : null}
              <details className="rubric-box">
                <summary>Rubric</summary>
                <ul>{exercise.expected_points?.map((point) => <li key={point}>{point}</li>)}</ul>
              </details>
              <textarea aria-label="Answer" value={answer} onChange={(event) => setAnswer(event.target.value)} />
              <button className="primary" title="Submit answer" onClick={submitAnswer} disabled={loading}>
                <CheckCircle2 size={17} />
                Submit answer
              </button>
              {grading && (
                <div className="grading-result">
                  {grading.needs_clarification ? (
                    <p>{grading.message}</p>
                  ) : (
                    <>
                      <div className="score-line">
                        <strong>{pct(grading.score)}</strong>
                        <span>{grading.verdict}</span>
                      </div>
                      <p>{grading.mastery_update?.status_reason || grading.explanation}</p>
                      {grading.mastery_update?.next_review_reason && <p>{grading.mastery_update.next_review_reason}</p>}
                      <div className="rubric-columns">
                        <div>
                          <h3>Covered</h3>
                          {grading.covered_points?.map((point) => <span key={point}>{point}</span>)}
                        </div>
                        <div>
                          <h3>Missed</h3>
                          {grading.missed_points?.length
                            ? grading.missed_points.map((point) => <span key={point}>{point}</span>)
                            : <span>None</span>}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}
            </>
          ) : <p className="empty">No active exercise.</p>}
          <label className="select-field">
            <span>Exercise type</span>
            <select value={exerciseType} onChange={(event) => setExerciseType(event.target.value)}>
              <option value="architecture_scenario">Architecture scenario</option>
              <option value="design_critique">Design critique</option>
              <option value="implementation_prompt">Implementation prompt</option>
              <option value="multiple_choice">Multiple choice</option>
              <option value="short_answer">Short answer</option>
            </select>
          </label>
        </div>

        <div className="panel progress-panel">
          <div className="panel-heading">
            <Activity size={18} />
            <h2>Progress</h2>
          </div>
          <div className="skill-list">
            {weakSkills.map((item) => (
              <div className="skill-row" key={item.skill}>
                <div>
                  <strong>{item.skill}</strong>
                  <span>{item.status}</span>
                </div>
                <meter min="0" max="1" value={item.proficiency} />
                <p>{item.status_reason || `Proficiency ${pct(item.proficiency)}`}</p>
                {item.next_review && <small>Next review: {item.next_review}</small>}
              </div>
            ))}
          </div>
        </div>

        <div className="panel plan-panel">
          <div className="panel-heading">
            <ClipboardCheck size={18} />
            <h2>Study Plan</h2>
          </div>
          <div className="plan-list">
            {studyPlan.length ? studyPlan.map((module) => (
              <div className="plan-row" key={`${module.order}-${module.skill}`}>
                <span>{module.order}</span>
                <div>
                  <strong>{module.skill}</strong>
                  <em>{module.status}</em>
                  <p>{module.milestone}</p>
                </div>
              </div>
            )) : <p className="empty">No plan generated.</p>}
          </div>
        </div>

        <div className="panel sources-panel">
          <div className="panel-heading">
            <Search size={18} />
            <h2>Sources Used</h2>
          </div>
          {renderSources(8)}
        </div>
      </section>
    )
  }

  function EducatorView() {
    return (
      <section className="workspace ops-grid">
        <div className="panel wide-panel">
          <div className="panel-heading">
            <Users size={18} />
            <h2>Cohort Progress</h2>
          </div>
          <div className="metric-strip">
            <div><strong>{cohort?.learner_count ?? 0}</strong><span>Learners</span></div>
            <div><strong>{cohort?.risk_areas?.length ?? 0}</strong><span>Risk areas</span></div>
            <div><strong>{interventions?.recommendations?.length ?? 0}</strong><span>Interventions</span></div>
          </div>
          <div className="table-list">
            {cohort?.learners?.length ? cohort.learners.map((learner) => (
              <div className="table-row" key={learner.learner_id}>
                <strong>{learner.learner_id}</strong>
                <span>{learner.weakest_skills.map((item) => `${item.skill} ${pct(item.proficiency)}`).join(' | ')}</span>
                <small>{learner.updated_at}</small>
              </div>
            )) : <p className="empty">No cohort data.</p>}
          </div>
        </div>
        <div className="panel">
          <div className="panel-heading">
            <Gauge size={18} />
            <h2>Skill Summary</h2>
          </div>
          <div className="skill-list">
            {cohort?.skill_summary?.map((item) => (
              <div className="skill-row" key={item.skill}>
                <div><strong>{item.skill}</strong><span>{pct(item.average_proficiency)}</span></div>
                <meter min="0" max="1" value={item.average_proficiency} />
              </div>
            ))}
          </div>
        </div>
        <div className="panel">
          <div className="panel-heading">
            <ClipboardCheck size={18} />
            <h2>Interventions</h2>
          </div>
          <div className="table-list">
            {interventions?.recommendations?.length ? interventions.recommendations.map((item) => (
              <div className="table-row" key={`${item.learner_id}-${item.skill}`}>
                <strong>{item.learner_id}</strong>
                <span>{item.skill} · {item.status} · {pct(item.proficiency)}</span>
                <small>{item.next_action}</small>
              </div>
            )) : <p className="empty">No interventions.</p>}
          </div>
        </div>
      </section>
    )
  }

  function AdminView() {
    return (
      <section className="workspace admin-grid">
        <div className="panel">
          <div className="panel-heading">
            <Database size={18} />
            <h2>Index</h2>
          </div>
          <div className="metric-strip compact">
            <div><strong>{adminData?.indexStatus?.document_count ?? 0}</strong><span>Docs</span></div>
            <div><strong>{adminData?.indexStatus?.ready ? 'Ready' : 'Down'}</strong><span>Status</span></div>
          </div>
          <p className="mono-line">{adminData?.indexStatus?.metadata?.corpus_checksum || 'unknown'}</p>
        </div>
        <div className="panel">
          <div className="panel-heading">
            <FileSearch size={18} />
            <h2>Source Quality</h2>
          </div>
          <div className="metric-strip compact">
            <div><strong>{adminData?.sourceQuality?.document_count ?? 0}</strong><span>Records</span></div>
            <div><strong>{adminData?.sourceQuality?.missing_citations_count ?? 0}</strong><span>No citations</span></div>
            <div><strong>{adminData?.sourceQuality?.missing_last_researched_at_count ?? 0}</strong><span>Unknown dates</span></div>
          </div>
        </div>
        <div className="panel">
          <div className="panel-heading">
            <ShieldCheck size={18} />
            <h2>Integrations</h2>
          </div>
          <div className="table-list">
            {adminData?.integrations && Object.entries(adminData.integrations).map(([key, value]) => (
              <div className="table-row" key={key}>
                <strong>{key.replaceAll('_', ' ')}</strong>
                <span>{String(value)}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="panel wide-panel">
          <div className="panel-heading">
            <Activity size={18} />
            <h2>Audit Log</h2>
          </div>
          <div className="table-list">
            {adminData?.auditEvents?.events?.length ? adminData.auditEvents.events.map((event) => (
              <div className="table-row" key={event.event_id}>
                <strong>{event.event_type}</strong>
                <span>{event.learner_id || event.user_id || event.role || 'system'} · {event.outcome}</span>
                <small>{event.at}</small>
              </div>
            )) : <p className="empty">No audit events.</p>}
          </div>
        </div>
        <div className="panel">
          <div className="panel-heading">
            <Search size={18} />
            <h2>Retrieval Eval</h2>
          </div>
          <div className="table-list">
            {adminData?.retrievalEval?.results?.map((item) => (
              <div className="table-row" key={item.topic}>
                <strong>{item.topic}</strong>
                <span>{item.hit_count} hits</span>
                <small>{item.has_topic_or_course ? 'topic/course present' : 'needs review'}</small>
              </div>
            ))}
          </div>
        </div>
      </section>
    )
  }

  function SourcesView() {
    return (
      <section className="workspace source-grid">
        <div className="panel wide-panel">
          <div className="panel-heading">
            <Search size={18} />
            <h2>Sources</h2>
          </div>
          <div className="chat-input">
            <input
              aria-label="Source query"
              value={sourceQuery}
              onChange={(event) => setSourceQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') searchSources(sourceQuery)
              }}
            />
            <button onClick={() => searchSources(sourceQuery)} disabled={loading}>
              <Search size={17} />
              Search
            </button>
          </div>
          {renderSources(20)}
        </div>
      </section>
    )
  }

  const View = mode === 'educator' ? EducatorView : mode === 'admin' ? AdminView : mode === 'sources' ? SourcesView : LearnerView

  return (
    <main className="app-shell">
      <section className="topbar">
        <div>
          <h1>Adaptive GenAI Learning Tutor</h1>
          <p>Local corpus: genai_research</p>
        </div>
        <nav className="mode-tabs" aria-label="Workspace mode">
          {modes.map((item) => {
            const Icon = modeIcons[item]
            return (
              <button
                className={mode === item ? 'active' : ''}
                key={item}
                onClick={() => setMode(item)}
                type="button"
              >
                <Icon size={16} />
                {item[0].toUpperCase() + item.slice(1)}
              </button>
            )
          })}
        </nav>
        {(identityInfo?.local_identity_switcher ?? true) && (
          <div className="identity-grid">
            <label>
              <span>Tenant</span>
              <input value={tenantId} onChange={(event) => setTenantId(event.target.value)} />
            </label>
            <label>
              <span>Learner</span>
              <input value={learnerId} onChange={(event) => setLearnerId(event.target.value)} />
            </label>
            <label>
              <span>Role</span>
              <select value={role} onChange={(event) => setRole(event.target.value)}>
                <option value="learner">Learner</option>
                <option value="educator">Educator</option>
                <option value="admin">Admin</option>
              </select>
            </label>
          </div>
        )}
      </section>
      {!online && <div className="status-banner offline"><WifiOff size={16} /> Offline</div>}
      {loading && <div className="status-banner">Loading</div>}
      {error && <div className="error">{error}</div>}
      <View />
    </main>
  )
}
