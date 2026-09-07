#!/usr/bin/env python3
"""Fetch Changi official monthly series (air cargo tonnage, aircraft movements).

Source: SingStat Tablebuilder M650031 (Civil Aircraft Arrivals And
Departures, Passengers, Air Cargo Tonnage And Mail - Changi Airport, Monthly).
data.gov.sg's CKAN package_show endpoint returns 403 since 2026-09-07, so the
tablebuilder API is used directly (same underlying series, no key needed).

Output: experiments/data/official/changi_monthly.csv
"""
import io
import requests
import pandas as pd

TABLE = "M650031"
OUT = "experiments/data/official/changi_monthly.csv"
WANT = {
    "Total Aircraft Arrivals And Departures": "aircraft_total",
    "Total Air Cargo Tonnage": "air_cargo_kt",
    "Air Cargo Tonnage - Total (Thousand Tonnes)": "air_cargo_kt",
    "Total Passengers (Thousand Persons)": "passengers_k",
}


def main():
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    d = s.get(f"https://tablebuilder.singstat.gov.sg/api/table/tabledata/{TABLE}",
              timeout=60).json()["Data"]
    print(f"{d['title']} | {d['frequency']} | last updated {d.get('dataLastUpdated','')[:10]}")
    frames = []
    for row in d["row"]:
        name = row["rowText"].strip()
        label = WANT.get(name)
        print(f"  series: {name[:60]:<60} {'✓' if label else ''}")
        if not label:
            continue
        df = pd.DataFrame(row["columns"])
        df.columns = ["month", label]
        frames.append(df.set_index("month"))
    out = frames[0]
    for f in frames[1:]:
        out = out.join(f, how="outer")
    out.index = pd.to_datetime(out.index, format="%Y %b").strftime("%Y-%m")
    out = out.sort_index()
    out.to_csv(OUT)
    print(f"\nsaved {OUT}: {len(out)} months, {out.index.min()}..{out.index.max()}")
    print(out.tail(4).to_string())


if __name__ == "__main__":
    main()
