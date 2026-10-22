"""Recreate portable design/token evidence with local tokenizer assets only, no model imports."""
import argparse
import gzip
import json
from pathlib import Path
from exception_pilot.core import digest
from exception_review.artifacts import sha
from exception_study2_native.shortcuts import audit_shortcuts
from exception_study2_current import BUDGET, MODEL, REVISION
from exception_study2_current.adapter import Tokenizer
from exception_study2_current.design import make_design
from exception_study2_current.planning import request, contract


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer-dir',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();out=Path(args.output)
    if out.exists():raise ValueError('Use a fresh evidence directory')
    tok=Tokenizer(args.tokenizer_dir);design=make_design();reqs=[request(c,tok,BUDGET) for c in design['cells']]
    manifest=dict(status='OFFLINE_ONLY_NO_MODEL_RESPONSES',design=design,requests=reqs,code_contract=contract())
    audit=audit_shortcuts(design['tables']);out.mkdir(parents=True)
    for name,value in [('manifest.json.gz',manifest),('shortcut-audit.json.gz',audit)]:
        data=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
        (out/name).write_bytes(gzip.compress(data,mtime=0))
    ids=[r['request']['input_ids'] for r in reqs]
    report=dict(status='OFFLINE_ONLY_NO_MODEL_RESPONSES',code_contract=contract(),model=MODEL,revision=REVISION,
        protocol=design['protocol'],counts=design['counts'],unique_request_hashes=len({r['request_hash'] for r in reqs}),
        prompt_tokens=dict(total=sum(map(len,ids)),minimum=min(map(len,ids)),maximum=max(map(len,ids))),
        tokenizer=tok.identity,perfect_shortcuts=audit['perfect_shortcuts'],histogram_only_upper_bound=audit['histogram_only_upper_bound'],
        counterbalance=design['counterbalance'],manifest_content_hash=digest(manifest),
        files={p.name:sha(p) for p in sorted(out.glob('*.gz'))},
        not_tested=['GPU/model loading','Actual generated thinking/final boundaries','vLLM runtime sampling/EOS behavior','Real prefix continuation','Scientific model effects'])
    (out/'verification.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report[k] for k in ('counts','unique_request_hashes','prompt_tokens','code_contract','files')},indent=2))

if __name__=='__main__':main()
