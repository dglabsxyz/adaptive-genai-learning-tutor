// Thin fetch wrapper for the tutor backend: injects identity headers, enforces a
// timeout, and normalizes the backend's {error:{code,message,details}, request_id}
// envelope into a typed ApiError. Every endpoint goes through here.

import { API_URL, REQUEST_TIMEOUT_MS } from '../config';

export class ApiError extends Error {
  constructor(message, { code = 'error', status = 0, requestId = null, details = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.requestId = requestId;
    this.details = details;
  }
}

function identityHeaders(identity) {
  const h = {};
  if (!identity) return h;
  if (identity.learnerId) h['x-tutor-user-id'] = identity.learnerId;
  if (identity.tenantId) h['x-tutor-tenant-id'] = identity.tenantId;
  if (identity.role) h['x-tutor-role'] = identity.role;
  return h;
}

export async function apiFetch(
  path,
  { method = 'GET', body, identity, signal, timeoutMs = REQUEST_TIMEOUT_MS } = {},
) {
  const url = `${API_URL}${path}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener('abort', () => controller.abort(), { once: true });
  }

  let response;
  try {
    response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', ...identityHeaders(identity) },
      body: body != null ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timer);
    if (err?.name === 'AbortError') {
      throw new ApiError('The request timed out or was cancelled.', { code: 'timeout' });
    }
    throw new ApiError(`Could not reach the tutor backend at ${API_URL}.`, { code: 'network' });
  }
  clearTimeout(timer);

  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { raw: text };
    }
  }

  if (!response.ok) {
    const err = (payload && payload.error) || {};
    throw new ApiError(err.message || `Request failed (${response.status}).`, {
      code: err.code || 'http_error',
      status: response.status,
      requestId: (payload && payload.request_id) || null,
      details: err.details || null,
    });
  }
  return payload;
}

// SSE streaming for POST /chat/stream. Parses `data: {json}` frames, calls
// onStep(label) for each progress event, and resolves with the terminal `final`
// event payload (same shape as POST /chat). Throws ApiError on transport failure
// so callers can fall back to the non-streaming /chat.
export async function streamChat(
  path,
  { body, identity, onStep, signal, timeoutMs = REQUEST_TIMEOUT_MS } = {},
) {
  const url = `${API_URL}${path}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener('abort', () => controller.abort(), { once: true });
  }

  let response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', ...identityHeaders(identity) },
      body: body != null ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timer);
    if (err?.name === 'AbortError') throw new ApiError('The request timed out or was cancelled.', { code: 'timeout' });
    throw new ApiError(`Could not reach the tutor backend at ${API_URL}.`, { code: 'network' });
  }
  if (!response.ok || !response.body) {
    clearTimeout(timer);
    throw new ApiError(`Stream failed (${response.status}).`, { code: 'stream', status: response.status });
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalEvent = null;
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const dataLine = frame.split('\n').find((l) => l.startsWith('data:'));
        if (!dataLine) continue;
        let evt;
        try {
          evt = JSON.parse(dataLine.slice(5).trim());
        } catch {
          continue;
        }
        if (evt.type === 'step') onStep?.(evt.label);
        else if (evt.type === 'final') finalEvent = evt;
      }
    }
  } finally {
    clearTimeout(timer);
  }
  if (!finalEvent) throw new ApiError('Stream ended without a final response.', { code: 'stream' });
  return finalEvent;
}
