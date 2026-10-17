"""Content identity is separate from ordinary repository revision provenance."""
import hashlib
import subprocess
from pathlib import Path
from exception_pilot.core import digest
from exception_study2_v5.core import source_hash
from exception_study2_v5_replication.integrity import code_hash as replication_hash

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def revision():
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def contract():
    helpers=('exception_review/artifacts.py','exception_review/telemetry.py',
             'exception_review/journal.py','exception_pilot/storage.py')
    return digest(dict(extension={p.name:sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
        protocol=sha(ROOT/'STUDY2_SOURCE_REPORT_V1_PROTOCOL.md'),scientific_source=source_hash(),
        replication=replication_hash(),helpers={p:sha(ROOT/p) for p in helpers}))


def separate(output,*inputs):
    out=Path(output).resolve()
    for name in inputs:
        p=Path(name).resolve()
        if out==p or out.is_relative_to(p) or p.is_relative_to(out):
            raise ValueError('Source-report output must be outside both historical source trees and tokenizer assets')
    return out
