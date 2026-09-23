import time
import unittest
from unittest import mock
import tkinter as tk
import numpy as np
from _harness import fs


class StubWorker:
    standalone = False

    def get_wd(self):
        return "."

    def log(self, msg):
        pass


def make_app():
    root = tk.Tk()
    root.withdraw()
    fs.App._on_reload = lambda self: None          # no Siril round trip
    app = fs.App(root, StubWorker())
    app._redraw_canvas = lambda: None              # window is withdrawn
    return root, app


class AppCase(unittest.TestCase):
    def setUp(self):
        try:
            self.root, self.app = make_app()
        except tk.TclError as e:
            self.skipTest(f"no display: {e}")

    def tearDown(self):
        for ident in self.root.tk.splitlist(self.root.tk.call("after", "info")):
            try:
                self.root.after_cancel(ident)
            except tk.TclError:
                pass
        self.root.destroy()


class TestPipeline(AppCase):
    def test_compose_applies_the_spike_layer(self):
        a = self.app
        base = np.full((20, 20, 3), 0.1, np.float32)
        l1 = np.full((20, 20, 3), 0.2, np.float32)
        a._base_preview_rgb, a._spike_layer_preview = base, l1
        a.spike_enabled.set(True)
        a._compose_preview()
        self.assertTrue(np.allclose(a._preview_rgb, fs.apply_spikes(base, l1)))
        a.spike_enabled.set(False)
        a._compose_preview()
        self.assertTrue(np.allclose(a._preview_rgb, base))

    def test_hide_background_composes_the_layer_onto_black(self):
        a = self.app
        base = np.full((20, 20, 3), 0.4, np.float32)
        l1 = np.full((20, 20, 3), 0.2, np.float32)
        a._base_preview_rgb, a._spike_layer_preview = base, l1
        a.spike_enabled.set(True)
        black = np.zeros_like(base)
        a.hide_background.set(True)
        a._compose_preview()
        self.assertTrue(np.allclose(a._preview_rgb, fs.apply_spikes(black, l1)))
        self.assertFalse(np.allclose(a._preview_rgb, fs.apply_spikes(base, l1)))
        a.hide_background.set(False)
        a._compose_preview()
        self.assertTrue(np.allclose(a._preview_rgb, fs.apply_spikes(base, l1)))

    def test_hide_background_toggle_is_cheap_no_rerender(self):
        """Toggling should recompose the already-cached layer, not trigger a
        fresh (expensive) spike render."""
        a = self.app
        a.loaded = True
        a.full_shape = (30, 30)
        a._base_preview_rgb = np.full((30, 30, 3), 0.5, np.float32)
        a._spike_layer_preview = np.full((30, 30, 3), 0.1, np.float32)
        a._spike_layer_key = "unchanged"
        a.hide_background.set(True)
        a._on_hide_background_toggle()
        self.assertEqual(a._spike_layer_key, "unchanged")
        self.assertTrue(np.allclose(a._preview_rgb, fs.apply_spikes(np.zeros((30, 30, 3), np.float32),
                                                                     a._spike_layer_preview)))

    def test_process_thread_ignores_hide_background(self):
        """The flag is preview-only: _process_thread must build rgb_final
        from the real pristine image regardless of hide_background."""
        a = self.app
        a.hide_background.set(True)
        a._pristine_full = np.full((10, 10, 3), 0.6, np.float32)
        a.full_shape = (10, 10)
        a._stars = []
        a.spike_enabled.set(False)
        a.worker.get_shape = lambda: (10, 10)
        a.worker.push_rgb = lambda rgb: setattr(a, "_pushed", rgb.copy())
        a._process_thread()
        self.assertTrue(np.allclose(a._pushed, 0.6))

    def test_preview_thread_renders_the_spike_layer(self):
        a = self.app
        a.loaded = True
        a.full_shape = (60, 80)
        a._base_preview_rgb = np.zeros((60, 80, 3), np.float32)
        a._stars = [(40.0, 30.0, 12.0, 1.0, (1.0, 1.0, 1.0))]
        a._start_spike_preview()
        for _ in range(400):
            self.root.update()
            if a._spike_layer_preview is not None:
                break
            time.sleep(0.05)
        self.assertEqual(a._spike_layer_preview.shape, (60, 80, 3))
        self.assertGreater(float(a._spike_layer_preview.max()), 0.0)
        self.assertIsNotNone(a._spike_layer_key)

    def test_disabling_spikes_drops_the_layer(self):
        a = self.app
        a.loaded = True
        a.full_shape = (60, 80)
        a._base_preview_rgb = np.zeros((60, 80, 3), np.float32)
        a._stars = [(40.0, 30.0, 12.0, 1.0, (1.0, 1.0, 1.0))]
        a._spike_layer_preview = np.ones((60, 80, 3), np.float32)
        a._spike_layer_key = "stale"
        a.spike_enabled.set(False)
        a._start_spike_preview()
        self.assertIsNone(a._spike_layer_preview)
        self.assertIsNone(a._spike_layer_key)


