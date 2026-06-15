import { expect, test } from '@playwright/test'

const sampleSource = {
  source_id: 'topic-rag',
  record_type: 'topic',
  slug: 'rag',
  title: 'RAG',
  path: 'genai_research/topics/rag/topic_summary.json',
  citations: ['https://example.com/rag'],
  snippet: 'RAG retrieves source records and grounds tutor answers.',
  last_researched_at: '2026-01-01',
}

const progressPayload = {
  learner_id: 'demo-learner',
  goals: ['I want to learn AI agents.'],
  active_exercise_id: 'ex_rag_1',
  progress: {
    RAG: {
      skill: 'RAG',
      proficiency: 0.54,
      status: 'developing',
      attempts: 1,
      next_review: '2026-06-15',
      status_reason: 'RAG is developing because source-backed retrieval evidence exists.',
      source_refs: [sampleSource],
    },
    MCP: {
      skill: 'MCP',
      proficiency: 0.18,
      status: 'exposure',
      attempts: 0,
      status_reason: 'MCP needs a first practice checkpoint.',
      source_refs: [sampleSource],
    },
  },
  study_plan: [
    {
      order: 1,
      skill: 'RAG',
      status: 'developing',
      milestone: 'Explain retrieval, grounding, and citations.',
    },
  ],
  updated_at: '2026-06-14T00:00:00+00:00',
}

const exercisePayload = {
  learner_id: 'demo-learner',
  exercise: {
    id: 'ex_rag_1',
    learner_id: 'demo-learner',
    tenant_id: 'local',
    skill: 'RAG',
    exercise_type: 'architecture_scenario',
    difficulty: 'developing',
    prompt: 'Design a RAG flow for a GenAI learning tutor.',
    choices: [],
    answer_key: [],
    expected_points: [
      'Retrieve relevant corpus records with embeddings or search before answering.',
      'Ground the response in source snippets and citations.',
    ],
    rubric: 'Award credit for retrieval and grounding.',
    hints: ['Name retrieval before generation.'],
    source_refs: [sampleSource],
  },
  source_refs: [sampleSource],
}

async function mockApi(page) {
  await page.route('http://127.0.0.1:8999/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    let payload

    if (path === '/identity') {
      payload = {
        identity: { user_id: 'demo-learner', tenant_id: 'local', role: 'learner' },
        auth_mode: 'local',
        local_identity_switcher: true,
      }
    } else if (path.startsWith('/progress/')) {
      payload = progressPayload
    } else if (path === '/chat') {
      payload = {
        learner_id: 'demo-learner',
        thread_id: 'demo-learner',
        intent: 'diagnose',
        message: 'Here is a source-backed study path.',
        study_plan: { modules: progressPayload.study_plan },
        source_refs: [sampleSource],
      }
    } else if (path === '/diagnostic') {
      payload = { learner_id: 'demo-learner', summary: 'Diagnostic complete.', source_refs: [sampleSource] }
    } else if (path === '/study-plan') {
      payload = {
        learner_id: 'demo-learner',
        goal: 'I want to learn AI agents.',
        summary: 'Recommended path is ordered by prerequisite depth.',
        modules: progressPayload.study_plan,
        source_refs: [sampleSource],
      }
    } else if (path === '/exercise') {
      payload = exercisePayload
    } else if (path === '/answer') {
      payload = {
        learner_id: 'demo-learner',
        exercise_id: 'ex_rag_1',
        skill: 'RAG',
        score: 1,
        verdict: 'strong',
        explanation: 'The answer retrieves, grounds, preserves uncertainty, and evaluates.',
        covered_points: exercisePayload.exercise.expected_points,
        missed_points: [],
        mastery_update: {
          status_reason: 'RAG is proficient after a strong answer.',
          next_review_reason: 'Next review is tomorrow.',
        },
        source_refs: [sampleSource],
      }
    } else if (path === '/sources/search') {
      payload = {
        query: url.searchParams.get('q'),
        summary: 'Found source-backed corpus records.',
        results: [{ title: 'RAG', record_type: 'topic', path: sampleSource.path, score: 0.9, summary: sampleSource.snippet, citations: sampleSource.citations }],
        source_refs: [sampleSource],
      }
    } else if (path === '/cohort/progress') {
      payload = {
        learner_count: 1,
        risk_areas: [{ skill: 'MCP', average_proficiency: 0.18 }],
        learners: [{ learner_id: 'demo-learner', weakest_skills: [{ skill: 'MCP', proficiency: 0.18 }], updated_at: '2026-06-14' }],
        skill_summary: [{ skill: 'RAG', average_proficiency: 0.54 }],
      }
    } else if (path === '/cohort/interventions') {
      payload = {
        recommendations: [{ learner_id: 'demo-learner', skill: 'MCP', status: 'exposure', proficiency: 0.18, next_action: 'Assign one MCP exercise.' }],
      }
    } else if (path === '/admin/index-status') {
      payload = { ready: true, document_count: 180, metadata: { corpus_checksum: 'abc123' } }
    } else if (path === '/admin/source-quality') {
      payload = { document_count: 180, missing_citations_count: 2, missing_last_researched_at_count: 3 }
    } else if (path === '/admin/integrations') {
      payload = { repository_backend: 'json', supabase_enabled: false, vector_provider: 'local', llm_provider: 'deterministic' }
    } else if (path === '/admin/audit-events') {
      payload = { events: [{ event_id: 'audit_1', event_type: 'diagnostic', learner_id: 'demo-learner', outcome: 'success', at: '2026-06-14' }] }
    } else if (path === '/admin/retrieval-evaluation') {
      payload = { results: [{ topic: 'RAG', hit_count: 3, has_topic_or_course: true }] }
    } else {
      return route.fulfill({ status: 404, json: { error: { message: `Unhandled ${request.method()} ${path}` } } })
    }

    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) })
  })
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('learner can complete the core tutor flow', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Tutor', exact: true })).toBeVisible()

  await page.getByLabel('Tutor message').fill('I want to learn AI agents.')
  await page.getByRole('button', { name: /Send/ }).click()
  await expect(page.getByText('Here is a source-backed study path.')).toBeVisible()
  await expect(page.getByText('Explain retrieval, grounding, and citations.')).toBeVisible()

  await page.getByRole('button', { name: /Exercise/ }).click()
  await expect(page.getByText('Design a RAG flow for a GenAI learning tutor.')).toBeVisible()

  await page.getByRole('textbox', { name: 'Answer' }).fill('Retrieve local source records, ground with citations, preserve unknowns, and evaluate faithfulness.')
  await page.getByRole('button', { name: /Submit answer/ }).click()
  await expect(page.getByText('100%', { exact: true })).toBeVisible()
  await expect(page.getByText('RAG is proficient after a strong answer.')).toBeVisible()
})

test('admin and source workspaces render operational data', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Role').selectOption('admin')

  await page.locator('.mode-tabs').getByRole('button', { name: 'Admin' }).click()
  await expect(page.getByRole('heading', { name: 'Integrations' })).toBeVisible()
  await expect(page.getByText('abc123')).toBeVisible()
  await expect(page.getByText('diagnostic')).toBeVisible()

  await page.locator('.mode-tabs').getByRole('button', { name: 'Sources' }).click()
  await page.getByLabel('Source query').fill('RAG citations')
  await page.getByRole('button', { name: 'Search' }).click()
  await expect(page.getByText('genai_research/topics/rag/topic_summary.json')).toBeVisible()
})
