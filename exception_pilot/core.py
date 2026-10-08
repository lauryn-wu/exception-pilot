"""Deterministic data, matched conditions, prompts, and answer parsing."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import random
import re

from . import PROTOCOL_VERSION

DESCRIPTORS = {
    "cold": ["Operates on polar ice", "Built for subzero temperatures", "Used at an Arctic station",
             "Equipped with snow tracks", "Designed for frozen terrain"],
    "warm": ["Operates in tropical forests", "Built for desert heat", "Used at an equatorial station",
             "Equipped for hot sand", "Designed for humid summers"],
}
ARMS = ("direct", "cot", "recall", "cot_record")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def rng_for(*parts):
    return random.Random(int(digest(parts), 16))


def source_digest():
    root = Path(__file__).parent
    return digest({p.name: p.read_text() for p in sorted(root.glob("*.py"))})


def load_config(path):
    config = json.loads(Path(path).read_text())
    required = {"stage", "n_lists", "seed", "model", "api_key_env", "temperature",
                "max_completion_tokens", "timeout_seconds"}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError("Config fields must exactly match the supplied example; never put keys in JSON.")
    for name in ("stage", "n_lists", "seed"):
        if type(config[name]) is not int:
            raise ValueError(f"{name} must be an integer")
    if config["stage"] not in (1, 2) or not 1 <= config["n_lists"] <= 1000:
        raise ValueError("stage must be 1 or 2; n_lists must be between 1 and 1000")
    if not isinstance(config["model"], str) or not re.fullmatch(
            r"gpt-4o-\d{4}-\d{2}-\d{2}", config["model"]):
        raise ValueError("This protocol requires a dated GPT-4o snapshot, not a reasoning-model alias.")
    if not isinstance(config["api_key_env"], str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z_0-9]*", config["api_key_env"]):
        raise ValueError("api_key_env must be an environment variable name")
    if type(config["temperature"]) not in (int, float) or config["temperature"] != 0:
        raise ValueError("Protocol v1 fixes temperature at 0")
    limits = config["max_completion_tokens"]
    if not isinstance(limits, dict) or set(limits) != {"direct", "cot"}:
        raise ValueError("max_completion_tokens requires direct and cot")
    if any(type(n) is not int or not 1 <= n <= 16384 for n in limits.values()):
        raise ValueError("Output limits must be integers in [1, 16384]")
    timeout = config["timeout_seconds"]
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout_seconds must be positive and finite")
    return config


def opposite(label):
    return "B" if label == "A" else "A"


def make_world(config, index, used_plates=None):
    """Five vehicles per climate; one exception per climate; balanced labels.

    Stage-specific RNG namespaces and license-plate prefixes guarantee disjoint
    item IDs in discovery and diagnostic stages for any configuration seed.
    """
    stage = config["stage"]
    used_plates = used_plates if used_plates is not None else set()
    rng = rng_for(PROTOCOL_VERSION, stage, config["seed"], index)
    cold_label = rng.choice(["A", "B"])
    items = []
    for climate in ("cold", "warm"):
        descriptions = DESCRIPTORS[climate].copy()
        rng.shuffle(descriptions)
        exception_index = rng.randrange(5)
        rule_label = cold_label if climate == "cold" else opposite(cold_label)
        for j, description in enumerate(descriptions):
            while True:
                prefix = "R" if stage == 1 else "D"
                plate = prefix + "".join(rng.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
                if plate not in used_plates:
                    used_plates.add(plate)
                    break
            item = {
                "id": plate,
                "descriptor": description,
                "transmission": rng.choice(["Manual", "Automatic"]),
                "seat_cover": rng.choice(["Cloth", "Vinyl"]),
                "doors": rng.choice(["Two", "Four"]),
                "climate": climate,
                "rule_label": rule_label,
                "is_exception": j == exception_index,
                "label": opposite(rule_label) if j == exception_index else rule_label,
            }
            items.append(item)
    orders = []
    for _ in range(3):
        order = list(range(10))
        rng.shuffle(order)
        orders.append(order)
    return {"id": f"s{stage}-list-{index:03d}", "items": items, "orders": orders}


def make_plan(config):
    used_plates = set()
    worlds = [make_world(config, i, used_plates) for i in range(config["n_lists"])]
    tasks = []
    for world in worlds:
        rng = rng_for("schedule", config["stage"], config["seed"], world["id"])
        if config["stage"] == 1:
            for round_index, order in enumerate(world["orders"]):
                for position, item_index in enumerate(order):
                    modes = ["direct", "cot"]
                    rng.shuffle(modes)
                    for mode in modes:
                        tasks.append({
                            "id": f"{world['id']}/{mode}/r{round_index+1}/p{position+1}",
                            "world_id": world["id"], "condition": mode,
                            "round": round_index + 1, "position": position + 1,
                            "item_index": item_index,
                        })
        else:
            for i, item in enumerate(world["items"]):
                if item["is_exception"]:
                    cells = [(background, arm) for background in ("conflict", "support")
                             for arm in ARMS]
                    rng.shuffle(cells)
                    for background, arm in cells:
                        tasks.append({
                            "id": f"{world['id']}/{i}/{background}/{arm}",
                            "world_id": world["id"], "condition": arm,
                            "background": background, "item_index": i,
                        })
    result = {"protocol_version": PROTOCOL_VERSION, "source_digest": source_digest(),
              "config": config, "worlds": worlds, "tasks": tasks}
    result["plan_hash"] = digest(result)
    return result


def check_plan(plan):
    content = {k: v for k, v in plan.items() if k != "plan_hash"}
    if plan.get("plan_hash") != digest(content):
        raise ValueError("Plan integrity check failed; do not edit a run's plan.json")


def world_for(plan, task):
    return next(w for w in plan["worlds"] if w["id"] == task["world_id"])


def items_for(world, background="conflict"):
    items = copy.deepcopy(world["items"])
    if background == "support":
        # Both target records remain unchanged. Only the eight other labels flip.
        for item in items:
            if not item["is_exception"]:
                item["label"] = opposite(item["label"])
    return items


def describe(item):
    # Ground truth and latent categories are intentionally excluded.
    return (f"License plate: {item['id']}\nDescription: {item['descriptor']}\n"
            f"Transmission: {item['transmission']}\nSeat cover: {item['seat_cover']}\n"
            f"Doors: {item['doors']}")


def question(item, condition):
    text = describe(item) + "\nWhich class, A or B, does this vehicle belong to?"
    text += "\nChoose the more likely class even if uncertain."
    if condition == "direct":
        return text + "\nReply with only A or B."
    return text + "\nWork through the classification, then put A or B alone on the final line."


def feedback(item, answer):
    verdict = "Correct." if answer == item["label"] else "Incorrect."
    return f"{verdict} Verified class for {item['id']}: {item['label']}."


def messages_for(plan, task, completed):
    world = world_for(plan, task)
    if plan["config"]["stage"] == 1:
        history = []
        previous_feedback = None
        for other in plan["tasks"]:
            if other["world_id"] != task["world_id"] or other["condition"] != task["condition"]:
                continue
            item = world["items"][other["item_index"]]
            prompt = question(item, task["condition"])
            if previous_feedback:
                prompt = previous_feedback + "\n\n" + prompt
            history.append({"role": "user", "content": prompt})
            if other["id"] == task["id"]:
                return history
            record = completed.get(other["id"])
            if not record or record["status"] != "complete":
                raise ValueError("A dependent trial has no valid previous answer")
            history.append({"role": "assistant", "content": record["response"]["text"]})
            previous_feedback = feedback(item, record["answer"])
        raise ValueError("Unknown task")
    items = items_for(world, task["background"])
    target = items[task["item_index"]]
    rows = [describe(items[i]) + f"\nVerified class: {items[i]['label']}"
            for i in world["orders"][0]]
    context = ("These are records of previously observed vehicles. Every record is accurate. "
               "An individual vehicle's class is fixed, and its license plate identifies it.\n\n"
               + "\n\n".join(rows))
    if task["condition"] == "recall":
        prompt = (f"What verified class was recorded for license plate {target['id']}? "
                  "Reply with only A or B.")
    else:
        prompt = question(target, task["condition"])
        if task["condition"] == "cot_record":
            prompt = ("Repeated record from the evidence above:\n" + describe(target)
                      + f"\nVerified class: {target['label']}\n\n" + prompt)
    # Every diagnostic is a fresh call; no diagnostic answer becomes evidence.
    return [{"role": "user", "content": context + "\n\n" + prompt}]


def parse_answer(text):
    """Only the final nonempty line; never search a rationale for A/B tokens."""
    if not isinstance(text, str) or not text.strip():
        return None
    last = text.strip().splitlines()[-1].strip()
    last = last.replace("**", "").replace("`", "").strip()
    match = re.fullmatch(r"(?:[Ff]inal answer:\s*|[Aa]nswer:\s*)?[\"'‘’]?([AB])[\"'‘’]?[.!]?", last)
    return match.group(1) if match else None


def task_meta(plan, task):
    item = world_for(plan, task)["items"][task["item_index"]]
    return {"world_id": task["world_id"], "condition": task["condition"],
            "item_id": item["id"], "round": task.get("round"),
            "background": task.get("background"), "is_exception": item["is_exception"],
            "expected": item["label"], "rule_label_in_conflict": item["rule_label"]}


def payload_for(config, task, messages):
    kind = "cot" if task["condition"] in ("cot", "cot_record") else "direct"
    return {"model": config["model"], "messages": messages, "temperature": config["temperature"],
            "max_completion_tokens": config["max_completion_tokens"][kind], "store": False,
            "n": 1}
