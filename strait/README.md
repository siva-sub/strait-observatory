# strait-observatory

Python tools for candidate-vessel detection from prepared Sentinel-1 imagery, zone aggregation, and exploratory economic comparisons.

**Source version: 0.3.0rc1, a release candidate.** This version has not been uploaded to PyPI. No remote downloader is bundled, and no accuracy or forecasting performance is guaranteed for a new port.

## Try the synthetic demo

```python
import strait

cutout = strait.Cutout(module="demo", time=slice("2021-01", "2021-03"))
cutout.prepare(n_scenes=3)
detections = cutout.detect(preset="balanced")
counts = cutout.aggregate(detections, zones=strait.Zones.singapore_strait())
```

These are synthetic observations. `aggregate()` sums detections; it does not infer unobserved dates or compute a monthly mean per acquisition. Maintain a separate scene inventory when constructing a presence index.

## Use a local cache

`Cutout(module="sentinel1")` needs an already aligned **EPSG:4326** cache:

```text
cache/
  scenes/s1_YYYYMMDD.tif  # calibrated linear sigma0, matching requested bounds/shape
  land_mask.tif          # same grid; positive = excluded land
```

Pass its path to `Cutout(path="cache", x=..., y=..., time=..., shape=(rows, cols))`. Bounds, CRS, shape, full dates and time selection are checked. Missing data remain invalid. Malformed dates such as `s1_20160.tif`, different grids or a missing land mask raise explicit errors; they are not silently reinterpreted.

For native projected TIFFs, use `strait.experimental.read_power_window()` with explicit acquisition, track, lineage and radiometry. It reads a bounded georeferenced window without silently assigning a different CRS. It does not infer a coastline mask.

## Experimental model comparison

```python
from strait.experimental import expanding_compare

# panel is a numeric, monthly-indexed DataFrame with these three columns.
# Missing months are inserted as NaN, never bridged by row-based lags.
predictions = expanding_compare(
    panel,
    target="bunker",
    features=["stock", "movement"],
    train_start="2024-01-01",
    min_train=12,
    penalty=1.0,
)
```

Returns expanding-mean, previous-month, seasonal-12-month and fixed-ridge predictions on the same dates/folds. Scaling is fit on training rows only. Current-month predictors make this a **retrospective contemporaneous comparison**, not automatically a forecast or an operationally timely nowcast. Empty output means insufficient common data, not zero error.

`temporal_change()` measures mean absolute backscatter change on shared valid pixels. It requires matching grids/tracks/radiometry and actual source-product lineage by default. An explicit `allow_catalogue=True` override labels catalogue-only pairing **conditional**. Change is not vessel turnover.

## AIS comparisons

```python
matcher = strait.AISMatch(source="file").load("ais_snapshot.json")
proximity = matcher.match(detections, threshold_m=500)
```

The legacy matcher computes bidirectional nearest-neighbor proximity fractions. The `precision` and `recall` keys name these fractions; without acquisition-time labels, one-to-one assignment and known receiver coverage they are **not validated detection precision/recall**. An unmatched point is not evidence that a ship disabled AIS. The class reads local JSON; it does not fetch live AIS or load arbitrary historical CSV schemas.

## Singapore study

The retained monthly count index correlates with bunker sales at r=0.727 across 57 months; this is an in-sample association. The bounded extension compared 22 common months and nine retrospectively inspected test months. Adding a SAR change feature reduced the original-index RMSE from 333.98 to 296.24 kt, but its uncertainty interval includes no improvement. No fresh-holdout gain or general port-level validity is established.

The package evaluation API reproduces those saved predictions; it does not create new empirical evidence. See the [working paper](https://github.com/siva-sub/strait-observatory/blob/master/papers/singapore-strait-observatory.md) and local `experiments/strait-bounded-run/results/` artifacts.

## Install and tests

```bash
# From the repository root, install this source candidate:
python -m pip install -e './strait[dev]'
python -m pytest strait/tests -q
```

A normal `pip install strait-observatory` installs the published version, not this unpublished candidate.

## Sources

- Repository: https://github.com/siva-sub/strait-observatory
- Published package: https://pypi.org/project/strait-observatory/
- Cutout abstraction inspiration, atlite: https://github.com/PyPSA/atlite
- Jung (2026), *Watching Trade from Space*, arXiv:2604.15444v2: https://arxiv.org/abs/2604.15444v2 . The experimental change helper is not a replication of that paper.

MIT licensed. API documentation: [documentation](docs/index.md).
