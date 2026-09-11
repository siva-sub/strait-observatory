"""Aggregate vessel detections by zone and time period."""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple


def aggregate(
    detections,
    zones: Optional[Dict[str, Tuple[float, float, float, float]]] = None,
    freq: str = "MS",
) -> pd.DataFrame:
    """Aggregate detections by zone and time period.

    Parameters
    ----------
    detections : geopandas.GeoDataFrame
        Output from detect_vessels() — needs geometry + date columns
    zones : dict
        {"zone_name": (lon_min, lat_min, lon_max, lat_max)}
    freq : str
        Pandas frequency: "MS" (monthly), "W" (weekly), "D" (daily)

    Returns
    -------
    pd.DataFrame
        Indexed by period, one column per zone (+ "total"). These are sums of
        detections, not per-acquisition presence means or zero-observation records.
    """
    if detections is None or len(detections) == 0:
        return pd.DataFrame()

    df = detections.copy()

    # Assign zones
    if zones:
        df["zone"] = _assign_zones(df, zones)
    else:
        df["zone"] = "all"

    # Preserve full scene dates. Never invent today's date for missing metadata.
    if "date" not in df.columns:
        raise ValueError("detections need a date column")
    def parse_date(v):
        text = str(v)
        if len(text) == 6 and text.isdigit():
            return pd.to_datetime(text, format="%Y%m", errors="raise")
        if len(text) == 8 and text.isdigit():
            return pd.to_datetime(text, format="%Y%m%d", errors="raise")
        import re
        if not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2}(?:[ T].*)?)?", text):
            raise ValueError(f"date must be a fixed calendar date, not {text!r}")
        return pd.to_datetime(text, errors="raise")
    df["period"] = df["date"].map(parse_date)
    if df["period"].isna().any():
        raise ValueError("invalid or missing date")

    # Group by period × zone
    result = df.groupby([pd.Grouper(key="period", freq=freq), "zone"]).size()
    result = result.unstack(fill_value=0)

    # Add total
    result["total"] = result.sum(axis=1)

    return result


def _assign_zones(df, zones):
    """Assign zone name to each detection based on lat/lon."""
    zone_names = []
    for _, row in df.iterrows():
        lon, lat = row.geometry.x, row.geometry.y
        assigned = "other"
        for name, (lon_min, lat_min, lon_max, lat_max) in zones.items():
            if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
                assigned = name
                break
        zone_names.append(assigned)
    return zone_names
