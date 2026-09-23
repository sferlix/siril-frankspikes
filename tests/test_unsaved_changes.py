"""Standalone mode: closing the window (or opening another image) with
edits that haven't been saved asks for confirmation first."""
import unittest
import tkinter as tk
from unittest import mock
from _harness import fs


class _StandaloneStub:
    standalone = True
    _src_ext = ".jpg"
    last_rgb = None

    def get_wd(self):
        return "."

    def log(self, msg):
        pass

    def clear_stars(self):
        pass

    def save_rgb(self, rgb, path, bit_depth=None):
        pass


class _SirilStub(_StandaloneStub):
    standalone = False


class UnsavedCase(unittest.TestCase):
    worker_cls = _StandaloneStub

    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest(f"no display: {e}")
        self.root.withdraw()
        self._orig_reload = fs.App._on_reload
        fs.App._on_reload = lambda self: None
        self.app = fs.App(self.root, self.worker_cls())
        self.app._redraw_canvas = lambda: None
        # as right after an image finished loading
        self.app.loaded = True
        self.app._saved_sig = self.app._edit_signature()
        self.destroyed = False
        self._real_destroy = self.root.destroy
        self.root.destroy = lambda: setattr(self, "destroyed", True)

    def tearDown(self):
        fs.App._on_reload = self._orig_reload
        for ident in self.root.tk.splitlist(self.root.tk.call("after", "info")):
            try:
                self.root.after_cancel(ident)
            except tk.TclError:
                pass
        self._real_destroy()

    def _close(self, answer):
        with mock.patch.object(fs.messagebox, "askyesno", return_value=answer) as ask:
            self.app._on_close()
        return ask


class TestUnsavedChanges(UnsavedCase):
    def test_no_edits_closes_without_asking(self):
        ask = self._close(False)
        ask.assert_not_called()
        self.assertTrue(self.destroyed)

    def test_edited_asks_and_no_keeps_it_open(self):
        self.app.spike_rotation.set(self.app.spike_rotation.get() + 10)
        ask = self._close(False)
        ask.assert_called_once()
        self.assertFalse(self.destroyed)

    def test_edited_asks_and_yes_closes(self):
        self.app.tone["exposure"].set(0.5)
        ask = self._close(True)
        ask.assert_called_once()
        self.assertTrue(self.destroyed)

    def test_per_star_edits_count_too(self):
        self.app._spike_disabled.add(0)
        self.assertTrue(self.app._has_unsaved_changes())

    def test_saved_result_clears_it(self):
        self.app.spike_rotation.set(self.app.spike_rotation.get() + 10)
        self.app._processed_sig = self.app._edit_signature()   # Process
        with mock.patch.object(fs.filedialog, "asksaveasfilename", return_value="out.jpg"):
            self.app._prompt_save_as(None)
        ask = self._close(False)
        ask.assert_not_called()
        self.assertTrue(self.destroyed)

    def test_edits_after_the_save_are_unsaved_again(self):
        self.app._processed_sig = self.app._edit_signature()
        with mock.patch.object(fs.filedialog, "asksaveasfilename", return_value="out.jpg"):
            self.app._prompt_save_as(None)
        self.app.spike_rotation.set(self.app.spike_rotation.get() + 10)
        self.assertTrue(self.app._has_unsaved_changes())

    def test_cancelled_save_is_still_unsaved(self):
        self.app.spike_rotation.set(self.app.spike_rotation.get() + 10)
        self.app._processed_sig = self.app._edit_signature()
        with mock.patch.object(fs.filedialog, "asksaveasfilename", return_value=""):
            self.app._prompt_save_as(None)
        self.assertTrue(self.app._has_unsaved_changes())

    def test_opening_another_image_asks_first(self):
        self.app.spike_rotation.set(self.app.spike_rotation.get() + 10)
        with mock.patch.object(fs.messagebox, "askyesno", return_value=False) as ask, \
                mock.patch.object(fs.filedialog, "askopenfilename") as pick:
            self.app._on_open_file()
        ask.assert_called_once()
        pick.assert_not_called()


class TestSirilModeNeverAsks(UnsavedCase):
    worker_cls = _SirilStub

    def test_edits_in_siril_mode_close_directly(self):
        self.app.spike_rotation.set(self.app.spike_rotation.get() + 10)
        ask = self._close(False)
        ask.assert_not_called()
        self.assertTrue(self.destroyed)


if __name__ == "__main__":
    unittest.main()
