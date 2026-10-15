"""Phase association and preliminary location with PyOcto."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def read_velocity_model(path: str | Path) -> pd.DataFrame:
    """Read a layered model with columns ``depth_km, vp, vs`` (depth below sea level)."""
    df = pd.read_csv(path, comment="#")
    return df[["depth_km", "vp", "vs"]].astype(float).sort_values("depth_km")


def layered_to_pyocto(
    model: pd.DataFrame, datum_km: float, delta: float
) -> pd.DataFrame:
    """Convert a layer-over-halfspace model to PyOcto's piecewise-linear format.

    PyOcto interpolates linearly between consecutive rows, so each layer is
    represented by two nodes (top and just above the next interface) to keep
    the velocities constant within a layer. Depths are shifted so that 0 is
    the model datum (``datum_km`` above sea level).
    """
    rows = []
    d = model["depth_km"].to_numpy() + datum_km
    for i, (vp, vs) in enumerate(zip(model["vp"], model["vs"])):
        rows.append((d[i], vp, vs))
        if i + 1 < len(model):
            rows.append((d[i + 1] - delta, vp, vs))
    out = pd.DataFrame(rows, columns=["depth", "vp", "vs"])
    if out["depth"].iloc[0] < 0:
        raise ValueError("datum_km must be at or above the top of the velocity model")
    return out


def surface_velocities(model_csv: str | Path) -> tuple[float, float]:
    """P and S velocity of the top layer (used for PyOcto's station-elevation correction)."""
    vm = read_velocity_model(model_csv)
    return float(vm["vp"].iloc[0]), float(vm["vs"].iloc[0])


def build_travel_time_table(
    model_csv: str | Path,
    datum_km: float,
    cache_dir: str | Path,
    xdist_km: float = 60.0,
    zdist_km: float = 45.0,
    delta_km: float = 0.1,
) -> Path:
    """Pre-compute the 1D travel-time table (needs ``pyrocko``).

    The table is cached in ``cache_dir`` under a name that encodes the model
    and all grid parameters, so changing any of them builds a new table.
    """
    import hashlib

    import pyocto

    vm = read_velocity_model(model_csv)
    key = hashlib.sha1(
        (vm.to_csv(index=False) + f"{datum_km}|{xdist_km}|{zdist_km}|{delta_km}").encode()
    ).hexdigest()[:10]
    out_path = Path(cache_dir) / f"pyocto_1d_{key}.bin"
    if out_path.exists():
        return out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model = layered_to_pyocto(vm, datum_km, delta_km)
    pyocto.VelocityModel1D.create_model(model, delta_km, xdist_km, zdist_km, out_path)
    return out_path


def make_associator(
    lat: tuple[float, float],
    lon: tuple[float, float],
    depth_bsl_km: tuple[float, float],
    datum_km: float,
    table_path: str | Path,
    surface_vp: float,
    surface_vs: float,
    tolerance: float = 1.0,
    cutoff_km: float = 30.0,
    **kwargs,
):
    """Create an ``OctoAssociator`` for a lat/lon box.

    ``depth_bsl_km`` is given below sea level and converted to the datum used by
    the travel-time table. PyOcto computes travel times with the receiver at the
    datum and then subtracts ``(station depth below datum) / surface velocity``;
    ``surface_vp`` / ``surface_vs`` must therefore be the velocities of the
    layer between the datum and the stations (the top layer of the model).
    Remaining keyword arguments are passed to PyOcto (e.g. ``n_picks``).
    """
    import pyocto

    vel = pyocto.VelocityModel1D(
        str(table_path),
        tolerance=tolerance,
        association_cutoff_distance=cutoff_km,
        surface_p_velocity=surface_vp,
        surface_s_velocity=surface_vs,
    )
    zlim = (depth_bsl_km[0] + datum_km, depth_bsl_km[1] + datum_km)
    params = dict(time_before=30.0, n_picks=6, n_p_picks=3, n_s_picks=2, n_p_and_s_picks=2)
    params.update(kwargs)
    return pyocto.OctoAssociator.from_area(
        lat=lat, lon=lon, zlim=zlim, velocity_model=vel, **params
    )


def stations_frame(stations: pd.DataFrame, associator, datum_km: float) -> pd.DataFrame:
    """Station table in PyOcto format (``id`` must match SeisBench ``trace_id``).

    Elevations are expressed relative to the model datum, so PyOcto's ``z``
    is the station depth below the datum (positive down).
    """
    df = pd.DataFrame(
        {
            "id": stations["network"] + "." + stations["station"] + ".",
            "latitude": stations["latitude"].astype(float),
            "longitude": stations["longitude"].astype(float),
            "elevation": stations["elevation_m"].astype(float) - datum_km * 1000.0,
        }
    )
    return associator.transform_stations(df)


def associate(
    picks: pd.DataFrame, stations: pd.DataFrame, associator, datum_km: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Associate a pick table (from :func:`alutoml.picking.picks_to_frame`).

    Returns
    -------
    events
        One row per event: ``event_id, time, latitude, longitude, depth_km`` (below
        sea level), ``x, y, z`` (local km) and the number of P/S picks.
    assignments
        The input picks that were associated, with ``event_id`` and travel-time residual.
    """
    if picks.empty:
        return _empty_events(), picks.assign(event_id=pd.Series(dtype=int))
    p = pd.DataFrame(
        {
            "station": picks["trace_id"],
            "time": picks["time"].map(lambda t: t.timestamp()),
            "phase": picks["phase"],
            "probability": picks["probability"],
        }
    )
    events, assign = associator.associate(p, stations)
    if events.empty:
        return _empty_events(), picks.iloc[:0].assign(event_id=pd.Series(dtype=int))
    associator.transform_events(events)
    events = events.rename(columns={"idx": "event_id"})
    events["time"] = pd.to_datetime(events["time"], unit="s", utc=True)
    events["depth_km"] = events["z"] - datum_km

    assign = assign.rename(columns={"event_idx": "event_id"})
    picked = picks.iloc[assign["pick_idx"].to_numpy()].copy()
    picked["event_id"] = assign["event_id"].to_numpy()
    if "residual" in assign:
        picked["tt_residual"] = assign["residual"].to_numpy()
    counts = picked.groupby(["event_id", "phase"]).size().unstack(fill_value=0)
    events["n_P"] = events["event_id"].map(counts.get("P", pd.Series(dtype=int))).fillna(0).astype(int)
    events["n_S"] = events["event_id"].map(counts.get("S", pd.Series(dtype=int))).fillna(0).astype(int)
    cols = ["event_id", "time", "latitude", "longitude", "depth_km", "x", "y", "z", "n_P", "n_S"]
    return events[cols].reset_index(drop=True), picked.reset_index(drop=True)


def _empty_events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": pd.Series(dtype=int),
            "time": pd.Series(dtype="datetime64[ns, UTC]"),
            "latitude": pd.Series(dtype=float),
            "longitude": pd.Series(dtype=float),
            "depth_km": pd.Series(dtype=float),
            "x": pd.Series(dtype=float),
            "y": pd.Series(dtype=float),
            "z": pd.Series(dtype=float),
            "n_P": pd.Series(dtype=int),
            "n_S": pd.Series(dtype=int),
        }
    )


def predicted_travel_times(
    event: pd.Series, stations: pd.DataFrame, vp: float = 4.6, vs: float = 2.6
) -> pd.DataFrame:
    """Straight-ray travel times in a homogeneous medium (for quick plotting only)."""
    dx = stations["x"] - event["x"]
    dy = stations["y"] - event["y"]
    dz = stations["z"] - event["z"]
    r = np.sqrt(dx**2 + dy**2 + dz**2)
    return pd.DataFrame({"id": stations["id"], "dist_km": r, "tP": r / vp, "tS": r / vs})
