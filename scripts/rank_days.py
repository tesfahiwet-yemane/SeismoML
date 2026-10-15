#!/usr/bin/env python
"""Rank candidate days by station coverage (FDSN availability) and, optionally,
by the number of events in a reference catalogue.

    python scripts/rank_days.py --start 2012-11-01 --end 2012-12-01
    python scripts/rank_days.py --catalogue data/reference/catalogue.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from obspy import UTCDateTime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alutoml import catalogue  # noqa: E402
from alutoml.config import load_config  # noqa: E402


def coverage_from_fdsn(cfg, t0: UTCDateTime, t1: UTCDateTime) -> pd.DataFrame:
    """Fraction of each day covered, averaged over the configured HHZ channels."""
    import requests

    url = "https://service.iris.edu/fdsnws/availability/1/query"
    params = {
        "net": cfg.network, "sta": ",".join(cfg.stations), "cha": "HHZ",
        "start": str(t0)[:19], "end": str(t1)[:19], "format": "geocsv",
        "merge": "samplerate,quality", "mergegaps": 1.0,
    }
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    from io import StringIO

    av = pd.read_csv(StringIO(r.text), comment="#", sep="|")
    av.columns = [c.strip() for c in av.columns]
    av["Earliest"] = pd.to_datetime(av["Earliest"], utc=True)
    av["Latest"] = pd.to_datetime(av["Latest"], utc=True)
    days = pd.date_range(pd.Timestamp(t0.datetime, tz="UTC"), pd.Timestamp(t1.datetime, tz="UTC"),
                         freq="1D", inclusive="left")
    rows = []
    for d in days:
        e = d + pd.Timedelta(days=1)
        cov = {}
        for _, seg in av.iterrows():
            s, f = max(seg["Earliest"], d), min(seg["Latest"], e)
            if f > s:
                cov[seg["Station"]] = cov.get(seg["Station"], 0) + (f - s).total_seconds() / 86400
        rows.append({"day": d.date(), "n_stations_full": sum(v > 0.99 for v in cov.values()),
                     "mean_coverage": sum(cov.values()) / len(cfg.stations)})
    return pd.DataFrame(rows)


def main() -> int:
    cfg = load_config(ROOT)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2012-11-01")
    ap.add_argument("--end", default="2012-12-01")
    ap.add_argument("--catalogue", default=None)
    ap.add_argument("--no-fdsn", action="store_true")
    args = ap.parse_args()
    t0, t1 = UTCDateTime(args.start), UTCDateTime(args.end)

    table = pd.DataFrame({"day": pd.date_range(args.start, args.end, freq="1D", inclusive="left").date})
    if not args.no_fdsn:
        table = table.merge(coverage_from_fdsn(cfg, t0, t1), on="day", how="left")
    if args.catalogue:
        cat = catalogue.select_window(catalogue.read_catalogue(args.catalogue), t0, t1)
        n = cat.groupby(cat["time"].dt.date).size().rename("n_events")
        table = table.merge(n, left_on="day", right_index=True, how="left").fillna({"n_events": 0})
    sort_cols = [c for c in ("n_stations_full", "n_events", "mean_coverage") if c in table]
    print(table.sort_values(sort_cols, ascending=False).head(15).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
