import time
import unittest
import tkinter as tk
import numpy as np
from _harness import fs


class StubWorker:
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


class TestPhysState(AppCase):
    def test_config_simple_mode(self):
        cfg = self.app._phys_config()
        self.assertEqual(len(cfg["anchors"]), 2)
        lo, hi = sorted(cfg["anchors"], key=lambda a: a["diam"])
        self.assertEqual(lo["depth"], 0.0)
        self.assertEqual(lo["streaks"], 0.0)
        self.assertAlmostEqual(hi["diam"], lo["diam"] * fs.SPIKE_UNIFORM_REF_MULT)
        self.assertEqual(hi["depth"], fs.PHYS_UNIFORM_DEFAULTS["depth"])
        self.assertEqual(lo["vane"], hi["vane"])
        self.assertEqual(cfg["aperture"], "spider4")

    def test_config_per_size_uses_classic_diameters(self):
        self.app.spike_mode.set("per_size")
        cfg = self.app._phys_config()
        self.assertEqual(len(cfg["anchors"]), 3)
        self.assertEqual([a["diam"] for a in cfg["anchors"]],
                         [av["diam"].get() for av in self.app.spike_anchors])

    def test_star_lists_have_independent_overrides(self):
        a = self.app
        a._stars = [(10.0, 10.0, 6.0, 0.5, (1, 1, 1)), (50.0, 50.0, 9.0, 0.7, (1, 1, 1)),
                    (90.0, 90.0, 7.0, 0.6, (1, 1, 1))]
        a._spike_disabled = {2}
        a._spike_manual = [(1, 30.0, 30.0, 8.0, 0.5, (1, 1, 1))]
        a._spike_star_overrides = {("auto", 0): {"length": 1.0}}
        a._phys_star_overrides = {("auto", 1): {"depth": 5.0}}
        classic, phys = a._effective_stars(), a._effective_phys_stars()
        self.assertEqual(len(classic), 3)
        self.assertEqual(len(phys), 3)
        self.assertIsNotNone(classic[0][6])
        self.assertIsNone(phys[0][6])
        self.assertIsNone(classic[1][6])
        self.assertIsNotNone(phys[1][6])
        self.assertTrue(classic[2][5] and phys[2][5])        # manual star is forced in both

    def test_defaults_reset_covers_physical_set(self):
        a = self.app
        a.phys_uniform["depth"].set(10.0)
        a.phys_rotation.set(33.0)
        a._reset_spike_defaults()
        self.assertEqual(a.phys_uniform["depth"].get(), fs.PHYS_UNIFORM_DEFAULTS["depth"])
        self.assertEqual(a.phys_rotation.get(), fs.PHYS_DEFAULTS["rotation"])

    def test_reset_edits_clears_physical_overrides(self):
        self.app._phys_star_overrides[("auto", 0)] = {"depth": 1.0}
        self.app._reset_spike_edits()
        self.assertEqual(self.app._phys_star_overrides, {})

    def test_select_star_fills_physical_sliders(self):
        a = self.app
        a._stars = [(10.0, 10.0, 12.0, 0.5, (1, 1, 1))]
        a._phys_star_overrides[("auto", 0)] = dict(fs.PHYS_UNIFORM_DEFAULTS, depth=33.0)
        a._select_star(("auto", 0))
        self.assertEqual(a.phys_star["depth"].get(), 33.0)


