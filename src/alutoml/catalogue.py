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
