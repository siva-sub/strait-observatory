"""Regression oracles defined before the 0.3 experimental implementation."""
import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin
from strait.experimental import SARFrame, temporal_change, monthly_calendar, expanding_compare
from strait.data.sentinel1 import load_local_scenes


def frame(a, date='2024-01-01', **kw):
    params=dict(power=np.array(a,float),transform=from_origin(0,20,10,10),crs='EPSG:32648',
                acquired_at=date,track='S1A-98-ASCENDING',lineage='verified',radiometry='sigma0')
    params.update(kw);return SARFrame(**params)


def test_change_masks_nodata_and_normalizes():
    a=frame([[1,0],[np.nan,1]])
    c=frame([[2,0],[np.nan,2]],date='2024-01-13')
    r=temporal_change(a,c,min_coverage=.5)
    assert r['mean_abs_db']==pytest.approx(10*np.log10(2))
    assert r['coverage']==.5 and r['valid_pixels']==2
    assert r['interpretation']=='backscatter change, not vessel turnover'
    assert temporal_change(a,c,min_coverage=.9)['mean_abs_db'] is None


def test_change_lineage_fail_closed():
    a=frame([[1,1],[1,1]],lineage='catalogue')
    b=frame([[1,1],[1,1]],date='2024-01-13',lineage='catalogue')
    with pytest.raises(ValueError,match='lineage'):temporal_change(a,b)
    r=temporal_change(a,b,allow_catalogue=True)
    assert r['status']=='conditional' and r['mean_abs_db']==0


@pytest.mark.parametrize('kwargs',[{'track':'S1A-171-ASCENDING'}, {'crs':'EPSG:32649'},
    {'transform':from_origin(10,20,10,10)}, {'radiometry':'gamma0'}, {'acquired_at':'2024-02-01'}])
def test_bad_pair_rejected(kwargs):
    a=frame([[1,1],[1,1]])
    b=frame([[1,1],[1,1]],date='2024-01-13',**kwargs)
    with pytest.raises(ValueError):temporal_change(a,b)


def test_calendar_duplicates_and_missing():
    f=pd.DataFrame({'y':[1,3]},index=['2024-01','2024-03'])
    c=monthly_calendar(f)
    assert np.isnan(c.y.shift().loc['2024-03-01'])
    with pytest.raises(ValueError,match='duplicate'):monthly_calendar(pd.concat([f,f]))
    with pytest.raises(ValueError):monthly_calendar(pd.DataFrame({'y':[np.inf]},index=['2024-01']))


def toy():
    r=np.random.default_rng(1)
    return pd.DataFrame({'bunker':np.arange(36.)*2+5+r.normal(size=36),
                         'stock':np.arange(36.)+r.normal(size=36),
                         'movement':r.normal(size=36)},index=pd.date_range('2024-01',periods=36,freq='MS'))


def test_expanding_no_future_leakage_equal_folds():
    a=toy();x=expanding_compare(a,target='bunker',features=['stock','movement'])
    a.iloc[-1]=10000;y=expanding_compare(a,target='bunker',features=['stock','movement'])
    pd.testing.assert_frame_equal(x.iloc[:-1],y.iloc[:-1])
    assert (x.n_train>=12).all()
    for r in x.itertuples():assert all(d<r.month for d in r.train_months.split(';'))


def make_tif(path, a, bounds=(0,0,2,2), nodata=0):
    path.parent.mkdir(parents=True,exist_ok=True)
    from rasterio.transform import from_bounds
    with rasterio.open(path,'w',driver='GTiff',height=a.shape[0],width=a.shape[1],count=1,
                       dtype=a.dtype,crs='EPSG:4326',transform=from_bounds(*bounds,a.shape[1],a.shape[0]),nodata=nodata) as s:s.write(a,1)


