# Data sources

The package works with prepared local images, land masks, AIS records and economic time series. Acquisition services are separate from the package. Choose a bounded area and date range, and record source identifiers before processing.

## Sentinel-1 radar imagery

Copernicus Sentinel-1 imagery is the primary input to the Singapore study. The detector uses VV backscatter from processed Ground Range Detected imagery. A display image or an uncalibrated array is not an equivalent input.

Keep the acquisition time, source-product identifiers, orbit, coordinate reference system, affine transform and calibrated-power convention with each image. The basic `Cutout` cache expects aligned EPSG:4326 GeoTIFFs with calibrated linear sigma0 values and full dates in filenames. The experimental reader supports native projected grids and requires an explicit radiometric convention. Neither reader infers an image's physical calibration from its pixel values.

The Copernicus catalogue, Browser and openEO documentation describe acquisition and processing options. Service permissions and quotas depend on the route used; access to a catalogue does not establish access to a processing service. The research repository contains acquisition scripts, but they are outside the package and do not constitute a supported download client.

- Catalogue: https://catalogue.dataspace.copernicus.eu/odata/v1/Products
- Browser: https://browser.dataspace.copernicus.eu
- Processing documentation: https://documentation.dataspace.copernicus.eu/APIs/openEO/openeo_processing.html

NoData and nonpositive power must be excluded before conversion to decibels. In the processing service used for the paired-image study, zero can also arise from thermal-noise removal. Treating it as a faint radar return changes the measurement.

## Land and water masks

A land mask defines which pixels enter the detector. It must match the image grid. In the local cache, zero denotes water; nonzero values and invalid mask cells are excluded.

The historical Singapore count series used a temporal-median mask. The paired-image study used a coastline mask based on S2Coast-2023 with a shore buffer. These are distinct measurement definitions; the historical index was not rebuilt under the coastline mask.

A temporal-median mask can also exclude persistent bright returns on water. A coastline mask needs appropriate handling of shoreline position, buffers and resampling. Inspect either mask against its intended area before interpreting candidate counts.

S2Coast-2023 source record: https://zenodo.org/records/17092775

## AIS observations

AIS reports describe vessel identifiers, positions and reported attributes. They can support contextual analysis or acquisition-matched validation, provided their temporal and spatial coverage is understood.

The Singapore study uses the October 2023 subset of *AIS Data from 11 ports around the globe*. Daily unions of reported identifiers are compared descriptively with radar snapshots. They are not one-to-one detection labels.

`AISMatch(source="file")` accepts the package's local JSON format. Historical CSVs and provider feeds need separate preparation. Preserve report timestamps, handle duplicate records explicitly and inspect receiver coverage. An unmatched radar candidate can result from a false detection, movement between observations or a reporting gap; it does not establish deliberate AIS deactivation.

Historical data, DOI 10.17632/r37vwd493d.1: https://data.mendeley.com/datasets/r37vwd493d/1

## Official monthly statistics

Match the economic quantity, geographic scope, reporting month and units before joining a series to satellite observations. Retain the downloaded snapshot and any revision information. The Singapore analysis uses:

| Series | Resource ID | Role |
|---|---|---|
| Monthly bunker sales | `d_4f5abbf4486bf8e52bbed3be56dde562` | Primary target: marine-fuel sales |
| Total vessel arrivals above 75 GT | `d_d48c5a038904f6da3c603cd854b6c191` | Secondary association and in-sample predictor |
| Monthly container throughput | `d_da030f7028200d19ffcbe4a2d71af39c` | Secondary association |

Bunker sales are expressed in thousand tonnes in the study tables. The `arrivals` field contains total arrivals, not tanker-only arrivals. These Singapore-wide series have broader geographic coverage than the eastern satellite analysis rectangle.

## Contextual data

ERA5 wind is used in an auxiliary statistical comparison. Selected annual VIIRS night-light rasters provide context but are not inputs to the monthly count-plus-change model. Annual imagery should not be described as independent validation of a monthly fuel-sales estimate.

## Sources

- Bunker sales: https://data.gov.sg/datasets/d_4f5abbf4486bf8e52bbed3be56dde562/view
- Vessel arrivals: https://data.gov.sg/datasets/d_d48c5a038904f6da3c603cd854b6c191/view
- Container throughput: https://data.gov.sg/datasets/d_da030f7028200d19ffcbe4a2d71af39c/view
- ERA5: https://cds.climate.copernicus.eu
- VIIRS: https://eogdata.mines.edu/products/vnl/
- Study methods and numerical provenance: [working paper](../../papers/singapore-strait-observatory.md)
