"""Freeze two fresh API arms; no Qwen output becomes a GPT control."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze, sha
from exception_study2_native import FINAL_INSTRUCTION
from exception_study2_native.planning import fresh
from exception_study2_source_report.integrity import separate, revision
from exception_study2_explanation.planning import contract as qwen_explanation_contract
from . import VERSION, SETTINGS, INSTRUCTION, SOURCE_ZIP, DOCUMENTATION, PRICING, SCHEDULE_SEED
from .source import Source, sha_bytes


def contract():
    here = Path(__file__).parent; root = here.parent
    helpers = ('exception_review/providers.py','exception_review/artifacts.py','exception_pilot/core.py',
               'exception_pilot/storage.py','exception_study2_v5/journal.py','exception_study2_native/recovery.py',
               'exception_study2_source_report/reporting.py','exception_continuation/runner.py')
    return digest(dict(modules={p.name:sha(p) for p in sorted(here.glob('*.py'))},
                       protocol=sha(root/'STUDY2_GPT_EXPLANATION_V1.md'),
                       qwen_explanation_contract=qwen_explanation_contract(), helpers={p:sha(root/p) for p in helpers}))


def plan_fields(src):
    cases = sorted(src.cases, key=lambda r: digest(dict(seed=SCHEDULE_SEED, cell_id=r['cell']['id'])))
    worlds = sorted({r['cell']['world'] for r in cases})
    requests = []
    for original in cases:
        old = original['request']['prompt']
        if not old.endswith(FINAL_INSTRUCTION):
            raise ValueError('Source terminal instruction differs')
        prefix = old[:-len(FINAL_INSTRUCTION)]
        pair_id = original['cell']['id'].removesuffix('/thinking-0')
        # Six worlds per block: alternate first arm by world, balanced within each relation/block.
        arms = ('direct','explanation') if worlds.index(original['cell']['world']) % 2 == 0 else ('explanation','direct')
        for arm in arms:
            prompt = old if arm == 'direct' else prefix + INSTRUCTION
            cell = {k:deepcopy(original['cell'][k]) for k in ('world','block','variant','cue_state','relation','expected','pattern','target_plate','table')}
            cell.update(id=VERSION+'/'+pair_id+'/'+arm, pair_id=pair_id, arm=arm, prompt=prompt)
            payload = dict(deepcopy(SETTINGS), input=[dict(role='user', content=prompt)])
            q = dict(protocol=VERSION, cell_id=cell['id'], pair_id=pair_id, arm=arm,
                     source_binding_hash=digest(src.binding), source_reference=src.reference(original),
                     prompt_sha256=sha_bytes(prompt.encode()), preceding_prompt_sha256=sha_bytes(prefix.encode()), payload=payload)
            requests.append(dict(sequence=len(requests), cell=cell, request=q, request_hash=digest(q)))
    if len(requests) != 192 or len({r['request_hash'] for r in requests}) != 192:
        raise ValueError('Expected 192 unique fresh requests')
    counts = Counter((r['cell']['arm'],r['cell']['relation']) for r in requests)
    if set(counts.values()) != {48} or len(counts) != 4:
        raise ValueError('Wrong arm/condition counts')
    return dict(protocol=VERSION, code_contract=contract(), source=src.binding, requests=requests,
                planned_requests=192, fresh_responses_per_arm=96, reused_model_outputs=0,
                api_settings=deepcopy(SETTINGS), documentation=deepcopy(DOCUMENTATION), pricing=deepcopy(PRICING),
                maximum_output_tokens=192*4096, input_token_count=None,
                schedule=dict(seed=SCHEDULE_SEED, seed_role='Scheduling only; no model-generation seed is sent.',
                              method='Hash-sort matched pairs, adjacent opposite arms; alternate first arm by sorted world index.',
                              direct_first_pairs=48, explanation_first_pairs=48),
                request_budget=192, additional_smoke_calls=0)


def prepare(source, output):
    archive = Path(source).resolve(); out = separate(output, archive.parent)
    src = Source(archive); fields = plan_fields(src)
    with run_lock(out):
        fresh(out)
        (out/'source-evidence').mkdir()
        with (out/'source-evidence'/SOURCE_ZIP).open('xb') as handle:
            handle.write(src.data)
        plan = freeze(out/'plan.json', dict(fields, code_revision=revision()))
        freeze(out/'source-validation.json', dict(source=src.binding, archived_paths_used=False,
                                                  tokenizer_loads=0, model_loads=0, reused_model_outputs=0))
    return dict(plan_hash=plan['artifact_hash'], requests=192, pairs=96, model_loads=0, network_calls=0)


class Context:
    def __init__(self, output):
        self.out = Path(output).resolve(); self.plan = sealed_read(self.out/'plan.json')
        if self.plan['protocol'] != VERSION or self.plan['code_contract'] != contract():
            raise ValueError('GPT code/protocol changed; preserve this frozen run')
        self.source = Source(self.out/'source-evidence'/SOURCE_ZIP)
        expected = plan_fields(self.source)
        if any(self.plan.get(k) != v for k,v in expected.items()):
            raise ValueError('Frozen GPT plan differs from source/settings/schedule')
        self.requests = self.plan['requests']
