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


if __name__ == "__main__":
    unittest.main()
