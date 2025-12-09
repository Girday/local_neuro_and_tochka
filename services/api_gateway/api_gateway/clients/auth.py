from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status

from api_gateway.core.context import AuthenticatedUser


class AuthClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        introspection_url: Optional[str],
        audience: Optional[str],
        timeout: float,
        mock_mode: bool = False,
    ) -> None:
        self.http_client = http_client
        self.introspection_url = introspection_url
        self.audience = audience
        self.timeout = timeout
        self.mock_mode = mock_mode

    async def introspect(self, token: str) -> AuthenticatedUser:
        if self.mock_mode or not self.introspection_url:
            # minimal offline fallback
            return AuthenticatedUser(
                user_id="demo",
                username="demo",
                tenant_id="demo",
                roles=["admin"],
            )
        try:
            response = await self.http_client.post(
                self.introspection_url,
                data={"token": token, "audience": self.audience},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail="invalid token") from exc
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"auth provider unavailable: {exc}") from exc
        payload: Dict[str, Any] = response.json()
        if not payload.get("active", True):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token inactive")
        return AuthenticatedUser(
            user_id=str(payload.get("sub")),
            username=payload.get("username") or payload.get("preferred_username") or "user",
            tenant_id=str(payload.get("tenant_id") or payload.get("tenant") or "unknown"),
            roles=payload.get("roles") or [],
            display_name=payload.get("name"),
        )
