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

## First comment (post immediately after, before replying to anyone)

The interactive version is the one to click: every dot on the map is a real detection, hover for zone counts.
https://siva-sub.github.io/strait-observatory/

Code, paper draft (with the failed tests reported alongside the correlation), and the pip package:
https://github.com/siva-sub/strait-observatory
https://pypi.org/project/strait-observatory/

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

## Share kit — what goes where

**In the post itself (one attachment):**
- `outputs/linkedin-card.png` — the designed card. No link in the body; LinkedIn deprioritizes posts with external links.

**First comment:** the three links above, map first. Post the comment within a minute of publishing, then reply to early commenters underneath it.

**Your profile (do this the same morning, before the post):**
- Featured section: add the live map link — it now previews with the card image (Open Graph tags deployed). Title suggestion: "Singapore Strait Observatory — vessel detection from Sentinel-1".
- Headline: if it currently reads as settlement banking only, consider appending something like "· geospatial data pipelines" so visitors from the post see the connect.
- The post's first sentence ("Geospatial data kept showing up in my feed…") answers the obvious visitor question "since when does this person do satellites?" — the EDKP/BIS line is doing credential work; keep it if asked to shorten.

**If the post gets traction, follow-up comments you can drop (one per thread, not a dump):**
- On "isn't this just ship counting?": the failure history — total counts track nothing, the anchorage zone is the whole result.
- On "can it predict?": no, skill +0.006 vs persistence; it's a same-week read.
- On methodology: the paper draft in the repo reports the three failed tests next to the correlation.

**Optional second asset (only if asked or for a later post):** a PDF of the paper draft as a LinkedIn document — but the repo link already carries it; don't front-load.
