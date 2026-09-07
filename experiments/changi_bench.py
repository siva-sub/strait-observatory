#!/usr/bin/env python3
"""Changi bench: S2 apron occupancy vs official air cargo (autoresearch iter 33+).

Pipeline:
  1. STAC search (earth-search.aws.element84.com, free) for Sentinel-2 L2A
     scenes over Changi per month, sorted by cloud cover.
  2. Windowed read of B04/B08/SCL COGs from sentinel-cogs S3 via /vsicurl
     (no auth, no quota; only the ~11x12 km bbox downloads).
  3. Zone metrics per scene: bright-blob area fraction (occupancy proxy) on
     B04 within each zone box, cloud-masked via SCL. Per-aircraft counting is
     NOT reliable at 10 m (blobs merge; reviewer floor ~3 FP) — zone-level
     occupancy is the robust unit, analogous to SAR zone counts.
  4. Monthly mean per zone, joined to changi_monthly.csv (SingStat M650031).
  5. Report: Pearson r per zone vs air_cargo_kt and aircraft_total, WITH n,
     scenes/month, usable dates, and gap structure.

Zones grounded on the 2026-07-05 scene by a vision-model review against OSM:
west/east cargo aprons, T1-T3 stands, T4. (The scout's original cargo box was
1.4 km too far south and crossed runway 02L/20R — corrected.)

Usage:
  python experiments/changi_bench.py fetch   # download scene crops (slow)
  python experiments/changi_bench.py detect  # zone metrics per scene
  python experiments/changi_bench.py join    # monthly join + r/n report
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.windows import from_bounds

STAC = "https://earth-search.aws.element84.com/v1/search"
CROP_DIR = "experiments/data/changi"
OUT_SCENE = "experiments/results/changi_scene_metrics.csv"
OUT_MONTH = "experiments/results/changi_monthly.csv"
OUT_JOIN = "experiments/results/changi_join.csv"

BBOX_LL = (103.96, 1.31, 104.06, 1.42)

# zone boxes (lon_min, lat_min, lon_max, lat_max), grounded 2026-07-05 + OSM
ZONES = {
    # west cargo apron around (103.9921, 1.3729): ALPS/SATCO freight stands
    "west_cargo": (103.988, 1.368, 103.997, 1.377),
    # east cargo apron around (103.9981, 1.3736)
    "east_cargo": (103.9965, 1.369, 104.004, 1.378),
    # T1-T3 contact + remote stands cluster ~103.985-103.995, 1.351-1.366
    "pax_t123": (103.983, 1.351, 103.996, 1.367),
    # T4 stands (southeast of the main complex, ~104.004-104.010, 1.355-1.362)
    "pax_t4": (104.002, 1.354, 104.012, 1.363),
}

START, END = "2019-01-01", "2026-08-31"  # match official series span of use


def stac_months():
    months = pd.period_range(START, END, freq="M")
    out = {}
    for m in months:
        r = requests.post(STAC, json={
            "collections": ["sentinel-2-l2a"], "bbox": list(BBOX_LL),
            "datetime": f"{m.start_time.isoformat()}Z/{m.end_time.isoformat()}Z",
            "limit": 30}, timeout=60)
        feats = r.json().get("features", [])
        feats.sort(key=lambda f: f["properties"].get("eo:cloud_cover", 100))
        out[str(m)] = feats
    return out


def fetch(months, per_month=3, max_cloud=70):
    os.makedirs(CROP_DIR, exist_ok=True)
    manifest = {}
    for m, feats in months.items():
        picked = [f for f in feats if f["properties"].get("eo:cloud_cover", 100) <= max_cloud][:per_month]
        manifest[m] = []
        for f in picked:
            fid = f["id"]
            path = f"{CROP_DIR}/{fid}.tif"
            manifest[m].append({"id": fid, "path": path,
                                "cloud": f["properties"]["eo:cloud_cover"]})
            if os.path.exists(path):
                continue
            def httpsify(u):
                if u.startswith("s3://"):
                    return "https://sentinel-cogs.s3.us-west-2.amazonaws.com/" + u[len("s3://sentinel-cogs/"):]
                return u
            red = httpsify(f["assets"]["red"]["href"])
            scl = httpsify(f["assets"]["scl"]["href"])
            try:
                bands = {}
                with rasterio.open(f"/vsicurl?max_size=2000000000&url={red}") as src:
                    tr = Transformer_cached(src.crs)
                    x0, y0 = tr(BBOX_LL[0], BBOX_LL[1]); x1, y1 = tr(BBOX_LL[2], BBOX_LL[3])
                    for tag, u in (("B04", red), ("SCL", scl)):
                        with rasterio.open(f"/vsicurl?max_size=2000000000&url={u}") as b:
                            win = from_bounds(x0, y0, x1, y1, transform=b.transform)
                            bands[tag] = b.read(1, window=win).astype("float32")
                h, w = bands["B04"].shape
                from rasterio.transform import from_bounds as tfb
                with rasterio.open(path, "w", driver="GTiff", height=h, width=w,
                                   count=2, dtype="float32",
                                   transform=tfb(x0, y0, x1, y1, w, h),
                                   crs=b.crs) as dst:
                    dst.write(bands["B04"], 1); dst.write(bands["SCL"], 2)
                print(f"{m}: saved {fid} (cloud {f['properties']['eo:cloud_cover']:.0f}%)", flush=True)
            except Exception as e:
                manifest[m][-1]["error"] = str(e)[:120]
                print(f"{m}: SKIP {fid} ({str(e)[:60]})", flush=True)
                continue
        print(f"{m}: {len(manifest[m])} scenes (of {len(feats)} available)")
    with open(f"{CROP_DIR}/manifest.json", "w") as fh:
        json.dump(manifest, fh)
    return manifest


_TR = {}
def Transformer_cached(crs):
    from pyproj import Transformer
    key = str(crs)
    if key not in _TR:
        _TR[key] = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
    return _TR[key]


def detect(manifest):
    rows = []
    for m, scenes in manifest.items():
        for s in scenes:
            p = s["path"]
            if not os.path.exists(p):
                continue
            with rasterio.open(p) as src:
                b04 = src.read(1); scl = src.read(2)
                tr = Transformer_cached(src.crs)
                cloudy = np.isin(scl, [3, 8, 9])
                # per-zone occupancy: bright-blob area fraction on B04
                for z, (lo0, la0, lo1, la1) in ZONES.items():
                    x0, y0 = tr(lo0, la0); x1, y1 = tr(lo1, la1)
                    win = from_bounds(x0, y0, x1, y1, transform=src.transform).round_offsets().round_lengths()
                    if win.width < 4 or win.height < 4:
                        continue
                    zr = rasterio.windows.Window(int(win.col_off), int(win.row_off),
                                                  int(win.width), int(win.height))
                    b = src.read(1, window=zr); c = src.read(2, window=zr)
                    cloud = np.isin(c, [3, 8, 9])
                    if cloud.mean() > 0.3:
                        rows.append({"month": m, "scene": s["id"], "zone": z,
                                     "occupancy": np.nan, "cloud": cloud.mean(),
                                     "status": "CLOUDY"})
                        continue
                    # adaptive threshold: bright pixels = mu + 1.5 sigma of the zone
                    mu, sd = b.mean(), b.std()
                    occ = float((b > mu + 1.5 * sd).mean())
                    rows.append({"month": m, "scene": s["id"], "zone": z,
                                 "occupancy": occ, "cloud": cloud.mean(),
                                 "status": "OK"})
    df = pd.DataFrame(rows)
    df.to_csv(OUT_SCENE, index=False)
    print(f"scene metrics: {len(df)} rows -> {OUT_SCENE}")
    return df


def join():
    sm = pd.read_csv(OUT_SCENE)
    sm = sm[sm.status == "OK"]
    mon = (sm.groupby(["month", "zone"])["occupancy"].mean().reset_index()
             .pivot(index="month", columns="zone", values="occupancy"))
    mon.to_csv(OUT_MONTH)
    off = pd.read_csv("experiments/data/official/changi_monthly.csv", index_col=0)
    j = mon.join(off, how="inner")
    j.to_csv(OUT_JOIN)
    from scipy import stats
    print(f"\njoin: {len(j)} months, {j.index.min()}..{j.index.max()}")
    for z in ZONES:
        sub = j.dropna(subset=[z, "air_cargo_kt"])
        if len(sub) < 8:
            print(f"  {z}: n={len(sub)} (too few)"); continue
        r, p = stats.pearsonr(sub[z], sub["air_cargo_kt"])
        r2, p2 = stats.pearsonr(sub[z], sub["aircraft_total"])
        print(f"  {z}: n={len(sub)} | vs air_cargo r={r:+.3f} (p={p:.3f}) | vs aircraft_total r={r2:+.3f} (p={p2:.3f})")
    nmon = sm.groupby("month").size()
    print(f"\nscenes/month: median {nmon.median():.0f}, min {nmon.min()}, max {nmon.max()}, months with 0 scenes: {(nmon==0).sum()}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "join"
    if cmd == "fetch":
        fetch(stac_months())
    elif cmd == "detect":
        with open(f"{CROP_DIR}/manifest.json") as fh:
            detect(json.load(fh))
    else:
        join()