class TestFlareSymmetrySlider(AppCase):
    """The global "Flare ray symmetry" slider replaces the old Ray flare
    count: it must reach the render config and be restored by Defaults."""

    def test_reaches_the_config_and_resets(self):
        a = self.app
        a.spike_flare_symmetry.set(90.0)
        a._update_all_labels()
        self.assertEqual(a._spike_config()["flare_symmetry"], 90.0)
        self.assertEqual(a.spike_flare_symmetry_label.get(), "90")
        a._reset_spike_defaults()
        self.assertEqual(a.spike_flare_symmetry.get(), fs.SPIKE_DEFAULTS["flare_symmetry"])


class TestSimpleModeKeepsFlareGeometry(AppCase):
    """In Simple mode every strength ramps from 0 at the Minimum diameter,
    but the flare reach/ring diameter must not - a reach ramping from 0
    collapsed mid-size stars' flares into their own core."""

    def test_geometry_keys_do_not_ramp(self):
        a = self.app
        a.spike_uniform["flare_reach"].set(70.0)
        a.spike_uniform["ring_diam"].set(2.5)
        lo, hi = sorted(a._uniform_anchors(), key=lambda x: x["diam"])
        self.assertEqual(lo["flare_reach"], 70.0)
        self.assertEqual(lo["ring_diam"], 2.5)
        self.assertEqual(lo["soft_flare"], 0.0)

    def test_small_tab_gets_the_full_geometry_range(self):
        self.assertEqual(fs.spike_anchor_slider_range(0, "flare_reach"),
                         fs._SPIKE_ANCHOR_PARAM_FULL_RANGE["flare_reach"])


class TestToneResetButton(AppCase):
    """The left panel's own "Reset" button (separate from the Diffraction
    Spikes panel's "Reset manual edits"/"Defaults") must zero out Base/
    Detail alike."""

    def test_reset_zeroes_base_and_detail(self):
        a = self.app
        a.tone["exposure"].set(40.0)
        a.tone["saturation"].set(-25.0)
        a._reset_tone_defaults()
        self.assertEqual(a.tone["exposure"].get(), 0.0)
        self.assertEqual(a.tone["saturation"].get(), 0.0)

    def test_reset_does_not_touch_spike_settings(self):
        a = self.app
        a.spike_rotation.set(45.0)
        a.tone["exposure"].set(40.0)
        a._reset_tone_defaults()
        self.assertEqual(a.spike_rotation.get(), 45.0)


