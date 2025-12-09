from __future__ import annotations

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api_gateway.core.context import (
    build_request_context,
    reset_request_context,
    set_request_context,
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Populate per-request tracing context and propagate headers."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        incoming_trace = request.headers.get("X-Request-ID")
        tenant_id = request.headers.get("X-Tenant-ID")
        context = build_request_context(user=None, tenant_id=tenant_id, trace_id=incoming_trace)
        token = set_request_context(context)
        request.state.trace_id = context.trace_id
        if tenant_id:
            request.state.tenant_id = tenant_id
        try:
            response = await call_next(request)
        finally:
            reset_request_context(token)
        response.headers["X-Request-ID"] = context.trace_id
        if tenant_id:
            response.headers["X-Tenant-ID"] = tenant_id
        return response
