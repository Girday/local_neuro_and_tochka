from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException, status

from api_gateway.clients.base import DownstreamClient


class SafetyClient(DownstreamClient):
    async def check_input(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.mock_mode:
            return {"status": "allowed", "reason": "mock"}
        try:
            response = await self.post_json("/internal/safety/input-check", payload)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - network guard
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"safety check failed: {exc}") from exc
        return response.json()