class TestLengthCalibration(AppCase):
    """_apply_length_calibration scales the default Spike Length (Simple/
    Uniform and every per-size anchor) by the focal-length-derived factor
    computed in _reload_thread - see _focal_length_to_spike_length."""

    def test_scales_uniform_and_all_three_anchors(self):
        a = self.app
        a._apply_length_calibration(2.0)
        self.assertAlmostEqual(a.spike_uniform["length"].get(),
                                fs.SPIKE_UNIFORM_DEFAULTS["length"] * 2.0, places=3)
        for av, defaults in zip(a.spike_anchors, fs.SPIKE_DEFAULTS["anchors"]):
            lo, hi = fs.spike_anchor_slider_range(
                a.spike_anchors.index(av), "length")
            expected = min(hi, max(lo, defaults["length"] * 2.0))
            self.assertAlmostEqual(av["length"].get(), expected, places=3)

    def test_only_touches_length_not_other_look_params(self):
        a = self.app
        before = a.spike_anchors[2]["intensity"].get()
        a._apply_length_calibration(1.5)
        self.assertEqual(a.spike_anchors[2]["intensity"].get(), before)

    def test_result_is_clamped_to_the_slider_range(self):
        a = self.app
        a._apply_length_calibration(100.0)  # absurdly large - must clamp, not error
        lo, hi = fs._SPIKE_ANCHOR_PARAM_FULL_RANGE["length"]
        self.assertLessEqual(a.spike_uniform["length"].get(), hi)


class TestThicknessAndIntensityCalibration(AppCase):
    """Same _apply_anchor_param_scale machinery as Length (see
    TestLengthCalibration), applied to Thickness and Intensity - the two
    other focal-length-derived defaults from _reload_thread."""

    def test_thickness_scales_uniform_and_anchors(self):
        a = self.app
        a._apply_thickness_calibration(0.85)
        self.assertAlmostEqual(a.spike_uniform["thickness"].get(),
                                fs.SPIKE_UNIFORM_DEFAULTS["thickness"] * 0.85, places=3)
        for i, (av, defaults) in enumerate(zip(a.spike_anchors, fs.SPIKE_DEFAULTS["anchors"])):
            lo, hi = fs.spike_anchor_slider_range(i, "thickness")
            expected = min(hi, max(lo, defaults["thickness"] * 0.85))
            self.assertAlmostEqual(av["thickness"].get(), expected, places=3)

    def test_intensity_scales_uniform_and_anchors(self):
        a = self.app
        a._apply_intensity_calibration(1.15)
        self.assertAlmostEqual(a.spike_uniform["intensity"].get(),
                                fs.SPIKE_UNIFORM_DEFAULTS["intensity"] * 1.15, places=3)
        for i, (av, defaults) in enumerate(zip(a.spike_anchors, fs.SPIKE_DEFAULTS["anchors"])):
            lo, hi = fs.spike_anchor_slider_range(i, "intensity")
            expected = min(hi, max(lo, defaults["intensity"] * 1.15))
            self.assertAlmostEqual(av["intensity"].get(), expected, places=3)

    def test_thickness_calibration_does_not_touch_intensity_or_length(self):
        a = self.app
        before_intensity = a.spike_anchors[1]["intensity"].get()
        before_length = a.spike_anchors[1]["length"].get()
        a._apply_thickness_calibration(0.7)
        self.assertEqual(a.spike_anchors[1]["intensity"].get(), before_intensity)
        self.assertEqual(a.spike_anchors[1]["length"].get(), before_length)


