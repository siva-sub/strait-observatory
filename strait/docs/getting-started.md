# Getting started

For the unpublished 0.3.0rc1 source candidate, install from the repository root:

```bash
python -m pip install -e './strait[dev]'
python -m pytest strait/tests -q
```

Start with the [synthetic demo](../README.md#try-the-synthetic-demo); its observations are not real satellite results.

For real scenes, prepare a cache of calibrated linear-power TIFFs with full dates and a matching land mask. Legacy Cutout caches must already match the requested EPSG:4326 bounds and shape. No implicit warp or automatic download occurs. Use `strait.experimental.read_power_window` for projected imagery and preserve acquisition metadata. See the [API contracts](api-reference.md).

Per-scene counts need a separate observation inventory, including valid zero-detection scenes. `aggregate()` alone sums detection rows and cannot infer missing observations. Unknown presets, invalid dates, missing masks and mismatched grids are errors. Do not rename malformed date IDs to make them pass validation without source evidence.
