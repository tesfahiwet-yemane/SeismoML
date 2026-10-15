#!/usr/bin/env python
"""Convert NonLinLoc .hyp files into the reference catalogue and pick tables.

    python scripts/nlloc_to_csv.py                         # data/reference/nlloc/*.hyp
    python scripts/nlloc_to_csv.py ~/NLL/loc/*.grid0.loc.hyp --min-weight 0.1

Writes data/reference/catalogue.csv and data/reference/picks.csv (format:
data/reference/README.md). Re-run it whenever you add or change .hyp files.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from seismoml import catalogue  # noqa: E402
from seismoml.config import load_config  # noqa: E402


def main() -> int:
    cfg = load_config(ROOT)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="NonLinLoc .hyp files (default: data/reference/nlloc/*.hyp)")
    ap.add_argument("--min-weight", type=float, default=0.05,
                    help="drop phases the locator down-weighted below this (default 0.05)")
    args = ap.parse_args()
    files = [Path(f) for f in args.files] or sorted((ROOT / "data/reference/nlloc").glob("*.hyp"))
    files = [f for f in files if not f.name.endswith("sum.grid0.loc.hyp")]  # skip NLLoc summary files
    if not files:
        print("No .hyp files given or found.")
        return 1
    cat, picks = catalogue.nlloc_to_tables(files, args.min_weight)
    catalogue.write_table(cat, cfg.path("reference_catalogue"))
    catalogue.write_table(picks, cfg.path("reference_picks"))
    print(f"{len(cat)} events, {len(picks)} picks -> {cfg.path('reference_catalogue').parent}")
    print(cat[["event_id", "time", "latitude", "longitude", "depth_km", "rms_s", "n_phases", "gap_deg"]]
          .to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
