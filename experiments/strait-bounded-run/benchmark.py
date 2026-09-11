#!/usr/bin/env python3
"""Bounded, local-only SAR diagnostic. No downloads or remote processing.

This is NOT a replication of Jung: calibrated log-power absolute differences,
40 m area-mean grid, fixed land mask, catalogue-consistent same-track pairing.
Source-product lineage of openEO date mosaics is not retained. Movement results
are conditional diagnostics, not validated vessel turnover. Detector variants
are new algorithms, not replicas of the old neutral-fill/peak-splitting pipeline.
"""
import argparse, hashlib, json, math, os, re, time
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window, from_bounds
from rasterio.warp import transform_bounds, reproject, Resampling
from pyproj import Transformer
from scipy import ndimage, stats

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
RESULT=BASE/'results'; STATE=BASE/'state'; CACHE=BASE/'cache'
ZONE=(104.,1.24,104.35,1.40)
FACTOR=4
MIN_COVER=.80
MIN_TRAIN=12
PRIMARY_TRACK='A-98-ASCENDING'


def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [clean(v) for v in x]
    if isinstance(x,np.ndarray): return clean(x.tolist())
    if isinstance(x,(np.floating,float)): return float(x) if np.isfinite(x) else None
    if isinstance(x,np.integer): return int(x)
    if isinstance(x,np.bool_): return bool(x)
    return x

def dump(path,x):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    t=path.with_suffix(path.suffix+'.tmp');t.write_text(json.dumps(clean(x),indent=2,allow_nan=False));t.replace(path)

def valid_db(a,mask=None):
    a=np.asarray(a,np.float32)
    v=np.isfinite(a)&(a>0)
    if mask is not None:v &= mask
    d=np.full(a.shape,np.nan,np.float32)
    np.log10(a,out=d,where=v);d[v]*=10
    return d,v

def geo_window(transform,crs):
    if transform.b!=0 or transform.d!=0: raise ValueError('rotated grid unsupported')
    b=transform_bounds('EPSG:4326',crs,*ZONE,densify_pts=21)
    w=from_bounds(*b,transform=transform)
    # Align to 4-pixel blocks for a stable 40 m reduction grid.
    x0=math.floor(w.col_off/FACTOR)*FACTOR;y0=math.floor(w.row_off/FACTOR)*FACTOR
    x1=math.ceil((w.col_off+w.width)/FACTOR)*FACTOR;y1=math.ceil((w.row_off+w.height)/FACTOR)*FACTOR
    return Window(x0,y0,x1-x0,y1-y0)

def count_targets(db,valid,window,minpix):
    # Local moments conditional on valid water. Sufficient local support required.
    cnt=ndimage.uniform_filter(valid.astype(np.float32),size=window,mode='constant')
    a=np.where(valid,db,0).astype(np.float32)
    mu=ndimage.uniform_filter(a,size=window,mode='constant')/np.maximum(cnt,1e-6)
    sq=ndimage.uniform_filter(a*a,size=window,mode='constant')/np.maximum(cnt,1e-6)
    var=np.maximum(sq-mu*mu,0)
    bright=valid&(cnt>=.80)&(db>np.maximum(mu+5.5*np.sqrt(var),-12.))
    # Hard boundary/invalid-neighbor exclusion prevents nodata/shore edges counting.
    bright &= ndimage.binary_erosion(valid,iterations=1)
    lbl,n=ndimage.label(bright)
    sizes=np.bincount(lbl.ravel())[1:]
    return int(np.count_nonzero(sizes>=minpix)) if n else 0

def reduce_power(a,v,sea):
    h,w=a.shape; hh,ww=h//FACTOR,w//FACTOR
    def blocks(x):return x[:hh*FACTOR,:ww*FACTOR].reshape(hh,FACTOR,ww,FACTOR).sum(axis=(1,3))
    n=blocks(v.astype(np.float32)); expected=blocks(sea.astype(np.float32))
    summed=blocks(np.where(v,a,0))
    z=np.divide(summed,n,out=np.zeros_like(summed),where=n>0)
    db,vm=valid_db(z,(expected>0)&(n>=.95*expected))
    return db,expected

