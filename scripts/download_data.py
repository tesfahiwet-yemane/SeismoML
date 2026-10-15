#!/usr/bin/env python
"""Download the workshop day of ARGOS (XM) data from the EarthScope/IRIS FDSN service.

Writes miniSEED into an SDS archive and the StationXML (with responses) next to it.

    python scripts/download_data.py                  # day and stations from workshop.yml
    python scripts/download_data.py --day 2012-11-20 # another day
    python scripts/download_data.py --stations A01E A10E --hours 1
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from obspy import UTCDateTime

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from seismoml import data  # noqa: E402
from seismoml.config import load_config  # noqa: E402


def main() -> int:
    cfg = load_config(Path(__file__).resolve().parents[1])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--day", default=str(cfg.day.date), help="UTC day (YYYY-MM-DD)")
    ap.add_argument("--stations", nargs="+", default=cfg.stations)
    ap.add_argument("--hours", type=float, default=24.0, help="hours to fetch from 00:00 UTC")
    ap.add_argument("--sds", default=str(cfg.sds))
    ap.add_argument("--inventory", default=str(cfg.inventory_file))
    ap.add_argument("--provider", default=cfg.provider)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t0 = UTCDateTime(args.day)
    t1 = t0 + args.hours * 3600
    client = data.fdsn_client(args.provider)

    inv_path = Path(args.inventory)
    inv_path.parent.mkdir(parents=True, exist_ok=True)
    inv = data.download_inventory(client, cfg.network, args.stations, t0, t1, cfg.channels)
    inv.write(str(inv_path), format="STATIONXML")
    logging.info("Inventory: %d stations -> %s", len(inv[0]), inv_path)

    missing = []
    for sta in args.stations:
        st = data.download_waveforms(client, cfg.network, sta, t0, t1, cfg.channels, cfg.location)
        if len(st) == 0:
            missing.append(sta)
            continue
        files = data.write_sds(st, args.sds)
        logging.info("%s: %d traces, %d files", sta, len(st), len(files))
    if missing:
        logging.warning("No data returned for: %s", ", ".join(missing))
    return 0 if len(missing) < len(args.stations) else 1


if __name__ == "__main__":
    raise SystemExit(main())
