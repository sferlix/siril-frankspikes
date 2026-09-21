"""Renders a synthetic star field with the classic layer, the physical layer,
and both, into demo_spikes.png next to this file (developer aid, not shipped)."""
import os
import numpy as np
from PIL import Image
from _harness import fs, star_field

W, H = 1200, 800
stars = [s for s in star_field(150, W, H, seed=5) if s[2] >= 4.0]
stars += [(300.0, 250.0, 26.0, 1.0, (1.0, 0.85, 0.7), False, None),
          (800.0, 500.0, 40.0, 1.0, (0.8, 0.9, 1.0), False, None),
          (600.0, 150.0, 12.0, 1.0, (1.0, 1.0, 1.0), False, None)]
yy, xx = np.mgrid[:H, :W]
sky = np.full((H, W, 3), 0.03, np.float32)
for (x, y, fwhm, amp, color, _f, _o) in stars:
    sig = fwhm / 2.355
    g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sig ** 2))
    sky = np.clip(sky + (np.clip(3 * amp * g, 0, 1))[..., None] * np.array(color, np.float32), 0, 1)

ccfg = {"anchors": [dict(a) for a in fs.SPIKE_DEFAULTS["anchors"]], "rays": 4, "rotation": 30.0,
        "hue": 0.0, "sharpness": 100.0, "variation": 15.0}
pcfg = {"anchors": [dict(a, diam=c["diam"]) for a, c in zip(fs.PHYS_DEFAULTS["anchors"], ccfg["anchors"])],
        "aperture": "spider4", "blades": 6, "rotation": 30.0, "fft_from": 15.0, "seeing": fs.PHYS_DEFAULTS["seeing"]}
classic = fs.render_spike_layer((H, W), 0, 0, W, H, stars, ccfg)
phys = fs.render_physical_layer((H, W), 0, 0, W, H, stars, pcfg)
panels = [fs.apply_spikes(sky, classic), fs.apply_spikes(sky, phys),
          fs.apply_spikes(fs.apply_spikes(sky, classic), phys)]
out = np.concatenate(panels, axis=0)
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_spikes.png")
Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(path)
print(path)
