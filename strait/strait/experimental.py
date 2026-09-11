"""Experimental local SAR change and retrospective model comparison.

No remote service calls. No claim of detected vessel turnover, prediction lead,
or independent ground truth. Acquisition lineage is fail-closed by default;
only an explicit catalogue-only override permits a conditional diagnostic.
"""
from dataclasses import dataclass
from typing import Optional
import math

import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds


@dataclass(frozen=True)
class SARFrame:
    """An explicit calibrated-power observation on its native grid.

    ``track`` must identify platform, relative orbit and orbit direction.
    ``lineage`` is 'verified', 'catalogue', or 'unknown'. 'Verified' is a caller
    assertion about actual source products, not something this class establishes.
    Set ``valid`` to False at land/cloud/NoData pixels; nonpositive/nonfinite
    power is always invalid. ``radiometry`` is 'sigma0' or 'gamma0'.
    """
    power: np.ndarray
    transform: Affine
    crs: object
    acquired_at: object
    track: Optional[str]
    radiometry: str
    lineage: str = 'unknown'
    valid: Optional[np.ndarray] = None

    def __post_init__(self):
        power=np.array(self.power,dtype=np.float32,copy=True)
        if power.ndim!=2 or not power.size:
            raise ValueError('power must be a nonempty two-dimensional array')
        crs=CRS.from_user_input(self.crs)
        if (not isinstance(self.transform,Affine) or not np.isfinite(tuple(self.transform)).all()
                or self.transform.a<=0 or self.transform.e>=0):
            raise ValueError('a finite north-up affine transform is required')
        if self.transform.b!=0 or self.transform.d!=0:
            raise ValueError('rotated/sheared grids are not supported')
        import re
        import datetime
        if isinstance(self.acquired_at,str):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[ T].*)?",self.acquired_at):
                raise ValueError('acquisition date must be an absolute ISO date')
        elif not isinstance(self.acquired_at,(pd.Timestamp,np.datetime64,datetime.date)):
            raise ValueError('acquisition date must be an absolute date, not a numeric epoch')
        acquired=pd.Timestamp(self.acquired_at)
        if pd.isna(acquired):raise ValueError('acquisition date is required')
        if acquired.tz is not None:acquired=acquired.tz_convert('UTC').tz_localize(None)
        if self.radiometry not in ('sigma0','gamma0'):
            raise ValueError('declare calibrated linear radiometry: sigma0 or gamma0')
        if self.lineage not in ('verified','catalogue','unknown'):
            raise ValueError('lineage must be verified, catalogue, or unknown')
        valid=np.ones(power.shape,bool) if self.valid is None else _bool_mask(self.valid,power.shape)
        valid=valid & np.isfinite(power) & (power>0)
        power.setflags(write=False);valid.setflags(write=False)
        for name,value in [('power',power),('valid',valid),('crs',crs),('acquired_at',acquired)]:
            object.__setattr__(self,name,value)


def _bool_mask(mask, shape):
    a=np.asarray(mask)
    if a.shape!=shape or a.dtype.kind not in 'bifu' or not np.isfinite(a).all() or not np.isin(a,[0,1]).all():
        raise ValueError('mask must match the grid and contain finite boolean/0/1 values')
    return np.array(a,dtype=bool,copy=True)


