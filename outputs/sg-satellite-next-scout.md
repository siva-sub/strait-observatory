# Scout: next satellite × data.gov.sg project

**Date:** 2026-09-07
**Context:** strait-observatory shipped (paper v2 audited, PyPI 0.2.1, live map). This scout evaluates the next build, inspired by [alanalyzing/sgtraffic](https://github.com/alanalyzing/sgtraffic) and the data.gov.sg catalogue.

---

## 1. What sgtraffic does (teardown)

A live dashboard: 90+ data.gov.sg traffic cameras → AI vision model scores congestion 1-10 per image → Google Maps heatmap → 2-hour weather forecast API → NVIDIA synthetic personas for flavour. Two free APIs, one AI layer, one map. The whole thing is a **consumer-facing live product**, not a paper — the opposite end of the spectrum from our observatory.

What it proves about data.gov.sg real-time APIs (no key needed):
- `api.data.gov.sg/v1/transport/traffic-images` — 90+ cameras, images + GPS, ~5 min cadence
- `api.data.gov.sg/v1/environment/2-hour-weather-forecast` — per-area conditions

What to steal: the shape (live → AI layer → map → dashboard), not the substance.

What it does NOT do: anything historical, anything validated, anything economic. That's our lane.

## 2. Verified data.gov.sg assets for a satellite-adjacent project

Access pattern that works today (our `fetch_official_stats.py`): `package_show` by dataset ID → newest CSV. Verified live this session:

| Dataset | ID | Coverage | Agency |
|---|---|---|---|
| Air Traffic Movements (passengers, cargo, aircraft, mail, monthly) | `d_744e62bfb1c524508bce0a64a2488243` | Jan 2015 – **Jan 2026 (current)** | CAAS |
| Changi: arrivals/departures, passengers, air cargo tonnage, mail, monthly | `d_98e2567a033e812081b78aabe250fc13` | 1989–present | SINGSTAT |
| Index of Industrial Production (2019=100), monthly | `d_3e27810b557e6294f38484cda5ad6b32` | 1983 – Dec 2025 | SINGSTAT |
| Historical 24-hr PSI, regional | `d_b4cf557f8750260d229c49fd768e11ed` | Apr 2014 – Jul 2026 | NEA |
| PSI real-time API (15 min cadence) | `d_fe37906a0182569d891506e815e819b7` | live | NEA |
| (in use already) container TEU, vessel arrivals, bunker sales, merchandise trade | see `fetch_official_stats.py` | monthly, current | MPA/SINGSTAT |

Plus real-time endpoints: traffic images, 2h weather, rainfall radar (`environment/rainfall`), taxi availability — all keyless.

**Satellite feasibility check (run this session, CDSE OData, public):** Sentinel-2 L2A over the Changi bbox: **78 scenes in 2024, ~6 distinct acquisition dates/month**. Enough for monthly aggregation after cloud filtering (Singapore ~50-60% cloud cover; expect 2-4 usable dates/month — same class of sparsity as our SAR series pre-backfill).

## 3. Candidate projects, ranked

### A. Changi from orbit — count parked aircraft from Sentinel-2 vs air cargo stats ⭐ recommended

**The pitch:** we read the sea (ships → bunker sales). Now read the air: parked freighters at Changi's cargo aprons → air cargo tonnage. Same pipeline, different sensor and port.

- **Detector:** wide-bodies are 60-74 m wingspan = 6-7 Sentinel-2 pixels at 10 m; parked aircraft are high-albedo blobs on dark apron — a threshold detector (no CFAR needed) or small-template matching. Ground truth: ADS-B exchange history or CAAS movements totals.
- **Zones:** cargo aprons (ALPS/SATCO airfreight terminals, ~1.37N 103.99E), passenger stands, remote parking. All static, easy to box like the OPL zones.
- **Official series:** CAAS air cargo + aircraft movements (current to Jan 2026 — better lag behaviour than our MPA series).
- **Symmetry sells:** "two ports, one pipeline" — the package generalizes from strait-observatory to a genuine multi-port product.
- **Honest risks:** 5-day revisit + cloud = 2-4 usable dates/month (weaker sampling than SAR's all-weather 12-day); parked ≠ active (a plane at a gate overnight looks parked); passenger vs freighter mix needs length filtering.
- **Effort:** ~1 week to first correlation using existing infra (CDSE account, zones.py, aggregate.py, econ join pattern).

### B. sgtraffic-style live bunker-queue dashboard

The trader-facing product: live AIS in the OPL zone → "tankers waiting to load fuel right now vs the 18h median" + weather + tide. We already hold every ingredient (AISStream key, dwell stats, zone logic). Ships it as the demo layer that makes the paper's economics tangible to a trading desk. Risk: operational product maintenance; MarineTraffic-adjacent crowded space — differentiate with the validated dwell/queue statistics and the satellite-validated history.

### C. Haze event economics (paper section, not a project)

PSI 2014-2026 × our SAR series: does haze visibly dent port activity? (SAR sees through haze; optical competitors' indices would glitch — a cute methods point.) Run as a §4.11 of the paper, one afternoon.

### D. Manufacturing/industrial production from VIIRS + tanker berths vs IIP

Jurong Island night-lights + berth occupancy vs IIP. Weakest signal-to-effort; park it.

## 4. Recommendation

**A now, B as its demo layer, C folded into the paper when convenient.**

Sequencing:
1. Week 1: Changi module — zones + S2 fetch (OData, quota-free) + threshold detector + monthly join vs CAAS cargo. Target: one honest number (r with n and gaps, or an honest null).
2. Week 2: dashboard (B) on top — one page, live AIS queue + historical satellite strip, sgtraffic-grade polish.
3. The paper gains a §5 "generalization" section; the package gains `strait.modules.changi`.

None of it is blocked by the CDSE Process API quota (OData downloads worked for S1 crops; S2 L2A is on the same OData catalogue).

## Sources

- sgtraffic: https://github.com/alanalyzing/sgtraffic (Manus-built; traffic images + weather APIs + AI vision)
- CAAS Air Traffic Movements: https://data.gov.sg/datasets/d_744e62bfb1c524508bce0a64a2488243/view
- SINGSTAT Changi air cargo monthly: https://data.gov.sg/datasets/d_98e2567a033e812081b78aabe250fc13/view
- IIP monthly: https://data.gov.sg/datasets/d_3e27810b557e6294f38484cda5ad6b32/view
- Historical 24-hr PSI: https://data.gov.sg/datasets/d_b4cf557f8750260d229c49fd768e11ed/view
- PSI API: https://data.gov.sg/datasets/d_fe37906a0182569d891506e815e819b7/view
- Sentinel-2 coverage check: CDSE OData catalogue, Changi bbox 103.98-104.04E / 1.34-1.42N, 2024: 78 L2A scenes, 6 dates/month (June 2024)
- data.gov.sg API access pattern: `experiments/fetch_official_stats.py` (package_show → newest CSV)
