# Satellite-Observed Anchorage Activity and Singapore Marine-Fuel Sales

*Working paper · 9 September 2026*

## Abstract

Satellite images record vessels present during an overpass, whereas marine-fuel sales measure a flow accumulated over a month. We compare a monthly candidate-vessel count index from Sentinel-1 imagery of an eastern Singapore Strait anchorage area with official Singapore bunker sales. Across 57 months between May 2019 and March 2026, represented by 240 accepted scenes, the level correlation is 0.727. The correlation is 0.519 for year-over-year log changes and 0.180 for adjacent-month log changes, using 34 and 52 eligible month pairs, respectively. We then examine whether radar backscatter change adds information to presence counts. Across nine retrospectively evaluated months, adding change reduces root mean squared error from 333.98 to 296.24 thousand tonnes, an 11.3% reduction. A paired resampling interval for the error difference spans −68.6 to +23.2 thousand tonnes. These test dates had already been inspected, and source-product lineage for the paired rasters is incomplete. The results establish an association between observed anchorage presence and marine-fuel sales, with a weaker relationship in adjacent-month changes. Backscatter change warrants further testing as a supplementary measure; the present evidence does not establish a forecasting advantage.

## 1. Introduction

Marine-fuel sales connect shipping activity to demand for energy. Measuring that activity from satellite imagery could provide an additional source of economic information, particularly where vessel-position reports are incomplete. Yet a satellite does not observe fuel sales directly. A radar image records returns from objects and water during an overpass. Converting those observations into a monthly economic indicator requires decisions about where to measure, which returns to count and how to combine irregular observations.

An anchorage makes the measurement problem concrete. Vessels may remain in an area across several overpasses, while fuel can be delivered and recorded between observations. A high vessel count could accompany more shipping activity, longer stays or changes in the composition of vessels using the area. The count alone cannot distinguish these explanations. A useful economic association therefore need not imply an accurate estimate of short-term changes in fuel demand.

This paper studies a project-defined eastern anchorage area in the Singapore Strait and Singapore's monthly bunker sales, meaning sales of marine fuel. We ask whether satellite-observed vessel presence is associated with those sales, how the relationship differs between levels and changes over calendar intervals, and whether changes in radar backscatter provide additional information. The analysis combines a historical Sentinel-1 count series with a separate paired-image study. Official vessel-arrival and container-throughput series provide secondary comparisons; Automatic Identification System (AIS) reports help describe the activity observed in the area.

The main finding is a positive association between the presence index and fuel-sales levels, accompanied by a much weaker adjacent-month change relationship. Adding backscatter change lowers retrospective estimation error on a small set of months, but the uncertainty includes no improvement. The contribution is a geographically specific assessment of the economic information in two satellite measurements, together with software for comparing them under explicit spatial and calendar constraints.

### Related work

In *World Seaborne Trade in Real Time*, Cerdeiro et al. (2020) develop an AIS-based approach to measuring maritime trade. Here, imagery supplies the primary activity measure, while AIS provides a separate observational comparison. [S1] In *Watching Trade from Space: Measuring Maritime Trade Using Satellite Imagery*, Jung (2026) combines Sentinel-1 features, night lights and port characteristics to study maritime trade across ports. [S2] We address a different target: monthly marine-fuel sales associated with activity in one anchorage area. Our paired-image feature also differs in radiometric transformation, spatial averaging, masking and evaluation design.

These approaches share a measurement challenge. A satellite feature must first represent a physical quantity consistently and then be evaluated against the economic quantity of interest. Image differences can reflect vessel activity as well as sea state, speckle, registration and processing. A proximity match between a radar return and an AIS position presents a related difficulty: without matching acquisition times, it does not establish that both observations describe the same vessel.

## 2. Study area and data

### 2.1 Satellite observations

The eastern analysis rectangle covers 104.00–104.35°E and 1.24–1.40°N. It is an analytical boundary, not an official legal anchorage polygon. The historical Sentinel-1 images cover a larger area, 103.55–104.35°E and 1.05–1.55°N, from which eastern-zone counts are extracted.

