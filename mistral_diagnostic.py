"""Resume one journaled Mistral request with sanitized HTTP error details.

This optional transport observer lives outside the frozen experiment packages.
It delegates requests, successful responses, scoring, and gates to the original
runner. It neither changes a saved plan nor makes unjournaled diagnostic calls.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from urllib.error import HTTPError

from exception_mistral_prefix import core, provider, runner

MAX_ERROR_BYTES = 16_384
MAX_FIELD_CHARS = 800


def safe_http_details(exc, key):
    """Read only bounded error JSON; redact the key and omit raw bodies/headers."""
    def safe(value, limit=MAX_FIELD_CHARS):
        text = str(value)
        if key:
            text = text.replace(key, "[REDACTED]")
        return text[:limit]

    details = {"http_status": exc.code}
    if exc.headers is not None:
        retry_after = exc.headers.get("Retry-After")
        if retry_after is not None:
            details["retry_after"] = safe(retry_after, 128)
    try:
        body = exc.read(MAX_ERROR_BYTES + 1)
    except Exception:
        # The HTTP status remains a retryable provider error even if its body
        # cannot be read. Do not expose an exception containing provider text.
        details["body_status"] = "unreadable"
        return details
    if len(body) > MAX_ERROR_BYTES:
        details["body_status"] = "too_large_omitted"
        return details
    try:
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        details["body_status"] = "non_json_omitted"
        return details
    if not isinstance(payload, dict):
        details["body_status"] = "unexpected_json_shape"
        return details
    nested = payload.get("error")
    fields = nested if isinstance(nested, dict) else payload
    for name in ("message", "type", "code", "param", "detail"):
        value = fields.get(name)
        if isinstance(value, (str, int, float, bool)):
            details[name] = safe(value)
    if isinstance(nested, str) and "message" not in details:
        details["message"] = safe(nested)
    if not any(name in details for name in ("message", "type", "code", "param", "detail")):
        details["body_status"] = "no_recognized_error_fields"
    return details


# Capture the unchanged transport before run_once temporarily installs its wrapper.
_original_complete = provider.complete


def complete_with_diagnostics(config, payload):
    """Observe one failed HTTP response without replacing the original transport."""
    key = provider.credential(config)
    original_request = provider.request
    captured = {}

    class ObservedOpener:
        def __init__(self, opener):
            self.opener = opener

        def open(self, *args, **kwargs):
            try:
                return self.opener.open(*args, **kwargs)
            except HTTPError as exc:
                try:
                    captured.update(safe_http_details(exc, key))
                except Exception:
                    captured.update(http_status=exc.code, body_status="diagnostic_unavailable")
                raise

    def build_opener(*handlers):
        return ObservedOpener(original_request.build_opener(*handlers))

    # Rebind only this provider's request namespace. Do not patch urllib globally.
    provider.request = SimpleNamespace(Request=original_request.Request,
                                       build_opener=build_opener)
    try:
        return _original_complete(config, payload)
    except provider.ProviderError as exc:
        if not captured:
            raise
        details = json.dumps(captured, ensure_ascii=True, sort_keys=True)
        raise provider.ProviderError(f"HTTP {exc.status_code}; details={details}",
                                     status_code=exc.status_code) from None
    finally:
        provider.request = original_request


def run_once(config, output):
    """Exactly one attempted request, subject to the original run's fixed gates."""
    output = Path(output)
    if not (output / "plan.json").is_file() or not (output / "execution.json").is_file():
        raise ValueError("Diagnostic requires an existing started run; use the original runner to start one")
    original_complete = provider.complete
    provider.complete = complete_with_diagnostics
    try:
        return runner.run(config, output, max_calls=1, resume=True, retry_errors=True)
    finally:
        provider.complete = original_complete


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_once(core.load_config(args.config), args.output)
    except (ValueError, OSError, provider.ProviderError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return int(result["stopped"] not in ("complete", "call_limit"))


if __name__ == "__main__":
    sys.exit(main())
