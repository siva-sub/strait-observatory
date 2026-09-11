#!/usr/bin/env python3
"""Package-vs-frozen-benchmark oracle. Reproduce predictions, not retune them."""
from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'strait'))
from strait.experimental import expanding_compare

B=ROOT/'experiments/strait-bounded-run/results';O=Path(__file__).parent/'results'
O.mkdir(parents=True,exist_ok=True)
f=pd.read_csv(B/'monthly-panel.csv',index_col=0);f.index=pd.to_datetime(f.index)
rows=[]
for label,feature,ref in [('physical','stock','oos-predictions.csv'),('original','eopl','original_index-predictions.csv')]:
    q=f[['stock','movement','bunker']].copy();q['stock']=f[feature].where(f.stock.notna())
    pred=expanding_compare(q.loc[:'2026-03'],target='bunker',features=['stock','movement'])
    old=pd.read_csv(B/ref)
    assert pred.month.tolist()==old.month.tolist()
    assert pred.train_months.tolist()==old.train_months.tolist()
    numeric=['actual','n_train','expanding_mean','persistence','seasonal12','stock','stock_movement','lag_stock','lag_stock_movement']
    error=float(np.max(abs(pred[numeric].to_numpy(float)-old[numeric].to_numpy(float))))
    assert error<=1e-8,(label,error)
    pred.to_csv(O/(label+'-package-predictions.csv'),index=False)
    rows.append({'variant':label,'n_test':len(pred),'max_abs_error_kt':error,
                 'prediction_oracle':'PASS','original_artifact':str((B/ref).relative_to(ROOT)),
                 'rmse_base_kt':float(np.sqrt(np.mean((pred.stock-pred.actual)**2))),
                 'rmse_augmented_kt':float(np.sqrt(np.mean((pred.stock_movement-pred.actual)**2)))})
(O/'reproduction.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
