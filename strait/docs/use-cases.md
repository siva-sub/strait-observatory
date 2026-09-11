# Use cases and limits

## Candidate presence series

Use a consistent raster grid, explicit land mask and detector settings to construct per-acquisition candidate counts. Keep a separate scene inventory. Monthly means, valid-area-normalized counts and detection-row totals are different quantities. The package's basic aggregator supplies the last of these.

## Backscatter-change diagnostics

`SARFrame` and `temporal_change` require comparable grids, track, radiometry and acquisition times. Verified source-product lineage is required by default; a catalogue-only override is explicitly conditional. The result describes change in the radar return, not ships moving.

## Retrospective economic comparison

`expanding_compare` evaluates a base index and one additional feature with shared chronological folds and calendar-based history baselines. It does not select a model by maximizing observed correlation. A future release schedule and a locked holdout are needed for operational nowcasting.

## AIS proximity screening

The legacy `AISMatch` accepts local JSON snapshots. Use the resulting proximity fractions to inspect matches. Vessel identities and detection accuracy require one-to-one acquisition-time labels and a record of receiver coverage.

## Scope

The Singapore study evaluates candidate counts and economic associations. Operational forecasting, vessel-level enforcement and applications at other ports need separate evidence. See [interpretation](interpretation.md) and [API reference](api-reference.md).
