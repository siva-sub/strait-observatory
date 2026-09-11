#!/usr/bin/env python3
"""Strait movement index from openEO S1 monthly crops (Jung 2026 method).

Consumes experiments/data/openeo_strait/*.tif (VV+VH, linear sigma0 —
convert to dB) and computes, per month and zone:

  movement  = median over consecutive-date pairs of sum|dB(t+1) - dB(t)|
              over zone pixels (Jung eq. 1-2; ships arriving/departing)
  stock     = monthly median dB (Jung's VH analog; standing objects)

Zones identical to the validated v3.1 series. Join vs bunker sales
(perscene_join.csv) and AIS (Oct-2023 when it arrives).

Usage: python experiments/strait_movement.py
"""
import glob
import json
import re

import numpy as np
import pandas as pd
import rasterio

DIR = "experiments/data/openeo_strait"
OUT_SCENE = "experiments/results/strait_movement_scene.csv"
OUT_MONTH = "experiments/results/strait_movement_monthly.csv"

# zone boxes in lon/lat (match v3.1 series)
ZONES = {
    "eastern_opl": (104.00, 1.24, 104.35, 1.40),
    "port_core":   (103.68, 1.20, 104.02, 1.34),
    "western_opl": (103.58, 1.10, 103.78, 1.32),
    "strait_all":  (103.60, 1.10, 104.36, 1.46),
}

BBOX = (103.60, 1.10, 104.36, 1.46)


def zone_slices(shape):
    H, W = shape
    out = {}
    for z, (lo0, la0, lo1, la1) in ZONES.items():
        # clamp zone to the fetched bbox (wOPL extends 0.02 deg west of it)
        x0 = max(0, int((lo0 - BBOX[0]) / (BBOX[2] - BBOX[0]) * W))
        x1 = min(W, int((lo1 - BBOX[0]) / (BBOX[2] - BBOX[0]) * W))
        y0 = max(0, int((BBOX[3] - la1) / (BBOX[3] - BBOX[1]) * H))
        y1 = min(H, int((BBOX[3] - la0) / (BBOX[3] - BBOX[1]) * H))
        out[z] = slice(y0, y1), slice(x0, x1)
    return out


def to_db(x, eps=1e-6):
    return 10.0 * np.log10(np.maximum(x, eps))


def main():
    files = sorted(glob.glob(f"{DIR}/*openEO_*.tif"))
    scenes = []
    for f in files:
        m = re.search(r"openEO_(\d{4}-\d{2}-\d{2})Z", f)
        if not m:
            continue
        scenes.append({"date": m.group(1), "path": f})
    scenes.sort(key=lambda s: s["date"])
    print(f"{len(scenes)} scenes")

    rows = []
    prev = None
    from rasterio.windows import Window
    bad = []
    for sc in scenes:
        try:
            with rasterio.open(sc["path"]) as src:
                W_, H_ = src.width, src.height
                slices = zone_slices((H_, W_))
                y0 = min(s.start for s, _ in slices.values()); y1 = max(s.stop for s, _ in slices.values())
                x0 = min(s.start for _, s in slices.values()); x1 = max(s.stop for _, s in slices.values())
                win = Window(x0, y0, x1 - x0, y1 - y0)
                vv = to_db(src.read(1, window=win).astype("float32"))
                vh = to_db(src.read(2, window=win).astype("float32"))
        except Exception as e:
            bad.append(sc["path"])
            print(f"SKIP corrupt: {sc['path']} ({str(e)[:60]})", flush=True)
            prev = None
            continue
        cur = {}
        vh_by_zone = {}
        for z, (sy, sx) in slices.items():
            cur[z] = vv[sy.start - y0:sy.stop - y0, sx.start - x0:sx.stop - x0]
            vh_by_zone[z] = vh[sy.start - y0:sy.stop - y0, sx.start - x0:sx.stop - x0]
        for z in ZONES:
            rows.append({"date": sc["date"], "zone": z, "metric": "stock_vv",
                         "value": float(np.median(cur[z]))})
            rows.append({"date": sc["date"], "zone": z, "metric": "stock_vh",
                         "value": float(np.median(vh_by_zone[z]))})
        if prev is not None and prev["date"][:7] == sc["date"][:7]:
            for z in ZONES:
                d = np.abs(cur[z] - prev["zones"][z])
                # movement: sum of |diff| over bright-changed pixels only
                # (both-pass bright OR change) — ships dominate; waves partly cancel
                rows.append({"date": sc["date"], "zone": z,
                             "metric": "pairdiff_sum", "value": float(d.sum())})
                rows.append({"date": sc["date"], "zone": z,
                             "metric": "pairdiff_bright",
                             "value": float(d[d > 2].sum())})  # >2 dB change
        prev = {"date": sc["date"], "zones": cur}

    df = pd.DataFrame(rows)
    df["month"] = df.date.str[:7]
    df.to_csv(OUT_SCENE, index=False)
    mon = (df.groupby(["month", "zone", "metric"])["value"].median()
             .reset_index()
             .pivot_table(index="month", columns=["zone", "metric"], values="value"))
    mon.columns = [f"{z}_{m}" for z, m in mon.columns]
    mon.to_csv(OUT_MONTH)
    print(f"monthly: {len(mon)} months -> {OUT_MONTH}")

    # join vs bunker sales
    from scipy import stats
    j = pd.read_csv("experiments/results/perscene_join.csv", index_col=0)
    jj = mon.join(j[["eopl", "bunker"]], how="inner")
    jj.to_csv("experiments/results/strait_movement_join.csv")
    print(f"join: {len(jj)} months")
    for col in mon.columns:
        if "pairdiff" not in col:
            continue
        sub = jj.dropna(subset=[col, "bunker"])
        if len(sub) < 6:
            print(f"  {col}: n={len(sub)} (too few)"); continue
        r, p = stats.pearsonr(sub[col], sub["bunker"])
        re_, pe = stats.pearsonr(sub[col], sub["eopl"])
        print(f"  {col}: vs bunker r={r:+.3f} (p={p:.3f}) | vs S1-stock eopl r={re_:+.3f} | n={len(sub)}")


if __name__ == "__main__":
    main()