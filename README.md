# frankSpikes

A Python GUI script for [Siril](https://siril.org/) that adds light/tone/color
adjustments and realistic diffraction spikes to a single astrophotography
image, with a live full-resolution preview — right inside Siril.

![frankSpikes screenshot](docs/screenshot.webp)

## Features

### Light & Tones
- **Exposure** — brightens/darkens the whole image
- **Contrast** — separates the subject from the background
- **Blacks / Sky Background** — sets how deep the sky/background is
- **Highlights / Whites** — protects the brightest areas from burning, or pushes them brighter
- **Clarity** — local (mid-tone) contrast on a large-radius unsharp mask, brings out nebula structure without touching global contrast

### Color & Hue
- **Vibrance** — boosts weaker colors more than already-saturated ones (protects reds like Hα from clipping), unlike a flat Saturation boost
- **Saturation** — makes all colors more or less vivid, uniformly
- **Temperature** — blue/yellow color balance
- **Tint** — green/magenta color balance (handy for removing the greenish light-pollution cast)

### Diffraction Spikes
Realistic star spikes as produced by a reflector's secondary-mirror spider:

- **4 or 6 rays** — 2-vane/refractor spider vs. 3-vane spider (e.g. most Newtonians)
- **Small / Medium / Large stars tabs** — each star's own diameter smoothly blends its look between three size anchors, so a field of countless faint pinpoints and a handful of bright giants can look as different as they do in a real photo, instead of every qualifying star getting an identical spike. Length, intensity, thickness, soft flare, ring flare, color fringing, rainbow and color saturation are all independently tunable per anchor. Stars smaller than the Small anchor's diameter get no spike at all (that anchor doubles as the minimum-diameter cutoff)
- **Natural variation** — a small, deterministic per-star jitter on each spike's length and rotation (seeded by the star's own position) that breaks up the "stamped" look of many similar-size stars all rendering an identical spike
- Brightness also follows the star's own amplitude on top of its size, with each spike taking on **its own star's real color** (sampled from the star's own core pixels) rather than a flat white glow
- **Sharpness** — softens the whole effect for long focal lengths, where seeing/optics blur real diffraction spikes well beyond a pixel-crisp render
- **Color hue** — a global rotation of every spike's own star color
- **Manual editing** — Ctrl+Click a star in the preview to remove/restore its spikes (or force one onto a star smaller than the Small anchor's diameter), or Ctrl+Click empty space to add one manually, exactly where you click

### Preview & workflow
- Real full-resolution pan/zoom preview (Fit / 100% / +/-), with a **Navigator** thumbnail showing the current viewport
- Hold **Space** over the preview to flash back to the original, untouched image at the same pan/zoom position
- **Process and import in Siril** applies the result directly to the active image and pushes its own undo checkpoint in Siril — the script window stays open, so you can keep adjusting and reprocessing as many times as you like before saving

## Requirements

- [Siril](https://siril.org/) 1.2+ with Python scripting support (`sirilpy`)
- Python packages: `numpy`, `Pillow` (usually already available in Siril's bundled Python environment)

## Installation

1. Download [`frankSpikes.py`](frankSpikes.py).
2. In Siril, open **Scripts → Python Scripts → Show Scripts Repository Folder** (or add the folder containing this script as a Python scripts path).
3. Copy `frankSpikes.py` into that folder.
4. In Siril, open the image you want to edit.
5. Menu **Scripts → Python Scripts → frankSpikes**.

## How to use it

1. In Siril, open the image you want to edit.
2. Run the script. It reads the image that's already open in Siril automatically — there's nothing to browse for or load by hand.
3. Move the sliders while watching the preview.
4. Click **Process and import in Siril**: the result is applied directly to the active image in Siril. The script stays open, so if you don't like the result, keep adjusting the sliders and Process again as many times as you want — each pass starts fresh from the untouched original, never stacking on the previous result. Saving or undoing is done in Siril itself (File → Save, Ctrl+Z), exactly like any other Siril step.
5. Close the window whenever you're happy with the result.

## Author

**Frank Sferlazza** — [facebook.com/francesco.sferlazza](https://www.facebook.com/francesco.sferlazza)

## License

Not yet specified — all rights reserved by the author unless stated otherwise.
