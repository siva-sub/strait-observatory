#!/usr/bin/env python3
"""Secondary fixed checks: original-series comparator, compact-detector sensitivity,
paired predictive uncertainty, and descriptive daily AIS. No downloads."""
import importlib.util,json
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats
spec=importlib.util.spec_from_file_location('b',Path(__file__).with_name('benchmark.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
P=b.RESULT
panel=pd.read_csv(P/'monthly-panel.csv',index_col=0);panel.index=pd.to_datetime(panel.index)
primary=pd.read_csv(P/'oos-predictions.csv')
out={'notes':['Diagnostic post-test checks; no model selection based on these results.',
              'Old index was designed on these data; no uncontaminated holdout.',
              'AIS daily unique presence differs from instantaneous SAR scene counts. Not precision/recall.']}

# Same missingness, same training rules and test dates, original and compact counts.
for name,col in [('original_index','eopl'),('compact_detector','compact')]:
    f=panel[['stock','movement','bunker']].copy();f['stock']=panel[col].where(panel.stock.notna())
    pred=b.expanding(f.loc[:'2026-03'])
    assert pred.month.tolist()==primary.month.tolist(), 'unequal test months'
    assert pred.train_months.tolist()==primary.train_months.tolist(), 'unequal training folds'
    pred.to_csv(P/(name+'-predictions.csv'),index=False)
    out[name]=b.rmse_report(pred)

# Compare *actual squared errors*, not the in-sample correlation. Report block intervals.
y=primary.actual.to_numpy()
def paired_interval(a,c,block):
    rng=np.random.default_rng(175+block);n=len(y);vals=[]
    blocks=b.calendar_blocks(primary.month,block)
    for _ in range(2000):
        ix=b.bootstrap_indices(rng,blocks,n)
        vals.append(np.sqrt(np.mean((a[ix]-y[ix])**2))-np.sqrt(np.mean((c[ix]-y[ix])**2)))
    return np.quantile(vals,[.025,.975]).tolist()
original=pd.read_csv(P/'original_index-predictions.csv')
comp=primary.stock_movement.to_numpy()
out['combined_vs_comparators']={}
for name,q in [('new_stock',primary.stock.to_numpy()),('persistence',primary.persistence.to_numpy()),('original_stock',original.stock.to_numpy())]:
    err=comp-y;err0=q-y
    rmse=float(np.sqrt(np.mean(err**2)));rmse0=float(np.sqrt(np.mean(err0**2)))
    out['combined_vs_comparators'][name]={'rmse_reduction_fraction':1-rmse/rmse0,
        'paired_error_block2_delta95_kt':paired_interval(comp,q,2),
        'paired_error_block3_delta95_kt':paired_interval(comp,q,3),
        'paired_error_block4_delta95_kt':paired_interval(comp,q,4),
        'months_lower_absolute_error':int(np.sum(abs(err)<abs(err0))),
        'leave_one_test_month_out_rmse_delta_range_kt':[
           float(min(np.sqrt(np.mean(np.delete(err,i)**2))-np.sqrt(np.mean(np.delete(err0,i)**2)) for i in range(len(y)))),
           float(max(np.sqrt(np.mean(np.delete(err,i)**2))-np.sqrt(np.mean(np.delete(err0,i)**2)) for i in range(len(y))))]}

# Direct improvement question: add the new change feature to the ORIGINAL index.
orig_plus=original.stock_movement.to_numpy();orig_only=original.stock.to_numpy()
out['original_plus_change']={
    'rmse_reduction_fraction':1-np.sqrt(np.mean((orig_plus-y)**2))/np.sqrt(np.mean((orig_only-y)**2)),
    'paired_block3_delta95_kt':paired_interval(orig_plus,orig_only,3),
    'paired_vs_persistence_block3_delta95_kt':paired_interval(orig_plus,primary.persistence.to_numpy(),3),
    'better_abs_error_months':int(np.sum(abs(orig_plus-y)<abs(orig_only-y)))
}

# Same raw Mendeley dataset, one explicitly defined daily series (UTC rounded-time day).
raw=b.ROOT/'experiments/data/ais_historical/anon_data/Singapore_anonymized.csv'
if raw.exists():
    ais=pd.read_csv(raw,usecols=['MMSI','Latitude','Longitude','NavigationalStatus','Rounded_time','ShipType'])
    ais['day']=pd.to_datetime(ais.Rounded_time,utc=True).dt.strftime('%Y-%m-%d')
    all_days=sorted(ais.day.unique())
    z=ais[ais.Longitude.between(b.ZONE[0],b.ZONE[2])&ais.Latitude.between(b.ZONE[1],b.ZONE[3])]
    anchored=z[z.NavigationalStatus==1]
    daily=anchored.groupby('day').MMSI.nunique().rename('ais_daily_anchored_unique')
    sar=pd.read_csv(P/'scene-metrics.csv');sar=sar[(sar.status=='accepted')&sar.date.str.startswith('2023-10')]
    compais=sar[['date','compact_count','physical_count','coverage']].merge(daily,left_on='date',right_index=True,how='left')
    compais.to_csv(P/'ais-daily-descriptive.csv',index=False)
    out['ais_daily']={'source_raw_rows':len(ais),'eastern_box_unique':int(z.MMSI.nunique()),
        'anchored_reports':len(anchored),'tanker_share_reports':float(anchored.ShipType.between(80,89).mean()),
        'accepted_oct_sar_scenes':len(sar),'n_date_matches':int(compais.ais_daily_anchored_unique.notna().sum()),
        'scope':'whole-day unique anchored vessels vs scene candidate counts; different spatial support due SAR land+nodata masks; descriptive only',
        'compact_correlation':b.corr(compais.compact_count,compais.ais_daily_anchored_unique),
        'physical_correlation':b.corr(compais.physical_count,compais.ais_daily_anchored_unique)}
else:out['ais_daily']={'status':'blocked: raw AIS not present'}

# Derivation checks on held-out predictions and fold chronology.
assert (primary.n_train>=b.MIN_TRAIN).all()
for row in primary.itertuples():assert all(d<row.month for d in row.train_months.split(';'))
assert np.isfinite(primary[['actual','stock','stock_movement','persistence']].to_numpy()).all()
out['fold_checks']='passed: future dates excluded, equal comparator folds, finite predictions'
b.dump(P/'checks.json',out)
print(json.dumps(b.clean(out),indent=2))
