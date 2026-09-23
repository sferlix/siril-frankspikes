"""Realism pass prompted by a side-by-side comparison against a real
reference photo: the classic spikes read as flat-width "segments" instead
of a tapering needle, stayed pure white regardless of the star's own
colour, the ray flare's spokes were all identical, and the soft flare
didn't reach far enough to cover the ray flare's own tips. See the taper/
colour-default/jitter/soft-flare-radius changes in _add_spike_ray, the
SPIKE_DEFAULTS anchors and the `if p["soft_flare"] > 0`
block of render_spike_layer."""
import math
import unittest
import numpy as np
from _harness import fs


class TestSpikeTaper(unittest.TestCase):
    def _width_at(self, layer, cx, cy, x, threshold_frac=0.5):
        """Cross-section width (in px) of a horizontal ray at column x,
        measured where the red channel exceeds threshold_frac of its own
        peak value in that column - a stand-in for "how wide does this
        pixel column look."""
        col = layer[:, x, 0]
        peak = col.max()
        if peak <= 0:
            return 0.0
        return float(np.sum(col >= threshold_frac * peak))

    def test_width_stays_constant_not_a_tapering_needle(self):
        """Reference photos (see the analysis of Downloads/esempi) show a
        spike keeping its width all the way out - even broadening a little
        (+20-40%) - and fading in brightness instead; the old 8%-at-the-tip
        taper read as a synthetic needle."""
        h = w = 200
        cy, cx = h // 2, 20
        layer = np.zeros((h, w, 3), dtype=np.float32)
        length_px = 150.0
        fs._add_spike_ray(layer, cx, cy, 0.0, length_px, thickness_px=3.0,
                            peak=0.9, star_color=(1.0, 1.0, 1.0),
                            rainbow=0.0, saturation=0.0)
        near = self._width_at(layer, cx, cy, int(cx + 0.2 * length_px))
        far = self._width_at(layer, cx, cy, int(cx + 0.85 * length_px))
        self.assertGreaterEqual(far, near)
        self.assertLessEqual(far, near * 1.6)

    def test_brightness_also_fades_toward_the_tip(self):
        h = w = 200
        cy, cx = h // 2, 20
        layer = np.zeros((h, w, 3), dtype=np.float32)
        length_px = 150.0
        fs._add_spike_ray(layer, cx, cy, 0.0, length_px, thickness_px=3.0,
                            peak=0.9, star_color=(1.0, 1.0, 1.0),
                            rainbow=0.0, saturation=0.0)
        row = layer[cy, cx:cx + int(length_px), 0]
        near = row[int(0.2 * length_px)]
        far = row[int(0.85 * length_px)]
        self.assertGreater(near, far * 1.5)


class TestFlareMatchesSpikeSaturation(unittest.TestCase):
    """flare_saturation (soft/ring/ray flare's own colour) used to default
    to 0 (pure white) on every anchor while the spike rays' own saturation
    was raised well above 0 - a colour-tinted ray meeting a pure-white halo
    right where they overlap near the star read as a muddy/off colour (a
    yellow star's white-to-yellow seam looked sepia), not a clean, evenly-
    tinted star. Both should default to a comparably high, nonzero value."""

    def test_every_default_anchor_has_matching_nonzero_flare_saturation(self):
        for anchor in fs.SPIKE_DEFAULTS["anchors"]:
            if anchor["saturation"] > 0:
                self.assertGreater(anchor["flare_saturation"], 0,
                                    f"anchor diam={anchor['diam']}: spike rays are "
                                    f"tinted (saturation={anchor['saturation']}) but "
                                    f"the flare/halo stays pure white")

    def test_uniform_defaults_also_match(self):
        ud = fs.SPIKE_UNIFORM_DEFAULTS
        if ud["saturation"] > 0:
            self.assertGreater(ud["flare_saturation"], 0)


