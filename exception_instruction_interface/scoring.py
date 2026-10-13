"""Extract only the first field; score it independently of the remaining contract."""

import json
import math
import re

ASCII_WS = " \t\r\n"
FIELDS = ("first_value", "reasoning", "final_answer")
CATEGORIES = ("correct_class", "wrong_abc_class", "MISSING", "null", "other_emitted_value",
              "absent_or_unparseable")
PARSING_RULES = {
    "version": "first-field-v1",
    "whitespace": "Trim ASCII space/tab/CR/LF at outer boundaries only; no case/quote/Unicode normalization",
    "json_first": "First object key must be first_value. Decode its complete JSON value independently of the suffix; closed strings/containers and complete null/boolean literals count even at truncated EOF. Numbers require a JSON delimiter or normal-stop EOF. Reject malformed bare literals.",
    "text_first": "After outer leading ASCII whitespace, first line must start first_value:. Value ends at LF (optional CR) or normal-stop EOF; truncated EOF is incomplete. Literal null denotes null. Never scan later fields.",
    "contract": "Normal complete response, exactly first_value/reasoning/final_answer in order, string-or-null first, nonempty string reasoning, exact A/B/C final. JSON duplicate keys rejected; text permits multiline reasoning only.",
    "final": "Score only an explicit complete final_answer field in a fully parsed unique JSON object or a unique anchored text final field after reasoning; never infer from prose. Truncated text final requires LF.",
    "retention": "All returned first-entry failures count as incorrect; full first entries survive malformed/truncated suffixes; missing transport responses never count as incorrect",
}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("Non-JSON numeric constant: " + value)


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Number cannot be represented finitely")
    return number


DECODER = json.JSONDecoder(object_pairs_hook=_unique_object, parse_constant=_invalid_constant,
                          parse_float=_finite_float)


def _json_first(text, complete):
    s = text.lstrip(ASCII_WS)
    if not s.startswith("{"):
        return False, None, None
    s = s[1:].lstrip(ASCII_WS)
    try:
        key, end = DECODER.raw_decode(s)
        if key != "first_value":
            return False, None, None
        s = s[end:].lstrip(ASCII_WS)
        if not s.startswith(":"):
            return False, None, None
        s = s[1:].lstrip(ASCII_WS)
        value, end = DECODER.raw_decode(s)
        # Strings/containers have an explicit closing character. For bare values,
        # reject partial literals (nullx, 1e, ...) and ambiguous truncated EOF.
        if s[0] not in '\"[{':
            if end < len(s) and s[end] not in ASCII_WS + ",}":
                return False, None, None
            if end == len(s) and not complete and value is not None and type(value) is not bool:
                return False, None, None
        return True, value, s[:end]
    except (ValueError, TypeError, RecursionError):
        return False, None, None


def _text_first(text, complete):
    s = text.lstrip(ASCII_WS)
    if not s.startswith("first_value:"):
        return False, None, None
    value, separator, _ = s[len("first_value:"):].partition("\n")
    if not separator and not complete:
        return False, None, None
    value = value.removesuffix("\r")
    raw = value
    # Preserve the literal source separately from this format-specific null mapping.
    return True, None if value.strip(ASCII_WS) == "null" else value, raw


def _full_json(text):
    try:
        value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_invalid_constant,
                           parse_float=_finite_float)
        return value if isinstance(value, dict) else None
    except (ValueError, TypeError, RecursionError):
        return None


def _text_fields(text, complete):
    s = text.lstrip(ASCII_WS)
    # Neutral field names at the start of a line are reserved delimiters. Do not
    # interpret quoted/inline mentions in the rationale as answers.
    matches = list(re.finditer(r"(?m)^(first_value|reasoning|final_answer):", s))
    if not matches or matches[0].start() != 0:
        return None
    names = [m.group(1) for m in matches]
    if len(names) != len(set(names)):
        return None
    fields = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(s)
        raw = s[match.end():end]
        if match.group(1) != "reasoning":
            # Non-reasoning fields must occupy one complete line only.
            line, newline, tail = raw.partition("\n")
            if tail.strip(ASCII_WS) or not newline and not complete:
                continue
            raw = line
        fields[match.group(1)] = raw.strip(ASCII_WS)
    return fields


def score_response(task, response):
    text, complete = response["text"], response["complete"]
    is_json = task["interface"] == "json"
    emitted, raw, lexeme = (_json_first if is_json else _text_first)(text, complete)
    first = raw.strip(ASCII_WS) if isinstance(raw, str) else raw
    if not emitted:
        category = "absent_or_unparseable"
    elif first is None:
        category = "null"
    elif isinstance(first, str) and first in ("A", "B", "C"):
        category = "correct_class" if first == task["expected"] else "wrong_abc_class"
    elif first == "MISSING":
        category = "MISSING"
    else:
        category = "other_emitted_value"
    fields = _full_json(text) if is_json else _text_fields(text, complete)
    answer, reasoning, shape = None, None, False
    if fields is not None:
        final = fields.get("final_answer")
        final_position_ok = is_json or ("final_answer" in fields and "reasoning" in fields
                                       and list(fields).index("final_answer") > list(fields).index("reasoning"))
        if isinstance(final, str) and final in ("A", "B", "C") and final_position_ok:
            answer = final
        reasoning = fields.get("reasoning") if isinstance(fields.get("reasoning"), str) else None
        first_type_ok = isinstance(fields.get("first_value"), str) or fields.get("first_value") is None
        shape = (tuple(fields) == FIELDS and first_type_ok and reasoning is not None
                 and bool(reasoning.strip(ASCII_WS)) and answer is not None)
    contract = bool(complete and shape)
    return {"status": "complete" if contract else "invalid", "output_contract_met": contract,
            "first_emitted": emitted, "first_value_raw": raw, "first_value_lexeme": lexeme,
            "first_value": first, "first_category": category,
            "first_correct": category == "correct_class", "answer": answer, "reasoning": reasoning,
            "final_correct": answer == task["expected"] if answer is not None else None,
            "correct_first_wrong_final": category == "correct_class" and answer is not None
                                         and answer != task["expected"]}
