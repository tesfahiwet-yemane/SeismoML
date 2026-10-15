"""Figures used throughout the workshop (matplotlib only, no GUI backend assumptions)."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colormaps
from matplotlib.dates import DateFormatter

PHASE_COLOURS = {"P": "#1f77b4", "S": "#d62728"}
MODEL_CMAP = "tab10"


def use_style() -> None:
    """Consistent, publication-like defaults for every notebook."""
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": 200,
            "figure.constrained_layout.use": True,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "legend.frameon": False,
        }
    )


def model_colours(names) -> dict[str, tuple]:
    cmap = colormaps[MODEL_CMAP]
    return {n: cmap(i % cmap.N) for i, n in enumerate(names)}


# --------------------------------------------------------------------------
# Waveforms
# --------------------------------------------------------------------------
def _rel_times(tr, ref):
    return tr.times() + (tr.stats.starttime - ref)


def waveform_spectrogram(stream, title: str = "", fmax: float = 50.0, nfft: int = 256):
    """Each component as a waveform panel above its spectrogram (dB, shared scale)."""
    st = stream.copy()
    st.sort(keys=["channel"])
    ref = min(tr.stats.starttime for tr in st)
    n = len(st)
    fig, axes = plt.subplots(
        2 * n, 1, figsize=(10, 2.2 * n + 1), sharex=True,
        gridspec_kw={"height_ratios": [1, 1.6] * n},
    )
    images = []
    for k, tr in enumerate(st):
        ax_w, ax_s = axes[2 * k], axes[2 * k + 1]
        t = _rel_times(tr, ref)
        ax_w.plot(t, tr.data, lw=0.5, color="k")
        ax_w.set_ylabel(tr.stats.channel, rotation=0, ha="right", va="center")
        ax_w.set_yticks([])
        _, _, _, im = ax_s.specgram(
            tr.data - np.mean(tr.data), NFFT=nfft, Fs=tr.stats.sampling_rate,
            noverlap=nfft // 2, cmap="magma", scale="dB",
            xextent=(t[0], t[-1]),
        )
        images.append(im)
        ax_s.set_ylim(0, fmax)
        ax_s.set_ylabel("Hz")
        ax_s.grid(False)
    lo = np.percentile([im.get_array().min() for im in images], 50)
    hi = max(im.get_array().max() for im in images)
    for im in images:
        im.set_clim(max(lo, hi - 80), hi)
    fig.colorbar(images[-1], ax=axes[1::2], label="Power (dB)", shrink=0.8)
    axes[-1].set_xlabel(f"Seconds after {ref.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    if title:
        axes[0].set_title(title)
    return fig


def probability_panel(stream, annotations, picks: pd.DataFrame | None = None, title: str = ""):
    """Vertical waveform plus the model's P/S probability curves (and optional picks)."""
    ref = min(tr.stats.starttime for tr in stream)
    z = stream.select(component="Z") or stream[:1]
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(10, 4.5), sharex=True,
                                   gridspec_kw={"height_ratios": [1.2, 1]})
    for tr in z:
        ax0.plot(_rel_times(tr, ref), tr.data, lw=0.5, color="k")
    ax0.set_ylabel(z[0].stats.channel)
    ax0.set_yticks([])
    for tr in annotations:
        phase = tr.stats.channel.split("_")[-1]
        if phase not in PHASE_COLOURS:
            continue
        ax1.plot(_rel_times(tr, ref), tr.data, lw=1.0, color=PHASE_COLOURS[phase], label=phase)
    if picks is not None and len(picks):
        for _, p in picks.iterrows():
            t = (p["time"] - pd.Timestamp(ref.datetime, tz="UTC")).total_seconds()
            for ax in (ax0, ax1):
                ax.axvline(t, color=PHASE_COLOURS.get(p["phase"], "grey"), lw=0.8, ls="--")
    ax1.set_ylim(0, 1.02)
    ax1.set_ylabel("Probability")
    ax1.legend(loc="upper right", ncols=2)
    ax1.set_xlabel(f"Seconds after {ref.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    if title:
        ax0.set_title(title)
    return fig


def record_section(stream, picks: pd.DataFrame | None, station_dist: dict[str, float],
                   t0, t1, title: str = "", component: str = "Z"):
    """Normalised traces sorted by distance with picks overlaid."""
    fig, ax = plt.subplots(figsize=(9, 0.45 * len(station_dist) + 1.5))
    order = sorted(station_dist, key=station_dist.get)
    ref = pd.Timestamp(t0.datetime, tz="UTC")
    for k, sta in enumerate(order):
        sel = stream.select(station=sta, component=component).slice(t0, t1)
        for tr in sel:
            d = tr.data - np.mean(tr.data)
            d = d / (np.abs(d).max() or 1)
            ax.plot(tr.times() + (tr.stats.starttime - t0), k + 0.45 * d, lw=0.5, color="k")
        if picks is not None:
            for _, p in picks[picks["station"] == sta].iterrows():
                t = (p["time"] - ref).total_seconds()
                ax.plot([t, t], [k - 0.45, k + 0.45], color=PHASE_COLOURS[p["phase"]], lw=1.5)
    ax.set_yticks(range(len(order)), [f"{s}  {station_dist[s]:.1f} km" for s in order])
    ax.set_xlim(0, t1 - t0)
    ax.set_xlabel(f"Seconds after {t0.strftime('%H:%M:%S')} UTC")
    ax.set_title(title)
    return fig


# --------------------------------------------------------------------------
# Picks
# --------------------------------------------------------------------------
def probability_histograms(tables: dict[str, pd.DataFrame], bins=np.linspace(0, 1, 21)):
    """P and S probability distributions for several pick tables."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5), sharey=True)
    colours = model_colours(tables)
    for ax, ph in zip(axes, ("P", "S")):
        for name, df in tables.items():
            v = df.loc[df["phase"] == ph, "probability"]
            ax.hist(v, bins=bins, histtype="step", lw=1.6, color=colours[name],
                    label=f"{name} ({len(v)})")
        ax.set_title(f"{ph} picks")
        ax.set_xlabel("Peak probability")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Number of picks")
    return fig


def picks_per_hour(tables: dict[str, pd.DataFrame], phase: str = "P"):
    fig, ax = plt.subplots(figsize=(10, 3))
    colours = model_colours(tables)
    for name, df in tables.items():
        s = df.loc[df["phase"] == phase].set_index("time").resample("1h").size()
        ax.step(s.index, s.values, where="post", color=colours[name], label=name)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    ax.set_ylabel(f"{phase} picks / hour")
    ax.legend(fontsize=8, ncols=3)
    return fig


def matrix_heatmap(mat: pd.DataFrame, title: str = "", fmt: str = "{:.2f}", cmap="viridis"):
    fig, ax = plt.subplots(figsize=(0.9 * len(mat.columns) + 2.5, 0.7 * len(mat.index) + 1.6))
    im = ax.imshow(mat.to_numpy(dtype=float), vmin=0, vmax=1, cmap=cmap)
    ax.set_xticks(range(len(mat.columns)), mat.columns, rotation=40, ha="right")
    ax.set_yticks(range(len(mat.index)), mat.index)
    for i in range(len(mat.index)):
        for j in range(len(mat.columns)):
            v = mat.iat[i, j]
            if np.isfinite(v):
                ax.text(j, i, fmt.format(v), ha="center", va="center",
                        color="w" if v < 0.6 else "k", fontsize=9)
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title(title)
    return fig


def residual_histograms(matches: dict[str, pd.DataFrame], tolerance: float = 0.5):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5), sharey=False)
    colours = model_colours(matches)
    bins = np.linspace(-tolerance, tolerance, 41)
    for ax, ph in zip(axes, ("P", "S")):
        for name, m in matches.items():
            r = m.loc[m["phase"] == ph, "residual"]
            ax.hist(r, bins=bins, histtype="step", lw=1.6, color=colours[name],
                    label=f"{name}: med {r.median():+.3f} s" if len(r) else name)
        ax.axvline(0, color="k", lw=0.8)
        ax.set_title(f"{ph}: ML minus reference")
        ax.set_xlabel("Residual (s)")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Count")
    return fig


# --------------------------------------------------------------------------
# Maps and sections
# --------------------------------------------------------------------------
def _geo_aspect(ax, lat):
    ax.set_aspect(1.0 / np.cos(np.radians(lat)))


def event_map(stations: pd.DataFrame, events: pd.DataFrame | None = None,
              lat=None, lon=None, depth_range=(-2.5, 15), title: str = "",
              colour_by: str = "depth_km", size_by: str | None = None, ax=None,
              label_stations: bool = True):
    """Map view (lon/lat, true aspect) with depth-coloured events and stations."""
    own = ax is None
    if own:
        fig, ax = plt.subplots(figsize=(6.5, 6))
    else:
        fig = ax.figure
    sc = None
    if events is not None and len(events):
        sizes = 12 if size_by is None else 6 + 8 * (events[size_by] - events[size_by].min() + 0.5) ** 2
        sc = ax.scatter(events["longitude"], events["latitude"], c=events[colour_by],
                        s=sizes, cmap="viridis_r", vmin=depth_range[0], vmax=depth_range[1],
                        edgecolor="k", lw=0.3, zorder=3)
        if own:
            fig.colorbar(sc, ax=ax, label="Depth b.s.l. (km)", shrink=0.8)
    ax.scatter(stations["longitude"], stations["latitude"], marker="^", s=70,
               color="#ff7f0e", edgecolor="k", zorder=4, label="ARGOS station")
    if label_stations:
        for _, s in stations.iterrows():
            ax.annotate(s["station"], (s["longitude"], s["latitude"]), xytext=(4, 4),
                        textcoords="offset points", fontsize=7)
    if lat is not None:
        ax.set_ylim(*lat)
    if lon is not None:
        ax.set_xlim(*lon)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    _geo_aspect(ax, np.mean(ax.get_ylim()))
    ax.legend(loc="lower right", fontsize=8)
    if title:
        ax.set_title(title)
    return fig, sc


def map_and_sections(stations: pd.DataFrame, catalogues: dict[str, pd.DataFrame],
                     lat, lon, depth_range=(-2.5, 15), title: str = ""):
    """Map plus E-W and N-S depth sections for one or more catalogues."""
    fig = plt.figure(figsize=(10, 8.5))
    gs = fig.add_gridspec(2, 2, width_ratios=[3, 1.3], height_ratios=[3, 1.3])
    ax_map = fig.add_subplot(gs[0, 0])
    ax_ns = fig.add_subplot(gs[0, 1], sharey=ax_map)
    ax_ew = fig.add_subplot(gs[1, 0], sharex=ax_map)
    colours = model_colours(catalogues)
    markers = ["o", "s", "D", "v", "P"]
    for k, (name, cat) in enumerate(catalogues.items()):
        kw = dict(s=16, color=colours[name], marker=markers[k % len(markers)],
                  edgecolor="k", lw=0.3, alpha=0.85, label=f"{name} ({len(cat)})")
        ax_map.scatter(cat["longitude"], cat["latitude"], **kw)
        ax_ew.scatter(cat["longitude"], cat["depth_km"], **kw)
        ax_ns.scatter(cat["depth_km"], cat["latitude"], **kw)
    for ax_, x, y in ((ax_map, "longitude", "latitude"),):
        ax_.scatter(stations[x], stations[y], marker="^", s=60, color="#ff7f0e",
                    edgecolor="k", zorder=5, label="stations")
    ax_ew.scatter(stations["longitude"], -stations["elevation_m"] / 1000, marker="v",
                  s=30, color="#ff7f0e", edgecolor="k")
    ax_ns.scatter(-stations["elevation_m"] / 1000, stations["latitude"], marker=">",
                  s=30, color="#ff7f0e", edgecolor="k")
    ax_map.set_xlim(*lon)
    ax_map.set_ylim(*lat)  # near the equator 1° lon ≈ 1° lat, so panels stay aligned
    ax_map.set_ylabel("Latitude (°N)")
    ax_map.legend(loc="lower right", fontsize=8)
    ax_ew.set_ylim(depth_range[1], depth_range[0])
    ax_ew.set_ylabel("Depth (km b.s.l.)")
    ax_ew.set_xlabel("Longitude (°E)")
    ax_ns.set_xlim(depth_range[0], depth_range[1])
    ax_ns.set_xlabel("Depth (km)")
    plt.setp(ax_ns.get_yticklabels(), visible=False)
    plt.setp(ax_map.get_xticklabels(), visible=False)
    fig.set_constrained_layout(True)
    if title:
        ax_map.set_title(title)
    return fig


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------
def fmd_plot(fmd_table: pd.DataFrame, mc: float | None = None, b: float | None = None,
             a: float | None = None, label: str = "", ax=None):
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4.5))
    else:
        fig = ax.figure
    ax.semilogy(fmd_table["magnitude"], fmd_table["cumulative"], "o", ms=4, color="k",
                label="Cumulative")
    ax.semilogy(fmd_table["magnitude"], fmd_table["count"].replace(0, np.nan), "s", ms=4,
                mfc="none", color="grey", label="Non-cumulative")
    if mc is not None and np.isfinite(mc):
        ax.axvline(mc, color="#d62728", ls="--", lw=1, label=f"Mc = {mc:.1f}")
    if b is not None and a is not None and np.isfinite(b):
        m = np.linspace(mc, fmd_table["magnitude"].max(), 50)
        ax.semilogy(m, 10 ** (a - b * m), color="#1f77b4", lw=1.6, label=f"b = {b:.2f}")
    ax.set_xlabel("Magnitude")
    ax.set_ylabel("Number of events")
    ax.legend()
    if label:
        ax.set_title(label)
    return fig


def multi_model_curves(stream, annotations: dict, title: str = "", component: str = "Z"):
    """Waveform on top, then one panel per phase comparing several models' probabilities."""
    ref = min(tr.stats.starttime for tr in stream)
    z = stream.select(component=component) or stream[:1]
    fig, axes = plt.subplots(3, 1, figsize=(10, 6.5), sharex=True,
                             gridspec_kw={"height_ratios": [1.1, 1, 1]})
    for tr in z:
        axes[0].plot(_rel_times(tr, ref), tr.data, lw=0.5, color="k")
    axes[0].set_yticks([])
    axes[0].set_ylabel(z[0].stats.channel)
    colours = model_colours(annotations)
    for ax, ph in zip(axes[1:], ("P", "S")):
        for name, ann in annotations.items():
            for tr in ann:
                if tr.stats.channel.split("_")[-1] == ph:
                    ax.plot(_rel_times(tr, ref), tr.data, lw=1.1, color=colours[name], label=name)
        ax.set_ylim(0, 1.02)
        ax.set_ylabel(f"{ph} probability")
    handles, labels = axes[1].get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    axes[1].legend(uniq.values(), uniq.keys(), fontsize=8, ncols=3, loc="upper right")
    axes[-1].set_xlabel(f"Seconds after {ref.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    if title:
        axes[0].set_title(title)
    return fig


def deployment_timeline(table: pd.DataFrame, day=None, title: str = "ARGOS deployment"):
    """Gantt chart of station epochs with the workshop day highlighted."""
    fig, ax = plt.subplots(figsize=(10, 4))
    stations = sorted(table["station"].unique(), reverse=True)
    for k, sta in enumerate(stations):
        for _, row in table[table["station"] == sta].iterrows():
            ax.plot([row["start"], row["end"]], [k, k], lw=7, solid_capstyle="butt",
                    color="#4c72b0")
    if day is not None:
        d = pd.Timestamp(str(day)[:10])
        ax.axvline(d, color="#d62728", lw=2, label=f"Workshop day {d.date()}")
        ax.legend(loc="lower left")
    ax.set_yticks(range(len(stations)), stations)
    ax.set_title(title)
    return fig
