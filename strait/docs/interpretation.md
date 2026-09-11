# Interpreting results

A detected bright component is a **candidate**, not a verified vessel. Changing sensor grid, mask, radiometry or detector parameters changes the count scale. Historical preset names do not guarantee accuracy or recall.

- Compare coverage and observation counts before interpreting trends. A missing month is not zero activity.
- Apply calendar lags before dropping missing observations. Twelve retained rows need not be twelve months.
- Use exact same test dates and training folds for model comparisons. Correlation is not predictive skill.
- The legacy AIS matcher reports proximity fractions, not time-matched one-to-one accuracy. Receiver gaps, vessel movement and false detections all produce unmatched points. Do not label them dark vessels.
- Backscatter change includes weather, speckle and registration effects. It is not measured vessel turnover. Catalogue-only track labels do not prove actual source-product lineage.
- A non-significant result is not proof that a sensor or method cannot work.

In the bounded Singapore diagnostic, an add-on improved retrospective point estimates on nine already-inspected test months, but uncertainty included no gain. Evaluate the proposed addition on unseen outcomes before relying on the lower retrospective error. Numerical provenance is in the [paper](https://github.com/siva-sub/strait-observatory/blob/master/papers/singapore-strait-observatory.md).
