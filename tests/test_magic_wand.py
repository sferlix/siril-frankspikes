"""Magic Wand: auto white balance/levels (compute_auto_tone) and the
single source of truth for focal-length-derived spike defaults
(compute_focal_calibration), plus the App-level button that ties them
together - see App._on_magic_wand."""
import unittest
import numpy as np
from _harness import fs


class TestComputeAutoTone(unittest.TestCase):
    def test_returns_exactly_the_four_expected_keys(self):
        rgb = np.full((20, 20, 3), 0.3, dtype=np.float32)
        out = fs.compute_auto_tone(rgb)
        self.assertEqual(set(out.keys()), {"temperature", "tint", "blacks", "whites"})

    def _astro_like_image(self, seed=0, star_value=0.9, bg=0.06):
        """A dark, mostly-background field with a few bright "star" pixels
        - a much more representative fixture for an auto-levels test than
        a uniform gray frame (which has no real black/white point to find
        at all, and every editor's auto-levels does something extreme on
        one). At least 2% of pixels are "stars", comfortably above the
        99.5th-percentile threshold compute_auto_tone reads its white
        point from - fewer than that and the percentile lands back in the
        background noise instead, which is a real (if unusual) failure
        mode of any percentile-based auto-levels on a very sparse field,
        not something to paper over in the fixture... except here, where
        the point is to test the common case."""
        rng = np.random.default_rng(seed)
        rgb = np.clip(bg + rng.normal(0, 0.01, (60, 60, 3)), 0, 1).astype(np.float32)
        n_stars = 120  # 120/3600 = 3.3% of the frame
        ys = rng.integers(0, 60, size=n_stars)
        xs = rng.integers(0, 60, size=n_stars)
        rgb[ys, xs] = star_value
        return rgb

    def test_already_well_leveled_astro_image_needs_little_correction(self):
        rgb = self._astro_like_image(bg=0.03, star_value=0.95)
        out = fs.compute_auto_tone(rgb)
        self.assertLess(abs(out["temperature"]), 5.0)
        self.assertLess(abs(out["tint"]), 5.0)
        self.assertLess(abs(out["blacks"]), 15.0)
        self.assertLess(abs(out["whites"]), 15.0)

    def test_lifted_background_gets_pulled_back_toward_black(self):
        """A background that's noticeably above true black (e.g. an
        under-stretched or fogged sub) should get a positive Blacks
        correction pulling it back down."""
        rgb = self._astro_like_image(bg=0.22, star_value=0.9)
        out = fs.compute_auto_tone(rgb)
        self.assertGreater(out["blacks"], 5.0)

    def test_green_background_cast_is_corrected_with_positive_tint(self):
        """A light-pollution-style green cast in the (dark) background:
        apply_cosmetics' tint formula is G' = G - tint_shift, R'/B' get
        +0.5*tint_shift - so countering excess green needs a POSITIVE
        tint (confirmed by re-applying the correction: R'=G'=B' only when
        tint is positive here), not negative."""
        rgb = np.full((40, 40, 3), 0.08, dtype=np.float32)
        rgb[..., 1] += 0.05  # greenish background
        out = fs.compute_auto_tone(rgb)
        self.assertGreater(out["tint"], 1.0)
        # Verify it actually neutralizes the cast when re-applied.
        corrected = fs.apply_cosmetics(rgb, {**fs.TONE_DEFAULTS, **out})
        r, g, b = [float(np.mean(corrected[..., i])) for i in range(3)]
        self.assertAlmostEqual(r, g, places=2)
        self.assertAlmostEqual(g, b, places=2)

    def test_blue_heavy_background_shifts_temperature_warm(self):
        rgb = np.full((40, 40, 3), 0.08, dtype=np.float32)
        rgb[..., 2] += 0.06  # blue-heavy (cool) background
        out = fs.compute_auto_tone(rgb)
        self.assertGreater(out["temperature"], 1.0)

    def test_low_dynamic_range_image_gets_levels_stretched(self):
        rng = np.random.default_rng(1)
        rgb = np.clip(0.4 + rng.normal(0, 0.02, (40, 40, 3)), 0.3, 0.5).astype(np.float32)
        out = fs.compute_auto_tone(rgb)
        # Never touched 0 or 1 - blacks should raise the floor, whites
        # should lower the ceiling (both push the narrow range outward).
        self.assertGreater(out["blacks"], 1.0)
        self.assertGreater(out["whites"], 1.0)

    def test_result_stays_within_slider_ranges(self):
        rgb = np.zeros((10, 10, 3), dtype=np.float32)
        rgb[..., 0] = 1.0  # extreme, adversarial cast
        out = fs.compute_auto_tone(rgb)
        self.assertLessEqual(abs(out["temperature"]), 50.0)
        self.assertLessEqual(abs(out["tint"]), 50.0)
        self.assertLessEqual(abs(out["blacks"]), 100.0)
        self.assertLessEqual(abs(out["whites"]), 100.0)


class TestComputeFocalCalibration(unittest.TestCase):
    def test_invalid_focal_length_returns_all_none(self):
        calib = fs.compute_focal_calibration(None)
        self.assertEqual(calib, {"length_scale": None, "thickness_scale": None,
                                   "intensity_scale": None, "diam_scale": None})
        self.assertEqual(fs.compute_focal_calibration(0), calib)
        self.assertEqual(fs.compute_focal_calibration(-100.0), calib)

    def test_length_scale_matches_focal_length_to_spike_length(self):
        calib = fs.compute_focal_calibration(500.0)
        expected = fs._focal_length_to_spike_length(500.0) / fs.SPIKE_UNIFORM_DEFAULTS["length"]
        self.assertAlmostEqual(calib["length_scale"], expected, places=6)

    def test_all_scales_are_one_at_the_medium_reference(self):
        calib = fs.compute_focal_calibration(fs._FOCAL_LENGTH_REF2_MM)
        self.assertAlmostEqual(calib["thickness_scale"], 1.0, places=6)
        self.assertAlmostEqual(calib["intensity_scale"], 1.0, places=6)
        self.assertAlmostEqual(calib["diam_scale"], 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
