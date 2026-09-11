"""Local satellite candidate detection and exploratory port-activity comparisons.

No general accuracy, ship-turnover, dark-vessel or forecasting guarantee.
Experimental bounded raster and retrospective evaluation tools live in
strait.experimental. Remote downloading is not bundled.
"""

__version__ = "0.3.0rc1"
__author__ = "Sivasubramanian S."

from .cutout import Cutout
from .zones import Zones
from .detect import detect_vessels, TRIMMED_CFAR, CLASSIC_CFAR, PRESETS
from .aggregate import aggregate
from .validate import AISMatch

__all__ = [
    "Cutout",
    "Zones",
    "detect_vessels",
    "aggregate",
    "AISMatch",
    "TRIMMED_CFAR",
    "CLASSIC_CFAR",
    "PRESETS",
    "__version__",
]
