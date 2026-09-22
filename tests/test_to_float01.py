import unittest
import numpy as np
from _harness import fs


class TestToFloat01(unittest.TestCase):
    def test_uint8_divides_by_255(self):
        arr = np.array([[[0, 128, 255]]], dtype=np.uint8)
        out = fs.to_float01(arr)
        self.assertAlmostEqual(float(out[0, 0, 2]), 1.0, places=6)
        self.assertAlmostEqual(float(out[0, 0, 1]), 128 / 255.0, places=6)

    def test_genuine_uint16_divides_by_65535(self):
        # a real 16-bit astro frame uses far more than the bottom 8 bits
        arr = np.array([[[0, 30000, 65535]]], dtype=np.uint16)
        out = fs.to_float01(arr)
        self.assertAlmostEqual(float(out[0, 0, 2]), 1.0, places=6)
        self.assertAlmostEqual(float(out[0, 0, 1]), 30000 / 65535.0, places=6)

    def test_8bit_source_stored_as_uint16_is_not_darkened(self):
        """Siril's '16 bits' working mode can hand back an originally-8-bit
        image (e.g. a JPG) as a uint16 array whose values are never rescaled
        past 0-255 - dividing that by 65535 makes it ~256x too dark (the bug
        a user hit: fetch_full() max came back as 255/65535). Real case from
        the report: an image whose true 8-bit max was 255."""
        rng = np.random.default_rng(0)
        arr = rng.integers(0, 256, size=(20, 20, 3)).astype(np.uint16)
        arr[0, 0, 0] = 255  # guarantee the true max is present
        out = fs.to_float01(arr)
        self.assertAlmostEqual(float(out.max()), 1.0, places=6)
        self.assertGreater(float(out.mean()), 0.1)  # not collapsed to near-black

    def test_uint8_and_the_darkening_bug_look_identical_in_value_range(self):
        arr8 = np.array([[[0, 128, 255]]], dtype=np.uint8)
        arr16_same_values = arr8.astype(np.uint16)
        out8 = fs.to_float01(arr8)
        out16 = fs.to_float01(arr16_same_values)
        self.assertTrue(np.allclose(out8, out16))


if __name__ == "__main__":
    unittest.main()
