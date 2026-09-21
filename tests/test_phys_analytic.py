import unittest
import numpy as np
from _harness import fs

P0 = {"depth": 90.0, "extent": 30.0, "spikes": 100.0, "vane": 1.0, "rings": 100.0,
      "obstruction": 30.0, "dispersion": 0.0, "color": 0.0, "streaks": 0.0, "streak_len": 8.0}
FWHM = 6.0
U = FWHM / fs.PHYS_FWHM_PER_LAMD
SIZE = 601
C = SIZE // 2


def draw(p, aperture="spider4", blades=6, rot=0.0):
    cv = np.zeros((SIZE, SIZE, 3), np.float32)
    lines = fs._phys_spike_lines(aperture, blades, rot)
    fs._phys_draw_analytic(cv, 0, 0, float(C), float(C), FWHM, U, p, lines, (1.0, 1.0, 1.0), 1.0, blades)
    return cv


def arcs(v):
    # midway between the spike peak and the valley: the asinh display compresses
    # the contrast, so a fixed 50%-of-max threshold would merge close spikes
    on = v > 0.5 * (v.max() + v.min())
    return int(np.sum(on & ~np.roll(on, 1)))


def ring_samples(cv, radius, ch=1):
    th = np.radians(np.arange(360))
    ys = np.round(C + radius * np.sin(th)).astype(int)
    xs = np.round(C + radius * np.cos(th)).astype(int)
    return cv[ys, xs, ch]


class TestAnalytic(unittest.TestCase):
    def test_depth_zero_draws_nothing(self):
        self.assertEqual(float(draw(dict(P0, depth=0.0)).max()), 0.0)

    def test_spike_ray_counts(self):
        only_spikes = dict(P0, rings=0.0)
        self.assertEqual(arcs(ring_samples(draw(only_spikes, "spider4"), 8 * FWHM)), 4)
        self.assertEqual(arcs(ring_samples(draw(only_spikes, "spider3"), 8 * FWHM)), 6)
        self.assertEqual(arcs(ring_samples(draw(only_spikes, "polygon", 5), 8 * FWHM)), 10)
        self.assertEqual(arcs(ring_samples(draw(only_spikes, "polygon", 7), 8 * FWHM)), 14)

    def test_rotation_moves_spikes(self):
        v = ring_samples(draw(dict(P0, rings=0.0), "spider4", rot=20.0), 8 * FWHM)
        self.assertLessEqual(abs(int(np.argmax(v)) - 20), 3)

    def test_first_ring_radius(self):
        cv = draw(dict(P0, spikes=0.0))
        row = cv[C, C:, 1]
        lo, hi = int(1.3 * U), int(2.0 * U)
        peak = (lo + int(np.argmax(row[lo:hi]))) / U
        self.assertAlmostEqual(peak, 1.63, delta=0.12)

    def test_dispersion_widens_red_rings(self):
        cv = draw(dict(P0, spikes=0.0, dispersion=100.0))
        lo, hi = int(1.2 * U), int(2.6 * U)
        r_red = lo + int(np.argmax(cv[C, C + lo:C + hi, 0]))
        r_blue = lo + int(np.argmax(cv[C, C + lo:C + hi, 2]))
        self.assertAlmostEqual(r_red / r_blue, 600.0 / 450.0, delta=0.08)

    def test_core_is_excluded(self):
        cv = draw(P0)
        self.assertLess(float(cv[C, C, 1]), 0.05)


class TestStreaks(unittest.TestCase):
    def test_streaks_deterministic_and_outside_core(self):
        def go():
            cv = np.zeros((SIZE, SIZE, 3), np.float32)
            fs._phys_draw_streaks(cv, 0, 0, float(C), float(C), FWHM, U, dict(P0, streaks=100.0),
                                  (1.0, 1.0, 1.0), 1.0, 100.0, 200.0)
            return cv
        a, b = go(), go()
        self.assertTrue(np.array_equal(a, b))
        self.assertGreater(float(a.max()), 0.05)
        yy, xx = np.mgrid[:SIZE, :SIZE]
        far = np.hypot(xx - C, yy - C) > 4 * FWHM
        self.assertGreater(float(a[far].max()), 0.0)

    def test_zero_streaks_draws_nothing(self):
        cv = np.zeros((SIZE, SIZE, 3), np.float32)
        fs._phys_draw_streaks(cv, 0, 0, float(C), float(C), FWHM, U, dict(P0, streaks=0.0),
                              (1.0, 1.0, 1.0), 1.0, 1.0, 2.0)
        self.assertEqual(float(cv.max()), 0.0)


if __name__ == "__main__":
    unittest.main()
