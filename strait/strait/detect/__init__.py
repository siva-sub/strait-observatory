"""Local threshold detectors for candidate vessels in calibrated Sentinel-1 data.

The package and retained experiment detector are not interchangeable versions.
Presets retain historical parameter values, not portable accuracy guarantees.
"""
import logging
from typing import List, Optional, Tuple

import numpy as np
from scipy import ndimage
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from rasterio.transform import from_bounds

logger = logging.getLogger(__name__)

CLASSIC_CFAR = "cfar"
TRIMMED_CFAR = "trimmed_cfar"

# Parameter presets optimized via AIS ground-truth grid search (iteration 28)
# Grid: 72 combinations tested against 2,145 unique anchored AIS vessels
# See experiments/results/parameter_optimization.csv
PRESETS = {
    "balanced": {
        "k": 5.5, "window": 64, "min_pixels": 3,
        "description": "Historical default; matching performance is dataset-specific and not guaranteed",
    },
    "precision": {
        "k": 6.5, "window": 32, "min_pixels": 7,
        "description": "Higher-threshold historical preset; not an enforcement or accuracy guarantee",
    },
    "recall": {
        "k": 4.0, "window": 64, "min_pixels": 3,
        "description": "Lower-threshold historical preset; not a census or measured recall guarantee",
    },
}

# Default parameters
DEFAULT_K = 5.5
DEFAULT_WINDOW = 64       # pixels (~2.4 km at 37 m/px)
DEFAULT_MIN_PIXELS = 3
DEFAULT_SPLIT = 25        # split components larger than this into peaks
DEFAULT_FLOOR_DB = -12.0  # absolute floor (classic CFAR only)
SEA_FLOOR_DB = -30.0     # below this is not valid sea


def detect_vessels(
    scenes: List[np.ndarray],
    dates: List[str],
    land_mask: np.ndarray,
    method: str = TRIMMED_CFAR,
    bounds: Optional[Tuple[float, float, float, float]] = None,
    shape: Tuple[int, int] = (1500, 2400),
    k: float = DEFAULT_K,
    window: int = DEFAULT_WINDOW,
    min_pixels: int = DEFAULT_MIN_PIXELS,
    split_threshold: int = DEFAULT_SPLIT,
) -> gpd.GeoDataFrame:
    """Detect vessels in a stack of calibrated SAR scenes.

    Parameters
    ----------
    scenes : list of ndarray
        Calibrated scenes (linear sigma0, float32). Shape: (rows, cols).
    dates : list of str
        Date for each scene, format "YYYYMM" or "YYYYMMDD".
    land_mask : ndarray
        Boolean: True = land, False = sea.
    method : str
        "cfar" (classic) or "trimmed_cfar" (recommended).
    bounds : tuple
        (lon_min, lat_min, lon_max, lat_max). Required for georeferencing.
    shape : tuple
        (rows, cols) of each scene.
    k : float
        CFAR multiplier. Higher = fewer detections.
    window : int
        Background window size in pixels.
    min_pixels : int
        Minimum connected-component size to count as a vessel.
    split_threshold : int
        Split components larger than this into individual peaks.

    Returns
    -------
    geopandas.GeoDataFrame
        One row per vessel: geometry(Point), date, npix, peak_db.
    """
    if method not in (CLASSIC_CFAR, TRIMMED_CFAR):
        raise ValueError(f"Unknown method '{method}'. Use '{CLASSIC_CFAR}' or '{TRIMMED_CFAR}'.")
    if len(scenes) != len(dates):
        raise ValueError("scenes and dates must have identical lengths")
    if land_mask is None or np.shape(land_mask) != tuple(shape):
        raise ValueError("land_mask shape must match the declared grid")
    if any(np.shape(a) != tuple(shape) for a in scenes):
        raise ValueError("every scene shape must match the declared grid")
    if not np.isfinite(k) or k <= 0 or window < 1 or min_pixels < 1:
        raise ValueError("positive finite detector parameters required")
    if bounds is None:
        raise ValueError("bounds are required for georeferencing")
    try:
        bounds = tuple(float(v) for v in bounds)
    except (TypeError, ValueError) as e:
        raise ValueError("bounds must be numeric WGS84 coordinates") from e
    if len(bounds) != 4 or not np.isfinite(bounds).all() or not (
        -180 <= bounds[0] < bounds[2] <= 180 and -90 <= bounds[1] < bounds[3] <= 90
    ):
        raise ValueError("bounds must be finite, ordered WGS84 coordinates")

    transform = from_bounds(*bounds, shape[1], shape[0])
    sea = ~np.asarray(land_mask, dtype=bool)
    all_detections = []

    for scene, date in zip(scenes, dates):
        db = _to_db(scene)
        if method == CLASSIC_CFAR:
            thr = _classic_threshold(db, sea, k, window)
        else:
            thr = _trimmed_threshold(db, sea, k, window)

        dets = _label_and_count(db, sea, thr, transform,
                                min_pixels, split_threshold, date)
        all_detections.extend(dets)

    if not all_detections:
        return _empty_gdf()

    geometries = [Point(d["lon"], d["lat"]) for d in all_detections]
    df = pd.DataFrame(all_detections)
    return gpd.GeoDataFrame(df, geometry=geometries, crs="EPSG:4326")


