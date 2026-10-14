"""Versioned source adapter over unchanged judge modules.

Python's explicit package search path reuses workflow/journal/providers/decisions/
editing/boundaries/fixtures/semantic_eval source verbatim under this namespace.
Local adapters override artifacts/policy/integration/reporting; no module globals
are patched. Both package trees are fingerprinted by the v4 source contract.
"""
from pathlib import Path
import exception_review
VERSION = 'study2-automated-review-conditional-prefix-v4'
__path__.append(str(Path(exception_review.__file__).parent))
