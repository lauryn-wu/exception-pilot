"""Reuse the unchanged v4/shared journal and providers with isolated family globals."""
from pathlib import Path
import exception_review
__path__.append(str(Path(exception_review.__file__).parent))
