"""Separate, hash-bound v4 plans. Scientific task construction remains v3's."""
import copy
import json
from pathlib import Path
from exception_pilot.core import digest, check_plan
from exception_pilot.storage import run_lock
from exception_continuation import core as legacy
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from . import PROTOCOL, TECHNICAL, ESTIMAND

ROOT = Path(__file__).resolve().parents[1]
CUTS = (0, 1, 8, 16, 32)
ARMS = ('unchanged', 'meaning_control', 'availability_repair', 'value_repair')

def source_hash():
    from exception_review.policy import code_hash
    files = {str(p.relative_to(ROOT)): p.read_text() for p in sorted((ROOT/'exception_study2_v4').rglob('*.py'))}
    files['REASONING_CONTINUATION_V4_PROTOCOL.md'] = (ROOT/'REASONING_CONTINUATION_V4_PROTOCOL.md').read_text()
    return digest(dict(v3_scientific_source=legacy.source_hash(), shared_judge_source=code_hash(), v4=files))

def config():
    return json.loads((ROOT/'configs/continuation_v4_qwen3_32b.json').read_text())

def validate_config(value):
    if set(value) != {'protocol', 'technical_gate', 'model'} or value['protocol'] != PROTOCOL or value['technical_gate'] != TECHNICAL:
        raise ValueError('An explicit v4 config is required')
    legacy.validate_config(value['model'])
    if 'model_profile' not in value['model']:
        raise ValueError('v4 requires the pinned Qwen profile (mock runs remain explicitly MOCK)')
    return copy.deepcopy(value)

def make_plan(phase='selection', configuration=None, selection_lock=None):
    cfg = validate_config(configuration or config())
    base = legacy.make_plan(phase, cfg['model'], selection_lock)
    base.pop('plan_hash')
    base.update(protocol=PROTOCOL, event_version='conditional-events-v4',
                technical_gate=TECHNICAL, technical_cuts=list(CUTS),
                estimand=ESTIMAND, source_hash=source_hash(),
                scientific_v3_source_hash=legacy.source_hash(), config_envelope=cfg,
                arm_definitions=list(ARMS), raw_logit_gate=False)
    base['plan_hash'] = digest(base)
    return base

def read_plan(output):
    path = Path(output)/'plan-v4.json'
    if not path.exists():
        raise ValueError('A fresh v4 plan is required; v3 runs cannot be imported')
    plan = sealed_read(path); plan.pop('artifact_hash'); check_plan(plan)
    if plan['protocol'] != PROTOCOL or plan != make_plan(plan['phase'], plan['config_envelope'], plan['selection_lock']):
        raise ValueError('v4 source/config/plan identity changed')
    return plan

def prepare(output, phase='selection', configuration=None, selection_output=None, policy_lock=None):
    lock = None
    if phase == 'confirmation':
        from .source import Source
        from exception_continuation.validation import calibration_result
        from .review.policy import freeze_policy
        if not selection_output or not policy_lock:
            raise ValueError('Confirmation requires complete selection and a frozen v4 review-policy lock')
        source = Source(selection_output)
        policy = sealed_read(policy_lock)
        selection = source.plan
        if selection['phase'] != 'selection' or not calibration_result(selection, source.collection)['passed']:
            raise ValueError('Selection calibration has not passed')
        from .review.artifacts import Review
        review = Review(Path(policy_lock).parent)
        if (review.source.hash != source.hash or policy.get('source_hash') != source.hash
                or policy.get('selection_collection_hash') != source.collection['artifact_hash']
                or policy.get('policy_hash') != review.policy['policy_hash']
                or policy.get('code_hash') != source_hash() or policy.get('no_2a_selection') is not True):
            raise ValueError('Selection review-policy lock differs')
        if validate_config(configuration or config()) != selection['config_envelope']:
            raise ValueError('Confirmation model/config must match selection')
        lock = dict(collection_hash=source.collection['artifact_hash'], source_hash=source.hash,
                    backend_hash=source.execution['backend_hash'], mode=source.execution['mode'],
                    policy_hash=review.policy['policy_hash'], policy_lock_hash=policy['artifact_hash'],
                    calibration=calibration_result(selection, source.collection))
    plan = make_plan(phase, configuration, lock)
    with run_lock(output) as out:
        if any((out/n).exists() for n in ('plan.json', 'validation.json', 'collection.json')):
            raise ValueError('Preserve legacy outputs; use a fresh v4 directory')
        freeze(out/'plan-v4.json', plan)
        # freeze adds an artifact seal, distinct from the scientific plan hash.
        if not (out/'technical-status-v4.json').exists():
            freeze(out/'technical-status-v4.json', dict(protocol=PROTOCOL, plan_hash=plan['plan_hash'],
                        technical_same_input_passed=None, measurement='NOT_RUN', real_model_status='PENDING'))
    return plan


def configure(model_dir, output):
    """Write a fresh machine-local config before planning, never mutate frozen plans."""
    root=Path(model_dir).expanduser().resolve()
    if not root.is_dir():raise ValueError('Use the existing pinned local model directory; no download is performed')
    value=config();value['model']['model_dir']=str(root);validate_config(value)
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
    return dict(status='CONFIGURED_OFFLINE',config_path=str(target.resolve()),model_path=str(root),
                model_content_verified=False,note='The existing pinned loader verifies every file before live execution.')
