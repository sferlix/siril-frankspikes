"""Focal-length-scaled default spike Length - see
_focal_length_to_spike_length, _read_fits_focal_length and
App._apply_length_calibration."""
import os
import tempfile
import unittest
import numpy as np
from _harness import fs


class TestFocalLengthToSpikeLength(unittest.TestCase):
    def test_reference_points_are_exact(self):
        self.assertAlmostEqual(fs._focal_length_to_spike_length(300.0), 8.0, places=6)
        self.assertAlmostEqual(fs._focal_length_to_spike_length(800.0), 3.0, places=6)

    def test_monotonically_decreasing_with_focal_length(self):
        vals = [fs._focal_length_to_spike_length(fl) for fl in (200, 400, 600, 1000, 2000)]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_clamped_at_both_ends(self):
        very_short = fs._focal_length_to_spike_length(50.0)
        very_long = fs._focal_length_to_spike_length(5000.0)
        self.assertLessEqual(very_short, fs._FOCAL_LENGTH_LEN_MAX)
        self.assertGreaterEqual(very_long, fs._FOCAL_LENGTH_LEN_MIN)

    def test_invalid_input_returns_none(self):
        self.assertIsNone(fs._focal_length_to_spike_length(0))
        self.assertIsNone(fs._focal_length_to_spike_length(-50.0))
        self.assertIsNone(fs._focal_length_to_spike_length(None))


class TestFocalLengthScaleFactor(unittest.TestCase):
    """The generic interpolator behind Length/Thickness/Intensity/Minimum-
    diameter-cutoff scaling - see _focal_length_scale_factor."""

    def test_reference_points_are_exact(self):
        self.assertAlmostEqual(
            fs._focal_length_scale_factor(300.0, 0.85, 1.0), 0.85, places=6)
        self.assertAlmostEqual(
            fs._focal_length_scale_factor(800.0, 0.85, 1.0), 1.0, places=6)

    def test_one_is_identity_at_both_references(self):
        self.assertAlmostEqual(fs._focal_length_scale_factor(300.0, 1.0, 1.0), 1.0, places=6)
        self.assertAlmostEqual(fs._focal_length_scale_factor(800.0, 1.0, 1.0), 1.0, places=6)

    def test_clamps_to_given_bounds(self):
        v = fs._focal_length_scale_factor(50.0, 1.15, 1.0, lo=0.8, hi=1.6)
        self.assertLessEqual(v, 1.6)
        v2 = fs._focal_length_scale_factor(5000.0, 1.15, 1.0, lo=0.8, hi=1.6)
        self.assertGreaterEqual(v2, 0.8)

    def test_no_bounds_means_unclamped(self):
        v = fs._focal_length_scale_factor(50.0, 1.15, 1.0)
        self.assertIsNotNone(v)  # just shouldn't raise/clip silently to None

    def test_invalid_focal_length_returns_none(self):
        self.assertIsNone(fs._focal_length_scale_factor(0, 1.15, 1.0))
        self.assertIsNone(fs._focal_length_scale_factor(None, 1.15, 1.0))


class TestReadFitsFocalLength(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _write_fits(self, focal_length=None):
        from astropy.io import fits
        data = np.zeros((10, 10), dtype=np.float32)
        hdu = fits.PrimaryHDU(data=data)
        if focal_length is not None:
            hdu.header["FOCALLEN"] = focal_length
        path = os.path.join(self.tmpdir, "t.fits")
        hdu.writeto(path, overwrite=True)
        return path

    def test_reads_a_present_keyword(self):
        path = self._write_fits(focal_length=750.0)
        self.assertAlmostEqual(fs._read_fits_focal_length(path), 750.0, places=3)

    def test_missing_keyword_returns_none(self):
        path = self._write_fits(focal_length=None)
        self.assertIsNone(fs._read_fits_focal_length(path))

    def test_zero_keyword_returns_none(self):
        path = self._write_fits(focal_length=0.0)
        self.assertIsNone(fs._read_fits_focal_length(path))

    def test_missing_file_returns_none_not_raises(self):
        self.assertIsNone(fs._read_fits_focal_length(os.path.join(self.tmpdir, "nope.fits")))


class TestFileWorkerFocalLength(unittest.TestCase):
    def test_open_path_populates_focal_length_for_fits(self):
        tmpdir = tempfile.mkdtemp()
        from astropy.io import fits
        hdu = fits.PrimaryHDU(data=np.zeros((8, 8), dtype=np.float32))
        hdu.header["FOCALLEN"] = 400.0
        path = os.path.join(tmpdir, "t.fits")
        hdu.writeto(path, overwrite=True)

        w = fs.FileWorker()
        w.open_path(path)
        self.assertAlmostEqual(w.get_focal_length(), 400.0, places=3)

    def test_tiff_has_no_focal_length(self):
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "t.tiff")
        rgb = np.zeros((8, 8, 3), dtype=np.float32)
        fs._save_tiff(path, rgb, bit_depth=8)

        w = fs.FileWorker()
        w.open_path(path)
        self.assertIsNone(w.get_focal_length())


class _FakeKeywords:
    def __init__(self, focal_length):
        self.focal_length = focal_length


class _FakeSiril:
    def __init__(self, focal_length):
        self._focal_length = focal_length

    def get_image_keywords(self):
        return _FakeKeywords(self._focal_length)


class TestSirilWorkerFocalLength(unittest.TestCase):
    def _worker(self, focal_length):
        w = fs.SirilWorker.__new__(fs.SirilWorker)  # skip __init__'s real connect()
        w.siril = _FakeSiril(focal_length)
        return w

    def test_reads_a_positive_value(self):
        self.assertAlmostEqual(self._worker(950.0).get_focal_length(), 950.0, places=3)

    def test_zero_returns_none(self):
        self.assertIsNone(self._worker(0.0).get_focal_length())

    def test_missing_attribute_returns_none_not_raises(self):
        w = fs.SirilWorker.__new__(fs.SirilWorker)
        w.siril = object()  # no get_image_keywords() at all
        self.assertIsNone(w.get_focal_length())


if __name__ == "__main__":
    unittest.main()
