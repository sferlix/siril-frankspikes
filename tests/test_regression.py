import copy, unittest
import numpy as np
from _harness import fs, base, star_field

OVERRIDE_OLD = {"length": 5.0, "intensity": 150.0, "thickness": 1.2, "soft_flare": 30.0,
                "ring_flare": 15.0, "chroma": 30.0, "rainbow": 10.0, "saturation": 40.0}


def _new_anchor(a):
    return dict(a, flare_tail=0.0)


class TestClassicUnchanged(unittest.TestCase):
    def _check(self, anchors_old, view=(0, 0, 800, 600), out_shape=(600, 800)):
        old = {"anchors": anchors_old, "rays": 4, "rotation": 30.0, "hue": 0.0,
               "sharpness": 100.0, "variation": 15.0}
        new = copy.deepcopy(old)
        new["anchors"] = [_new_anchor(a) for a in anchors_old]
        stars_old = star_field()
        stars_old[3] = stars_old[3][:6] + (OVERRIDE_OLD,)
        stars_new = [s[:6] + ((dict(s[6], flare_tail=0.0) if s[6] else None),) for s in stars_old]
        a = base.render_spike_layer(out_shape, *view, stars_old, old)
        b = fs.render_spike_layer(out_shape, *view, stars_new, new)
        self.assertTrue(np.array_equal(a, b))
        self.assertGreater(float(a.max()), 0.0)

    def test_per_size_defaults(self):
        self._check(copy.deepcopy(base.SPIKE_DEFAULTS["anchors"]))

    def test_uniform_anchors(self):
        full = {k: base.SPIKE_UNIFORM_DEFAULTS[k] for k in base._ANCHOR_PARAM_KEYS}
        zero = {k: 0.0 for k in base._ANCHOR_PARAM_KEYS}
        d = base.SPIKE_UNIFORM_DEFAULTS["min_diam"]
        self._check([{"diam": d, **zero}, {"diam": d * 4.0, **full}])

    def test_scaled_view(self):
        self._check(copy.deepcopy(base.SPIKE_DEFAULTS["anchors"]),
                    view=(100, 50, 400, 300), out_shape=(150, 200))


if __name__ == "__main__":
    unittest.main()
