"""Fast unit tests for the workshop helper package (no network, no model weights)."""

import numpy as np
import pandas as pd
import pytest
from obspy import Stream, Trace, UTCDateTime

from seismoml import association, catalogue, data, magnitude, picking, stats
from seismoml.config import load_config


@pytest.fixture(scope="module")
def cfg():
    return load_config()


def test_config(cfg):
    assert cfg.network == "XM"
    assert cfg.demo_station in cfg.stations
    assert cfg.t1 - cfg.t0 == 86400
    assert cfg.velocity_model_file.exists()


def test_station_table_matches_config(cfg):
    table = data.station_table(cfg.path("stations"))
    active = data.active_stations(table, cfg.day)
    assert sorted(active["station"]) == sorted(cfg.stations)


def test_sds_roundtrip(tmp_path):
    t0 = UTCDateTime("2012-11-15T23:59:00")
    tr = Trace(np.arange(12000, dtype=np.int32), header={
        "network": "XM", "station": "TEST", "location": "", "channel": "HHZ",
        "sampling_rate": 100.0, "starttime": t0})
    paths = data.write_sds(Stream([tr]), tmp_path)
    assert len(paths) == 2  # split across midnight
    st = data.load_waveforms(tmp_path, "XM", "TEST", t0, t0 + 120)
    assert sum(t.stats.npts for t in st) == 12000


def _picks(times, station="A01E", phase="P", prob=0.9):
    return pd.DataFrame({
        "trace_id": f"XM.{station}.",
        "station": station,
        "phase": phase,
        "time": pd.to_datetime(times, utc=True, format="ISO8601"),
        "probability": prob,
    })


def test_match_picks_one_to_one():
    ref = _picks(["2012-11-15T00:00:10", "2012-11-15T00:00:20"])
    cand = _picks(["2012-11-15T00:00:10.1", "2012-11-15T00:00:10.2", "2012-11-15T00:00:30"])
    m = picking.match_picks(ref, cand, tolerance=0.5)
    assert len(m) == 1
    assert m["residual"].iloc[0] == pytest.approx(0.1, abs=1e-6)
    s = picking.detection_scores(ref, cand, tolerance=0.5)
    assert s.loc["P", "recall"] == 0.5
    assert s.loc["P", "precision"] == pytest.approx(1 / 3)


def test_b_value_recovers_truth():
    m = stats.synthetic_gr(20000, b=1.2, mc=0.5)
    b, sb, a, n = stats.b_value_mle(m, 0.5)
    assert b == pytest.approx(1.2, abs=3 * sb + 0.02)
    assert n == 20000


def test_mc_estimates_on_truncated_catalogue():
    rng = np.random.default_rng(1)
    full = stats.synthetic_gr(30000, b=1.0, mc=-0.5, seed=3)
    # incomplete below M 0.8: keep only a fraction of the small events
    keep = (full >= 0.8) | (rng.random(full.size) < np.clip((full + 0.5) / 1.3, 0, 1) ** 4)
    m = full[keep]
    assert stats.mc_maxc(m) == pytest.approx(0.8, abs=0.31)
    mc, tab = stats.mc_mbs(m)
    assert 0.4 <= mc <= 1.4


def test_pca_recovers_plane():
    rng = np.random.default_rng(0)
    # plane striking N-S (strike 0) and dipping 60 deg to the east
    u = rng.uniform(-2, 2, 2000)  # along strike (north)
    v = rng.uniform(0, 3, 2000)   # down dip
    dip = np.radians(60)
    xyz = np.c_[v * np.cos(dip), u, v * np.sin(dip)] + rng.normal(0, 0.02, (2000, 3))
    fit = stats.hypocentre_pca(xyz)
    assert fit.dip == pytest.approx(60, abs=2)
    assert min(abs(fit.strike - 0), abs(fit.strike - 360)) < 2


def test_keir_magnitude_reference_point():
    # At r = 17 km, A = 1 mm gives ML = 2.0 by construction.
    assert magnitude.ml_keir2006(1.0, 17.0) == pytest.approx(2.0)


def test_wood_anderson_response():
    """Static magnification 2800, natural period 0.8 s, damping 0.8."""
    from obspy.signal.invsim import paz_to_freq_resp

    wa = magnitude.WOOD_ANDERSON
    # displacement response = velocity response x i*omega; high-frequency gain -> 2800
    h, f = paz_to_freq_resp(wa["poles"], wa["zeros"] + [0j], wa["sensitivity"], 0.01, 2**16, freq=True)
    assert abs(h[-1]) == pytest.approx(2800, rel=1e-3)
    assert abs(wa["poles"][0]) == pytest.approx(2 * np.pi / 0.8)


def test_match_events_without_matches():
    a = pd.DataFrame({"event_id": [0], "time": pd.to_datetime(["2012-11-15T01:00:00"], utc=True),
                      "latitude": [7.8], "longitude": [38.8], "depth_km": [2.0]})
    b = a.assign(time=a["time"] + pd.Timedelta(seconds=60))
    m = catalogue.match_events(a, b)
    assert m.empty and "dt_s" in m.columns


def test_layered_model_conversion(cfg):
    vm = association.read_velocity_model(cfg.velocity_model_file)
    pm = association.layered_to_pyocto(vm, cfg.datum_km, 0.1)
    assert pm["depth"].iloc[0] == pytest.approx(0.0)
    assert pm["depth"].is_monotonic_increasing


