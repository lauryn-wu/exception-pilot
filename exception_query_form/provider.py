"""Stateless transport; returned malformed bodies are data, never retryable."""
import http.client
import json
import socket
import ssl
from urllib import error, request

from exception_pilot.provider import ENDPOINT, NoRedirect, ProviderError, credential
from exception_mistral_prefix_v2 import provider as mistral


def normalize(raw, config, mode):
    # The Mistral normalizer also accepts standard OpenAI chat completions and
    # preserves malformed bodies, telemetry, finish reasons and refusals.
    result = mistral.normalize(raw)
    expected = "MOCK-NOT-A-MODEL" if mode == "mock" else config["model"]
    observed = result["model"]
    result["model_mismatch"] = observed is not None and observed != expected
    if result["model_mismatch"]:
        result.update(complete=False, provider_invalid_reason="model_mismatch")
    return result


def _reject_constant(value):
    raise ValueError("Nonstandard JSON constant")


def complete(config, payload):
    if config["provider"] == "mistral":
        return normalize(mistral.complete(config, payload)["raw_response"], config, "live")
    key = credential(config)
    req = request.Request(ENDPOINT, data=json.dumps(payload, ensure_ascii=False, allow_nan=False).encode(),
                          method="POST", headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with request.build_opener(NoRedirect()).open(req, timeout=config["timeout_seconds"]) as response:
            body = response.read()
    except error.HTTPError as exc:
        status = exc.code
        exc.close()
        raise ProviderError(f"HTTP {status}", status_code=status) from None
    except (error.URLError, TimeoutError, socket.timeout, ssl.SSLError, http.client.HTTPException, OSError) as exc:
        raise ProviderError(type(exc).__name__) from None
    try:
        raw = json.loads(body.decode("utf-8"), parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        raw = {"_invalid_json_body": body.decode("utf-8", errors="replace")}
    return normalize(raw, config, "live")
