"""One stateless HTTP request, no SDK dependency and no hidden retries."""

from __future__ import annotations

import http.client
import json
import os
import socket
import ssl
from urllib import request, error

ENDPOINT = "https://api.openai.com/v1/chat/completions"


class ProviderError(RuntimeError):
    """Safe error message: never includes credentials, headers or provider body."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def credential(config):
    key = os.environ.get(config["api_key_env"], "")
    if not key:
        raise ProviderError(f"Missing {config['api_key_env']}; set it in your terminal")
    if not key.isascii() or any(ord(c) <= 32 or ord(c) == 127 for c in key):
        raise ProviderError("API key contains whitespace/non-ASCII characters; re-enter it")
    return key


def normalize(raw):
    choices = raw.get("choices")
    valid = isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict)
    choice = choices[0] if valid else {}
    message = choice.get("message", {})
    if not isinstance(message, dict):
        message = {}
    text = message.get("content", "")
    finish = choice.get("finish_reason", "missing")
    complete = (valid and finish == "stop" and message.get("role") == "assistant"
                and isinstance(text, str) and bool(text.strip()) and not raw.get("error")
                and not any(message.get(k) for k in ("refusal", "tool_calls", "function_call")))
    return {"text": text if isinstance(text, str) else "", "complete": bool(complete),
            "finish_reason": finish, "model": raw.get("model"), "usage": raw.get("usage", {}),
            "response_id": raw.get("id"), "raw_response": raw}


def complete(config, payload):
    key = credential(config)
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
    req = request.Request(ENDPOINT, data=body, method="POST", headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with request.build_opener(NoRedirect()).open(req, timeout=config["timeout_seconds"]) as r:
            raw = json.load(r)
    except error.HTTPError as exc:
        code = exc.code
        exc.close()
        raise ProviderError(f"HTTP {code}", status_code=code) from None
    except (error.URLError, TimeoutError, socket.timeout, ssl.SSLError,
            http.client.HTTPException, OSError) as exc:
        raise ProviderError(type(exc).__name__) from None
    except (ValueError, UnicodeError):
        raise ProviderError("InvalidJSONResponse") from None
    if not isinstance(raw, dict):
        raise ProviderError("InvalidResponseShape")
    result = normalize(raw)
    if result["model"] != config["model"]:
        result.update(complete=False, finish_reason="model_mismatch")
    return result
