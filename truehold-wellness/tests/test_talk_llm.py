import json

from wellness_agent.knowledge.talk import DEFAULT_LLM_MODEL, _chat, configured_llm_model


def test_default_llm_model_is_current_xai_chat_slug():
    # https://docs.x.ai/developers/models — "Chat: Grok 4.7"
    assert DEFAULT_LLM_MODEL == "grok-4.7"
    assert configured_llm_model() == "grok-4.7"


def test_configured_llm_model_honors_override(monkeypatch):
    monkeypatch.setenv("WELLNESS_LLM_MODEL", "grok-4.6")
    assert configured_llm_model() == "grok-4.6"


def test_chat_posts_default_grok_47(monkeypatch):
    captured = {}

    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "Hello from the floor."}}]}

    class _FakeClient:
        def __init__(self, timeout=20):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["json"] = json
            return _FakeResponse()

    monkeypatch.setenv("WELLNESS_LLM_API_KEY", "test-key")
    monkeypatch.delenv("WELLNESS_LLM_MODEL", raising=False)
    monkeypatch.setattr("wellness_agent.knowledge.talk.httpx.Client", _FakeClient)
    assert _chat("sys", "hi") == "Hello from the floor."
    assert captured["url"] == "https://api.x.ai/v1/chat/completions"
    assert captured["json"]["model"] == "grok-4.7"
    assert "grok-4-1-fast" not in json.dumps(captured["json"])
