"""Workshop configuration: one YAML file drives every notebook and script."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from obspy import UTCDateTime

CONFIG_NAME = "workshop.yml"


def find_root(start: str | Path | None = None) -> Path:
    """Return the repository root (the first parent directory holding ``workshop.yml``)."""
    here = Path(start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / CONFIG_NAME).is_file():
            return candidate
    raise FileNotFoundError(
        f"Could not find {CONFIG_NAME} above {here}. "
        "Run the notebooks from inside the workshop repository."
    )


@dataclass
class Config:
    """Typed view of ``workshop.yml`` with all paths resolved against the repo root."""

    root: Path
    raw: dict[str, Any] = field(repr=False)

    # --- simple accessors -------------------------------------------------
    @property
    def network(self) -> str:
        return self.raw["network"]

    @property
    def channels(self) -> str:
        return self.raw["channels"]

    @property
    def location(self) -> str:
        return self.raw.get("location", "")

    @property
    def provider(self) -> str:
        return self.raw.get("fdsn_provider", "IRIS")

    @property
    def stations(self) -> list[str]:
        return list(self.raw["stations"])

    @property
    def demo_station(self) -> str:
        return self.raw["demo_station"]

    @property
    def day(self) -> UTCDateTime:
        return UTCDateTime(self.raw["day"])

    @property
    def t0(self) -> UTCDateTime:
        return self.day

    @property
    def t1(self) -> UTCDateTime:
        return self.day + 86400

    @property
    def lat_range(self) -> tuple[float, float]:
        return tuple(self.raw["region"]["lat"])

    @property
    def lon_range(self) -> tuple[float, float]:
        return tuple(self.raw["region"]["lon"])

    @property
    def depth_range(self) -> tuple[float, float]:
        return tuple(self.raw["region"]["depth_km"])

    @property
    def centre(self) -> tuple[float, float]:
        c = self.raw["centre"]
        return c["lat"], c["lon"]

    @property
    def utm_epsg(self) -> int:
        return int(self.raw["utm_epsg"])

    @property
    def velocity_model_file(self) -> Path:
        return self.root / self.raw["velocity_model"]["file"]

    @property
    def datum_km(self) -> float:
        return float(self.raw["velocity_model"]["datum_km"])

    # --- paths ------------------------------------------------------------
    def path(self, key: str) -> Path:
        """Absolute path for an entry of the ``paths`` section."""
        return self.root / self.raw["paths"][key]

    @property
    def sds(self) -> Path:
        return self.path("sds")

    @property
    def inventory_file(self) -> Path:
        return self.path("inventory")

    @property
    def outputs(self) -> Path:
        out = self.path("outputs")
        out.mkdir(parents=True, exist_ok=True)
        return out

    @property
    def cache(self) -> Path:
        out = self.path("cache")
        out.mkdir(parents=True, exist_ok=True)
        return out


def load_config(path: str | Path | None = None) -> Config:
    """Load ``workshop.yml``.

    Parameters
    ----------
    path
        Either the YAML file itself or any directory inside the repository.
        Defaults to searching upwards from the current working directory.
    """
    if path is not None and Path(path).is_file():
        cfg_file = Path(path).resolve()
        root = cfg_file.parent
    else:
        root = find_root(path)
        cfg_file = root / CONFIG_NAME
    with open(cfg_file) as fh:
        raw = yaml.safe_load(fh)
    return Config(root=root, raw=raw)
