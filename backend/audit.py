"""Append-only audit events for tutor actions and operational checks."""

from __future__ import annotations

import contextvars
import json
import threading
import uuid
from typing import Any

from .enterprise_sink import mirror_audit_event
from .settings import get_settings
from .models import utc_now

_lock = threading.Lock()
_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
_tenant_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("tenant_id", default=None)
_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)
_role: contextvars.ContextVar[str | None] = contextvars.ContextVar("role", default=None)
# WEB-032, WEB-035: Track client IP for security events
_client_ip: contextvars.ContextVar[str | None] = contextvars.ContextVar("client_ip", default=None)

# Security event types for monitoring and alerting (WEB-032)
SECURITY_EVENT_TYPES = {
    "auth_success",
    "auth_failure",
    "rate_limit_exceeded",
    "token_budget_exceeded",
    "prompt_injection_blocked",
    "mcp_input_blocked",
    "invalid_role",
    "unauthorized_access",
    "state_integrity_failure",
}


def set_request_context(
    request_id: str | None = None,
    client_ip: str | None = None,
) -> tuple[contextvars.Token[str | None] | None, contextvars.Token[str | None] | None]:
    """Set request context including client IP for security logging (WEB-032)."""
    req_token = _request_id.set(request_id) if request_id else None
    ip_token = _client_ip.set(client_ip) if client_ip else None
    return req_token, ip_token


def reset_full_request_context(
    tokens: tuple[contextvars.Token[str | None] | None, contextvars.Token[str | None] | None],
) -> None:
    """Reset both request_id and client_ip context."""
    req_token, ip_token = tokens
    if req_token is not None:
        _request_id.reset(req_token)
    if ip_token is not None:
        _client_ip.reset(ip_token)


def set_actor_context(
    tenant_id: str | None = None,
    user_id: str | None = None,
    role: str | None = None,
) -> tuple[contextvars.Token[str | None] | None, ...]:
    return (
        _tenant_id.set(tenant_id) if tenant_id is not None else None,
        _user_id.set(user_id) if user_id is not None else None,
        _role.set(role) if role is not None else None,
    )


def clear_actor_context() -> tuple[contextvars.Token[str | None], ...]:
    return (_tenant_id.set(None), _user_id.set(None), _role.set(None))


def reset_context(tokens: tuple[contextvars.Token[str | None] | None, ...]) -> None:
    variables = (_tenant_id, _user_id, _role)
    for variable, token in zip(variables, tokens, strict=False):
        if token is not None:
            variable.reset(token)


def reset_request_context(token: contextvars.Token[str | None] | None) -> None:
    if token is not None:
        _request_id.reset(token)


def current_request_id() -> str | None:
    return _request_id.get()


def current_actor() -> dict[str, str | None]:
    return {
        "tenant_id": _tenant_id.get(),
        "user_id": _user_id.get(),
        "role": _role.get(),
    }


def write_audit_event(
    event_type: str,
    *,
    learner_id: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    role: str | None = None,
    outcome: str = "success",
    metadata: dict[str, Any] | None = None,
    client_ip: str | None = None,  # WEB-032: Explicit IP override
) -> dict[str, Any]:
    """Append a compact JSONL audit event and return the event payload.

    Security events (WEB-032) include client_ip for forensics. Event types in
    SECURITY_EVENT_TYPES are flagged with is_security_event=True.
    """
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    is_security = event_type in SECURITY_EVENT_TYPES
    event = {
        "event_id": f"audit_{uuid.uuid4().hex}",
        "at": utc_now(),
        "event_type": event_type,
        "is_security_event": is_security,  # WEB-032: Flag for SIEM filtering
        "request_id": _request_id.get(),
        "tenant_id": tenant_id or _tenant_id.get() or settings.local_tenant_id,
        "user_id": user_id or _user_id.get(),
        "role": role or _role.get(),
        "learner_id": learner_id,
        "outcome": outcome,
        "metadata": metadata or {},
    }
    # WEB-032: Include client IP for security events
    ip = client_ip or _client_ip.get()
    if ip and is_security:
        event["client_ip"] = ip
    with _lock:
        with settings.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    # Best-effort mirror to the Supabase audit_events table (no-op under json/local).
    mirror_audit_event(event)
    return event


def read_audit_events(
    *,
    tenant_id: str | None = None,
    learner_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.audit_log_path.exists():
        return []
    events: list[dict[str, Any]] = []
    with settings.audit_log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if tenant_id and event.get("tenant_id") != tenant_id:
                continue
            if learner_id and event.get("learner_id") != learner_id:
                continue
            if event_type and event.get("event_type") != event_type:
                continue
            events.append(event)
    return events[-max(1, limit) :]
