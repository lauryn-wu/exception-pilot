"""Frozen v5 design; the legacy pinned loader configuration is not a scientific cap."""
import copy
import itertools
import json
from pathlib import Path
from exception_pilot.core import digest, rng_for, check_plan
from exception_pilot.storage import run_lock
from exception_counterfactual.core import make_world
from exception_continuation import core as legacy
from exception_study2_v4.core import source_hash as v4_hash
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from . import PROTOCOL, TECHNICAL, BUDGET, ARMS

ROOT = Path(__file__).resolve().parents[1]
CUTS = (0, 1, 8, 16, 32)  # Technical only, identical to v4.
CHECKPOINTS = (0, 128, 256, 512, 1024)
V4_HASH = '913f64efa3f12a1a787575c14c7670e072e250d7e8a3690a9957cfa70bb88e78'
CALIBRATION = dict(min_direct_correct=20, min_matched_pattern_errors=3, min_error_worlds=2)
COHORT_MIN_WORLDS = 2  # Coverage gate, not a power claim.
LOOKUP = 'According to the table, what is the value in the Verified class column for license plate {plate}?'

def source_hash():
    if v4_hash() != V4_HASH:
        raise ValueError('Historical v4 scientific source changed')
    files = {str(p.relative_to(ROOT)): p.read_text() for p in sorted((ROOT/'exception_study2_v5').rglob('*.py'))}
    files['REASONING_CONTINUATION_V5_PROTOCOL.md'] = (ROOT/'REASONING_CONTINUATION_V5_PROTOCOL.md').read_text()
    return digest(dict(v4=V4_HASH, v5=files))

def config():
    return json.loads((ROOT/'configs/continuation_v5_qwen3_32b.json').read_text())

def validate_config(cfg):
    default = config()
    expected = copy.deepcopy(default)
    expected['model']['model_dir'] = cfg.get('model', {}).get('model_dir')
    if cfg != expected:
        raise ValueError('Exact v5 settings required; only the local model path may vary')
    legacy.validate_config(cfg['model'])
    if not cfg['model']['model_dir'] or cfg['scientific_budget'] != BUDGET:
        raise ValueError('Local path and explicit 2048 scientific budget required')
    return copy.deepcopy(cfg)

def make_plan(phase='selection', configuration=None, selection_lock=None):
    cfg = validate_config(configuration or config())
    if phase not in ('selection', 'confirmation') or (phase == 'confirmation' and not selection_lock):
        raise ValueError('Confirmation needs a selection protocol lock')
    seed, reps, plate_prefix = (20261015051, 1, 'V5S') if phase == 'selection' else (20261015052, 4, 'V5C')
    roles = list(itertools.product(itertools.permutations('ABC'), ('cold','warm'), range(reps)))
    rng_for(PROTOCOL, phase, 'world-order').shuffle(roles)
    worlds, tasks, used = [], [], set()
    for index, (classes, climate, replicate) in enumerate(roles):
        w = make_world({'seed': seed}, index, used)
        wid = f'{phase}-v5-{index:03d}'
        for item in w['items']:
            item['id'] = plate_prefix + item['id'][1:]
        target = next(i for i in w['target_indices'] if w['items'][i]['climate'] == climate)
        labels = [classes[2]] * 10
        opposite = [classes[0]] * 3 + [classes[1]] * 2
        rng = rng_for(PROTOCOL, phase, index)
        rng.shuffle(opposite)
        for i, item in enumerate(w['items']):
            item['audit_marker'] = rng.choice('XYZ')
            if item['climate'] != climate:
                labels[i] = opposite.pop()
        order = [i for i in w['order'] if i != target] + [target]
        cells = []
        for variant, framing, arm in itertools.product(range(2), ('original','lookup'), ('direct','visible')):
            ls = labels.copy(); ls[target] = classes[variant]
            rows = ['| License plate | Description | Transmission | Seat cover | Doors | Audit marker | Verified class |',
                    '|---|---|---|---|---|---|---|']
            for i in order:
                item = w['items'][i]
                rows.append('| ' + ' | '.join([item[k] for k in ('id','descriptor','transmission','seat_cover','doors','audit_marker')] + [ls[i]]) + ' |')
            plate = w['items'][target]['id']
            question = legacy.QUESTION if framing == 'original' else LOOKUP.format(plate=plate)
            prompt = legacy.INTRO + '\n\n' + '\n'.join(rows) + '\n\nLicense plate: ' + plate + '\n' + question + '\n' + legacy.INSTRUCTIONS[arm]
            cells.append(dict(id=f'{wid}/v{variant}/{framing}/{arm}', world=wid, variant=variant,
                              framing=framing, arm=arm, expected=classes[variant], pattern=classes[2],
                              prompt=prompt, table='\n'.join(rows), target_plate=plate, target_row=rows[-1]))
        rng.shuffle(cells); tasks.extend(cells)
        worlds.append(dict(id=wid, items=w['items'], target=target, order=order, roles=list(classes), climate=climate, replicate=replicate))
    plan = dict(protocol=PROTOCOL, technical_gate=TECHNICAL, source_hash=source_hash(), v4_source_hash=V4_HASH,
                phase=phase, config=cfg['model'], config_envelope=cfg, scientific_budget=BUDGET,
                seed=seed, worlds=worlds, tasks=tasks, checkpoints=list(CHECKPOINTS),
                technical_cuts=list(CUTS), selection_lock=selection_lock, calibration=CALIBRATION,
                arms=list(ARMS), cue_policy='both frozen cues at every eligible fixed/event/edited checkpoint')
    plan['plan_hash'] = digest(plan)
    return plan

def read_plan(output):
    p = sealed_read(Path(output)/'plan-v5.json'); p.pop('artifact_hash'); check_plan(p)
    if p != make_plan(p['phase'], p['config_envelope'], p['selection_lock']):
        raise ValueError('v5 source/config/plan identity changed')
    return p

def prepare(output, phase='selection', configuration=None, selection_output=None, policy_lock=None):
    cfg = validate_config(configuration or config()); lock = None
    if phase == 'confirmation':
        from .runner import Source
        from .reporting import behavioral_report
        from .review.workflow import validate_lock
        source = Source(selection_output)
        lock = validate_lock(source, policy_lock)
        if source.plan['phase'] != 'selection' or not behavioral_report(source.root)['calibration']['passed']:
            raise ValueError('Complete selection calibration required')
        if cfg != source.plan['config_envelope']:
            raise ValueError('Confirmation model configuration differs')
    out = Path(output)
    if out.exists() and any(out.iterdir()) and not (out/'plan-v5.json').exists():
        raise ValueError('Use a fresh v5 output directory; preserve historical artifacts')
    plan = make_plan(phase, cfg, lock)
    with run_lock(out):
        freeze(out/'plan-v5.json', plan)
    return plan

def configure(model_dir, output):
    root = Path(model_dir).expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Existing persistent local model directory required; no download')
    cfg = config(); cfg['model']['model_dir'] = str(root); validate_config(cfg)
    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(cfg, f, indent=2); f.write('\n')
    return dict(config=str(path), model_contents_verified=False, next_stage='STOP')
