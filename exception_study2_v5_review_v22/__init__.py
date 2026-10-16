"""Additive v2.2 repair; v2.1 source, journals and scientific code stay frozen."""
from pathlib import Path
import exception_review
VERSION='study2-review-v2.2'
SALVAGE_VERSION='retrospective-v2.1-salvage-v2.2'
# Reuse shared immutable journal/transport under this version's policy namespace.
__path__.append(str(Path(exception_review.__file__).parent))
