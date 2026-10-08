"""Freeze ten previously audited traces and change one availability statement."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import random
import re

from exception_pilot.core import check_plan, digest
from exception_explanation.core import source_digest as parent_source_digest

PROTOCOL_VERSION = "false-missingness-replay-v1"
PARENT_PLAN_HASH = "81d29ff260b9b06999bd26f5cbea5611d3b5a9e507af31692b6ce0bff33c2a5a"
# Canonical hashes, not raw responses. prepare reads the user's local parent run.
SOURCE_HASHES = {
    2: "dcc90f60148c4787d28a8c63ab08dbdac1db3e49479a9ff8ca118f51500f546a",
    22: "f5f30cae8e22ddd22b2956f118cc6abe01e56174ae11ec1bd233413eddcfec82",
    82: "f8f4cdbcaf1e840839bd4f4c245fbaf66d4ddd639d8fa6ee57c3c768fe14a573",
    105: "150fd583b73004136aa9e35cb39837aaff0a10c94c5b227106edbe6c4b82ef8a",
    129: "e89edf47d373d2405fd74f11212774c02eb8b4e143e27c2e17bfd980a245c05e",
    167: "d7a79ea2195dc50eadc526f1c1a12576cf71ba3c5a77bf37dfbc1a9b5ae9076e",
    170: "6104dc43a802ea569d82562a687f46be2c53f09b7a0a268f9fd74aac87709aae",
    240: "9cc32ac1715edccef5f15b5f22c22f7c7281ec999eafa0d5bcb7203e3578083c",
    297: "b0cb233213443e4dd61c520e5021ba9eaafbbcbd9f51d3815d1afda34c6c44ff",
    329: "c6986ed672000ecc143a68d2eab37a2712419f3855cdd4b16ab9ca9f85786143",
}
ARMS = ("original", "unavailable", "available", "gold")
CONTINUATION = ("Continue the reasoning from these notes. Then put ANSWER: followed by "
                "A, B, or C alone on the final line.")
DEFAULT_CONFIG = {
    "protocol": PROTOCOL_VERSION, "model": "gpt-4o-2024-08-06",
    "api_key_env": "OPENAI_API_KEY", "temperature": 0.0,
    "max_completion_tokens": 1000, "max_total_attempts": 48,
    "timeout_seconds": 120, "seed": 2026100891,
}
ANALYSIS_PLAN = {
    "selection": "Post hoc: ten false-MISSING traces without a clear correct-class statement; mixed attempt 60 excluded.",
    "n_cases": 10, "n_worlds": 9, "planned_calls": 40,
    "replay_gate": "All 10 original replays scorable and at least 8 exact original final-label matches; otherwise stop.",
    "primary": "available_minus_unavailable: correctness, average within world then across worlds",
    "secondary": ["available_minus_original", "gold_minus_available", "unavailable_minus_original"],
    "uncertainty": "Descriptive whole-world bootstrap only; selected small subset, not population inference.",
    "invalids": "Retain; complete-world analysis by contrast plus full-plan worst-case bounds.",
    "claim_limit": "Causal sensitivity to assistant-history text under a new continuation turn, not hidden-state identification.",
}


def validate_config(config):
    if set(config) != set(DEFAULT_CONFIG):
        raise ValueError("Config keys differ from the fixed missingness protocol")
    for key in DEFAULT_CONFIG:
        if key not in ("api_key_env", "timeout_seconds") and config[key] != DEFAULT_CONFIG[key]:
            raise ValueError(f"The missingness protocol fixes {key}")
    if not isinstance(config["api_key_env"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", config["api_key_env"]):
        raise ValueError("api_key_env must name an environment variable")
    timeout = config["timeout_seconds"]
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout_seconds must be positive and finite")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_digest():
    return digest({"parent_packages": parent_source_digest(), "missingness": {
        p.name: p.read_text() for p in sorted(Path(__file__).parent.glob("*.py"))}})


def load_sources(parent):
    from exception_explanation.runner import read_run
    plan, execution, attempts = read_run(parent, "live")
    if (plan["plan_hash"] != PARENT_PLAN_HASH or execution is None or len(attempts) != 384
            or any(a["status"] != "complete" for a in attempts)):
        raise ValueError("This diagnostic requires the audited, complete 384-call explanation-001 parent")
    return [attempts[number - 1] for number in SOURCE_HASHES]


def case_from_source(source):
    number = source["attempt"]
    if number not in SOURCE_HASHES or digest(source) != SOURCE_HASHES[number]:
        raise ValueError("A selected parent trace differs from the audited source")
    meta = source["meta"]
    if (meta["arm"] != "cot" or meta["value"] not in ("record_1", "record_2")
            or source["status"] != "complete" or source["answer"] not in "ABC"):
        raise ValueError("Selected source is not a scorable visible-record neutral-CoT response")
    lines = source["response"]["text"].splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines)
               if re.search(r"\b" + re.escape(meta["item_id"]) + r"\b", line)
               and re.search(r"\bMISSING\b", line)]
    if not matches:
        raise ValueError("Target-specific MISSING line was not found")
    index = matches[0]
    edit_line = lines[index].rstrip("\r\n")
    if edit_line.count("MISSING") != 1:
        raise ValueError("Edit location does not contain exactly one MISSING token")
    before = "".join(lines[:index])
    prefix = before + edit_line
    if "ANSWER:" in prefix:
        raise ValueError("The frozen prefix must end before the original final-answer line")
    return {"id": source["task_id"], "world_id": meta["world_id"], "item_id": meta["item_id"],
            "expected": meta["expected"], "pattern_label": meta["pattern_label"],
            "original_answer": source["answer"], "original_correct": source["answer"] == meta["expected"],
            "source_attempt": number, "source_hash": digest(source), "cut_line_1based": index + 1,
            "before_edit_line": before, "edit_line": edit_line, "prefix": prefix,
            "original_messages": copy.deepcopy(source["request"]["messages"])}


def make_plan(config, sources):
    validate_config(config)
    if [s["attempt"] for s in sources] != list(SOURCE_HASHES):
        raise ValueError("Source selection or order differs from the ten fixed cases")
    cases = [case_from_source(source) for source in sources]
    if len({c["world_id"] for c in cases}) != 9 or sum(c["original_correct"] for c in cases) != 2:
        raise ValueError("Expected nine worlds and two originally correct cases")
    def task(case, arm):
        return {"id": case["id"] + "/" + arm, "case_id": case["id"], "arm": arm}
    replay = [task(c, "original") for c in cases]
    edits = [task(c, arm) for c in cases for arm in ARMS[1:]]
    random.Random(config["seed"]).shuffle(edits)
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "parent_plan_hash": PARENT_PLAN_HASH, "config": copy.deepcopy(config),
            "sources": copy.deepcopy(sources), "cases": cases, "tasks": replay + edits,
            "analysis_plan": ANALYSIS_PLAN}
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text())
    check_plan(plan)
    if plan != make_plan(plan["config"], plan["sources"]):
        raise ValueError("Saved plan or code differs; preserve this run without changing its protocol")
    return plan


def case_for(plan, task):
    return next(c for c in plan["cases"] if c["id"] == task["case_id"])


def edited_prefix(case, arm):
    replacements = {"original": "MISSING", "unavailable": "NOT RECORDED IN THE TABLE",
                    "available": "RECORDED IN THE TABLE", "gold": case["expected"]}
    return case["before_edit_line"] + case["edit_line"].replace("MISSING", replacements[arm])


def task_meta(plan, task):
    case = case_for(plan, task)
    return {key: case[key] for key in ("id", "world_id", "item_id", "expected", "pattern_label",
                                      "source_attempt", "source_hash", "original_answer", "original_correct")}


def request_for(plan, task):
    config, case = plan["config"], case_for(plan, task)
    messages = copy.deepcopy(case["original_messages"]) + [
        {"role": "assistant", "content": edited_prefix(case, task["arm"])},
        {"role": "user", "content": CONTINUATION}]
    return {"model": config["model"], "messages": messages, "temperature": config["temperature"],
            "max_completion_tokens": config["max_completion_tokens"], "n": 1, "store": False}


def score_response(task, response):
    lines = response["text"].strip().splitlines() if response["complete"] else []
    match = re.fullmatch(r"ANSWER: ([ABC])", lines[-1].strip()) if lines else None
    answer = match.group(1) if match else None
    return {"answer": answer, "status": "complete" if answer is not None else "invalid"}
