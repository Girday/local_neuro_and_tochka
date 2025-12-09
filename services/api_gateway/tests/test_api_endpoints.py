from __future__ import annotations

from typing import Dict, List, Tuple

import pytest
from fastapi.testclient import TestClient

from api_gateway.core.context import AuthenticatedUser
from api_gateway.dependencies import (
    get_current_user,
    get_document_client,
    get_ingestion_client,
    get_orchestrator_client,
    get_rate_limiter,
    get_safety_client,
)
from api_gateway.main import app


class DummySafetyClient:
    def __init__(self) -> None:
        self.payloads: List[Dict] = []

    async def check_input(self, payload: Dict) -> Dict:
        self.payloads.append(payload)
        return {"status": "allowed", "reason": "ok"}


class DummyOrchestratorClient:
    def __init__(self) -> None:
        self.payloads: List[Dict] = []

    async def query(self, payload: Dict) -> Dict:
        self.payloads.append(payload)
        return {
            "answer": "Mocked response",
            "sources": [
                {
                    "doc_id": "doc_1",
                    "doc_title": "Guide",
                }
            ],
            "meta": {"latency_ms": 42, "trace_id": payload["trace_id"]},
        }


class DummyDocumentClient:
    def __init__(self) -> None:
        self.list_params: Dict | None = None
        self.requested_doc_id: str | None = None
        self._documents = [
            {
                "doc_id": "doc_1",
                "name": "Dummy",
                "status": "indexed",
                "product": "Orion",
                "version": "1.0",
                "tags": ["tag"],
            }
        ]

    async def list_documents(self, params: Dict) -> List[Dict]:
        self.list_params = params
        return self._documents

    async def get_document(self, doc_id: str) -> Dict:
        self.requested_doc_id = doc_id
        return {
            **self._documents[0],
            "sections": [],
        }


class DummyIngestionClient:
    def __init__(self) -> None:
        self.last_data: Dict | None = None
        self.last_files: Dict | None = None

    async def enqueue(self, data: Dict, files: Dict) -> Dict:
        self.last_data = data
        self.last_files = files
        return {"doc_id": "doc_upload", "status": "uploaded"}


class DummyRateLimiter:
    def __init__(self) -> None:
        self.keys: List[str] = []

    async def check(self, key: str) -> None:
        self.keys.append(key)


@pytest.fixture
def client_with_stubs() -> Tuple[TestClient, Dict[str, object]]:
    user = AuthenticatedUser(
        user_id="user-123",
        username="demo",
        tenant_id="tenant-456",
        roles=["admin"],
    )
    stubs = {
        "user": user,
        "safety": DummySafetyClient(),
        "orchestrator": DummyOrchestratorClient(),
        "documents": DummyDocumentClient(),
        "ingestion": DummyIngestionClient(),
        "rate_limiter": DummyRateLimiter(),
    }

    async def override_current_user():
        return stubs["user"]

    def override_safety_client():
        return stubs["safety"]

    def override_orchestrator_client():
        return stubs["orchestrator"]

    def override_document_client():
        return stubs["documents"]

    def override_ingestion_client():
        return stubs["ingestion"]

    def override_rate_limiter():
        return stubs["rate_limiter"]

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_safety_client] = override_safety_client
    app.dependency_overrides[get_orchestrator_client] = override_orchestrator_client
    app.dependency_overrides[get_document_client] = override_document_client
    app.dependency_overrides[get_ingestion_client] = override_ingestion_client
    app.dependency_overrides[get_rate_limiter] = override_rate_limiter

    with TestClient(app) as test_client:
        yield test_client, stubs

    app.dependency_overrides.clear()


def test_assistant_query_flow(client_with_stubs: Tuple[TestClient, Dict[str, object]]) -> None:
    client, stubs = client_with_stubs
    response = client.post(
        "/api/v1/assistant/query",
        json={"query": "Привет", "language": "ru"},
        headers={"Authorization": "Bearer dummy"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Mocked response"
    assert data["meta"]["trace_id"]
    assert stubs["safety"].payloads[-1]["query"] == "Привет"
    assert any(key.startswith("assistant:") for key in stubs["rate_limiter"].keys)


def test_document_routes(client_with_stubs: Tuple[TestClient, Dict[str, object]]) -> None:
    client, stubs = client_with_stubs
    list_response = client.get("/api/v1/documents", headers={"Authorization": "Bearer demo"})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert stubs["documents"].list_params == {"tenant_id": "tenant-456"}

    detail_response = client.get("/api/v1/documents/doc_1", headers={"Authorization": "Bearer demo"})
    assert detail_response.status_code == 200
    assert stubs["documents"].requested_doc_id == "doc_1"

    upload_response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("dummy.txt", b"payload", "text/plain")},
        data={"product": "Orion", "version": "1.0"},
        headers={"Authorization": "Bearer demo"},
    )
    assert upload_response.status_code == 202
    assert stubs["ingestion"].last_data == {"tenant_id": "tenant-456", "product": "Orion", "version": "1.0"}
    assert "file" in stubs["ingestion"].last_files
    # All doc endpoints should hit rate limiter under different prefixes
    assert any(key.startswith("doc-") for key in stubs["rate_limiter"].keys)