def change(a,b,weights):
    v=np.isfinite(a)&np.isfinite(b)&(weights>0)
    support=float(weights[v].sum());total=float(weights.sum())
    if not support:return {'coverage':0.,'mean_abs_db':None,'support_native_pixels':0}
    z=np.abs(b[v]-a[v]);q=weights[v]
    return {'coverage':support/total,'mean_abs_db':float(np.average(z,weights=q)),
            'exceed2_fraction':float(np.average(z>2,weights=q)),
            'support_native_pixels':support}

def pair_ok(a,b):
    dt=(pd.Timestamp(b['date'])-pd.Timestamp(a['date'])).days
    return bool(a.get('track') and a['track']==b.get('track') and a['grid']==b['grid']
                and a['date'][:7]==b['date'][:7] and 6<=dt<=24)

def calendar(f):
    f=f.copy();f.index=pd.to_datetime(f.index)
    return f.reindex(pd.date_range(f.index.min(),f.index.max(),freq='MS'))

def ridge_predict(train_y,train_x,test_x):
    train_x=np.asarray(train_x,float);test_x=np.asarray(test_x,float)
    mu=train_x.mean(axis=0);sd=train_x.std(axis=0);sd=np.where(sd>1e-9,sd,1.)
    x=(train_x-mu)/sd;q=(test_x-mu)/sd
    yc=np.asarray(train_y)-np.mean(train_y)
    beta=np.linalg.solve(x.T@x+np.eye(x.shape[1]),x.T@yc)
    return float(q@beta+np.mean(train_y))

def expanding(frame, train_start='2024-01-01'):
    f=calendar(frame)
    f['lag1']=f.bunker.shift(1);f['lag12']=f.bunker.shift(12)
    # Seasonal lag is a test comparator, not a requirement for fitting these models.
    fit=f[['stock','movement','bunker','lag1']].dropna().loc[train_start:]
    complete=f[['stock','movement','bunker','lag1','lag12']].dropna().loc[train_start:]
    rows=[]
    for d,row in complete.iterrows():
        train=fit.loc[fit.index<d]
        if len(train)<MIN_TRAIN:continue
        rec={'month':d.strftime('%Y-%m'),'actual':row.bunker,'n_train':len(train),
             'train_months':';'.join(train.index.strftime('%Y-%m')),
             'expanding_mean':float(train.bunker.mean()),'persistence':float(row.lag1),
             'seasonal12':float(row.lag12)}
        for label,cols in [('stock',['stock']),('stock_movement',['stock','movement']),
                           ('lag_stock',['lag1','stock']),('lag_stock_movement',['lag1','stock','movement'])]:
            rec[label]=ridge_predict(train.bunker.to_numpy(),train[cols].to_numpy(),row[cols].to_numpy())
        rows.append(rec)
    return pd.DataFrame(rows)

def track_map():
    p=STATE/'catalogue.json'
    if not p.exists():return {}
    d=json.loads(p.read_text());tracks=defaultdict(set)
    for row in d.get('value',[]):
        a={x['Name']:x.get('Value') for x in row.get('Attributes',[])}
        t=(a.get('platformSerialIdentifier'),a.get('relativeOrbitNumber'),a.get('orbitDirection'))
        if all(v is not None for v in t):tracks[row['ContentDate']['Start'][:10]].add('-'.join(map(str,t)))
    return {day:next(iter(ts)) if len(ts)==1 else None for day,ts in tracks.items()}

_GEOM={}
def geometry(src,win):
    tf=src.window_transform(win)
    key=str(src.crs)+str(tuple(tf))+str((int(win.height),int(win.width)))
    if key not in _GEOM:
        h,w=int(win.height),int(win.width)
        # Exact center membership in lon/lat, avoids the enclosing UTM rect bias.
        rr,cc=np.indices((h,w),dtype=np.float32)
        xx=tf.c+(cc+.5)*tf.a; yy=tf.f+(rr+.5)*tf.e
        lon,lat=Transformer.from_crs(src.crs,'EPSG:4326',always_xy=True).transform(xx,yy)
        inside=(lon>=ZONE[0])&(lon<=ZONE[2])&(lat>=ZONE[1])&(lat<=ZONE[3])
        land=np.full((h,w),255,np.uint8)
        with rasterio.open(ROOT/'experiments/data/s2coast/s2coast_sg_landmask.tif') as lm:
            reproject(rasterio.band(lm,1),land,src_transform=lm.transform,src_crs=lm.crs,
                      dst_transform=tf,dst_crs=src.crs,dst_nodata=255,resampling=Resampling.nearest)
        # Fixed 40m exclusion around land, not around the analysis zone itself.
        landbuffer=ndimage.binary_dilation(land!=0,iterations=4)
        sea=inside&~landbuffer
        _GEOM.clear()  # one grid expected, bounded RAM
        _GEOM[key]=(sea,hashlib.sha256(key.encode()).hexdigest(),float(abs(tf.a*tf.e)),
                    {'crs':str(src.crs),'transform':list(tf),'shape':[h,w],
                     'inside_pixels':int(inside.sum()),'sea_pixels':int(sea.sum()),
                     'land_or_buffer_fraction':float(1-sea.sum()/inside.sum())})
    return _GEOM[key]

