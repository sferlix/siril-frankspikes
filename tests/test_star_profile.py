"""_measure_bright_star_profile: the FWHM the standalone detector (and the
saturated-star supplement) reports. It used to take the OUTER edge of the
first whole-pixel ring below half maximum, so sizes came out as even
integers and about twice too big (a 3.2px star measured 6px); the half-max
crossing is now interpolated between ring centres."""
import unittest
import numpy as np
from _harness import fs


def _star(fwhm, size=81, cx=40.3, cy=39.7, amp=0.8, bg=0.05, clip=None):
    yy, xx = np.mgrid[0:size, 0:size]
    s = fwhm / 2.3548
    img = bg + amp * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s))
    if clip is not None:
        img = np.minimum(img, clip)
    return img.astype(np.float32), cx, cy


class TestStarProfile(unittest.TestCase):
    def test_gaussian_fwhm_is_measured_accurately(self):
        for true in (2.5, 3.2, 4.0, 5.5, 8.0, 12.0):
            img, cx, cy = _star(true)
            peak = float(img.max())
            fwhm, amp = fs._measure_bright_star_profile(img, cx, cy, peak)
            self.assertAlmostEqual(fwhm, true, delta=0.15 * true, msg=f"true {true}: got {fwhm}")
            self.assertGreater(amp, 0)

    def test_not_quantised_to_even_integers(self):
        sizes = [fs._measure_bright_star_profile(*_star(t)[:3], float(_star(t)[0].max()))[0]
                 for t in (3.0, 3.4, 3.8, 4.2)]
        self.assertEqual(sizes, sorted(sizes))
        self.assertGreater(len(set(round(s, 2) for s in sizes)), 3)

    def test_saturated_star_measures_its_visible_size(self):
        """A clipped (flat-topped) star is measured at half of its clipped
        peak - its visible disc - so a bigger clipped star is bigger."""
        small, cs, _ = _star(6.0, amp=3.0, clip=1.0)
        big, cb, _ = _star(12.0, amp=3.0, clip=1.0)
        f_small = fs._measure_bright_star_profile(small, cs, 39.7, 1.0)[0]
        f_big = fs._measure_bright_star_profile(big, cb, 39.7, 1.0)[0]
        self.assertGreater(f_small, 6.0)          # wider than the unclipped core
        self.assertGreater(f_big, f_small * 1.6)

    def test_minimum_size_floor(self):
        img, cx, cy = _star(0.8)
        self.assertGreaterEqual(fs._measure_bright_star_profile(img, cx, cy, float(img.max()))[0], 1.5)


if __name__ == "__main__":
    unittest.main()
