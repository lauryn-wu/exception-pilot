"""A frozen, paired history control for the existing downstream cases.

The historical classification responses are replayed unchanged. Both factual
question arms are newly collected; neither arm generates a new classification.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import re

from exception_downstream import core as downstream
from exception_study_support.core import content_digest, source_digest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = 'verified-facts-downstream-history-v1'
PLAN_SCHEMA_VERSION = 'downstream-history-plan-v1'
CONTEXT_EXTRACTION_VERSION = 'validated-intro-table-v1'
SNAPSHOT_DIGEST = downstream.SNAPSHOT_DIGEST
ARMS = ('history_present', 'history_absent')
COHORTS = ('contradiction', 'availability_control', 'genuine_missing_control',
           'wrong_final_diagnostic')
LABELS = downstream.LABELS
DEFAULT_CONFIG = {
    'protocol': PROTOCOL_VERSION, 'model': 'gpt-4o-2024-08-06',
    'api_key_env': 'OPENAI_API_KEY', 'temperature': 0,
    'max_completion_tokens': 64, 'max_total_attempts': 240,
    'timeout_seconds': 120, 'repetitions': 3, 'schedule_seed': 728140,
}

# These strings validate the *existing* source boundary; they are not newly
# supplied instructions. The standalone context is sliced from the original.
SOURCE_INTRO = (
    "These are records of previously observed vehicles. Every record is accurate. "
    "An individual vehicle's class is fixed, and its license plate identifies it. "
    "The audit marker is an administrative code assigned independently of class. "
    "MISSING means the verified class has not been recorded. If that cell is MISSING, "
    "make your best prediction from the other records."
)
SOURCE_CLASSIFICATION_QUESTION = 'Which class, A, B, or C, does this vehicle belong to?'
SOURCE_COPY_INSTRUCTION = (
    "First copy the target vehicle's Verified class cell exactly, using COPIED: followed "
    "by the cell value alone on the first line. Do not explain before that line. "
    "Think step by step, then put ANSWER: followed by A, B, or C alone on the final line."
)
SOURCE_COLUMNS = {
    'full': ('License plate', 'Description', 'Transmission', 'Seat cover', 'Doors',
             'Audit marker', 'Verified class'),
    'other_attributes': ('License plate', 'Transmission', 'Seat cover', 'Doors',
                         'Audit marker', 'Verified class'),
}
PROFILE_COLUMNS = ('Description', 'Transmission', 'Seat cover', 'Doors')


def _text_sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def load_config(path):
    config = json.loads(Path(path).read_text())
    validate_config(config)
    return config


def validate_config(config):
    if (not isinstance(config, dict) or config != DEFAULT_CONFIG
            or any(type(config.get(key)) is not type(value)
                   for key, value in DEFAULT_CONFIG.items())):
        raise ValueError('This frozen study requires configs/downstream_history_gpt4o.json unchanged')


def split_source_prompt(case):
    """Return literal (intro + table, classification tail), or reject the source.

    Validate every removed line against the known source format. In particular,
    the earlier explanation-study cases contain a feature profile, whose values
    must match the target row. Never silently discard an unrecognized tail.
    """
    request = case.get('source_request', {})
    messages = request.get('messages', [])
    if (len(messages) != 1 or messages[0].get('role') != 'user'
            or not isinstance(messages[0].get('content'), str)):
        raise ValueError('Expected exactly one original user message')
    original = messages[0]['content']
    parts = original.split('\n\n')
    if len(parts) != 3 or parts[0] != SOURCE_INTRO:
        raise ValueError('Unrecognized source introduction or section boundaries')
    intro, table, tail = parts
    columns = SOURCE_COLUMNS.get(case.get('schema'))
    if columns is None:
        raise ValueError('Unrecognized source table schema')
    lines = table.split('\n')
    header = '| ' + ' | '.join(columns) + ' |'
    separator = '|' + '|'.join('---' for _ in columns) + '|'
    if len(lines) != 12 or lines[:2] != [header, separator]:
        raise ValueError('Expected the original schema and ten-row table')
    rows = []
    for line in lines[2:]:
        values = line[2:-2].split(' | ')
        if (not line.startswith('| ') or not line.endswith(' |')
                or len(values) != len(columns)
                or any(not value or '|' in value for value in values)
                or line != '| ' + ' | '.join(values) + ' |'):
            raise ValueError('Unrecognized source table row')
        rows.append(dict(zip(columns, values)))
    plates = [row['License plate'] for row in rows]
    if len(set(plates)) != 10:
        raise ValueError('Source table plates must be unique')
    matches = [row for row in rows if row['License plate'] == case.get('item_id')]
    if len(matches) != 1:
        raise ValueError('Target must occur exactly once in the source table')
    target = matches[0]
    if (target['Verified class'] not in LABELS
            or target['Verified class'] != case.get('expected')):
        raise ValueError('Standalone table and frozen answer key differ')
    tail_lines = ['License plate: ' + case['item_id']]
    if case.get('source_run') == 'explanation-001':
        if case.get('schema') != 'full' or case.get('cohort') != 'genuine_missing_control':
            raise ValueError('Unexpected explanation-study source case')
        tail_lines.extend(column + ': ' + target[column] for column in PROFILE_COLUMNS)
    elif case.get('source_run') != 'columns-gpt4o-001':
        raise ValueError('Unrecognized source run')
    tail_lines.extend((SOURCE_CLASSIFICATION_QUESTION, SOURCE_COPY_INSTRUCTION))
    if tail != '\n'.join(tail_lines):
        raise ValueError('Unrecognized classification tail; refusing to remove it')
    context = intro + '\n\n' + table
    if context + '\n\n' + tail != original:
        raise ValueError('Source extraction did not preserve the literal context')
    return context, tail


def context_for(case):
    """The byte-identical original introduction and table, with no trailing gap."""
    return split_source_prompt(case)[0]


def classification_tail_for(case):
    """The validated removed tail, retained for inspection only."""
    return split_source_prompt(case)[1]


def question_for(case):
    plate = case.get('item_id')
    if not isinstance(plate, str) or re.fullmatch(r'[A-Z0-9]+', plate) is None:
        raise ValueError('Unexpected target license plate')
    return ("What is written in " + plate
            + "'s Verified class cell? Reply with exactly one of A, B, C, or MISSING.")


def load_snapshot():
    """Reuse the frozen, reviewed cases without any new outcome-based selection."""
    snapshot = downstream.load_snapshot()
    for case in snapshot['cases']:
        split_source_prompt(case)
        question_for(case)
    return snapshot


def make_plan(config):
    validate_config(config)
    cases = deepcopy(load_snapshot()['cases'])
    by_world = {}
    for case in cases:
        by_world.setdefault(case['world_id'], []).append(case)
    rng = random.Random(config['schedule_seed'])
    world_ids = sorted(by_world)
    rng.shuffle(world_ids)
    tasks = []
    # World blocks contain randomized case/repetition pairs. The two arms are
    # adjacent, with randomized order, to reduce unpaired time drift.
    for world_id in world_ids:
        pairs = [(case, repetition)
                 for case in sorted(by_world[world_id], key=lambda c: c['id'])
                 for repetition in range(1, config['repetitions'] + 1)]
        rng.shuffle(pairs)
        for case, repetition in pairs:
            arms = list(ARMS)
            rng.shuffle(arms)
            for arm in arms:
                tasks.append({
                    'id': case['id'] + '/' + arm + '/r' + str(repetition),
                    'case_id': case['id'], 'world_id': world_id,
                    'cohort': case['cohort'], 'arm': arm,
                    'repetition': repetition, 'expected': case['expected'],
                })
    if len(tasks) != 216 or Counter(task['arm'] for task in tasks) != dict.fromkeys(ARMS, 108):
        raise ValueError('Unexpected frozen call count')
    plan = {
        'schema_version': PLAN_SCHEMA_VERSION,
        'protocol_version': PROTOCOL_VERSION,
        'source_digest': source_digest(
            ROOT, 'exception_downstream_history',
            extra_paths=('configs/downstream_history_gpt4o.json', 'DOWNSTREAM_HISTORY_PROTOCOL.md',
                         'exception_downstream', 'configs/downstream_gpt4o.json',
                         'DOWNSTREAM_PROTOCOL.md', 'pyproject.toml')),
        'snapshot_digest': SNAPSHOT_DIGEST,
        'source_protocol_version': downstream.PROTOCOL_VERSION,
        'context_extraction_version': CONTEXT_EXTRACTION_VERSION,
        'config': deepcopy(config), 'worlds': world_ids, 'cases': cases, 'tasks': tasks,
        'analysis_plan': {
            'primary_cohort': 'contradiction', 'primary_metric': 'false_missing',
            'primary_contrast': list(ARMS),
            'contrast_direction': 'history_present minus history_absent',
            'weighting': 'repetition then case then equal world',
            'estimand': 'selected-cohort world-average effect of the prior classification exchange',
            'secondary_cohorts': list(COHORTS),
            'secondary_metrics': ['accuracy', 'false_missing'],
            'pool_cohorts': False,
            'bootstrap_replicates': 10000, 'bootstrap_seed': 481602,
            'scientific_success_gate': None,
        },
    }
    plan['plan_hash'] = content_digest(plan)
    return plan


def read_plan(output):
    plan = json.loads((Path(output) / 'plan.json').read_text())
    if plan != make_plan(plan['config']):
        raise ValueError('Saved plan, source, configuration or schedule drifted')
    return plan


def _case(plan, task):
    matches = [case for case in plan['cases'] if case['id'] == task['case_id']]
    if len(matches) != 1:
        raise ValueError('Task must identify exactly one frozen case')
    case = matches[0]
    if (task['arm'] not in ARMS
            or any(task[key] != case[key] for key in ('world_id', 'cohort', 'expected'))
            or type(task['repetition']) is not int
            or not 1 <= task['repetition'] <= plan['config']['repetitions']):
        raise ValueError('Task and frozen case differ')
    return case


def request_for(plan, task):
    case = _case(plan, task)
    context = context_for(case)
    question = question_for(case)
    # Reuse the original-arm builder, guaranteeing payload identity for the
    # fresh history-present reference. The second arm changes only messages.
    request = downstream.request_for(plan, task | {'arm': 'original'})
    if request['messages'][-1] != {'role': 'user', 'content': question}:
        raise ValueError('Original downstream factual question changed')
    if task['arm'] == 'history_absent':
        request['messages'] = [{'role': 'user', 'content': context + '\n\n' + question}]
    return request


def task_meta(plan, task):
    case = _case(plan, task)
    context, tail = split_source_prompt(case)
    question = question_for(case)
    return deepcopy(task) | {
        key: case[key] for key in (
            'source_id', 'source_run', 'item_id', 'schema', 'value', 'target_position',
            'text_sha256', 'request_digest', 'response_digest',
            'source_attempt_sha256', 'source_attempt_filename')
    } | {
        'metadata_schema_version': PLAN_SCHEMA_VERSION,
        'snapshot_digest': SNAPSHOT_DIGEST,
        'context_extraction_version': CONTEXT_EXTRACTION_VERSION,
        'context_sha256': _text_sha256(context),
        'factual_question': question, 'factual_question_sha256': _text_sha256(question),
        'removed_classification_tail': tail,
        'removed_classification_tail_sha256': _text_sha256(tail),
        'classification_tail_removed': task['arm'] == 'history_absent',
        'feature_profile_in_source_tail': case['source_run'] == 'explanation-001',
        'classification_response_replayed': task['arm'] == 'history_present',
    }


def score_response(task, response):
    return downstream.score_response(task, response)


def mock_complete(plan, task):
    return downstream.mock_complete(plan, task)
