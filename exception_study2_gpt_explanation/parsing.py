"""Responses API text handling; never use judge JSON parsing or reasoning summaries as answers."""
from copy import deepcopy
from exception_review.providers import loads, usage_cost
from . import SETTINGS, PRICING


def body_of(raw):
    try:
        body = loads(raw['response']['body'])
        return body if isinstance(body, dict) else None
    except (KeyError, TypeError, ValueError):
        return None


def infrastructure_error(raw):
    response = raw.get('response', {})
    if type(response.get('status')) is not int or not 200 <= response['status'] < 300:
        return 'HTTP_' + str(response.get('status'))
    body = body_of(raw)
    if body is not None:
        if body.get('error') is not None or body.get('status') in ('failed','cancelled','queued','in_progress'):
            return 'API_' + str(body.get('status'))
        # Alias resolution is allowed. Echoed decoding settings, when present, must match.
        for key in ('max_output_tokens','temperature','top_p','store'):
            if key in body and body[key] != SETTINGS[key]:
                return 'API_setting_mismatch_' + key
        if 'reasoning' in body and (not isinstance(body['reasoning'],dict) or body['reasoning'].get('effort') != 'none'):
            return 'API_setting_mismatch_reasoning'
    usage = body.get('usage') if body is not None else None
    if isinstance(usage,dict) and type(usage.get('output_tokens')) is int and usage['output_tokens'] > SETTINGS['max_output_tokens']:
        return 'API_output_exceeded_frozen_cap'
    return None


def parse_result(raw, cell):
    result = dict(valid=False, correct=False, answer=None, category='malformed_response', malformed=True,
                  truncated=False, refusal=False, missing_answer=True, messages=[], output_items=[],
                  complete_visible_text='', final_answer_text=None, explanation_text=None,
                  explanation_format_compliant=False, explanation_compliance='not_reviewed',
                  response_id=None, returned_model=None, usage=None, status=None, incomplete_details=None,
                  request_id=raw.get('response',{}).get('request_id'), requested_model=SETTINGS['model'],
                  client_started_utc=raw.get('started_utc'), client_finished_utc=raw.get('finished_utc'),
                  errors=[], final_message_index=None)
    body = body_of(raw)
    if body is None:
        result['errors'] = ['Invalid JSON response object']; return result
    for key in ('usage','status','incomplete_details','created_at','completed_at','service_tier'):
        result[key] = body.get(key)
    result.update(response_id=body.get('id'), returned_model=body.get('model'), output_items=body.get('output'))
    infra = infrastructure_error(raw)
    if infra:
        result.update(category='infrastructure_failure', errors=[infra]); return result
    errors = []
    if not isinstance(body.get('model'),str) or not body['model'] or not isinstance(body.get('id'),str) or not body['id']:
        errors.append('Missing model/response identity')
    if body.get('status') not in ('completed','incomplete'):
        errors.append('Unexpected response status')
    items = body.get('output'); messages = []
    if not isinstance(items,list):
        items = []; errors.append('Missing output array')
    for index,item in enumerate(items):
        if not isinstance(item,dict):
            errors.append('Malformed output item'); continue
        if item.get('type') == 'reasoning':
            continue  # Fully retained in raw/output_items. Summaries are not visible explanation.
        if item.get('type') != 'message' or item.get('role') != 'assistant' or not isinstance(item.get('content'),list):
            errors.append('Unexpected output item'); continue
        phase = item.get('phase'); parts = []; refusals = []
        if phase not in (None,'commentary','final_answer'):
            errors.append('Unknown assistant phase')
        if item.get('status') not in (None,'completed','incomplete'):
            errors.append('Unexpected message status')
        if body.get('status') == 'completed' and item.get('status') == 'incomplete':
            errors.append('Completed response with incomplete message')
        for part in item['content']:
            if not isinstance(part,dict):
                errors.append('Malformed content part'); continue
            if part.get('type') == 'output_text' and isinstance(part.get('text'),str):
                parts.append(part['text'])
            elif part.get('type') == 'refusal' and isinstance(part.get('refusal'),str):
                refusals.append(part['refusal'])
            else:
                errors.append('Unexpected content part')
        messages.append(dict(output_index=index, message_id=item.get('id'), phase=phase, status=item.get('status'),
                             content=deepcopy(item['content']), text=''.join(parts), refusals=refusals))
    result['messages'] = messages
    result['complete_visible_text'] = '\n'.join(m['text'] for m in messages)
    explicit = [m for m in messages if m['phase'] == 'final_answer']
    final = explicit[0] if len(explicit) == 1 else messages[0] if len(messages) == 1 and messages[0]['phase'] is None else None
    if len(explicit) > 1 or len(messages) > 1 and (final is None or final is not messages[-1]
            or any(m['phase'] != 'commentary' for m in messages[:-1])):
        errors.append('Ambiguous final message boundaries')
    if final:
        result.update(final_message_index=final['output_index'], final_answer_text=final['text'])
    text = final['text'] if final else ''
    lines = text.splitlines(keepends=True); nonempty = [i for i,line in enumerate(lines) if line.strip()]
    last = nonempty[-1] if nonempty else None
    last_line = lines[last].rstrip('\r\n') if last is not None else ''
    final_prefix = ''.join(lines[:last]) if last is not None else text
    preceding_messages = [m for m in messages if final is not None and m['output_index'] < final['output_index']]
    explanation_parts = [dict(output_index=m['output_index'], phase=m['phase'], text=m['text']) for m in preceding_messages]
    if final is not None:
        explanation_parts.append(dict(output_index=final['output_index'], phase=final['phase'], text=final_prefix))
    explanation = '\n'.join(p['text'] for p in explanation_parts)
    result['explanation_parts'] = explanation_parts if cell['arm'] == 'explanation' else []
    result['explanation_text'] = explanation if cell['arm'] == 'explanation' else None
    candidate = result['complete_visible_text'].strip() if cell['arm'] == 'direct' else last_line
    answer_ok = candidate in ('A','B','C') and final is not None
    details = body.get('incomplete_details')
    if body.get('status') == 'incomplete' and not isinstance(details,dict):
        errors.append('Incomplete response missing details')
    truncated = body.get('status') == 'incomplete' and isinstance(details,dict) and details.get('reason') == 'max_output_tokens'
    refusal = any(m['refusals'] for m in messages)
    valid = not errors and body.get('status') == 'completed' and not refusal and answer_ok
    category = ('malformed_response' if errors else 'truncated' if truncated else 'refusal' if refusal
                else 'incomplete' if body.get('status') == 'incomplete' else 'invalid_format' if not answer_ok
                else 'correct' if candidate == cell['expected'] else 'wrong_label')
    result.update(valid=valid, correct=valid and candidate == cell['expected'], answer=candidate if valid else None,
                  observed_final_candidate=candidate, category=category, malformed=bool(errors), errors=errors,
                  truncated=truncated, refusal=refusal, missing_answer=not answer_ok,
                  explanation_format_compliant=bool(cell['arm']=='explanation' and valid and explanation.strip()),
                  explanation_note='Nonempty text before the final label is format compliance; semantic compliance remains not reviewed.')
    return result


