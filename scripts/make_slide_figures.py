#!/usr/bin/env python
"""Draw the real-data figures used in the slides (docs/slides/figures/).

    python scripts/make_slide_figures.py

Needs the workshop day of waveforms (scripts/fetch_data.py) and the reference picks.
The probability-curve figure also needs the model weights (downloaded on first use).
Each figure is drawn independently: if one fails, the others are still produced.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from obspy import UTCDateTime  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from seismoml import catalogue, data, picking, plotting  # noqa: E402
from seismoml.config import load_config  # noqa: E402

OUT = ROOT / "docs" / "slides" / "figures"
LAVA, BASALT = "#e8590c", "#24313d"


def best_event(cfg):
    """The analyst event with most phases, its picks, and the closest station with P and S."""
    cat = catalogue.select_window(catalogue.read_catalogue(cfg.path("reference_catalogue")), cfg.t0, cfg.t1)
    picks = catalogue.read_reference_picks(cfg.path("reference_picks"))
    picks = picks[picks["event_id"].isin(cat["event_id"]) & picks["station"].isin(cfg.stations)]
    if picks.empty:
        raise SystemExit("No analyst picks on the workshop day: nothing to draw.")
    best_id = picks.groupby("event_id").size().idxmax()   # event with most analyst picks
    ev = cat.set_index("event_id").loc[best_id].copy()
    ev["event_id"] = best_id
    ep = picks[picks["event_id"] == best_id]
    stations = data.active_stations(data.station_table(cfg.path("stations")), cfg.day)
    st_xy = catalogue.to_utm(stations, cfg.utm_epsg)
    e_xy = catalogue.to_utm(pd.DataFrame([ev]), cfg.utm_epsg).iloc[0]
    dist = {r.station: float(np.hypot(r.easting_km - e_xy.easting_km, r.northing_km - e_xy.northing_km))
            for r in st_xy.itertuples()}
    both = [s for s, g in ep.groupby("station") if {"P", "S"} <= set(g["phase"])]
    sta = min(both, key=dist.get) if both else min(ep["station"], key=dist.get)
    return ev, ep, dist, sta


def fig_record_section(cfg, ev, ep, dist, sta):
    t0 = UTCDateTime(ev["time"].timestamp())
    st = data.load_waveforms(cfg.sds, cfg.network, cfg.stations, t0 - 5, t0 + 25)
    st.detrend("demean").filter("bandpass", freqmin=2, freqmax=25, zerophase=True)
    fig = plotting.record_section(st, ep, dist, t0 - 2, t0 + 12,
                                  title=f"Analyst picks · event {ev['time']:%Y-%m-%d %H:%M:%S} UTC")
    fig.set_size_inches(9, 6)
    return fig


def fig_stalta(cfg, ev, ep, dist, sta):
    from obspy.signal.trigger import recursive_sta_lta

    t0 = UTCDateTime(ev["time"].timestamp())
    st = data.load_waveforms(cfg.sds, cfg.network, sta, t0 - 60, t0 + 40, channels="HHZ")
    tr = st.merge(method=1, fill_value="interpolate")[0]
    tr.detrend("demean").taper(0.02).filter("bandpass", freqmin=2, freqmax=20, zerophase=True)
    fs = tr.stats.sampling_rate
    cft = recursive_sta_lta(tr.data.astype(float), int(0.5 * fs), int(10 * fs))
    t = tr.times() + (tr.stats.starttime - t0)
    keep = t > -40  # skip LTA warm-up
    fig, (a0, a1) = plt.subplots(2, 1, figsize=(9, 4.8), sharex=True, layout="constrained")
    a0.plot(t[keep], tr.data[keep], color=BASALT, lw=0.5)
    a0.set_yticks([])
    a0.set_title(f"{cfg.network}.{sta}.HHZ, 2–20 Hz", loc="left", fontsize=11)
    a1.plot(t[keep], cft[keep], color=LAVA, lw=1.2, label="STA/LTA (0.5 s / 10 s)")
    a1.axhline(3.5, color="0.4", ls="--", lw=1, label="trigger on")
    a1.axhline(1.5, color="0.6", ls=":", lw=1, label="trigger off")
    for _, p in ep[ep["station"] == sta].iterrows():
        tp = (p["time"] - ev["time"]).total_seconds()
        for ax in (a0, a1):
            ax.axvline(tp, color=plotting.PHASE_COLOURS[p["phase"]], lw=1.2)
    a1.set_ylabel("Ratio")
    a1.set_xlabel("Seconds after origin time")
    a1.legend(loc="upper left", fontsize=8, frameon=False)
    a1.set_xlim(-20, 30)
    return fig


def fig_probabilities(cfg, ev, ep, dist, sta):
    t0 = UTCDateTime(ev["time"].timestamp())
    st = data.load_waveforms(cfg.sds, cfg.network, sta, t0 - 60, t0 + 60)
    specs = [picking.ModelSpec("PhaseNet", "instance"), picking.ModelSpec("PhaseNet", "volpick"),
             picking.ModelSpec("EQTransformer", "volpick")]
    ann = {s.label: s.load().annotate(st) for s in specs}
    fig = plotting.multi_model_curves(st.slice(t0 - 5, t0 + 20), ann,
                                      title=f"{cfg.network}.{sta}: P and S probabilities")
    for ax in fig.axes[:3]:
        ax.set_xlim(0, 25)
        for _, p in ep[ep["station"] == sta].iterrows():
            ax.axvline((p["time"] - ev["time"]).total_seconds() + 5,
                       color=plotting.PHASE_COLOURS[p["phase"]], lw=1, ls="--")
    fig.set_size_inches(9, 5.5)
    return fig


def main() -> int:
    plotting.use_style()
    cfg = load_config(ROOT)
    OUT.mkdir(parents=True, exist_ok=True)
    ev, ep, dist, sta = best_event(cfg)
    print(f"Event {ev['time']}, demo station {sta}")
    failed = 0
    for name, fn in [("record_section", fig_record_section), ("stalta", fig_stalta),
                     ("probabilities", fig_probabilities)]:
        try:
            fig = fn(cfg, ev, ep, dist, sta)
            fig.savefig(OUT / f"{name}.png", dpi=160, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            print(f"ok   {name}.png")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}.png")
            traceback.print_exc()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
