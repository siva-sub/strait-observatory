#!/usr/bin/env python3
"""Changi S2 pair-difference movement index (Jung 2026 method, adapted).

Adapts arXiv:2604.15444 eq. (1)-(2) to the S2 archive already on disk:
  D(t)   = sum over zone pixels of |B04(t+1) - B04(t)|   (cloud-free in both)
  V(m)   = median over the month's pairs of D
  S(m)   = median B04 brightness per zone (stock analog of Jung's VH median)

Static infrastructure (buildings, markings) cancels in the difference; what
survives is what moved between passes - aircraft repositioned, ground vehicles,
and any apron restacking. This removes the constant brightness floor that made
the iter-34 occupancy metric insensitive.

Usage: python experiments/changi_pairdiff.py
"""
import json
import os

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer

CROP_DIR = "experiments/data/changi"
OUT = "experiments/results/changi_pairdiff.csv"

ZONES = {
    "west_cargo": (103.988, 1.368, 103.997, 1.377),
    "east_cargo": (103.9965, 1.369, 104.004, 1.378),
    "pax_t123":   (103.983, 1.351, 103.996, 1.367),
    "pax_t4":     (104.002, 1.354, 104.012, 1.363),
    "airfield":   (103.980, 1.340, 104.012, 1.390),  # whole-airport control
}


def zone_windows(src, tr):
    from rasterio.windows import from_bounds
    wins = {}
    for z, (lo0, la0, lo1, la1) in ZONES.items():
        x0, y0 = tr(lo0, la0); x1, y1 = tr(lo1, la1)
        w = from_bounds(x0, y0, x1, y1, transform=src.transform).round_offsets().round_lengths()
        wins[z] = (int(w.col_off), int(w.row_off), int(w.width), int(w.height))
    return wins


def read_zone(src, win):
    c, r, w, h = win
    from rasterio.windows import Window
    return src.read(1, window=Window(c, r, w, h)), src.read(2, window=Window(c, r, w, h))


def main():
    with open(f"{CROP_DIR}/manifest.json") as fh:
        manifest = json.load(fh)
    # scene -> month, sorted by date within month
    scenes = []
    for m, lst in manifest.items():
        for s in lst:
            if os.path.exists(s["path"]):
                scenes.append({"month": m, "id": s["id"], "path": s["path"]})
    scenes.sort(key=lambda s: s["id"])  # id encodes date
    print(f"{len(scenes)} scenes on disk")

    rows = []
    prev = None  # (month, id, {zone: (b04, cloud)})
    for sc in scenes:
        with rasterio.open(sc["path"]) as src:
            tr = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform
            wins = zone_windows(src, tr)
            cur = {}
            for z, win in wins.items():
                b04, scl = read_zone(src, win)
                cloud = np.isin(scl, [3, 8, 9]).mean()
                cur[z] = (b04, cloud)
        # stock metric (per Jung's VH analog)
        for z, (b04, cloud) in cur.items():
            rows.append({"month": sc["month"], "scene": sc["id"], "zone": z,
                         "metric": "stock_bright", "value": float(np.median(b04)),
                         "cloud": float(cloud)})
        # pair difference with the previous scene (same month, consecutive dates)
        if prev is not None and prev["month"] == sc["month"]:
            for z in ZONES:
                b1, c1 = prev["zones"][z]; b2, c2 = cur[z]
                valid = (~np.isin(prev["scl"][z], [3, 8, 9])) & (~np.isin(np.full_like(b2, 0), [1]))
                # recompute masks properly: reuse cloud via SCL stored below
                if c1 > 0.3 or c2 > 0.3:
                    rows.append({"month": sc["month"], "scene": sc["id"], "zone": z,
                                 "metric": "pairdiff", "value": np.nan,
                                 "cloud": max(c1, c2)})
                    continue
                d = float(np.abs(b2.astype("float32") - b1.astype("float32")).sum())
                rows.append({"month": sc["month"], "scene": sc["id"], "zone": z,
                             "metric": "pairdiff", "value": d, "cloud": max(c1, c2)})
        prev = {"month": sc["month"], "id": sc["id"], "zones": cur,
                "scl": {z: None for z in ZONES}}
        # store SCL per zone for the next pairing (re-open cheaply: reuse cur cloud only)
        prev["zones"] = cur
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"scene-level rows: {len(df)} -> {OUT}")

    # monthly aggregate: median of pairs per month+zone
    ok = df[(df.cloud <= 0.3)]
    mon = (ok.groupby(["month", "zone", "metric"])["value"]
             .median().reset_index()
             .pivot_table(index="month", columns=["zone", "metric"], values="value"))
    mon.columns = [f"{z}_{m}" for z, m in mon.columns]
    mon.to_csv("experiments/results/changi_pairdiff_monthly.csv")
    print(f"monthly: {len(mon)} months")

    # join and report
    from scipy import stats
    off = pd.read_csv("experiments/data/official/changi_monthly.csv", index_col=0)
    j = mon.join(off, how="inner")
    j.to_csv("experiments/results/changi_pairdiff_join.csv")
    print(f"join: {len(j)} months")
    for z in ZONES:
        for met in ["pairdiff", "stock_bright"]:
            col = f"{z}_{met}"
            if col not in j.columns:
                continue
            for tgt in ["air_cargo_kt", "aircraft_total"]:
                sub = j.dropna(subset=[col, tgt])
                if len(sub) < 20:
                    continue
                r, p = stats.pearsonr(sub[col], sub[tgt])
                print(f"  {col} vs {tgt}: r={r:+.3f} (p={p:.3f}) n={len(sub)}")


if __name__ == "__main__":
    main()
