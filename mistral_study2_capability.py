"""Isolated, offline-by-default Mistral Study 2 capability probe (not a backend)."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


MODEL = 'mistral-small-2603'
ENDPOINT = 'https://api.mistral.ai/v1/chat/completions'
PROMPT = 'Write a paragraph of at least 80 words describing the steps for organizing a bookshelf.'
CUE = '\nANSWER:'
CANDIDATES = {c: ' ' + c + '\n' for c in 'ABC'}
CAP = 192
CUTS = (32, 64)
MAX_REQUESTS = 12
SETTINGS = dict(model=MODEL, temperature=0, top_p=1, random_seed=20261012,
                reasoning_effort='none', stream=False, n=1, safe_prompt=False)
SOURCES = [
    'https://docs.mistral.ai/models/mistral-small-4-0-26-03',
    'https://docs.mistral.ai/studio/conversations/chat-completion',
    'https://docs.mistral.ai/studio/conversations/reasoning',
    'https://docs.mistral.ai/api/endpoint/chat',
    'https://docs.mistral.ai/openapi.yaml',
]


def payload(prefix=None, budget=CAP, **fields):
    messages = [dict(role='user', content=PROMPT)]
    if prefix is not None:
        messages.append(dict(role='assistant', content=prefix, prefix=True))
    return dict(SETTINGS, messages=messages, max_tokens=budget, **fields)


def plan():
    return dict(
        check='mistral-study2-capability-v1', mode='offline', live_tested=False,
        model=MODEL, endpoint=ENDPOINT, settings=SETTINGS, prompt=PROMPT,
        candidates=CANDIDATES, cue=CUE, max_requests=MAX_REQUESTS,
        max_requested_output_tokens=1062, retries=0, redirects=False,
        docs_checked='2026-10-12', sources=SOURCES,
        openapi_sha256='6c349f3bdef67bbbe43b49973f15825c92e7fcc1ff4fadbcc2d87564ef277a03',
        slots=[
            '01_plain_original: 192 tokens',
            '02_plain_char32: unchanged 32-character prefix; 192 tokens',
            '03_plain_char64: unchanged 64-character prefix; 192 tokens',
            '04_logprobs_original: logprobs=true; 192 tokens',
            '05_token32: unchanged 32-token prefix; logprobs + prompt_logprobs; 160 tokens',
            '06_token64: unchanged 64-token prefix; logprobs + prompt_logprobs; 128 tokens',
            '07_top_output: checkpoint + cue; logprobs + top_logprobs=5; 1 token',
            '08_prompt_context: checkpoint + cue; prompt_logprobs; 1 token',
            '09_top_prompt: same context; prompt_logprobs + top_prompt_logprobs=5; 1 token',
            '10_candidate_A: context + complete candidate; prompt_logprobs; 1 token',
            '11_candidate_B: context + complete candidate; prompt_logprobs; 1 token',
            '12_candidate_C: context + complete candidate; prompt_logprobs; 1 token',
        ],
        limits=validation_limits(),
        study_2a=dict(status='not_live_tested', protocol_compatible=False,
                      reason='Complete candidate likelihoods and replay gates remain unverified.'),
        study_2b=dict(status='not_live_tested', protocol_compatible=False,
                      reason='Prefix replay untested; token/distribution gates and behavioral calibration pending.'),
    )


def validation_limits():
    return dict(
        documented='Assistant prefix; output/prompt logprobs with token_id, bytes, token and optional top_logprobs.',
        testable='Returned text/finish equality; observable suffix IDs; returned prompt tail IDs; aligned complete candidate logprobs.',
        full_vocabulary_logits='not_exposed_by_documented_chat_schema',
        full_distribution_equivalence='not_established; top-k and sampled-token logprobs cannot establish it',
        local_protocol_gates='unchanged; raw-logit allclose, full-vocabulary probability allclose and TV remain untestable',
        server_identity='Returned model name is observable; exact weights, tokenizer, template, precision and deployment are not pinned.',
        token_identity='Bytes are not IDs. Server prefix-tail IDs can be compared if returned; arbitrary token-ID input is not documented.',
        full_serialized_generation_input='Not verified: original input token serialization is not captured by the output-only reference.',
        probability_semantics='Schema does not specify whether reported logprobs precede decoding transforms; temperature=0 is not proof.',
        calibration='No selection/confirmation cases, false-missingness screening or edited intervention arms are collected.',
        implementation='Full API backend pending; this report never opens local study gates.',
    )


def dump(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post(body, key):
    """One attempt, no SDK retries or redirect-following; called only by --live."""
    request = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=90) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def response_view(data):
    """Reject thinking/tool/multiple-choice/changed-model output for comparisons."""
    if not isinstance(data, dict) or data.get('model') != MODEL:
        return None
    choices = data.get('choices')
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        return None
    choice = choices[0]
    message = choice.get('message')
    if not isinstance(message, dict) or message.get('tool_calls') or message.get('reasoning_content') or message.get('thinking'):
        return None
    content = message.get('content')
    if isinstance(content, list):
        if any(not isinstance(c, dict) or c.get('type') != 'text' or not isinstance(c.get('text'), str) for c in content):
            return None
        content = ''.join(c['text'] for c in content)
    if not isinstance(content, str) or any(t in content.lower() for t in ('<think', '</think', '[think', '[/think')):
        return None
    return dict(text=content, finish=choice.get('finish_reason'), choice=choice)


def token_rows(view, field):
    obj = view['choice'].get(field) if view else None
    rows = obj.get('content') if isinstance(obj, dict) else None
    if not isinstance(rows, list) or not rows:
        return None
    for row in rows:
        if not isinstance(row, dict) or type(row.get('token_id')) is not int or row['token_id'] < 0:
            return None
        values = row.get('bytes')
        if not isinstance(values, list) or any(type(b) is not int or not 0 <= b <= 255 for b in values):
            return None
    return rows


def row_bytes(rows):
    return b''.join(bytes(r['bytes']) for r in rows)


def ids(rows):
    return [r['token_id'] for r in rows]


def finite_logprob(value):
    return type(value) in (int, float) and math.isfinite(value) and value <= 0


def original_tokens(view):
    rows = token_rows(view, 'logprobs')
    # Do not strip unexplained EOS/special-token bytes or invent a tokenizer.
    return rows if rows and row_bytes(rows) == view['text'].encode('utf-8') else None


def suffix_rows(rows, suffix):
    """Find a unique exact token-boundary tail; no substring/byte slicing of tokens."""
    if not rows or not suffix:
        return None
    ends = [i for i in range(len(rows)) if row_bytes(rows[i:]) == suffix]
    return rows[ends[0]:] if len(ends) == 1 else None


def replay_report(reference, replay, prefix, k=None):
    result = dict(behavioral_replay=False, suffix_token_ids_equal=None,
                  server_prefix_tail_ids_equal=None, full_distribution_equivalence=False)
    if not reference or not replay:
        return dict(result, reason='response_missing_or_identity_interface_rejected')
    expected = reference['text'][len(prefix):]
    result.update(returned_full_text_equal=replay['text'] == reference['text'],
                  returned_suffix_text_equal=replay['text'] == expected,
                  finish_equal=replay['finish'] == reference['finish'],
                  original_finish=reference['finish'], replay_finish=replay['finish'])
    # A length-limited match is evidence about a fragment, not a completed replay.
    result['behavioral_replay'] = (result['returned_full_text_equal'] or result['returned_suffix_text_equal']) and result['finish_equal'] and reference['finish'] == 'stop'
    if k is not None:
        original = original_tokens(reference)
        observed = token_rows(replay, 'logprobs')
        tail = (suffix_rows(observed, expected.encode()) if observed and
                row_bytes(observed) in (reference['text'].encode(), expected.encode()) else None)
        if original and tail:
            result['suffix_token_ids_equal'] = ids(tail) == ids(original[k:])
            if ids(tail) == ids(original[k:]) and all(finite_logprob(r.get('logprob')) for r in tail + original[k:]):
                result['max_observed_token_logprob_difference'] = max(abs(a['logprob']-b['logprob']) for a, b in zip(tail, original[k:]))
        prompt_tail = suffix_rows(token_rows(replay, 'prompt_logprobs'), prefix.encode())
        if original and prompt_tail:
            result['server_prefix_tail_ids_equal'] = ids(prompt_tail) == ids(original[:k])
    return result


def candidate_score(context_view, candidate_view, context, candidate):
    """Teacher-forced prompt likelihood only; missing top-k never means zero."""
    result = dict(status='unavailable', logprob=None, token_ids=None)
    base = token_rows(context_view, 'prompt_logprobs')
    rows = token_rows(candidate_view, 'prompt_logprobs')
    if not base or not rows:
        return dict(result, reason='missing_or_malformed_prompt_token_telemetry')
    # Prefix serialization must end exactly at the cue; added terminators fail closed.
    if not row_bytes(base).endswith(context.encode()):
        return dict(result, reason='context_not_exact_prompt_tail')
    n = len(base)
    if len(rows) <= n or ids(rows[:n]) != ids(base) or [r['bytes'] for r in rows[:n]] != [r['bytes'] for r in base]:
        return dict(result, reason='checkpoint_context_token_identity_changed')
    tail = rows[n:]
    if row_bytes(tail) != candidate.encode() or any(not r['bytes'] for r in tail):
        return dict(result, reason='candidate_boundary_or_complete_string_not_verified')
    if not all(finite_logprob(r.get('logprob')) for r in tail):
        return dict(result, reason='missing_or_invalid_candidate_token_logprob')
    return dict(status='observed_complete_candidate', logprob=sum(r['logprob'] for r in tail),
                token_ids=ids(tail), token_logprobs=[r['logprob'] for r in tail],
                context_token_ids_sha256=hashlib.sha256(json.dumps(ids(base)).encode()).hexdigest(),
                interpretation='Server-tokenized sequence, no length normalization; raw-logit semantics and standalone tokenization unverified.')


def probability_fields(view):
    result = {}
    for field in ('logprobs', 'prompt_logprobs'):
        rows = token_rows(view, field)
        choice = view['choice'] if view else {}
        status = ('not_returned' if field not in choice else 'null' if choice[field] is None
                  else 'token_rows_observed' if rows else 'malformed_or_empty')
        result[field] = dict(status=status, valid_token_rows=len(rows) if rows else 0,
                             scored_rows=sum(finite_logprob(r.get('logprob')) for r in rows) if rows else 0,
                             rows_with_top_k=sum(isinstance(r.get('top_logprobs'), list) and bool(r['top_logprobs']) for r in rows) if rows else 0,
                             top_k_interpretation='Presence only; raw entries saved. Not complete candidate or full-vocabulary probabilities.')
    return result


class Probe:
    def __init__(self, output, key, transport):
        self.output, self.key, self.transport = output, key, transport
        self.attempts, self.records, self.halted = 0, [], False

    def skip(self, name, reason):
        self.records.append(dict(slot=name, status='skipped', reason=reason))
        return None

    def call(self, name, body):
        if self.halted:
            return self.skip(name, 'fatal_transport_auth_or_rate_error; no retries')
        if self.attempts >= MAX_REQUESTS:
            raise RuntimeError('Fixed request budget exhausted')
        self.attempts += 1  # Count even timeouts/errors; save before network access.
        dump(self.output / (name + '.request.json'), body)
        record = dict(slot=name, status='attempted', requested_fields=sorted(body))
        self.records.append(record)
        try:
            status, headers, raw = self.transport(body, self.key)
        except (OSError, TimeoutError) as exc:
            self.halted = True
            record.update(status='transport_error', error_type=type(exc).__name__)
            dump(self.output / (name + '.metadata.json'), record)
            return None
        with (self.output / (name + '.response.bin')).open('xb') as f:
            f.write(raw)
        record.update(http_status=status, response_bytes=len(raw),
                      response_sha256=hashlib.sha256(raw).hexdigest(),
                      headers={k: v for k, v in headers.items() if k.lower() in ('x-request-id', 'request-id', 'date', 'content-type')})
        self.halted = status in (401, 403, 429) or status >= 500 or 300 <= status < 400
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            data = None
        view = response_view(data) if status == 200 else None
        record.update(status='observed' if view else 'rejected_or_unusable',
                      returned_model=data.get('model') if isinstance(data, dict) else None,
                      response_id=data.get('id') if isinstance(data, dict) else None,
                      usage=data.get('usage') if isinstance(data, dict) else None,
                      probability_fields=probability_fields(view))
        dump(self.output / (name + '.metadata.json'), record)
        return view


def run_live(output, key, transport=post):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)  # No resume/overwrite/retry of old runs.
    manifest = plan()
    manifest.update(mode='live_requested', script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    dump(output / 'plan.json', manifest)
    probe = Probe(output, key, transport)
    plain = probe.call('01_plain_original', payload())
    replays = []
    for slot, cut in zip(('02_plain_char32', '03_plain_char64'), CUTS):
        if plain and len(plain['text']) > cut:
            prefix = plain['text'][:cut]
            dump(output / (slot + '.prefix.json'), dict(unit='unicode_characters_not_tokens', cut=cut, prefix=prefix))
            replay = probe.call(slot, payload(prefix))
            replays.append(dict(slot=slot, unit='characters', cut=cut, **replay_report(plain, replay, prefix)))
        else:
            probe.skip(slot, 'no_usable_original_or_original_too_short')
    original = probe.call('04_logprobs_original', payload(logprobs=True))
    tokens = original_tokens(original)
    for slot, cut in zip(('05_token32', '06_token64'), CUTS):
        prefix = None
        if tokens and len(tokens) > cut:
            try:
                prefix = row_bytes(tokens[:cut]).decode('utf-8')
            except UnicodeDecodeError:
                pass
        if not prefix:
            probe.skip(slot, 'no_exact_observed_token_boundary; no tokenizer substitution')
            continue
        dump(output / (slot + '.prefix.json'), dict(unit='observed_tokens', cut=cut, prefix=prefix, token_ids=ids(tokens[:cut])))
        replay = probe.call(slot, payload(prefix, CAP-cut, logprobs=True, prompt_logprobs=True))
        replays.append(dict(slot=slot, unit='observed_tokens', cut=cut, **replay_report(original, replay, prefix, cut)))
    # Freeze one checkpoint for every scoring request, independent of answer/probability.
    # Prefer an observed 32-token boundary; otherwise use the unchanged 32-character
    # prefix for a clearly labelled text-interface test (never a protocol checkpoint).
    checkpoint = None
    if tokens and len(tokens) > 32:
        try:
            checkpoint = dict(prefix=row_bytes(tokens[:32]).decode('utf-8'), unit='observed_tokens', cut=32)
        except UnicodeDecodeError:
            pass
    if checkpoint is None and plain and len(plain['text']) > 32:
        checkpoint = dict(prefix=plain['text'][:32], unit='characters_not_protocol_tokens', cut=32)
    candidates = {c: dict(status='not_tested', logprob=None) for c in CANDIDATES}
    score_slots = ['07_top_output', '08_prompt_context', '09_top_prompt'] + [f'{i}_candidate_{c}' for i, c in enumerate(CANDIDATES, 10)]
    if checkpoint is None:
        for slot in score_slots:
            probe.skip(slot, 'no_unchanged_saved_checkpoint')
    else:
        context = checkpoint['prefix'] + CUE
        dump(output / 'scoring-context.json', dict(checkpoint, cue=CUE, context=context, candidates=CANDIDATES))
        probe.call('07_top_output', payload(context, 1, logprobs=True, top_logprobs=5))
        base = probe.call('08_prompt_context', payload(context, 1, prompt_logprobs=True))
        probe.call('09_top_prompt', payload(context, 1, prompt_logprobs=True, top_prompt_logprobs=5))
        for i, (label, candidate) in enumerate(CANDIDATES.items(), 10):
            view = probe.call(f'{i}_candidate_{label}', payload(context + candidate, 1, prompt_logprobs=True))
            candidates[label] = candidate_score(base, view, context, candidate)
    all_scores = all(c['status'] == 'observed_complete_candidate' for c in candidates.values())
    report = dict(check=manifest['check'], mode='live', requests_attempted=probe.attempts,
        records=probe.records, replays=replays, candidates=candidates, limits=validation_limits(),
        plain_and_instrumented_text_equal=(plain['text'] == original['text'] if plain and original else None),
        study_2a=dict(status='candidate_scores_observed_but_protocol_blocked' if all_scores else 'candidate_scoring_not_established',
                      complete_candidate_scores_observed=all_scores, protocol_compatible=False,
                      reason='Full-vocabulary raw-logit/probability replay gates remain unmet; server scoring semantics unverified.'),
        study_2b=dict(status='behavioral_replay_observed_but_protocol_blocked' if any(r['behavioral_replay'] for r in replays) else 'behavioral_replay_not_established',
                      protocol_compatible=False, false_missingness_calibration='not_tested',
                      reason='Behavioral equality does not establish token/full-distribution equivalence; no interventions or calibration performed.'))
    dump(output / 'report.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Authorize up to 12 potentially paid API requests, with no retries.')
    parser.add_argument('--output', type=Path, help='Required fresh output directory for --live; unused offline.')
    args = parser.parse_args(argv)
    if not args.live:
        print(json.dumps(plan(), indent=2))
        return 0
    if args.output is None:
        parser.error('--live requires a fresh --output directory')
    key = os.environ.get('MISTRAL_API_KEY')
    if not key:
        parser.error('--live requires MISTRAL_API_KEY in the environment')
    try:
        report = run_live(args.output, key)
    except (OSError, ValueError) as exc:
        print(json.dumps(dict(error=str(exc))), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    # Completion of a diagnostic is not study compatibility. Unusable requests
    # are reflected in the exit status; detailed capability limits are in report.
    return int(any(r['status'] in ('transport_error', 'rejected_or_unusable') for r in report['records']))


if __name__ == '__main__':
    sys.exit(main())
