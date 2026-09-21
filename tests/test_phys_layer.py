import time
import unittest
import numpy as np
from _harness import fs, star_field

FULL = {"depth": 85.0, "extent": 20.0, "spikes": 100.0, "vane": 1.0, "rings": 100.0,
        "obstruction": 30.0, "dispersion": 100.0, "color": 60.0, "streaks": 0.0, "streak_len": 8.0}


def cfg(fft_from=15.0, **over):
    a = dict(FULL, **over)
    return {"anchors": [dict(a, diam=3.0), dict(a, diam=8.0), dict(a, diam=18.0)],
            "aperture": "spider4", "blades": 6, "rotation": 0.0, "fft_from": fft_from}


def one_star(fwhm, x=300.0, y=300.0, forced=False, override=None):
    return [(x, y, fwhm, 1.0, (1.0, 0.9, 0.8), forced, override)]


def render(stars, c, shape=(600, 600)):
    return fs.render_physical_layer(shape, 0, 0, shape[1], shape[0], stars, c)


class TestLayer(unittest.TestCase):
    def test_tables(self):
        self.assertEqual(len(fs._PHYS_PARAM_KEYS), 10)
        for a in fs.PHYS_DEFAULTS["anchors"]:
            self.assertEqual(set(a), set(fs._PHYS_PARAM_KEYS))
        self.assertEqual(set(fs.PHYS_UNIFORM_DEFAULTS), set(fs._PHYS_PARAM_KEYS))
        self.assertFalse(fs.PHYS_DEFAULTS["enabled"])

    def test_empty_and_range(self):
        self.assertEqual(float(render([], cfg()).max()), 0.0)
        out = render(one_star(9.0), cfg(fft_from=200.0))
        self.assertEqual(out.dtype, np.float32)
        self.assertGreater(float(out.max()), 0.05)
        self.assertLessEqual(float(out.max()), 1.0)

    def test_below_min_diameter_is_skipped_unless_forced(self):
        self.assertEqual(float(render(one_star(1.5), cfg()).max()), 0.0)
        self.assertGreater(float(render(one_star(1.5, forced=True), cfg()).max()), 0.0)

    def test_override_used_verbatim(self):
        out = render(one_star(1.5, override=dict(FULL, depth=0.0)), cfg())
        self.assertEqual(float(out.max()), 0.0)

    def test_streaks_work_without_depth(self):
        out = render(one_star(9.0), cfg(depth=0.0, streaks=100.0))
        self.assertGreater(float(out.max()), 0.02)

    def test_analytic_and_fft_agree_in_total_light(self):
        star = one_star(14.0)
        a = render(star, cfg(fft_from=200.0))
        f = render(star, cfg(fft_from=8.0))
        ratio = float(f.sum()) / float(a.sum())
        self.assertGreater(ratio, 0.75, msg=f"ratio={ratio:.2f}")
        self.assertLess(ratio, 1.33, msg=f"ratio={ratio:.2f}")

    def test_blend_zone_is_between_the_branches(self):
        # fft_from=15 -> blend zone 9.4..15: fwhm 12 must sit between pure analytic and pure FFT
        star = one_star(12.0)
        a = float(render(star, cfg(fft_from=200.0)).sum())
        f = float(render(star, cfg(fft_from=8.0)).sum())
        b = float(render(star, cfg(fft_from=15.0)).sum())
        lo, hi = min(a, f), max(a, f)
        self.assertGreaterEqual(b, 0.9 * lo)
        self.assertLessEqual(b, 1.1 * hi)

    def test_view_offset_matches_full_frame(self):
        star = one_star(9.0, x=420.0, y=380.0)
        c = cfg(fft_from=200.0)
        full = render(star, c, (600, 600))
        crop = fs.render_physical_layer((200, 200), 320, 280, 200, 200, star, c)
        self.assertTrue(np.allclose(full[280:480, 320:520], crop, atol=1e-6))

    def test_speed_300_analytic_stars(self):
        stars = [s for s in star_field(300, 1200, 900, seed=3)]
        t0 = time.time()
        out = fs.render_physical_layer((900, 1200), 0, 0, 1200, 900, stars, cfg(fft_from=200.0))
        dt = time.time() - t0
        print(f"[speed] 300 stars, 1200x900 analytic: {dt:.2f}s")
        self.assertGreater(float(out.max()), 0.0)
        self.assertLess(dt, 30.0)


if __name__ == "__main__":
    unittest.main()
