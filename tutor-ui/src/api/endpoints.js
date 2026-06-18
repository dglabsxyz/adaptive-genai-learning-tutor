// Typed endpoint functions for the tutor backend. Each takes the current `identity`
// ({ learnerId, tenantId, role }) so requests carry the right auth headers + scope.
// Prefer the bound versions from useApi() in components.

import { apiFetch, streamChat } from './client';

// --- health / identity ---------------------------------------------------
export const getHealth = (identity) => apiFetch('/health', { identity });
export const getIdentity = (identity) => apiFetch('/identity', { identity });

// --- deep-agent chat (flagship) -----------------------------------------
export const postChat = (identity, { learnerId, message, threadId }) =>
  apiFetch('/chat', {
    method: 'POST',
    identity,
    body: { learner_id: learnerId, message, thread_id: threadId },
  });

// resume an interrupted (HITL) turn. `resume` is the decisions payload, e.g.
// { decisions: [{ type: 'approve' }] } or { decisions: [{ type: 'reject' }] };
// for a clarification interrupt it is the answer string.
export const postChatResume = (identity, { learnerId, threadId, resume }) =>
  apiFetch('/chat/resume', {
    method: 'POST',
    identity,
    body: { learner_id: learnerId, thread_id: threadId, resume },
  });

// streaming variant of postChat: onStep(label) fires per progress event; resolves
// with the same final payload as postChat. Falls back to postChat on transport error.
export const postChatStream = (identity, { learnerId, message, threadId }, { onStep, signal } = {}) =>
  streamChat('/chat/stream', {
    identity,
    body: { learner_id: learnerId, message, thread_id: threadId },
    onStep,
    signal,
  });

// --- deterministic tutor REST (fast; power the structured pages) ----------
export const postDiagnostic = (identity, { learnerId, goal, answers }) =>
  apiFetch('/diagnostic', {
    method: 'POST',
    identity,
    body: { learner_id: learnerId, goal, answers },
  });

export const postStudyPlan = (identity, { learnerId, goal }) =>
  apiFetch('/study-plan', { method: 'POST', identity, body: { learner_id: learnerId, goal } });

export const postExercise = (identity, { learnerId, skill, goal, exerciseType }) =>
  apiFetch('/exercise', {
    method: 'POST',
    identity,
    body: { learner_id: learnerId, skill, goal, exercise_type: exerciseType },
  });

export const postAnswer = (identity, { learnerId, exerciseId, answer }) =>
  apiFetch('/answer', {
    method: 'POST',
    identity,
    body: { learner_id: learnerId, exercise_id: exerciseId, answer },
  });

// --- progress ------------------------------------------------------------
const enc = encodeURIComponent;
export const getProgress = (identity, learnerId) =>
  apiFetch(`/progress/${enc(learnerId)}`, { identity });
export const getEvidence = (identity, learnerId, skill) =>
  apiFetch(`/progress/${enc(learnerId)}/evidence${skill ? `?skill=${enc(skill)}` : ''}`, { identity });
export const getExport = (identity, learnerId) =>
  apiFetch(`/progress/${enc(learnerId)}/export`, { identity });
export const resetProgress = (identity, learnerId, scope = 'all') =>
  apiFetch(`/progress/${enc(learnerId)}/reset`, {
    method: 'POST',
    identity,
    body: { confirm: true, scope },
  });

// --- corpus --------------------------------------------------------------
export const searchSources = (identity, q, k = 8) =>
  apiFetch(`/sources/search?q=${enc(q)}&k=${k}`, { identity });

// --- educator / admin ----------------------------------------------------
export const getCohortProgress = (identity) => apiFetch('/cohort/progress', { identity });
export const getCohortInterventions = (identity) => apiFetch('/cohort/interventions', { identity });
export const getAdminIntegrations = (identity) => apiFetch('/admin/integrations', { identity });
export const getAdminIndexStatus = (identity) => apiFetch('/admin/index-status', { identity });
export const getAdminAuditEvents = (identity, { limit = 50 } = {}) =>
  apiFetch(`/admin/audit-events?limit=${limit}`, { identity });
