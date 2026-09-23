"""Flare reach ("flare_reach", % of the rendered spike length): the soft
flare and its rays live in a band from the star's own visible edge out to
that reach - never past the spike tips (a flare reaching beyond the spikes
reads as a separate oversized disc), and never so short that it hides
inside the star's own core (floored at the core edge + 1.5 diameters)."""
import unittest
import numpy as np
from _harness import fs

FWHM = 12.0
LENGTH = 8.0            # spike = 96 px


def _anchor(**over):
    a = {"diam": 8.0, "length": LENGTH, "intensity": 0.0, "thickness": 1.1,
         "soft_flare": 80.0, "flare_reach": 45.0, "flare_rays": 80.0,
         "ring_flare": 0.0, "ring_diam": 1.6, "flare_saturation": 0.0,
         "rainbow": 0.0, "saturation": 100.0}
    a.update(over)
    return a


def _render(anchor, size=300):
    star = [(size / 2, size / 2, FWHM, 1.0, (1.0, 1.0, 1.0), True, None)]
    cfg = {"anchors": [dict(anchor, diam=3.0), dict(anchor, diam=40.0)], "rays": 4,
           "rotation": 30.0, "hue": 0.0, "sharpness": 100.0, "variation": 0.0,
           "twinkle": 0.0, "flare_symmetry": 40.0}
    return fs.render_spike_layer((size, size), 0, 0, size, size, star, cfg)[..., 0]


def _radius(img, size=300):
    yy, xx = np.mgrid[0:size, 0:size]
    return np.hypot(xx - size / 2, yy - size / 2)


def _extent(img, thr=0.01):
    r = _radius(img)
    return float(r[img > thr].max())


class TestFlareReach(unittest.TestCase):
    def test_never_past_the_spike_tips(self):
        for reach in (45.0, 100.0):
            img = _render(_anchor(flare_reach=reach))
            self.assertLessEqual(_extent(img, thr=1e-6), FWHM * LENGTH + 1.5)

    def test_reach_scales_with_the_spike_length(self):
        short = _extent(_render(_anchor(flare_reach=30.0)))
        long_ = _extent(_render(_anchor(flare_reach=80.0)))
        self.assertGreater(long_, short * 1.8)
        self.assertLess(long_, FWHM * LENGTH * 0.85)

    def test_a_low_reach_still_shows_outside_the_core(self):
        """The old gaussian flare at a small reach sat entirely inside the
        star's own core - now the rays start at the core edge and the
        reach is floored at core + 1.5 diameters."""
        img = _render(_anchor(flare_reach=10.0))
        r = _radius(img)
        core = FWHM / 2
        ring = img[(r > core + 0.5 * FWHM) & (r < core + FWHM)]
        self.assertGreater(ring.max(), 0.1)
        self.assertGreater(_extent(img), core + FWHM)


if __name__ == "__main__":
    unittest.main()
