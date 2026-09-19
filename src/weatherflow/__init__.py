"""Weatherflow command line interface.

The pipeline lives in the repository (`pipeline/`, `common/`, `config/`) rather
than inside the installed package, so this shortcut resolves the project root
first and then delegates to ``pipeline.main``.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    """Run the weather pipeline (same as ``python -m pipeline.main``)."""

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from pipeline.main import main as run_pipeline

    return run_pipeline()


__all__ = ["main"]