def test_local_cache_grid_time_and_nodata(tmp_path):
    make_tif(tmp_path/'land_mask.tif',np.zeros((4,4),'uint8'),nodata=None)
    a=np.ones((4,4),'float32');a[1,1]=0
    make_tif(tmp_path/'scenes'/'s1_20240105.tif',a)
    make_tif(tmp_path/'scenes'/'s1_20240205.tif',a)
    scenes,dates,mask=load_local_scenes(str(tmp_path),bounds=(0,0,2,2),shape=(4,4),time_range=('2024-01','2024-01'))
    assert dates==['20240105'] and len(scenes)==1
    assert np.isnan(scenes[0][1,1])
    with pytest.raises(ValueError,match='bounds'):load_local_scenes(str(tmp_path),bounds=(1,1,3,3),shape=(4,4))
    with pytest.raises(ValueError,match='shape'):load_local_scenes(str(tmp_path),bounds=(0,0,2,2),shape=(8,8))


def test_local_cache_requires_mask_and_valid_date(tmp_path):
    make_tif(tmp_path/'scenes'/'s1_20240105.tif',np.ones((4,4),'float32'))
    with pytest.raises(FileNotFoundError,match='mask'):load_local_scenes(str(tmp_path),bounds=(0,0,2,2),shape=(4,4))
    make_tif(tmp_path/'land_mask.tif',np.zeros((4,4),'uint8'),nodata=None)
    make_tif(tmp_path/'scenes'/'s1_20160.tif',np.ones((4,4),'float32'))
    with pytest.raises(ValueError,match='date'):load_local_scenes(str(tmp_path),bounds=(0,0,2,2),shape=(4,4))


def test_detector_rejects_truncated_scene_date_zip():
    from strait.detect import detect_vessels
    a=np.ones((16,16),np.float32)*.01
    with pytest.raises(ValueError,match='dates'):
        detect_vessels([a,a],['202401'],np.zeros_like(a,bool),bounds=(0,0,1,1),shape=a.shape)


def test_detector_invalid_returns_do_not_become_targets():
    from strait.detect import detect_vessels
    a=np.ones((64,64),np.float32)*.01;a[25:29,25:29]=np.inf
    d=detect_vessels([a],['20240105'],np.zeros_like(a,bool),bounds=(0,0,1,1),shape=a.shape)
    assert len(d)==0


def test_aggregate_full_dates_and_missing_metadata():
    import geopandas as gpd
    from shapely.geometry import Point
    from strait import aggregate
    d=gpd.GeoDataFrame({'date':['20240105','2024-01-19','20240301']},geometry=[Point(0,0)]*3,crs='EPSG:4326')
    out=aggregate(d)
    assert out.loc['2024-01-01','total']==2
    assert out.loc['2024-03-01','total']==1
    with pytest.raises(ValueError,match='date'):aggregate(d.drop(columns='date'))


def test_unknown_preset_does_not_silently_use_balanced(tmp_path):
    from strait import Cutout
    c=Cutout(path=str(tmp_path));c._scenes=[np.ones((4,4))]
    with pytest.raises(ValueError,match='preset'):c.detect(preset='precison')


def test_bounded_native_window_preserves_georeference(tmp_path):
    from strait.experimental import read_power_window
    a=np.ones((4,4),'float32');a[1,1]=0
    make_tif(tmp_path/'scene.tif',a)
    r=read_power_window(tmp_path/'scene.tif',(0,0,2,2),acquired_at='2024-01-01',
        track='A-98-ASCENDING',radiometry='sigma0',max_pixels=16)
    assert r.power.shape==(4,4) and r.crs.to_epsg()==4326
    assert r.transform.c==0 and r.transform.f==2
    assert not r.valid[1,1]
    with pytest.raises(ValueError,match='budget'):
        read_power_window(tmp_path/'scene.tif',(0,0,2,2),acquired_at='2024-01-01',
            track='A-98-ASCENDING',radiometry='sigma0',max_pixels=4)


@pytest.mark.parametrize('which',['valid','support'])
def test_nan_boolean_masks_rejected(which):
    if which=='valid':
        with pytest.raises(ValueError,match='mask'):frame([[1,1],[1,1]],valid=np.array([[1,np.nan],[1,1]]))
    else:
        a=frame([[1,1],[1,1]]);c=frame([[2,2],[2,2]],date='2024-01-13')
        with pytest.raises(ValueError,match='mask'):temporal_change(a,c,support=np.array([[1,np.nan],[1,1]]))


