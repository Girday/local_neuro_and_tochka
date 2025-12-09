from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api_gateway.clients.auth import AuthClient
from api_gateway.clients.documents import DocumentClient
from api_gateway.clients.ingestion import IngestionClient
from api_gateway.clients.orchestrator import OrchestratorClient
from api_gateway.clients.safety import SafetyClient
from api_gateway.config import Settings, get_settings
from api_gateway.core.context import AuthenticatedUser, bind_user_to_context
from api_gateway.core.rate_limit import RateLimiter

bearer_scheme = HTTPBearer(auto_error=False)


def get_http_client(request: Request):
    http_client = getattr(request.app.state, "http_client", None)
    if http_client is None:
        raise RuntimeError("HTTP client is not initialized")
    return http_client


def get_auth_client(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AuthClient:
    http_client = get_http_client(request)
    introspection_url = str(settings.auth_introspection_url) if settings.auth_introspection_url else None
    return AuthClient(
        http_client=http_client,
        introspection_url=introspection_url,
        audience=settings.auth_audience,
        timeout=settings.auth_timeout_seconds,
        mock_mode=settings.mock_mode,
    )


async def get_bearer_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing Authorization header")
    return credentials.credentials


async def get_current_user(
    request: Request,
    token: str = Depends(get_bearer_token),
    auth_client: AuthClient = Depends(get_auth_client),
) -> AuthenticatedUser:
    user = await auth_client.introspect(token)
    bind_user_to_context(user)
    request.state.tenant_id = user.tenant_id
    return user


def get_safety_client(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> SafetyClient:
    http_client = get_http_client(request)
    base_url = str(settings.safety_base_url) if settings.safety_base_url else None
    return SafetyClient(http_client, base_url, service_name="safety", mock_mode=settings.mock_mode)


def get_orchestrator_client(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> OrchestratorClient:
    http_client = get_http_client(request)
    base_url = str(settings.orchestrator_base_url) if settings.orchestrator_base_url else None
    return OrchestratorClient(http_client, base_url, service_name="orchestrator", mock_mode=settings.mock_mode)


def get_ingestion_client(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> IngestionClient:
    http_client = get_http_client(request)
    base_url = str(settings.ingestion_base_url) if settings.ingestion_base_url else None
    return IngestionClient(http_client, base_url, service_name="ingestion", mock_mode=settings.mock_mode)


def get_document_client(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> DocumentClient:
    http_client = get_http_client(request)
    base_url = str(settings.documents_base_url) if settings.documents_base_url else None
    return DocumentClient(http_client, base_url, service_name="documents", mock_mode=settings.mock_mode)


@lru_cache(maxsize=1)
def _get_rate_limiter(limit: int) -> RateLimiter:
    return RateLimiter(limit)


def get_rate_limiter(settings: Settings = Depends(get_settings)) -> RateLimiter:
    return _get_rate_limiter(settings.rate_limit_per_minute)
