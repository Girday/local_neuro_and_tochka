import contextvars
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AuthenticatedUser:
    user_id: str
    username: str
    tenant_id: str
    roles: list[str] = field(default_factory=list)
    display_name: Optional[str] = None


@dataclass
class RequestContext:
    trace_id: str
    tenant_id: Optional[str]
    user: Optional[AuthenticatedUser]


_request_context: contextvars.ContextVar[RequestContext] = contextvars.ContextVar("request_context")


def generate_trace_id() -> str:
    return str(uuid.uuid4())


def set_request_context(context: RequestContext) -> contextvars.Token[RequestContext]:
    return _request_context.set(context)


def reset_request_context(token: contextvars.Token[RequestContext]) -> None:
    _request_context.reset(token)


def get_request_context() -> RequestContext:
    try:
        return _request_context.get()
    except LookupError as exc:  # pragma: no cover
        raise RuntimeError("Request context is not set") from exc


def build_request_context(user: Optional[AuthenticatedUser], tenant_id: Optional[str], trace_id: Optional[str] = None) -> RequestContext:
    return RequestContext(trace_id=trace_id or generate_trace_id(), tenant_id=tenant_id, user=user)


def bind_user_to_context(user: AuthenticatedUser) -> RequestContext:
    current = get_request_context()
    context = RequestContext(trace_id=current.trace_id, tenant_id=user.tenant_id or current.tenant_id, user=user)
    set_request_context(context)
    return context