class TestTonePreviewZoomGating(AppCase):
    """A tone slider drag while zoomed in (zoom_mode == "manual") must only
    refresh the visible hi-res crop, not the whole (Fit) raster - see the
    note on _on_tone_slider. Returning to Fit (_zoom_fit) then refreshes
    the whole raster in one shot."""

    def test_manual_zoom_skips_full_preview_render(self):
        a = self.app
        a.loaded = True
        a.zoom_mode = "manual"
        calls = {"render": 0, "hires": 0}
        a._render_preview = lambda: calls.__setitem__("render", calls["render"] + 1)
        a._schedule_hires_fetch = lambda: calls.__setitem__("hires", calls["hires"] + 1)
        a._on_tone_slider()
        self.assertEqual(calls["render"], 0)
        self.assertEqual(calls["hires"], 1)

    def test_fit_zoom_renders_the_full_preview(self):
        a = self.app
        a.loaded = True
        a.zoom_mode = "fit"
        calls = {"render": 0, "hires": 0}
        a._render_preview = lambda: calls.__setitem__("render", calls["render"] + 1)
        a._schedule_hires_fetch = lambda: calls.__setitem__("hires", calls["hires"] + 1)
        a._on_tone_slider()
        self.assertEqual(calls["render"], 1)
        self.assertEqual(calls["hires"], 0)

    def test_zoom_fit_refreshes_the_full_preview_when_loaded(self):
        a = self.app
        a.loaded = True
        a.zoom_mode = "manual"
        calls = {"render": 0}
        a._render_preview = lambda: calls.__setitem__("render", calls["render"] + 1)
        a._zoom_fit()
        self.assertEqual(a.zoom_mode, "fit")
        self.assertEqual(calls["render"], 1)

    def test_zoom_fit_does_not_crash_before_load(self):
        a = self.app
        a.loaded = False
        a._zoom_fit()  # must not raise even with no image loaded yet
        self.assertEqual(a.zoom_mode, "fit")


