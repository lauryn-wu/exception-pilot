"""Own contract plus transitive, unchanged historical dependencies."""
from pathlib import Path
from exception_pilot.core import digest
from exception_study2_source_report.integrity import sha, revision, separate, contract as v1_contract
from exception_study2_source_report_v2.integrity import contract as v2_contract
from . import V1_CONTRACT, V2_CONTRACT
ROOT = Path(__file__).resolve().parents[1]


def contract():
    if v1_contract()!=V1_CONTRACT or v2_contract()!=V2_CONTRACT:
        raise ValueError('Historical v1/v2 code contracts changed; preserve them')
    # Explicit direct helpers supplement the transitive v2 scientific/dependency lock.
    helpers=('exception_pilot/core.py','exception_continuation/runner.py',
             'exception_study2_v5/journal.py','exception_study2_v5/runner.py',
             'exception_study2_v5_replication/integrity.py')
    return digest(dict(extension={p.name:sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
        protocol=sha(ROOT/'STUDY2_SOURCE_USER_PILOT_PROTOCOL.md'),v2_contract=v2_contract(),
        helpers={p:sha(ROOT/p) for p in helpers}))


def artifact_files(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('Regular evidence directory required')
    files={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise ValueError('Artifact symlinks forbidden')
        if not p.is_file() or p.name=='run.lock':continue
        if p.suffix not in ('.json','.md','.txt'):raise ValueError('Unexpected artifact; no weights may be read')
        files[str(p.relative_to(root))]=sha(p)
    return files