def read_power_window(path, bounds, *, acquired_at, track, radiometry,
                      lineage='unknown', band=1, max_pixels=8_000_000):
    """Read a WGS84 bounding window from a trusted self-contained local GeoTIFF.

    Returns SARFrame. No land mask is inferred. Partly outside raster pixels stay
    invalid. A bounded pixel budget prevents accidentally loading a full swath.
    """
    if len(bounds)!=4 or not (-180<=bounds[0]<bounds[2]<=180 and -90<=bounds[1]<bounds[3]<=90):
        raise ValueError('bounds must be ordered WGS84 coordinates')
    if not isinstance(max_pixels,(int,np.integer)) or max_pixels<=0:
        raise ValueError('max_pixels must be a positive finite integer')
    from pathlib import Path
    from urllib.parse import urlparse
    value=str(path)
    if urlparse(value).scheme or value.startswith('/vsi'):
        raise ValueError('only local filesystem rasters are supported')
    path=Path(path).expanduser()
    if not path.is_file():raise FileNotFoundError(f'local raster does not exist: {path}')
    # A local VRT can reference a remote source. Refuse it even with a .tif name.
    with path.open('rb') as fh:magic=fh.read(4)
    if magic not in (b'II*\x00',b'MM\x00*',b'II+\x00',b'MM\x00+'):
        raise ValueError('local reader requires a self-contained GeoTIFF, not VRT or another driver')
    with rasterio.open(path, driver='GTiff') as src:
        if src.crs is None:raise ValueError('raster CRS is required')
        if src.transform.b!=0 or src.transform.d!=0:raise ValueError('rotated grid unsupported')
        b=transform_bounds('EPSG:4326',src.crs,*bounds,densify_pts=21)
        w=from_bounds(*b,transform=src.transform)
        x0,y0=math.floor(w.col_off),math.floor(w.row_off)
        x1,y1=math.ceil(w.col_off+w.width),math.ceil(w.row_off+w.height)
        if (x1-x0)*(y1-y0)>max_pixels:raise ValueError('requested window exceeds max_pixels budget')
        w=Window(x0,y0,x1-x0,y1-y0)
        a=src.read(band,window=w,boundless=True,fill_value=0,out_dtype='float32')
        valid=src.read_masks(band,window=w,boundless=True)>0
        return SARFrame(a,src.window_transform(w),src.crs,acquired_at,track,radiometry,lineage,valid)


def temporal_change(before, after, *, min_coverage=.8, min_days=6, max_days=24,
                    support=None, allow_catalogue=False):
    """Mean absolute dB difference on shared valid pixels of comparable frames.

    Does not reproject or coregister. Reject incompatible grids/tracks/radiometry,
    cross-month pairs, duplicate/reversed dates and insufficient metadata. An
    explicit catalogue-only override labels the result conditional, never verified.
    ``support`` is a fixed boolean mask such as valid ocean; coverage is relative
    to it, not relative only to the pixels surviving in both frames.
    """
    if not 0<min_coverage<=1 or not 0<min_days<=max_days:
        raise ValueError('invalid coverage or acquisition-gap bounds')
    if before.power.shape!=after.power.shape or before.crs!=after.crs or before.transform!=after.transform:
        raise ValueError('pair must share exactly the same grid')
    if not before.track or before.track!=after.track:raise ValueError('pair track mismatch or missing')
    if before.radiometry!=after.radiometry:raise ValueError('pair radiometry mismatch')
    days=(after.acquired_at-before.acquired_at).total_seconds()/86400
    if before.acquired_at.to_period('M')!=after.acquired_at.to_period('M') or not min_days<=days<=max_days:
        raise ValueError('pair dates must be ordered, same-month and within gap bounds')
    if before.lineage==after.lineage=='verified':status='accepted'
    elif allow_catalogue and before.lineage in ('verified','catalogue') and after.lineage in ('verified','catalogue'):
        status='conditional'
    else:raise ValueError('actual source-product lineage required; catalogue override must be explicit')
    s=np.ones(before.power.shape,bool) if support is None else _bool_mask(support,before.power.shape)
    if s.shape!=before.power.shape or not s.any():raise ValueError('support must be nonempty and match grid')
    v=s&before.valid&after.valid;n=int(v.sum());coverage=float(n/s.sum())
    result=dict(status=status,coverage=coverage,valid_pixels=n,days=days,
                mean_abs_db=None,interpretation='backscatter change, not vessel turnover')
    if coverage<min_coverage or not n:result['status']='insufficient_shared_support';return result
    change=np.abs(10*np.log10(after.power[v])-10*np.log10(before.power[v]))
    result['mean_abs_db']=float(np.mean(change));return result


