"""Physical diffraction rainbow along the main spikes (see
_diffraction_mult/_add_spike_ray). Modelled on reference photos: a spike
starts in the star's own colour, then breaks into short coloured segments
with dimmer gaps whose spacing is a property of the optics (the same in px
for every star), and washes back to neutral after a few orders."""
import colorsys
import unittest
import numpy as np
from _harness import fs


def _hue_sat(rgb):
    rgb = np.asarray(rgb, dtype=float)
    h, s, _v = colorsys.rgb_to_hsv(*(rgb / max(rgb.max(), 1e-9)))
    return h * 360.0, s


class TestDiffractionMult(unittest.TestCase):
    def _mult(self, dist, period=50.0, amount=100.0, saturation=100.0):
        r, g, b = fs._diffraction_mult(np.asarray(dist, dtype=np.float32), period,
                                       amount, saturation)
        return np.stack([r, g, b], axis=-1)

    def test_off_is_identity(self):
        d = np.linspace(0, 300, 50)
        self.assertTrue(np.allclose(self._mult(d, amount=0.0), 1.0))
        self.assertTrue(np.allclose(self._mult(d, period=0.0), 1.0))

    def test_starts_in_the_star_colour(self):
        near = self._mult([2.0])[0]
        self.assertTrue(np.allclose(near, 1.0, atol=0.03), near)

    def test_coloured_segments_after_the_first_null(self):
        d = np.arange(50.0, 150.0, 2.0)
        m = self._mult(d)
        hues = [_hue_sat(c)[0] for c in m if _hue_sat(c)[1] > 0.1]
        # several distinct hues across the first couple of orders
        spread = np.ptp(np.unwrap(np.radians(hues))) * 180 / np.pi
        self.assertGreater(len(hues), 10)
        self.assertGreater(spread, 180.0)

    def test_spacing_scales_with_period(self):
        d = np.arange(0.0, 200.0, 1.0)
        a = self._mult(d, period=40.0)
        b = self._mult(d * 2.0, period=80.0)
        self.assertTrue(np.allclose(a, b, atol=1e-5))

    def test_segments_dim_at_the_nulls(self):
        lum = self._mult(np.arange(0.0, 200.0, 1.0)).mean(axis=-1)
        self.assertLess(lum[40:80].min(), 0.8)
        self.assertGreater(lum[40:80].min(), 0.3)

    def test_washes_out_far_away(self):
        d = np.arange(0.0, 800.0, 1.0)
        sat = np.array([_hue_sat(c)[1] for c in self._mult(d)])
        self.assertLess(sat[600:].max(), sat[50:150].max() * 0.6)

    def test_zero_saturation_keeps_segments_but_grey(self):
        m = self._mult(np.arange(50.0, 150.0, 2.0), saturation=0.0)
        self.assertTrue(np.allclose(m[:, 0], m[:, 1]) and np.allclose(m[:, 1], m[:, 2]))
        self.assertLess(m.min(), 0.9)


class TestSpikeRainbowInRender(unittest.TestCase):
    def _cfg(self, rainbow, period=40.0):
        anchor = {"diam": 5.0, "length": 12.0, "intensity": 100.0, "thickness": 1.5,
                  "soft_flare": 0.0, "flare_reach": 45.0, "ring_flare": 0.0, "ring_diam": 1.6,
                  "flare_saturation": 0.0, "flare_rays": 0.0,
                  "rainbow": rainbow, "saturation": 100.0}
        return {"anchors": [anchor, dict(anchor, diam=50.0)], "rays": 4, "rotation": 0.0,
                "hue": 0.0, "sharpness": 100.0, "variation": 0.0, "twinkle": 0.0,
                "rainbow_period": period}

    def _row(self, fwhm, rainbow, out=400, view=400):
        stars = [(20.0, 200.0, fwhm, 1.0, (1.0, 1.0, 1.0), False, None)]
        layer = fs.render_spike_layer((out, out), 0, 0, view, view, stars, self._cfg(rainbow))
        return layer[out // 2]

    def test_period_is_the_same_for_every_star_size(self):
        """Two stars of different size (so different spike lengths) show
        their colour segments at the same distances from the star."""
        small = self._row(15.0, 100.0)
        big = self._row(25.0, 100.0)
        # compare hue in the region both cover, well inside both spikes
        checked = 0
        for x in range(60, 150, 3):
            hs, ss = _hue_sat(small[x])
            hb, sb = _hue_sat(big[x])
            if ss > 0.15 and sb > 0.15:
                checked += 1
                dh = abs((hs - hb + 180) % 360 - 180)
                self.assertLess(dh, 40.0, f"x={x}: {hs:.0f} vs {hb:.0f}")
        self.assertGreater(checked, 5)

    def test_rainbow_zero_keeps_star_colour(self):
        row = self._row(20.0, 0.0)
        for x in range(40, 200, 10):
            if row[x].max() > 0.02:
                self.assertLess(_hue_sat(row[x])[1], 0.02)

    def test_zoom_consistency(self):
        """Fit preview (half scale) and full resolution put the segments at
        the same real-image distance."""
        full = self._row(20.0, 100.0, out=400, view=400)
        half = self._row(20.0, 100.0, out=200, view=400)
        agree = 0
        total = 0
        for x_full in range(80, 200, 8):
            hf, sf = _hue_sat(full[x_full])
            hh, sh = _hue_sat(half[(x_full - 20) // 2 + 10])
            if sf > 0.15 and sh > 0.15:
                total += 1
                agree += abs((hf - hh + 180) % 360 - 180) < 45
        self.assertGreater(total, 5)
        self.assertGreaterEqual(agree / total, 0.7)


if __name__ == "__main__":
    unittest.main()
