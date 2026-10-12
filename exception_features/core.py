"""A frozen factorial intervention on feature bundles; no outcome selection."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import random
import re
from exception_pilot.core import check_plan, digest
from exception_mistral_map_v3.parser import answer_boundary
from . import PROTOCOL_VERSION

ROOT = Path(__file__).resolve().parents[1]
SEED = 2026101202
ARMS = ("direct", "cot", "copy_class")
RECORDS = ("record_1", "record_2")
CUES = ("favor_1", "favor_2", "balanced_record_cues")
FEATURES = ("transmission", "seat_cover", "doors")
FEATURE_VALUES = (("Manual", "Automatic"), ("Vinyl", "Cloth"), ("Four", "Two"))
COLUMNS = ("id", "descriptor", *FEATURES, "audit_marker", "class")
HEADERS = ("License plate", "Description", "Transmission", "Seat cover", "Doors", "Audit marker", "Verified class")
INTRO = ("These are records of previously observed vehicles. Every record is accurate. "
         "An individual vehicle's class is fixed, and its license plate identifies it. "
         "The audit marker is an administrative code assigned independently of class. "
         "MISSING means the verified class has not been recorded. If that cell is "
         "MISSING, make your best prediction from the other records.")
QUESTION = "Which class, A, B, or C, does this vehicle belong to?"
FINAL = "Think step by step, then put ANSWER: followed by A, B, or C alone on the final line."
INSTRUCTIONS = {"direct": "Reply with only ANSWER: followed by A, B, or C.", "cot": FINAL,
    "copy_class": "First copy the target vehicle's Verified class cell exactly, using COPIED: followed by the cell value alone on the first line. Do not explain before that line. " + FINAL}
DESCRIPTORS = {
    "cold": ("Built for subzero temperatures", "Designed for frozen terrain", "Used at an Arctic station", "Operates on polar ice", "Equipped with snow tracks", "Built for icy roads"),
    "warm": ("Operates in tropical forests", "Designed for humid summers", "Used at an equatorial station", "Equipped for hot sand", "Built for desert heat", "Designed for tropical heat"),
}
ANALYSIS_PLAN = {"primary": "cot_minus_direct_cue_sensitivity", "unit": "world; all 18 cells paired",
 "bootstrap": "10000 whole-world resamples, seed 981723; descriptive unadjusted 95% intervals",
 "missing": "contrast-specific complete worlds; full-plan bounds vary every invalid or missing answer over A/B/C",
 "scope": "fresh exploratory structured-cue worlds, not confirmation of the original random-column mechanism",
 "decision": "fixed sample; no success threshold or outcome-dependent extension"}


def rng(*parts):
    return random.Random(int(hashlib.sha256(json.dumps((SEED, *parts)).encode()).hexdigest(), 16))


def validate_config(config):
    expected = {"protocol": PROTOCOL_VERSION, "model": "gpt-4o-2024-08-06", "temperature": 0,
                "max_completion_tokens": 1000, "max_total_attempts": 684}
    if set(config) != set(expected) | {"api_key_env", "timeout_seconds"}:
        raise ValueError("Config fields differ from frozen feature-support design")
    for key, value in expected.items():
        if config[key] != value or isinstance(config[key], bool):
            raise ValueError(f"Frozen config requires {key}={value!r}")
    if any(type(config[k]) is not int for k in ("max_completion_tokens", "max_total_attempts")):
        raise ValueError("Caps must be integers")
    if not isinstance(config["api_key_env"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", config["api_key_env"]):
        raise ValueError("api_key_env must name a variable, never contain a key")
    if type(config["timeout_seconds"]) not in (int, float) or not math.isfinite(config["timeout_seconds"]) or config["timeout_seconds"] <= 0:
        raise ValueError("Invalid timeout")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))

def source_hash():
    from exception_study_support.core import source_digest
    return source_digest(ROOT, "exception_features", extra_paths=("configs/features_gpt4o.json", "FEATURES_PROTOCOL.md"))


def make_worlds():
    worlds = []
    cyclic = (("A", "B", "C"), ("B", "C", "A"), ("C", "A", "B"))
    anticyclic = (("A", "C", "B"), ("B", "A", "C"), ("C", "B", "A"))
    # Complemented pairs give exactly 18 instances of each feature value.
    target_bits = [bits for i in range(18) for bits in ((i % 8), (7 - i % 8))]
    rng("target-values").shuffle(target_bits)
    for position in range(1, 13):
        for role_index, labels in enumerate(cyclic if position % 2 else anticyclic):
            index = len(worlds)
            wid = f"features-{index:03d}"
            prng = rng(wid)
            roles = dict(zip((*RECORDS, "pattern"), labels))
            climate = "warm" if (position + role_index) % 2 else "cold"
            opposite = "cold" if climate == "warm" else "warm"
            target_vals = {key: values[(target_bits[index] >> j) & 1] for j, (key, values) in enumerate(zip(FEATURES, FEATURE_VALUES))}
            plates = []
            while len(plates) < 12:
                plate = "F" + "".join(prng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(5))
                if plate not in plates:
                    plates.append(plate)
            same_desc = list(DESCRIPTORS[climate]); prng.shuffle(same_desc)
            other_desc = list(DESCRIPTORS[opposite]); prng.shuffle(other_desc)
            target = {"id": plates[0], "descriptor": same_desc[0], **target_vals, "audit_marker": "XYZ"[role_index], "climate": climate}
            rows = [target]
            groups = {}
            for role in (*RECORDS, "pattern"):
                groups[role] = []
                markers = list("XYZ"); prng.shuffle(markers)
                for j in range(3):
                    row_index = len(rows)
                    groups[role].append(row_index)
                    desc = same_desc[j + 1] if role == "pattern" else other_desc[(0 if role == "record_1" else 3) + j]
                    rows.append({"id": plates[row_index], "descriptor": desc, "audit_marker": markers[j], "class": roles[role], "climate": climate if role == "pattern" else opposite})
            # Two fixed nonmatching pattern rows prevent the target label
            # from becoming the overall majority under either record variant.
            for j in range(2):
                extra = {"id": plates[len(rows)], "descriptor": same_desc[4+j],
                         "class": roles["pattern"], "climate": climate,
                         "audit_marker": [m for m in "XYZ" if m != target["audit_marker"]][j]}
                for key, choices in zip(FEATURES, FEATURE_VALUES):
                    extra[key] = next(v for v in choices if v != target_vals[key])
                rows.append(extra)
            order = list(range(1, 12)); prng.shuffle(order); order.insert(position - 1, 0)
            # Fixed slot permutations preserve P rows exactly for favor_1 versus favor_2.
            slots = {role: list(indices) for role, indices in groups.items()}
            for indices in slots.values(): prng.shuffle(indices)
            pairs = [("100", "011"), ("010", "101"), ("001", "110")]
            prng.shuffle(pairs)
            neutral = {role: ["111", *pairs[i]] for i, role in enumerate((*RECORDS, "pattern"))}
            for bundles in neutral.values(): prng.shuffle(bundles)
            assignments = {
                "favor_1": {"record_1": ["111"] * 3, "record_2": ["100", "010", "001"], "pattern": ["110", "101", "011"]},
                "favor_2": {"record_1": ["100", "010", "001"], "record_2": ["111"] * 3, "pattern": ["110", "101", "011"]},
                "balanced_record_cues": neutral,
            }
            cue_rows = {}
            for cue, assignment in assignments.items():
                cell_rows = [dict(r) for r in rows]
                for role, bundles in assignment.items():
                    for row_index, bundle in zip(slots[role], bundles):
                        for j, (key, choices) in enumerate(zip(FEATURES, FEATURE_VALUES)):
                            value = target_vals[key]
                            cell_rows[row_index][key] = value if bundle[j] == "1" else next(v for v in choices if v != value)
                cue_rows[cue] = cell_rows
            worlds.append({"id": wid, "roles": roles, "target_position": position, "target_index": 0, "target_climate": climate,
                "target_id": target["id"], "order": order, "groups": groups, "cue_rows": cue_rows})
    return worlds


def make_plan(config):
    validate_config(config)
    worlds = make_worlds()
    tasks = []
    for world in worlds:
        cells = [{"id": f"{world['id']}/{record}/{cue}/{arm}", "world_id": world["id"], "record": record, "cue": cue, "arm": arm}
                 for record in RECORDS for cue in CUES for arm in ARMS]
        rng(world["id"], "schedule").shuffle(cells)
        tasks.extend(cells)
    plan = {"protocol_version": PROTOCOL_VERSION, "source_hash": source_hash(), "config": config, "worlds": worlds,
            "tasks": tasks, "analysis_plan": ANALYSIS_PLAN, "seed": SEED}
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text())
    check_plan(plan)
    if plan != make_plan(plan["config"]):
        raise ValueError("Source/config/frozen plan changed; use a new run directory")
    return plan


def world_for(plan, task):
    return next(w for w in plan["worlds"] if w["id"] == task["world_id"])


def table_rows(plan, task):
    world = world_for(plan, task)
    rows = [dict(r) for r in world["cue_rows"][task["cue"]]]
    rows[0]["class"] = world["roles"][task["record"]]
    return [rows[i] for i in world["order"]]


def table_text(plan, task):
    lines = ["| " + " | ".join(HEADERS) + " |", "|" + "---|" * len(COLUMNS)]
    for row in table_rows(plan, task):
        lines.append("| " + " | ".join(row[k] for k in COLUMNS) + " |")
    return "\n".join(lines)


def task_meta(plan, task):
    world = world_for(plan, task)
    favored = world["roles"]["record_1" if task["cue"] == "favor_1" else "record_2"] if task["cue"] != "balanced_record_cues" else None
    gold = world["roles"][task["record"]]
    return {**task, "target_id": world["target_id"], "target_position": world["target_position"], "expected": gold,
            "pattern_label": world["roles"]["pattern"], "favored_label": favored,
            "alignment": "balanced_record_cues" if favored is None else "aligned" if favored == gold else "opposed"}


def request_for(plan, task):
    target_id = world_for(plan, task)["target_id"]
    prompt = INTRO + "\n\n" + table_text(plan, task) + "\n\nLicense plate: " + target_id + "\n" + QUESTION + "\n" + INSTRUCTIONS[task["arm"]]
    return {"model": plan["config"]["model"], "messages": [{"role": "user", "content": prompt}], "temperature": 0,
            "max_completion_tokens": 1000, "n": 1, "store": False}


def reasoning_text(text):
    answer, start = answer_boundary(text.strip())
    pretext = text.strip()[:start].strip() if start is not None else text.strip()
    return re.sub(r"\ACOPIED: (?:[ABC]|MISSING)\s*(?:\n|$)", "", pretext, count=1).strip()


def score_response(task, response):
    text = response["text"].strip()
    answer, start = answer_boundary(text) if response["complete"] else (None, None)
    pretext = text[:start].strip() if start is not None else text
    match = re.fullmatch(r"COPIED: ([ABC]|MISSING)", pretext.partition("\n")[0].strip()) if task["arm"] == "copy_class" else None
    copied = match[1] if match else None
    reasoning = pretext.partition("\n")[2].strip() if match else pretext
    strict = answer is not None and text[start:].strip() == "ANSWER: " + answer
    has_reasoning = bool(reasoning)
    adherence = not pretext if task["arm"] == "direct" else has_reasoning and (bool(match) if task["arm"] == "copy_class" else True)
    return {"status": "complete" if answer is not None else "invalid", "answer": answer, "copied": copied,
        "copy_valid": bool(match) if task["arm"] == "copy_class" else None, "strict_final_format": strict,
        "answer_only": answer is not None and not pretext, "has_reasoning": has_reasoning,
        "contract_met": bool(answer is not None and strict and adherence), "reasoning_words": len(reasoning.split())}


def mock_complete(plan, task):
    gold = task_meta(plan, task)["expected"]
    text = ("COPIED: " + gold + "\n" if task["arm"] == "copy_class" else "")
    text += "SIMULATED ONLY: use the recorded class.\n" if task["arm"] != "direct" else ""
    text += "ANSWER: " + gold
    return {"model": "MOCK-NOT-A-MODEL", "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}], "usage": {}}
