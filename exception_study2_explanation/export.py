"""Portable audit and a blank, overlapping semantic review sheet."""
import csv
import io
import json
import zipfile
from pathlib import Path
from exception_pilot.storage import run_lock
from exception_review.artifacts import sha
from exception_study2_source_report.integrity import separate
from .planning import Context
from .execution import journal
from .analysis import report, markdown
from .source import sha_bytes

ANNOTATIONS = ('correct_record_mention', 'factual_false_absence_claim', 'induced_rule_justification',
               'target_row_used_as_rule_evidence', 'explanation_compliance')
TOP = {'plan.json', 'locations.json', 'execution.json', 'source-validation.json'}
DIRS = {'source-evidence', 'operations-v5', 'dispatches', 'invocations', 'journal-recovery'}


def review_sheet(rows):
    stream = io.StringIO()
    fields = ['cell_id', 'world', 'variant', 'cue_state', 'relation', 'expected', 'pattern',
              'matched_input_prompt', 'explanation_input_prompt', 'raw_explanation', 'answer', 'correct',
              'operation_status', 'request_hash', 'operation_hash', 'direct_reference', 'direct_raw', 'direct_answer',
              'native_on_reference', 'native_on_raw', 'native_on_answer', 'explanation_format_compliant']
    for annotation in ANNOTATIONS:
        fields += [annotation, annotation+'_quote', annotation+'_start', annotation+'_end']
    writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
    for r in rows:
        cell = r['cell']; score = r['score']; controls = r['controls']
        row = {k: cell[k] for k in ('world', 'variant', 'cue_state', 'relation', 'expected', 'pattern')}
        row.update(cell_id=cell['id'], matched_input_prompt=controls['direct']['cell']['prompt'], explanation_input_prompt=cell['prompt'],
                   raw_explanation=r['raw'].get('raw_text', '') if isinstance(r['raw'], dict) else '',
                   answer=score['answer'] if score else '', correct=score['correct'] if score else '',
                   operation_status=r['operation_status'], request_hash=r['request_hash'], operation_hash=r['operation_hash'],
                   explanation_format_compliant=score['explanation_format_compliant'] if score else '')
        for arm in ('direct', 'native_on'):
            row[arm+'_reference'] = json.dumps(controls[arm]['reference'], sort_keys=True)
            row[arm+'_raw'] = controls[arm]['raw']['raw_text']; row[arm+'_answer'] = controls[arm]['score']['answer']
        for annotation in ANNOTATIONS:
            row[annotation] = 'not_reviewed'
        writer.writerow(row)
    return stream.getvalue()


def export(output, destination, tokenizer_dir=None):
    c = Context(output, tokenizer_dir)
    target = separate(destination, c.out, c.tokenizer_dir, c.model_dir)
    if target.exists():
        raise ValueError('Fresh export destination required')
    with run_lock(c.out):
        current, _, _ = journal(c); value = report(c, current, dict(new_dispatches=0, model_loads=0))
        files = {}
        for p in sorted(c.out.rglob('*')):
            relative = p.relative_to(c.out)
            if relative.parts[0] not in DIRS and str(relative) not in TOP:
                continue
            if p.is_symlink():
                raise ValueError('Export rejects symlinks')
            if p.is_file():
                files[str(relative)] = p.read_bytes()
        files['analysis.json'] = (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()
        files['analysis.md'] = markdown(value).encode()
        files['manual-review.csv'] = review_sheet(value['cases']).encode()
        traces = []
        for r in value['cases']:
            traces += [r['cell']['id'], json.dumps({k: r[k] for k in ('request_hash', 'operation_hash', 'operation_status', 'score')}, ensure_ascii=False),
                       str(r['raw'].get('raw_text', '')) if isinstance(r['raw'], dict) else '[no returned text]', '']
        files['explanation-traces.txt'] = '\n'.join(traces).encode()
        files['protocol.md'] = (Path(__file__).parents[1]/'STUDY2_CURRENT_QWEN_EXPLANATION_V1.md').read_bytes()
        manifest = dict(protocol=c.plan['protocol'], plan_hash=c.plan['artifact_hash'], code_contract=c.plan['code_contract'],
                        source=c.plan['source'], files={k: dict(bytes=len(v), sha256=sha_bytes(v)) for k, v in sorted(files.items())},
                        annotation_states=['not_reviewed', 'absent', 'present', 'uncertain'],
                        annotation_offsets='Zero-based half-open Unicode offsets in raw_explanation. Indicators may overlap. No automatic semantic labels.',
                        relocation='Extract into a fresh directory. Pass --tokenizer-dir for local pinned tokenizer assets. Historical absolute paths are provenance only.')
        files['bundle-manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            with zipfile.ZipFile(f, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                for name, data in sorted(files.items()):
                    z.writestr(name, data)
    return dict(path=str(target), sha256=sha(target), files=len(files), complete=value['complete'], model_loads=0)
