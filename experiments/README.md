# Reproducing the Singapore study

This directory contains analysis code and compact data tables for [Satellite-Observed Anchorage Activity and Singapore Marine-Fuel Sales](../papers/singapore-strait-observatory.md). Raw satellite rasters, AIS archives, processing caches and working notes are not included.

## Reproduce the reported tables

From the repository root:

```bash
python -m pip install -e './strait[dev]'
python -m pytest strait/tests -q
python experiments/strait-update/paper_metrics.py
python experiments/strait-update/reproduce.py
```

`paper_metrics.py` calculates the historical correlations, calendar-aligned changes and auxiliary in-sample models. `reproduce.py` uses the package's evaluation interface to reconstruct the saved expanding-window predictions. It checks both prediction values and training-month lists against the reference tables, with a numerical tolerance of 10⁻⁸ thousand tonnes.

These commands use the supplied tables. They do not download imagery, contact a model service or start cloud processing.

## Included inputs and results

| Location | Contents |
|---|---|
| `results/perscene_counts.csv` | Historical scene counts and coverage status |
| `results/perscene_join.csv` | Monthly count index and economic data |
| `data/official/` | Saved bunker-sales, total-arrivals and container-throughput series |
| `data/era5_wind_monthly.csv` | Monthly wind values for the auxiliary comparison |
| `strait-bounded-run/results/` | Scene and pair summaries, common-month feature table, predictions and uncertainty calculations |
| `strait-bounded-run/state/` | Scientific input inventory and satellite catalogue metadata; no rasters |
| `strait-update/results/` | Historical statistical summary and package prediction comparison |

The historical count series has 243 accepted scenes, of which 240 contribute to the 57 months paired with bunker sales. The supplementary paired-image comparison uses 22 common months and nine retrospectively inspected test months. These samples are separate.

## Image-level processing

`strait-bounded-run/benchmark.py` contains the geographic windowing, coverage rules, count variants and paired-image feature. Its image extraction and analysis stages require locally prepared rasters and processing caches that are not distributed here. `checks.py` includes AIS-dependent checks requiring the external historical AIS data.

Other scripts retain the image-processing and acquisition implementations used during development. They may require provider access, raw inputs and additional preparation. They are not called by the table-reproduction commands above, and their intermediate outputs are not substitutes for the paper's evidence tables.

The original cropped-image archive and complete source-product lineage are unavailable. Reproducing the statistical tables does not establish vessel-level detection accuracy or validate the physical interpretation of a backscatter change.

## Sources

- Official bunker sales: https://data.gov.sg/datasets/d_4f5abbf4486bf8e52bbed3be56dde562/view
- Total vessel arrivals: https://data.gov.sg/datasets/d_d48c5a038904f6da3c603cd854b6c191/view
- Container throughput: https://data.gov.sg/datasets/d_da030f7028200d19ffcbe4a2d71af39c/view
- Historical AIS, DOI 10.17632/r37vwd493d.1: https://data.mendeley.com/datasets/r37vwd493d/1
- Sentinel-1 processing: https://documentation.dataspace.copernicus.eu/APIs/openEO/openeo_processing.html
