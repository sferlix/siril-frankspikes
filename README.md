# frankSpikes

A Python GUI script for [Siril](https://siril.org/) that adds light/tone/color
adjustments and realistic diffraction spikes to a single astrophotography
image, with a live full-resolution preview — right inside Siril.

![frankSpikes screenshot](docs/screenshot.webp)

## Features

### Light, Tone & Color — a simplified "camera raw" panel
Two collapsible sections, deliberately kept to *global* adjustments — nothing that asks you to make a decision about one specific color or channel (that turned out to add complexity without helping):

- **✨ Magic Wand** (Camera RAW) — a one-click, conservative finishing pass for an already-processed image, on the tone sliders only (the spikes have their own Magic Wand). It analyses the untouched image (sky background level and colour cast, saturated cores, background noise, colour saturation), then sets: an automatic white balance on the sky background (Temperature/Tint neutralise a light-pollution cast without touching real nebula/star colour) and black/white points, plus conservative finishing moves — Highlights −5…−15 (protect cores), Shadows +5…+12 and Texture +5…+10 (less when noisy), Vibrance +8…+15, Clarity/Dehaze/Saturation 0. The black point is solved after Shadows, so opening up the faint signal never washes out the sky. Exposure and Contrast are left as they are; a report explains what it found and why
- **Base** — Temperature/Tint (white balance), Exposure, Contrast, Highlights/Shadows (recover or push just the brightest/darkest tonal region, leaving midtones alone), Whites/Blacks (the absolute white/black point)
- **Detail** — Texture (fine, small-radius local contrast), Clarity (broader mid-tone local contrast — brings out nebula structure), Dehaze (a much larger-radius local-contrast + saturation push, a simplified stand-in for removing — or, negative, adding — a soft haze/veil), Vibrance (boosts weaker colors more than already-saturated ones, protecting reds like Hα from clipping), Saturation (uniform)
- **Reset** — zeroes every Base/Detail slider back to no-change (separate from the Diffraction Spikes panel's own Reset/Defaults buttons)

### Diffraction Spikes
Realistic star spikes as produced by a reflector's secondary-mirror spider:

- **4 or 6 rays** — 2-vane/refractor spider vs. 3-vane spider (e.g. most Newtonians)
- **✨ Magic Wand** (spikes) — sets the spike sliders only, and runs automatically whenever an image is opened. From the focal length (the FITS `FOCALLEN` when present, otherwise an estimated field type: wide field/astro-landscape, medium, or long-focal deep sky) and the detected stars, it gives a spike only to the stars that stand out, in whichever mode is active — it never switches it. In Per size mode the Small tab's diameter is the cutoff (at most ~12% of the stars, and at least the focal-length size target, 3 px short → 10 px long) and Medium/Large get the full look; in Simple mode the Minimum diameter keeps noticeable spikes to about 12% of the stars while the biggest ones still reach at least half the look (Per size is more selective when the star sizes are very similar, and the report says so). The look: with Length 12×→8×, Intensity 130→165, Thickness 0.6→1.0 and Sharpness 95→55 from short to long focal length, plus Rainbow 40, Color saturation 70, Soft flare 15, Flare reach 40%, Natural variation and Twinkle 15. The ray count, flare rays/ring settings and per-star edits are left as they are; the button shows a report
- **Simple mode** (default) — one flat set of sliders (length, intensity, thickness, soft flare, flare reach, ring flare, ring flare diameter, flare rays, flare color saturation, diffraction rainbow, color saturation) covers every star in the image. Each slider's real-world effect still scales smoothly with each star's own size — essentially no effect right at the "Minimum star diameter" slider, the full dialled-in value from about 4x that diameter up — so a field of countless faint pinpoints and a handful of bright giants still look as different as they do in a real photo, from one set of controls. Stars smaller than the minimum get no spike at all
- **Per size mode** — the more advanced alternative: separate **Small / Medium / Large stars** tabs, each with the full set of controls tuned independently, blending smoothly between the three (not a hard cutoff) for finer control than Simple's one-knob-per-parameter scaling. The Small tab's own diameter doubles as the minimum-diameter cutoff. Switching from Simple to Per size carries the current look over onto the three tabs instead of resetting them, so you have a matching starting point to fine-tune from
- **Calibrated to your image** — right after detecting stars, the Small/Medium/Large (or Simple's Minimum diameter) sliders are automatically positioned from *this image's own* detected star sizes (5th/50th/90th percentile of the real field), not a one-size-fits-all guess — what counts as a "Large" star is set per picture, not hardcoded. The default spike **Length** is calibrated too, from the telescope's own focal length (the FITS `FOCALLEN` keyword, when present) — a short focal length defaults to a longer, more dramatic spike (~8x star diameter), a medium one to a shorter one (~3x), matching how the same physical spike spans more star-diameters at a shorter focal length's coarser plate scale
- **Natural variation** — a small, deterministic per-star jitter on each spike's length (seeded by the star's own position) that breaks up the "stamped" look of many similar-size stars all rendering an identical spike. Rotation is never jittered — a real spike's angle comes from the telescope's own spider vanes, the same for every star in the frame
- **Twinkle** — a tiny, fixed hint of spike on every star below the Minimum diameter/Small anchor, instead of nothing at all. A real photo never truly zeroes a star's spike out below some size — even faint stars show a small sparkle; this is deliberately much weaker than any real anchor's own look. 0 = the old hard cutoff
- **Physical spike profile** — like in real photos, each spike keeps its width along its whole length and fades with a long power-law tail plus a slight, irregular brightness flicker, instead of tapering to a needle point
- **Diffraction rainbow** — a per-size/per-star slider for the real colour pattern of a diffraction spike: it starts in the star's own colour, then further out breaks into short coloured segments with dimmer gaps (the wavelength-dependent diffraction nulls of a spider vane of finite width), washing back to neutral after a few segments. **Rainbow segment spacing** (global, in px) sets their distance — a property of the optics, so the same for every star; bigger stars with longer spikes simply show more segments
- Brightness also follows the star's own amplitude on top of its size, with each spike taking on **its own star's real color** (sampled from the star's own core pixels) rather than a flat white glow
- **Flare reach** — a per-size/per-star slider, in % of the spike length, controlling how far the Soft flare and its rays extend (default 45%). The flare starts right at the star's visible edge, so even a short reach shows outside the core instead of hiding inside it, and it never reaches past the spike tips. In Simple mode it keeps its value for every star size (only the strengths grow with size)
- **Realistic ring & soft flare** — the ring hugs the star like a real telescope's Airy diffraction ring, and a second, fainter ring is added alongside it — a real Airy pattern is a series of rings, not one clean circle. Both stay inside the spikes
- **Ring flare diameter** — a per-size/per-star slider setting the ring's own diameter in star diameters (default 1.6x, just past the star's edge); always kept outside the core and inside the spikes
- **Flare color saturation** — a per-size/per-star slider, separate from the spike rays' own Color saturation, that tints the Soft flare and Ring flare glow toward the star's own color (0 = pure white, the original look)
- **Flare rays** — a per-size/per-star slider that breaks the Soft flare glow up into the soft, irregular streaks of a real sunburst: the same halo light redistributed into rays of uneven brightness and spacing, more of them further out (they branch), with the strongest ones hugging each main spike as faint secondary spikes (0 = a plain round glow). **Flare ray symmetry** (global) sets how strictly the pattern repeats in every wedge between main spikes — 100 = exactly, like the spider geometry itself; 0 = fully irregular, like scatter and seeing; real photos sit in between (default 40). Replaces the old separate Ray flare
- **Sharpness** — softens the whole effect for long focal lengths, where seeing/optics blur real diffraction spikes well beyond a pixel-crisp render
- **Color hue** — a global rotation of every spike's own star color
- **Robust star detection** — a very rich star field (e.g. a dense Milky Way region) can hold far more real stars than Siril's own detector returns in one pass; frankSpikes tiles the image and detects each tile separately to cover the whole frame, and separately catches bright/saturated stars whose blown-out core a normal PSF fit rejects — so a field with thousands of real stars doesn't end up with spikes on only a lucky few
- **Manual editing** — Ctrl+Click a star in the preview to remove/restore its spikes (or force one onto a star smaller than the current minimum diameter), or Ctrl+Click empty space to add one manually, exactly where you click
- **Per-star editing** — Shift+Click a star to select it (marked with a dashed circle) and its own sliders replace the global ones, letting you dial in that one star's exact look, completely independent of the Simple/Per-size settings. Shift+Click empty space, or the panel's Deselect button, goes back to the global controls; "Reset this star to its size-based look" drops just that star's override

### Preview & workflow
- Real full-resolution pan/zoom preview (Fit / 100% / +/-), with a **Navigator** thumbnail showing the current viewport. While zoomed in, dragging a Base/Detail slider only recomputes the crop actually on screen, not the whole image — full-image work only happens once, right when you pan/zoom or go back to Fit
- **Hide background (spikes only)** — a toolbar checkbox that shows just the additive spike layer on black, so its own shape and colour can be judged without the photo underneath. Preview-only: never affects Process/import in Siril
- Hold **Space** over the preview to flash back to the original, untouched image at the same pan/zoom position
- The mouse pointer switches to a busy cursor whenever a render is in progress, so it's always clear when it's safe to keep adjusting
- **Process and import in Siril** applies the result directly to the active image and pushes its own undo checkpoint in Siril — the script window stays open, so you can keep adjusting and reprocessing as many times as you like before saving

## Standalone mode (no Siril required)

frankSpikes also runs on its own, without Siril open at all — useful for editing a FITS, TIFF, JPG or PNG file directly, or on a machine without Siril installed. Launching the script with no Siril connection available automatically switches it to standalone mode:

- **File → Open...** (Ctrl+O) loads a `.fits`/`.fit`/`.fts`, `.tif`/`.tiff`, `.jpg`/`.jpeg` or `.png` file directly from disk. JPG/PNG are 8-bit (16-bit only for greyscale PNG) and carry no focal length, so the spike defaults aren't focal-length calibrated for them
- Star detection uses [photutils](https://photutils.readthedocs.io/)' `DAOStarFinder` in place of Siril's own `findstar`
- The button becomes **Process and Save As...**: it renders the result, then opens a Save dialog (FITS, TIFF, JPG or PNG, picked by the extension you type/choose; JPG/PNG are saved 8-bit, JPG at quality 95) instead of pushing into a live Siril image
- **File → Save As...** (Ctrl+S) re-exports the last processed result without recomputing, e.g. to save a second copy in another format
- Closing the window, or opening another image, with edits that haven't been saved yet asks for confirmation first

Standalone mode needs a few packages beyond the Siril-connected mode's `numpy`/`Pillow`:

```
pip install astropy photutils tifffile
```

If you already have Siril installed, its own bundled Python environment (`%LOCALAPPDATA%/siril/venv` on Windows) typically already has all of these — you can run frankSpikes standalone with that same interpreter instead of installing anything: `path\to\siril\venv\Scripts\python.exe frankSpikes.py`.

## Requirements

- Either [Siril](https://siril.org/) 1.2+ with Python scripting support (`sirilpy`), **or** standalone mode's own dependencies (see above) — not both
- Python packages: `numpy`, `Pillow` (usually already available in Siril's bundled Python environment); standalone mode additionally needs `astropy`, `photutils`, `tifffile`

## Installation

**Inside Siril:**
1. Download [`frankSpikes.py`](frankSpikes.py).
2. In Siril, open **Scripts → Python Scripts → Show Scripts Repository Folder** (or add the folder containing this script as a Python scripts path).
3. Copy `frankSpikes.py` into that folder.
4. In Siril, open the image you want to edit.
5. Menu **Scripts → Python Scripts → frankSpikes**.

**Standalone:** run `python frankSpikes.py` (with the dependencies above installed) with no Siril running - see "Standalone mode" above.

## How to use it

1. In Siril, open the image you want to edit (standalone mode: use **File → Open...** instead once the script window is up).
2. Run the script. It reads the image that's already open in Siril automatically — there's nothing to browse for or load by hand.
3. Move the sliders while watching the preview.
4. Click **Process and import in Siril**: the result is applied directly to the active image in Siril. The script stays open, so if you don't like the result, keep adjusting the sliders and Process again as many times as you want — each pass starts fresh from the untouched original, never stacking on the previous result. Saving or undoing is done in Siril itself (File → Save, Ctrl+Z), exactly like any other Siril step. In standalone mode, this button instead prompts a Save dialog each time.
5. Close the window whenever you're happy with the result. If there are edits you haven't applied to Siril yet with Process, frankSpikes asks for confirmation first, since closing would lose them.

## Author

**Frank Sferlazza** — [facebook.com/francesco.sferlazza](https://www.facebook.com/francesco.sferlazza)

## License

Not yet specified — all rights reserved by the author unless stated otherwise.
