# LinkedIn post — strait-observatory launch (v2)

**Image to attach:** `outputs/linkedin-card.png`
**Links:** first comment only.

---

## The post

Geospatial data kept showing up in my feed. My only hands-on exposure to satellite data was the EDKP work at the BIS Innovation Hub, so I ran a fun side project to see what one person can do with publicly available data. No vendors, no procurement.

I picked the Singapore Strait. 243 Sentinel-1 radar scenes, 2019 to 2026, and a question: do the ships tell you anything the official statistics haven't printed yet?

The first version failed. Total ship counts correlate with nothing.

What worked was one small zone, the Eastern OPL anchorage where tankers wait to take fuel. Its monthly count tracks MPA bunker sales at r = 0.73 over 57 months; radar alone explains 53% of the variance. ERA5 wind barely moves the correlation. And 610,000 AIS records explain why the zone works: 70% of anchored vessels are tankers, median stay 18 hours.

I got things wrong. My zone sat partly on Batam for weeks, so I was counting land. A "mega-ship consolidation" trend I talked myself into turned out to be two detector versions mixed on one chart. The audit of my own paper found five blocking errors, one an R² from the wrong sample.

It's a same-week read, not a forecast. Run as a nowcast, it barely matches "same as last month."

The pipeline is on PyPI as strait-observatory. Live map, code, paper in the comments.

If you price or finance commodity flows, which number do you personally wait for?

---

## First comment

Everything is public:
- Live map: https://siva-sub.github.io/strait-observatory/
- Code + paper draft: https://github.com/siva-sub/strait-observatory
- Package: https://pypi.org/project/strait-observatory/

The paper reports the failed tests alongside the correlation.

## Alt text for the image

Dark navy card titled "Singapore's bunker sales, read from orbit." Left panel: map of the Singapore Strait with the Singapore coastline and 371 blue dots marking vessels detected by satellite radar in one August 2026 pass, with a gold dashed box around the Eastern OPL anchorage. Right panel: line chart, 2019 to 2026, annual means z-scored, a gold line (radar anchorage counts) and a blue line (official MPA bunker sales) both rising together; callout reads "radar alone explains 53% of the variance". Footer: r = +0.73, n = 57 months, pip install strait-observatory.


## Mechanics

- Post Tue–Thu, 8–10am SGT.
- No edits in the first hour.
- Reply to substantive comments within two hours.

## Number provenance

| Post claim | Source |
|---|---|
| 243 scenes, 2019–2026 | `perscene_counts.csv` |
| 610,000 AIS records | Mendeley DOI 10.17632/r37vwd493d.1 |
| r = +0.73, 53%, n = 57 | `perscene_join.csv` |
| wind control holds | `era5_wind_monthly.csv`: same-sample r 0.691 → partial 0.696 (n=54) |
| 70% tankers, 18h median | `ais_historical_stats.json`, `ais_dwell_times.csv` |
| loses to persistence | `nowcast_oos.json` (skill +0.006) |
| five blocking errors | `outputs/strait-observatory-code-audit.md` |
