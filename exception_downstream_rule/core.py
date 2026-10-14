"""Frozen factorial control of history and the original prediction instruction.

All four factual-follow-up conditions are collected afresh. Historical assistant
responses are replayed verbatim even when their preceding instruction is edited;
this intervention does not regenerate the preceding classification trajectory.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random

from exception_downstream import core as downstream
from exception_downstream_history import core as history
from exception_study_support.core import content_digest, source_digest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_VERSION = 'verified-facts-downstream-rule-v1'
PLAN_SCHEMA_VERSION = 'downstream-rule-plan-v1'
CONTEXT_EXTRACTION_VERSION = 'validated-intro-table-prediction-rule-v1'
SNAPSHOT_DIGEST = downstream.SNAPSHOT_DIGEST
ARMS = (
    'history_present_rule_present',
    'history_absent_rule_present',
    'history_present_rule_absent',
    'history_absent_rule_absent',
)
ARM_FACTORS = {
    'history_present_rule_present': {
        'history_present': True, 'prediction_rule_present': True},
    'history_absent_rule_present': {
        'history_present': False, 'prediction_rule_present': True},
    'history_present_rule_absent': {
        'history_present': True, 'prediction_rule_present': False},
    'history_absent_rule_absent': {
        'history_present': False, 'prediction_rule_present': False},
}
COHORTS = history.COHORTS
LABELS = downstream.LABELS
PREDICTION_RULE = (
    'If that cell is MISSING, make your best prediction from the other records.'
)
# The separator belongs to the removed suffix, preserving the preceding period
# and every other byte in the introduction, table, and subsequent messages.
PREDICTION_RULE_SUFFIX = ' ' + PREDICTION_RULE
SOURCE_INTRO = history.SOURCE_INTRO
PRIMARY_CONTRAST = 'rule_effect_without_history'
INTERACTION = 'history_by_rule_interaction'
CONTRASTS = {
    PRIMARY_CONTRAST: {
        'history_absent_rule_absent': 1, 'history_absent_rule_present': -1},
    'rule_effect_with_history': {
        'history_present_rule_absent': 1, 'history_present_rule_present': -1},
    'history_effect_rule_present': {
        'history_present_rule_present': 1, 'history_absent_rule_present': -1},
    'history_effect_rule_absent': {
        'history_present_rule_absent': 1, 'history_absent_rule_absent': -1},
    INTERACTION: {
        'history_present_rule_present': 1, 'history_absent_rule_present': -1,
        'history_present_rule_absent': -1, 'history_absent_rule_absent': 1},
}
DEFAULT_CONFIG = {
    'protocol': PROTOCOL_VERSION, 'model': 'gpt-4o-2024-08-06',
    'api_key_env': 'OPENAI_API_KEY', 'temperature': 0,
    'max_completion_tokens': 64, 'max_total_attempts': 480,
    'timeout_seconds': 120, 'repetitions': 3, 'schedule_seed': 728141,
}


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
        raise ValueError('This frozen study requires configs/downstream_rule_gpt4o.json unchanged')


def split_source_prompt(case):
    """Validate the exact original source using the completed history study."""
    return history.split_source_prompt(case)


def intro_for(prediction_rule_present=True):
    """Return the exact original intro, optionally deleting its known suffix."""
    if type(prediction_rule_present) is not bool:
        raise ValueError('Prediction-rule presence must be a boolean')
    if (not SOURCE_INTRO.endswith(PREDICTION_RULE_SUFFIX)
            or SOURCE_INTRO.count(PREDICTION_RULE_SUFFIX) != 1):
        raise ValueError('Original prediction instruction boundary changed')
    return (SOURCE_INTRO if prediction_rule_present
            else SOURCE_INTRO[:-len(PREDICTION_RULE_SUFFIX)])


def context_for(case, prediction_rule_present=True):
    """Preserve the validated table exactly; edit only the introductory suffix."""
    context, _ = split_source_prompt(case)
    intro = intro_for(prediction_rule_present)
    if context[:len(SOURCE_INTRO)] != SOURCE_INTRO:
        raise ValueError('Validated introduction was not the original prefix')
    return intro + context[len(SOURCE_INTRO):]


def classification_tail_for(case):
    return split_source_prompt(case)[1]


def question_for(case):
    """Use the identical literal factual question and four answer options."""
    return history.question_for(case)


def load_snapshot():
    """Reuse all 36 frozen sources, with no selection using follow-up outcomes."""
    snapshot = history.load_snapshot()
    for case in snapshot['cases']:
        context_for(case, True)
        context_for(case, False)
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
    # Shuffle world blocks, then case/repetition blocks within each world. All
    # four arms of a block stay adjacent, with independently shuffled arm order.
    for world_id in world_ids:
        blocks = [(case, repetition)
                  for case in sorted(by_world[world_id], key=lambda c: c['id'])
                  for repetition in range(1, config['repetitions'] + 1)]
        rng.shuffle(blocks)
        for case, repetition in blocks:
            arms = list(ARMS)
            rng.shuffle(arms)
            for arm in arms:
                tasks.append({
                    'id': case['id'] + '/' + arm + '/r' + str(repetition),
                    'case_id': case['id'], 'world_id': world_id,
                    'cohort': case['cohort'], 'arm': arm,
                    'repetition': repetition, 'expected': case['expected'],
                })
    if (len(tasks) != 432
            or Counter(task['arm'] for task in tasks) != dict.fromkeys(ARMS, 108)):
        raise ValueError('Unexpected frozen call count')
    plan = {
        'schema_version': PLAN_SCHEMA_VERSION,
        'protocol_version': PROTOCOL_VERSION,
        'source_digest': source_digest(
            ROOT, 'exception_downstream_rule',
            extra_paths=('configs/downstream_rule_gpt4o.json', 'DOWNSTREAM_RULE_PROTOCOL.md',
                         'exception_downstream_history', 'configs/downstream_history_gpt4o.json',
                         'DOWNSTREAM_HISTORY_PROTOCOL.md', 'exception_downstream',
                         'configs/downstream_gpt4o.json', 'DOWNSTREAM_PROTOCOL.md',
                         'pyproject.toml')),
        'snapshot_digest': SNAPSHOT_DIGEST,
        'source_protocol_version': downstream.PROTOCOL_VERSION,
        'history_protocol_version': history.PROTOCOL_VERSION,
        'context_extraction_version': CONTEXT_EXTRACTION_VERSION,
        'config': deepcopy(config), 'worlds': world_ids, 'cases': cases, 'tasks': tasks,
        'arm_factors': deepcopy(ARM_FACTORS),
        'prediction_rule': PREDICTION_RULE,
        'prediction_rule_removed_suffix': PREDICTION_RULE_SUFFIX,
        'classification_response_fixed_across_rule_conditions': True,
        'analysis_plan': {
            'primary_cohort': 'genuine_missing_control', 'primary_metric': 'accuracy',
            'primary_contrast': PRIMARY_CONTRAST,
            'contrast_weights': deepcopy(CONTRASTS),
            'contrast_direction': 'rule absent minus rule present without classification history',
            'interaction_contrast': INTERACTION,
            'interaction_direction': 'history effect with rule minus history effect without rule',
            'weighting': 'repetition then case then equal world',
            'estimand': 'selected-cohort world-average effects of displayed prediction rule and replayed history',
            'secondary_cohorts': list(COHORTS),
            'secondary_metrics': ['accuracy', 'false_missing'],
            'pool_cohorts': False,
            'complete_worlds': 'same complete constituent-arm membership within each contrast',
            'interaction_complete_worlds': 'all four arms complete for every case and repetition in the world',
            'bootstrap_replicates': 10000, 'bootstrap_seed': 481603,
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
    factors = ARM_FACTORS[task['arm']]
    old_arm = 'history_present' if factors['history_present'] else 'history_absent'
    # Using the completed study's builder preserves both rule-present payloads
    # exactly. The rule-absent conditions alter only the first user paragraph.
    request = history.request_for(plan, task | {'arm': old_arm})
    source_context = context_for(case, True)
    edited_context = context_for(case, factors['prediction_rule_present'])
    first = request['messages'][0]
    if (first['role'] != 'user'
            or not first['content'].startswith(source_context + '\n\n')):
        raise ValueError('Original context was not the first user message prefix')
    first['content'] = edited_context + first['content'][len(source_context):]
    if factors['history_present']:
        if request['messages'][1] != {'role': 'assistant', 'content': case['source_response']['text']}:
            raise ValueError('Historical classification response must be replayed unchanged')
        if request['messages'][-1] != {'role': 'user', 'content': question_for(case)}:
            raise ValueError('Factual follow-up question changed')
    elif request['messages'] != [{'role': 'user', 'content': edited_context + '\n\n' + question_for(case)}]:
        raise ValueError('Standalone factual question or context changed')
    return request


def task_meta(plan, task):
    case = _case(plan, task)
    factors = ARM_FACTORS[task['arm']]
    source_context, tail = split_source_prompt(case)
    context = context_for(case, factors['prediction_rule_present'])
    question = question_for(case)
    return deepcopy(task) | {
        key: case[key] for key in (
            'source_id', 'source_run', 'item_id', 'schema', 'value', 'target_position',
            'text_sha256', 'request_digest', 'response_digest',
            'source_attempt_sha256', 'source_attempt_filename')
    } | deepcopy(factors) | {
        'metadata_schema_version': PLAN_SCHEMA_VERSION,
        'snapshot_digest': SNAPSHOT_DIGEST,
        'context_extraction_version': CONTEXT_EXTRACTION_VERSION,
        'source_context_sha256': _text_sha256(source_context),
        'context_sha256': _text_sha256(context),
        'factual_question': question, 'factual_question_sha256': _text_sha256(question),
        'prediction_rule': PREDICTION_RULE,
        'removed_prediction_rule': '' if factors['prediction_rule_present'] else PREDICTION_RULE,
        'removed_prediction_rule_suffix': '' if factors['prediction_rule_present'] else PREDICTION_RULE_SUFFIX,
        'prediction_rule_removed': not factors['prediction_rule_present'],
        'source_classification_tail': tail,
        'source_classification_tail_sha256': _text_sha256(tail),
        'classification_tail_removed': not factors['history_present'],
        'feature_profile_in_source_tail': case['source_run'] == 'explanation-001',
        'classification_response_replayed': factors['history_present'],
        'classification_response_fixed_across_rule_conditions': True,
    }


def score_response(task, response):
    return downstream.score_response(task, response)


def mock_complete(plan, task):
    return downstream.mock_complete(plan, task)
