"""Recheck this machine's preserved artifacts; read-only, no inference or network."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def inventory(root):
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Missing/nonregular historical directory: '+str(root))
    paths=list(root.rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise ValueError('Unexpected historical symlink')
    return {str(p.relative_to(root)):sha(p) for p in sorted(paths) if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,help='Fresh report filename; never overwrite')
    parser.add_argument('--baseline',default=str(Path(__file__).with_name('historical-baseline.json')))
    parser.add_argument('--repository',default=str(Path(__file__).resolve().parents[2]))
    args=parser.parse_args();baseline=json.loads(Path(args.baseline).read_text());repo=Path(args.repository)
    differences=[name for name,h in baseline['tracked'].items() if not (repo/name).is_file() or sha(repo/name)!=h]
    archives=[]
    for name,old in baseline['historical'].items():
        actual=inventory(Path(name));changed=[p for p in set(old)|set(actual) if old.get(p)!=actual.get(p)]
        archives.append(dict(path=name,files_before=len(old),files_after=len(actual),changed_files=sorted(changed),byte_identical=not changed))
    passed=not differences and all(a['byte_identical'] for a in archives)
    result=dict(base_revision=baseline['base'],baseline_sha256=sha(Path(args.baseline)),
        preexisting_tracked_files=len(baseline['tracked']),changed_preexisting_files=differences,
        historical_archives=archives,historical_file_count=sum(a['files_before'] for a in archives),
        passed=passed,inference_calls=0,paid_calls=0,original_artifacts_modified=False if passed else None)
    with Path(args.output).open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result,indent=2))
    if not passed:raise SystemExit(1)

if __name__=='__main__':main()