def test_association_on_synthetic_picks(cfg, tmp_path):
    """PyOcto must recover a synthetic event generated with the same 1D model."""
    table = association.build_travel_time_table(
        cfg.velocity_model_file, cfg.datum_km, tmp_path,
        xdist_km=60, zdist_km=45, delta_km=0.2)
    vp0, vs0 = association.surface_velocities(cfg.velocity_model_file)
    assoc = association.make_associator(
        cfg.lat_range, cfg.lon_range, cfg.depth_range, cfg.datum_km, table, vp0, vs0,
        tolerance=0.3)
    st = data.active_stations(data.station_table(cfg.path("stations")), cfg.day)
    sdf = association.stations_frame(st, assoc, cfg.datum_km)

    tables = _read_table(table)
    # event 3 km below sea level under the caldera centre
    ev = pd.DataFrame({"latitude": [7.79], "longitude": [38.79]})
    ev = assoc.transform_stations(ev)
    ex, ey, ez = ev["x"].iloc[0], ev["y"].iloc[0], 3.0 + cfg.datum_km
    t0 = pd.Timestamp("2012-11-15T12:00:00", tz="UTC")
    rows = []
    for _, s in sdf.iterrows():
        for ph in "PS":
            # PyOcto convention: receiver at the datum, minus a vertical
            # correction through the top layer down to the station
            tt = _travel_time(tables, s, ex, ey, ez, ph) - s["z"] / (vp0 if ph == "P" else vs0)
            rows.append({"trace_id": s["id"], "station": s["id"].split(".")[1], "phase": ph,
                         "time": t0 + pd.Timedelta(seconds=tt), "probability": 0.9})
    picks = pd.DataFrame(rows)
    events, assigned = association.associate(picks, sdf, assoc, cfg.datum_km)
    assert len(events) == 1
    e = events.iloc[0]
    assert abs((e["time"] - t0).total_seconds()) < 0.3
    assert abs(e["depth_km"] - 3.0) < 0.5
    assert len(assigned) >= 0.8 * len(picks)


def _read_table(path):
    """Read PyOcto's binary 1D travel-time table (header: nx, nz, delta)."""
    import struct

    raw = open(path, "rb").read()
    nx, nz, delta = struct.unpack("iid", raw[:16])
    arr = np.frombuffer(raw[16:], dtype=np.float64).reshape(2, nx, nz)
    return {"P": arr[0], "S": arr[1], "delta": delta}


def _travel_time(tables, station, x, y, z, phase):
    """Bilinear lookup at (horizontal distance, source depth below the datum)."""
    from scipy.interpolate import RegularGridInterpolator

    t = tables[phase]
    d = tables["delta"]
    grid = (np.arange(t.shape[0]) * d, np.arange(t.shape[1]) * d)
    r = np.hypot(station["x"] - x, station["y"] - y)
    return float(RegularGridInterpolator(grid, t)([r, z])[0])


def test_knee_point():
    y = np.r_[np.linspace(0, 1, 80), np.linspace(1.5, 10, 20)]
    assert 75 <= stats.knee_point(y) <= 82


def test_empty_pick_tables_keep_datetime(tmp_path):
    empty = picking.picks_to_frame([])
    assert str(empty["time"].dtype).startswith("datetime64")
    full = _picks(["2012-11-15T00:00:10"])
    both = pd.concat([empty, full], ignore_index=True)
    picking.save_picks(both, tmp_path / "p.csv")
    picking.save_picks(empty, tmp_path / "e.csv")
    assert len(picking.read_picks(tmp_path / "p.csv")) == 1


def test_nonlinloc_export(cfg, tmp_path):
    from seismoml import nonlinloc

    ev = pd.DataFrame({"event_id": [0], "time": pd.to_datetime(["2012-11-15T03:00:00"], utc=True)})
    asg = _picks(["2012-11-15T03:00:01.2345", "2012-11-15T03:00:02.5"], station="A10E")
    asg["phase"] = ["P", "S"]
    asg["probability"] = [1.0, 0.0]
    asg["event_id"] = 0
    st = data.active_stations(data.station_table(cfg.path("stations")), cfg.day)
    out = nonlinloc.write_project(tmp_path, ev, asg, st, cfg.velocity_model_file, cfg.centre)
    obs = sorted((tmp_path / "obs").glob("*.nonlinloc"))
    assert out["n_obs"] == 1 and obs[0].name == "20121115030001234.nonlinloc"
    p_line, s_line = obs[0].read_text().splitlines()
    f = p_line.split()
    assert f[0] == "A10E" and f[4] == "P" and f[6] == "20121115" and f[7] == "0300"
    assert float(f[8]) == pytest.approx(1.2345) and float(f[10]) == pytest.approx(0.03)
    assert float(s_line.split()[10]) == pytest.approx(0.20)
    assert len((tmp_path / "stations.txt").read_text().splitlines()) == len(st)
    ctrl = (tmp_path / "nlloc.in").read_text()
    for key in ("TRANS SIMPLE", "VGGRID", "GTFILES", "LOCFILES", "LOCGRID", "INCLUDE model.txt"):
        assert key in ctrl
