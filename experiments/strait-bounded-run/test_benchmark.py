import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from rasterio.transform import from_origin
spec=importlib.util.spec_from_file_location('bounded',Path(__file__).with_name('benchmark.py'))
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

class OracleTests(unittest.TestCase):
    def test_nodata(self):
        a=np.array([[0.,np.nan,-1.,0.1,1.]])
        d,v=b.valid_db(a)
        self.assertEqual(v.sum(),2)
        self.assertTrue(np.isnan(d[0,0]))
        np.testing.assert_allclose(d[0,3:],[ -10.,0.])
    def test_change_on_common_pixels(self):
        a=np.array([[1.,np.nan],[2.,3.]])
        q=b.change(a,a,np.ones_like(a))
        self.assertEqual(q['mean_abs_db'],0)
        self.assertAlmostEqual(q['coverage'],.75)
        q=b.change(a,a+3,np.ones_like(a))
        self.assertAlmostEqual(q['mean_abs_db'],3)
        q=b.change(a,np.full_like(a,np.nan),np.ones_like(a))
        self.assertIsNone(q['mean_abs_db'])
    def test_grids_and_tracks(self):
        a={'grid':'a','track':'A-98-ASCENDING','date':'2024-01-01'}
        c={**a,'date':'2024-01-13'}
        self.assertTrue(b.pair_ok(a,c))
        for k,v in [('grid','b'),('track','A-171-ASCENDING'),('track',None),('date','2024-02-01')]:
            self.assertFalse(b.pair_ok(a,{**c,k:v}))
    def test_true_crs_window(self):
        w=b.geo_window(from_origin(300000,200040,10,10),'EPSG:32648')
        self.assertGreater(w.col_off,14000/10)
        self.assertTrue(3800<w.width<4100)
        self.assertTrue(1600<w.height<2000)
    def test_calendar_gap(self):
        s=pd.Series([1.,3.],index=pd.to_datetime(['2024-01-01','2024-03-01']))
        cal=b.calendar(s.to_frame('bunker'))
        self.assertTrue(np.isnan(cal.bunker.shift(1).loc['2024-03-01']))
    def test_fold_scaling_no_future_leakage(self):
        f=pd.DataFrame({'stock':np.arange(24.)+3,'movement':np.cos(np.arange(24.)),'bunker':np.arange(24.)*2+8},index=pd.date_range('2024-01-01',periods=24,freq='MS'))
        p=b.expanding(f)
        g=f.copy();g.iloc[-1,:]=100000.
        q=b.expanding(g)
        pd.testing.assert_frame_equal(p.iloc[:-1],q.iloc[:-1])
    def test_bootstrap_stops_at_calendar_gaps(self):
        dates=['2025-06','2025-07','2025-10','2025-12','2026-01']
        blocks=b.calendar_blocks(dates,3)
        ordinal=pd.PeriodIndex(dates,freq='M').asi8
        for block in blocks:
            self.assertTrue(np.all(np.diff(ordinal[block])==1))
            self.assertLessEqual(len(block),3)
        self.assertEqual(blocks[2].tolist(),[2])
    def test_detector_synthetic(self):
        a=np.ones((128,128),np.float32)*.01
        a[62:65,62:65]=1
        d,v=b.valid_db(a)
        n=b.count_targets(d,v,64,3)
        self.assertEqual(n,1)
        self.assertEqual(b.count_targets(d,np.zeros_like(v),64,3),0)

if __name__=='__main__': unittest.main()
