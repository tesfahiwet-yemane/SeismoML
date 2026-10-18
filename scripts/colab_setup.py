#!/usr/bin/env python
"""Prepare a Google Colab runtime for the workshop notebooks.

Called by the first code cell of every notebook when it runs on Colab:

    python scripts/colab_setup.py                     # packages only
    python scripts/colab_setup.py --data              # + the workshop day of waveforms
    python scripts/colab_setup.py --data --outputs    # + precomputed picks and catalogues

Every Colab notebook runs on its own fresh machine, so notebooks 02-05 download the
picks and catalogues produced by the latest website build instead of recomputing them.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Colab already provides numpy, pandas, scipy, matplotlib, scikit-learn and PyTorch.
PACKAGES = ["seisbench==0.12.6", "pyocto==0.2.0", "obspy==1.5.1", "pyrocko", "pyproj", "PyYAML"]


def pip_install() -> None:
    print("Installing seismology packages (about 1 minute)...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *PACKAGES], check=True)


def fetch_outputs() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    from seismoml.config import load_config

    cfg = load_config(ROOT)
    if (cfg.outputs / "picks").is_dir() and (cfg.outputs / "catalogues").is_dir():
        print("Precomputed outputs already present.")
        return
    url = cfg.raw.get("archive", {}).get("outputs_url", "")
    if not url:
        print("No outputs_url in workshop.yml; run the earlier notebooks first.")
        return
    print("Downloading precomputed picks and catalogues...")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "outputs.tar.gz"
            urllib.request.urlretrieve(url, dest)
            with tarfile.open(dest) as tar:
                tar.extractall(ROOT, filter="data")
        print("Outputs ready in", cfg.outputs)
    except Exception as exc:  # noqa: BLE001
        print(f"Could not download precomputed outputs ({exc}).")
        print("Run notebooks 02 and 03 in this session first, or wait for the next website build.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", action="store_true", help="download the workshop day of waveforms")
    ap.add_argument("--outputs", action="store_true", help="download precomputed picks and catalogues")
    args = ap.parse_args()
    pip_install()
    if args.data:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "fetch_data.py")], check=True)
    if args.outputs:
        fetch_outputs()
    print("Colab setup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
