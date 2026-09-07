# Autoresearch session: Changi from orbit (iterations 33+)

**Session:** changi-air-cargo
**Started:** 2026-09-07 (continues repo numbering; iterations 0–32 archived at autoresearch-archive/2026-09-07-strait-observatory/)
**Parent project:** strait-observatory (243 S1 scenes, eOPL r=+0.73 vs bunker sales)

## Optimization target

Pearson r between satellite-derived Changi apron/aircraft presence and official
monthly air cargo (CAAS d_744e62bfb1c524508bce0a64a2488243), reported WITH n,
usable-scene count, and gap structure. Higher is better. An honest null at n
adequate is a logged result, not a failure.

- Sensor: Sentinel-2 L2A (CDSE OData, quota-free; Process API is 403-blocked)
- Zones: Changi cargo aprons (ALPS/SATCO ~1.37N 103.99E), passenger stands,
  remote parking — static boxes
- Detector: threshold/blob on 10m bands (wide-bodies 60–74m = 6–7 px)
- Benchmark: `python experiments/changi_bench.py` → r, n, scenes/month
- Direction: higher | Max iterations: 20 | Environment: local (.venv)

## Log

(see autoresearch.jsonl)
