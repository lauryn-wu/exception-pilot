"""Offline source audit and portable request preview, never an execution plan."""
import argparse
import gzip
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from exception_pilot.core import digest
from exception_study2_current.adapter import Tokenizer
from exception_study2_explanation import SOURCE_ZIP, SOURCE_CONTRACT
from exception_study2_explanation.source import Source
from exception_study2_explanation.planning import plan_fields
from exception_study2_explanation.analysis import report, markdown


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tokenizer-dir', required=True); p.add_argument('--output', required=True)
    a = p.parse_args(); out = Path(a.output)
    if out.exists():
        raise ValueError('Use a fresh audit output directory')
    tok = Tokenizer(a.tokenizer_dir)
    root = Path(__file__).resolve().parents[2]
    src = Source(root/'results/current-qwen-screen-v1'/SOURCE_ZIP, tok)
    fields = plan_fields(src, tok)
    with tempfile.TemporaryDirectory() as temp:
        c = SimpleNamespace(out=Path(temp), source=src, tok=tok, requests=fields['requests'],
                            plan=dict(fields, artifact_hash=digest(fields)),
                            recovery=dict(pending=[], records=[], uncommitted=[]))
        preview = report(c, {r['cell']['id']:None for r in c.requests}, {})
    # Content preview is relocatable and has no runtime paths or fabricated model responses.
    preview.pop('cases')
    for arms in preview['sensitivities'].values():
        for metric in arms.values():
            metric.pop('pairs')
    preview['plan_hash'] = None
    preview['portable_request_manifest_hash'] = digest(fields)
    preview['preview_only'] = True
    preview['instruction'] = 'Prepare a fresh execution directory on RunPod; this audit is not a runnable frozen plan.'
    preview['validation'] = dict(sealed_source_members=src.seals_checked, scientific_returns_checked=384,
        smoke_returns_checked=8, unchanged_original_contract=SOURCE_CONTRACT,
        actual_record_cells_checked=True, raw_token_text_input_sampling_and_dispatch_checks=True,
        model_loads=0, new_real_generations=0)
    out.mkdir(parents=True)
    manifest = (json.dumps(fields, indent=2, sort_keys=True)+'\n').encode()
    (out/'request-manifest.json.gz').write_bytes(gzip.compress(manifest, mtime=0))
    (out/'preview.json').write_text(json.dumps(preview, indent=2, sort_keys=True)+'\n')
    (out/'preview.md').write_text('Offline preparation preview; no new scientific responses.\n\n'+markdown(preview))
    print(json.dumps(dict(new_requests=96, reused_controls=192, input_tokens=fields['total_input_token_occurrences'],
                         output_cap=fields['maximum_output_tokens'], code_contract=fields['code_contract'],
                         portable_manifest_hash=digest(fields), model_loads=0), indent=2))

if __name__ == '__main__':
    main()