def test_frame_copies_and_freezes_input():
    a=np.ones((2,2),np.float32);mask=np.ones((2,2),bool)
    f=SARFrame(a,from_origin(0,20,10,10),'EPSG:32648','2024-01-01',
               'A-98-ASCENDING','sigma0',lineage='verified',valid=mask)
    a[0,0]=0;mask[0,0]=False
    assert f.power[0,0]==1 and f.valid[0,0]
    with pytest.raises(ValueError):f.power[0,0]=0
    with pytest.raises(ValueError):f.valid[0,0]=False
    with pytest.raises(Exception):f.track='different'
    with pytest.raises(ValueError):frame(a,transform=from_origin(np.nan,20,10,10))


def test_reader_refuses_remote_and_unbounded_budget():
    from strait.experimental import read_power_window
    kwargs=dict(acquired_at='2024-01-01',track='A-98-ASCENDING',radiometry='sigma0')
    with pytest.raises(ValueError,match='local'):
        read_power_window('https://example.org/file.tif',(0,0,2,2),**kwargs)
    with pytest.raises(ValueError):read_power_window('x.tif',(0,0,2,2),max_pixels=np.inf,**kwargs)


def test_aggregate_never_uses_runtime_date():
    import geopandas as gpd
    from shapely.geometry import Point
    from strait import aggregate
    for date in ['now','today','yesterday','bad']:
        d=gpd.GeoDataFrame({'date':[date]},geometry=[Point(0,0)],crs='EPSG:4326')
        with pytest.raises(ValueError,match='date'):aggregate(d)


def test_mask_nan_is_excluded_not_water(tmp_path):
    mask=np.zeros((4,4),'float32');mask[0,0]=np.nan
    make_tif(tmp_path/'land_mask.tif',mask,nodata=None)
    make_tif(tmp_path/'scenes'/'s1_20240105.tif',np.ones((4,4),'float32'))
    _,_,land=load_local_scenes(str(tmp_path),bounds=(0,0,2,2),shape=(4,4))
    assert land[0,0]


@pytest.mark.parametrize('bounds',[(0,0,np.inf,1),(1000,2000,1001,2001),(0,0,1,np.nan)])
def test_detector_bounds_must_be_finite_wgs84(bounds):
    from strait.detect import detect_vessels
    a=np.ones((16,16),np.float32)
    with pytest.raises(ValueError,match='bounds'):
        detect_vessels([a],['20240105'],np.zeros_like(a,bool),bounds=bounds,shape=a.shape)


@pytest.mark.parametrize('date',['now','today','2024'])
def test_sar_frame_requires_fixed_acquisition_date(date):
    with pytest.raises(ValueError,match='date'):frame([[1,1],[1,1]],date=date)


def test_monthly_panel_rejects_runtime_or_incomplete_dates():
    for date in ['now','today','2024',0]:
        with pytest.raises(ValueError,match='date'):
            monthly_calendar(pd.DataFrame({'y':[1]},index=[date]))


@pytest.mark.parametrize('date',[None,0])
def test_frame_rejects_absent_or_numeric_epoch_date(date):
    with pytest.raises(ValueError,match='date'):frame([[1,1],[1,1]],date=date)


def test_reader_refuses_local_vrt_disguised_as_tiff(tmp_path):
    from strait.experimental import read_power_window
    p=tmp_path/'not_really.tif'
    p.write_text('<VRTDataset rasterXSize="1" rasterYSize="1"><VRTRasterBand dataType="Float32" band="1"><SimpleSource><SourceFilename>https://example.org/remote.tif</SourceFilename></SimpleSource></VRTRasterBand></VRTDataset>')
    with pytest.raises(ValueError,match='GeoTIFF'):
        read_power_window(p,(0,0,2,2),acquired_at='2024-01-01',track='A-98-ASCENDING',radiometry='sigma0')
