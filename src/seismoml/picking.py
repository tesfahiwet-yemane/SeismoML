"""Helpers around SeisBench pickers: running models, tabulating and comparing picks."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

PICK_COLUMNS = ["trace_id", "station", "phase", "time", "probability"]


@dataclass(frozen=True)
class ModelSpec:
    """A SeisBench architecture + pretrained weight name."""

    architecture: str  # e.g. "PhaseNet" or "EQTransformer"
    weights: str  # e.g. "volpick", "instance", "original"

    @property
    def label(self) -> str:
        short = {"PhaseNet": "PN", "EQTransformer": "EQT"}.get(
            self.architecture, self.architecture
        )
        return f"{short}-{self.weights}"

    def load(self):
        """Instantiate the model with pretrained weights (downloads on first use)."""
        import seisbench.models as sbm

        cls = getattr(sbm, self.architecture)
        model = cls.from_pretrained(self.weights)
        model.eval()
        return model


def default_inference_args(model) -> dict:
    """Overlap/blinding settings that suit the model's window length.

    A 50 % overlap with ``avg`` stacking, and blinding of the outermost 5 % of
    every window (where predictions are least reliable).
    """
    n = model.in_samples
    return {
        "overlap": n // 2,
        "blinding": (n // 20, n // 20),
        "stacking": "avg",
    }


def picks_to_frame(picks) -> pd.DataFrame:
    """Convert a SeisBench ``PickList`` to a tidy DataFrame (times as UTC Timestamps)."""
    rows = [
        {
            "trace_id": p.trace_id,
            "station": p.trace_id.split(".")[1],
            "phase": p.phase,
            "time": pd.Timestamp(p.peak_time.datetime, tz="UTC"),
            "probability": float(p.peak_value),
        }
        for p in picks
    ]
    df = pd.DataFrame(rows, columns=PICK_COLUMNS)
    # keep a datetime dtype even when there are no picks, so empty and full tables combine
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["probability"] = df["probability"].astype(float)
    return df.sort_values(["time", "station"]).reset_index(drop=True)


def run_picker(model, stream, threshold: float | dict = 0.3, **kwargs) -> pd.DataFrame:
    """Run ``model.classify`` and return the picks as a DataFrame.

    ``threshold`` may be a single value or ``{"P": .., "S": ..}``.
    The wall-clock runtime is stored in ``df.attrs["runtime_s"]``.
    """
    if not isinstance(threshold, dict):
        threshold = {"P": threshold, "S": threshold}
    args = default_inference_args(model) | kwargs
    for phase, value in threshold.items():
        args[f"{phase}_threshold"] = value
    tic = time.perf_counter()
    out = model.classify(stream, **args)
    df = picks_to_frame(out.picks)
    df.attrs["runtime_s"] = time.perf_counter() - tic
    return df


def match_picks(
    reference: pd.DataFrame,
    candidate: pd.DataFrame,
    tolerance: float = 0.5,
) -> pd.DataFrame:
    """One-to-one matching of two pick tables (same station and phase).

    Candidate pairs within ``tolerance`` are found with a sorted search (memory
    scales with the number of nearby pairs, not with the product of table
    sizes). Pairs are then accepted greedily from the smallest absolute time
    difference upwards, so each pick is used at most once.

    Returns one row per matched pair with ``residual`` = candidate - reference (s).
    """
    cols = [
        "station", "phase", "time_ref", "time_cand", "residual",
        "prob_ref", "prob_cand", "ref_index", "cand_index",
    ]
    out = []
    cand_groups = dict(tuple(candidate.groupby(["station", "phase"])))
    for key, ref in reference.groupby(["station", "phase"]):
        cand = cand_groups.get(key)
        if cand is None or cand.empty:
            continue
        tr = _seconds(ref["time"])
        tc = _seconds(cand["time"])
        oc = np.argsort(tc, kind="stable")
        tcs = tc[oc]
        lo = np.searchsorted(tcs, tr - tolerance, side="left")
        hi = np.searchsorted(tcs, tr + tolerance, side="right")
        counts = hi - lo
        if counts.sum() == 0:
            continue
        i = np.repeat(np.arange(tr.size), counts)
        j = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts) + np.repeat(lo, counts)
        diff = tcs[j] - tr[i]
        used_r, used_c = set(), set()
        for k in np.argsort(np.abs(diff), kind="stable"):
            a, b = int(i[k]), int(oc[j[k]])
            if a in used_r or b in used_c:
                continue
            used_r.add(a)
            used_c.add(b)
            out.append(
                {
                    "station": key[0],
                    "phase": key[1],
                    "time_ref": ref["time"].iloc[a],
                    "time_cand": cand["time"].iloc[b],
                    "residual": float(diff[k]),
                    "prob_ref": ref["probability"].iloc[a] if "probability" in ref else np.nan,
                    "prob_cand": cand["probability"].iloc[b],
                    "ref_index": ref.index[a],
                    "cand_index": cand.index[b],
                }
            )
    return pd.DataFrame(out, columns=cols)


def _seconds(times: pd.Series) -> np.ndarray:
    """UTC timestamps -> float seconds since the epoch."""
    return times.to_numpy(dtype="datetime64[ns]").astype("int64") / 1e9


def detection_scores(
    reference: pd.DataFrame, candidate: pd.DataFrame, tolerance: float = 0.5
) -> pd.DataFrame:
    """Recall / precision / F1 of ``candidate`` against ``reference``, per phase."""
    m = match_picks(reference, candidate, tolerance)
    rows = []
    for ph in ("P", "S"):
        n_ref = int((reference["phase"] == ph).sum())
        n_cand = int((candidate["phase"] == ph).sum())
        n_tp = int((m["phase"] == ph).sum())
        recall = n_tp / n_ref if n_ref else np.nan
        precision = n_tp / n_cand if n_cand else np.nan
        f1 = (
            2 * recall * precision / (recall + precision)
            if n_tp and recall + precision > 0
            else 0.0
        )
        res = m.loc[m["phase"] == ph, "residual"]
        rows.append(
            {
                "phase": ph,
                "n_reference": n_ref,
                "n_candidate": n_cand,
                "matched": n_tp,
                "recall": recall,
                "precision": precision,
                "F1": f1,
                "median_residual_s": res.median() if n_tp else np.nan,
                "MAD_residual_s": (res - res.median()).abs().median() if n_tp else np.nan,
            }
        )
    return pd.DataFrame(rows).set_index("phase")


def agreement_matrix(
    tables: dict[str, pd.DataFrame], phase: str = "P", tolerance: float = 0.5
) -> pd.DataFrame:
    """Fraction of picks of model *row* that are also found by model *column*."""
    names = list(tables)
    mat = pd.DataFrame(index=names, columns=names, dtype=float)
    for a in names:
        ta = tables[a][tables[a]["phase"] == phase]
        for b in names:
            tb = tables[b][tables[b]["phase"] == phase]
            if len(ta) == 0:
                mat.loc[a, b] = np.nan
                continue
            mat.loc[a, b] = len(match_picks(ta, tb, tolerance)) / len(ta)
    return mat


def threshold_curve(
    picks: pd.DataFrame, thresholds=np.arange(0.05, 0.95, 0.05)
) -> pd.DataFrame:
    """Number of picks per phase that survive each probability threshold."""
    rows = []
    for t in thresholds:
        sel = picks[picks["probability"] >= t]
        rows.append(
            {
                "threshold": round(float(t), 3),
                "P": int((sel["phase"] == "P").sum()),
                "S": int((sel["phase"] == "S").sum()),
            }
        )
    return pd.DataFrame(rows)


def save_picks(df: pd.DataFrame, path) -> None:
    out = df.copy()
    out["time"] = pd.to_datetime(out["time"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    out.to_csv(path, index=False)


def read_picks(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["time"], utc=True, format="ISO8601")
    return df


# --------------------------------------------------------------------------
# Classic (non-ML) tools used as a baseline and to locate demo events
# --------------------------------------------------------------------------
def strip_model_prefix(stream):
    """Rename e.g. ``DeepDenoiser_HHZ`` back to ``HHZ`` so the output can be re-picked."""
    st = stream.copy()
    for tr in st:
        tr.stats.channel = tr.stats.channel.split("_")[-1]
    return st


def sta_lta_triggers(
    data, sta: float = 0.5, lta: float = 10.0, on: float = 5.0, off: float = 1.5,
    freqmin: float = 2.0, freqmax: float = 20.0,
) -> pd.DataFrame:
    """Recursive STA/LTA triggers on a vertical component, strongest first.

    ``data`` is a Trace or a Stream of gap-split segments. Each continuous
    segment is processed separately and the first LTA window of every segment
    is blanked, so gaps cannot produce spurious triggers.
    """
    from obspy import Stream
    from obspy.signal.trigger import recursive_sta_lta, trigger_onset

    segments = data if isinstance(data, Stream) else [data]
    rows = []
    for seg in segments:
        fs = seg.stats.sampling_rate
        if seg.stats.npts < 3 * lta * fs:
            continue
        tr = seg.copy().detrend("demean").taper(0.01)
        tr.filter("bandpass", freqmin=freqmin, freqmax=freqmax, corners=4, zerophase=True)
        cft = recursive_sta_lta(tr.data.astype(float), int(sta * fs), int(lta * fs))
        cft[: int(lta * fs)] = 0  # LTA warm-up
        for i0, i1 in trigger_onset(cft, on, off):
            rows.append(
                {
                    "onset": pd.Timestamp((tr.stats.starttime + i0 / fs).datetime, tz="UTC"),
                    "duration_s": (i1 - i0) / fs,
                    "peak_ratio": float(cft[i0 : i1 + 1].max()),
                }
            )
    df = pd.DataFrame(rows, columns=["onset", "duration_s", "peak_ratio"])
    return df.sort_values("peak_ratio", ascending=False).reset_index(drop=True)


def snr_db(trace, onset, noise=(-6.0, -1.0), signal=(0.0, 5.0)) -> float:
    """RMS signal-to-noise ratio (dB) around an onset time (``obspy.UTCDateTime``)."""
    n = trace.slice(onset + noise[0], onset + noise[1]).data.astype(float)
    s = trace.slice(onset + signal[0], onset + signal[1]).data.astype(float)
    if n.size == 0 or s.size == 0:
        return np.nan
    n = n - n.mean()
    s = s - s.mean()
    return float(20 * np.log10(np.sqrt(np.mean(s**2)) / max(np.sqrt(np.mean(n**2)), 1e-20)))
