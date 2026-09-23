"""Magic Wands: the Camera RAW one (compute_tone_wand) and the spike one (compute_spike_wand), and the
single source of truth for focal-length-derived spike defaults
(compute_focal_calibration), plus the App-level button that ties them
together - see App._on_magic_wand."""
import unittest
import numpy as np
from _harness import fs


def _sky(level=0.08, cast=(0.0, 0.0, 0.0), noise=0.004, size=400, seed=0, stars=60,
         core_frac=0.0):
    """A stretched sky background (level, per-channel cast, gaussian noise)
    with some stars, optionally with a blown-out extended core covering
    core_frac of the frame."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size, 3), level, np.float32) + np.array(cast, np.float32)
    img += rng.normal(0, noise, img.shape).astype(np.float32)
    yy, xx = np.mgrid[0:size, 0:size]
    for _ in range(stars):
        cx, cy, s = rng.uniform(10, size - 10), rng.uniform(10, size - 10), rng.uniform(1.0, 2.5)
        img += (0.9 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s)))[..., None]
    if core_frac > 0:
        r = np.sqrt(core_frac * size * size / np.pi)
        img[np.hypot(xx - size / 2, yy - size / 2) < r] = 1.0
    return np.clip(img, 0, 1)


def _stars(fwhms, h=400):
    return [(10.0 + i, h * (0.1 + 0.8 * (i % 7) / 7), float(f), 1.0) for i, f in enumerate(fwhms)]


# the finishing moves' fixed conservative ranges (Temperature/Tint/Blacks/
# Whites come from the auto white balance/levels, see compute_auto_tone)
RANGES = {"highlights": (-15, -5), "shadows": (5, 12), "texture": (5, 10), "clarity": (0, 0),
          "dehaze": (0, 0), "vibrance": (8, 15), "saturation": (0, 0)}


def _luma(x):
    return 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]


def _sky_stats(img, out):
    """(median sky luma before, after, sky RGB after) on the darkest 40%."""
    bg = _luma(img) <= np.percentile(_luma(img), 40)
    return float(np.median(_luma(img)[bg])), float(np.median(_luma(out)[bg])), out[bg].mean(0)


class TestMagicWandTone(unittest.TestCase):
    def _tone(self, img):
        return fs.magic_wand_tone(fs.analyze_image_tone(img), img)

    def test_finishing_values_stay_in_their_conservative_ranges(self):
        for img in (_sky(), _sky(level=0.3), _sky(cast=(-0.01, 0.03, -0.01)),
                    _sky(noise=0.05), _sky(core_frac=0.05), _sky(level=0.01)):
            tone = self._tone(img)
            self.assertEqual(set(tone), set(fs.TONE_DEFAULTS) - {"exposure", "contrast"})
            for k, (lo, hi) in RANGES.items():
                self.assertTrue(lo <= tone[k] <= hi, f"{k}={tone[k]} not in {lo}..{hi}")
            for k, _label, lo, hi, _step, _fmt in fs.TONE_PARAM_DEFS:
                if k in tone:
                    self.assertTrue(lo <= tone[k] <= hi)

    def test_colour_casts_are_neutralised_on_the_sky(self):
        for cast in ((-0.01, 0.02, -0.01), (0.03, 0.0, -0.03)):
            img = _sky(cast=cast)
            _b, _a, rgb = _sky_stats(img, fs.apply_cosmetics(img, self._tone(img)))
            before = img[_luma(img) <= np.percentile(_luma(img), 40)].mean(0)
            self.assertLess(np.ptp(rgb), np.ptp(before) * 0.5)

    def test_shadows_do_not_wash_out_the_sky(self):
        """Shadows +5..+12 lifts everything below mid-grey in this app;
        the black point, solved after it, keeps the sky from getting
        lighter."""
        img = _sky(level=0.08)
        tone = self._tone(img)
        self.assertGreaterEqual(tone["shadows"], 5)
        before, after, _ = _sky_stats(img, fs.apply_cosmetics(img, tone))
        self.assertLessEqual(after, before + 0.005)

    def test_washed_out_sky_gets_darker(self):
        img = _sky(level=0.30)
        tone = self._tone(img)
        self.assertGreater(tone["blacks"], 0)
        before, after, _ = _sky_stats(img, fs.apply_cosmetics(img, tone))
        self.assertLess(after, before - 0.05)

    def test_noise_lowers_shadows_and_texture(self):
        clean, noisy = self._tone(_sky(noise=0.003)), self._tone(_sky(noise=0.06))
        self.assertGreater(clean["shadows"], noisy["shadows"])
        self.assertGreater(clean["texture"], noisy["texture"])

    def test_blown_cores_push_highlights_toward_minus_15(self):
        plain, blown = self._tone(_sky(stars=5)), self._tone(_sky(core_frac=0.05))
        self.assertLess(blown["highlights"], plain["highlights"])
        self.assertEqual(blown["highlights"], -15.0)


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


class TestMagicWandFocalAndSpikes(unittest.TestCase):
    def test_declared_focal_length_wins(self):
        ftype, f, src, _ = fs.estimate_field_type(1400.0, _stars([2.0] * 50), (400, 400))
        self.assertEqual((ftype, f, src), ("long", 1400.0, "declared"))
        self.assertEqual(fs.estimate_field_type(50.0, [], (400, 400))[0], "wide")

    def test_estimate_from_stars(self):
        big = fs.estimate_field_type(None, _stars([7.0] * 30, h=2000), (2000, 2000))
        self.assertEqual((big[0], big[2]), ("long", "estimated"))
        small_dense = fs.estimate_field_type(None, _stars([2.0] * 400, h=1000), (1000, 1000))
        self.assertEqual(small_dense[0], "wide")

    def test_landscape_foreground_reads_as_wide_field(self):
        stars = [(float(i), 50.0 + (i % 40), 4.0, 1.0) for i in range(60)]   # all near the top
        self.assertEqual(fs.estimate_field_type(None, stars, (400, 400))[0], "wide")

    def test_spike_values_follow_focal_length_within_the_ranges(self):
        many = _stars(np.linspace(2, 40, 200))
        g_s, a_s, _s, _ = fs.magic_wand_spikes(35.0, many, 30.0)
        g_l, a_l, _s, _ = fs.magic_wand_spikes(1500.0, many, 30.0)
        self.assertEqual((g_s["sharpness"], g_l["sharpness"]), (95.0, 55.0))
        self.assertEqual((a_s[2]["length"], a_l[2]["length"]), (12.0, 8.0))     # Large tab
        self.assertEqual((a_s[2]["thickness"], a_l[2]["thickness"]), (0.6, 1.0))
        for anchors in (a_s, a_l):
            lg = anchors[2]
            self.assertTrue(120 <= lg["intensity"] <= 170)
            self.assertTrue(30 <= lg["rainbow"] <= 50 and 60 <= lg["saturation"] <= 80)
            self.assertTrue(10 <= lg["soft_flare"] <= 20 and 30 <= lg["flare_reach"] <= 50)
            self.assertTrue(anchors[0]["diam"] < anchors[1]["diam"] < anchors[2]["diam"])
            for tab, anchor in enumerate(anchors):
                for k, v in anchor.items():
                    lo, hi = fs.spike_anchor_slider_range(tab, k)
                    self.assertTrue(lo <= v <= hi + 0.05, f"tab {tab} {k}={v}")
        for g in (g_s, g_l):
            self.assertTrue(10 <= g["variation"] <= 20 and 10 <= g["twinkle"] <= 20)

    def test_only_the_standout_stars_get_spikes(self):
        rng = np.random.default_rng(1)
        f = np.exp(rng.normal(np.log(3.5), 0.25, 1500))
        f[:30] = rng.uniform(10, 25, 30)
        for fw in (f, 2 * np.round(f / 2)):          # continuous and detector-quantized
            for focal in (35.0, 300.0, 1200.0):
                _g, anchors, _s, info = fs.magic_wand_spikes(focal, _stars(fw), 30.0)
                cutoff = anchors[0]["diam"]
                self.assertLessEqual(np.mean(fw >= cutoff), fs.MAGIC_WAND_SPIKED_FRACTION)
                self.assertGreater(np.count_nonzero(fw >= cutoff), 0)
                self.assertEqual(info["n_spiked"], int(np.count_nonzero(fw >= cutoff)))

    def test_focal_target_raises_the_cutoff_but_never_past_the_biggest_star(self):
        fw = np.linspace(2, 8, 100)
        cut_short = fs.magic_wand_spikes(35.0, _stars(fw), 30.0)[1][0]["diam"]
        cut_long = fs.magic_wand_spikes(1500.0, _stars(fw), 30.0)[1][0]["diam"]
        self.assertLessEqual(cut_short, cut_long)
        self.assertLessEqual(cut_long, 8.0)

    def test_a_shared_size_is_not_let_in_as_a_block(self):
        fw = [4.0] * 95 + [10.0] * 5
        cutoff = fs.magic_wand_spikes(35.0, _stars(fw), 30.0)[1][0]["diam"]
        self.assertGreater(cutoff, 4.0)

    def test_all_stars_the_same_size_spikes_none(self):
        _g, anchors, _s, info = fs.magic_wand_spikes(300.0, _stars([4.0] * 100), 30.0)
        self.assertGreater(anchors[0]["diam"], 4.0)
        self.assertIsNotNone(info["note"])

    def test_simple_mode_values(self):
        """Simple mode: the look at full value, and a Minimum diameter that
        keeps noticeable (>= 10% strength) spikes to <= ~12% of the stars
        while the biggest 2% reach half strength."""
        rng = np.random.default_rng(1)
        f = np.exp(rng.normal(np.log(3.5), 0.25, 1500))
        f[:30] = rng.uniform(10, 25, 30)
        for fw in (f, 2 * np.round(f / 2)):
            for focal in (35.0, 300.0, 1200.0):
                _g, _a, simple, info = fs.magic_wand_spikes(focal, _stars(fw), 30.0)
                m = simple["min_diam"]
                self.assertEqual(m, round(m))
                self.assertLessEqual(np.mean(fw >= m * fs._SIMPLE_NOTICEABLE_MULT),
                                     fs.MAGIC_WAND_SPIKED_FRACTION)
                self.assertGreaterEqual(np.mean(fw >= 2 * m), 0.02)
                self.assertIsNone(info["simple_note"])
        _g, _a, s_short, _ = fs.magic_wand_spikes(35.0, _stars(f), 30.0)
        _g, _a, s_long, _ = fs.magic_wand_spikes(1500.0, _stars(f), 30.0)
        self.assertEqual((s_short["length"], s_long["length"]), (12.0, 8.0))
        self.assertEqual((s_short["thickness"], s_long["thickness"]), (0.6, 1.0))
        self.assertEqual(s_short["saturation"], 70.0)   # full range, no tab ceiling

    def test_simple_mode_says_when_sizes_are_too_similar(self):
        _g, _a, simple, info = fs.magic_wand_spikes(300.0, _stars(np.linspace(2, 8, 300)), 30.0)
        self.assertIsNotNone(info["simple_note"])

    def test_report_describes_the_mode_it_was_written_to(self):
        stars = _stars(np.linspace(2, 20, 100))
        self.assertIn("SPIKES (Simple mode)", fs.compute_spike_wand(stars, None, (400, 400))["report"])
        self.assertIn("SPIKES (Per size mode)",
                      fs.compute_spike_wand(stars, None, (400, 400), mode="per_size")["report"])

    def test_rotation_kept_when_natural_else_30(self):
        self.assertEqual(fs.magic_wand_spikes(300.0, [], 12.0)[0]["rotation"], 12.0)
        self.assertEqual(fs.magic_wand_spikes(300.0, [], 80.0)[0]["rotation"], 30.0)

    def test_each_wand_is_idempotent_and_reports_its_own_part(self):
        img = _sky(cast=(0.0, 0.02, 0.0))
        t1, t2 = fs.compute_tone_wand(img), fs.compute_tone_wand(img)
        self.assertEqual(t1["tone"], t2["tone"])
        self.assertEqual(t1["report"], t2["report"])
        self.assertIn("Sky background", t1["report"])
        self.assertNotIn("FOCAL LENGTH", t1["report"])
        self.assertNotIn("spike_anchors", t1)

        s1 = fs.compute_spike_wand(_stars([3, 4, 5, 9]), None, img.shape)
        s2 = fs.compute_spike_wand(_stars([3, 4, 5, 9]), None, img.shape)
        self.assertEqual(s1["spike_anchors"], s2["spike_anchors"])
        for word in ("FOCAL LENGTH", "estimated", "Minimum star diameter"):
            self.assertIn(word, s1["report"])
        self.assertNotIn("Sky background", s1["report"])
        self.assertNotIn("tone", s1)


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
