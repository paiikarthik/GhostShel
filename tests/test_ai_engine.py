"""
Unit and integration tests for GhostShell's local AI engine (Ollama interface).
Tests offline detection, timeout recovery, error handling, and prompt structures.
"""

import json
from unittest.mock import patch, MagicMock
import requests
import pytest
from ghostshell.ai_engine import OllamaAIEngine
from ghostshell.prompts import (
    build_chat_prompt,
    build_command_explanation_prompt,
    build_story_prompt
)


@pytest.fixture
def engine():
    return OllamaAIEngine(base_url="http://127.0.0.1:11434", model="qwen2.5:3b", timeout=2)


def test_ai_engine_offline_detection(engine):
    """When Ollama is not running, check_status should report available=False without raising an exception."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        status = engine.check_status()
        assert status["available"] is False
        assert "Cannot connect to Ollama" in status["error"]
        assert status["installed_models"] == []
        assert "https://ollama.com" in status["setup_guide"]


def test_ai_engine_ssrf_blocking():
    """Verify that external or malicious URLs are blocked by SSRF protection."""
    external_engine = OllamaAIEngine(base_url="http://169.254.169.254/metadata")
    status = external_engine.check_status()
    assert status["available"] is False
    assert "SSRF" in status["error"]


def test_ai_engine_online_with_models(engine):
    """Verify status reporting when Ollama responds with model list."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [
            {"name": "qwen2.5:3b", "size": 1900000000, "modified_at": "2026-10-01T00:00:00Z"},
            {"name": "llama3.2:1b", "size": 1300000000, "modified_at": "2026-10-02T00:00:00Z"}
        ]
    }
    with patch("requests.get", return_value=mock_resp):
        status = engine.check_status()
        assert status["available"] is True
        assert status["model_available"] is True
        assert len(status["installed_models"]) == 2
        assert status["error"] is None


def test_ai_engine_missing_model(engine):
    """Verify status when Ollama is running but requested model is not downloaded."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [
            {"name": "mistral:7b", "size": 4000000000}
        ]
    }
    with patch("requests.get", return_value=mock_resp):
        status = engine.check_status()
        assert status["available"] is True
        assert status["model_available"] is False
        assert "not in local Ollama storage" in status["error"]
        assert "ollama pull" in status["setup_guide"]


def test_ai_engine_chat_sync_offline(engine):
    """When offline, chat_sync should return a friendly diagnostic message without crashing."""
    with patch.object(engine, "check_status", return_value={"available": False, "error": "Offline"}):
        result = engine.generate_chat_sync([{"role": "user", "content": "hello"}])
        assert result["success"] is False
        assert "dormant" in result["content"]


def test_ai_engine_chat_sync_timeout(engine):
    """Verify timeout recovery in synchronous chat."""
    with patch.object(engine, "check_status", return_value={"available": True, "model_available": True}):
        with patch("requests.post", side_effect=requests.exceptions.Timeout("Request timed out")):
            result = engine.generate_chat_sync([{"role": "user", "content": "hello"}])
            assert result["success"] is False
            assert "Timed Out" in result["content"]


def test_ai_engine_chat_sync_success(engine):
    """Verify successful chat completion."""
    mock_post = MagicMock()
    mock_post.status_code = 200
    mock_post.json.return_value = {
        "message": {"role": "assistant", "content": "👻 Greetings, mortal engineer!"},
        "eval_count": 42
    }
    with patch.object(engine, "check_status", return_value={"available": True, "model_available": True}):
        with patch("requests.post", return_value=mock_post):
            result = engine.generate_chat_sync([{"role": "user", "content": "hello"}])
            assert result["success"] is True
            assert "Greetings" in result["content"]
            assert result["eval_count"] == 42


def test_ai_engine_streaming(engine):
    """Verify streaming generator chunks and completion."""
    fake_stream_lines = [
        json.dumps({"message": {"content": "👻 "}, "done": False}).encode("utf-8"),
        json.dumps({"message": {"content": "Boo!"}, "done": True}).encode("utf-8")
    ]
    mock_post = MagicMock()
    mock_post.status_code = 200
    mock_post.iter_lines.return_value = fake_stream_lines

    with patch.object(engine, "check_status", return_value={"available": True, "model_available": True}):
        with patch("requests.post", return_value=mock_post):
            generator = engine.generate_chat_stream([{"role": "user", "content": "spook me"}])
            chunks = list(generator)
            assert len(chunks) == 2
            parsed_1 = json.loads(chunks[0])
            parsed_2 = json.loads(chunks[1])
            assert parsed_1["content"] == "👻 "
            assert parsed_2["content"] == "Boo!"
            assert parsed_2["done"] is True


def test_prompt_construction_preserves_deterministic_findings():
    """Verify prompt explicitly contains deterministic findings and risk level."""
    analysis = {
        "risk_level": "CRITICAL",
        "platform": "linux",
        "findings": ["Root recursive deletion"],
        "explanation": "Destroys filesystem",
        "recommendation": "Do not run"
    }
    messages = build_command_explanation_prompt("rm -rf /", analysis)
    user_prompt = messages[1]["content"]
    assert "CRITICAL" in user_prompt
    assert "Root recursive deletion" in user_prompt
    assert "rm -rf /" in user_prompt


def test_story_prompt_parameters():
    """Verify story generation prompt incorporates user choices."""
    params = {
        "prompt": "The server room lights turn red",
        "length": "short",
        "intensity": "terrifying",
        "setting": "air_gapped_bunker",
        "story_type": "incident_report"
    }
    messages = build_story_prompt(params)
    prompt_str = messages[1]["content"]
    assert "Cold War" in prompt_str
    assert "Incident Report" in prompt_str
    assert "The server room lights turn red" in prompt_str
