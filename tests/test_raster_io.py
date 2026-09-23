"""Standalone mode: JPG/PNG open and save (via Pillow, already a
dependency) alongside FITS/TIFF - same raw/display convention as
_load_tiff (row 0 = top on disk, flipped to raw row 0 = bottom)."""
import os
import tempfile
import unittest
import numpy as np
from PIL import Image
from _harness import fs


def _gradient(h=40, w=60):
    yy, xx = np.mgrid[0:h, 0:w]
    return np.stack([xx / (w - 1), yy / (h - 1), 0.5 * np.ones((h, w))], -1).astype(np.float32)


class TestRasterIO(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def _roundtrip(self, ext):
        rgb = _gradient()
        path = os.path.join(self.dir, "img" + ext)
        w = fs.FileWorker()
        w.save_rgb(rgb, path)
        w2 = fs.FileWorker()
        w2.open_path(path)
        raw = w2.fetch_full()
        self.assertEqual(raw.shape, rgb.shape)
        return rgb, raw[::-1], w2   # raw (bottom-up) -> display

    def test_png_roundtrip_is_8bit_exact(self):
        rgb, back, _ = self._roundtrip(".png")
        self.assertLess(float(np.abs(back - rgb).max()), 1.0 / 255 + 1e-6)

    def test_jpg_roundtrip_is_close(self):
        for ext in (".jpg", ".jpeg"):
            rgb, back, _ = self._roundtrip(ext)
            self.assertLess(float(np.abs(back - rgb).mean()), 0.02)

    def test_orientation_top_row_stays_on_top(self):
        rgb, back, _ = self._roundtrip(".png")
        # green grows downward in _gradient: first display row must be dark green
        self.assertLess(back[0, :, 1].mean(), back[-1, :, 1].mean())

    def test_no_focal_length_from_raster(self):
        _rgb, _back, w = self._roundtrip(".jpg")
        self.assertIsNone(w.get_focal_length())

    def test_16bit_grayscale_png_uses_full_range(self):
        path = os.path.join(self.dir, "g16.png")
        data = (np.linspace(0, 65535, 40 * 60).reshape(40, 60)).astype(np.uint16)
        Image.fromarray(data).save(path)
        w = fs.FileWorker()
        w.open_path(path)
        raw = w.fetch_full()
        self.assertEqual(raw.shape, (40, 60, 3))
        self.assertAlmostEqual(float(raw.max()), 1.0, places=3)

    def test_rgba_png_drops_alpha(self):
        path = os.path.join(self.dir, "a.png")
        Image.new("RGBA", (10, 8), (255, 0, 0, 128)).save(path)
        w = fs.FileWorker()
        w.open_path(path)
        self.assertEqual(w.fetch_full().shape, (8, 10, 3))

    def test_other_formats_still_rejected(self):
        path = os.path.join(self.dir, "x.bmp")
        Image.new("RGB", (4, 4)).save(path)
        with self.assertRaises(ValueError):
            fs.FileWorker().open_path(path)


if __name__ == "__main__":
    unittest.main()
