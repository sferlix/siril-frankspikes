import unittest
import numpy as np
from _harness import fs

P = {"depth": 90.0, "extent": 30.0, "spikes": 100.0, "vane": 1.0, "rings": 100.0,
     "obstruction": 30.0, "dispersion": 0.0, "color": 0.0, "streaks": 0.0, "streak_len": 8.0}


def dex(a, b):
    return abs(np.log10(max(a, 1e-30) / max(b, 1e-30)))


class TestTemplate(unittest.TestCase):
    def test_shapes_centre_and_cache(self):
        t1 = fs._phys_template("spider4", 6, 0.0, 0.3, 0.01, 0.0)
        self.assertEqual(t1["ring"][0].shape, (1024, 1024, 3))
        self.assertEqual(t1["spk"][1].shape, (512, 512, 3))
        self.assertEqual(len(t1["ring"]), 4)
        self.assertAlmostEqual(float(t1["ring"][0][512, 512, 1]), 1.0, places=3)
        self.assertIs(t1, fs._phys_template("spider4", 6, 0.0, 0.3, 0.01, 0.0))

    def test_lru_is_bounded(self):
        for rot in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0):
            fs._phys_template("spider4", 6, rot, 0.3, 0.01, 0.0)
        self.assertLessEqual(len(fs._phys_tpl_cache), 4)

    def test_dispersion_scales_channels(self):
        t = fs._phys_template("spider4", 6, 0.0, 0.0, 0.01, 100.0)
        ring = t["ring"][0]
        # first dark ring: ~1.22 lambda/D scaled by the channel's wavelength
        r_red = 10 + int(np.argmin(ring[512, 512 + 10:512 + 26, 0]))
        r_blue = 10 + int(np.argmin(ring[512, 512 + 10:512 + 26, 2]))
        self.assertGreater(r_red / r_blue, 1.15)


class TestCalibration(unittest.TestCase):
    """Analytic spike model vs the FFT template (spec 8, item 6)."""

    def test_vane_spike_level(self):
        t = fs._phys_template("spider4", 6, 0.0, 0.3, 0.01, 0.0)
        spk = t["spk"][0][:, :, 1]
        ln = fs._phys_spike_lines("spider4", 6, 0.0)[0]          # +x
        for lo, hi in ((8, 12), (12, 18), (18, 26)):
            fft_val = float(spk[510:515, 512 + 16 * lo:512 + 16 * hi].mean())
            a = np.linspace(lo, hi, 60)
            model = float(fs._phys_spike_along(a, ln, 0.3, 0.01).mean())
            self.assertLess(dex(fft_val, model), 0.35, msg=f"a={lo}-{hi} fft={fft_val:.2e} model={model:.2e}")

    def test_spider3_gain(self):
        t = fs._phys_template("spider3", 6, 0.0, 0.3, 0.01, 0.0)
        spk = t["spk"][0][:, :, 1]
        ln = fs._phys_spike_lines("spider3", 6, 0.0)[0]          # +x
        lo, hi = 12, 22
        fft_val = float(spk[510:515, 512 + 16 * lo:512 + 16 * hi].mean())
        model = float(fs._phys_spike_along(np.linspace(lo, hi, 60), ln, 0.3, 0.01).mean())
        self.assertLess(dex(fft_val, model), 0.35, msg=f"fft={fft_val:.2e} model={model:.2e}")

    def test_polygon_edge_level(self):
        for n in (5, 6, 7, 8):
            t = fs._phys_template("polygon", n, 0.0, 0.0, 0.01, 0.0)
            spk = t["spk"][0][:, :, 1]
            ln = fs._phys_spike_lines("polygon", n, 0.0)[0]      # angle 90 -> +y
            lo, hi = 8, 24
            fft_val = float(spk[512 + 16 * lo:512 + 16 * hi, 510:515].mean())
            model = float(fs._phys_spike_along(np.linspace(lo, hi, 80), ln, 0.0, 0.01).mean())
            self.assertLess(dex(fft_val, model), 0.35, msg=f"n={n} fft={fft_val:.2e} model={model:.2e}")


class TestStamp(unittest.TestCase):
    def test_draw_is_symmetric_and_visible(self):
        t = fs._phys_template("spider4", 6, 0.0, 0.3, 0.01, 0.0)
        size = 801
        cv = np.zeros((size, size, 3), np.float32)
        fwhm = 16.0
        fs._phys_draw_fft(cv, 0, 0, 400.0, 400.0, fwhm, fwhm / fs.PHYS_FWHM_PER_LAMD, P, t,
                          (1.0, 1.0, 1.0), 1.0)
        self.assertGreater(float(cv.max()), 0.05)
        for d in (30, 60, 120):
            self.assertAlmostEqual(float(cv[400, 400 + d, 1]), float(cv[400, 400 - d, 1]), delta=2e-3)
        self.assertLess(float(cv[400, 400, 1]), 0.05)      # core excluded

    def test_small_scale_uses_mip(self):
        t = fs._phys_template("spider4", 6, 0.0, 0.3, 0.01, 0.0)
        cv = np.zeros((301, 301, 3), np.float32)
        fs._phys_draw_fft(cv, 0, 0, 150.0, 150.0, 4.0, 4.0 / fs.PHYS_FWHM_PER_LAMD, P, t, (1.0, 1.0, 1.0), 1.0)
        self.assertGreater(float(cv.max()), 0.02)


if __name__ == "__main__":
    unittest.main()