def account(raw, rates=PRICING):
    """Extend the existing usage helper for cache writes; missing fields never become zero."""
    body = body_of(raw) or {}; usage = body.get('usage')
    result = dict(usage=usage, input_tokens=None, output_tokens=None, reasoning_tokens=None,
                  cached_input_tokens=None, cache_write_input_tokens=None, estimated_usd=None,
                  cost_note='Missing or inconsistent usage, or unpriced service tier. Exact estimate unavailable.')
    if not isinstance(usage,dict): return result
    inp, output = usage.get('input_tokens'), usage.get('output_tokens')
    details = usage.get('input_tokens_details'); od = usage.get('output_tokens_details')
    reasoning = od.get('reasoning_tokens') if isinstance(od,dict) else None
    result.update(input_tokens=inp, output_tokens=output, reasoning_tokens=reasoning)
    if not isinstance(details,dict): return result
    cached, writes = details.get('cached_tokens'), details.get('cache_write_tokens')
    result.update(cached_input_tokens=cached, cache_write_input_tokens=writes)
    if any(type(x) is not int or x < 0 for x in (inp, output, cached, writes)) or cached+writes > inp:
        return result
    if reasoning is not None and (type(reasoning) is not int or not 0 <= reasoning <= output): return result
    if body.get('service_tier') not in (None,'default'): return result
    write_details = details.get('cache_write_tokens_details')
    if writes == 0:
        w30, w12 = 0, 0
    elif isinstance(write_details,dict):
        w30, w12 = write_details.get('ttl_30m_tokens'), write_details.get('ttl_12h_tokens')
        if any(type(x) is not int or x < 0 for x in (w30,w12)) or w30+w12 != writes: return result
    else:
        return result
    long = inp > rates['long_context_threshold']; input_factor = 2 if long else 1
    resolved = dict(input_per_million=rates['input_per_million']*input_factor,
                    cached_input_per_million=rates['cached_input_per_million']*input_factor,
                    output_per_million=rates['output_per_million']*(1.5 if long else 1))
    # Normalize only the helper input; retain absent/malformed reasoning metadata in the returned accounting record.
    ordinary_and_cached = dict(input_tokens=inp-writes, output_tokens=output,
                               input_tokens_details=dict(cached_tokens=cached),
                               output_tokens_details=dict(reasoning_tokens=reasoning or 0))
    base = usage_cost('openai', ordinary_and_cached, resolved)
    cost = base['estimated_usd'] + (w30*rates['cache_write_30m_per_million']+w12*rates['cache_write_12h_per_million'])*input_factor/1e6
    result.update(ordinary_input_tokens=inp-cached-writes, cache_write_30m_tokens=w30, cache_write_12h_tokens=w12,
                  estimated_usd=cost, long_context=long,
                  cost_note='Output total includes reasoning tokens; they are not billed twice. Cache writes are disjoint from ordinary input and cache reads.')
    return result
