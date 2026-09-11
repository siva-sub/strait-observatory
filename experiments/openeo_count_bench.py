#!/usr/bin/env python3
"""Apples-to-apples: v3.1-constant detector counts on the SAME openEO scenes the
movement index uses. eOPL only (open water, no landmask). Monthly vs bunker."""
import glob, re
import numpy as np, pandas as pd, rasterio
from scipy import ndimage
from pyproj import Transformer

BBOX = (103.60, 1.10, 104.36, 1.46)
ZONE = (104.00, 1.24, 104.35, 1.40)
K, WIN, MINP, FLOOR = 5.5, 64, 3, -12.0

rows, bad = [], 0
files = sorted(glob.glob("experiments/data/openeo_strait/*openEO_*.tif"))
for f in files:
    m = re.search(r"openEO_(\d{4}-\d{2}-\d{2})Z", f)
    if not m: continue
    try:
        with rasterio.open(f) as src:
            tr = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform
            vv = src.read(1).astype("float32")
            vv = 10*np.log10(np.maximum(vv, 1e-6))
            H, W = vv.shape
            x0 = int((ZONE[0]-BBOX[0])/(BBOX[2]-BBOX[0])*W); x1 = int((ZONE[2]-BBOX[0])/(BBOX[2]-BBOX[0])*W)
            y0 = int((BBOX[3]-ZONE[3])/(BBOX[3]-BBOX[1])*H); y1 = int((BBOX[3]-ZONE[1])/(BBOX[3]-BBOX[1])*H)
            z = vv[y0:y1, x0:x1]
            mu = ndimage.uniform_filter(z, size=WIN)
            sq = ndimage.uniform_filter(z**2, size=WIN)
            sd = np.sqrt(np.maximum(sq - mu**2, 0))
            thr = np.maximum(mu + K*sd, FLOOR)
            bright = z > thr
            lbl, n = ndimage.label(bright)
            ships = int((ndimage.sum(bright, lbl, range(1, n+1)) >= MINP).sum()) if n else 0
            rows.append({"date": m.group(1), "openeo_eopl_count": ships})
    except Exception:
        bad += 1
df = pd.DataFrame(rows)
df["month"] = df.date.str[:7]
mon = df.groupby("month")["openeo_eopl_count"].mean()
print(f"scenes: {len(df)} (bad: {bad}) | months: {len(mon)}")
j = pd.read_csv("experiments/results/perscene_join.csv", index_col=0)
jj = mon.to_frame().join(j[["eopl", "bunker"]], how="inner").dropna(subset=["bunker"])
jj.to_csv("experiments/results/openeo_count_join.csv")
from scipy import stats
r, p = stats.pearsonr(jj.openeo_eopl_count, jj.bunker)
r0, p0 = stats.pearsonr(jj.openeo_eopl_count, jj.eopl)
print(f"\nopenEO detector count vs bunker: r={r:+.3f} (p={p:.3f}) n={len(jj)}")
print(f"openEO count vs original S1 series: r={r0:+.3f} (cross-pipeline agreement)")
print(f"means: openEO={jj.openeo_eopl_count.mean():.0f} | original={jj.eopl.mean():.0f}")
