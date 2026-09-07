# LinkedIn post: strait-observatory launch (v2)

**Image to attach:** `outputs/linkedin-card.png`
**Links:** first comment only.

---

## The post

Geospatial data kept showing up in my feed. My only satellite exposure was EDKP work at the BIS Innovation Hub, so I ran a side project on public data. No vendors, no procurement.

I picked the Singapore Strait. 243 Sentinel-1 scenes, 2019 to 2026. A detection filter pulls vessel positions from each image, and the monthly counts go against Singapore's official bunker sales (ship fuel). Night-lights data and AIS ship-tracking as overlays.

Counting every ship in the strait told me nothing. What worked was counting the parked ones. Ships wait at two anchorages just outside the port boundary (the OPL, Outer Port Limits), and the eastern one is where tankers load fuel. That single count tracks bunker sales at r = 0.73 over 57 months; the satellite alone explains 53% of the month-to-month movement. 610,000 AIS records say why: 70% of the anchored vessels are tankers, median stay 18 hours.

My anchorage box sat on Batam for weeks, so I was counting land. A "mega-ship consolidation" trend I believed for a week was two detector versions on one chart. When I audited the finished paper against its code, five blocking errors turned up, one a number from the wrong sample. All of it is in the repo.

As a forecast this barely matches "same as last month." It's a same-week read of activity.

The pipeline is a pip install, strait-observatory. Live map, code and paper in the comments.

If you price or finance commodity flows, which number do you personally wait for?

---

## First comment

Everything is public:
- Live map: https://siva-sub.github.io/strait-observatory/
- Code + paper draft: https://github.com/siva-sub/strait-observatory
- Package: https://pypi.org/project/strait-observatory/

The paper reports the failed tests alongside the correlation.

## Alt text for the image

Dark navy card titled "Singapore's bunker sales, read from orbit." with subtitle "what one person can do with public data, no vendors". Left panel: map of the Singapore Strait with the Singapore coastline and 371 blue dots marking vessels detected by satellite radar in one August 2026 pass, with a gold dashed box around the Eastern OPL anchorage. Right panel: line chart, 2019 to 2026, annual means z-scored, a gold line (radar anchorage counts) and a blue line (official MPA bunker sales) both rising together; callout reads "Sentinel-1 alone explains 53% of the variance". Footer: r = +0.73, n = 57 months, pip install strait-observatory.


## Mechanics

- Post Tue–Thu, 8–10am SGT.
- No edits in the first hour.
- Reply to substantive comments within two hours.

## Number provenance

| Post claim | Source |
|---|---|
| 243 scenes, 2019–2026 | `perscene_counts.csv` |
| 610,000 AIS records | Mendeley DOI 10.17632/r37vwd493d.1 |
| VIIRS night-lights overlay | `experiments/data/vnl/sg_crops/` 4 annual rasters; paper Table 11 (corroboration, annual cadence) |
| r = +0.73, 53%, n = 57 | `perscene_join.csv` |
| 70% tankers, 18h median | `ais_historical_stats.json`, `ais_dwell_times.csv` |
| loses to persistence | `nowcast_oos.json` (skill +0.006) |
| five blocking errors | `outputs/strait-observatory-code-audit.md` |
