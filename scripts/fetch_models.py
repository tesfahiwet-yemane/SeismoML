#!/usr/bin/env python
"""Download every model used in the notebooks into the SeisBench cache (~/.seisbench).

    python scripts/fetch_models.py

Useful before a workshop or a flight: afterwards the notebooks need no access to the
SeisBench model repository. Falls back to the GFZ backup mirror automatically.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from seismoml.picking import ModelSpec  # noqa: E402

MODELS = [
    ("DeepDenoiser", "original"), ("DeepDenoiser", "urban"),
    ("PhaseNet", "original"), ("PhaseNet", "instance"), ("PhaseNet", "stead"), ("PhaseNet", "volpick"),
    ("EQTransformer", "original"), ("EQTransformer", "volpick"),
]


def main() -> int:
    for arch, weights in MODELS:
        ModelSpec(arch, weights).load()
        print(f"ok  {arch:14s} {weights}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
