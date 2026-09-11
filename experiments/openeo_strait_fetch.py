#!/usr/bin/env python3
"""openEO strait fetch: monthly S1 VV+VH crops via CDSE openEO (headless).

For each month in range: submit a batch job (load_collection SENTINEL1_GRD,
strait bbox, VV+VH, one month), poll to finish, download the per-date GeoTIFFs
into experiments/data/openeo_strait/. Resume-safe: months already downloaded
are skipped via state file. Auth renews from the stored refresh token.

This replaces the quota-blocked Sentinel Hub Process API for the pair-diff
movement index (Jung 2026 method) over our own validated strait zones.

Usage: python experiments/openeo_strait_fetch.py [--start 2024-01 --end 2026-08]
"""
import json
import os
import sys
import time

import openeo

DIR = "experiments/data/openeo_strait"
STATE = f"{DIR}/state.json"
BBOX = {"west": 103.60, "south": 1.10, "east": 104.36, "north": 1.46}


def months(start, end):
    y, m = int(start[:4]), int(start[5:])
    ye, me = int(end[:4]), int(end[5:])
    out = []
    while (y, m) <= (ye, me):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"done": [], "failed": []}


def save_state(s):
    json.dump(s, open(STATE, "w"), indent=1)


def main():
    # User ended the open-ended download queue on 2026-09-09. Keep this legacy
    # fetcher fail-closed: cached-only benchmark is now the default workflow.
    if os.path.exists("experiments/strait-bounded-run/state/downloads-paused.json"):
        raise SystemExit(
            "Downloads are paused by the bounded-run policy. Use autoresearch.sh "
            "for the cached experiment. A future fetch needs a new explicit "
            "byte/time/asset budget and atomic .part downloads; this legacy "
            "unbounded queue must not be restarted."
        )
    args = sys.argv[1:]
    start = args[args.index("--start") + 1] if "--start" in args else "2024-01"
    end = args[args.index("--end") + 1] if "--end" in args else "2026-08"
    os.makedirs(DIR, exist_ok=True)
    state = load_state()

    conn = openeo.connect("https://openeo.dataspace.copernicus.eu")
    conn.authenticate_oidc()
    print("auth ok (refresh token)", flush=True)

    for m in months(start, end):
        if m in state["done"]:
            continue
        yy, mm = int(m[:4]), int(m[5:])
        nxt_y, nxt_m = (yy, mm + 1) if mm < 12 else (yy + 1, 1)
        t0, t1 = f"{yy}-{mm:02d}-01", f"{nxt_y}-{nxt_m:02d}-01"
        try:
            cube = conn.load_collection(
                "SENTINEL1_GRD", spatial_extent=BBOX,
                temporal_extent=[t0, t1], bands=["VV", "VH"])
            job = cube.save_result(format="GTiff").create_job(title=f"strait-{m}")
            job.start_job()
            print(f"{m}: job {job.job_id} submitted", flush=True)
            st = job.status()
            for i in range(90):
                if st in ("finished", "error", "canceled"):
                    break
                time.sleep(15)
                st = job.status()
            if st != "finished":
                state["failed"].append({"month": m, "job": job.job_id, "status": st})
                save_state(state)
                print(f"{m}: FAILED ({st})", flush=True)
                continue
            res = job.get_results()
            assets = [a for a in res.get_assets() if a.name.endswith(".tif")]
            n = 0
            for a in assets:
                a.download(f"{DIR}/{m}_{a.name}")
                n += 1
            state["done"].append(m)
            save_state(state)
            print(f"{m}: DONE, {n} tifs", flush=True)
        except Exception as e:
            state["failed"].append({"month": m, "error": str(e)[:150]})
            save_state(state)
            print(f"{m}: ERROR {str(e)[:120]}", flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()