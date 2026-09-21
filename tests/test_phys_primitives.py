import unittest
import numpy as np
from _harness import fs


def j1_ref(x):
    t = np.linspace(0.0, np.pi, 200001)
    f = np.cos(t - x * np.sin(t))
    return float(np.sum((f[1:] + f[:-1]) * np.diff(t)) / 2.0 / np.pi)


class TestBessel(unittest.TestCase):
    def test_matches_numeric_integral(self):
        for x in (0.001, 0.5, 1.0, 2.9, 3.0, 3.1, 5.0, 10.0, 50.0, 100.0, 200.0):
            self.assertAlmostEqual(float(fs._bessel_j1(np.array([x]))[0]), j1_ref(x), delta=5e-7, msg=str(x))

    def test_odd(self):
        self.assertAlmostEqual(float(fs._bessel_j1(np.array([-2.0]))[0]), -j1_ref(2.0), delta=5e-7)


class TestAiry(unittest.TestCase):
    def test_peak_and_first_zero(self):
        self.assertAlmostEqual(float(fs._airy_obstructed_intensity(np.array([0.0]), 0.0)[0]), 1.0, places=6)
        self.assertLess(float(fs._airy_obstructed_intensity(np.array([1.2197]), 0.0)[0]), 1e-3)

    def test_first_ring_levels(self):
        rho = np.linspace(1.3, 2.0, 2000)
        for eps, want in ((0.0, 0.0174), (0.3, 0.0473), (0.55, 0.1082)):
            got = float(fs._airy_obstructed_intensity(rho, eps).max())
            self.assertAlmostEqual(got, want, delta=0.1 * want, msg=str(eps))


class TestGeometry(unittest.TestCase):
    def _angles(self, lines):
        return sorted(round(l["angle"] % 360.0, 3) for l in lines)

    def test_ray_counts(self):
        self.assertEqual(len(fs._phys_spike_lines("spider4", 6, 0.0)), 4)
        self.assertEqual(len(fs._phys_spike_lines("spider3", 6, 0.0)), 6)
        for n, want in ((5, 10), (6, 6), (7, 14), (8, 8), (9, 18)):
            self.assertEqual(len(fs._phys_spike_lines("polygon", n, 0.0)), want, msg=str(n))

    def test_spider4_angles_follow_rotation(self):
        self.assertEqual(self._angles(fs._phys_spike_lines("spider4", 6, 20.0)), [20.0, 110.0, 200.0, 290.0])

    def test_channel_scales(self):
        r, g, b = fs._phys_channel_scales(100.0)
        self.assertAlmostEqual(g, 1.0)
        self.assertAlmostEqual(r, 600.0 / 530.0, places=6)
        self.assertAlmostEqual(b, 450.0 / 530.0, places=6)
        self.assertEqual(fs._phys_channel_scales(0.0), [1.0, 1.0, 1.0])

    def test_vane_plateau_matches_formula(self):
        ln = fs._phys_spike_lines("spider4", 6, 0.0)[0]
        w, eps = 0.0156, 0.3
        P = (4 * w / (np.pi * (1 + eps))) ** 2
        got = float(fs._phys_spike_along(np.array([10.0]), ln, eps, w)[0])
        self.assertAlmostEqual(got, P / (1 + (np.pi * w * 10.0) ** 2), delta=1e-9)

    def test_near_field_turned_off(self):
        ln = fs._phys_spike_lines("spider4", 6, 0.0)[0]
        self.assertEqual(float(fs._phys_spike_along(np.array([0.5]), ln, 0.3, 0.01)[0]), 0.0)


if __name__ == "__main__":
    unittest.main()
