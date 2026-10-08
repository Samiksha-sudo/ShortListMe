import httpx
import pytest

from app.core.config import settings
from app.services import llm


def reply(text):
    return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_max_retries", 2)
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)


def fake(monkeypatch, responses):
    calls = []

    def post(url, json, headers, timeout):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        item = responses[min(len(calls), len(responses)) - 1]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(llm.httpx, "post", post)
    return calls


def test_generate_returns_text_and_sends_key_in_header_not_url(monkeypatch):
    calls = fake(monkeypatch, [reply("  hello  ")])
    assert llm.generate("hi", system="be brief") == "hello"
    call = calls[0]
    assert call["headers"]["x-goog-api-key"] == "test-key"
    assert "test-key" not in call["url"]
    assert call["json"]["systemInstruction"]["parts"][0]["text"] == "be brief"
    assert call["json"]["contents"][0]["parts"][0]["text"] == "hi"


def test_generate_json_parses_and_requests_json_mode(monkeypatch):
    calls = fake(monkeypatch, [reply('{"a": 1}')])
    assert llm.generate_json("x") == {"a": 1}
    assert calls[0]["json"]["generationConfig"]["responseMimeType"] == "application/json"


def test_malformed_json_raises(monkeypatch):
    fake(monkeypatch, [reply("not json")])
    with pytest.raises(llm.LLMError, match="malformed"):
        llm.generate_json("x")


def test_retries_transient_errors_then_succeeds(monkeypatch):
    calls = fake(monkeypatch, [httpx.Response(503), httpx.ConnectTimeout("slow"), reply("ok")])
    assert llm.generate("x") == "ok"
    assert len(calls) == 3


def test_gives_up_after_max_retries(monkeypatch):
    calls = fake(monkeypatch, [httpx.Response(429)])
    with pytest.raises(llm.LLMError, match="quota is used up"):
        llm.generate("x")
    assert len(calls) == 3


def test_bad_key_is_not_retried(monkeypatch):
    calls = fake(monkeypatch, [httpx.Response(403)])
    with pytest.raises(llm.LLMError, match="API key"):
        llm.generate("x")
    assert len(calls) == 1


def test_blocked_response_without_content_raises(monkeypatch):
    fake(monkeypatch, [httpx.Response(200, json={"candidates": [{"finishReason": "SAFETY"}]})])
    with pytest.raises(llm.LLMError, match="no answer"):
        llm.generate("x")


def test_missing_key_fails_without_calling_out(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    calls = fake(monkeypatch, [reply("x")])
    with pytest.raises(llm.LLMError, match="not configured"):
        llm.generate("x")
    assert calls == []


def test_unknown_provider_rejected(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "other")
    with pytest.raises(llm.LLMError, match="Unsupported"):
        llm.generate("x")


def openai_reply(text):
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}],
                                     "usage": {"prompt_tokens": 3, "completion_tokens": 2}})


def use_openai(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")


def test_openai_sends_bearer_key_and_system_message(monkeypatch):
    use_openai(monkeypatch)
    calls = fake(monkeypatch, [openai_reply(" hello ")])
    assert llm.generate("hi", system="be brief") == "hello"
    call = calls[0]
    assert call["url"] == llm.OPENAI_URL
    assert call["headers"]["Authorization"] == "Bearer sk-test" and "sk-test" not in call["url"]
    assert call["json"]["messages"] == [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}]


def test_openai_json_mode_parses_reply(monkeypatch):
    use_openai(monkeypatch)
    calls = fake(monkeypatch, [openai_reply('{"a": 1}')])
    assert llm.generate_json("x") == {"a": 1}
    assert calls[0]["json"]["response_format"] == {"type": "json_object"}
    assert "JSON" in calls[0]["json"]["messages"][0]["content"]


def test_openai_missing_key_names_the_variable(monkeypatch):
    use_openai(monkeypatch)
    monkeypatch.setattr(settings, "openai_api_key", "")
    with pytest.raises(llm.LLMError, match="OPENAI_API_KEY"):
        llm.generate("x")
