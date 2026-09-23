"""Soft flare with ray structure ("Flare rays" + global "Flare ray
symmetry") - replaces the old separate Ray flare. Modelled on reference
photos: the sunburst is a modulation of the halo itself, 24-48 soft,
irregularly spaced streaks of uneven brightness, more of them further out,
the strongest hugging the main spikes."""
import unittest
import numpy as np
from _harness import fs


def _anchor(**over):
    # length 10 x fwhm 20 = 200px spike, reach 45% = 90px
    a = {"diam": 8.0, "length": 10.0, "intensity": 0.0, "thickness": 1.1,
         "soft_flare": 60.0, "flare_reach": 45.0, "flare_rays": 70.0,
         "ring_flare": 0.0, "ring_diam": 1.6, "flare_saturation": 0.0,
         "rainbow": 0.0, "saturation": 100.0}
    a.update(over)
    return a


def _render(anchor, symmetry=40.0, w=400, h=400, x=None, y=None, out=None, rotation=30.0,
            rays=4):
    x = w / 2 if x is None else x
    y = h / 2 if y is None else y
    star = [(x, y, 20.0, 1.0, (1.0, 1.0, 1.0), True, None)]
    cfg = {"anchors": [dict(anchor, diam=3.0), dict(anchor, diam=40.0)], "rays": rays,
           "rotation": rotation, "hue": 0.0, "sharpness": 100.0, "variation": 0.0,
           "twinkle": 0.0, "flare_symmetry": symmetry}
    oh, ow = out or (h, w)
    return fs.render_spike_layer((oh, ow), 0, 0, w, h, star, cfg)[..., 0]


def _ring(img, cx, cy, r, n=1440, dr=None):
    """Angular profile at radius r, averaged over a thin annulus (bilinear
    samples) so thin rays aren't split into several peaks by pixel
    rounding."""
    from scipy import ndimage as ndi
    dr = max(1.0, r * 0.05) if dr is None else dr
    t = np.radians(np.arange(n) * 360.0 / n)
    out = np.zeros(n)
    radii = np.linspace(r - dr, r + dr, 5)
    for rr in radii:
        out += ndi.map_coordinates(img, [cy + rr * np.sin(t), cx + rr * np.cos(t)], order=1)
    return out / len(radii)


def _count_peaks(v, rel=0.08):
    base = np.convolve(np.r_[v[-60:], v, v[:60]], np.ones(121) / 121, "valid")
    d = v - base
    thr = rel * v.mean()
    peaks = (d > thr) & (d >= np.roll(d, 1)) & (d > np.roll(d, -1))
    return int(peaks.sum())


class TestFlareRays(unittest.TestCase):
    def test_zero_rays_is_the_plain_round_glow(self):
        img = _render(_anchor(flare_rays=0.0))
        v = _ring(img, 200, 200, 30)
        self.assertLess(v.std() / v.mean(), 0.03)

    def test_rays_break_the_glow_into_many_irregular_streaks(self):
        img = _render(_anchor())
        v = _ring(img, 200, 200, 40)
        self.assertGreater(v.std() / v.mean(), 0.15)
        n = _count_peaks(v)
        self.assertGreaterEqual(n, 16)
        self.assertLessEqual(n, 60)

    def test_more_rays_further_out(self):
        img = _render(_anchor())
        self.assertGreaterEqual(_count_peaks(_ring(img, 200, 200, 70)),
                                _count_peaks(_ring(img, 200, 200, 25)))

    def test_rays_sit_on_a_halo_not_lines_on_black(self):
        """Between the rays the smooth halo is still there - the rays are
        structure in the flare, not bare lines on a black background."""
        plain = _ring(_render(_anchor(flare_rays=0.0)), 200, 200, 40).mean()
        v = _ring(_render(_anchor()), 200, 200, 40)
        self.assertGreater(np.percentile(v, 5), plain * 0.3)
        self.assertGreater(v.mean(), plain)

    def test_strongest_rays_hug_the_main_spikes(self):
        img = _render(_anchor(), rotation=30.0)
        v = _ring(img, 200, 200, 45)
        ang = np.arange(len(v)) * 360.0 / len(v)
        d = np.min([np.abs((ang - s + 180) % 360 - 180) for s in (30, 120, 210, 300)], axis=0)
        self.assertGreater(v[d < 10].mean(), v[d >= 10].mean())

    def test_full_symmetry_repeats_every_wedge(self):
        img = _render(_anchor(), symmetry=100.0)
        v = _ring(img, 200, 200, 45)
        q = len(v) // 4
        corr = np.corrcoef(v, np.roll(v, q))[0, 1]
        self.assertGreater(corr, 0.9)

    def test_six_ray_full_symmetry_repeats_every_60_degrees(self):
        img = _render(_anchor(), symmetry=100.0, rays=6)
        v = _ring(img, 200, 200, 45)
        self.assertGreater(np.corrcoef(v, np.roll(v, len(v) // 6))[0, 1], 0.9)

    def test_six_ray_default_has_many_rays(self):
        img = _render(_anchor(), rays=6)
        self.assertGreaterEqual(_count_peaks(_ring(img, 200, 200, 45)), 16)

    def test_partial_symmetry_is_irregular(self):
        img = _render(_anchor(), symmetry=0.0)
        v = _ring(img, 200, 200, 45)
        q = len(v) // 4
        self.assertLess(np.corrcoef(v, np.roll(v, q))[0, 1], 0.8)

    def test_deterministic_and_differs_per_star(self):
        a = _render(_anchor())
        b = _render(_anchor())
        self.assertTrue(np.array_equal(a, b))
        c = _render(_anchor(), x=201.0, y=207.0)
        va, vc = _ring(a, 200, 200, 45), _ring(c, 201, 207, 45)
        self.assertLess(np.corrcoef(va, vc)[0, 1], 0.9)

    def test_ends_at_its_reach_with_no_box_edge(self):
        img = _render(_anchor(), w=500, h=500)
        yy, xx = np.mgrid[0:500, 0:500]
        r = np.hypot(xx - 250, yy - 250)
        self.assertEqual(float(img[r > 91].max()), 0.0)
        # ... while the rays are clearly visible well inside it
        self.assertGreater(img[(r > 30) & (r < 50)].max(), 0.05)

    def test_same_pattern_at_fit_preview_scale(self):
        full = _render(_anchor(), w=400, h=400)
        half = _render(_anchor(), w=400, h=400, out=(200, 200))
        vf, vh = _ring(full, 200, 200, 50), _ring(half, 100, 100, 25)
        self.assertGreater(np.corrcoef(vf, vh)[0, 1], 0.85)

    def test_old_ray_flare_parameters_are_gone(self):
        for k in ("ray_flare", "ray_flare_length"):
            self.assertNotIn(k, fs._ANCHOR_PARAM_KEYS)
        self.assertNotIn("ray_flare_count", fs.SPIKE_DEFAULTS)
        self.assertIn("flare_rays", fs._ANCHOR_PARAM_KEYS)


if __name__ == "__main__":
    unittest.main()
