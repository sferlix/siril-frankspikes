"""Ring flare diameter ("ring_diam", x star diameter): the ring's own
DIAMETER relative to the star's, so it hugs the star (the old "size" was
used as a radius in star diameters, which put the ring a whole diameter
away, detached from the core). Kept just outside the core and inside the
spikes, including the fainter second Airy ring."""
import unittest
import numpy as np
from _harness import fs

FWHM = 12.0


def _anchor(**over):
    a = {"diam": 8.0, "length": 8.0, "intensity": 0.0, "thickness": 1.1,
         "soft_flare": 0.0, "flare_reach": 45.0, "flare_rays": 0.0,
         "ring_flare": 80.0, "ring_diam": 1.6, "flare_saturation": 0.0,
         "rainbow": 0.0, "saturation": 100.0}
    a.update(over)
    return a


def _render(anchor, size=300):
    star = [(size / 2, size / 2, FWHM, 1.0, (1.0, 1.0, 1.0), True, None)]
    cfg = {"anchors": [dict(anchor, diam=3.0), dict(anchor, diam=40.0)], "rays": 4,
           "rotation": 30.0, "hue": 0.0, "sharpness": 100.0, "variation": 0.0,
           "twinkle": 0.0}
    return fs.render_spike_layer((size, size), 0, 0, size, size, star, cfg)[..., 0]


def _peak_radius(img, size=300):
    row = img[size // 2, size // 2:]
    return float(np.argmax(row))


class TestRingDiameter(unittest.TestCase):
    def test_ring_diameter_is_in_star_diameters(self):
        for d in (2.0, 3.0):
            self.assertAlmostEqual(_peak_radius(_render(_anchor(ring_diam=d))),
                                   d * FWHM / 2, delta=1.5)

    def test_default_hugs_the_star(self):
        r = _peak_radius(_render(_anchor()))
        self.assertGreater(r, FWHM / 2)
        self.assertLess(r, FWHM * 1.0)

    def test_never_inside_the_core(self):
        self.assertGreaterEqual(_peak_radius(_render(_anchor(ring_diam=1.0))), FWHM / 2)

    def test_both_rings_stay_inside_the_spikes(self):
        img = _render(_anchor(ring_diam=6.0))
        yy, xx = np.mgrid[0:300, 0:300]
        r = np.hypot(xx - 150, yy - 150)
        self.assertLess(float(img[r > 8.0 * FWHM].max()), 0.02)


if __name__ == "__main__":
    unittest.main()
