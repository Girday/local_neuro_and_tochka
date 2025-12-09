from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException

from api_gateway.core.context import get_request_context


class DownstreamClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: Optional[str],
        service_name: str,
        mock_mode: bool = False,
    ) -> None:
        self.http_client = http_client
        self.base_url = base_url.rstrip("/") + "/" if base_url else None
        self.service_name = service_name
        self.mock_mode = mock_mode

    def _require_base_url(self) -> str:
        if not self.base_url:
            raise HTTPException(
                status_code=503,
                detail=f"{self.service_name} endpoint is not configured",
            )
        return self.base_url

    def _build_url(self, path: str) -> str:
        base = self._require_base_url()
        path = path.lstrip("/")
        return urljoin(base, path)

    def _build_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        ctx = get_request_context()
        headers: Dict[str, str] = {"X-Request-ID": ctx.trace_id}
        if ctx.tenant_id:
            headers["X-Tenant-ID"] = ctx.tenant_id
        if ctx.user:
            headers["X-User-ID"] = ctx.user.user_id
            if ctx.user.roles:
                headers["X-User-Roles"] = ",".join(ctx.user.roles)
        if extra:
            headers.update(extra)
        return headers

    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - http layer
            detail = exc.response.text or exc.response.reason_phrase
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
        return response

    async def post_json(
        self, path: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        url = self._build_url(path)
        response = await self.http_client.post(url, json=payload, headers=self._build_headers(headers))
        return self._handle_response(response)

    async def get(
        self, path: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        url = self._build_url(path)
        response = await self.http_client.get(url, params=params, headers=self._build_headers(headers))
        return self._handle_response(response)

    async def post_multipart(
        self, path: str, data: Dict[str, Any], files: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        url = self._build_url(path)
        response = await self.http_client.post(
            url,
            data=data,
            files=files,
            headers=self._build_headers(headers),
        )
        return self._handle_response(response)
