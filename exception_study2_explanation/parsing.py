"""Strict output identity and final-line parsing; no semantic classification."""


def metadata_errors(raw, request, tok, resolved):
    """Also used to audit old raw returns without changing their scoring rules."""
    if not isinstance(raw, dict) or not isinstance(raw.get('tokens'), list):
        return ['invalid payload']
    ids = raw['tokens']
    try:
        text = tok.decode_all(ids)
    except (ValueError, TypeError, OverflowError, IndexError):
        return ['invalid token IDs']
    errors = []
    eos = bool(ids and ids[-1] in tok.eos_ids)
    actual = raw.get('actual_input_ids')
    if (raw.get('input_ids_verified') is not True or not isinstance(actual, list)
            or any(type(i) is not int for i in actual) or actual != request['input_ids']):
        errors.append('input token identity differs')
    if raw.get('raw_text') != text or raw.get('text') != tok.decode(ids):
        errors.append('token/text mismatch')
    if raw.get('stopped') is not eos or raw.get('finish') != ('eos' if eos else 'length'):
        errors.append('finish/EOS mismatch')
    if raw.get('backend_finish_reason') != ('stop' if eos else 'length'):
        errors.append('backend finish mismatch')
    stop = raw.get('backend_stop_reason')
    if 'backend_stop_reason' not in raw or (stop is not None and (type(stop) is not int or not eos or stop != ids[-1])):
        errors.append('backend stop reason mismatch')
    if not ids or len(ids) > request['budget'] or not eos and len(ids) != request['budget']:
        errors.append('invalid generation length')
    if raw.get('resolved_sampling') != resolved:
        errors.append('resolved sampling differs')
    return errors


def parse_result(raw, request, tok):
    errors = metadata_errors(raw, request, tok, request['resolved_sampling'])
    empty = dict(answer=None, correct=False, valid=False, malformed=True, truncated=False,
                 missing_answer=True, explanation_text=None, ordinary_text=None,
                 explanation_format_compliant=False, explanation_compliance='not_reviewed',
                 token_count=None, eos_observed=False, errors=errors, category='metadata_malformed')
    if not isinstance(raw, dict) or not isinstance(raw.get('tokens'), list):
        return empty
    ids = raw['tokens']
    try:
        tok.decode_all(ids)
    except (ValueError, TypeError, OverflowError, IndexError):
        return empty
    eos = bool(ids and ids[-1] in tok.eos_ids)
    body = ids[:-1] if eos else ids
    # No structural tokens are allowed in ordinary output, including native think markers.
    # Transformers' all_special_ids omits some added control tokens (including im_start).
    # The pinned added-token inventory also contains tool/FIM/multimodal delimiters.
    structural = tok.special_ids | set(tok.tokenizer.added_tokens_decoder)
    channel_ok = not any(i in structural for i in body)
    channel_ok = channel_ok and request['thinking'] is False and not request['prefix_token_ids']
    text = tok.decode_all(body)
    lines = text.splitlines(keepends=True)
    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    last = nonempty[-1] if nonempty else None
    # Line terminators may be removed; spaces or punctuation around the letter may not.
    final = lines[last].rstrip('\r\n') if last is not None else ''
    answer_line = final in ('A', 'B', 'C')
    explanation = ''.join(lines[:last]) if last is not None else text
    truncated = not eos and len(ids) == request['budget']
    valid = not errors and channel_ok and eos and answer_line
    category = ('metadata_malformed' if errors else 'malformed_channel' if not channel_ok
                else 'truncated' if truncated else 'missing_answer' if not nonempty
                else 'invalid_format' if not answer_line else 'correct' if final == request['expected'] else 'wrong_label')
    return dict(answer=final if valid else None, correct=valid and final == request['expected'],
                valid=valid, malformed=bool(errors or not channel_ok), truncated=truncated,
                missing_answer=not answer_line, category=category, errors=errors,
                eos_observed=eos, token_count=len(ids), ordinary_text=text,
                explanation_text=explanation, final_line=final,
                explanation_format_compliant=bool(valid and explanation.strip()),
                explanation_compliance='not_reviewed',
                explanation_note='Nonempty preceding text is a format observation, not a verified semantic explanation.',
                final_line_character_start=sum(len(x) for x in lines[:last]) if last is not None else None)
