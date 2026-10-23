"""Portable raw-response audit and blank semantic review, with no source-result control reuse."""
import csv
import io
import json
import zipfile
from pathlib import Path
from exception_pilot.storage import run_lock
from exception_review.artifacts import sha
from exception_study2_source_report.integrity import separate
from exception_study2_explanation.export import ANNOTATIONS
from .planning import Context
from .execution import journal
from .analysis import report, markdown
from .source import sha_bytes
TOP = {'plan.json','source-validation.json','execution.json'}
DIRS = {'source-evidence','operations-v5','dispatches','responses','invocations','journal-recovery'}


def review_sheet(rows):
    stream = io.StringIO()
    fields = ['cell_id','pair_id','arm','world','variant','cue_state','relation','expected','pattern','prompt',
              'request_hash','operation_hash','operation_status','ordered_messages_json','final_answer_text','answer','correct',
              'category','explanation_format_compliant']
    for a in ANNOTATIONS: fields += [a,a+'_quote',a+'_message_index',a+'_start',a+'_end']
    writer = csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
    for r in rows:
        cell = r['cell']; score = r['score'] or {}
        row = {k:cell[k] for k in ('pair_id','arm','world','variant','cue_state','relation','expected','pattern','prompt')}
        row.update(cell_id=cell['id'], **{k:r[k] for k in ('request_hash','operation_hash','operation_status')},
                   ordered_messages_json=json.dumps(score.get('messages',[]),ensure_ascii=False),
                   **{k:score.get(k) for k in ('final_answer_text','answer','correct','category','explanation_format_compliant')})
        row.update({a:'not_reviewed' for a in ANNOTATIONS}); writer.writerow(row)
    return stream.getvalue()


def export(output, destination):
    target = separate(destination,output)
    if target.exists(): raise ValueError('Fresh export destination required')
    with run_lock(output):
        c = Context(output); current,_ = journal(c); value = report(c,current,dict(new_dispatches=0))
        files = {}
        for p in sorted(c.out.rglob('*')):
            rel = p.relative_to(c.out)
            if rel.parts[0] not in DIRS and str(rel) not in TOP: continue
            if p.is_symlink(): raise ValueError('Export rejects symlinks')
            if p.is_file(): files[str(rel)] = p.read_bytes()
        files['analysis.json'] = (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
        files['analysis.md'] = markdown(value).encode()
        files['manual-review.csv'] = review_sheet(value['cases']).encode()
        traces = []
        for r in value['cases']:
            traces += [r['cell']['id'],json.dumps({k:r[k] for k in ('operation_status','request_hash','operation_hash')})]
            if r['score']:
                for m in r['score']['messages']:
                    traces += [f"[output {m['output_index']} / phase {m['phase']}]",m['text']]
                    traces += ['[refusal] '+x for x in m['refusals']]
            else: traces += ['[no scoreable returned response; consult raw journal if failed/ambiguous]']
            traces += ['']
        files['gpt-traces.txt'] = '\n'.join(traces).encode()
        files['protocol.md'] = (Path(__file__).parents[1]/'STUDY2_GPT_EXPLANATION_V1.md').read_bytes()
        files['bundle-manifest.json'] = (json.dumps(dict(protocol=c.plan['protocol'],plan_hash=c.plan['artifact_hash'],
            code_contract=c.plan['code_contract'],source=c.plan['source'],measurement_mode=value['measurement_mode'],
            files={k:dict(bytes=len(v),sha256=sha_bytes(v)) for k,v in sorted(files.items())},
            annotation_states=['not_reviewed','absent','present','uncertain'],
            offsets='Zero-based half-open Unicode offsets within the selected message text; preserve output_index and phase. Indicators may overlap.',
            relocation='Extract into a fresh directory with this code contract. No Qwen tokenizer, weights, original paths or API key is required to inspect.'),indent=2,sort_keys=True)+'\n').encode()
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:
            with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:
                for name,data in sorted(files.items()): z.writestr(name,data)
    return dict(path=str(target),sha256=sha(target),files=len(files),complete=value['complete'],network_calls=0)