def monthly_calendar(frame):
    """Unique, month-start numeric panel, reindexed without filling data gaps."""
    f=frame.copy()
    if len(f)==0:raise ValueError('monthly panel is empty')
    if isinstance(f.index,pd.PeriodIndex):ix=f.index.asfreq('M').to_timestamp()
    else:
        import re
        import datetime
        for v in f.index:
            if isinstance(v,str):
                if not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2}(?:[ T].*)?)?",v):
                    raise ValueError('index needs fixed calendar month/date values')
            elif not isinstance(v,(pd.Timestamp,np.datetime64,datetime.date)):
                raise ValueError('index needs fixed calendar month/date values')
        ix=pd.to_datetime(f.index,errors='raise')
        if ix.tz is not None:ix=ix.tz_convert('UTC').tz_localize(None)
        ix=ix.to_period('M').to_timestamp()
    if ix.hasnans or ix.duplicated().any():raise ValueError('missing or duplicate calendar month')
    f.index=ix;f=f.sort_index()
    try:f=f.astype(float)
    except (TypeError,ValueError) as e:raise ValueError('panel must be numeric') from e
    if np.isinf(f.to_numpy()).any():raise ValueError('infinite panel values not supported')
    return f.reindex(pd.date_range(f.index.min(),f.index.max(),freq='MS'))


def _ridge_predict(y,x,test_x,penalty):
    x=np.asarray(x,float);test_x=np.asarray(test_x,float)
    mu=x.mean(0);sd=x.std(0);sd=np.where(sd>1e-9,sd,1.)
    x=(x-mu)/sd;q=(test_x-mu)/sd;yc=np.asarray(y)-np.mean(y)
    beta=np.linalg.solve(x.T@x+penalty*np.eye(x.shape[1]),x.T@yc)
    return float(q@beta+np.mean(y))


def expanding_compare(frame, *, target, features, train_start='2024-01-01',
                      min_train=12, penalty=1.0):
    """Two-feature retrospective comparison on identical folds and test months.

    ``features`` supplies [count_or_original_index, change_feature]. Current-month
    features are permitted, so this is NOT necessarily a forecast or timely nowcast.
    Models and baselines are evaluated only where all are defined. Predictor names
    in output are stable labels: stock, stock_movement, lag_stock and
    lag_stock_movement. Missing months remain NaN; lag1/lag12 use calendar offsets.
    """
    if len(features)!=2 or len(set(features))!=2 or target in features:
        raise ValueError('two distinct features, separate from target, required')
    if min_train<3 or not np.isfinite(penalty) or penalty<=0:
        raise ValueError('min_train>=3 and positive finite ridge penalty required')
    f=monthly_calendar(frame[[target]+list(features)]).rename(columns={target:'bunker',features[0]:'stock',features[1]:'movement'})
    f['lag1']=f.bunker.shift(1);f['lag12']=f.bunker.shift(12)
    fit=f[['stock','movement','bunker','lag1']].dropna().loc[train_start:]
    test=f[['stock','movement','bunker','lag1','lag12']].dropna().loc[train_start:]
    rows=[]
    for d,row in test.iterrows():
        tr=fit.loc[fit.index<d]
        if len(tr)<min_train:continue
        rec={'month':d.strftime('%Y-%m'),'actual':float(row.bunker),'n_train':len(tr),
             'train_months':';'.join(tr.index.strftime('%Y-%m')),'expanding_mean':float(tr.bunker.mean()),
             'persistence':float(row.lag1),'seasonal12':float(row.lag12)}
        for label,cols in [('stock',['stock']),('stock_movement',['stock','movement']),
                           ('lag_stock',['lag1','stock']),('lag_stock_movement',['lag1','stock','movement'])]:
            rec[label]=_ridge_predict(tr.bunker.to_numpy(),tr[cols].to_numpy(),row[cols].to_numpy(),penalty)
        rows.append(rec)
    columns=['month','actual','n_train','train_months','expanding_mean','persistence','seasonal12',
             'stock','stock_movement','lag_stock','lag_stock_movement']
    return pd.DataFrame(rows,columns=columns)
