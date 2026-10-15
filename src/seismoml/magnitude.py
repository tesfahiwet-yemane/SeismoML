"""Local magnitude for the Main Ethiopian Rift (Keir et al., 2006)."""

from __future__ import annotations

import logging
from typing import Callable

import numpy as np
import pandas as pd
from obspy import Inventory, Stream, UTCDateTime
from obspy.geodetics import gps2dist_azimuth

log = logging.getLogger(__name__)

# Keir, D., Stuart, G. W., Jackson, A., & Ayele, A. (2006). Local earthquake
# magnitude scale and seismicity rate for the Ethiopian Rift. BSSA 96(6), 2221-2230.
#   ML = log10(A) + 1.196997 * log10(r / 17) + 0.001066 * (r - 17) + 2.0
# A: zero-to-peak Wood-Anderson amplitude in mm, measured on each horizontal
# component separately; r: hypocentral distance in km.
KEIR2006 = {"n": 1.196997, "k": 0.001066, "r_ref": 17.0, "m_ref": 2.0}

# Wood-Anderson torsion seismometer as used by Keir et al. (2006): natural period
# 0.8 s, damping 0.8, static magnification 2800. Applied to ground velocity
# (one zero), it returns Wood-Anderson displacement.
_W0 = 2 * np.pi / 0.8
_H = 0.8
WOOD_ANDERSON = {
    "poles": [complex(-_H * _W0, _W0 * np.sqrt(1 - _H**2)),
              complex(-_H * _W0, -_W0 * np.sqrt(1 - _H**2))],
    "zeros": [0j],
    "gain": 1.0,
    "sensitivity": 2800.0,
}


def ml_keir2006(amp_mm, r_km):
    """Local magnitude from Wood-Anderson amplitude (mm) and hypocentral distance (km)."""
    c = KEIR2006
    amp_mm = np.asarray(amp_mm, dtype=float)
    r_km = np.asarray(r_km, dtype=float)
    return (
        np.log10(amp_mm)
        + c["n"] * np.log10(r_km / c["r_ref"])
        + c["k"] * (r_km - c["r_ref"])
        + c["m_ref"]
    )


def wood_anderson_amplitudes(
    stream: Stream,
    inventory: Inventory,
    t0: UTCDateTime,
    t1: UTCDateTime,
    pre_filt=(0.5, 1.0, 40.0, 45.0),
) -> dict[str, float]:
    """Zero-to-peak Wood-Anderson amplitude (mm) of each horizontal channel in ``[t0, t1]``.

    ``stream`` should extend some seconds beyond the window on both sides, so
    that tapering and deconvolution do not affect the measurement.
    """
    out = {}
    for tr in stream.select(channel="??[NE12]"):
        if tr.stats.endtime < t1 or tr.stats.starttime > t0:
            continue  # window not fully covered by this segment
        tr = tr.copy()
        try:
            tr.detrend("demean").taper(0.05)
            tr.remove_response(inventory=inventory, output="VEL", pre_filt=pre_filt)
            tr.simulate(paz_simulate=WOOD_ANDERSON, water_level=None)
        except Exception as exc:  # noqa: BLE001 - missing response etc.
            log.warning("No WA amplitude for %s: %s", tr.id, exc)
            continue
        win = tr.slice(t0, t1)
        if win.stats.npts:
            out[tr.stats.channel] = 1000.0 * float(np.abs(win.data).max())  # m -> mm
    return out


def measurement_window(picks: pd.DataFrame) -> tuple[UTCDateTime, UTCDateTime]:
    """From 0.5 s before P to 1.5 x (S-P) after S (5 s after the first pick if P or S is missing)."""
    p = picks.loc[picks["phase"] == "P", "time"]
    s = picks.loc[picks["phase"] == "S", "time"]
    tp = UTCDateTime(p.min().timestamp()) if len(p) else None
    ts = UTCDateTime(s.min().timestamp()) if len(s) else None
    first = min(t for t in (tp, ts) if t is not None)
    if tp is not None and ts is not None and ts > tp:
        return first - 0.5, ts + 1.5 * (ts - tp)
    return first - 0.5, first + 5.0


def catalogue_magnitudes(
    events: pd.DataFrame,
    assigned_picks: pd.DataFrame,
    stations: pd.DataFrame,
    inventory: Inventory,
    load_station: Callable[[str], Stream],
    min_stations: int = 2,
    pad: float = 20.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Network ML for every event of a catalogue.

    Stations are processed one at a time (``load_station(code)`` returns that
    station's waveforms for the day), so memory stays at one station-day.
    Every horizontal component gives one ML value (Keir et al., 2006); the
    event magnitude is the median of all component values from at least
    ``min_stations`` stations. No station corrections are applied.

    Returns the events with ``magnitude`` and ``n_mag_stations`` columns, and
    the per-component amplitude table.
    """
    ev = events.set_index("event_id")
    coords = stations.set_index("station")
    rows = []
    for sta, picks_sta in assigned_picks.groupby("station"):
        if sta not in coords.index:
            continue
        try:
            st_day = load_station(sta)
        except FileNotFoundError as exc:
            log.warning("%s", exc)
            continue
        s = coords.loc[sta]
        for eid, p in picks_sta.groupby("event_id"):
            if eid not in ev.index:
                continue
            t0, t1 = measurement_window(p)
            amps = wood_anderson_amplitudes(st_day.slice(t0 - pad, t1 + pad), inventory, t0, t1)
            e = ev.loc[eid]
            epi_m, _, _ = gps2dist_azimuth(e["latitude"], e["longitude"], s["latitude"], s["longitude"])
            r = float(np.hypot(epi_m / 1000.0, e["depth_km"] + s["elevation_m"] / 1000.0))
            for cha, a in amps.items():
                if a > 0:
                    rows.append({"event_id": eid, "station": sta, "channel": cha,
                                 "amp_mm": a, "r_km": r})
    per = pd.DataFrame(rows, columns=["event_id", "station", "channel", "amp_mm", "r_km"])
    per["ML"] = ml_keir2006(per["amp_mm"], per["r_km"]) if len(per) else pd.Series(dtype=float)
    n_sta = per.groupby("event_id")["station"].nunique()
    ml = per.groupby("event_id")["ML"].median().where(n_sta >= min_stations)
    out = events.copy()
    out["magnitude"] = out["event_id"].map(ml)
    out["n_mag_stations"] = out["event_id"].map(n_sta).fillna(0).astype(int)
    return out, per
