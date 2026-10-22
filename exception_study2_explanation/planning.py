"""Freeze source-derived requests; no world generation, calibration, or GPU work."""
import hashlib
from copy import deepcopy
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze, sha
from exception_study2_current.adapter import Tokenizer
from exception_study2_current.planning import contract as original_contract
from exception_study2_native import FINAL_INSTRUCTION
from exception_study2_native.planning import fresh
from exception_study2_source_report.integrity import separate, revision
from . import VERSION, INSTRUCTION, SOURCE_ZIP, SOURCE_CONTRACT, ENVIRONMENT
from .source import Source, match_key


def contract():
    here = Path(__file__).parent
    return digest(dict(modules={p.name: sha(p) for p in sorted(here.glob('*.py'))},
                       protocol=sha(here.parent/'STUDY2_CURRENT_QWEN_EXPLANATION_V1.md'),
                       original_contract=original_contract()))


def requests_from_source(source, tok):
    requests = []; controls = []
    for off in source.off:
        on = source.on[match_key(off['cell'])]
        refs = dict(direct=source.reference(off), native_on=source.reference(on))
        controls.extend(refs.values())
        old = off['request']; prompt = old['prompt']
        if not prompt.endswith(FINAL_INSTRUCTION):
            raise ValueError('Original answer-only suffix differs')
        preceding = prompt[:-len(FINAL_INSTRUCTION)]
        new_prompt = preceding + INSTRUCTION
        if new_prompt[:-len(INSTRUCTION)].encode('utf-8') != preceding.encode('utf-8'):
            raise ValueError('Preceding prompt bytes changed')
        cell = deepcopy(off['cell'])
        cell.update(id=VERSION + '/' + cell['id'], arm='explicit_explanation',
                    prompt=new_prompt, prompt_hash=digest(new_prompt))
        q = deepcopy(old); ids = tok.render(new_prompt, False)
        q.update(protocol=VERSION, cell_id=cell['id'], prompt=new_prompt, prompt_hash=digest(new_prompt),
                 input_ids=ids, input_hash=digest(ids), rendered_input=tok.decode_all(ids),
                 controls=refs, source_binding_hash=digest(source.binding),
                 preceding_prompt_utf8_sha256=hashlib.sha256(preceding.encode('utf-8')).hexdigest(),
                 resolved_sampling=deepcopy(source.operations[off['cell']['id']]['result']['resolved_sampling']))
        if len(ids) + q['budget'] > min(tok.context_limit, q['engine']['max_model_len']):
            raise ValueError('Explanation prompt exceeds unchanged context cap')
        # Every decoding, seed, budget, template and engine field comes from the original request.
        changed = {'protocol', 'cell_id', 'prompt', 'prompt_hash', 'input_ids', 'input_hash', 'rendered_input'}
        if any(q[k] != v for k, v in old.items() if k not in changed):
            raise ValueError('A matched source setting changed')
        if q['thinking'] is not False or q['budget'] != 4096 or q['prefix_token_ids']:
            raise ValueError('Expected uninterrupted OFF generation at the source budget')
        requests.append(dict(cell=cell, request=q, request_hash=digest(q)))
    if len(requests) != 96 or len(controls) != 192 or len({x['cell_id'] for x in controls}) != 192:
        raise ValueError('Wrong scientific/control population')
    return requests, controls


def plan_fields(source, tok):
    requests, controls = requests_from_source(source, tok)
    return dict(protocol=VERSION, code_contract=contract(), source=source.binding,
                requests=requests, controls=controls, planned_new_responses=96, historical_controls=192,
                total_input_token_occurrences=sum(len(r['request']['input_ids']) for r in requests),
                maximum_output_tokens=sum(r['request']['budget'] for r in requests),
                runtime_environment=ENVIRONMENT, backend=source.execution['backend'],
                backend_hash=source.execution['backend_hash'], tokenizer=tok.identity,
                stop_after=96, smoke_new_requests=0)


def prepare(source, output, tokenizer_dir=None, model_dir=None):
    archive = Path(source).resolve()
    # Read the existing configuration to select paths; no guessed model directory.
    import json, zipfile
    with zipfile.ZipFile(archive) as z:
        locations = json.loads(z.read('locations.json'))
    tokenizer_dir = tokenizer_dir or locations['tokenizer']
    model_dir = model_dir or locations['model']
    out = separate(output, archive.parent, tokenizer_dir, model_dir)
    tok = Tokenizer(tokenizer_dir); src = Source(archive, tok)
    value = plan_fields(src, tok)
    with run_lock(out):
        fresh(out)
        folder = out/'source-evidence'; folder.mkdir()
        for name, data in src.inputs.items():
            with (folder/name).open('xb') as handle:
                handle.write(data)
        plan = freeze(out/'plan.json', dict(value, code_revision=revision()))
        freeze(out/'locations.json', dict(model=str(Path(model_dir).resolve()), tokenizer=str(Path(tokenizer_dir).resolve())))
        freeze(out/'source-validation.json', dict(source=src.binding, original_contract=SOURCE_CONTRACT,
               verified_scientific_returns=384, verified_smoke_returns=8, verified_sealed_files=src.seals_checked,
               original_wording_controls=192, historical_correct=sum(src.scores[x['cell_id']]['correct'] for x in value['controls']),
               uses_archived_absolute_paths=False, semantic_annotations='not_reviewed'))
    return dict(plan_hash=plan['artifact_hash'], new_requests=96, reused_controls=192, smoke_requests=0,
                input_tokens=value['total_input_token_occurrences'], maximum_output_tokens=value['maximum_output_tokens'], model_loads=0)


class Context:
    def __init__(self, output, tokenizer_dir=None, model_dir=None):
        self.out = Path(output).resolve()
        self.plan = sealed_read(self.out/'plan.json')
        if self.plan['protocol'] != VERSION or self.plan['code_contract'] != contract():
            raise ValueError('Explanation code/protocol changed; preserve frozen run')
        self.locations = sealed_read(self.out/'locations.json')
        # Explicit local overrides support moving a bundle; sealed historical paths stay untouched.
        self.tokenizer_dir = tokenizer_dir or self.locations['tokenizer']
        self.model_dir = model_dir or self.locations['model']
        self.tok = Tokenizer(self.tokenizer_dir)
        self.source = Source(self.out/'source-evidence'/SOURCE_ZIP, self.tok)
        expected = plan_fields(self.source, self.tok)
        if any(self.plan.get(k) != v for k, v in expected.items()):
            raise ValueError('Frozen explanation source/request/settings changed')
        proof = sealed_read(self.out/'source-validation.json')
        if proof['source'] != self.source.binding or proof['original_contract'] != original_contract():
            raise ValueError('Source validation binding differs')
        self.requests = self.plan['requests']
        self.by_cell = {r['cell']['id']: r for r in self.requests}