The historical per-scene table contains 381 records. Of these, 243 meet the coverage criterion and 138 are marked as having insufficient coverage. The accepted observations span 60 months; 240 scenes in 57 months can be paired with the available bunker-sales data between May 2019 and March 2026. The other three accepted scenes fall in July–September 2026. Sampling is uneven, and some calendar months are absent. The analysis uses the saved scene counts and monthly index; the complete original cropped-image archive and source-product lineage are unavailable. [A1]

A separate image collection supports the paired-image analysis. Its fixed inventory contains 225 processed rasters. Nineteen files from incompletely downloaded months are excluded. Of the remaining 206, 195 have valid observations over at least 80% of the water area within the analysis window, as required. The inventory and exclusion records are preserved with the analysis. [A2]

These rasters have a 10 m grid in EPSG:32648. Geographic bounds are transformed into the raster coordinate system, and pixel centers determine membership in the analysis rectangle. A coastline mask with a 40 m shore buffer excludes 22.2% of the rectangle's pixels. Nonfinite values, NoData and nonpositive power values are excluded before logarithms or image statistics are calculated. These exclusions are relevant to the processing service used here: CDSE documentation notes that zero values can arise from thermal-noise removal and can also be interpreted as NoData. [S3]

Pair selection requires compatible grids and uses dates whose catalogue metadata identify Sentinel-1A, relative orbit 98, ascending. Eligible pairs fall within the same month and are 6–24 days apart; the accepted primary-track pairs are 12 days apart. The catalogue association does not establish which source products contributed to every date-level raster, and pixel registration has not been independently assessed. We therefore treat the change feature as conditional on acquisition and processing compatibility. [A2]

### 2.2 Economic and AIS data

The primary target is monthly Singapore bunker sales from data.gov.sg, expressed in thousands of tonnes (kt). Secondary series measure total arrivals of vessels above 75 gross tonnage and container throughput. The analysis uses saved data snapshots rather than assuming that the values incorporate subsequent official revisions. The geographic coverage differs: the satellite index describes one eastern rectangle, while the economic series describe Singapore-wide activity. [S4–S6]

Historical AIS observations come from the Singapore subset of *AIS Data from 11 ports around the globe*, covering October 2023. The local file contains 609,975 reports. Navigation status and vessel type are reported attributes; tanker classification or anchored status alone does not identify a fuel transaction. [S7] Monthly ERA5 wind is used for an auxiliary weather comparison. [S8]

## 3. Methods

### 3.1 Measuring vessel presence

The historical detector operates on VV backscatter expressed in decibels. It identifies candidate returns above a local mean-plus-standard-deviation threshold:

$$
T(i)=\max\left[\mu_B(i)+5.5\sigma_B(i),-12\ \mathrm{dB}\right],
$$

where $B$ is a 64-pixel background window. The implementation clips the local variance to [0, 400] dB² before taking its square root to obtain $\sigma_B$. Connected components smaller than three pixels are excluded, and components larger than 25 pixels are split using local peaks. A temporal-median mask excludes persistent bright areas. For local background calculations, excluded pixels are filled with the scene's median valid-sea value. Scenes require at least 80% valid-sea coverage over the processed area. These rules define a candidate-return detector; they do not establish a calibrated false-alarm rate or a complete vessel census. [A1]

The monthly presence index is the mean eastern-zone count across accepted observations. Each accepted scene receives equal weight. Any base-100 presentation scaling leaves the reported correlations unchanged. The term *presence* refers to candidates observed during the sampled overpasses, not unique vessels visiting during the month.

The paired-image study includes two additional count measures. The physical-window variant uses the same threshold coefficient and dB floor, a 237-pixel background window on the 10 m grid, and a minimum component of 41 pixels. The background window and minimum component correspond to approximately 2.37 km and 4,100 m², respectively. A compact-window variant uses a 64-pixel window and three-pixel minimum. Counts are expressed per 100 km² of valid water. Differences in masking, sampling, peak splitting and resolution prevent these variants from being treated as interchangeable versions of the historical index. [A2]

