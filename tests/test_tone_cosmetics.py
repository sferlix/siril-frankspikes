"""Left panel ("camera raw"-style) Base/Detail tone controls - see
TONE_PARAM_DEFS/apply_cosmetics. Covers the table-driven dict refactor (all-
defaults must stay an exact identity - test_app_smoke.py's
test_process_thread_ignores_hide_background also guards this end-to-end)
and the new Highlights/Shadows (tone-region masked) vs Whites/Blacks (flat
stretch) split."""
import unittest
import numpy as np
from _harness import fs


def _params(**over):
    p = dict(fs.TONE_DEFAULTS)
    p.update(over)
    return p


class TestAllDefaultsIsIdentity(unittest.TestCase):
    def test_flat_image_unchanged(self):
        rgb = np.full((10, 10, 3), 0.42, dtype=np.float32)
        out = fs.apply_cosmetics(rgb, _params())
        self.assertTrue(np.array_equal(out, rgb))

    def test_gradient_image_unchanged(self):
        rgb = np.tile(np.linspace(0, 1, 20, dtype=np.float32)[None, :, None], (20, 1, 3))
        out = fs.apply_cosmetics(rgb, _params())
        self.assertTrue(np.array_equal(out, rgb))

    def test_missing_keys_default_to_zero(self):
        rgb = np.full((5, 5, 3), 0.5, dtype=np.float32)
        out = fs.apply_cosmetics(rgb, {})
        self.assertTrue(np.array_equal(out, rgb))

    def test_param_defs_and_defaults_keys_match(self):
        self.assertEqual(set(fs.TONE_DEFAULTS.keys()),
                          {k for k, *_r in fs.TONE_PARAM_DEFS})


class TestHighlightsShadowsAreRegionMasked(unittest.TestCase):
    """Highlights/Shadows should move only their own tonal region, unlike
    Whites/Blacks (a flat stretch of the whole range) - see the docstring
    on apply_cosmetics."""

    def _gradient(self):
        # A row from near-black to near-white.
        return np.tile(np.linspace(0.05, 0.95, 100, dtype=np.float32)[None, :, None],
                        (1, 1, 3))

    def test_highlights_barely_touches_the_dark_end(self):
        rgb = self._gradient()
        out = fs.apply_cosmetics(rgb, _params(highlights=100.0))
        dark_shift = abs(float(out[0, 0, 0] - rgb[0, 0, 0]))
        bright_shift = abs(float(out[0, -1, 0] - rgb[0, -1, 0]))
        self.assertGreater(bright_shift, dark_shift * 5)

    def test_shadows_barely_touches_the_bright_end(self):
        rgb = self._gradient()
        out = fs.apply_cosmetics(rgb, _params(shadows=100.0))
        dark_shift = abs(float(out[0, 0, 0] - rgb[0, 0, 0]))
        bright_shift = abs(float(out[0, -1, 0] - rgb[0, -1, 0]))
        self.assertGreater(dark_shift, bright_shift * 5)

    def test_positive_highlights_brightens_the_bright_end(self):
        rgb = self._gradient()
        out = fs.apply_cosmetics(rgb, _params(highlights=100.0))
        self.assertGreater(float(out[0, -1, 0]), float(rgb[0, -1, 0]))

    def test_negative_highlights_darkens_the_bright_end(self):
        rgb = self._gradient()
        out = fs.apply_cosmetics(rgb, _params(highlights=-100.0))
        self.assertLess(float(out[0, -1, 0]), float(rgb[0, -1, 0]))


class TestWhitesBlacksAffectTheWholeRange(unittest.TestCase):
    def test_whites_shifts_the_bright_end_and_still_touches_mid(self):
        rgb = np.tile(np.linspace(0.05, 0.95, 100, dtype=np.float32)[None, :, None], (1, 1, 3))
        out = fs.apply_cosmetics(rgb, _params(whites=-50.0))
        # A flat stretch (unlike the region-masked Highlights) noticeably
        # moves the midpoint too, not just the bright end.
        mid_shift = abs(float(out[0, 50, 0] - rgb[0, 50, 0]))
        self.assertGreater(mid_shift, 0.02)

    def test_blacks_shifts_the_dark_end_and_still_touches_mid(self):
        rgb = np.tile(np.linspace(0.05, 0.95, 100, dtype=np.float32)[None, :, None], (1, 1, 3))
        out = fs.apply_cosmetics(rgb, _params(blacks=50.0))
        mid_shift = abs(float(out[0, 50, 0] - rgb[0, 50, 0]))
        self.assertGreater(mid_shift, 0.02)


class TestTextureAndDehaze(unittest.TestCase):
    def _noisy_patch(self, seed=0):
        rng = np.random.default_rng(seed)
        base = np.full((60, 60), 0.5, dtype=np.float32)
        base[20:40, 20:40] = 0.8
        base += rng.normal(0, 0.02, base.shape).astype(np.float32)
        return np.clip(np.stack([base, base, base], axis=-1), 0, 1)

    def test_texture_zero_is_noop(self):
        rgb = self._noisy_patch()
        out = fs.apply_cosmetics(rgb, _params(texture=0.0))
        self.assertTrue(np.array_equal(out, rgb))

    def test_texture_nonzero_changes_the_image(self):
        rgb = self._noisy_patch()
        out = fs.apply_cosmetics(rgb, _params(texture=80.0))
        self.assertFalse(np.array_equal(out, rgb))

    def test_dehaze_zero_is_noop(self):
        rgb = self._noisy_patch()
        out = fs.apply_cosmetics(rgb, _params(dehaze=0.0))
        self.assertTrue(np.array_equal(out, rgb))

    def test_dehaze_positive_increases_saturation_of_a_tinted_patch(self):
        rgb = self._noisy_patch()
        rgb[..., 2] *= 0.6  # give it some real chroma to boost
        out = fs.apply_cosmetics(rgb, _params(dehaze=60.0))
        def sat(a):
            return float(np.mean(np.max(a, axis=-1) - np.min(a, axis=-1)))
        self.assertGreater(sat(out), sat(rgb))


if __name__ == "__main__":
    unittest.main()
