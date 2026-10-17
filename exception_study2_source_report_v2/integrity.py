"""V2 identity covers its own code/protocol and all reused v1 dependencies."""
from pathlib import Path
from exception_pilot.core import digest
from exception_study2_source_report.integrity import contract as v1_contract,sha,revision,separate
ROOT=Path(__file__).resolve().parents[1]


def contract():
    return digest(dict(extension={p.name:sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
        protocol=sha(ROOT/'STUDY2_SOURCE_REPORT_V2_PROTOCOL.md'),reused_v1_dependency_contract=v1_contract()))
