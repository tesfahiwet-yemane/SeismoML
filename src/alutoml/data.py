"""Waveform and metadata access: FDSN download, SDS archive, station tables."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from obspy import Inventory, Stream, UTCDateTime, read, read_inventory
from obspy.clients.filesystem.sds import Client as SDSClient

log = logging.getLogger(__name__)

SDS_PATTERN = "{year}/{net}/{sta}/{cha}.D/{net}.{sta}.{loc}.{cha}.D.{year}.{jday:03d}"


# --------------------------------------------------------------------------
# Station metadata
# --------------------------------------------------------------------------
def station_table(path: str | Path) -> pd.DataFrame:
    """Read the ARGOS deployment table (one row per station epoch)."""
    df = pd.read_csv(path, parse_dates=["start", "end"])
    return df


def active_stations(table: pd.DataFrame, day: UTCDateTime) -> pd.DataFrame:
    """Stations whose deployment epoch covers the whole of ``day``."""
    d0 = pd.Timestamp(day.datetime)
    d1 = d0 + pd.Timedelta(days=1)
    mask = (table["start"] <= d0) & (table["end"] >= d1)
    return table.loc[mask].drop_duplicates("station").reset_index(drop=True)


def inventory_table(inventory: Inventory) -> pd.DataFrame:
    """Flatten an ObsPy inventory into one row per station."""
    rows = []
    for net in inventory:
        for sta in net:
            rows.append(
                {
                    "network": net.code,
                    "station": sta.code,
                    "latitude": sta.latitude,
                    "longitude": sta.longitude,
                    "elevation_m": sta.elevation,
                    "site": sta.site.name if sta.site else "",
                    "n_channels": len(sta.channels),
                    "start": sta.start_date,
                    "end": sta.end_date,
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# FDSN download
# --------------------------------------------------------------------------
def fdsn_client(provider: str = "IRIS", timeout: int = 120):
    """Return an ObsPy FDSN client (imported lazily so offline use stays fast)."""
    from obspy.clients.fdsn import Client

    return Client(provider, timeout=timeout)


def download_inventory(
    client,
    network: str,
    stations: list[str],
    t0: UTCDateTime,
    t1: UTCDateTime,
    channels: str = "HH?",
    level: str = "response",
) -> Inventory:
    """Fetch StationXML for the given stations and time window."""
    return client.get_stations(
        network=network,
        station=",".join(stations),
        channel=channels,
        starttime=t0,
        endtime=t1,
        level=level,
    )


def download_waveforms(
    client,
    network: str,
    station: str,
    t0: UTCDateTime,
    t1: UTCDateTime,
    channels: str = "HH?",
    location: str = "",
    chunk: float = 6 * 3600,
) -> Stream:
    """Download one station in chunks (robust against time-outs on long requests)."""
    st = Stream()
    loc = location if location else "--"
    start = t0
    while start < t1:
        end = min(start + chunk, t1)
        try:
            st += client.get_waveforms(network, station, loc, channels, start, end)
        except Exception as exc:  # noqa: BLE001 - FDSN raises many types
            log.warning("No data for %s.%s %s-%s: %s", network, station, start, end, exc)
        start = end
    st.merge(method=1)
    return st


# --------------------------------------------------------------------------
# SDS archive
# --------------------------------------------------------------------------
def sds_path(root: str | Path, tr_id: str, t: UTCDateTime) -> Path:
    net, sta, loc, cha = tr_id.split(".")
    rel = SDS_PATTERN.format(
        year=t.year, net=net, sta=sta, loc=loc, cha=cha, jday=t.julday
    )
    return Path(root) / rel


def write_sds(stream: Stream, root: str | Path, encoding: str = "STEIM2") -> list[Path]:
    """Write a stream into an SDS archive, splitting at UTC day boundaries.

    Existing day files are merged with the new data rather than overwritten.
    """
    written = []
    for tr in stream.copy().split():
        t = UTCDateTime(tr.stats.starttime.date)
        while t < tr.stats.endtime:
            # every sample before midnight (sample times need not be on whole 1/100 s)
            piece = tr.slice(t, t + 86400 - 1e-6, nearest_sample=False)
            t += 86400
            if piece.stats.npts == 0:
                continue
            path = sds_path(root, piece.id, piece.stats.starttime)
            path.parent.mkdir(parents=True, exist_ok=True)
            day = Stream([piece])
            if path.exists():
                day += read(str(path))
                day.merge(method=1)
                day = day.split()
            for t_ in day:
                if t_.data.dtype != np.int32:
                    t_.data = np.round(t_.data).astype(np.int32)
            day.write(str(path), format="MSEED", encoding=encoding)
            written.append(path)
    return sorted(set(written))


def sds_client(root: str | Path) -> SDSClient:
    return SDSClient(str(root))


def load_waveforms(
    root: str | Path,
    network: str,
    stations: list[str] | str,
    t0: UTCDateTime,
    t1: UTCDateTime,
    channels: str = "HH?",
    location: str = "*",
) -> Stream:
    """Read waveforms from the SDS archive.

    Gaps are *not* zero-filled: the stream is split at gaps so that SeisBench
    processes each continuous segment separately and no artificial steps are
    introduced.
    """
    client = sds_client(root)
    if isinstance(stations, str):
        stations = [stations]
    st = Stream()
    for sta in stations:
        st += client.get_waveforms(network, sta, location, channels, t0, t1)
    if len(st) == 0:
        raise FileNotFoundError(
            f"No waveforms for {network}.{stations} between {t0} and {t1} in {root}. "
            "Run `python scripts/fetch_data.py` (or notebook 00) first."
        )
    st.merge(method=1)
    st = st.split()
    st.sort(keys=["network", "station", "channel", "starttime"])
    return st


def availability(stream: Stream, t0: UTCDateTime, t1: UTCDateTime) -> pd.DataFrame:
    """Fraction of the window covered by data, per channel."""
    span = t1 - t0
    rows = {}
    for tr in stream:
        s = max(tr.stats.starttime, t0)
        e = min(tr.stats.endtime, t1)
        rows.setdefault(tr.id, 0.0)
        rows[tr.id] += max(0.0, e - s)
    df = pd.DataFrame(
        {"trace_id": list(rows), "coverage": [v / span for v in rows.values()]}
    )
    df[["network", "station", "location", "channel"]] = df["trace_id"].str.split(
        ".", expand=True
    )
    return df


def load_inventory(path: str | Path) -> Inventory:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python scripts/fetch_data.py` (or notebook 00) first."
        )
    return read_inventory(str(path))
