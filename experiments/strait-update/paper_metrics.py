#!/usr/bin/env python3
"""Deterministic paper update from retained CSVs; no downloads, no target tuning."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from scipy import stats
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent/'results'


def pair_stats(f,x,y):
    q=f[[x,y]].replace([np.inf,-np.inf],np.nan).dropna()
    r,p=stats.pearsonr(q[x],q[y]);rho=stats.spearmanr(q[x],q[y]).statistic
    return dict(n=len(q),r=float(r),rho=float(rho),nominal_iid_p=float(p))


def fit(f,target,features):
    q=f[[target]+features].dropna();x=q[features].to_numpy(float);y=q[target].to_numpy(float)
    x=(x-x.mean(0))/x.std(0);x=np.column_stack([np.ones(len(x)),x])
    beta=np.linalg.lstsq(x,y,rcond=None)[0];res=y-x@beta
    return dict(n=len(q),r2=float(1-(res@res)/np.sum((y-y.mean())**2)),predictors=features)


def main():
    j=ROOT/'experiments/results/perscene_join.csv';m=pd.read_csv(j,index_col=0);m.index=pd.to_datetime(m.index)
    assert m.index.is_unique
    m=m.reindex(pd.date_range(m.index.min(),m.index.max(),freq='MS'))
    variables=['eopl','bunker','arrivals','container'];v=m[variables]
    log=np.log(v.where(v>0));yoy=log.diff(12);mom=log.diff(1)
    pct=v.pct_change(12,fill_method=None)
    o=dict(source=str(j.relative_to(ROOT)),sha256=hashlib.sha256(j.read_bytes()).hexdigest(),
           headline={y:pair_stats(v,'eopl',y) for y in ['bunker','arrivals','container']},
           calendar_yoy_log={y:pair_stats(yoy,'eopl',y) for y in ['bunker','arrivals','container']},
           calendar_yoy_pct={y:pair_stats(pct,'eopl',y) for y in ['bunker','arrivals','container']},
           calendar_mom_log={y:pair_stats(mom,'eopl',y) for y in ['bunker','arrivals','container']},
           post2021=pair_stats(v.loc['2021-01':],'eopl','bunker'))
    # Historical row-based statistic preserved explicitly, not called year-over-year.
    sparse=v.dropna(subset=['eopl','bunker'])
    o['legacy_observation_lag12_pct']=pair_stats(sparse.pct_change(12,fill_method=None),'eopl','bunker')
    w=pd.read_csv(ROOT/'experiments/data/era5_wind_monthly.csv',index_col=0);w.index=pd.to_datetime(w.index)
    mw=v.join(w);col='era5_wind_ms';c=mw[['eopl','bunker',col]].dropna()
    rx=stats.pearsonr(c.eopl,c[col]).statistic;ry=stats.pearsonr(c.bunker,c[col]).statistic;r=stats.pearsonr(c.eopl,c.bunker).statistic
    o['wind']={'n':len(c),'raw_r':r,'partial_r':float((r-rx*ry)/np.sqrt((1-rx*rx)*(1-ry*ry)))}
    o['fusion']={'satellite_full':fit(v,'bunker',['eopl']),
       'total_arrivals_full':fit(v,'bunker',['eopl','arrivals']),
       'wind_common_satellite':fit(c,'bunker',['eopl']),
       'wind_common_combined':fit(c,'bunker',['eopl',col])}
    # Explicit exclusions, complete calendar before transformations.
    outside=~v.index.to_series().between('2020-01-01','2021-12-31').to_numpy()
    o['exclude_2020_2021_levels']=pair_stats(v.loc[outside],'eopl','bunker')
    counts=pd.read_csv(ROOT/'experiments/results/perscene_counts.csv',dtype={'day':str})
    ok=counts[counts.status=='OK'];o['counts']={'rows':len(counts),'accepted':len(ok),
       'since2021':int((ok.day.str[:4].astype(int)>=2021).sum()),'unique_days':ok.day.nunique(),
       'accepted_by_year':ok.day.str[:4].value_counts().sort_index().to_dict()}
    # Verify no unsupported observation is silently presented as a one-year lag.
    assert o['headline']['bunker']['n']==57 and o['calendar_yoy_log']['bunker']['n']==34
    OUT.mkdir(exist_ok=True);(OUT/'paper-metrics.json').write_text(json.dumps(o,indent=2,allow_nan=False))
    print(json.dumps(o,indent=2))

if __name__=='__main__':main()
