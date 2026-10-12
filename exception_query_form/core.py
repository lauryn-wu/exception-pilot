"""Model-independent frozen worlds, exact prompts, and correctness-blind scoring."""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
import re

from exception_counterfactual.core import make_world
from exception_explanation.core import INTRO, QUESTION
from exception_mistral_map_v3.parser import answer_boundary
from exception_mistral_prefix_v2.core import ENDPOINT as MISTRAL_ENDPOINT
from exception_pilot.core import check_plan, describe, digest, rng_for

from . import CALLS_PER_WORLD, PROTOCOL_VERSION

VALUES = ("record_1", "record_2")
QUERIES = ("profile", "key")
ARMS = ("direct", "visible", "filler")
LABELS = ("A", "B", "C")
PLATE_PREFIX = "U"
SEED = 2026101001

# Approximately 320 words, chosen before new collection from the approximately
# 318/322-word median visible outputs in the archived cue/Mistral base studies.
# This is generated verbatim inside the same response, not an assistant prefill.
FILLER = (
    "Along the quiet shore, small waves move over smooth stones and return toward open water. "
    "Morning light spreads slowly across the surface, revealing ripples that overlap and fade. "
    "Farther inland, branches sway above the path while fallen leaves rest between exposed roots. "
    "The air feels cool beneath the trees, and the ground remains soft from overnight rain. "
    "Beyond the next bend, low hills rise behind the meadow, their outlines softened by mist. "
    "Wild grasses lean together when the breeze passes, then settle into their earlier places. "
    "Near the stream, moss covers the shaded stones with uneven patches of deep green. "
    "Water gathers briefly in shallow pools before continuing around roots and beneath loose branches. "
    "Beyond the shaded bank, thin reeds grow close together where the water becomes still. "
    "Small circles spread across the surface whenever droplets fall from the overhanging leaves. "
    "Soon the ripples disappear, leaving the reflections of branches clear against the pale sky. "
    "There is no hurry in the movement of the clouds or the slow change of light. "
    "Occasional birdsong comes from somewhere beyond the clearing, then gives way to silence again. "
    "The path follows the stream for some distance before climbing toward the edge of the woods. "
    "From that higher ground, the shore becomes visible through gaps between the slender trunks. "
    "Sunlight now reaches the meadow, touching the tips of the grasses and the scattered flowers. "
    "Dew remains on the leaves where the shade has not yet lifted from the ground. "
    "The same breeze travels through the clearing and out across the water toward the distant hills. "
    "Its passage is visible only in the brief movement of leaves and the changing texture of ripples. "
    "Along the shore, the smooth stones remain where the small waves have left them. "
    "Nothing requires attention here beyond the ordinary sounds of water, branches, and the passing wind. "
    "The morning continues quietly as the mist thins and the horizon grows clearer."
)
INSTRUCTIONS = {
    "direct": "Output only ANSWER: followed by A, B, or C.",
    "visible": ("Think step by step before answering. Write your reasoning, then put "
                "ANSWER: followed by A, B, or C alone on the final line."),
    "filler": ("First copy the following neutral paragraph exactly, without its delimiters. "
               "Do not add an explanation. Then put ANSWER: followed by A, B, or C "
               "alone on the final line.\n<neutral_paragraph>\n" + FILLER +
               "\n</neutral_paragraph>"),
}
PREDICTIONS = {
    "P1": "Profile direct minus visible record sensitivity >= 0.30.",
    "P2": "Key direct minus visible record sensitivity <= 0.10.",
    "P3": "Record-sensitivity interaction >= 0.20 with exact two-sided sign-test p < 0.05.",
    "P4": "Direct minus filler record sensitivity <= 0.10 in each query form.",
    "P5": "Among wrong visible responses, never_stated plus relabeled_missing >= 75%; provisional automated text coding only, not a gate.",
    "P6": "Mistral has the same positive interaction sign and interaction >= 0.20.",
}
DECISION_RULE = {
    "purpose": "Practical spending rule, not proof of a mechanism or equivalence.",
    "both_models_required": True,
    "minimum_complete_worlds_primary": 22,
    "minimum_filler_exact_fraction": 0.95,
    "minimum_visible_pretext_fraction": 0.95,
    "proceed": {"profile_harm_lower_bound": 0.30, "key_harm_upper_bound": 0.10,
                "interaction_lower_bound": 0.20, "sign_p_less_than": 0.05,
                "filler_harm_upper_bound_each_query": 0.10},
    "stop_filler": "Either filler harm full-plan lower bound > 0.10 and bootstrap lower endpoint > 0.",
    "stop_query": "Both visible harm full-plan lower bounds > 0.10 and both bootstrap lower endpoints > 0.",
    "precedence": ["incomplete", "model_identity_failure", "output_manipulation_inconclusive",
                   "stop_tokens_account_live", "stop_query_form", "eligible_for_dose_review", "inconclusive"],
    "cross_model": "Both complete live models must be eligible on the same design; otherwise no proceed_to_dose. Missing peer -> awaiting_replication. Mock -> simulated_only.",
}
ANALYSIS_PLAN = {
    "primary": "record_sensitivity/interaction",
    "secondary": "accuracy/interaction and simple effects",
    "record_sensitivity": "Average +1 correct, -1 other target label, 0 pattern over the two variants; range [-1,1].",
    "unit": "Whole independent world, keeping variants, query forms, and arms paired.",
    "bootstrap_resamples": 10000, "bootstrap_seed": 981723,
    "intervals": "Descriptive, unadjusted 95% percentile intervals; degenerate intervals do not establish equivalence.",
    "sign_test": "Exact two-sided binomial test on nonzero world differences; report ties separately. It tests sign balance, not the mean.",
    "bounds": "All planned worlds; valid responses fixed, each missing/invalid label ranges over A/B/C; coefficient signs retained.",
    "predictions": PREDICTIONS, "decision_rule": DECISION_RULE,
    "filler": "Same-response verbatim neutral-text generation; approximately length matched from historical traces. Input length and instruction semantics still differ.",
    "rationale_coding": "Provisional lexical evidence coding; no inference about hidden reasoning or retrieval; P5 never gates spending.",
}