### 3.2 Measuring backscatter change

For the paired-image feature, native power is averaged onto 40 m cells before conversion to dB. Each cell requires valid observations over at least 95% of its expected water area, and each pair requires at least 80% shared water coverage. For observations at $t$ and $t'$, let $V_{t,t'}$ denote the shared valid-water cells and $w_i$ the water-area weights. The feature is

$$
C_{t,t'}=
\frac{\sum_{i\in V_{t,t'}}w_i
\left|10\log_{10}I_{t'}(i)-10\log_{10}I_t(i)\right|}
{\sum_{i\in V_{t,t'}}w_i}.
$$

The monthly value is the median across accepted within-month pairs. The new count measures use the unique endpoint scenes of the accepted pairs. There are usually one or two accepted pairs per supported month. Count density is normalized by each scene's valid area; change uses the area observed in both scenes. The historical presence index remains a separate monthly series with its own acquisition sample. Thus, matching months does not make the measurements identical in pixel support or observation times. [A2]

This feature measures changes in radar returns. Interpreting it as a vessel-turnover rate would require acquisition-matched observations of vessel movement and controls for other causes of backscatter variation.

### 3.3 Association and retrospective estimation

We calculate Pearson correlations for levels, year-over-year log changes and adjacent-month log changes. The calendar is completed before differencing. Annual changes are $\log X_m-\log X_{m-12}$; adjacent-month changes are $\log X_m-\log X_{m-1}$. A pair is used only when both required calendar months are observed. Rank correlations and correlations of year-over-year percentage changes provide additional descriptive comparisons. [A1]

The paired-image comparison contains 22 common months between January 2024 and March 2026. Missing months are November–December 2024 and January, September and November 2025. Expanding-window models require at least 12 preceding observations with the required target and features. This yields nine test months: May–August, October and December 2025, followed by January–March 2026. Training samples grow from 12 to 20 observations. [A2]

We fit ridge regressions with penalty 1 and an intercept, standardizing features using training data only. Each model estimates current-month bunker sales from current-month satellite features. Comparators use the same test dates and training folds. The baselines are the expanding training mean, previous-calendar-month sales and sales from twelve calendar months earlier. Performance is measured by root mean squared error (RMSE) in kt.

These are exploratory retrospective comparisons. The historical zone and detector were developed while examining outcomes, and the test dates had been inspected during model development. The historical-index-plus-change model was considered after the new-detector comparison. Chronological training prevents future observations from entering a fitted model, but does not remove this specification-selection problem. Nor does the use of current-month imagery establish when an estimate could have been available operationally.

For the combined-minus-presence RMSE difference, we report the 2.5th and 97.5th percentiles of 2,000 paired block-resampling draws. Blocks contain at most three observations and stop at calendar gaps or sequence ends. With only nine test months, this is an uncertainty sensitivity analysis rather than a definitive significance test. [A2]

### 3.4 AIS comparison

We aggregate October 2023 AIS reports within the eastern rectangle by date, anchored status and unique identifier. The resulting daily totals are compared with available radar counts. A daily union of identifiers differs from an overpass snapshot, and the image water mask further restricts the observed area. The comparison therefore assesses broad agreement between two observation systems, not detection precision or recall. A reproducible, acquisition-time reference set with one-to-one vessel matching is unavailable. [A3]

## 4. Results

### 4.1 Presence is associated with sales levels, less strongly with adjacent-month changes

The historical presence index and bunker sales have a Pearson correlation of 0.727 across 57 months and a rank correlation of 0.738. The year-over-year log-change correlation is 0.519 across 34 month pairs. Adjacent-month log changes are more weakly related, at 0.180 across 52 pairs. [A1]

**Table 1. Associations between the historical presence index and official monthly statistics.**

| Target | Levels, Pearson r (n=57) | Year-over-year log changes, r (n=34) | Adjacent-month log changes, r (n=52) |
|---|---:|---:|---:|
| Bunker sales | 0.727 | 0.519 | 0.180 |
| Total vessel arrivals | 0.637 | 0.230 | −0.038 |
| Container throughput | 0.571 | 0.188 | −0.143 |

*All differences use calendar-aligned observations. Year-over-year percentage changes give a bunker-sales correlation of 0.508 on the same 34 pairs. Source: A1.*

Bunker sales have the largest correlation among the three economic series under each reported transformation. The relationships are descriptive: the transformations use different eligible samples, and seasonality, serial dependence and historical specification selection remain possible explanations for part of the association. In particular, the level correlation should not be interpreted as evidence of accurate month-to-month estimation.

### 4.2 Count definitions affect the measured association

On the 22 months shared by the historical and paired-image studies, the historical presence index has a bunker-sales correlation of 0.606. The physical-window and compact-window count measures have correlations of 0.499 and 0.342, respectively. Their different results show that detector and sampling choices matter to the empirical association. They do not isolate which processing choice is responsible. [A2]

**Table 2. Satellite measures compared with bunker sales on identical months.**

| Measure | Pearson r | Spearman ρ | Months |
|---|---:|---:|---:|
| Historical presence index | 0.606 | 0.493 | 22 |
| Physical-window count density | 0.499 | 0.567 | 22 |
| Compact-window count density | 0.342 | 0.400 | 22 |
| Backscatter change | 0.096 | −0.031 | 22 |

*New counts are candidates per 100 km² of valid water. Change is the area-weighted absolute dB difference. Source: A2.*

The physical-window count and historical index have a correlation of 0.691 across these months. This agreement between two processing routes is distinct from agreement with observed vessels. Backscatter change has little standalone linear association with fuel sales, but that does not determine whether it adds information conditional on presence counts.

### 4.3 Change lowers retrospective error, but the improvement is uncertain

Adding change to the historical index reduces RMSE from 333.98 to 296.24 kt on the nine test months. Absolute error is lower in seven of nine months. The relative RMSE reduction is 11.3%, while the paired resampling interval for combined-minus-presence RMSE is [−68.6, +23.2] kt. The interval includes both improvement and deterioration. [A2]

**Table 3. Retrospective estimation errors on the same nine test months.**

| Model | RMSE (kt) |
|---|---:|
| Expanding training mean | 443.79 |
| Twelve-month seasonal baseline | 444.61 |
| Previous-month sales | 376.57 |
| Historical presence index | 333.98 |
| Historical presence index + change | 296.24 |
| Physical-window count density | 385.11 |
| Physical-window count density + change | 338.06 |
| Compact-window count density | 436.83 |
| Compact-window count density + change | 423.15 |

*Ridge models use penalty 1, training-only standardization and identical expanding folds. All satellite predictors are contemporaneous with the target month. Dates and specification choices were retrospectively inspected. Source: A2.*

The physical-window count model alone performs worse than the previous-month baseline. Adding change reduces its error, but the resulting RMSE of 338.06 kt remains above that of the historical presence index alone. The compact-window models perform worse still. The results provide a reason to test change as an addition to the historical index; they do not support replacing that index with either new count measure.

### 4.4 AIS describes the activity, but does not validate individual detections

The October 2023 AIS data contain 4,414 unique identifiers within the eastern rectangle. Among 42,617 anchored-status reports, 70.05% carry tanker type codes. Tankers therefore account for a substantial share of reported anchored activity. This is a share of reports, not of unique vessels, and it does not establish which vessels purchased fuel. [A3]

Eight accepted radar dates are available for that month, and seven can be paired with daily AIS totals. The physical-window count and daily total of unique identifiers with anchored status have a correlation of 0.236, with an illustrative independent-observation Fisher interval of [−0.629, +0.840]. The small sample and mismatched temporal and spatial supports make this result inconclusive. Vessel-level detection accuracy cannot be inferred from it. [A3]

## 5. Discussion

### Economic interpretation

The historical presence index contains information associated with monthly marine-fuel sales, but its interpretation depends on the quantity being compared. An average of overpass counts measures sampled occupancy. Monthly sales accumulate transactions across vessels and locations. The positive level and year-over-year relationships are compatible with shared variation in shipping activity; the weak adjacent-month relationship limits the case for using presence alone to estimate short-term changes.

Several explanations remain unresolved. Changes in vessel mix, length of stay or the location of fuel deliveries could alter sales without a proportional change in eastern-zone occupancy. Conversely, vessels could accumulate in the rectangle without a corresponding increase in fuel purchases. The AIS tanker share makes the economic comparison relevant, but does not distinguish these mechanisms. The mismatch between a single analysis area and Singapore-wide sales further limits attribution.

Backscatter change could supply information that a monthly mean count omits. Its weak standalone correlation alongside lower combined-model error is consistent with that possibility. It is also compatible with chance, processing effects or specification selection in a small sample. Exact source-product lineage and registration checks are needed before assigning a physical interpretation to the incremental feature.

### Measurement and evaluation limits

The two image studies have different acquisition samples, masks and detector behavior. Even in the common-month comparison, a count from the historical pipeline and a paired-image count need not describe the same vessels or water pixels. Land masking, valid-area thresholds, sea state and the number of observations per month can all affect the index. One or two within-month pairs provide sparse sampling of activity, and annual or seasonal associations do not by themselves resolve those measurement uncertainties.

The retrospective error comparison is particularly limited by the nine inspected test dates. Identical folds and training-only standardization make the fitted-model comparison reproducible, but do not make it an independent test of a previously explored specification. Historical release times for official data and availability times for imagery have also not been reconstructed. Consequently, the analysis does not establish an information lead over published statistics.

The incomplete original image archive limits reproduction from source imagery, while the saved tables support numerical reproduction of the reported associations and model comparisons. The AIS data cover one month and lack a validated acquisition-time reference set. These constraints restrict the claims to this area, these samples and these processing definitions.

### Implications for further measurement

The results support keeping presence and backscatter change as separate measurements rather than assigning both a vessel-traffic interpretation. A subsequent evaluation should fix the count and change specifications before later sales outcomes are examined, preserve the contributing satellite products and record when both predictors and official targets become available. Acquisition-time AIS matching would address detection accuracy; an unseen-month economic test would address estimation performance. Those tests answer different questions, and both are needed before operational use.

## 6. Conclusion

Sentinel-1 candidate-vessel counts in an eastern Singapore Strait anchorage area are associated with Singapore marine-fuel sales in levels and year-over-year changes. The weaker adjacent-month relationship shows the limit of interpreting that association as short-term estimation skill. Backscatter change reduces error when added to the historical count index in a small retrospective comparison, but the uncertainty includes no gain. The evidence supports further evaluation of satellite-observed anchorage presence as an economic measure, with change tested as a supplementary feature on unseen outcomes.

## Data and code availability

The analysis code and Python package are maintained at https://github.com/siva-sub/strait-observatory. The source used for the numerical reproduction is `strait-observatory` 0.3.0rc1; this release candidate has not been uploaded to PyPI. The experimental interface checks raster grids, acquisition dates, declared radiometry, track metadata and valid support. Catalogue-only lineage requires an explicit conditional-use setting.

The package reproduces both the historical-index and physical-window prediction tables with a maximum difference below 10⁻⁸ kt. This tests numerical implementation on saved features, not the validity of the underlying vessel measurements. Source-to-result reproduction remains limited by the unavailable original cropped-image archive. Appendix B identifies the retained numerical inputs and outputs.

From the repository root:

```bash
python -m pip install -e './strait[dev]'
python -m pytest strait/tests -q
python experiments/strait-update/paper_metrics.py
python experiments/strait-update/reproduce.py
```

## Appendix A. Auxiliary in-sample comparisons

Adding total vessel arrivals to the historical presence index increases in-sample R² from 0.528 to 0.700 across 57 months. This model includes an official statistic and does not measure satellite-only performance.

The weather comparison examines the association after controlling for wind. On the 54 months with wind data, the count–sales correlation is 0.691; controlling for ERA5 wind gives a partial correlation of 0.696. The weather comparison is limited to this variable and sample. [A1]

**Table A1. In-sample model fit, with the estimation sample stated for each model.**

| Predictors | R² | Months |
|---|---:|---:|
| Historical presence index | 0.528 | 57 |
| Historical presence index + total vessel arrivals | 0.700 | 57 |
| Historical presence index, wind-complete sample | 0.478 | 54 |
| Historical presence index + ERA5 wind, same sample | 0.495 | 54 |

*Source: A1. These in-sample fits are separate from the nine-month retrospective comparison in Table 3.*

## Appendix B. Numerical provenance

Paths are relative to the repository root. The entries distinguish reproduction of saved statistical results from validation of the image measurements.

| ID | Inputs and analysis | Retained outputs |
|---|---|---|
| A1 | `experiments/results/perscene_counts.csv`; `experiments/results/perscene_join.csv`; `experiments/data/era5_wind_monthly.csv`; analysis in `experiments/strait-update/paper_metrics.py` | `experiments/strait-update/results/paper-metrics.json` |
| A2 | `experiments/strait-bounded-run/state/input-manifest.json`; `experiments/strait-bounded-run/benchmark.py`; `experiments/strait-bounded-run/checks.py` | In `experiments/strait-bounded-run/results/`: `summary.json`, `checks.json`, `scene-metrics.csv`, `pair-metrics.csv`, `monthly-panel.csv`, `oos-predictions.csv`, `original_index-predictions.csv`, `compact_detector-predictions.csv` |
| A3 | October 2023 Singapore AIS subset; aggregation and daily comparison in `experiments/strait-bounded-run/checks.py` | `experiments/strait-bounded-run/results/checks.json`; `experiments/strait-bounded-run/results/ais-daily-descriptive.csv` |
| A4 | Package numerical comparison in `experiments/strait-update/reproduce.py`; regression tests in `strait/tests/` | `experiments/strait-update/results/reproduction.json` |

## Sources

- **S1.** Cerdeiro, Komáromi, Liu and Sridhar (2020). *World Seaborne Trade in Real Time.* https://www.elibrary.imf.org/downloadpdf/journals/001/2020/057/001.2020.issue-057-en.xml
- **S2.** Jung (2026). *Watching Trade from Space: Measuring Maritime Trade Using Satellite Imagery.* arXiv:2604.15444v2. https://arxiv.org/abs/2604.15444v2 . Code: https://github.com/yonggeun-jung/watching_trade_public
- **S3.** Copernicus Data Space Ecosystem. *openEO processing* and *Sentinel-1 documentation.* https://documentation.dataspace.copernicus.eu/APIs/openEO/openeo_processing.html ; https://documentation.dataspace.copernicus.eu/Data/Sentinel1.html . Product catalogue: https://catalogue.dataspace.copernicus.eu/odata/v1/Products
- **S4.** data.gov.sg. *Bunker sales, monthly.* Resource `d_4f5abbf4486bf8e52bbed3be56dde562`. https://data.gov.sg/datasets/d_4f5abbf4486bf8e52bbed3be56dde562/view
- **S5.** data.gov.sg. *Vessel Arrivals (>75 GT) Total, Monthly.* Resource `d_d48c5a038904f6da3c603cd854b6c191`. https://data.gov.sg/datasets/d_d48c5a038904f6da3c603cd854b6c191/view
- **S6.** data.gov.sg. *Container throughput, monthly.* Resource `d_da030f7028200d19ffcbe4a2d71af39c`. https://data.gov.sg/datasets/d_da030f7028200d19ffcbe4a2d71af39c/view
- **S7.** Mendeley Data. *AIS Data from 11 ports around the globe.* DOI:10.17632/r37vwd493d.1. https://data.mendeley.com/datasets/r37vwd493d/1
- **S8.** Copernicus Climate Data Store. *ERA5.* https://cds.climate.copernicus.eu
