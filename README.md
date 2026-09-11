# Strait Observatory

Strait Observatory uses public satellite imagery to study anchorage activity and Singapore's marine-fuel sales. It turns Sentinel-1 radar returns into candidate-vessel counts, groups them by area and month, and compares them with official statistics.

- [Working paper: Satellite-Observed Anchorage Activity and Singapore Marine-Fuel Sales](papers/singapore-strait-observatory.md)
- [Interactive map](https://siva-sub.github.io/strait-observatory/): historical monthly composites and candidate detections
- [Python package and examples](strait/README.md)
- [API documentation](strait/docs/api-reference.md)

## From an image to an economic comparison

1. Read prepared Sentinel-1 radar images with their dates and geographic coordinates.
2. Exclude land and invalid pixels, then identify bright components that could be vessels.
3. Calculate candidate counts for the eastern Singapore Strait analysis area.
4. Compare monthly presence with Singapore's official bunker sales, meaning sales of marine fuel.

AIS ship-position reports provide context and a separate observational comparison. Annual VIIRS night lights are available as contextual data; neither dataset establishes vessel-level detection accuracy or independently validates the monthly fuel-sales model.

## Singapore findings

The historical study uses **240 accepted scenes across 57 months** between May 2019 and March 2026, with gaps. Counts and sales are associated in levels and year-over-year changes, with a weaker adjacent-month relationship.

| Comparison with bunker sales | Pearson r | Eligible months or month pairs |
|---|---:|---:|
| Monthly levels | 0.727 | 57 |
| Year-over-year log changes | 0.519 | 34 |
| Adjacent-month log changes | 0.180 | 52 |

These transformations use different eligible samples. The coefficients describe associations; they do not identify individual fuel transactions or establish forecasting performance.

A separate comparison adds radar backscatter change to the presence index. On **nine retrospectively inspected test months**, RMSE falls from **333.98 to 296.24 thousand tonnes**, or 11.3%. The paired uncertainty interval is **[−68.6, +23.2] thousand tonnes**, so the improvement remains uncertain. Exact source-product lineage for the paired rasters is incomplete. The [paper](papers/singapore-strait-observatory.md) reports the alternative count measures, baselines and limitations.

Singapore is a case study. Applying the software to another port requires local measurement and validation work.

## Use the package

The published package is available through:

```bash
python -m pip install strait-observatory
```

The source version is **0.3.0rc1**, an unpublished release candidate. Its experimental interfaces check raster compatibility, preserve calendar gaps and compare models on shared chronological folds. A regular PyPI install currently provides **0.2.1**, not these unreleased additions.

For the source examples and synthetic demo, see [getting started](strait/docs/getting-started.md). The package expects prepared local data; it does not bundle remote acquisition.

## Reproduce the study tables

The commands below reproduce the saved tables without raw imagery. A shallow clone also avoids downloading the older repository history.

```bash
git clone --depth 1 https://github.com/siva-sub/strait-observatory.git
cd strait-observatory
python -m pip install -e './strait[dev]'
python -m pytest strait/tests -q
python experiments/strait-update/paper_metrics.py
python experiments/strait-update/reproduce.py
```

The analysis commands use saved data and feature tables without downloading imagery or starting cloud jobs. The original cropped-image archive is incomplete, so numerical reproduction of the tables is more complete than reproduction from source imagery.

## Repository guide

- `papers/`: the working paper and numerical provenance.
- `strait/`: Python package, tests and documentation.
- `web/`: the historical map explorer.
- `experiments/`: analysis code, compact result tables and a reproduction guide.

Personal research project; not affiliated with MPA or ESA.

## Sources

- Code: https://github.com/siva-sub/strait-observatory
- Package: https://pypi.org/project/strait-observatory/
- Sentinel-1 processing: https://documentation.dataspace.copernicus.eu/APIs/openEO/openeo_processing.html
- Official bunker sales: https://data.gov.sg/datasets/d_4f5abbf4486bf8e52bbed3be56dde562/view
- Historical AIS, DOI 10.17632/r37vwd493d.1: https://data.mendeley.com/datasets/r37vwd493d/1
- VIIRS night lights: https://eogdata.mines.edu/products/vnl/
- Jung (2026), *Watching Trade from Space*, arXiv:2604.15444v2: https://arxiv.org/abs/2604.15444v2
