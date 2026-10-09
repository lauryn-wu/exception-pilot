"""A bounded, correctness-blind grammar for one terminal answer block.

The grammar admits ASCII case-insensitive ANSWER, one uppercase A/B/C,
ASCII whitespace, balanced *, **, _, __, or ` wrappers, and at most one
period. Wrappers may surround the block, marker (colon inside or outside),
or label, with a maximum nesting depth of three. An optional complete
triple-backtick/triple-tilde fence has no language, text, or plaintext.
Only the final standalone block is parsed; adjacent answer blocks fail.
"""

from __future__ import annotations

from collections import deque
from functools import lru_cache
import re


ASCII_WHITESPACE = " \t\r\n\f\v"
MAX_WRAPPER_DEPTH = 3
# At depth three the marker and label can each have three wrapper pairs:
# 24 delimiter characters + ANSWER + colon + label + one period = 28 tokens.
MAX_TOKENS = 28
MAX_CANDIDATE_LINES = MAX_TOKENS + 2  # Two additional lines for a fence.
_WRAPPERS = (("*", "*"), ("*",), ("_", "_"), ("_",), ("`",))
_TOKEN = re.compile(r"[ \t\r\n\f\v]+|(?ai:ANSWER)|[ABC:*_`.]")
_FENCE_LINE = re.compile(r"^[ \t]*(?P<run>`{3,}|~{3,})(?P<tail>[^\r\n]*)\r?$")
_FENCE_HEADER = re.compile(r"[ \t]*(?P<fence>```|~~~)[ \t]*(?:(?ai:text|plaintext))?[ \t]*\r?\Z")


def _tokens(text):
    """Ignore only explicit whitespace, never punctuation or arbitrary text."""
    result = []
    position = 0
    count = 0
    whitespace = False
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            return None
        token = match.group()
        if token[0] not in ASCII_WHITESPACE:
            # Keep a boundary between separate delimiter runs. Otherwise
            # '* **ANSWER:** A *' would collapse into a different wrapper.
            if whitespace and result and token == result[-1] and token in "*_`":
                result.append(" ")
            result.append("ANSWER" if len(token) == 6 else token)
            count += 1
            whitespace = False
            if count > MAX_TOKENS:
                return None
        else:
            whitespace = True
        position = match.end()
    return tuple(result)


@lru_cache(maxsize=4096)
def _unwrapped(tokens, budget, allow_period):
    """Enumerate a finite number of balanced outer-wrapper removals."""
    while tokens[:1] == (" ",):
        tokens = tokens[1:]
    while tokens[-1:] == (" ",):
        tokens = tokens[:-1]
    results = {(tokens, 0, 0)}
    if allow_period and tokens[-1:] == (".",):
        for inner, depth, periods in _unwrapped(tokens[:-1], budget, False):
            results.add((inner, depth, periods + 1))
    if budget:
        for wrapper in _WRAPPERS:
            width = len(wrapper)
            # ** and __ are atomic before single-star/underscore wrappers.
            # This prevents malformed bold from being rescued by splitting
            # it across an outer wrapper, a marker, and a label.
            if wrapper in (("*",), ("_",)) and (
                tokens[:2] == wrapper * 2 or tokens[-2:] == wrapper * 2
            ):
                continue
            if len(tokens) >= 2 * width and tokens[:width] == tokens[-width:] == wrapper:
                for inner, depth, periods in _unwrapped(tokens[width:-width], budget - 1, allow_period):
                    results.add((inner, depth + 1, periods))
    return frozenset(results)


def _marker(tokens, budget):
    # Wrappers outside the colon and wrappers inside the colon share a budget.
    for inner, used, _ in _unwrapped(tokens, budget, False):
        if inner[-1:] == (":",):
            if any(value == ("ANSWER",)
                   for value, _, _ in _unwrapped(inner[:-1], budget - used, False)):
                return True
    return False


def _plain_answer(text):
    tokens = _tokens(text)
    if tokens is None or tokens.count(":") != 1:
        return None
    for block, used, periods in _unwrapped(tokens, MAX_WRAPPER_DEPTH, True):
        if ":" not in block:
            continue
        budget = MAX_WRAPPER_DEPTH - used
        # At most 28 syntax tokens plus delimiter-run boundaries.
        for split in range(block.index(":") + 1, len(block)):
            if not _marker(block[:split], budget):
                continue
            for label, _, _ in _unwrapped(block[split:], budget, not periods):
                if len(label) == 1 and label[0] in ("A", "B", "C"):
                    return label[0]
    return None


def _block_answer(text):
    stripped = text.rstrip(ASCII_WHITESPACE)
    first_line = stripped.split("\n", 1)[0]
    if first_line.lstrip(" \t").startswith(("```", "~~~")):
        lines = stripped.split("\n")
        header = _FENCE_HEADER.fullmatch(lines[0])
        if header is None or len(lines) < 3:
            return None
        if lines[-1].strip(" \t\r") != header["fence"]:
            return None
        return _plain_answer("\n".join(lines[1:-1]))
    return _plain_answer(stripped)


def _candidate_starts(text):
    """Keep a small structurally sufficient suffix, tracking open code fences.

    Blank lines do not use the bound, so arbitrary intervening whitespace is
    allowed. A valid block has at most MAX_TOKENS nonblank content lines.
    """
    candidates = deque(maxlen=MAX_CANDIDATE_LINES)
    active_fence = None
    offset = 0
    for line in text.split("\n"):
        if line.strip(ASCII_WHITESPACE):
            # The boundary includes indentation, not just the ANSWER token.
            if line.lstrip(" \t")[:1] not in ("\r", "\f", "\v"):
                candidates.append((offset, active_fence is not None))
        fence = _FENCE_LINE.fullmatch(line)
        if fence is not None:
            run, tail = fence["run"], fence["tail"]
            if active_fence is None:
                active_fence = (run[0], len(run))
            elif (run[0] == active_fence[0] and len(run) >= active_fence[1]
                  and not tail.strip(" \t\r")):
                active_fence = None
        offset += len(line) + 1
    return candidates


def _dangling_wrapper_before(text, start):
    previous = text[:start].rstrip(ASCII_WHITESPACE).rsplit("\n", 1)[-1].strip(" \t\r")
    # Complete code fences are handled by the fence-state scan. A closed
    # reasoning fence immediately before an answer is legitimate pretext.
    if re.fullmatch(r"`{3,}", previous):
        return False
    return bool(previous) and set(previous) <= {"*", "_", "`"}


def _terminal_block(text):
    for start, inside_fence in _candidate_starts(text):
        if inside_fence or _dangling_wrapper_before(text, start):
            continue
        answer = _block_answer(text[start:])
        if answer is not None:
            return answer, start
    return None, None


def answer_boundary(text: str) -> tuple[str | None, int | None]:
    """Return (A/B/C, raw first-line offset), or (None, None).

    No expected answer or task metadata is accepted. The complete opening
    wrapper/fence and its indentation belong to the returned final block.
    Earlier answer-like discussion is allowed, but two adjacent standalone
    answer blocks (even identical ones) are ambiguous and rejected.
    """
    answer, start = _terminal_block(text)
    if answer is None:
        return None, None
    prefix = text[:start].rstrip(ASCII_WHITESPACE)
    if prefix and _terminal_block(prefix)[0] is not None:
        return None, None
    return answer, start
