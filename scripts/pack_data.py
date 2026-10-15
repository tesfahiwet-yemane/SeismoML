#!/usr/bin/env python
"""Pack the downloaded day (SDS + StationXML) into a release archive and print its checksum.

    python scripts/pack_data.py            # -> dist/aluto_xm_<day>.tar.gz
"""

from __future__ import annotations

import hashlib
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alutoml.config import load_config  # noqa: E402


def main() -> int:
    cfg = load_config(ROOT)
    out = ROOT / "dist" / f"aluto_xm_{cfg.day.date}.tar.gz"
    out.parent.mkdir(exist_ok=True)
    with tarfile.open(out, "w:gz") as tar:
        tar.add(cfg.sds, arcname=str(cfg.sds.relative_to(ROOT)))
        tar.add(cfg.inventory_file, arcname=str(cfg.inventory_file.relative_to(ROOT)))
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"{out}  {out.stat().st_size / 1e6:.1f} MB")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
