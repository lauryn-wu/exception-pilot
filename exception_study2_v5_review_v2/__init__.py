"""Additive CPU-only candidate-first review. Scientific v5 remains frozen."""
from pathlib import Path
import exception_review
VERSION = 'study2-review-v2.1'
# Load the unchanged shared journal/providers in an isolated policy namespace.
__path__.append(str(Path(exception_review.__file__).parent))
