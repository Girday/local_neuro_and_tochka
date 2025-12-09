from fastapi.testclient import TestClient

from safety_service.config import Settings, get_settings
from safety_service.main import app


def override_settings() -> Settings:
    return Settings(
        blocklist=["breach"],
        policy_mode="balanced",
        enable_pii_sanitize=True,
        default_policy_id="policy_test",
    )


def test_input_endpoint_returns_expected_payload() -> None:
    app.dependency_overrides[get_settings] = override_settings
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/internal/safety/input-check",
                json={
                    "user": {"user_id": "u", "tenant_id": "t"},
                    "query": "This is a secret +12345678901",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "transformed"
            assert data["policy_id"] == "policy_test"
    finally:
        app.dependency_overrides.clear()


def test_output_endpoint_blocks_blocklisted_answer() -> None:
    app.dependency_overrides[get_settings] = override_settings
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/internal/safety/output-check",
                json={
                    "user": {"user_id": "u", "tenant_id": "t"},
                    "query": "",
                    "answer": "Internal breach instructions",
                },
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "blocked"
    finally:
        app.dependency_overrides.clear()
