"""Content locks are independent of ordinary Git provenance and derived counters."""
from pathlib import Path
from exception_pilot.core import digest
from exception_study2_source_user_pilot.integrity import contract as pilot_contract,sha,revision,separate,artifact_files
from . import PILOT_CONTRACT
ROOT=Path(__file__).resolve().parents[1]


def contract():
    previous=pilot_contract()  # Also enforces unchanged v1 and v2 contracts.
    if previous!=PILOT_CONTRACT:raise ValueError('Frozen pilot contract changed')
    return digest(dict(extension={p.name:sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
        protocol=sha(ROOT/'STUDY2_SOURCE_USER_MAIN_PROTOCOL.md'),pilot_contract=previous))


def scientific_files(root):
    # Only the pilot's top-level derived reports are excluded. Nested v2 evidence
    # remains immutable, as required by its existing authenticated parent contract.
    return {n:h for n,h in artifact_files(root).items() if n not in ('report.json','report.md')}
