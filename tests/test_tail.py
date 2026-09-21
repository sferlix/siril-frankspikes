import unittest
import numpy as np
from _harness import fs


def render(tail_len_px=None, radius=20.0, peak=0.8, size=241):
    layer = np.zeros((size, size, 3), dtype=np.float32)
    if tail_len_px is None:
        fs._add_soft_flare(layer, size // 2, size // 2, radius, peak)
    else:
        fs._add_soft_flare(layer, size // 2, size // 2, radius, peak, tail_len_px)
    return layer[..., 0]


class TestTail(unittest.TestCase):
    def test_zero_tail_is_identical_to_no_argument(self):
        self.assertTrue(np.array_equal(render(None), render(0.0)))

    def test_identical_inside_two_sigma(self):
        a, b = render(None), render(60.0)
        yy, xx = np.mgrid[:241, :241]
        r = np.hypot(xx - 120, yy - 120)
        inside = r <= 20.0          # sigma = 10 -> 2 sigma
        self.assertTrue(np.array_equal(a[inside], b[inside]))

    def test_tail_is_longer_and_monotonic(self):
        row = render(60.0)[120, 120:]
        self.assertTrue(np.all(np.diff(row) <= 1e-6))
        self.assertGreater(row[30], render(None)[120, 150])

    def test_zero_past_tail_length(self):
        row = render(60.0)[120, 120:]
        self.assertEqual(float(row[61:].max()), 0.0)


if __name__ == "__main__":
    unittest.main()