def validate_config(config):
    common = {"protocol", "provider", "model", "api_key_env", "seed", "n_worlds",
              "temperature", "max_total_attempts", "timeout_seconds"}
    if not isinstance(config, dict) or config.get("provider") not in ("openai", "mistral"):
        raise ValueError("provider must be openai or mistral")
    mistral = config["provider"] == "mistral"
    extra = {"endpoint", "reasoning_effort", "max_tokens"} if mistral else {"max_completion_tokens"}
    if set(config) != common | extra:
        raise ValueError("Config fields must exactly match the supplied provider config; never include credentials")
    fixed = {"protocol": PROTOCOL_VERSION, "seed": SEED, "n_worlds": 24,
             "model": "mistral-small-2603" if mistral else "gpt-4o-2024-08-06",
             "max_total_attempts": 316, "timeout_seconds": 120, "temperature": 0}
    for key, value in fixed.items():
        if config[key] != value or isinstance(config[key], bool):
            raise ValueError(f"This study fixes {key}={value!r}")
    for key in ("seed", "n_worlds", "max_total_attempts"):
        if type(config[key]) is not int:
            raise ValueError(f"{key} must be an integer")
    if not isinstance(config["api_key_env"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", config["api_key_env"]):
        raise ValueError("api_key_env must be an environment variable name")
    if mistral and (config["endpoint"] != MISTRAL_ENDPOINT or config["reasoning_effort"] != "none"):
        raise ValueError("Mistral endpoint and reasoning_effort=none are fixed")
    limits = config["max_tokens" if mistral else "max_completion_tokens"]
    if not isinstance(limits, dict) or limits != {arm: 1600 if mistral else 1000 for arm in ARMS} or any(type(v) is not int for v in limits.values()):
        raise ValueError("All arms require the fixed equal provider completion cap")
    return config


def load_config(path):
    return validate_config(json.loads(Path(path).read_text()))


def source_digest():
    root = Path(__file__).resolve().parents[1]
    packages = ("exception_pilot", "exception_counterfactual", "exception_wording",
                "exception_factorial", "exception_explanation", "exception_cue", "exception_prefix",
                "exception_mistral_prefix", "exception_mistral_prefix_v2", "exception_mistral_map_v3",
                "exception_query_form")
    paths = [p for package in packages for p in sorted((root / package).glob("*.py"))]
    paths += [root / "code_rationales.py", root / "QUERY_FORM_PROTOCOL.md"]
    return digest({str(p.relative_to(root)): p.read_text() for p in paths})


def make_plan(config):
    validate_config(config)
    # Copied ternary role assignment from cue; do not call cue.make_plan.
    assignments = [(p, climate) for p in itertools.permutations(LABELS)
                   for climate in ("cold", "warm") for _ in range(2)]
    rng_for(PROTOCOL_VERSION, "assignments", SEED).shuffle(assignments)
    worlds, tasks, used = [], [], set()
    for index, (roles, climate) in enumerate(assignments):
        world = make_world({"seed": SEED}, index, used)
        world["id"] = f"qf-list-{index:03d}"
        for item in world["items"]:
            item["id"] = PLATE_PREFIX + item["id"][1:]
        target = next(i for i in world["target_indices"] if world["items"][i]["climate"] == climate)
        world["target_index"] = target
        world["roles"] = dict(zip(("record_1", "record_2", "pattern"), roles))
        rng = rng_for(PROTOCOL_VERSION, "ternary", SEED, index)
        other_labels = ([roles[0]] * 2 + [roles[1]] * 3 if index % 2
                        else [roles[0]] * 3 + [roles[1]] * 2)
        rng.shuffle(other_labels)
        labels, markers = [], ["X", "Y", "Z"] * 3 + [rng.choice(["X", "Y", "Z"])]
        rng.shuffle(markers)
        for i, item in enumerate(world["items"]):
            item["audit_marker"] = markers[i]
            labels.append(roles[2] if item["climate"] == climate else other_labels.pop())
        world["record_labels"] = {}
        for value in VALUES:
            version = labels.copy()
            version[target] = world["roles"][value]
            world["record_labels"][value] = version
        worlds.append(world)
        cells = [{"id": f"{world['id']}/{value}/{query}/{arm}", "world_id": world["id"],
                  "family": "diagnostic", "value": value, "query": query, "arm": arm}
                 for value in VALUES for query in QUERIES for arm in ARMS]
        assert len(cells) == CALLS_PER_WORLD
        rng_for(PROTOCOL_VERSION, "schedule", SEED, index).shuffle(cells)
        tasks.extend(cells)
    plan = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
            "design": {"seed": SEED, "n_worlds": 24, "plate_prefix": PLATE_PREFIX},
            "worlds": worlds, "tasks": tasks, "analysis_plan": copy.deepcopy(ANALYSIS_PLAN)}
    plan["plan_hash"] = digest(plan)
    return plan


def read_plan(output):
    output = Path(output)
    plan = json.loads((output / "plan.json").read_text())
    check_plan(plan)
    frozen = json.loads((output / "run_config.json").read_text())
    config = validate_config(frozen["config"])
    if frozen != {"config": config, "config_hash": digest(config), "plan_hash": plan["plan_hash"]}:
        raise ValueError("Frozen config identity differs")
    if plan != make_plan(config):
        raise ValueError("Code or saved plan differs; preserve this run and use a new directory")
    return plan, config


def world_for(plan, task):
    return next(w for w in plan["worlds"] if w["id"] == task["world_id"])


def task_meta(plan, task):
    world = world_for(plan, task)
    target = world["target_index"]
    return {k: task[k] for k in ("world_id", "family", "value", "query", "arm")} | {
        "item_id": world["items"][target]["id"], "expected": world["roles"][task["value"]],
        "pattern_label": world["roles"]["pattern"], "target_position": world["order"].index(target) + 1}


def prompt_parts(plan, task):
    world = world_for(plan, task)
    lines = [INTRO, "", "| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |",
             "|---|---|---|---|---|---|---|"]
    for i in world["order"]:
        item = world["items"][i]
        fields = [item[k] for k in ("id", "descriptor", "transmission", "seat_cover", "doors", "audit_marker")]
        lines.append("| " + " | ".join(fields + [world["record_labels"][task["value"]][i]]) + " |")
    target = world["items"][world["target_index"]]
    query = describe(target) if task["query"] == "profile" else "License plate: " + target["id"]
    return "\n".join(lines) + "\n\n", query, "\n" + QUESTION + "\n" + INSTRUCTIONS[task["arm"]]


def messages_for(plan, task):
    return [{"role": "user", "content": "".join(prompt_parts(plan, task))}]


def request_for(plan, task, config):
    result = {"model": config["model"], "messages": messages_for(plan, task), "temperature": 0}
    if config["provider"] == "mistral":
        result.update(max_tokens=config["max_tokens"][task["arm"]], reasoning_effort="none", stream=False)
    else:
        result.update(max_completion_tokens=config["max_completion_tokens"][task["arm"]], n=1, store=False)
    return result


def score_response(task, response):
    text = response.get("text", "")
    answer, start = answer_boundary(text) if response.get("complete") is True and isinstance(text, str) else (None, None)
    before = text[:start].strip() if start is not None else None
    strict = bool(re.fullmatch(r"ANSWER: [ABC]", text.strip().splitlines()[-1])) if answer else False
    answer_only = before == "" if answer else None
    filler_exact = before == FILLER if answer and task["arm"] == "filler" else None
    contract = {"direct": answer_only, "visible": bool(before), "filler": filler_exact}[task["arm"]]
    return {"answer": answer, "status": "complete" if answer else "invalid", "strict_answer_match": strict,
            "pre_answer_text": bool(before) if answer else None, "answer_only": answer_only,
            "output_contract_met": bool(answer and strict and contract), "filler_exact": filler_exact,
            "pre_answer_words": len(before.split()) if before is not None else None,
            "invalid_reason": None if answer else "incomplete_or_unparseable_terminal_answer"}
