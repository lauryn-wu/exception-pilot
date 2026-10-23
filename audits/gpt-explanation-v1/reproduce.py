"""Create an UNEXECUTED audit export using only the standard library and local source evidence."""
import argparse
import gzip
import json
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from exception_study2_gpt_explanation import SOURCE_ZIP, SOURCE_SHA256
from exception_study2_gpt_explanation.planning import prepare, Context
from exception_study2_gpt_explanation.execution import inspect, run, analyze
from exception_study2_gpt_explanation.export import export
from exception_review.artifacts import sha


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',required=True)
    out=Path(parser.parse_args().output).resolve()
    if out.exists(): raise ValueError('Fresh audit output directory required')
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='gpt-explanation-audit-') as tmp:
        run_dir=Path(tmp)/'run'
        setup=prepare(ROOT/'results/current-qwen-screen-v1'/SOURCE_ZIP,run_dir)
        context=Context(run_dir)
        preview=inspect(run_dir)
        assert run(run_dir)['this_invocation']['new_dispatches']==0
        value=analyze(run_dir)
        bundle=export(run_dir,out/'offline-plan-evidence.zip')
        assert value['totals']['pending']==192 and value['totals']['completed']==0 and not value['complete']
        report=dict(prepare=setup,code_contract=context.plan['code_contract'],code_revision=context.plan['code_revision'],
                    source_sha256=SOURCE_SHA256,source_validation=context.source.binding,
                    schedule=context.plan['schedule'],api_settings=context.plan['api_settings'],
                    documentation=context.plan['documentation'],pricing=context.plan['pricing'],
                    counts=preview['totals'],measurement_mode=preview['measurement_mode'],
                    export={k:v for k,v in bundle.items() if k!='path'},
                    note='UNEXECUTED plan only. No GPT results, paid API calls, tokenizer loads or GPU inference. Audit revision is pre-commit provenance; code_contract identifies the actual implementation bytes.')
        (out/'preview.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
        manifest=json.dumps(context.requests,indent=2,sort_keys=True,ensure_ascii=False).encode()
        (out/'request-manifest.json.gz').write_bytes(gzip.compress(manifest,mtime=0))
    (out/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file()))
    print(json.dumps(report,indent=2,sort_keys=True))


if __name__=='__main__': main()
