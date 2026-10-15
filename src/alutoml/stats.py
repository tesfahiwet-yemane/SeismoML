"""Catalogue statistics: frequency-magnitude distribution, Mc, b-value, clustering, PCA.

All functions are written from the original references:

* Aki (1965) and Utsu (1966): maximum-likelihood b-value with bin correction.
* Shi & Bolt (1982): standard error of b.
* Wiemer & Wyss (2000): maximum-curvature (MAXC) estimate of Mc.
* Cao & Gao (2002), Woessner & Wiemer (2005): b-value stability (MBS) estimate of Mc.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

LOG10E = np.log10(np.e)


def _bin(m, dm):
    """Round magnitudes to the bin grid (avoids floating point bin edges)."""
    return np.round(np.asarray(m, dtype=float) / dm) * dm


def fmd(mags, dm: float = 0.1) -> pd.DataFrame:
    """Non-cumulative and cumulative frequency-magnitude distribution."""
    m = _bin(mags[np.isfinite(mags)], dm)
    if m.size == 0:
        return pd.DataFrame(columns=["magnitude", "count", "cumulative"])
    centres = np.round(np.arange(m.min(), m.max() + dm / 2, dm), 6)
    counts = np.array([np.sum(np.isclose(m, c)) for c in centres])
    cumulative = counts[::-1].cumsum()[::-1]
    return pd.DataFrame({"magnitude": centres, "count": counts, "cumulative": cumulative})


def b_value_mle(mags, mc: float, dm: float = 0.1) -> tuple[float, float, float, int]:
    """Aki-Utsu maximum-likelihood b-value for magnitudes >= Mc.

    Returns ``(b, sigma_b, a, n)`` where ``sigma_b`` follows Shi & Bolt (1982)
    and ``a`` is the a-value such that log10 N(>=Mc) = a - b*Mc.
    """
    m = _bin(mags, dm)
    m = m[np.isfinite(m) & (m >= mc - dm / 2)]
    n = m.size
    if n < 2:
        return np.nan, np.nan, np.nan, n
    mean = m.mean()
    b = LOG10E / (mean - (mc - dm / 2))
    sigma = 2.3 * b**2 * np.sqrt(np.sum((m - mean) ** 2) / (n * (n - 1)))
    a = np.log10(n) + b * mc
    return float(b), float(sigma), float(a), int(n)


def mc_maxc(mags, dm: float = 0.1, correction: float = 0.0) -> float:
    """Magnitude of completeness from the maximum of the non-cumulative FMD.

    MAXC is known to underestimate Mc for gradually curved FMDs; a
    ``correction`` of +0.2 is common practice (Woessner & Wiemer, 2005).
    """
    f = fmd(np.asarray(mags), dm)
    if f.empty:
        return np.nan
    return float(f["magnitude"].iloc[int(np.argmax(f["count"]))] + correction)


def mc_mbs(
    mags, dm: float = 0.1, window: float = 0.5, min_events: int = 50
) -> tuple[float, pd.DataFrame]:
    """b-value stability method.

    For each trial Mc the b-value is compared with the average b over the next
    ``window`` magnitude units; Mc is the smallest trial for which the
    difference is below the Shi & Bolt uncertainty.
    """
    mags = np.asarray(mags, dtype=float)
    mags = mags[np.isfinite(mags)]
    m = _bin(mags, dm)
    trials = np.round(np.arange(m.min(), m.max() + dm / 2, dm), 6)
    rows = []
    for mc in trials:
        b, sb, _, n = b_value_mle(m, mc, dm)
        rows.append({"mc": mc, "b": b, "sigma_b": sb, "n": n})
    tab = pd.DataFrame(rows)
    nwin = int(round(window / dm))
    tab["b_avg"] = [
        tab["b"].iloc[i : i + nwin + 1].mean() if i + nwin < len(tab) else np.nan
        for i in range(len(tab))
    ]
    tab["stable"] = (
        (np.abs(tab["b_avg"] - tab["b"]) <= tab["sigma_b"]) & (tab["n"] >= min_events)
    )
    stable = tab.loc[tab["stable"], "mc"]
    mc = float(stable.iloc[0]) if len(stable) else np.nan
    return mc, tab


@dataclass
class BootstrapResult:
    mc: np.ndarray
    b: np.ndarray

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "mean": [np.nanmean(self.mc), np.nanmean(self.b)],
                "std": [np.nanstd(self.mc), np.nanstd(self.b)],
                "p05": [np.nanpercentile(self.mc, 5), np.nanpercentile(self.b, 5)],
                "p95": [np.nanpercentile(self.mc, 95), np.nanpercentile(self.b, 95)],
            },
            index=["Mc", "b"],
        )


def bootstrap_mc_b(
    mags, method: str = "maxc", n_boot: int = 500, dm: float = 0.1, seed: int = 42, **kwargs
) -> BootstrapResult:
    """Bootstrap the Mc and b-value estimates (resampling events with replacement)."""
    rng = np.random.default_rng(seed)
    mags = np.asarray(mags, dtype=float)
    mags = mags[np.isfinite(mags)]
    mcs, bs = np.full(n_boot, np.nan), np.full(n_boot, np.nan)
    for i in range(n_boot):
        sample = rng.choice(mags, size=mags.size, replace=True)
        if method == "maxc":
            mc = mc_maxc(sample, dm, **kwargs)
        elif method == "mbs":
            mc, _ = mc_mbs(sample, dm, **kwargs)
        else:
            raise ValueError("method must be 'maxc' or 'mbs'")
        mcs[i] = mc
        if np.isfinite(mc):
            bs[i] = b_value_mle(sample, mc, dm)[0]
    return BootstrapResult(mc=mcs, b=bs)


def synthetic_gr(n: int, b: float = 1.0, mc: float = 0.5, dm: float = 0.1, seed: int = 0):
    """Draw a Gutenberg-Richter catalogue (useful for testing and teaching)."""
    rng = np.random.default_rng(seed)
    beta = b / LOG10E
    m = (mc - dm / 2) + rng.exponential(1.0 / beta, n)
    return _bin(m, dm)


# --------------------------------------------------------------------------
# Spatial analysis
# --------------------------------------------------------------------------
def dbscan_labels(xyz: np.ndarray, eps_km: float = 1.0, min_samples: int = 5) -> np.ndarray:
    """DBSCAN cluster labels on hypocentres in km (label -1 = noise)."""
    from sklearn.cluster import DBSCAN

    return DBSCAN(eps=eps_km, min_samples=min_samples).fit_predict(np.asarray(xyz))


def k_distance(xyz: np.ndarray, k: int = 5) -> np.ndarray:
    """Sorted distance to the k-th nearest neighbour (to choose DBSCAN ``eps``)."""
    from sklearn.neighbors import NearestNeighbors

    nn = NearestNeighbors(n_neighbors=k + 1).fit(xyz)
    dist, _ = nn.kneighbors(xyz)
    return np.sort(dist[:, -1])


def knee_point(y: np.ndarray) -> int:
    """Index of the knee of a monotonically increasing curve.

    The point farthest from the straight line joining the first and last
    points (a simple form of the Kneedle algorithm; Satopaa et al., 2011).
    """
    y = np.asarray(y, dtype=float)
    x = np.linspace(0, 1, y.size)
    yn = (y - y.min()) / (np.ptp(y) or 1.0)
    return int(np.argmax(x - yn))


@dataclass
class PlaneFit:
    centroid: np.ndarray
    eigenvalues: np.ndarray  # descending
    eigenvectors: np.ndarray  # columns, matching eigenvalues
    strike: float
    dip: float
    planarity: float  # (l2 - l3) / l1
    linearity: float  # (l1 - l2) / l1


def hypocentre_pca(xyz: np.ndarray) -> PlaneFit:
    """Principal component analysis of a hypocentre cloud.

    ``xyz`` columns are easting, northing (km) and depth (km, positive down).
    The eigenvector with the smallest eigenvalue is the normal of the
    best-fitting plane, from which strike (right-hand rule) and dip are derived.
    """
    xyz = np.asarray(xyz, dtype=float)
    c = xyz.mean(axis=0)
    cov = np.cov((xyz - c).T)
    w, v = np.linalg.eigh(cov)
    order = np.argsort(w)[::-1]
    w, v = w[order], v[:, order]
    normal = v[:, 2].copy()
    if normal[2] < 0:  # point the normal downwards (z positive down)
        normal = -normal
    e, n, d = normal
    dip = np.degrees(np.arccos(np.clip(abs(d), 0, 1)))
    dip_dir = np.degrees(np.arctan2(-e, -n)) % 360  # direction the plane dips towards
    strike = (dip_dir - 90.0) % 360
    l1, l2, l3 = w
    return PlaneFit(
        centroid=c,
        eigenvalues=w,
        eigenvectors=v,
        strike=float(strike),
        dip=float(dip),
        planarity=float((l2 - l3) / l1) if l1 > 0 else np.nan,
        linearity=float((l1 - l2) / l1) if l1 > 0 else np.nan,
    )
