// Runtime configuration, sourced from Vite env vars (VITE_*) with safe local defaults.
// Local dev points at the backend on :8000; the deployed SPA is built with
// VITE_API_URL set to the Railway backend URL.

const RAW_API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const API_URL = RAW_API.replace(/\/+$/, ''); // strip any trailing slash

// Sent as x-tutor-tenant-id. The Supabase-backed prod backend requires the seeded
// tenant UUID; for a local json backend any value works.
export const DEFAULT_TENANT_ID =
  import.meta.env.VITE_TUTOR_TENANT_ID || '0507cc0e-4a9f-4468-ab32-b56bd87fc97d';

export const DEFAULT_LEARNER_ID = import.meta.env.VITE_TUTOR_LEARNER_ID || 'demo-learner';
export const DEFAULT_ROLE = import.meta.env.VITE_TUTOR_ROLE || 'learner';

// Deep-agent /chat turns run several Qwen calls and can take ~40s; keep the client
// timeout generous so the flagship chat doesn't abort mid-turn.
export const REQUEST_TIMEOUT_MS = Number(import.meta.env.VITE_REQUEST_TIMEOUT_MS || 90000);

export const ROLES = ['learner', 'educator', 'admin'];
