"""Request IDs, structured logs, and error response helpers."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from .audit import clear_actor_context, current_actor, reset_context, reset_request_context, set_request_context
from .settings import get_settings

logger = logging.getLogger("adaptive_tutor")


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    settings = get_settings()
    request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex}"
    token = set_request_context(request_id)
    actor_tokens = clear_actor_context()
    start = time.perf_counter()
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.request_body_limit_bytes:
        response = JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "request_too_large",
                    "message": "Request body exceeds configured limit.",
                },
                "request_id": request_id,
            },
        )
        response.headers["x-request-id"] = request_id
        reset_context(actor_tokens)
        reset_request_context(token)
        return response
    try:
        response = await call_next(request)
        status_code = response.status_code
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        actor = current_actor()
        tenant_id = actor.get("tenant_id") or request.headers.get("x-tutor-tenant-id")
        user_id = actor.get("user_id") or request.headers.get("x-tutor-user-id")
        role = actor.get("role") or request.headers.get("x-tutor-role")
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": locals().get("status_code", 500),
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "role": role,
                    "duration_ms": duration_ms,
                },
                sort_keys=True,
            )
        )
        reset_context(actor_tokens)
        reset_request_context(token)
    response.headers["x-request-id"] = request_id
    return response
