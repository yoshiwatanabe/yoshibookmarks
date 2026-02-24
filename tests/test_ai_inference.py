"""Unit tests for AI inference provider handling and parsing."""

import pytest

from yoshibookmark.core.ai_inference import MultiProviderInferenceService
from yoshibookmark.models.config import AppConfig


class _FakeResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload
        self.text = ""

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, calls):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, endpoint, headers=None, json=None):
        self.calls.append({"endpoint": endpoint, "headers": headers, "json": json})
        return _FakeResponse(
            {"choices": [{"message": {"content": "{\"title\":\"ok\",\"keywords\":[]}"}}]}
        )


def _service_for_openai():
    config = AppConfig(
        storage_locations=[],
        openai_enabled=True,
        openai_endpoint="https://api.openai.com/v1/chat/completions",
        openai_model="gpt-5-mini",
        openai_api_keys=["test-key"],
        azure_openai_enabled=False,
        anthropic_enabled=False,
        gemini_enabled=False,
        agent_providers=["openai"],
    )
    return MultiProviderInferenceService(config)


class TestAiInference:
    @pytest.mark.asyncio
    async def test_openai_payload_omits_temperature(self, monkeypatch):
        service = _service_for_openai()
        calls = []

        monkeypatch.setattr(
            "yoshibookmark.core.ai_inference.httpx.AsyncClient",
            lambda timeout: _FakeAsyncClient(calls),
        )

        await service._generate_text("openai", "test prompt")
        assert len(calls) == 1
        assert "temperature" not in calls[0]["json"]

    def test_parse_json_payload_with_wrapped_text(self):
        service = _service_for_openai()
        text = (
            "<think>analysis here</think>\n"
            '{"title":"cmdai","keywords":["github"],"tags":[],"summary":"ok","confidence":0.8}\n'
            "</final>"
        )
        parsed = service._parse_json_payload(text)
        assert parsed["title"] == "cmdai"
        assert parsed["confidence"] == 0.8

    def test_parse_json_payload_with_codeblock_and_trailing_text(self):
        service = _service_for_openai()
        text = (
            "```json\n"
            '{"title":"repo","keywords":[],"tags":[],"summary":"x","confidence":0.6}\n'
            "```\n"
            "extra trailing text"
        )
        parsed = service._parse_json_payload(text)
        assert parsed["title"] == "repo"
