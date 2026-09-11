#!/usr/bin/env python3
"""Run against an already installed local wheel directory, not the source import."""
import sys,tempfile,json,importlib.metadata
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
site=Path(sys.argv[1]).resolve();sys.path.insert(0,str(site))
import strait
from strait.experimental import SARFrame,temporal_change,expanding_compare
from rasterio.transform import from_origin
assert Path(strait.__file__).is_relative_to(site)
assert strait.__version__==importlib.metadata.version('strait-observatory')=='0.3.0rc1'
with tempfile.TemporaryDirectory() as td:
    c=strait.Cutout(module='demo',path=td,time=slice('2021-01','2021-03'),shape=(160,240))
    c.prepare(n_scenes=2);d=c.detect();a=c.aggregate(d)
    print('installed version',strait.__version__,'module',strait.__file__)
    print('synthetic demo',len(c._scenes),'scenes',len(d),'candidates',len(a),'periods')
kw=dict(transform=from_origin(0,20,10,10),crs='EPSG:32648',track='A-98-ASCENDING',radiometry='sigma0',lineage='verified')
a=SARFrame(np.ones((2,2)),acquired_at='2024-01-01',**kw)
b=SARFrame(np.ones((2,2))*2,acquired_at='2024-01-13',**kw)
assert abs(temporal_change(a,b)['mean_abs_db']-10*np.log10(2))<1e-6
p=pd.read_csv(ROOT/'experiments/strait-bounded-run/results/monthly-panel.csv',index_col=0);p.index=pd.to_datetime(p.index)
p['stock']=p.eopl.where(p.stock.notna())
r=expanding_compare(p.loc[:'2026-03'],target='bunker',features=['stock','movement'])
gold=pd.read_csv(ROOT/'experiments/strait-bounded-run/results/original_index-predictions.csv')
assert r.month.tolist()==gold.month.tolist()
err=float(np.max(abs(r.stock_movement.to_numpy()-gold.stock_movement.to_numpy())))
assert err<=1e-8
print('installed prediction oracle error',err,'kt;',len(r),'common test months')
print('PASS: metadata, isolated import, demo, change and prediction oracle')
