"""Changes made after comparing frankSpikes' classic renderer against a real
reference photo (see the conversation / commit message): every star should
show at least a hint of spike (no hard zero for faint ones), the default
look shouldn't cycle through an artificial rainbow, and the ring shouldn't
read as a crisp separate circle."""
import unittest
import numpy as np
from _harness import fs


def _cfg(anchors, twinkle=0.0, **over):
    cfg = {"anchors": anchors, "rays": 4, "rotation": 0.0, "hue": 0.0,
           "sharpness": 100.0, "variation": 0.0, "twinkle": twinkle}
    cfg.update(over)
    return cfg


def _anchors():
    import copy
    return copy.deepcopy(fs.SPIKE_DEFAULTS["anchors"])


class TestTwinkleFloor(unittest.TestCase):
    def test_default_twinkle_is_nonzero(self):
        self.assertGreater(fs.SPIKE_DEFAULTS["twinkle"], 0.0)

    def test_zero_twinkle_matches_v2_0_0_below_cutoff(self):
        """twinkle=0 must reproduce the old hard-cutoff behaviour exactly."""
        anchors = _anchors()
        min_d = anchors[0]["diam"]
        star = [(50.0, 50.0, min_d - 1.0, 1.0, (1.0, 1.0, 1.0), False, None)]
        layer = fs.render_spike_layer((120, 120), 0, 0, 120, 120, star, _cfg(anchors, twinkle=0.0))
        self.assertEqual(float(layer.max()), 0.0)

    def test_nonzero_twinkle_draws_something_below_cutoff(self):
        anchors = _anchors()
        min_d = anchors[0]["diam"]
        star = [(50.0, 50.0, min_d - 1.0, 1.0, (1.0, 1.0, 1.0), False, None)]
        layer = fs.render_spike_layer((120, 120), 0, 0, 120, 120, star, _cfg(anchors, twinkle=30.0))
        self.assertGreater(float(layer.max()), 0.0)

    def test_twinkle_is_much_weaker_than_the_smallest_anchors_own_look(self):
        """The floor must read as a hint, not as big as an actual Small star."""
        anchors = _anchors()
        min_d = anchors[0]["diam"]
        below = [(50.0, 50.0, min_d - 1.0, 1.0, (1.0, 1.0, 1.0), False, None)]
        at = [(50.0, 50.0, min_d, 1.0, (1.0, 1.0, 1.0), False, None)]
        twinkle_layer = fs.render_spike_layer((120, 120), 0, 0, 120, 120, below,
                                              _cfg(anchors, twinkle=fs.SPIKE_DEFAULTS["twinkle"]))
        small_layer = fs.render_spike_layer((120, 120), 0, 0, 120, 120, at, _cfg(anchors, twinkle=0.0))
        self.assertLess(float(twinkle_layer.sum()), float(small_layer.sum()))

    def test_twinkle_does_not_change_stars_above_the_cutoff(self):
        """The floor only fills in stars that would otherwise get nothing -
        it must not add to or replace the normal per-size look."""
        anchors = _anchors()
        min_d = anchors[0]["diam"]
        star = [(50.0, 50.0, min_d + 5.0, 1.0, (1.0, 1.0, 1.0), False, None)]
        a = fs.render_spike_layer((120, 120), 0, 0, 120, 120, star, _cfg(anchors, twinkle=0.0))
        b = fs.render_spike_layer((120, 120), 0, 0, 120, 120, star,
                                  _cfg(anchors, twinkle=fs.SPIKE_DEFAULTS["twinkle"]))
        self.assertTrue(np.array_equal(a, b))

    def test_forced_and_manual_stars_below_cutoff_unaffected_by_twinkle_key(self):
        """A Ctrl+Click-forced star already gets the full anchor look
        regardless of twinkle - twinkle must not interfere with that path."""
        anchors = _anchors()
        min_d = anchors[0]["diam"]
        star = [(50.0, 50.0, min_d - 1.0, 1.0, (1.0, 1.0, 1.0), True, None)]
        a = fs.render_spike_layer((120, 120), 0, 0, 120, 120, star, _cfg(anchors, twinkle=0.0))
        b = fs.render_spike_layer((120, 120), 0, 0, 120, 120, star,
                                  _cfg(anchors, twinkle=fs.SPIKE_DEFAULTS["twinkle"]))
        self.assertTrue(np.array_equal(a, b))


class TestRainbowDefaults(unittest.TestCase):
    def test_small_stars_have_no_rainbow_and_it_grows_with_size(self):
        """The rainbow is now the physical diffraction pattern (see
        _diffraction_mult), not an artificial hue cycle - on by default,
        but only where a star is big enough to show it."""
        anchors = fs.SPIKE_DEFAULTS["anchors"]
        self.assertEqual(anchors[0]["rainbow"], 0.0)
        self.assertLessEqual(anchors[1]["rainbow"], anchors[2]["rainbow"])
        self.assertGreater(anchors[2]["rainbow"], 0.0)

    def test_chroma_parameter_is_gone(self):
        self.assertNotIn("chroma", fs._ANCHOR_PARAM_KEYS)


class TestRingBlend(unittest.TestCase):
    def test_ring_width_scales_with_its_own_radius(self):
        """The ring's Gaussian width must be a sizeable fraction of its own
        radius (a soft bump), not a small fixed fraction of the star's fwhm
        (a crisp thin circle) - otherwise it reads as a separate ring shape,
        which the reference photo does not show at all."""
        layer = np.zeros((400, 400, 3), np.float32)
        radius, width = 60.0, fs.ring_width_for_radius(60.0, fwhm_px=10.0)
        fs._add_ring_flare(layer, 200, 200, radius, width, 0.5)
        prof = layer[200, 200:, 1]
        # a crisp ring has near-zero brightness at the centre; a soft bump
        # stays clearly lit most of the way from the core to the ring peak
        self.assertGreater(float(prof[int(radius * 0.4)]), 0.15)

    def test_ring_width_grows_with_radius(self):
        w1 = fs.ring_width_for_radius(10.0, fwhm_px=8.0)
        w2 = fs.ring_width_for_radius(40.0, fwhm_px=8.0)
        self.assertGreater(w2, w1)


if __name__ == "__main__":
    unittest.main()
