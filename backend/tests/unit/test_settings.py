from pathlib import Path

from app.config import settings
import app.config as config


def test_get_settings_masks_api_key(client):
    old_key = settings.LLM_API_KEY
    try:
        settings.LLM_API_KEY = "sk-test-1234567890"
        res = client.get("/api/settings")
        assert res.status_code == 200
        data = res.json()
        assert data["has_api_key"] is True
        assert data["api_key_masked"] != "sk-test-1234567890"
        assert "llm_api_key" not in data
    finally:
        settings.LLM_API_KEY = old_key


def test_placeholder_api_key_is_not_configured(client):
    old_key = settings.LLM_API_KEY
    try:
        settings.LLM_API_KEY = "your-api-key-here"
        res = client.get("/api/settings")
        assert res.status_code == 200
        data = res.json()
        assert data["has_api_key"] is False
        assert data["api_key_masked"] == ""
    finally:
        settings.LLM_API_KEY = old_key


def test_update_settings_persists_and_updates_runtime(client, tmp_path, monkeypatch):
    env_path = Path(tmp_path) / ".env"
    monkeypatch.setattr(config, "USER_ENV_PATH", env_path)

    old_key = settings.LLM_API_KEY
    old_base = settings.LLM_BASE_URL
    old_model = settings.LLM_MODEL
    try:
        res = client.put("/api/settings", json={
            "llm_api_key": "sk-new-value",
            "llm_base_url": "https://example.test/v1",
            "llm_model": "test-model",
        })
        assert res.status_code == 200
        assert settings.LLM_API_KEY == "sk-new-value"
        assert settings.LLM_BASE_URL == "https://example.test/v1"
        assert settings.LLM_MODEL == "test-model"
        content = env_path.read_text(encoding="utf-8")
        assert "LLM_API_KEY=sk-new-value" in content
        assert "LLM_MODEL=test-model" in content
    finally:
        settings.LLM_API_KEY = old_key
        settings.LLM_BASE_URL = old_base
        settings.LLM_MODEL = old_model


def test_shutdown_testing_mode_does_not_exit(client):
    res = client.post("/api/shutdown")
    assert res.status_code == 200
    assert res.json()["ok"] is True
