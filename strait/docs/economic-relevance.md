# Economic interpretation

The Singapore study compares satellite-observed vessel candidates in an eastern anchorage area with official marine-fuel sales. The satellite index measures sampled presence; sales accumulate across vessels and locations over a month.

Across 57 months, the historical count index has a correlation of 0.727 with bunker sales and an in-sample R² of 0.528. Year-over-year log changes give r=0.519 across 34 pairs. Adjacent-month log changes give r=0.180 across 52 pairs. These are different eligible samples, so the coefficients are descriptive comparisons of the relationship at those intervals.

Adding total vessel arrivals gives an in-sample R² of 0.700 on the same 57 months. That model includes an official statistic and cannot be described as satellite-only performance.

A separate retrospective comparison adds radar backscatter change to the historical index. On nine inspected test months, RMSE falls from 333.98 to 296.24 thousand tonnes, an 11.3% reduction. The paired uncertainty interval for the difference is [−68.6, +23.2] thousand tonnes. Performance on unseen outcomes and an operational publication-time advantage remain unestablished.

AIS tanker prevalence helps describe the study area. It does not identify individual fuel transactions. Annual VIIRS night lights provide context and are not part of the monthly estimation model.

## Sources

- [Working paper and numerical provenance](../../papers/singapore-strait-observatory.md)
- Official bunker sales: https://data.gov.sg/datasets/d_4f5abbf4486bf8e52bbed3be56dde562/view
- Local calculations: `experiments/strait-update/results/paper-metrics.json` and `experiments/strait-bounded-run/results/checks.json`
