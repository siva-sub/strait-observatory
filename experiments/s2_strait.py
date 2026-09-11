#!/usr/bin/env python3
"""S2 strait cross-sensor validation (autoresearch iter 37+).

Question: does free Sentinel-2 optical see the same ships Sentinel-1 does,
in the same zones, on the same dates?

Method:
  1. STAC search for S2 L2A over the strait bbox (same footprint as S1 crops).
  2. Windowed COG reads (B04 red, B08 NIR, SCL cloud) — free, no auth.
  3. Ship detection on optical: bright blobs on dark water. Water mask from
     B08 (NIR water < threshold), land from the same image + S2Coast raster,
     clouds from SCL. Connected components sized 20..2000 px (a 100-300 m
     vessel is 10x30..30x90 px at 10 m).
  4. Zone counts (eOPL / port_core / wOPL — same boxes as S1 series).
  5. Cross-validate: S2 zone counts vs (a) S1 counts near the same date,
     (b) AIS anchored counts for Oct-2023 scenes (the Mendeley ground truth).

Usage:
  python experiments/s2_strait.py fetch    # scenes for target months
  python experiments/s2_strait.py detect   # zone counts per scene
  python experiments/s2_strait.py validate # cross-sensor + AIS tables
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import rasterio
import requests
from pyproj import Transformer
from rasterio.windows import from_bounds

STAC = "https://earth-search.aws.element84.com/v1/search"
DIR = "experiments/data/s2_strait"
OUT_SCENE = "experiments/results/s2_strait_scene_counts.csv"

BBOX = (103.60, 1.10, 104.36, 1.46)  # S1 crop footprint

ZONES = {
    "eastern_opl": (104.00, 1.24, 104.35, 1.40),
    "port_core":   (103.68, 1.20, 104.02, 1.34),
    "western_opl": (103.58, 1.10, 103.78, 1.32),
}

# target months: Oct-2023 (AIS ground-truth month) + a 2024-2026 spread
MONTHS = ["2023-10", "2024-04", "2024-10", "2025-01", "2025-04", "2025-07",
          "2025-10", "2026-01", "2026-04", "2026-07"]


def httpsify(u):
    if u.startswith("s3://"):
        return "https://sentinel-cogs.s3.us-west-2.amazonaws.com/" + u[len("s3://sentinel-cogs/"):]
    return u


def fetch(per_month=4, max_cloud=60):
    os.makedirs(DIR, exist_ok=True)
    manifest = {}
    for m in MONTHS:
        y, mo = int(m[:4]), int(m[5:])
        r = requests.post(STAC, json={
            "collections": ["sentinel-2-l2a"], "bbox": list(BBOX),
            "datetime": f"{y}-{mo:02d}-01T00:00:00Z/{y}-{mo:02d}-28T23:59:59Z",
            "limit": 30}, timeout=60).json()
        feats = r.get("features", [])
        feats.sort(key=lambda f: f["properties"].get("eo:cloud_cover", 100))
        picked = [f for f in feats if f["properties"].get("eo:cloud_cover", 100) <= max_cloud][:per_month]
        manifest[m] = []
        for f in picked:
            fid = f["id"]; path = f"{DIR}/{fid}.tif"
            manifest[m].append({"id": fid, "path": path,
                                "cloud": f["properties"]["eo:cloud_cover"],
                                "date": f["properties"]["datetime"][:10]})
            if os.path.exists(path):
                continue
            red = httpsify(f["assets"]["red"]["href"])
            nir = httpsify(f["assets"]["nir"]["href"])
            scl = httpsify(f["assets"]["scl"]["href"])
            try:
                bands = {}
                with rasterio.open(f"/vsicurl?max_size=2000000000&url={red}") as src:
                    tr = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform
                    x0, y0 = tr(BBOX[0], BBOX[1]); x1, y1 = tr(BBOX[2], BBOX[3])
                    for tag, u in (("B04", red), ("B08", nir), ("SCL", scl)):
                        with rasterio.open(f"/vsicurl?max_size=2000000000&url={u}") as b:
                            win = from_bounds(x0, y0, x1, y1, transform=b.transform)
                            bands[tag] = b.read(1, window=win).astype("float32")
                h, w = bands["B04"].shape
                from rasterio.transform import from_bounds as tfb
                with rasterio.open(path, "w", driver="GTiff", height=h, width=w,
                                   count=3, dtype="float32",
                                   transform=tfb(x0, y0, x1, y1, w, h), crs=b.crs) as dst:
                    dst.write(bands["B04"], 1); dst.write(bands["B08"], 2); dst.write(bands["SCL"], 3)
                print(f"{m}: saved {fid} ({f['properties']['eo:cloud_cover']:.0f}%)", flush=True)
            except Exception as e:
                manifest[m][-1]["error"] = str(e)[:120]
                print(f"{m}: SKIP {fid} ({str(e)[:60]})", flush=True)
        print(f"{m}: {len(manifest[m])} scenes", flush=True)
    with open(f"{DIR}/manifest.json", "w") as fh:
        json.dump(manifest, fh)
    return manifest


def detect_ships(b04, b08, scl):
    """Optical vessel detection via LOCAL CFAR (same principle as the S1 v3.1
    detector): per-pixel background from a 64-px uniform filter over the sea
    mask, threshold mu + 3.0 sigma locally. Handles turbidity gradients that
    break a global sigma threshold. Component size 20..2000 px."""
    from scipy import ndimage
    water = (b08 < 2500) & (b04 < 2500)
    clear = ~np.isin(scl, [3, 8, 9])
    sea = (water & clear).astype("float32")
    if sea.sum() < 1000:
        return None, 0.0
    img = np.where(sea > 0, b04, np.nan)
    filled = np.where(sea > 0, b04, 0.0)
    n = ndimage.uniform_filter(sea, size=64) * 64 * 64
    mu = ndimage.uniform_filter(filled, size=64) / np.maximum(n / (64 * 64), 1e-6) * (n > 0)
    # simpler: masked local mean/std via filters on filled + count
    cnt = ndimage.uniform_filter(sea, size=64)
    mean = ndimage.uniform_filter(filled, size=64) / np.maximum(cnt, 1e-6)
    sq = ndimage.uniform_filter(np.where(sea > 0, b04.astype("float32") ** 2, 0), size=64) / np.maximum(cnt, 1e-6)
    var = np.maximum(sq - mean ** 2, 0)
    thr = mean + 3.0 * np.sqrt(var)
    bright = (b04 > thr) & (sea > 0)
    frac = bright.sum() / max(sea.sum(), 1)
    if frac > 0.02:
        return None, 1.0  # glint/residual cloud flood: reject scene
    lbl, nlab = ndimage.label(bright)
    if nlab == 0:
        return [], 0.0
    sizes = ndimage.sum(bright, lbl, range(1, nlab + 1))
    ships = [i + 1 for i, s in enumerate(sizes) if 20 <= s <= 2000]
    return ships, 0.0


def detect(manifest):
    rows = []
    for m, scenes in manifest.items():
        for s in scenes:
            if not os.path.exists(s["path"]) or "error" in s:
                continue
            with rasterio.open(s["path"]) as src:
                tr = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform
                b04f = src.read(1); b08f = src.read(2); sclf = src.read(3)
                total = 0
                zone_counts = {}
                for z, (lo0, la0, lo1, la1) in ZONES.items():
                    x0, y0 = tr(lo0, la0); x1, y1 = tr(lo1, la1)
                    w = from_bounds(x0, y0, x1, y1, transform=src.transform).round_offsets().round_lengths()
                    from rasterio.windows import Window
                    win = Window(int(w.col_off), int(w.row_off), int(w.width), int(w.height))
                    b04 = src.read(1, window=win); b08 = src.read(2, window=win)
                    scl = src.read(3, window=win)
                    ships, glint = detect_ships(b04, b08, scl)
                    zone_counts[z] = len(ships) if ships is not None else np.nan
                    total += len(ships) if ships is not None else 0
                    status = "GLINT" if glint > 0.5 else "OK"
                rows.append({"month": m, "date": s["date"], "scene": s["id"],
                             "s2_cloud_pct": s.get("cloud", np.nan), "status": status,
                             **zone_counts, "total": total})
                print(f"{s['date']}: eOPL={zone_counts.get('eastern_opl')} total={total}", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT_SCENE, index=False)
    print(f"\n{len(df)} scenes -> {OUT_SCENE}")
    return df


def validate():
    from scipy import stats
    s2 = pd.read_csv(OUT_SCENE)
    s1 = pd.read_csv("experiments/results/perscene_join.csv", index_col=0)
    s1m = s1.dropna(subset=["eopl"])
    print("═══ S2 vs S1 monthly (same month, both observed) ═══")
    merged = []
    for _, r in s2.iterrows():
        m = r["month"]
        if m in s1m.index:
            merged.append({"month": m, "s2_eopl": r["eastern_opl"],
                           "s1_eopl": s1m.loc[m, "eopl"],
                           "s2_total": r["total"], "s1_total": s1m.loc[m, "total_mean"]})
    md = pd.DataFrame(merged)
    if len(md) >= 3:
        print(md.to_string(index=False))
        for a, b in [("s2_eopl", "s1_eopl"), ("s2_total", "s1_total")]:
            sub = md.dropna(subset=[a, b])
            if len(sub) >= 3:
                r, p = stats.pearsonr(sub[a], sub[b])
                print(f"  {a} vs {b}: r={r:+.3f} (p={p:.3f}) n={len(sub)}")
    print("\n═══ S2 Oct-2023 vs AIS anchored ground truth ═══")
    oct23 = s2[s2.month == "2023-10"].dropna(subset=["eastern_opl"])
    ais = pd.read_csv("experiments/results/ais_historical_daily_anchored.csv")
    aisl = [c for c in ais.columns if c not in ("date",)]
    print("AIS anchored daily means by zone:", {c: round(ais[c].mean(), 1) for c in aisl})
    if len(oct23):
        print(oct23[["date", "eastern_opl", "port_core", "western_opl", "total"]].to_string(index=False))
        print("S2 eOPL mean vs AIS eOPL daily mean:",
              round(oct23.eastern_opl.mean(), 1), "vs",
              round(ais.get("eastern_opl", pd.Series([np.nan])).mean(), 1))
    md.to_csv("experiments/results/s2_strait_vs_s1.csv", index=False)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if cmd == "fetch":
        fetch()
    elif cmd == "detect":
        with open(f"{DIR}/manifest.json") as fh:
            detect(json.load(fh))
    else:
        validate()
