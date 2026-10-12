"""One HTTP call; successful but malformed responses are terminal retained data."""

from __future__ import annotations

import http.client
import json
import socket
import ssl
from urllib import error, request

from exception_pilot.provider import ENDPOINT, NoRedirect, ProviderError, credential, normalize as normalize_openai


def normalize(raw, config, mode):
    if isinstance(raw, dict):
        result = normalize_openai(raw)
    else:
        result = {"text": "", "complete": False, "finish_reason": "invalid_response_shape",
                  "model": None, "usage": {}, "response_id": None, "raw_response": raw}
    identity = "match" if result["model"] == config["model"] else "missing" if result["model"] is None else "mismatch"
    result["model_identity"] = "simulated" if mode == "mock" else identity
    if mode == "live" and identity != "match":
        result.update(complete=False, finish_reason="model_" + identity)
    return result


def complete(config, payload):
    req = request.Request(ENDPOINT, data=json.dumps(payload, allow_nan=False).encode(), method="POST",
                          headers={"Authorization": "Bearer " + credential(config), "Content-Type": "application/json"})
    try:
        with request.build_opener(NoRedirect()).open(req, timeout=config["timeout_seconds"]) as response:
            body = response.read()
    except error.HTTPError as exc:
        code = exc.code
        exc.close()
        raise ProviderError(f"HTTP {code}", status_code=code) from None
    except (error.URLError, TimeoutError, socket.timeout, ssl.SSLError, http.client.HTTPException, OSError) as exc:
        raise ProviderError(type(exc).__name__) from None
    try:
        return json.loads(body)
    except (ValueError, UnicodeError):
        # Successful HTTP response: retain instead of calling it retryable.
        return {"unparseable_http_body_utf8": body.decode("utf-8", errors="replace")}