def extract(seconds=480):
    start=time.monotonic();CACHE.mkdir(exist_ok=True);RESULT.mkdir(exist_ok=True)
    inventory=json.loads((STATE/'input-manifest.json').read_text());tracks=track_map()
    limit=0;done=0
    for item in inventory:
        if not item['eligible']:continue
        tag=item['date'];path=ROOT/item['path'];out=CACHE/(tag+'.json')
        if out.exists():done+=1;continue
        if time.monotonic()-start>seconds:limit=1;break
        rec={**item,'track':tracks.get(tag),'lineage':'catalogue_unique_track_not_asset_provenance'}
        try:
            st=path.stat()
            if st.st_size!=item['bytes'] or st.st_mtime_ns!=item['mtime_ns']:raise ValueError('input changed after freeze')
            with rasterio.Env(GDAL_CACHEMAX=128*1024*1024,GDAL_NUM_THREADS='1'):
                with rasterio.open(path) as src:
                    if src.descriptions[:2]!=('VV','VH'):raise ValueError('unexpected band labels')
                    if abs(src.res[0]-10)>.01 or abs(src.res[1]-10)>.01:raise ValueError('not 10m native grid')
                    win=geo_window(src.transform,src.crs)
                    sea,grid,pixarea,geom=geometry(src,win)
                    a=src.read(1,window=win,boundless=True,fill_value=0,out_dtype='float32')
                    mask=src.read_masks(1,window=win,boundless=True)>0
                    d,v=valid_db(a,mask&sea)
                    rec.update(grid=grid,geometry=geom,coverage=float(v.sum()/sea.sum()),
                               sea_area_km2=float(sea.sum()*pixarea/1e6),valid_area_km2=float(v.sum()*pixarea/1e6))
                    if rec['coverage']<MIN_COVER:
                        rec['status']='insufficient_valid_water'
                    else:
                        rec['status']='accepted'
                        rec['median_db']=float(np.median(d[v]))
                        # Both prespecified; no outcome-driven threshold search.
                        for name,w,mp in [('compact',64,3),('physical',237,41)]:
                            count=count_targets(d,v,w,mp)
                            rec[name+'_count']=count
                            rec[name+'_density']=count/rec['valid_area_km2']*100
                        coarse,weights=reduce_power(a,v,sea)
                        np.savez_compressed(CACHE/(tag+'.npz'),db=coarse,weights=weights)
                        rec['zone_array_sha256']=hashlib.sha256(a.tobytes()+v.tobytes()).hexdigest()
            dump(out,rec);done+=1
            print(tag,rec['status'],f"coverage={rec.get('coverage',0):.3f}",flush=True)
        except Exception as e:
            rec.update(status='read_or_metadata_error',error=str(e)[:300]);dump(out,rec);done+=1
            print(tag,rec['status'],rec['error'],flush=True)
    dump(RESULT/'extract-state.json',{'seconds':time.monotonic()-start,'checkpointed':done,
           'eligible':sum(x['eligible'] for x in inventory),'time_cap_reached':bool(limit),
           'imagery_download_bytes':0})
    print('EXTRACT',json.loads((RESULT/'extract-state.json').read_text()),flush=True)

def corr(x,y):
    s=pd.DataFrame({'x':x,'y':y}).replace([np.inf,-np.inf],np.nan).dropna()
    if len(s)<4 or s.x.nunique()<2 or s.y.nunique()<2:return {'n':len(s),'r':None}
    r,p=stats.pearsonr(s.x,s.y);rho=stats.spearmanr(s.x,s.y).statistic
    se=1/np.sqrt(len(s)-3);z=np.arctanh(r)
    return {'n':len(s),'r':float(r),'nominal_p_iid':float(p),'rho':float(rho),
            'fisher95_iid':np.tanh([z-1.96*se,z+1.96*se]).tolist()}

