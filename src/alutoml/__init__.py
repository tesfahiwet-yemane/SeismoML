"""Helper package for the Aluto machine-learning seismicity workshop."""

from . import association, catalogue, data, magnitude, picking, plotting, stats
from .config import Config, load_config

__all__ = [
    "Config",
    "load_config",
    "association",
    "catalogue",
    "data",
    "magnitude",
    "picking",
    "plotting",
    "stats",
]
__version__ = "1.0.0"