class TestPipeline(AppCase):
    def test_compose_applies_both_layers_in_order(self):
        a = self.app
        base = np.full((20, 20, 3), 0.1, np.float32)
        l1 = np.full((20, 20, 3), 0.2, np.float32)
        l2 = np.full((20, 20, 3), 0.3, np.float32)
        a._base_preview_rgb, a._spike_layer_preview, a._phys_layer_preview = base, l1, l2
        a.spike_enabled.set(True)
        a.phys_enabled.set(True)
        a._compose_preview()
        self.assertTrue(np.allclose(a._preview_rgb, fs.apply_spikes(fs.apply_spikes(base, l1), l2)))
        a.phys_enabled.set(False)
        a._compose_preview()
        self.assertTrue(np.allclose(a._preview_rgb, fs.apply_spikes(base, l1)))

    def test_hide_background_composes_layers_onto_black(self):
        a = self.app
        base = np.full((20, 20, 3), 0.4, np.float32)
        l1 = np.full((20, 20, 3), 0.2, np.float32)
        l2 = np.full((20, 20, 3), 0.3, np.float32)
        a._base_preview_rgb, a._spike_layer_preview, a._phys_layer_preview = base, l1, l2
        a.spike_enabled.set(True)
        a.phys_enabled.set(True)
        black = np.zeros_like(base)
        a.hide_background.set(True)
        a._compose_preview()
        self.assertTrue(np.allclose(a._preview_rgb, fs.apply_spikes(fs.apply_spikes(black, l1), l2)))
        self.assertFalse(np.allclose(a._preview_rgb, fs.apply_spikes(fs.apply_spikes(base, l1), l2)))
        a.hide_background.set(False)
        a._compose_preview()
        self.assertTrue(np.allclose(a._preview_rgb, fs.apply_spikes(fs.apply_spikes(base, l1), l2)))

    def test_hide_background_toggle_is_cheap_no_rerender(self):
        """Toggling should recompose the already-cached layers, not trigger
        a fresh (expensive) spike render."""
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
        a.phys_enabled.set(False)
        a.worker.get_shape = lambda: (10, 10)
        a.worker.push_rgb = lambda rgb: setattr(a, "_pushed", rgb.copy())
        a._process_thread()
        self.assertTrue(np.allclose(a._pushed, 0.6))

    def test_preview_thread_renders_both_layers(self):
        a = self.app
        a.loaded = True
        a.full_shape = (60, 80)
        a._base_preview_rgb = np.zeros((60, 80, 3), np.float32)
        a._stars = [(40.0, 30.0, 12.0, 1.0, (1.0, 1.0, 1.0))]
        a.phys_enabled.set(True)
        a._start_spike_preview()
        for _ in range(400):
            self.root.update()
            if a._phys_layer_preview is not None and a._spike_layer_preview is not None:
                break
            time.sleep(0.05)
        self.assertEqual(a._phys_layer_preview.shape, (60, 80, 3))
        self.assertGreater(float(a._phys_layer_preview.max()), 0.0)
        self.assertGreater(float(a._spike_layer_preview.max()), 0.0)
        self.assertIsNotNone(a._phys_layer_key)

    def test_disabling_physical_drops_its_layer(self):
        a = self.app
        a.loaded = True
        a.full_shape = (60, 80)
        a._base_preview_rgb = np.zeros((60, 80, 3), np.float32)
        a._stars = [(40.0, 30.0, 12.0, 1.0, (1.0, 1.0, 1.0))]
        a._phys_layer_preview = np.ones((60, 80, 3), np.float32)
        a._phys_layer_key = "stale"
        a.phys_enabled.set(False)
        a.spike_enabled.set(False)
        a._start_spike_preview()
        self.assertIsNone(a._phys_layer_preview)
        self.assertIsNone(a._phys_layer_key)


def shown(widget):
    return widget.winfo_manager() != ""


class TestPhysUI(AppCase):
    def test_simple_mode_shows_uniform_frame(self):
        a = self.app
        a.spike_mode.set("uniform")
        a._update_spike_mode_ui()
        self.assertTrue(shown(a._phys_uniform_frame))
        self.assertFalse(shown(a._phys_notebook))
        self.assertFalse(shown(a._phys_star_frame))

    def test_per_size_mode_shows_notebook_with_three_tabs(self):
        a = self.app
        a.spike_mode.set("per_size")
        a._update_spike_mode_ui()
        self.assertTrue(shown(a._phys_notebook))
        self.assertEqual(len(a._phys_notebook.tabs()), 3)
        self.assertFalse(shown(a._phys_uniform_frame))

    def test_selecting_a_star_shows_both_star_panels(self):
        a = self.app
        a._stars = [(10.0, 10.0, 12.0, 0.5, (1, 1, 1))]
        a._select_star(("auto", 0))
        self.assertTrue(shown(a._phys_star_frame))
        self.assertTrue(shown(a._spike_star_frame))
        self.assertFalse(shown(a._phys_uniform_frame))
        a._deselect_star()
        self.assertFalse(shown(a._phys_star_frame))
        self.assertTrue(shown(a._phys_uniform_frame))

    def test_moving_a_physical_star_slider_creates_an_override(self):
        a = self.app
        a._stars = [(10.0, 10.0, 12.0, 0.5, (1, 1, 1))]
        a._select_star(("auto", 0))
        a.phys_star["depth"].set(42.0)
        a._on_phys_star_slider_change()
        self.assertEqual(a._phys_star_overrides[("auto", 0)]["depth"], 42.0)
        self.assertNotIn(("auto", 0), a._spike_star_overrides)
        a._reset_selected_phys_override()
        self.assertNotIn(("auto", 0), a._phys_star_overrides)


if __name__ == "__main__":
    unittest.main()
