from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException, status

from api_gateway.clients.base import DownstreamClient


class DocumentClient(DownstreamClient):
    async def list_documents(self, params: Dict[str, Any]) -> list[dict[str, Any]]:
        if self.mock_mode:
            return []
        try:
            response = await self.get("/internal/documents/list", params=params)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"documents list error: {exc}") from exc
        return response.json()

    async def get_document(self, doc_id: str) -> dict[str, Any]:
        if self.mock_mode:
            return {"doc_id": doc_id, "status": "unknown"}
        try:
            response = await self.get(f"/internal/documents/{doc_id}")
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"document fetch error: {exc}") from exc
        return response.json()
