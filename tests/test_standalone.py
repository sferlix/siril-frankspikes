"""Standalone (no Siril) mode: FITS/TIFF file I/O, star detection and
FileWorker's duck-typed contract with SirilWorker - see frankSpikes.py's
"Standalone (no Siril) mode" section and the FileWorker class docstring for
the raw/display convention this all has to match."""
import os
import tempfile
import unittest
import numpy as np
from _harness import fs


def _synthetic_stars_image(w=300, h=200, seed=3):
    """A plain background plus a handful of Gaussian point sources, bright
    enough for DAOStarFinder to find reliably - used to sanity-check
    _detect_stars_standalone without needing a real FITS/TIFF fixture."""
    rng = np.random.default_rng(seed)
    img = np.full((h, w), 0.05, dtype=np.float32)
    placed = []
    for _ in range(8):
        cx, cy = rng.uniform(20, w - 20), rng.uniform(20, h - 20)
        amp, sigma = rng.uniform(0.5, 0.9), rng.uniform(1.5, 3.0)
        yy, xx = np.mgrid[0:h, 0:w]
        img += amp * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma ** 2))
        placed.append((cx, cy, sigma))
    img += rng.normal(0, 0.003, size=img.shape).astype(np.float32)
    rgb = np.clip(np.stack([img, img, img], axis=-1), 0, 1).astype(np.float32)
    return rgb, placed


class TestNormalizeFloat01(unittest.TestCase):
    def test_already_normalized_is_untouched(self):
        arr = np.array([0.0, 0.3, 1.0], dtype=np.float32)
        out = fs._normalize_float01(arr)
        self.assertTrue(np.array_equal(out, arr))

    def test_rescales_an_arbitrary_range(self):
        arr = np.array([100.0, 200.0, 400.0], dtype=np.float32)
        out = fs._normalize_float01(arr)
        self.assertAlmostEqual(float(out.min()), 0.0, places=5)
        self.assertAlmostEqual(float(out.max()), 1.0, places=5)


class TestFitsRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_16bit_round_trip_preserves_orientation_and_values(self):
        h, w = 12, 20
        # A simple vertical gradient, brighter at the array's row 0 - lets
        # orientation bugs (an unwanted extra flip) show up as a reversed
        # gradient after the round trip, not just wrong pixel values.
        rgb = np.tile(np.linspace(1.0, 0.0, h, dtype=np.float32)[:, None, None],
                      (1, w, 3))
        path = os.path.join(self.tmpdir, "t.fits")
        fs._save_fits(path, rgb, bit_depth=16)
        loaded_raw = fs._load_fits(path)  # raw (row 0 = bottom) convention
        # _save_fits flips display->raw before writing, _load_fits reads
        # FITS' native order back out with no flip - so the raw array
        # loaded back should be rgb reversed top-to-bottom.
        np.testing.assert_allclose(loaded_raw, rgb[::-1, :, :], atol=1.0 / 65535 * 2)

    def test_32bit_float_round_trip(self):
        rgb = np.random.default_rng(1).uniform(0, 1, size=(10, 14, 3)).astype(np.float32)
        path = os.path.join(self.tmpdir, "t32.fits")
        fs._save_fits(path, rgb, bit_depth=32)
        loaded_raw = fs._load_fits(path)
        np.testing.assert_allclose(loaded_raw, rgb[::-1, :, :], atol=1e-6)


class TestTiffRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_16bit_round_trip_preserves_orientation_and_values(self):
        h, w = 12, 20
        rgb = np.tile(np.linspace(1.0, 0.0, h, dtype=np.float32)[:, None, None],
                      (1, w, 3))
        path = os.path.join(self.tmpdir, "t.tiff")
        fs._save_tiff(path, rgb, bit_depth=16)
        loaded_raw = fs._load_tiff(path)
        # TIFF's native order is row 0 = top (same as rgb/display here), so
        # _save_tiff writes with no flip and _load_tiff flips once on the
        # way back in (top-down -> raw) - net one flip vs. the source.
        np.testing.assert_allclose(loaded_raw, rgb[::-1, :, :], atol=1.0 / 65535 * 2)

    def test_8bit_round_trip(self):
        rgb = np.random.default_rng(2).uniform(0, 1, size=(8, 10, 3)).astype(np.float32)
        path = os.path.join(self.tmpdir, "t8.tiff")
        fs._save_tiff(path, rgb, bit_depth=8)
        loaded_raw = fs._load_tiff(path)
        np.testing.assert_allclose(loaded_raw, rgb[::-1, :, :], atol=1.0 / 255)


class TestDetectStarsStandalone(unittest.TestCase):
    def test_finds_the_placed_synthetic_stars(self):
        rgb, placed = _synthetic_stars_image()
        found = fs._detect_stars_standalone(rgb)
        self.assertGreaterEqual(len(found), len(placed) - 2)  # allow a miss or two
        for (px, py, _sigma) in placed:
            self.assertTrue(
                any(abs(fx - px) < 3 and abs(fy - py) < 3 for (fx, fy, *_r) in found),
                f"no detection near placed star at ({px:.1f},{py:.1f})")

    def test_flat_image_finds_nothing(self):
        flat = np.full((100, 100, 3), 0.1, dtype=np.float32)
        self.assertEqual(fs._detect_stars_standalone(flat), [])


class TestFileWorkerContract(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_open_path_rejects_unsupported_extension(self):
        w = fs.FileWorker()
        with self.assertRaises(ValueError):
            w.open_path("not_an_image.png")

    def test_get_stars_y_is_flipped_to_display_convention(self):
        """get_stars() must return y in DISPLAY (top-down) convention, the
        same contract SirilWorker.get_stars() has - App._reload_thread
        depends on this to correctly re-align stars with fetch_full()'s
        raw (bottom-up) pixel data (see the comment there)."""
        rgb, placed = _synthetic_stars_image()
        path = os.path.join(self.tmpdir, "stars.fits")
        # rgb is already in "raw" convention as far as _save_fits assumes
        # display input - to keep this test's expectations simple, treat
        # rgb itself as the raw array FileWorker will hand back from
        # fetch_full(), and place it directly rather than round-tripping
        # through a save (which would flip it).
        fs._save_fits(path, rgb[::-1, :, :], bit_depth=32)  # undo: land back as `rgb` raw
        w = fs.FileWorker()
        w.open_path(path)
        h, _wd = w.get_shape()
        raw_stars = fs._detect_stars_standalone(w.fetch_full())
        display_stars = w.get_stars()
        self.assertEqual(len(raw_stars), len(display_stars))
        for (rx, ry, *_r), (dx, dy, *_d) in zip(sorted(raw_stars), sorted(display_stars)):
            self.assertAlmostEqual(dx, rx, places=3)
            self.assertAlmostEqual(dy, h - 1.0 - ry, places=3)

    def test_push_rgb_then_save_rgb_writes_a_readable_file(self):
        w = fs.FileWorker()
        rgb = np.random.default_rng(4).uniform(0, 1, size=(10, 10, 3)).astype(np.float32)
        w.push_rgb(rgb)
        self.assertIsNotNone(w.last_rgb)
        path = os.path.join(self.tmpdir, "out.fits")
        w.save_rgb(w.last_rgb, path)
        self.assertTrue(os.path.exists(path))
        np.testing.assert_allclose(fs._load_fits(path), rgb[::-1, :, :], atol=1e-6)


if __name__ == "__main__":
    unittest.main()
