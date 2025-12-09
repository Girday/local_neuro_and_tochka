from __future__ import annotations

import secrets
from typing import Any, Dict

from fastapi import HTTPException, status

from api_gateway.clients.base import DownstreamClient


class IngestionClient(DownstreamClient):
    async def enqueue(self, data: Dict[str, Any], files: Dict[str, Any]) -> Dict[str, Any]:
        if self.mock_mode:
            return {"doc_id": f"mock_{secrets.token_hex(4)}", "status": "uploaded"}
        try:
            response = await self.post_multipart("/internal/ingestion/enqueue", data=data, files=files)
        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"ingestion error: {exc}") from exc
        return response.json()
