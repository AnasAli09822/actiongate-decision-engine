from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["version"] == "2.0.0"


def test_home_page_is_served():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "ActionGate" in response.text


def test_scenarios_and_decision_endpoint_end_to_end():
    with TestClient(app) as client:
        scenarios = client.get("/api/scenarios").json()
        assert len(scenarios) >= 6
        response = client.post("/api/decisions/evaluate", json=scenarios[0]["request"])
        assert response.status_code == 200
        body = response.json()
        assert body["decision"] == scenarios[0]["expected_decision"]
        assert "confidence" in body
        assert "risk_score" in body
        assert "evidence_used" in body
        assert "missing_information" in body
        assert "reversibility" in body
        audit = client.get(f"/api/decisions/{body['decision_id']}/audit")
        assert audit.status_code == 200
        assert audit.json()["chain_valid"] is True


def test_invalid_extra_fields_are_rejected():
    with TestClient(app) as client:
        payload = client.get("/api/scenarios").json()[0]["request"]
        payload["unexpected"] = "field"
        response = client.post("/api/decisions/evaluate", json=payload)
        assert response.status_code == 422


def test_unknown_decision_audit_returns_404():
    with TestClient(app) as client:
        response = client.get("/api/decisions/dec_does_not_exist/audit")
        assert response.status_code == 404
