"""Frozen, paired next-turn interventions on observed explanation contradictions."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import re

from exception_study_support.core import content_digest, source_digest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = 'verified-facts-downstream-v1'
SNAPSHOT_DIGEST = '5a491edff3df2412a724b313966f8e8da2aadb8bde2e699663f59760e06daa3f'
ARMS = ('original', 'availability_repair', 'missing_synonym', 'value_repair', 'endpoints_only')
LABELS = ('A', 'B', 'C', 'MISSING')
DEFAULT_CONFIG = {
    'protocol': PROTOCOL_VERSION, 'model': 'gpt-4o-2024-08-06',
    'api_key_env': 'OPENAI_API_KEY', 'temperature': 0, 'max_completion_tokens': 64,
    'max_total_attempts': 378, 'timeout_seconds': 120, 'repetitions': 3,
    'schedule_seed': 728139,
}


def load_config(path):
    config = json.loads(Path(path).read_text())
    validate_config(config)
    return config


def validate_config(config):
    if config != DEFAULT_CONFIG:
        raise ValueError('This frozen study requires configs/downstream_gpt4o.json unchanged')
    if any(type(config[k]) is not int for k in ('max_completion_tokens', 'max_total_attempts', 'repetitions', 'schedule_seed')):
        raise ValueError('Integer configuration fields must be integers')


def table_cell(prompt, plate):
    """Obtain the answer from the original table, independently of source scores."""
    lines = [line for line in prompt.splitlines() if line.startswith('|')]
    if len(lines) != 12:
        raise ValueError('Expected the original ten-row table')
    header = [x.strip() for x in lines[0].strip('|').split('|')]
    if len(set(header)) != len(header) or 'Verified class' not in header or 'License plate' not in header:
        raise ValueError('Ambiguous original table header')
    rows = [[x.strip() for x in line.strip('|').split('|')] for line in lines[2:]]
    if any(len(row) != len(header) for row in rows):
        raise ValueError('Malformed original table')
    matches = [row for row in rows if row[header.index('License plate')] == plate]
    if len(matches) != 1:
        raise ValueError('Target plate must occur once')
    cell = matches[0][header.index('Verified class')]
    if cell not in LABELS:
        raise ValueError('Unexpected original class cell')
    return cell


def _validate_case(case):
    request, response = case['source_request'], case['source_response']
    if (request['model'] != DEFAULT_CONFIG['model'] or len(request['messages']) != 1
            or request['messages'][0]['role'] != 'user'):
        raise ValueError('Unexpected source conversation or model')
    if content_digest(request) != case['request_digest'] or content_digest(response) != case['response_digest']:
        raise ValueError('Source request/response digest mismatch')
    text = response['text']
    if hashlib.sha256(text.encode()).hexdigest() != case['text_sha256']:
        raise ValueError('Source text digest mismatch')
    if not response['complete'] or response['finish_reason'] != 'stop':
        raise ValueError('Original source response was incomplete')
    if table_cell(request['messages'][0]['content'], case['item_id']) != case['expected']:
        raise ValueError('Source table and frozen answer key differ')
    lines = text.splitlines()
    if lines[0] != case['copied_line'] or lines[-1] != case['answer_line']:
        raise ValueError('Original endpoint lines differ')
    if case['copied_line'] != 'COPIED: ' + case['expected']:
        raise ValueError('All selected sources require a correct literal copy')
    if not re.fullmatch(r'ANSWER: [ABC]', case['answer_line']):
        raise ValueError('Unexpected original prediction line')
    is_missing = case['cohort'] == 'genuine_missing_control'
    if (case['expected'] == 'MISSING') != is_missing:
        raise ValueError('Missingness cohort and source table disagree')
    if case['cohort'] in ('contradiction', 'availability_control') and case['answer_line'] != 'ANSWER: ' + case['expected']:
        raise ValueError('Main and availability controls require correct original answers')
    if case['cohort'] == 'wrong_final_diagnostic' and case['answer_line'] == 'ANSWER: ' + case['expected']:
        raise ValueError('Wrong-final diagnostic requires an original error')
    previous_end = len(lines[0])
    for span in case['spans']:
        start, end = span['start'], span['end']
        if start < previous_end or end > len(text) - len(lines[-1]) or text[start:end] != 'MISSING':
            raise ValueError('Invalid or overlapping annotated target span')
        line_start = text.rfind('\n', 0, start) + 1
        line_end = text.find('\n', end)
        line_end = len(text) if line_end == -1 else line_end
        if text[line_start:line_end] != span['evidence_line'] or case['item_id'] not in span['evidence_line']:
            raise ValueError('Annotation does not identify this target')
        if any(span[arm] != replacement for arm, replacement in (
                ('availability_repair', 'RECORDED'), ('missing_synonym', 'UNRECORDED'),
                ('value_repair', 'recorded as ' + case['expected']))):
            raise ValueError('Unexpected span replacement')
        previous_end = end
    if bool(case['spans']) != (case['cohort'] in ('contradiction', 'wrong_final_diagnostic')):
        raise ValueError('Intervention annotation and cohort disagree')
    if case['spans'] and len(case['spans']) != len(re.findall(r'\bMISSING\b', text)):
        raise ValueError('Positive source has an unannotated MISSING occurrence')


def load_snapshot():
    snapshot = json.loads((ROOT / 'exception_downstream/source_snapshot.json').read_text())
    if content_digest(snapshot) != SNAPSHOT_DIGEST:
        raise ValueError('Frozen downstream source snapshot changed')
    if len(snapshot['inventory']) != 192 or len({r['id'] for r in snapshot['inventory']}) != 192:
        raise ValueError('Source inventory must cover all 192 column-study class-copy returns')
    cases = snapshot['cases']
    if Counter(c['cohort'] for c in cases) != {'contradiction': 13, 'availability_control': 13, 'genuine_missing_control': 9, 'wrong_final_diagnostic': 1}:
        raise ValueError('Frozen cohort sizes differ')
    if len({c['id'] for c in cases}) != 36:
        raise ValueError('Duplicate parent cases')
    for case in cases:
        _validate_case(case)
    primary = [c for c in cases if c['cohort'] == 'contradiction']
    if len({c['world_id'] for c in primary}) != 9 or sum(len(c['spans']) for c in primary) != 46:
        raise ValueError('Main-world or annotation count differs')
    return snapshot


def edited_text(case, arm):
    original = case['source_response']['text']
    if arm == 'original':
        return original
    if arm == 'endpoints_only':
        return case['copied_line'] + '\n\n' + case['answer_line']
    if arm not in ARMS or not case['spans']:
        raise ValueError('Unsupported edit for this parent')
    text = original
    for span in reversed(case['spans']):
        text = text[:span['start']] + span[arm] + text[span['end']:]
    if text.splitlines()[0] != case['copied_line'] or text.splitlines()[-1] != case['answer_line']:
        raise ValueError('An intervention modified an endpoint')
    return text


def make_plan(config):
    validate_config(config)
    snapshot = load_snapshot()
    cases = deepcopy(snapshot['cases'])
    by_world = {}
    for case in cases:
        by_world.setdefault(case['world_id'], []).append(case)
    rng = random.Random(config['schedule_seed'])
    world_ids = sorted(by_world)
    rng.shuffle(world_ids)
    tasks = []
    # Randomize within each world block; every arm/repetition is an independent branch.
    for world_id in world_ids:
        block = []
        for case in sorted(by_world[world_id], key=lambda c: c['id']):
            arms = ARMS if case['spans'] else ('original', 'endpoints_only')
            for arm in arms:
                for repetition in range(1, config['repetitions'] + 1):
                    block.append({'id': case['id'] + '/' + arm + '/r' + str(repetition),
                                  'case_id': case['id'], 'world_id': world_id, 'cohort': case['cohort'],
                                  'arm': arm, 'repetition': repetition, 'expected': case['expected']})
        rng.shuffle(block)
        tasks.extend(block)
    if len(tasks) != 342:
        raise ValueError('Unexpected frozen call count')
    plan = {'protocol_version': PROTOCOL_VERSION, 'source_digest': source_digest(ROOT, 'exception_downstream',
                extra_paths=('configs/downstream_gpt4o.json', 'DOWNSTREAM_PROTOCOL.md')),
            'snapshot_digest': SNAPSHOT_DIGEST, 'config': deepcopy(config), 'worlds': world_ids,
            'cases': cases, 'tasks': tasks,
            'analysis_plan': {'primary_cohort': 'contradiction', 'primary_metric': 'false_missing',
                'primary_contrast': ['original', 'availability_repair'], 'weighting': 'repetition then case then equal world',
                'bootstrap_replicates': 10000, 'bootstrap_seed': 481602, 'scientific_success_gate': None}}
    plan['plan_hash'] = content_digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / 'plan.json').read_text())
    if plan != make_plan(plan['config']):
        raise ValueError('Saved plan, source, configuration or schedule drifted')
    return plan


def _case(plan, task):
    return next(c for c in plan['cases'] if c['id'] == task['case_id'])


def request_for(plan, task):
    case = _case(plan, task)
    return {'model': plan['config']['model'], 'temperature': plan['config']['temperature'],
            'max_completion_tokens': plan['config']['max_completion_tokens'], 'n': 1, 'store': False,
            'messages': deepcopy(case['source_request']['messages']) + [
                {'role': 'assistant', 'content': edited_text(case, task['arm'])},
                {'role': 'user', 'content': "What is written in " + case['item_id'] + "'s Verified class cell? Reply with exactly one of A, B, C, or MISSING."}]}


def task_meta(plan, task):
    case = _case(plan, task)
    return deepcopy(task) | {k: case[k] for k in ('source_id', 'source_run', 'item_id', 'schema', 'value', 'target_position', 'text_sha256')}


def score_response(task, response):
    text = response.get('text', '')
    trimmed = text.strip() if isinstance(text, str) else ''
    valid = bool(response.get('complete') and response.get('model_identity') in ('match', 'simulated') and trimmed in LABELS)
    answer = trimmed if valid else None
    return {'status': 'complete' if valid else 'invalid', 'answer': answer,
            'correct': answer == task['expected'] if valid else None,
            'false_missing': (answer == 'MISSING' and task['expected'] != 'MISSING') if valid else None,
            'wrong_class': (answer in ('A', 'B', 'C') and answer != task['expected']) if valid else None,
            'strict_format': trimmed in LABELS}


def mock_complete(plan, task):
    return {'model': 'MOCK-NOT-A-MODEL', 'choices': [{'message': {'role': 'assistant', 'content': task['expected']},
            'finish_reason': 'stop'}], 'usage': {}}
