"""Catalogue I/O, coordinate transforms and event matching."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

CATALOGUE_COLUMNS = ["event_id", "time", "latitude", "longitude", "depth_km", "magnitude"]
PICK_COLUMNS = ["event_id", "station", "phase", "time"]


def read_catalogue(path: str | Path) -> pd.DataFrame:
    """Read a catalogue CSV with at least ``time, latitude, longitude, depth_km``.

    ``depth_km`` is below sea level. ``magnitude`` and ``event_id`` are optional.
    """
    df = pd.read_csv(path, comment="#")
    missing = {"time", "latitude", "longitude", "depth_km"} - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    df["time"] = pd.to_datetime(df["time"], utc=True, format="ISO8601")
    if "event_id" not in df:
        df.insert(0, "event_id", np.arange(len(df)))
    if "magnitude" not in df:
        df["magnitude"] = np.nan
    return df.sort_values("time").reset_index(drop=True)


def read_reference_picks(path: str | Path) -> pd.DataFrame:
    """Read analyst picks: ``event_id, station, phase, time`` (+ optional extra columns)."""
    df = pd.read_csv(path, comment="#")
    missing = set(PICK_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    df["time"] = pd.to_datetime(df["time"], utc=True, format="ISO8601")
    df["phase"] = df["phase"].str.upper().str[0]
    return df.sort_values("time").reset_index(drop=True)


def _utc(t) -> pd.Timestamp:
    ts = pd.Timestamp(str(t))
    return ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")


def select_window(df: pd.DataFrame, t0, t1, column: str = "time") -> pd.DataFrame:
    """Rows with ``t0 <= df[column] < t1`` (accepts UTCDateTime, str or Timestamp)."""
    return df[(df[column] >= _utc(t0)) & (df[column] < _utc(t1))].reset_index(drop=True)


def to_utm(df: pd.DataFrame, epsg: int = 32637) -> pd.DataFrame:
    """Add ``easting_km`` and ``northing_km`` columns (default UTM 37N)."""
    tf = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    e, n = tf.transform(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    out = df.copy()
    out["easting_km"] = np.asarray(e) / 1000.0
    out["northing_km"] = np.asarray(n) / 1000.0
    return out


def match_events(
    reference: pd.DataFrame,
    candidate: pd.DataFrame,
    max_dt: float = 3.0,
    max_dist_km: float | None = 10.0,
    epsg: int = 32637,
) -> pd.DataFrame:
    """One-to-one event matching on origin time (and optionally hypocentral distance).

    Returns one row per matched pair with time and location differences
    (candidate minus reference).
    """
    columns = ["ref_id", "cand_id", "dt_s", "dh_km", "dz_km", "dist_km"]
    if reference.empty or candidate.empty:
        return pd.DataFrame(columns=columns)
    a = to_utm(reference, epsg)
    b = to_utm(candidate, epsg)
    ta = a["time"].to_numpy(dtype="datetime64[ns]").astype("int64") / 1e9
    tb = b["time"].to_numpy(dtype="datetime64[ns]").astype("int64") / 1e9
    dt = tb[None, :] - ta[:, None]
    de = b["easting_km"].to_numpy()[None, :] - a["easting_km"].to_numpy()[:, None]
    dn = b["northing_km"].to_numpy()[None, :] - a["northing_km"].to_numpy()[:, None]
    dz = b["depth_km"].to_numpy()[None, :] - a["depth_km"].to_numpy()[:, None]
    dist = np.sqrt(de**2 + dn**2 + dz**2)
    ok = np.abs(dt) <= max_dt
    if max_dist_km is not None:
        ok &= dist <= max_dist_km
    i, j = np.nonzero(ok)
    order = np.argsort(np.abs(dt[i, j]))
    used_a, used_b, rows = set(), set(), []
    for k in order:
        x, y = i[k], j[k]
        if x in used_a or y in used_b:
            continue
        used_a.add(x)
        used_b.add(y)
        rows.append(
            {
                "ref_id": a["event_id"].iloc[x],
                "cand_id": b["event_id"].iloc[y],
                "dt_s": dt[x, y],
                "dh_km": float(np.hypot(de[x, y], dn[x, y])),
                "dz_km": dz[x, y],
                "dist_km": dist[x, y],
            }
        )
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values("ref_id").reset_index(drop=True)


# --------------------------------------------------------------------------
# NonLinLoc
# --------------------------------------------------------------------------
def read_nlloc_hyp(path, min_weight: float = 0.05) -> tuple[dict, list[dict]]:
    """Parse one NonLinLoc ``.hyp`` file (single event).

    Returns the event (maximum-likelihood hypocentre, depth km b.s.l., origin
    quality) and its phases. Phases with an NLLoc weight below ``min_weight``
    (picks the locator effectively rejected) are dropped.
    """
    event, phases, in_phases = {}, [], False
    with open(path) as fh:
        for line in fh:
            tok = line.split()
            if not tok:
                continue
            key = tok[0]
            if key == "GEOGRAPHIC":
                yr, mo, dy, hr, mn = (int(v) for v in tok[2:7])
                sec = float(tok[7])
                event["time"] = pd.Timestamp(yr, mo, dy, hr, mn, tz="UTC") + pd.Timedelta(seconds=sec)
                event["latitude"] = float(tok[9])
                event["longitude"] = float(tok[11])
                event["depth_km"] = float(tok[13])
            elif key == "QUALITY":
                q = dict(zip(tok[1::2], tok[2::2]))
                event["rms_s"] = float(q["RMS"])
                event["n_phases"] = int(q["Nphs"])
                event["gap_deg"] = float(q["Gap"])
                event["min_dist_km"] = float(q["Dist"])
            elif key == "QML_OriginUncertainty":
                q = dict(zip(tok[1::2], tok[2::2]))
                event["err_h_km"] = float(q["maxHorUnc"])
            elif key == "QML_ConfidenceEllipsoid":
                q = dict(zip(tok[1::2], tok[2::2]))
                event["err_max_km"] = float(q["semiMajorAxisLength"])
            elif key == "PHASE":
                in_phases = True
            elif key == "END_PHASE":
                in_phases = False
            elif in_phases:
                sta, pha = tok[0], tok[4]
                date, hrmn, sec = tok[6], tok[7], float(tok[8])
                t = pd.Timestamp(f"{date[:4]}-{date[4:6]}-{date[6:]}T{hrmn[:2]}:{hrmn[2:]}:00",
                                 tz="UTC") + pd.Timedelta(seconds=sec)
                gt = tok.index(">")
                weight = float(tok[gt + 3])
                if weight < min_weight:
                    continue
                phases.append({"station": sta, "phase": pha.upper()[0], "time": t,
                               "residual_s": float(tok[gt + 2]), "weight": weight})
    if "time" not in event:
        raise ValueError(f"{path}: no GEOGRAPHIC line (not located?)")
    event["magnitude"] = np.nan
    event["source_file"] = Path(path).name
    return event, phases


def nlloc_to_tables(paths, min_weight: float = 0.05) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert many ``.hyp`` files into ``catalogue`` and ``picks`` tables (sorted by time)."""
    parsed = sorted((read_nlloc_hyp(p, min_weight) for p in paths), key=lambda x: x[0]["time"])
    events, picks = [], []
    for eid, (ev, ph) in enumerate(parsed):
        events.append({"event_id": eid, **ev})
        picks += [{"event_id": eid, **p} for p in ph]
    cat = pd.DataFrame(events)
    pk = pd.DataFrame(picks, columns=["event_id", "station", "phase", "time", "residual_s", "weight"])
    return cat, pk


def write_table(df: pd.DataFrame, path) -> None:
    """CSV with ISO 8601 UTC times (millisecond precision)."""
    out = df.copy()
    out["time"] = pd.to_datetime(out["time"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z"
    out.to_csv(path, index=False, float_format="%.5f")