def ols_r2(y,x):
    y=np.asarray(y,float);x=np.asarray(x,float)
    # scale BEFORE least squares; raw large differences formerly ill-conditioned.
    x=(x-x.mean(0))/np.maximum(x.std(0),1e-12)
    X=np.column_stack([np.ones(len(y)),x]);b=np.linalg.lstsq(X,y,rcond=None)[0]
    return float(1-np.sum((y-X@b)**2)/np.sum((y-y.mean())**2))

def calendar_blocks(dates, length):
    months=pd.PeriodIndex(dates, freq='M').asi8
    blocks=[]
    for start in range(len(months)):
        stop=start+1
        while stop<len(months) and stop-start<length and months[stop]-months[stop-1]==1:
            stop+=1
        blocks.append(np.arange(start,stop))
    return blocks

def bootstrap_indices(rng, blocks, n):
    chosen=[];k=0
    while k<n:
        b=blocks[int(rng.integers(len(blocks)))];chosen.append(b);k+=len(b)
    return np.concatenate(chosen)[:n]

def rmse_report(pred):
    if pred.empty:return {'n_test':0,'status':'insufficient common training/test months'}
    y=pred.actual.to_numpy();out={'n_test':len(pred),'months':pred.month.tolist(),'models':{}}
    for c in ['expanding_mean','persistence','seasonal12','stock','stock_movement','lag_stock','lag_stock_movement']:
        e=pred[c].to_numpy()-y;out['models'][c]={'rmse_kt':float(np.sqrt(np.mean(e*e))),'mae_kt':float(np.mean(abs(e)))}
    # Paired sensitivity resampling; blocks STOP at actual calendar gaps and end.
    # With nine tests this is not a calibrated significance test.
    rng=np.random.default_rng(173);n=len(y);blocks=calendar_blocks(pred.month,min(3,n));draws=[]
    for _ in range(2000):
        idx=bootstrap_indices(rng,blocks,n)
        e0=(pred['stock'].to_numpy()-y)[idx];e1=(pred['stock_movement'].to_numpy()-y)[idx]
        draws.append(np.sqrt(np.mean(e1*e1))-np.sqrt(np.mean(e0*e0)))
    out['added_movement_rmse_delta95_kt']=np.quantile(draws,[.025,.975]).tolist()
    return out

