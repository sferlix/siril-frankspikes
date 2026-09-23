"""Developer aid: opens the real UI with a stub worker and saves screenshots of the
window (whole window and the Physical spikes area) next to this file."""
import os
import tkinter as tk
from PIL import ImageGrab
from _harness import fs


class StubWorker:
    standalone = False

    def get_wd(self):
        return "."

    def log(self, msg):
        pass


fs.App._on_reload = lambda self: None
root = tk.Tk()
fs._make_dpi_aware() if hasattr(fs, "_make_dpi_aware") else None
app = fs.App(root, StubWorker())
root.geometry("1500x950+20+20")
root.update_idletasks()
root.update()
here = os.path.dirname(os.path.abspath(__file__))


def shot(name):
    root.update()
    x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(os.path.join(here, name))


shot("ui_simple.png")
# scroll the spikes panel down to see the rest of the controls
app._spikes_canvas.yview_moveto(0.55)
shot("ui_simple_scrolled.png")
root.destroy()
print("saved")
