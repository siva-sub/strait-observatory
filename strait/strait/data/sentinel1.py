"""Local Sentinel-1 cache access. Remote downloading is NOT bundled.

Caches contain scenes/s1_YYYYMMDD.tif (calibrated linear sigma0), a matching
land_mask.tif, and optional manifest.json. Legacy Cutout caches must already
share the requested EPSG:4326 grid. Use experimental.read_power_window for
native projected imagery. NoData, dates and bounds are checked explicitly.
"""
import os
import json
import logging
import glob as globlib
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
import rasterio
from rasterio.transform import from_bounds as affine_from_bounds

logger = logging.getLogger(__name__)


def _scene_date(path):
    """Parse only documented date-bearing filenames; never truncate date IDs."""
    import re
    import pandas as pd
    stem = Path(path).stem
    m = re.search(r"(?:^s1_|^|openEO_)(\d{4}-\d{2}-\d{2}|\d{8}|\d{6})(?:Z|$)", stem)
    if not m:
        raise ValueError(f"Cannot resolve scene date from {Path(path).name}")
    text = m.group(1)
    fmt = "%Y-%m-%d" if "-" in text else "%Y%m%d" if len(text) == 8 else "%Y%m"
    try:
        return pd.to_datetime(text, format=fmt).strftime("%Y%m%d")
    except ValueError as e:
        raise ValueError(f"Invalid scene date in {Path(path).name}") from e


def discover_local_scenes(cache_dir: str = "~/.strait") -> List[dict]:
    """Inspect local TIFFs; preserve full dates and native grid metadata.

    Invalid filenames or unreadable rasters raise rather than silently disappear.
    """
    cache = Path(cache_dir).expanduser()
    found = []
    for path in sorted((cache / "scenes").glob("*.tif")):
        date = _scene_date(path)
        with rasterio.open(path) as src:
            found.append({"path": str(path), "date": date,
                          "bounds": tuple(src.bounds), "shape": src.shape,
                          "crs": str(src.crs), "transform": list(src.transform)})
    return found


def _check_grid(src, bounds, shape, label):
    if src.crs != rasterio.crs.CRS.from_epsg(4326):
        raise ValueError(f"{label}: legacy Cutout cache needs EPSG:4326; use experimental.read_power_window for native CRS data")
    if src.transform.b != 0 or src.transform.d != 0 or src.transform.a <= 0 or src.transform.e >= 0:
        raise ValueError(f"{label}: north-up axis-aligned grid required")
    if tuple(src.shape) != tuple(shape):
        raise ValueError(f"{label}: shape {src.shape} does not match requested {shape}")
    if not np.allclose(tuple(src.bounds), tuple(bounds), rtol=0, atol=1e-9):
        raise ValueError(f"{label}: bounds do not match the requested grid; no implicit warp is performed")


def load_local_scenes(cache_dir="~/.strait", bounds=None, shape=(1500, 2400), time_range=None):
    """Load an already aligned EPSG:4326 scene cache with explicit land mask.

    Unlike <=0.2.x, mismatched bounds/CRS/shape and ambiguous dates are errors.
    There is no implicit reprojection. Full acquisition dates are retained and
    optional time_range (inclusive; month strings include their whole month) is
    applied. Zero/NoData/nonfinite power remains NaN, not a synthetic dark return.
    """
    import pandas as pd
    cache = Path(cache_dir).expanduser()
    mask_path = cache / "land_mask.tif"
    if not mask_path.exists():
        raise FileNotFoundError(f"Required land mask is missing: {mask_path}")
    items = discover_local_scenes(str(cache))
    if not items:
        raise FileNotFoundError(f"No valid scene TIFFs in {cache / 'scenes'}")
    if bounds is None:
        bounds = items[0]["bounds"]
    if time_range is not None:
        start, end = map(str, time_range)
        if len(start) == 6 and start.isdigit(): start = start[:4] + "-" + start[4:]
        if len(end) == 6 and end.isdigit(): end = end[:4] + "-" + end[4:]
        lo = pd.Timestamp(start)
        hi = pd.Period(end, freq="M").end_time if len(end) in (7, 6) else pd.Timestamp(end)
        if lo > hi:
            raise ValueError("time_range starts after its end")
        items = [x for x in items if lo <= pd.Timestamp(x["date"]) <= hi]
    if not items:
        raise FileNotFoundError("No scenes within the requested time_range")
    with rasterio.open(mask_path) as src:
        _check_grid(src, bounds, shape, "land mask")
        mask_data = src.read(1)
        land_mask = (mask_data != 0) | ~np.isfinite(mask_data) | (src.read_masks(1) == 0)
    scenes, dates = [], []
    for item in items:
        with rasterio.open(item["path"]) as src:
            _check_grid(src, bounds, shape, Path(item["path"]).name)
            a = src.read(1, masked=True).astype(np.float32).filled(np.nan)
        a[~np.isfinite(a) | (a <= 0)] = np.nan
        scenes.append(a); dates.append(item["date"])
    return scenes, dates, land_mask