def analyse():
    inv=json.loads((STATE/'input-manifest.json').read_text())
    recs=[json.loads(p.read_text()) for p in sorted(CACHE.glob('*.json'))]
    if not recs:raise ValueError('no cached scene records')
    df=pd.DataFrame([{k:v for k,v in r.items() if k!='geometry'} for r in recs])
    df.to_csv(RESULT/'scene-metrics.csv',index=False)
    good=[r for r in recs if r['status']=='accepted'];pairs=[]
    # No cross-month or cross-platform pairs; unique track inferred from catalogue only.
    groups=defaultdict(list)
    for r in good:
        if r.get('track'):groups[(r['date'][:7],r['track'],r['grid'])].append(r)
    for key,rs in groups.items():
        rs.sort(key=lambda r:r['date'])
        for a,b in zip(rs,rs[1:]):
            if not pair_ok(a,b):continue
            aa=np.load(CACHE/(a['date']+'.npz'));bb=np.load(CACHE/(b['date']+'.npz'))
            q=change(aa['db'],bb['db'],np.minimum(aa['weights'],bb['weights']))
            q.update(month=b['month'],date0=a['date'],date1=b['date'],track=b['track'],
                     dt_days=(pd.Timestamp(b['date'])-pd.Timestamp(a['date'])).days,
                     candidate_product_lineage_only=True)
            q['status']='accepted' if q['coverage']>=MIN_COVER else 'insufficient_shared_water'
            pairs.append(q)
    pair=pd.DataFrame(pairs);pair.to_csv(RESULT/'pair-metrics.csv',index=False)
    gm=pd.DataFrame(good)
    monthly=gm.groupby('month').agg(stock=('physical_density','mean'),compact=('compact_density','mean'),
             raw_stock=('physical_count','mean'),raw_compact=('compact_count','mean'),n_scenes=('date','nunique'),coverage=('coverage','mean'))
    monthly.loc[monthly.n_scenes<2,['stock','compact','raw_stock','raw_compact']]=np.nan
    # Primary count/change comparison uses the exact endpoint scenes of accepted
    # primary-track pairs; retain all-track stock only as labelled sensitivity.
    monthly=monthly.rename(columns={c:'all_tracks_'+c for c in ['stock','compact','raw_stock','raw_compact','n_scenes','coverage']})
    if len(pair):
        eligible=pair[(pair.status=='accepted')&(pair.track==PRIMARY_TRACK)]
        endpoints=set(eligible.date0)|set(eligible.date1)
        matched=gm[gm.date.isin(endpoints)]
        sm=matched.groupby('month').agg(stock=('physical_density','mean'),compact=('compact_density','mean'),
             raw_stock=('physical_count','mean'),raw_compact=('compact_count','mean'),n_scenes=('date','nunique'),coverage=('coverage','mean'))
        monthly=monthly.join(sm)
        mov=eligible.groupby('month').agg(movement=('mean_abs_db','median'),n_pairs=('date1','size'),pair_coverage=('coverage','mean'))
        monthly=monthly.join(mov)
        for tr in sorted(pair.track.unique()):
            q=pair[(pair.status=='accepted')&(pair.track==tr)].groupby('month').mean_abs_db.median()
            monthly=monthly.join(q.rename('movement_'+tr))
    for c in ['movement','stock','compact','raw_stock','raw_compact','n_scenes','coverage']:
        if c not in monthly:monthly[c]=np.nan
    original=pd.read_csv(ROOT/'experiments/results/perscene_join.csv',index_col=0)
    panel=calendar(monthly.join(original[['eopl','bunker','container','arrivals']],how='outer'))
    panel.index.name='month';panel.to_csv(RESULT/'monthly-panel.csv')
    # Model assessment excludes Oct2023: AIS-only window and isolated early data.
    target=panel.loc['2024-01':'2026-03'];common=target.dropna(subset=['stock','compact','movement','bunker','eopl'])
    out={'metric_units':{'stock':'new detector candidates / 100 km2 valid sea','movement':'mean absolute VV dB difference on 40m grid'},
         'primary_track':PRIMARY_TRACK,'n_frozen':len(inv),'n_eligible':sum(x['eligible'] for x in inv),
         'accepted_scenes':len(good),'scene_status_counts':df.status.value_counts().to_dict(),
         'target_window':['2024-01','2026-03'],'expected_months':27,
         'paired_months':common.index.strftime('%Y-%m').tolist(),'n_common':len(common),
         'missing_common_months':target.index.difference(common.index).strftime('%Y-%m').tolist(),
         'pair_status_counts':pair.status.value_counts().to_dict() if len(pair) else {},
         'primary_lineage_status':'CONDITIONAL: unique catalogue track, not verified asset source-product lineage',
         'comparisons':{}}
    for label,c in [('new_stock','stock'),('compact_stock','compact'),('change','movement'),('original_stock','eopl')]:
        out['comparisons'][label]=corr(common[c],common.bunker)
    out['processing_agreement_on_common']=corr(common.stock,common.eopl)
    out['processing_agreement_compact']=corr(common.compact,common.eopl)
    if len(common)>5:
        r2=ols_r2(common.bunker,common[['stock']]);r2m=ols_r2(common.bunker,common[['stock','movement']])
        out['in_sample_r2']={'stock':r2,'stock_movement':r2m,'delta':r2m-r2}
    # Diffs on FULL calendar before dropping rows (not observation lag).
    dif=target[['stock','movement','bunker']].diff(12)
    out['calendar_yoy_diagnostics']={c:corr(dif[c],dif.bunker) for c in ['stock','movement']}
    out['secondary_target_associations']={c:corr(common.movement,common[c]) for c in ['container','arrivals']}
    # Histories are valid raw target months, even when satellites are unavailable.
    pred=expanding(panel[['stock','movement','bunker']].loc[:'2026-03'])
    pred.to_csv(RESULT/'oos-predictions.csv',index=False)
    out['retrospective_expanding_test']=rmse_report(pred)
    # Track sensitivity: descriptive only. Do not choose best orbit against outcome.
    out['track_sensitivity']={c:corr(target[c],target.bunker) for c in target.columns if c.startswith('movement_')}
    dump(RESULT/'summary.json',out)
    print(json.dumps(clean(out),indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['extract','analyse']);p.add_argument('--seconds',type=int,default=480)
    args=p.parse_args()
    if args.command=='extract':extract(args.seconds)
    else:analyse()
