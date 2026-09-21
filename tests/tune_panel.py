"""Developer aid: single-star grid of the physical layer for a few (depth, seeing) pairs."""
import os
import numpy as np
from PIL import Image, ImageDraw
from _harness import fs

S = 500
FW = (6.0, 12.0, 26.0)
SETS = [(85, 1.0)]
rows = []
for depth, seeing in SETS:
    tiles = []
    for fw in FW:
        yy, xx = np.mgrid[:S, :S]
        g = np.exp(-((xx - S / 2) ** 2 + (yy - S / 2) ** 2) / (2 * (fw / 2.355) ** 2))
        sky = np.clip(0.03 + np.clip(3 * g, 0, 1)[..., None] * np.ones(3), 0, 1).astype(np.float32)
        p = dict(fs.PHYS_UNIFORM_DEFAULTS, depth=float(depth))
        anchors = [dict(p, diam=3.0), dict(p, diam=12.0)]
        cfg = {"anchors": anchors, "aperture": "spider4", "blades": 6, "rotation": 0.0,
               "fft_from": 15.0, "seeing": seeing}
        star = [(S / 2.0, S / 2.0, fw, 1.0, (1.0, 0.95, 0.9), False, None)]
        layer = fs.render_physical_layer((S, S), 0, 0, S, S, star, cfg)
        img = (np.clip(fs.apply_spikes(sky, layer), 0, 1) * 255).astype(np.uint8)
        im = Image.fromarray(img)
        ImageDraw.Draw(im).text((4, 4), f"fwhm {fw:.0f} depth {depth} seeing {seeing}", fill=(255, 220, 120))
        tiles.append(np.asarray(im))
    rows.append(np.concatenate(tiles, axis=1))
out = np.concatenate(rows, axis=0)
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tune_panel.png")
Image.fromarray(out).save(path)
print(path)
