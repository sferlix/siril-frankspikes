"""Sanity checks for render_spike_layer's own config shapes (Per size and
Simple/Uniform anchors). Used to compare byte-for-byte against frankSpikes
2.0.0 before the realism pass (twinkle floor, rainbow defaults, ring-flare
blending) intentionally changed the classic look - see the commit that
rewrote this file. Now just confirms each mode still renders something."""
import copy, unittest
from _harness import fs, star_field


def _cfg(anchors, **over):
    cfg = {"anchors": anchors, "rays": 4, "rotation": 30.0, "hue": 0.0,
           "sharpness": 100.0, "variation": 15.0, "twinkle": 0.0}
    cfg.update(over)
    return cfg


class TestClassicRenders(unittest.TestCase):
    def _check(self, anchors, view=(0, 0, 800, 600), out_shape=(600, 800)):
        stars = star_field()
        layer = fs.render_spike_layer(out_shape, *view, stars, _cfg(anchors))
        self.assertEqual(layer.shape, (out_shape[0], out_shape[1], 3))
        self.assertGreater(float(layer.max()), 0.0)
        self.assertLessEqual(float(layer.max()), 1.0)

    def test_per_size_defaults(self):
        self._check(copy.deepcopy(fs.SPIKE_DEFAULTS["anchors"]))

    def test_uniform_anchors(self):
        ud = fs.SPIKE_UNIFORM_DEFAULTS
        full = {k: ud[k] for k in fs._ANCHOR_PARAM_KEYS}
        zero = {k: 0.0 for k in fs._ANCHOR_PARAM_KEYS}
        d = ud["min_diam"]
        self._check([{"diam": d, **zero}, {"diam": d * fs.SPIKE_UNIFORM_REF_MULT, **full}])

    def test_scaled_view(self):
        self._check(copy.deepcopy(fs.SPIKE_DEFAULTS["anchors"]),
                    view=(100, 50, 400, 300), out_shape=(150, 200))


if __name__ == "__main__":
    unittest.main()
