#!/usr/bin/env python
"""Get the workshop data the fast way: the pre-packed release archive.

Falls back to a direct FDSN download (scripts/download_data.py) if the archive
is not available. Does nothing if the data are already in place.

    python scripts/fetch_data.py
    python scripts/fetch_data.py --force-fdsn
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from seismoml.config import load_config  # noqa: E402


def have_data(cfg) -> bool:
    day = cfg.day
    files = list(cfg.sds.glob(f"{day.year}/{cfg.network}/*/HHZ.D/*.{day.julday:03d}"))
    return cfg.inventory_file.exists() and len(files) >= len(cfg.stations) - 1


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def from_archive(cfg) -> bool:
    url = cfg.raw.get("archive", {}).get("url", "")
    expected = cfg.raw.get("archive", {}).get("sha256", "")
    if not url or "tesfahiwet-yemane/SeismoML" in url:
        print("No archive URL configured; skipping.")
        return False
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "data.tar.gz"
        print(f"Downloading {url}")
        try:
            urllib.request.urlretrieve(url, dest)
        except Exception as exc:  # noqa: BLE001
            print(f"Archive download failed: {exc}")
            return False
        if expected and sha256(dest) != expected:
            print("Checksum mismatch; ignoring archive.")
            return False
        with tarfile.open(dest) as tar:
            tar.extractall(ROOT, filter="data")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force-fdsn", action="store_true")
    args = ap.parse_args()
    cfg = load_config(ROOT)
    if have_data(cfg):
        print("Data already present.")
        return 0
    if not args.force_fdsn and from_archive(cfg) and have_data(cfg):
        print("Data extracted from archive.")
        return 0
    print("Downloading from FDSN instead.")
    return subprocess.call([sys.executable, str(ROOT / "scripts" / "download_data.py")])


if __name__ == "__main__":
    raise SystemExit(main())