class TestSpikeFollowsStarColor(unittest.TestCase):
    def test_default_large_anchor_saturation_tints_toward_star_color(self):
        """SPIKE_DEFAULTS' Large anchor used to default to saturation=0
        (pure white) with a strong warm-tip chroma fighting a blue star's
        own colour - now it should read as blue-white throughout, closer
        to the star's own colour than to flat white."""
        large = fs.SPIKE_DEFAULTS["anchors"][2]
        layer = np.zeros((60, 60, 3), dtype=np.float32)
        blue_white = (0.6, 0.75, 1.0)
        fs._add_spike_ray(layer, 5, 30, 0.0, length_px=40, thickness_px=3.0,
                            peak=0.9, star_color=blue_white,
                            rainbow=0.0, saturation=large["saturation"])
        x = 15  # near the base
        r, g, b = layer[30, x, 0], layer[30, x, 1], layer[30, x, 2]
        self.assertGreater(b, r, "should read blue-tinted like the star, not white/pink")

    def test_zero_saturation_still_gives_pure_white(self):
        layer = np.zeros((60, 60, 3), dtype=np.float32)
        fs._add_spike_ray(layer, 5, 30, 0.0, length_px=40, thickness_px=3.0,
                            peak=0.9, star_color=(0.6, 0.75, 1.0),
                            rainbow=0.0, saturation=0.0)
        x = 15
        r, g, b = layer[30, x, 0], layer[30, x, 1], layer[30, x, 2]
        self.assertAlmostEqual(r, g, places=5)
        self.assertAlmostEqual(g, b, places=5)

    def test_saturation_stays_visible_along_the_whole_length_not_just_the_base(self):
        """With no diffraction rainbow, the R:G:B ratio should stay close
        to the star's own colour ratio all along the ray, not drift toward
        equal (white/grey) partway out (the old "chroma" warm-tip gradient
        used to do exactly that)."""
        layer = np.zeros((250, 250, 3), dtype=np.float32)
        star_color = (0.6, 0.75, 1.0)
        fs._add_spike_ray(layer, 5, 125, 0.0, length_px=200, thickness_px=3.0,
                            peak=0.9, star_color=star_color,
                            rainbow=0.0, saturation=95.0)
        near = layer[125, 20]
        far = layer[125, 160]  # well past the midpoint, still inside length_px
        near_ratio = near[0] / near[2]   # R/B
        far_ratio = far[0] / far[2]
        star_ratio = star_color[0] / star_color[2]
        # 95% (not 100%) saturation blends slightly toward white, so the
        # ratio sits a little above the star's own raw ratio - the point
        # here is that it stays THAT close, and identical, at both ends of
        # the ray, rather than drifting toward 1.0 (grey/white) by mid-ray.
        self.assertAlmostEqual(near_ratio, far_ratio, places=3)
        self.assertLess(abs(near_ratio - star_ratio), 0.03)


class TestVariationDoesNotJitterRotation(unittest.TestCase):
    """A real diffraction spike's angle is set by the telescope's own
    spider-vane geometry - identical for every star in one photo, unlike
    Length (which legitimately varies a little with seeing/PSF noise).
    "Natural variation" jittering rotation per star would put each star's
    spikes at a random angle, which no real telescope does."""

    def _cfg(self, variation, rotation=0.0, num_rays=4):
        anchor = {"diam": 8.0, "length": 4.0, "intensity": 150.0, "thickness": 1.0,
                  "soft_flare": 0.0, "flare_reach": 45.0, "ring_flare": 0.0, "ring_diam": 1.6,
                  "flare_saturation": 0.0, "flare_rays": 0.0,
                  "chroma": 0.0, "rainbow": 0.0, "saturation": 0.0}
        return {"anchors": [dict(anchor, diam=3.0), anchor, dict(anchor, diam=18.0)],
                "rays": num_rays, "rotation": rotation, "hue": 0.0, "sharpness": 100.0,
                "variation": variation, "twinkle": 0.0}

    def test_ray_lands_at_the_exact_configured_angle_regardless_of_position(self):
        w = h = 200
        cx = cy = 100
        radius = 40
        for (sx, sy) in [(30.0, 30.0), (170.0, 45.0), (60.0, 160.0), (150.0, 150.0)]:
            star = [(sx, sy, 10.0, 1.0, (1.0, 1.0, 1.0), True, None)]
            layer = fs.render_spike_layer((h, w), sx - w / 2, sy - h / 2, w, h,
                                            star, self._cfg(variation=100.0))
            # rotation=0, 4 rays -> exact angles 0/90/180/270 deg from the
            # star's own centre (which render_spike_layer places at (w/2,
            # h/2) in view-local coords here, since the view is centred on
            # the star).
            val = layer[h // 2, w // 2 + radius, 0]
            self.assertGreater(val, 0.0,
                                f"no ray at the exact 0-degree angle for star at "
                                f"({sx},{sy}) - rotation must have been jittered")

    def test_length_still_varies_between_stars(self):
        """Sanity check that turning rotation-jitter off didn't accidentally
        remove length jitter too."""
        w = h = 400
        lengths = []
        for (sx, sy) in [(50.0, 50.0), (350.0, 90.0), (120.0, 300.0)]:
            star = [(sx, sy, 10.0, 1.0, (1.0, 1.0, 1.0), True, None)]
            layer = fs.render_spike_layer((h, w), 0, 0, w, h, star,
                                            self._cfg(variation=100.0))
            row = layer[int(sy), int(sx):, 0]
            nz = np.where(row > 0)[0]
            lengths.append(int(nz.max()) if len(nz) else 0)
        self.assertGreater(len(set(lengths)), 1,
                            "all three stars rendered the exact same ray length")


if __name__ == "__main__":
    unittest.main()
