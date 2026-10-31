"""
Integration tests for GhostShell Flask web routes and API endpoints.
Tests status codes, JSON validation, payload limits, security headers, and error states.
"""

import json
from unittest.mock import patch, MagicMock
import pytest
from app import create_app
from config import TestingConfig


@pytest.fixture
def client():
    app = create_app(TestingConfig)
    with app.test_client() as client:
        yield client


def test_index_route(client):
    """GET / should render the main terminal template."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"GhostShell" in resp.data
    # Security headers check
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"


def test_css_route(client):
    """GET /css/style.css should serve the stylesheet directly."""
    resp = client.get("/css/style.css")
    assert resp.status_code == 200
    assert b"GhostShell" in resp.data or b"crt-overlay" in resp.data


def test_settings_route(client):
    """GET /settings should render the settings page."""
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert b"Settings" in resp.data or b"Ollama" in resp.data


def test_api_status_endpoint(client):
    """GET /api/status returns structured JSON status."""
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "status" in data
    assert "current_model" in data
    assert "installed_models" in data


def test_api_models_endpoint(client):
    """GET /api/models returns model catalog."""
    resp = client.get("/api/models")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "models" in data


def test_analyze_command_deterministic(client):
    """POST /api/analyze-command evaluates commands safely without executing them."""
    payload = {"command": "rm -rf /", "with_ai": False}
    resp = client.post(
        "/api/analyze-command",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["risk_level"] == "CRITICAL"
    assert data["is_safe"] is False
    assert len(data["findings"]) > 0


def test_analyze_command_harmless(client):
    """POST /api/analyze-command correctly evaluates harmless command."""
    payload = {"command": "echo 'spectral echoes'", "with_ai": False}
    resp = client.post(
        "/api/analyze-command",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["risk_level"] == "SAFE"
    assert data["is_safe"] is True


def test_analyze_command_empty_input(client):
    """POST /api/analyze-command rejects empty command input."""
    payload = {"command": "   "}
    resp = client.post(
        "/api/analyze-command",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "code" in data
    assert data["code"] == "VALIDATION_ERROR"


def test_chat_invalid_json(client):
    """POST /api/chat rejects malformed JSON."""
    resp = client.post(
        "/api/chat",
        data="this is not json",
        content_type="application/json"
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "INVALID_JSON"


def test_chat_empty_message(client):
    """POST /api/chat rejects empty message."""
    resp = client.post(
        "/api/chat",
        data=json.dumps({"message": ""}),
        content_type="application/json"
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["code"] == "VALIDATION_ERROR"


def test_chat_offline_fallback(client):
    """POST /api/chat returns friendly offline ghost response when Ollama is offline."""
    resp = client.post(
        "/api/chat",
        data=json.dumps({"message": "Hello ghost, are you there?"}),
        content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "dormant" in data["content"] or "Offline" in data["content"] or "Ghost" in data["content"]


def test_story_offline_sample(client):
    """POST /api/story returns pre-archived anomaly log when Ollama is offline."""
    payload = {
        "prompt": "The server room lights turn red",
        "length": "short",
        "intensity": "creepy",
        "setting": "deserted_server_room",
        "story_type": "incident_report"
    }
    resp = client.post(
        "/api/story",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "story" in data
    assert "HAUNTED ARCHIVES" in data["story"]


def test_switch_model_endpoint(client):
    """POST /api/settings/model updates current model configuration."""
    resp = client.post(
        "/api/settings/model",
        data=json.dumps({"model": "llama3.2:1b"}),
        content_type="application/json"
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["current_model"] == "llama3.2:1b"


def test_switch_model_invalid_name(client):
    """POST /api/settings/model rejects illegal characters."""
    resp = client.post(
        "/api/settings/model",
        data=json.dumps({"model": "rm -rf /; malicious"}),
        content_type="application/json"
    )
    assert resp.status_code == 400


def test_oversized_payload(client):
    """Requests exceeding MAX_CONTENT_LENGTH (64 KB) must be rejected with 413."""
    huge_data = "A" * (70 * 1024)
    resp = client.post(
        "/api/chat",
        data=json.dumps({"message": huge_data}),
        content_type="application/json"
    )
    assert resp.status_code == 413
    data = resp.get_json()
    assert data["code"] == "PAYLOAD_TOO_LARGE"