def create_cache_from_directory(
    source_dir: str,
    cache_dir: str = "~/.strait",
    land_mask_path: Optional[str] = None,
):
    """Build a local cache from a directory of .tif scenes.

    This is the bridge between the observatory project's raw data
    and the strait package's cache format.
    """
    cache = Path(cache_dir).expanduser()
    scenes_dir = cache / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    # Copy scenes
    copied = 0
    for path in sorted(globlib.glob(os.path.join(source_dir, "*.tif"))):
        dst = scenes_dir / Path(path).name
        if not dst.exists():
            import shutil
            shutil.copy2(path, dst)
            copied += 1

    # Copy land mask
    if land_mask_path:
        dst_mask = cache / "land_mask.tif"
        if not dst_mask.exists():
            import shutil
            shutil.copy2(land_mask_path, dst_mask)

    # Write manifest
    manifest = {"scenes": discover_local_scenes(str(cache)), "created": str(np.datetime64("now"))}
    with open(cache / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=1)

    logger.info("Cache created: %d scenes copied, mask: %s", copied, bool(land_mask_path))


# ── CDSE access (requires credentials) ──

def get_credentials() -> Tuple[str, str]:
    """Get CDSE credentials from environment or .env file."""
    user = os.environ.get("CDSE_USER", "")
    password = os.environ.get("CDSE_PASSWORD", "")

    if not user:
        for env_path in [".env", os.path.expanduser("~/.strait/.env")]:
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("CDSE_USER="):
                            user = line.split("=", 1)[1]
                        elif line.startswith("CDSE_PASSWORD="):
                            password = line.split("=", 1)[1]
    return user, password


def get_token() -> str:
    """Get OAuth token from CDSE."""
    import requests

    user, password = get_credentials()
    if not user:
        raise RuntimeError("CDSE credentials not found. Set CDSE_USER and CDSE_PASSWORD.")

    r = requests.post(
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data={"grant_type": "password", "username": user, "password": password,
              "client_id": "cdse-public"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def prepare_sentinel1(
    bounds: Tuple[float, float, float, float],
    time_range: Tuple[str, str],
    cache_dir=None,
    shape: Tuple[int, int] = (1500, 2400),
    use_local: bool = True,
) -> Tuple[List[np.ndarray], List[str], np.ndarray]:
    """Prepare Sentinel-1 scenes for a bounding box.

    Loads local cache only. Remote mode raises a clear NotImplementedError.
    """
    if use_local:
        try:
            return load_local_scenes(str(cache_dir or "~/.strait"), bounds, shape, time_range=time_range)
        except FileNotFoundError:
            logger.info("No suitable local cache found; remote download is not bundled.")

    # CDSE path (requires credentials and quota).
    # NOTE: the OData downloader is not bundled in v0.2.x — remote download is
    # not supported yet. Point users at the observatory scripts instead of
    # crashing with an opaque ModuleNotFoundError.
    raise NotImplementedError(
        "No local scene cache found and the CDSE downloader is not bundled "
        "in this release. Either (a) create a local cache with "
        "create_cache_from_directory(...) from pre-processed Sentinel-1 "
        "GeoTIFFs (see the observatory repo's experiments/ scripts for "
        "downloading via CDSE), or (b) wait for download support in a "
        "future release."
    )