class TestMagicWand(AppCase):
    """Two Magic Wands, one job each: the Camera RAW one only sets the tone
    sliders, the spike one only the spike sliders (and runs by itself
    when an image loads) - see App._on_magic_wand/_apply_spike_wand."""

    def _prime_loaded_state(self, focal_length=500.0):
        a = self.app
        a.loaded = True
        rng = np.random.default_rng(0)
        img = np.clip(0.05 + rng.normal(0, 0.01, (60, 60, 3)), 0, 1).astype(np.float32)
        img[::5, ::5] = 0.9  # sprinkle in enough "stars" to be a believable field
        a._pristine_full = img
        a._src_preview_rgb = img
        a._stars = [(float(x), float(y), 6.0 + (x % 5), 1.0, (1.0, 1.0, 1.0))
                    for x in range(0, 60, 5) for y in range(0, 60, 5)]
        a.worker.get_focal_length = lambda: focal_length
        a._render_preview = lambda: None
        a._schedule_spike_preview = lambda: None
        return a

    def _spike_state(self):
        a = self.app
        return (a.spike_mode.get(), a.spike_sharpness.get(), a.spike_twinkle.get(),
                [{k: av[k].get() for k in fs._ANCHOR_PARAM_KEYS + ("diam",)} for av in a.spike_anchors],
                {k: a.spike_uniform[k].get() for k in fs._ANCHOR_PARAM_KEYS})

    def _tone_state(self):
        return {k: v.get() for k, v in self.app.tone.items() if not k.endswith("_label")}

    def _press(self, method):
        with mock.patch.object(fs.messagebox, "showinfo") as info:
            method()
        return info

    def test_does_nothing_before_an_image_is_loaded(self):
        a = self.app
        a.loaded = False
        before = (self._tone_state(), self._spike_state())
        i1 = self._press(a._on_magic_wand)
        i2 = self._press(a._on_spike_magic_wand)
        self.assertEqual((self._tone_state(), self._spike_state()), before)
        i1.assert_not_called()
        i2.assert_not_called()

    def test_tone_wand_sets_only_the_camera_raw_sliders(self):
        a = self._prime_loaded_state()
        a.tone["exposure"].set(7.0)
        spikes_before = self._spike_state()
        info = self._press(a._on_magic_wand)
        tw = fs.compute_tone_wand(a._pristine_full)
        for key, value in tw["tone"].items():
            self.assertAlmostEqual(a.tone[key].get(), value, places=3)
        self.assertEqual(a.tone["exposure"].get(), 7.0)
        self.assertEqual(self._spike_state(), spikes_before)
        info.assert_called_once()
        self.assertNotIn("FOCAL LENGTH", info.call_args[0][1])

    def test_spike_wand_in_simple_mode_writes_simple_and_stays_simple(self):
        a = self._prime_loaded_state()
        a.spike_mode.set("uniform")
        a._on_spike_mode_change()
        tone_before = self._tone_state()
        tabs_before = [{k: av[k].get() for k in fs._ANCHOR_PARAM_KEYS} for av in a.spike_anchors]
        info = self._press(a._on_spike_magic_wand)
        sw = fs.compute_spike_wand(a._stars, 500.0, a._pristine_full.shape,
                                   current_rotation=a.spike_rotation.get(), mode="uniform")
        self.assertEqual(a.spike_mode.get(), "uniform")
        self.assertEqual(a.spike_uniform_min_diam.get(), sw["spike_simple"]["min_diam"])
        for key, value in sw["spike_simple"].items():
            if key != "min_diam":
                self.assertAlmostEqual(a.spike_uniform[key].get(), value, places=3)
        self.assertEqual([{k: av[k].get() for k in fs._ANCHOR_PARAM_KEYS} for av in a.spike_anchors],
                         tabs_before)
        self.assertEqual(self._tone_state(), tone_before)
        self.assertIn("SPIKES (Simple mode)", info.call_args[0][1])

    def test_spike_wand_in_per_size_mode_writes_the_tabs(self):
        a = self._prime_loaded_state()
        a.spike_mode.set("per_size")
        a._on_spike_mode_change()
        rays_before = a.spike_rays.get()
        info = self._press(a._on_spike_magic_wand)
        sw = fs.compute_spike_wand(a._stars, 500.0, a._pristine_full.shape,
                                   current_rotation=a.spike_rotation.get(), mode="per_size")
        self.assertEqual(a.spike_mode.get(), "per_size")
        for av, values in zip(a.spike_anchors, sw["spike_anchors"]):
            for key, value in values.items():
                self.assertAlmostEqual(av[key].get(), value, places=3)
        self.assertEqual(a.spike_sharpness.get(), sw["spike_globals"]["sharpness"])
        self.assertEqual(a.spike_rays.get(), rays_before)
        self.assertIn("SPIKES (Per size mode)", info.call_args[0][1])

    def test_pressing_twice_gives_the_same_sliders(self):
        a = self._prime_loaded_state(focal_length=None)
        self._press(a._on_magic_wand)
        self._press(a._on_spike_magic_wand)
        first = (self._tone_state(), self._spike_state())
        self._press(a._on_magic_wand)
        self._press(a._on_spike_magic_wand)
        self.assertEqual((self._tone_state(), self._spike_state()), first)

    def test_loading_an_image_runs_the_spike_wand_in_simple_mode_not_the_tone_wand(self):
        a = self.app
        a.worker.get_focal_length = lambda: 400.0
        a._render_preview = lambda: None
        a._schedule_spike_preview = lambda: None
        a._schedule_hires_fetch = lambda: None
        a.spike_mode.set("uniform")
        a._on_spike_mode_change()
        tone_before = self._tone_state()
        img = np.clip(0.05 + np.random.default_rng(1).normal(0, 0.01, (60, 60, 3)), 0, 1).astype(np.float32)
        stars = [(float(x), float(y), 3.0 + (x % 7), 1.0, (1.0, 1.0, 1.0))
                 for x in range(0, 60, 4) for y in range(0, 60, 4)]
        a.queue.put(("loaded", ("img.fits", img, img, (60, 60), stars, None, None, None, None)))
        with mock.patch.object(fs.messagebox, "showinfo") as info:
            a._poll_queue()
        info.assert_not_called()          # no pop-up on open, only on the button
        sw = fs.compute_spike_wand(stars, 400.0, img.shape, current_rotation=a.spike_rotation.get())
        self.assertEqual(a.spike_mode.get(), "uniform")      # stays in Simple
        self.assertEqual(a.spike_uniform_min_diam.get(), sw["spike_simple"]["min_diam"])
        self.assertEqual(self._tone_state(), tone_before)
        # and the freshly opened image doesn't count as having unsaved edits
        self.assertEqual(a._saved_sig, a._edit_signature())


if __name__ == "__main__":
    unittest.main()
