import json
import logging
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)
BAD_JSON_RETRIES = 2

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
RETRY_STATUSES = {429, 500, 502, 503, 504}
PROVIDERS = ("gemini", "openai")


class LLMError(Exception):
    """The model could not give a usable answer; the message is safe to show to users."""


def _model() -> str:
    return settings.openai_model if settings.llm_provider == "openai" else settings.gemini_model


def _post(url: str, payload: dict, headers: dict) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(settings.llm_max_retries + 1):
        if attempt:
            time.sleep(min(2 ** attempt, 8))
        try:
            res = httpx.post(url, json=payload, headers=headers, timeout=settings.llm_timeout_seconds)
        except httpx.HTTPError as exc:
            last = exc
            logger.warning("llm request failed (attempt %d): %s: %s", attempt + 1, type(exc).__name__, exc)
            continue
        if res.status_code in RETRY_STATUSES:
            last = LLMError("The AI service's quota is used up. Try again later or switch model." if res.status_code == 429
                            else f"The AI service is busy (HTTP {res.status_code}).")
            logger.warning("llm request failed (attempt %d): HTTP %d %s", attempt + 1, res.status_code, res.text[:200])
            continue
        return res
    if isinstance(last, LLMError):  # the last attempt got an answer, just not a usable one
        raise last
    if isinstance(last, httpx.TimeoutException):
        raise LLMError("The AI service took too long to answer. Please try again.") from last
    detail = f" ({type(last).__name__})" if last else ""
    raise LLMError(f"The AI service did not respond{detail}. Please try again.") from last


def _text(res: httpx.Response) -> str:
    if res.status_code in (400, 401, 403):
        raise LLMError("The AI service rejected the request. Check the API key and model name.")
    if res.status_code != 200:
        raise LLMError(f"The AI service returned an error (HTTP {res.status_code}).")
    try:
        if settings.llm_provider == "openai":
            return (res.json()["choices"][0]["message"]["content"] or "").strip()
        parts = res.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        # Blocked or empty candidates have no content.
        raise LLMError("The AI service returned no answer.") from exc


def _log_usage(res: httpx.Response, started: float) -> None:
    usage = {}
    try:
        usage = res.json().get("usage" if settings.llm_provider == "openai" else "usageMetadata", {})
    except ValueError:
        pass
    if settings.llm_provider == "openai":
        prompt_tokens, output_tokens = usage.get("prompt_tokens"), usage.get("completion_tokens")
    else:
        prompt_tokens, output_tokens = usage.get("promptTokenCount"), usage.get("candidatesTokenCount")
    logger.info(
        "llm call provider=%s model=%s latency_ms=%d prompt_tokens=%s output_tokens=%s",
        settings.llm_provider, _model(), (time.perf_counter() - started) * 1000, prompt_tokens, output_tokens,
    )


def _send(prompt: str, system: str | None, temperature: float, json_mode: bool) -> httpx.Response:
    if settings.llm_provider == "openai":
        # OpenAI's JSON mode requires the word "JSON" to appear in the messages.
        sys_text = system or ""
        if json_mode:
            sys_text = (sys_text + "\n\nReply with a single valid JSON object.").strip()
        messages = ([{"role": "system", "content": sys_text}] if sys_text else []) + [{"role": "user", "content": prompt}]
        payload: dict = {"model": settings.openai_model, "messages": messages, "temperature": temperature}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        return _post(OPENAI_URL, payload, {"Authorization": f"Bearer {settings.openai_api_key}"})
    config: dict = {"temperature": temperature}
    if json_mode:
        config["responseMimeType"] = "application/json"
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": config}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    return _post(GEMINI_URL.format(model=settings.gemini_model), payload,
                 {"x-goog-api-key": settings.gemini_api_key})


def _request(prompt: str, system: str | None, temperature: float, json_mode: bool = False) -> str:
    if settings.llm_provider not in PROVIDERS:
        raise LLMError(f"Unsupported LLM provider: {settings.llm_provider}.")
    key_name = f"{settings.llm_provider}_api_key"
    if not getattr(settings, key_name):
        raise LLMError(f"The AI service is not configured ({key_name.upper()} is empty).")
    started = time.perf_counter()
    res = _send(prompt, system, temperature, json_mode)
    _log_usage(res, started)
    return _text(res)


def generate(prompt: str, system: str | None = None, temperature: float = 0.2) -> str:
    """Plain-text completion."""
    return _request(prompt, system, temperature)


def generate_json(prompt: str, system: str | None = None, temperature: float = 0.0) -> dict | list:
    """Completion constrained to JSON and parsed; raises LLMError if the reply isn't valid JSON."""
    raw = _request(prompt, system, temperature, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError("The AI service returned a malformed answer.") from exc


def generate_model(prompt: str, schema: type[T], system: str | None = None, temperature: float = 0.0) -> T:
    """Completion validated against a Pydantic model; bad JSON or the wrong shape is retried twice."""
    problem = ""
    for attempt in range(BAD_JSON_RETRIES + 1):
        note = f"\n\nYour previous answer was invalid ({problem}). Reply with valid JSON only." if problem else ""
        raw = _request(prompt + note, system, temperature, json_mode=True)
        try:
            return schema.model_validate_json(raw)
        except ValidationError as exc:
            problem = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:3])
            logger.warning("llm answer failed validation (attempt %d): %s", attempt + 1, problem)
    raise LLMError("The AI service returned a malformed answer.")
