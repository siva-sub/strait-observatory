# API reference: 0.3.0rc1

Source release candidate, not yet published to PyPI. Refer to function docstrings for complete signatures.

## Established entry points

- `Cutout(module="demo", x=..., y=..., time=..., path=..., shape=(1500,2400))`: spatial/time configuration. `prepare()` creates synthetic scenes in demo mode; Sentinel-1 mode loads an aligned local cache only.
- `Cutout.detect(method="trimmed_cfar", preset="balanced", **kwargs)`: candidate detections. Unknown presets/parameters are errors. `k`, `window`, `min_pixels`, `split_threshold` overrides are supported. Window/minimum-size parameters are in pixels, not fixed metres.
- `Cutout.aggregate(detections, zones, freq="MS")`: sums detection records. Not a per-scene mean. It cannot infer valid zero-detection scenes or missing acquisition dates from detections alone.
- `Zones.singapore_strait()` and `Zones.custom({...})`: rectangular analysis zones; not official legal boundaries.
- `AISMatch(source="file").load(path).match(detections, threshold_m=500)`: local-JSON proximity matching. `precision`/`recall` keys are legacy names for proximity fractions, not validated classifier scores.

## Local data

`strait.data.sentinel1.load_local_scenes(cache_dir, bounds=None, shape=(1500,2400), time_range=None)` returns scenes, full-date strings and land mask. Both raster and mask must match the requested EPSG:4326 grid. NoData and nonpositive/nonfinite power remain invalid. Time-range endpoints are inclusive; YYYY-MM endpoints include that whole month. Invalid filenames and grid mismatches raise instead of being silently skipped.

Supported scene filenames: `s1_YYYYMM.tif`, `s1_YYYYMMDD.tif`, or a date-tagged `openEO_YYYY-MM-DDZ.tif`. Filename recognition does not override the grid check. Projected openEO rasters require the experimental reader below.

`prepare_sentinel1()` cannot download. Missing local data raises an actionable error. Credentials are not required for local cache or experimental file operations.

## Experimental functions

```python
from strait.experimental import (
    SARFrame, read_power_window, temporal_change,
    monthly_calendar, expanding_compare,
)
```

### SARFrame / read_power_window

`SARFrame(power, transform, crs, acquired_at, track, radiometry, lineage="unknown", valid=None)` declares calibrated linear power and metadata. Radiometry is `sigma0` or `gamma0`; lineage is `verified`, `catalogue`, or `unknown`. The frame stores read-only copies of power and validity arrays. A verified label is a caller assertion, not something this object establishes.

`read_power_window(path, bounds, *, acquired_at, track, radiometry, lineage="unknown", band=1, max_pixels=8000000)` uses actual raster CRS/affine coordinates. It accepts trusted self-contained local GeoTIFFs, rejecting remote paths and VRTs. Bounds are WGS84; it reads the outward-rounded bounding window, including invalid pixels where it lies outside the source. It does not apply precise polygon-center clipping or a land mask. The pixel budget is checked before reading.

### temporal_change

`temporal_change(before, after, min_coverage=.8, min_days=6, max_days=24, support=None, allow_catalogue=False)` requires identical grids, track and radiometry, ordered same-month dates, sufficient common valid support and verified lineage. It returns mean absolute dB change and coverage, not vessel arrivals/departures. Catalogue-only override produces `status="conditional"`. Insufficient support returns `mean_abs_db=None`, not zero. No resampling or registration is performed.

### monthly_calendar / expanding_compare

`monthly_calendar(frame)` normalizes a unique monthly numeric panel and inserts missing months as NaN. Duplicate months, infinities and unparseable dates are errors.

`expanding_compare(frame, *, target, features, train_start="2024-01-01", min_train=12, penalty=1.0)` expects exactly two features: base index and change feature. Stable output names are `stock`, `stock_movement`, `lag_stock`, `lag_stock_movement`; the names identify models, not verified physical quantities. All compared models share dates/folds; lag1 and lag12 are calendar-based, and standardization is train-only. Returns an empty typed-column DataFrame if insufficient data.

This API contains no automatic target search, model selection, significance claim, or data-availability validation.

## Sources

- Source: https://github.com/siva-sub/strait-observatory/tree/master/strait/strait
- Research protocol: repository `experiments/strait-bounded-run/`
