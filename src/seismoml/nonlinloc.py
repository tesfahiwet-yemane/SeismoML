"""Export an associated catalogue as a ready-to-run NonLinLoc project.

``write_project`` creates::

    <folder>/
        obs/<YYYYmmddHHMMSSfff>.nonlinloc   one NLLOC_OBS file per event
        stations.txt                        GTSRCE lines (station coordinates)
        model.txt                           LAYER lines (1D velocity model)
        nlloc.in                            control file (Vel2Grid, Grid2Time, NLLoc)
        run_nlloc.sh                        runs the three programs in order

NonLinLoc: Lomax et al. (2000), http://alomax.free.fr/nlloc/ and
https://github.com/alomax/NonLinLoc
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .association import read_velocity_model


def pick_uncertainty(probability, best: float = 0.03, worst: float = 0.20) -> np.ndarray:
    """Gaussian pick error (s) from the model probability: 1 -> ``best``, 0 -> ``worst``."""
    p = np.clip(np.asarray(probability, dtype=float), 0.0, 1.0)
    return worst - (worst - best) * p


def obs_lines(picks: pd.DataFrame) -> list[str]:
    """NLLOC_OBS phase lines for one event (columns: station, phase, time, probability)."""
    lines = []
    for _, p in picks.sort_values("time").iterrows():
        t = pd.Timestamp(p["time"]).tz_convert("UTC")
        sec = t.second + t.microsecond / 1e6
        err = float(pick_uncertainty(p.get("probability", 0.5)))
        lines.append(
            f"{p['station']:<6s} ?    ?    ? {p['phase'].upper():<6s} ? "
            f"{t:%Y%m%d} {t:%H%M} {sec:9.4f} GAU {err:9.2e} -1.00e+00 -1.00e+00 -1.00e+00"
        )
    return lines


def write_obs(events: pd.DataFrame, assigned: pd.DataFrame, folder: str | Path) -> list[Path]:
    """One NLLOC_OBS file per event, named after the first pick time (YYYYmmddHHMMSSfff)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for eid in events["event_id"]:
        ep = assigned[assigned["event_id"] == eid]
        if ep.empty:
            continue
        t0 = pd.Timestamp(ep["time"].min()).tz_convert("UTC")
        path = folder / f"{t0:%Y%m%d%H%M%S}{t0.microsecond // 1000:03d}.nonlinloc"
        path.write_text("\n".join(obs_lines(ep)) + "\n")
        written.append(path)
    return written


def station_lines(stations: pd.DataFrame) -> list[str]:
    """GTSRCE lines: label LATLON lat lon depth(km, 0) elevation(km)."""
    return [
        f"GTSRCE {s.station:<6s} LATLON {s.latitude:9.5f} {s.longitude:9.5f} 0.0 {s.elevation_m / 1000.0:.3f}"
        for s in stations.itertuples()
    ]


def layer_lines(model_csv: str | Path, density: float = 2.7) -> list[str]:
    """LAYER lines: depth (km b.s.l.), Vp, dVp/dz, Vs, dVs/dz, density, gradient."""
    vm = read_velocity_model(model_csv)
    return [
        f"LAYER {r.depth_km:6.2f} {r.vp:5.2f} 0.00 {r.vs:5.2f} 0.00 {density:4.2f} 0.00"
        for r in vm.itertuples()
    ]


def control_file(
    centre: tuple[float, float],
    name: str = "seismoml",
    half_width_km: float = 30.0,
    max_depth_km: float = 40.0,
    top_km: float = -2.5,
    dx: float = 0.5,
    comment: str = "SeismoML quick-start export",
) -> str:
    """NonLinLoc control file for a local 1D problem centred on ``centre`` (lat, lon)."""
    lat0, lon0 = centre
    n_xy = int(round(2 * half_width_km / dx)) + 1
    n_z = int(round((max_depth_km - top_km) / dx)) + 1
    n_dist = int(round(2.5 * half_width_km / dx)) + 1  # covers the grid diagonal
    return f"""# NonLinLoc control file written by SeismoML ({comment})
# Run:  bash run_nlloc.sh      (needs Vel2Grid, Grid2Time and NLLoc on the PATH)
# Docs: http://alomax.free.fr/nlloc/

CONTROL 1 54321
TRANS SIMPLE {lat0:.5f} {lon0:.5f} 0.0

# ---------------- Vel2Grid: 1D model on a 2D grid (distance, depth) -------------
VGOUT ./model/{name}
VGTYPE P
VGTYPE S
VGGRID 2 {n_dist} {n_z} 0.0 0.0 {top_km:.2f} {dx} {dx} {dx} SLOW_LEN
INCLUDE model.txt

# ---------------- Grid2Time: travel times for every station ---------------------
GTFILES ./model/{name} ./time/{name} P
GTMODE GRID2D ANGLES_YES
INCLUDE stations.txt
GT_PLFD 1.0e-3 0

# ---------------- NLLoc: probabilistic location --------------------------------
LOCSIG {comment}
LOCCOM {comment}
LOCFILES ./obs/*.nonlinloc NLLOC_OBS ./time/{name} ./loc/{name}
LOCHYPOUT SAVE_NLLOC_ALL
LOCSEARCH OCT 10 10 4 0.01 20000 5000 0 1
LOCGRID {n_xy} {n_xy} {n_z} {-half_width_km:.1f} {-half_width_km:.1f} {top_km:.2f} {dx} {dx} {dx} PROB_DENSITY SAVE
LOCMETH EDT_OT_WT 9999.0 4 -1 -1 -1 -1 -1 1
LOCGAU 0.2 0.0
LOCGAU2 0.02 0.05 2.0
LOCPHASEID P P p Pg
LOCPHASEID S S s Sg
LOCQUAL2ERR 0.03 0.05 0.1 0.2 99999.9
LOCANGLES ANGLES_YES 5
"""


RUN_SCRIPT = """#!/usr/bin/env bash
# Relocate the exported events with NonLinLoc (Vel2Grid -> Grid2Time P, S -> NLLoc).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p model time loc
Vel2Grid nlloc.in
Grid2Time nlloc.in
sed 's|^GTFILES \\(.*\\) P$|GTFILES \\1 S|' nlloc.in > nlloc_S.in
Grid2Time nlloc_S.in
NLLoc nlloc.in
echo "Locations written to loc/ (one .hyp file per event)."
"""


def write_project(
    folder: str | Path,
    events: pd.DataFrame,
    assigned: pd.DataFrame,
    stations: pd.DataFrame,
    model_csv: str | Path,
    centre: tuple[float, float],
    max_depth_km: float = 40.0,
    top_km: float = -2.5,
) -> dict[str, Path]:
    """Write a complete NonLinLoc project for the catalogue (see module docstring)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    obs = write_obs(events, assigned, folder / "obs")
    (folder / "stations.txt").write_text("\n".join(station_lines(stations)) + "\n")
    (folder / "model.txt").write_text("\n".join(layer_lines(model_csv)) + "\n")
    (folder / "nlloc.in").write_text(control_file(centre, max_depth_km=max_depth_km, top_km=top_km))
    run = folder / "run_nlloc.sh"
    run.write_text(RUN_SCRIPT)
    run.chmod(0o755)
    return {"folder": folder, "n_obs": len(obs), "control": folder / "nlloc.in", "run": run}
