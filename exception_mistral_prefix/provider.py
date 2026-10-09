"""One Mistral chat-completions HTTP request, with no SDK or hidden retries."""

from __future__ import annotations

import http.client
import json
import socket
import ssl
from urllib import error, request

from exception_pilot.provider import NoRedirect, ProviderError, credential

from .core import ENDPOINT


def _content_text(content):
    if isinstance(content, str):
        return content, None, "string"
    if isinstance(content, list):
        if not all(isinstance(chunk, dict) and set(chunk) == {"type", "text"}
                   and chunk["type"] == "text" and isinstance(chunk["text"], str)
                   for chunk in content):
            return "", "nontext_or_malformed_content_chunk", "invalid_chunks"
        return "".join(chunk["text"] for chunk in content), None, "text_chunks"
    return "", "empty_or_nonstring_content", "invalid"


def normalize(raw, observed_model=None):
    """Keep the full provider object and reject invisible reasoning or identity drift."""
    payload = raw if isinstance(raw, dict) else {}
    choices = payload.get("choices")
    choice_valid = isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict)
    choice = choices[0] if choice_valid else {}
    message = choice.get("message")
    message = message if isinstance(message, dict) else {}
    text, content_error, content_form = _content_text(message.get("content"))
    reasoning = message.get("reasoning_content")
    model = payload.get("model")
    raw_usage = payload.get("usage")
    usage = raw_usage if isinstance(raw_usage, dict) else {}
    finish = choice.get("finish_reason", "missing")
    invalid = None
    if not isinstance(raw, dict) or not choice_valid:
        invalid = "malformed_provider_response"
    elif payload.get("error"):
        invalid = "provider_error_response"
    elif not isinstance(model, str) or not model.strip():
        invalid = "missing_response_model"
    elif observed_model is not None and model != observed_model:
        invalid = "response_model_changed"
    elif message.get("role") != "assistant":
        invalid = "assistant_message_required"
    elif content_error is not None:
        invalid = content_error
    elif not text.strip():
        invalid = "empty_or_nonstring_content"
    elif reasoning not in (None, ""):
        invalid = "unexpected_reasoning_content"
    elif any(message.get(key) for key in ("refusal", "tool_calls", "function_call")):
        invalid = "refusal_or_tool_response"
    elif finish != "stop":
        invalid = "incomplete_finish_reason"
    elif raw_usage is not None and not isinstance(raw_usage, dict):
        invalid = "malformed_usage"
    elif any(value is not None and (type(value) is not int or value < 0)
             for key, value in usage.items()
             if key in ("prompt_tokens", "completion_tokens", "total_tokens")):
        invalid = "malformed_usage"
    # Keep known counts safe for audited summary arithmetic. The unchanged raw
    # object above remains available even for malformed telemetry.
    safe_usage = {key: value for key, value in usage.items()
                  if key not in ("prompt_tokens", "completion_tokens", "total_tokens")
                  or value is None or (type(value) is int and value >= 0)}
    return {"text": text if isinstance(text, str) else "", "complete": invalid is None,
            "finish_reason": finish, "provider_invalid_reason": invalid, "model": model,
            "content_form": content_form,
            "reasoning_content": reasoning, "system_fingerprint": payload.get("system_fingerprint"),
            "usage": safe_usage, "response_id": payload.get("id"), "raw_response": raw}


def _reject_constant(value):
    raise ValueError("Nonstandard JSON constant")


def complete(config, payload):
    if config["endpoint"] != ENDPOINT:
        raise ValueError("The Mistral prefix screen's endpoint is fixed")
    key = credential(config)
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
    req = request.Request(ENDPOINT, data=body, method="POST", headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with request.build_opener(NoRedirect()).open(req, timeout=config["timeout_seconds"]) as result:
            response_bytes = result.read()
    except error.HTTPError as exc:
        code = exc.code
        exc.close()
        raise ProviderError(f"HTTP {code}", status_code=code) from None
    except (error.URLError, TimeoutError, socket.timeout, ssl.SSLError,
            http.client.HTTPException, OSError) as exc:
        raise ProviderError(type(exc).__name__) from None
    # A returned malformed body is retained as a terminal response, not turned
    # into a retryable error. Never print it or an Authorization header.
    try:
        raw = json.loads(response_bytes.decode("utf-8"), parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        raw = {"_invalid_json_body": response_bytes.decode("utf-8", errors="replace")}
    return normalize(raw)