def _to_db(scene: np.ndarray) -> np.ndarray:
    scene = np.asarray(scene, dtype=np.float32)
    valid = np.isfinite(scene) & (scene > 0)
    out = np.full(scene.shape, np.nan, dtype=np.float32)
    np.log10(scene, out=out, where=valid)
    out[valid] *= 10.0
    return out


def _classic_threshold(db, sea, k, window):
    """v3.1: local mean + k*sigma with absolute floor."""
    valid = sea & np.isfinite(db) & (db > SEA_FLOOR_DB)
    if valid.sum() < 100:
        return np.full_like(db, 999.0)

    fill = float(np.median(db[valid]))
    x = np.where(valid, db, 0.0)
    x2 = np.where(valid, db * db, 0.0)
    v = valid.astype(np.float32)
    vf = np.maximum(ndimage.uniform_filter(v, window), 1e-6)

    mu = ndimage.uniform_filter(x, window) / vf
    var = ndimage.uniform_filter(x2, window) / vf - mu * mu
    sig = np.sqrt(np.clip(var, 0, 400))
    return np.maximum(mu + k * sig, DEFAULT_FLOOR_DB)


def _trimmed_threshold(db, sea, k, window):
    """v4: two-pass censored statistics (from SAR literature).

    Guards against degenerate cases:
    - Minimum MAD floor (prevents provisional threshold collapsing to median
      when background is perfectly uniform, e.g., synthetic test scenes)
    - Minimum background fraction (ensures enough pixels for stable stats)
    """
    valid = sea & np.isfinite(db) & (db > SEA_FLOOR_DB)
    if valid.sum() < 100:
        return np.full_like(db, 999.0)

    vals = db[valid]
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826
    # Guard: floor MAD to prevent degenerate threshold on uniform backgrounds
    MIN_MAD_DB = 0.5  # at least 0.5 dB spread in the background
    mad = max(mad, MIN_MAD_DB)
    provisional = med + k * mad

    bg = valid & (db < provisional)
    # Guard: ensure at least 30% of valid sea pixels remain as background
    if bg.sum() < valid.sum() * 0.3:
        bg = valid  # fall back to all valid pixels (equivalent to classic CFAR)

    x = np.where(bg, db, 0.0)
    x2 = np.where(bg, db * db, 0.0)
    v = bg.astype(np.float32)
    vf = np.maximum(ndimage.uniform_filter(v, window), 1e-6)

    mu = ndimage.uniform_filter(x, window) / vf
    var = ndimage.uniform_filter(x2, window) / vf - mu * mu
    sig = np.sqrt(np.clip(var, 0, 400))
    # Guard: minimum sigma to prevent zero-variance thresholds
    MIN_SIG_DB = 0.1
    sig = np.maximum(sig, MIN_SIG_DB)
    return mu + k * sig


def _label_and_count(db, sea, thr, transform, min_pixels, split, date):
    """Label connected components and extract vessel positions."""
    cand = sea & np.isfinite(db) & (db > thr)
    labeled, n = ndimage.label(cand)
    if n == 0:
        return []

    lmax = ndimage.maximum_filter(np.where(np.isfinite(db), db, -np.inf), size=7)
    detections = []

    for i, sl in enumerate(ndimage.find_objects(labeled), start=1):
        comp = labeled[sl] == i
        npix = int(comp.sum())
        if npix < min_pixels:
            continue

        sub = np.where(comp, db[sl], -99.0)

        if npix > split:
            peaks = comp & (sub >= lmax[sl])
            ys, xs = np.nonzero(peaks)
            if len(ys) == 0:
                cy, cx = ndimage.center_of_mass(comp)
                ys, xs = np.array([int(round(cy))]), np.array([int(round(cx))])
        else:
            cy, cx = ndimage.center_of_mass(comp)
            ys, xs = np.array([int(round(cy))]), np.array([int(round(cx))])

        for y, x in zip(ys, xs):
            row = y + sl[0].start
            col = x + sl[1].start
            lon, lat = _transform_xy(transform, col, row)
            detections.append({
                "lon": lon, "lat": lat,
                "date": date,
                "npix": npix,
                "peak_db": round(float(sub.max()), 1),
            })

    return detections


def _transform_xy(transform, col, row):
    """Convert (col, row) to (lon, lat) using an affine transform."""
    lon, lat = transform * (col + 0.5, row + 0.5)
    return lon, lat


def _empty_gdf():
    return gpd.GeoDataFrame(
        {"lon": [], "lat": [], "date": [], "npix": [], "peak_db": []},
        geometry=[],
        crs="EPSG:4326",
    )
