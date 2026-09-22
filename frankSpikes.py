"""
frankSpikes - Siril GUI script (Python)
Author: Frank Sferlazza

Light/tone and color/hue adjustment tool for a single image, in the same
dark-themed style and with the same real full-resolution zoom/pan preview
as BB/NB Mixer.

Controls:
Light & Tones
   - Exposure: brightens/darkens the whole image
   - Contrast: separates the subject from the background
   - Blacks / Sky Background: sets how deep the sky/background is
   - Highlights / Whites: protects the brightest areas from burning, or
     pushes them brighter
   - Clarity: local (mid-tone) contrast on a large-radius unsharp mask,
     brings out nebula structure without touching global contrast
Color & Hue
   - Vibrance: boosts weaker colors more than already-saturated ones
     (protects reds like Ha from clipping), unlike a flat Saturation boost
   - Saturation: makes all colors more or less vivid, uniformly
   - Temperature: blue/yellow color balance
   - Tint: green/magenta color balance (handy for removing the greenish
     light-pollution cast)
Diffraction Spikes (panel to the right of the preview)
   - Realistic star spikes as produced by a reflector's secondary-mirror
     spider: 4 rays for a 2-vane (or refractor) spider, 6 rays for a 3-vane
     spider (e.g. most Newtonians).
   - Simple / Per size mode: two ways to control how a star's own diameter
     shapes its spike (Simple is the default).
     * Simple (one control for all stars): one flat slider set - no size
       tabs to juggle. Every slider's real-world effect still scales with
       each star's own size - essentially no effect right at the Minimum
       star diameter, the full dialled-in value from about 4x that diameter
       up - so a field of countless faint pinpoints and a handful of bright
       giants still look as different as they do in a real photo, just from
       one set of sliders. Stars smaller than the Minimum star diameter get
       no spike at all.
     * Per size (Small/Medium/Large tabs): each star's look blends smoothly
       between three size anchors you tune independently (not a hard
       cutoff) - length, intensity, thickness, soft flare, ring flare,
       color fringing, rainbow and color saturation - for finer control
       than Simple's one-knob-per-parameter scaling. Stars smaller than the
       Small tab's own star size get no spike at all (that tab doubles as
       the old "minimum diameter" cutoff).
   - Natural variation: a small, deterministic per-star jitter on each
     spike's length and rotation (seeded by the star's own position, so it
     never changes between re-renders) - breaks up the "stamped/CGI" look
     of many similar-size stars all rendering pixel-identical spikes.
     0 = perfectly formulaic, matching every star's raw parameters exactly.
   - Twinkle: a tiny, fixed hint of spike on every star below the Minimum
     diameter/Small anchor, instead of nothing - real photos never show a
     hard cutoff, even faint stars show a small sparkle. Much weaker than
     any real anchor's own look; 0 = the old hard cutoff.
   - Brightness also follows the star's own amplitude on top of its size
     (with a floor so ordinary stars aren't crushed to invisibility next to
     the single brightest one in the field), and rays stay strong for most
     of their length before tapering near the tip.
   - Each spike takes on its own star's real colour (sampled from the
     star's own core pixels) rather than a flat white glow.
   - Sharpness: softens the whole effect - useful at long focal lengths,
     where seeing/optics blur real diffraction spikes well beyond a
     pixel-crisp render (100 = untouched, lower = softer).
   - Color hue: rotates every star's spike colour by the same amount.
   - Color fringing (per anchor): a blue-near-star/warm-near-tip chromatic
     separation on top of the star's colour, like real wavelength-dependent
     diffraction.
   - Rainbow intensity (per anchor): an artistic multi-hue cycle along each
     ray, also layered on top of the star's own colour.
   - Color saturation (per anchor): 0 keeps that size of star's spike/flare
     pure white regardless of its own colour or the other color sliders.
   - Soft flare tail length (per anchor): adds a long power-law tail to the
     Soft flare glow, out to that many star diameters (0 = the original
     gaussian-only glow, unchanged).
   - After generating, Ctrl+Click a star in the preview to remove/restore
     its spikes (this also lets you force a spike onto a star smaller than
     the Small anchor's diameter), or Ctrl+Click empty space to add one
     manually.
   - Shift+Click a star to select it for individual editing: a dashed
     circle marks it, and the same sliders switch to that one star's own
     look, completely overriding the Small/Medium/Large or Simple size-
     based settings for it from then on. Shift+Click empty space, or the
     panel's Deselect button, returns to editing the global settings;
     "Reset this star to its size-based look" drops just that star's
     override.

Hold Space over the preview to see the original, untouched image at the
same pan/zoom position - release to go back to the edited view.

HOW TO USE IT
1. In Siril, open the image you want to edit.
2. Menu Scripts -> Python Scripts -> run this file. It reads the image
   that is already open in Siril automatically - there is nothing to
   browse for or load by hand.
3. Move the sliders while watching the preview.
4. Click "Process and import in Siril": the result is applied directly to
   the active image in Siril - the script stays open, so if you don't like
   it, keep adjusting the sliders and Process again as many times as you
   want (each time starts fresh from the untouched original, never
   stacking on the previous result). Saving or undoing any of those
   results is done in Siril itself (File > Save, Ctrl+Z), exactly like any
   other Siril step - each Process pushes its own undo checkpoint there.
   Close the window whenever you're happy with the result.
"""

import os
import sys
import math
import threading
import queue
import traceback
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageTk

import sirilpy as s
from sirilpy import SirilConnectionError

APP_VERSION = "2.2.0"
PREVIEW_MAX_W = 1600
NAV_MAX_W = 210
NAV_MAX_H = 160
FACEBOOK_URL = "https://www.facebook.com/francesco.sferlazza"

# One row per size-anchor parameter: (key, slider label, lo, hi, step,
# display format). Drives both the tk.Var setup and the tabbed UI in a
# loop, instead of ~30 hand-written blocks (one per param per anchor).
SPIKE_ANCHOR_PARAM_DEFS = [
    # "diam"'s (lo, hi) here are just a fallback shape - the actual slider
    # range for each tab comes from SPIKE_ANCHOR_DIAM_RANGES below, since a
    # "Small" star and a "Large" star warrant very different ranges (no
    # real star's FWHM ever approaches this row's own numbers).
    ("diam",       "Star size this tab applies to (px)", 1,   160, 1,   "{:.0f}"),
    ("length",     "Spike length (x star diameter)",     0.5, 12,  0.1, "{:.1f}x"),
    ("intensity",  "Intensity",                          0,   250, 5,   "{:.0f}"),
    ("thickness",  "Thickness",                          0.1, 6,   0.1, "{:.1f}"),
    ("soft_flare", "Soft flare",                          0,   100, 5,   "{:.0f}"),
    ("flare_tail", "Soft flare tail length (x star diameter)", 0, 30,  0.5, "{:.1f}x"),
    ("ring_flare", "Ring flare",                          0,   100, 5,   "{:.0f}"),
    ("chroma",     "Color fringing (chromatic)",          0,   100, 5,   "{:.0f}"),
    ("rainbow",    "Rainbow intensity",                   0,   100, 5,   "{:.0f}"),
    ("saturation", "Color saturation",                    0,   100, 5,   "{:.0f}"),
]
SPIKE_ANCHOR_TAB_LABELS = ("Small stars", "Medium stars", "Large stars")
# Per-tab (lo, hi) px range for the Diameter anchor slider - tighter at the
# small end (typical cutoff sizes) and capped at the large end to what a
# badly bloated/saturated star's FWHM realistically reaches; a uniform
# 1-300 range on every tab made small, precise drags on "Small" and
# "Medium" nearly impossible. Calibrated against a real field's detected
# fwhm distribution (frankSpikes' own diagnostic Reload log): most stars
# fall under ~10px, with a genuinely large/bright star around ~15-20px -
# the original 1/5/15-40/90/160 ranges assumed FWHM values roughly 4-8x
# too big, which is why a 20px "minimum diameter" cutoff used to exclude
# 98%+ of real stars in that field.
SPIKE_ANCHOR_DIAM_RANGES = ((1, 15), (2, 30), (5, 60))
# Small stars are supposed to look subtler than Large ones - that's the
# whole point of size grading - so their well-tuned Intensity/Thickness/etc.
# values naturally sit low. But every tab shared the same slider ceiling
# (SPIKE_ANCHOR_PARAM_DEFS' "hi", e.g. Intensity 0-250), so a Small value
# like 10 or 15 lived in the bottom ~5% of the slider's travel - clicking
# anywhere on most of the track overshot it by a huge margin, making fine
# adjustment nearly impossible. Each tab's sliders (for every key except
# "diam", which already has its own per-tab SPIKE_ANCHOR_DIAM_RANGES) now
# scale their ceiling down from the full defined (lo, hi) span by this
# fraction (Small, Medium, Large) - Large keeps the full range unchanged
# (scale 1.0, so its own hand-tuned defaults and anything a user dials in
# still fit exactly as before), Small and Medium get a proportionally
# tighter one so the same slider travel maps to a finer value increment.
SPIKE_ANCHOR_LOOK_SCALE = (0.4, 0.7, 1.0)
_SPIKE_ANCHOR_PARAM_FULL_RANGE = {k: (lo, hi) for k, _label, lo, hi, _step, _fmt in SPIKE_ANCHOR_PARAM_DEFS}


def spike_anchor_slider_range(tab_index, key):
    """(lo, hi) a given per-size tab's slider for `key` actually spans -
    the same math _build_ui uses to construct the widgets, exposed so
    other code (the Uniform -> Per-size seeding hand-off, the per-image
    auto-calibration) can clamp values it sets into range instead of
    silently exceeding what the slider can display."""
    if key == "diam":
        return SPIKE_ANCHOR_DIAM_RANGES[tab_index]
    lo, hi = _SPIKE_ANCHOR_PARAM_FULL_RANGE[key]
    return lo, lo + (hi - lo) * SPIKE_ANCHOR_LOOK_SCALE[tab_index]

# Single source of truth for the spike panel's defaults, used both to set
# up the controls and by the "Defaults" button - one place to tune them.
# The "Medium" anchor's 8 look parameters reproduce frankSpikes 1.0's old
# fixed look exactly (same numbers, previously the only size available) -
# only stars smaller or larger than it taper toward a subtler or a more
# dramatic look instead of getting an identical spike regardless of size.
# The anchors' "diam" positions (where each look actually applies) were
# originally guessed far too high - a real field's detected fwhm rarely
# exceeds ~20px, so a "Large" anchor at 80px was essentially unreachable
# and a 20px "Small"/minimum-diameter cutoff excluded ~98% of real stars
# (confirmed via frankSpikes' own diagnostic Reload log on a real image:
# fwhm min=2.0px median=6.8px, only 16/1000 stars above 20px). Repositioned
# to 3/8/18px to actually span a typical field's stars.
SPIKE_DEFAULTS = {
    "enabled": True,
    "rays": 4,
    "rotation": 30.0,
    "hue": 0.0,
    "sharpness": 100.0,
    "variation": 15.0,
    # A real photo never truly zeroes a star out below some size threshold -
    # even faint ones show a tiny hint of a cross (see the analysis in the
    # commit that added this). "Twinkle" gives every star below the current
    # Minimum diameter/Small anchor that same small, fixed hint instead of
    # nothing, independent of Simple/Per-size and much weaker than any real
    # anchor's own look (see TWINKLE_* below). 0 reproduces frankSpikes 2.1's
    # hard cutoff exactly.
    "twinkle": 20.0,
    "anchors": [
        {"diam": 3.0, "length": 2.0, "intensity": 40.0, "thickness": 0.8,
         "soft_flare": 0.0, "flare_tail": 0.0, "ring_flare": 0.0, "chroma": 0.0,
         "rainbow": 0.0, "saturation": 0.0},
        {"diam": 8.0, "length": 4.0, "intensity": 110.0, "thickness": 1.1,
         "soft_flare": 11.0, "flare_tail": 0.0, "ring_flare": 7.0, "chroma": 21.0,
         # A real reference photo's spikes stay close to the star's own
         # colour with at most a mild shift (see chroma above) - no cycling
         # multi-hue "rainbow" by default. The slider itself stays available.
         "rainbow": 0.0, "saturation": 0.0},
        {"diam": 18.0, "length": 6.5, "intensity": 170.0, "thickness": 1.6,
         "soft_flare": 35.0, "flare_tail": 0.0, "ring_flare": 20.0, "chroma": 45.0,
         "rainbow": 0.0, "saturation": 55.0},
    ],
}

# "Uniform" mode (single slider set for every star size, see spike_mode)
# reuses the exact same anchor-interpolation code as the per-size anchors
# above, fed two synthetic anchors instead of three: zero effect right at
# "min_diam" (the cutoff, same role as the smallest per-size anchor's
# diameter) and these literal slider values at SPIKE_UNIFORM_REF_MULT times
# that diameter and beyond - so every parameter's real-world impact still
# scales smoothly with each star's own size from a single knob per
# parameter. Defaults tuned for a natural, photographic look (restrained
# length/intensity, thin rays, only a slight star-colour tint, no rainbow,
# minimal ring flare) rather than a flashy preset - only the handful of
# genuinely bright stars in a field should show a clearly visible spike.
# min_diam matches SPIKE_DEFAULTS' Small anchor - see that dict's comment
# for why 20px (the original default) excluded ~98% of a real field's stars.
SPIKE_UNIFORM_REF_MULT = 4.0
SPIKE_UNIFORM_DEFAULTS = {
    "min_diam": 3.0,
    "length": 5.0, "intensity": 140.0, "thickness": 1.0,
    "soft_flare": 15.0, "flare_tail": 0.0, "ring_flare": 5.0, "chroma": 15.0,
    "rainbow": 0.0, "saturation": 25.0,
}

PALETTE = {
    "bg": "#0e1117",
    "panel": "#161a23",
    "border": "#262c3a",
    "input_bg": "#1c212c",
    "trough": "#0a0c11",
    "text": "#e7e9ee",
    "muted": "#8891a5",
    "accent": "#4f7cff",
    "accent_hover": "#6f95ff",
    "accent_disabled": "#33405e",
    "green": "#3ddc84",
    "red": "#ef5555",
    "red_hover": "#f47a7a",
    "amber": "#e0a53d",
    "amber_hover": "#eab662",
}

FONT_BASE = ("Segoe UI", 9)
FONT_HEADER = ("Segoe UI", 15, "bold")
FONT_SUBHEADER = ("Segoe UI", 9)
FONT_CARD_TITLE = ("Segoe UI", 10, "bold")
FONT_BADGE = ("Segoe UI", 8, "bold")


def build_app_icon(size=64):
    """A small diffraction-spike glyph (bright core + 8 tapered rays) used
    as the window/taskbar icon - drawn in code rather than a bundled image
    file, so the app stays a single script, and directly evokes what it
    does instead of Tk's generic default feather icon."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = size / 2
    core = (255, 255, 255, 255)
    ray = (111, 149, 255, 255)  # PALETTE["accent_hover"]
    for angle, length_frac, width in (
        (0, 0.46, 3), (90, 0.46, 3), (180, 0.46, 3), (270, 0.46, 3),
        (45, 0.24, 2), (135, 0.24, 2), (225, 0.24, 2), (315, 0.24, 2),
    ):
        rad = math.radians(angle)
        x2 = cx + size * length_frac * math.cos(rad)
        y2 = cy + size * length_frac * math.sin(rad)
        draw.line([(cx, cy), (x2, y2)], fill=ray, width=width)
    r = size * 0.09
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=core)
    return img.filter(ImageFilter.GaussianBlur(0.6))


def setup_style(root):
    """Dark theme with blue accents, matching BB/NB Mixer: cards with bold
    headers, solid buttons for the main actions, a 'pill' toolbar for zoom.
    'clam' is the only ttk theme that actually honors custom colors on
    Windows (the native theme ignores most of them)."""
    P = PALETTE
    root.configure(bg=P["bg"])

    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=P["bg"], foreground=P["text"], font=FONT_BASE,
                     fieldbackground=P["input_bg"], bordercolor=P["border"],
                     lightcolor=P["border"], darkcolor=P["border"])

    style.configure("TFrame", background=P["bg"])
    style.configure("Card.TFrame", background=P["panel"])
    style.configure("Toolbar.TFrame", background=P["panel"])

    style.configure("TLabel", background=P["bg"], foreground=P["text"])
    style.configure("Muted.TLabel", background=P["bg"], foreground=P["muted"])
    style.configure("Card.TLabel", background=P["panel"], foreground=P["text"])
    style.configure("CardMuted.TLabel", background=P["panel"], foreground=P["muted"])
    style.configure("Header.TLabel", background=P["bg"], foreground=P["text"], font=FONT_HEADER)
    style.configure("SubHeader.TLabel", background=P["bg"], foreground=P["muted"], font=FONT_SUBHEADER)
    style.configure("Badge.TLabel", background=P["accent"], foreground="white",
                     font=FONT_BADGE, padding=(8, 3))
    style.configure("ZoomPct.TLabel", background=P["panel"], foreground=P["accent"],
                     font=FONT_CARD_TITLE)
    style.configure("Status.TLabel", background=P["panel"], foreground=P["green"], font=FONT_BASE)

    style.configure("TLabelframe", background=P["panel"], bordercolor=P["border"],
                     relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=P["panel"], foreground=P["accent"],
                     font=FONT_CARD_TITLE)

    style.configure("TEntry", fieldbackground=P["input_bg"], foreground=P["text"],
                     bordercolor=P["border"], insertcolor=P["text"], padding=4)
    style.map("TEntry", fieldbackground=[("readonly", P["panel"])],
              foreground=[("readonly", P["muted"])])

    # Unstyled, these fall back to the 'clam' theme's own light/white
    # background - readable on a light window but not on this dark one,
    # and even less so once hovered/active.
    style.configure("TCheckbutton", background=P["panel"], foreground=P["text"],
                     indicatorbackground=P["input_bg"], indicatorforeground=P["accent"])
    style.map("TCheckbutton",
              background=[("active", P["panel"])],
              foreground=[("disabled", P["muted"])],
              indicatorbackground=[("selected", P["accent"]), ("active", P["input_bg"])])

    style.configure("TRadiobutton", background=P["panel"], foreground=P["text"],
                     indicatorbackground=P["input_bg"], indicatorforeground=P["accent"])
    style.map("TRadiobutton",
              background=[("active", P["panel"])],
              foreground=[("disabled", P["muted"])],
              indicatorbackground=[("selected", P["accent"]), ("active", P["input_bg"])])

    style.configure("TButton", background=P["input_bg"], foreground=P["text"],
                     bordercolor=P["border"], padding=6, relief="flat")
    style.map("TButton", background=[("active", P["border"]), ("disabled", P["panel"])],
              foreground=[("disabled", P["muted"])])

    style.configure("Accent.TButton", background=P["accent"], foreground="white",
                     padding=9, font=("Segoe UI", 9, "bold"), relief="flat")
    style.map("Accent.TButton",
              background=[("active", P["accent_hover"]), ("disabled", P["accent_disabled"])],
              foreground=[("disabled", P["muted"])])

    style.configure("Toolbar.TButton", background=P["panel"], foreground=P["text"],
                     bordercolor=P["border"], padding=(10, 5), relief="flat")
    style.map("Toolbar.TButton", background=[("active", P["accent"])])

    style.configure("Warn.TButton", background=P["amber"], foreground="#1a1200",
                     padding=6, relief="flat")
    style.map("Warn.TButton", background=[("active", P["amber_hover"])])

    style.configure("Danger.TButton", background=P["red"], foreground="white",
                     padding=6, relief="flat")
    style.map("Danger.TButton", background=[("active", P["red_hover"])])

    style.configure("Spin.TButton", background=P["input_bg"], foreground=P["text"],
                     bordercolor=P["border"], padding=0, relief="flat",
                     font=("Segoe UI", 6))
    style.map("Spin.TButton", background=[("active", P["border"])])

    style.configure("Horizontal.TScale", background=P["panel"], troughcolor=P["trough"],
                     bordercolor=P["panel"], lightcolor=P["accent"], darkcolor=P["accent"])

    style.configure("TNotebook", background=P["panel"], bordercolor=P["border"],
                     tabmargins=(2, 4, 2, 0))
    style.configure("TNotebook.Tab", background=P["input_bg"], foreground=P["text"],
                     bordercolor=P["border"], padding=(10, 5))
    style.map("TNotebook.Tab",
              background=[("selected", P["accent"]), ("active", P["border"])],
              foreground=[("selected", "white")])

    style.configure("TProgressbar", background=P["accent"], troughcolor=P["trough"],
                     bordercolor=P["panel"], lightcolor=P["accent"], darkcolor=P["accent"])

    return style


def to_hwc(arr):
    """Convert Siril's (C,H,W) pixel data (or plain (H,W) mono) to (H,W,3) RGB."""
    if arr.ndim == 2:
        return np.stack([arr, arr, arr], axis=-1)
    if arr.ndim == 3:
        if arr.shape[0] == 1:
            a = arr[0]
            return np.stack([a, a, a], axis=-1)
        if arr.shape[0] == 3:
            return np.transpose(arr, (1, 2, 0))
    return arr


def to_float01(arr):
    if arr.dtype == np.uint16:
        # Siril's "16 bits" working mode stores an originally-8-bit source (e.g.
        # a JPG) as a uint16 array whose values are never rescaled past 0-255 -
        # only the numpy dtype says "16-bit", not the actual data (confirmed via
        # a user report: fetch_full() came back with max=0.00389 == 255/65535,
        # i.e. an 8-bit image divided by the wrong denominator, ~256x too dark,
        # rendering as solid black once composited/downsampled). A genuine
        # 16-bit astro image essentially never tops out under 256 - real sensor
        # data uses far more of the range - so this is a safe, low-risk way to
        # tell the two apart without needing Siril's own bit-depth metadata.
        if arr.max() <= 255:
            return arr.astype(np.float32) / 255.0
        return arr.astype(np.float32) / 65535.0
    if arr.dtype == np.uint8:
        return arr.astype(np.float32) / 255.0
    return arr.astype(np.float32)


def downsample(arr, max_w=PREVIEW_MAX_W):
    h, w = arr.shape[:2]
    if w <= max_w:
        return arr
    scale = max_w / w
    new_w, new_h = max_w, max(1, int(h * scale))
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    im = im.resize((new_w, new_h), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0


def resize_layer(layer, out_w, out_h):
    """Area-averaging resize of an additive (H,W,3) glow layer to an exact
    target size (used to properly downsample a supersampled spike render,
    rather than point-sampling a thin line on a sparse grid)."""
    img = Image.fromarray((np.clip(layer, 0, 1) * 255).astype(np.uint8))
    img = img.resize((out_w, out_h), Image.BILINEAR)
    return np.asarray(img).astype(np.float32) / 255.0


def _blur_layer_rgb(layer, radius):
    """Gaussian-blur an additive (H,W,3) glow layer - used for the spike
    Sharpness slider (long-focal-length setups and average seeing soften
    real diffraction spikes well beyond a crisp pixel-for-pixel render)."""
    if radius <= 0:
        return layer
    img = Image.fromarray((np.clip(layer, 0, 1) * 255).astype(np.uint8), mode="RGB")
    blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.asarray(blurred).astype(np.float32) / 255.0


def format_error(e):
    """Error message with debug-useful details (errno/winerror on Windows)
    instead of plain str(e), which for OSError can hide key information."""
    head = str(e)
    if isinstance(e, OSError):
        head = f"errno={e.errno} winerror={getattr(e, 'winerror', None)} {head}"
    return head + "\n\n" + traceback.format_exc()


def _gaussian_blur(gray, radius):
    """Gaussian blur of a single-channel float [0,1] array via PIL (no scipy
    dependency needed)."""
    img = Image.fromarray((np.clip(gray, 0, 1) * 255).astype(np.uint8))
    blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.asarray(blurred).astype(np.float32) / 255.0


def apply_cosmetics(rgb, exposure, temperature, tint, contrast, blacks, highlights,
                     clarity, vibrance, saturation):
    """Full light/tone/color pass on an (H,W,3) float [0,1] image. All 9
    parameters are on a -100..100 scale, 0 = no change. Order: exposure,
    then white balance (temperature/tint), then contrast, then black/white
    point, then clarity (local contrast), then vibrance and saturation last
    (act on the final color balance)."""
    out = rgb.astype(np.float32).copy()

    stops = exposure / 100.0 * 2.0
    out = out * (2.0 ** stops)

    temp_shift = temperature / 100.0 * 0.15
    tint_shift = tint / 100.0 * 0.15
    out[..., 0] = out[..., 0] + temp_shift + tint_shift * 0.5   # R: warm + magenta
    out[..., 1] = out[..., 1] - tint_shift                       # G: green <-> magenta axis
    out[..., 2] = out[..., 2] - temp_shift + tint_shift * 0.5    # B: cool + magenta
    out = np.clip(out, 0.0, 1.0)

    c_factor = 1.0 + contrast / 100.0
    out = (out - 0.5) * c_factor + 0.5

    bp = float(np.clip(blacks / 100.0 * 0.3, -0.9, 0.9))
    out = (out - bp) / max(1e-6, 1.0 - bp)

    wp = 1.0 - float(np.clip(highlights / 100.0 * 0.3, -0.9, 0.9))
    out = out / max(1e-6, wp)

    out = np.clip(out, 0.0, 1.0)

    if clarity != 0:
        # Local (mid-tone) contrast: unsharp-mask the luminance with a large
        # radius (~1% of the shorter side) and add the extracted detail back
        # into every channel equally, so structure pops without a color
        # shift the way a per-channel unsharp mask would cause.
        h, w = out.shape[:2]
        radius = max(2, int(round(min(h, w) * 0.01)))
        luma = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
        detail = luma - _gaussian_blur(luma, radius)
        out = out + (detail * (clarity / 100.0) * 1.5)[..., None]
        out = np.clip(out, 0.0, 1.0)

    if vibrance != 0:
        # Unlike Saturation (flat boost everywhere), Vibrance pushes weakly
        # saturated pixels harder and already-vivid ones (e.g. a strong Ha
        # red) less, so it doesn't clip colors that are already intense.
        maxc = np.max(out, axis=-1)
        minc = np.min(out, axis=-1)
        cur_sat = maxc - minc
        v_factor = 1.0 + (vibrance / 100.0) * (1.0 - cur_sat)
        luma = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
        out = luma[..., None] + (out - luma[..., None]) * v_factor[..., None]
        out = np.clip(out, 0.0, 1.0)

    luma = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
    s_factor = 1.0 + saturation / 100.0
    out = luma[..., None] + (out - luma[..., None]) * s_factor

    return np.clip(out, 0.0, 1.0)


def _star_attr(st, *names, default=0.0):
    """Read the first attribute name that exists on a PSFStar object. Siril's
    Python API has used slightly different naming across versions (e.g.
    fwhm_x vs fwhmx); this keeps star detection working even if the exact
    field name drifts."""
    for n in names:
        if hasattr(st, n):
            try:
                return float(getattr(st, n))
            except (TypeError, ValueError):
                pass
    return default


def _dedupe_stars(stars, min_sep=8.0):
    """Drops near-duplicate (x, y, fwhm, amplitude) tuples that are within
    `min_sep` px of one another - used to merge tiled findstar results,
    where a star sitting near a tile boundary can get independently
    detected by more than one adjacent tile. A spatial hash (bucket size =
    min_sep) keeps this close to O(n) instead of an O(n^2) all-pairs scan,
    which matters once tiling can produce thousands of stars."""
    cell = max(1.0, min_sep)
    buckets = {}
    kept = []
    min_sep2 = min_sep * min_sep
    for star in stars:
        x, y = star[0], star[1]
        cx, cy = int(x // cell), int(y // cell)
        is_dup = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for (ox, oy) in buckets.get((cx + dx, cy + dy), ()):
                    if (ox - x) ** 2 + (oy - y) ** 2 < min_sep2:
                        is_dup = True
                        break
                if is_dup:
                    break
            if is_dup:
                break
        if is_dup:
            continue
        kept.append(star)
        buckets.setdefault((cx, cy), []).append((x, y))
    return kept


def refine_star_position(full_rgb, x, y, fwhm, max_shift_frac=0.3):
    """findstar's PSF-fit centroid can be pulled slightly off a star's true
    visual peak by nearby nebulosity or a neighbouring star, especially in
    crowded or nebulous fields - this snaps to a brightness-weighted
    centroid of the brightest pixels in a small window around the reported
    position, so spikes and flares centre on what the eye actually sees as
    the star. Robust to single-pixel noise (a weighted average of the top
    10% brightest pixels, not just the single brightest one).

    The proposed correction is capped at max_shift_frac * fwhm (floor 2px):
    findstar's own PSF fit is a more reliable estimate than this simple
    weighted centroid, so a LARGE proposed shift more likely means the
    search window caught a neighbour or a nebula wisp instead of the star
    itself - in that case the original position is kept rather than
    trusting a correction that's actually making things worse."""
    h, w = full_rgb.shape[:2]
    r = max(2, int(round(fwhm * 0.7)))
    xi, yi = int(round(x)), int(round(y))
    x0, x1 = max(0, xi - r), min(w, xi + r + 1)
    y0, y1 = max(0, yi - r), min(h, yi + r + 1)
    if x1 <= x0 or y1 <= y0:
        return x, y
    patch = full_rgb[y0:y1, x0:x1]
    luma = 0.299 * patch[..., 0] + 0.587 * patch[..., 1] + 0.114 * patch[..., 2]
    thresh = float(np.percentile(luma, 90)) if luma.size > 4 else float(luma.max())
    mask = luma >= thresh
    if not mask.any():
        return x, y
    yy, xx = np.mgrid[0:luma.shape[0], 0:luma.shape[1]]
    weights = luma[mask]
    cy = float(np.average(yy[mask], weights=weights))
    cx = float(np.average(xx[mask], weights=weights))
    rx, ry = x0 + cx, y0 + cy

    shift = ((rx - x) ** 2 + (ry - y) ** 2) ** 0.5
    if shift > max(2.0, fwhm * max_shift_frac):
        return x, y
    return rx, ry


def sample_star_color(full_rgb, x, y, fwhm):
    """The star's own colour, normalized so its brightest channel is 1.0 (a
    pure hue/colour direction - actual brightness is handled separately by
    the intensity/amplitude system).

    Any star bright enough to earn a prominent spike is usually clipped to
    white at its very core (sensor/stretch saturation) - sampling the
    brightest pixels of the patch, as a naive approach would, mostly grabs
    that clipped white and washes every star to the same near-colourless
    tint regardless of whether it looks blue or orange in the image. So
    unclipped pixels (no channel pinned near 1.0) are preferred, and the
    brightest among THOSE are used - still clearly starlight, not sky
    background, but from the PSF's wings where the true colour survives."""
    h, w = full_rgb.shape[:2]
    r = max(3, int(round(fwhm * 1.5)))
    xi, yi = int(round(x)), int(round(y))
    x0, x1 = max(0, xi - r), min(w, xi + r + 1)
    y0, y1 = max(0, yi - r), min(h, yi + r + 1)
    if x1 <= x0 or y1 <= y0:
        return (1.0, 1.0, 1.0)
    patch = full_rgb[y0:y1, x0:x1].reshape(-1, 3)
    luma = 0.299 * patch[:, 0] + 0.587 * patch[:, 1] + 0.114 * patch[:, 2]
    channel_max = patch.max(axis=1)
    not_clipped = channel_max < 0.98
    if not_clipped.any():
        candidates, cand_luma = patch[not_clipped], luma[not_clipped]
    else:
        candidates, cand_luma = patch, luma  # genuinely a fully white/overexposed star
    thresh = float(np.percentile(cand_luma, 70)) if cand_luma.size > 4 else float(cand_luma.max())
    mask = cand_luma >= thresh
    if not mask.any():
        mask = cand_luma >= cand_luma.max() * 0.9
    col = candidates[mask].mean(axis=0)
    m = max(float(col.max()), 1e-4)
    return (float(col[0] / m), float(col[1] / m), float(col[2] / m))


def _local_plateau_size(luma, x, y, peak, r=3, tol=0.995):
    """How many pixels within radius `r` of (x,y) sit within `tol` of
    `peak` - near 1 for a normal smooth PSF core (a several-pixel-sigma
    star's profile already drops several percent one pixel off centre),
    much larger for a clipped/saturated core (a real flat top). Confirmed
    on real stacked data: a visibly saturated star had 10-12 such pixels in
    a 3px radius; this is the signature used to tell the two apart, not
    just "very bright" (which a normal, well-fit bright star also is)."""
    h, w = luma.shape
    xi, yi = int(round(x)), int(round(y))
    x0, x1 = max(0, xi - r), min(w, xi + r + 1)
    y0, y1 = max(0, yi - r), min(h, yi + r + 1)
    if x1 <= x0 or y1 <= y0:
        return 0
    patch = luma[y0:y1, x0:x1]
    return int(np.sum(patch >= tol * peak))


def _measure_bright_star_profile(luma, x, y, peak, r=25):
    """Rough fwhm/amplitude estimate for a bright point source straight
    from its pixel profile (detect_saturated_stars doesn't have a PSF fit
    to read these from) - a radially-binned half-max crossing. Only needs
    to be a representative size for this script's own size-dependent
    rendering, not photometrically precise."""
    h, w = luma.shape
    xi, yi = int(round(x)), int(round(y))
    x0, x1 = max(0, xi - r), min(w, xi + r + 1)
    y0, y1 = max(0, yi - r), min(h, yi + r + 1)
    if x1 <= x0 or y1 <= y0:
        return 0.0, 0.0
    patch = luma[y0:y1, x0:x1]
    yy, xx = np.mgrid[y0:y1, x0:x1]
    rad = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
    outer = patch[rad > r * 0.7]
    bg = float(np.median(outer)) if outer.size else float(np.median(patch))
    half = bg + max(peak - bg, 1e-6) / 2.0
    half_r = float(r)
    for radius in range(1, r):
        ring = patch[(rad >= radius - 1) & (rad < radius)]
        if ring.size and float(ring.mean()) < half:
            half_r = float(radius)
            break
    fwhm = max(1.5, half_r * 2.0)
    amplitude = max(1e-6, peak - bg)
    return fwhm, amplitude


def detect_saturated_stars(full_rgb, existing_stars, bright_floor=0.90,
                            plateau_min=5, min_sep=15, max_raw_candidates=4000,
                            max_candidates=1500, downsample_factor=3):
    """Supplementary detection for very bright/saturated point sources that
    Siril's own findstar can miss - confirmed (by inspecting real stacked
    pixel data) to be because a clipped, flat-topped core fails a Gaussian/
    Moffat PSF fit's quality checks, not because those stars are dim - they
    are frequently the single brightest pixels in the whole image, findstar
    just can't fit a clean profile to them. Deliberately narrow in scope -
    only genuinely clipped/plateaued peaks (see _local_plateau_size) past
    `bright_floor` - this is not a general-purpose star finder, just a
    targeted patch for the one confirmed failure mode; findstar remains the
    primary detector for everything else, including ordinary bright stars.

    full_rgb: (H,W,3) float [0,1], the same raw-orientation array the
    caller already has in hand - no extra Siril round-trip. existing_stars:
    the (x,y,fwhm,amplitude) tuples already found by Siril, in the SAME
    pixel/coordinate convention as full_rgb, used only to avoid re-adding a
    star findstar already reported. Returns a list of new
    (xpos, ypos, fwhm, amplitude) tuples in that same convention, meant to
    be concatenated onto `existing_stars`."""
    h, w = full_rgb.shape[:2]
    luma = 0.299 * full_rgb[..., 0] + 0.587 * full_rgb[..., 1] + 0.114 * full_rgb[..., 2]

    # The local-max search runs on a downsampled copy - PIL's MaxFilter has
    # no separable fast path and measured ~18s at full 15px-window
    # resolution on a 26-megapixel image, entirely dominating Reload time.
    # A few saturated stars merging into one candidate at this coarser
    # scale is fine: the non-max-suppression pass below already collapses
    # near-duplicates, and every kept candidate is re-centred and measured
    # on the FULL-resolution luma afterward, so this only trades a little
    # positional slop for ~50x less work up front.
    ds = max(1, int(downsample_factor))
    img8_small = Image.fromarray((np.clip(luma, 0, 1) * 255).astype(np.uint8)) \
        .resize((max(1, w // ds), max(1, h // ds)), Image.BOX)
    small = np.asarray(img8_small)
    maxed_small = np.asarray(img8_small.filter(ImageFilter.MaxFilter(5)))
    bright_val = int(round(bright_floor * 255))
    mask = (small == maxed_small) & (small >= bright_val)
    ys_s, xs_s = np.nonzero(mask)
    if ys_s.size == 0:
        return []

    # Re-centre each downsampled candidate on the true full-resolution peak
    # within its cell (+/- half a downsampled pixel of slack either side).
    r = ds + 1
    ys, xs, peaks = [], [], []
    for ysd, xsd in zip(ys_s, xs_s):
        fy, fx = int(ysd * ds + ds // 2), int(xsd * ds + ds // 2)
        y0, y1 = max(0, fy - r), min(h, fy + r + 1)
        x0, x1 = max(0, fx - r), min(w, fx + r + 1)
        patch = luma[y0:y1, x0:x1]
        if patch.size == 0:
            continue
        py, px = np.unravel_index(np.argmax(patch), patch.shape)
        ys.append(y0 + py)
        xs.append(x0 + px)
        peaks.append(float(patch[py, px]))
    ys, xs, peaks = np.array(ys), np.array(xs), np.array(peaks)

    order = np.argsort(-peaks)[:max_raw_candidates]
    ys, xs, peaks = ys[order], xs[order], peaks[order]

    ex_x = np.array([s[0] for s in existing_stars], dtype=np.float64)
    ex_y = np.array([s[1] for s in existing_stars], dtype=np.float64)
    min_sep2 = min_sep * min_sep

    accepted = []  # (y, x, peak)
    for y, x, peak in zip(ys, xs, peaks):
        if ex_x.size and float(np.min((ex_x - x) ** 2 + (ex_y - y) ** 2)) < min_sep2:
            continue
        too_close = any((ay - y) ** 2 + (ax - x) ** 2 < min_sep2 for ay, ax, _ in accepted)
        if too_close:
            continue
        if _local_plateau_size(luma, x, y, peak) < plateau_min:
            continue
        accepted.append((y, x, peak))
        if len(accepted) >= max_candidates:
            break

    out = []
    for y, x, peak in accepted:
        fwhm, amplitude = _measure_bright_star_profile(luma, x, y, peak)
        if fwhm > 0:
            out.append((float(x), float(y), fwhm, amplitude))
    return out


def _rotate_hue(rgb, degrees):
    """Rotate the hue of a normalized (r,g,b) colour by `degrees`, keeping
    its saturation/value. Used to let the user dial the star-colour spikes
    toward a different tint (StarSpikes Pro's "Color Hue")."""
    if not degrees:
        return rgb
    r, g, b = rgb
    mx, mn = max(r, g, b), min(r, g, b)
    v = mx
    d = mx - mn
    s = 0.0 if mx <= 1e-6 else d / mx
    if d <= 1e-6:
        h = 0.0
    elif mx == r:
        h = (60 * ((g - b) / d) + 360) % 360
    elif mx == g:
        h = (60 * ((b - r) / d) + 120) % 360
    else:
        h = (60 * ((r - g) / d) + 240) % 360
    h = (h + degrees) % 360
    c = v * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = v - c
    if h < 60: rp, gp, bp = c, x, 0.0
    elif h < 120: rp, gp, bp = x, c, 0.0
    elif h < 180: rp, gp, bp = 0.0, c, x
    elif h < 240: rp, gp, bp = 0.0, x, c
    elif h < 300: rp, gp, bp = x, 0.0, c
    else: rp, gp, bp = c, 0.0, x
    return (rp + m, gp + m, bp + m)


def _spike_color_mult(t, star_color, chroma, rainbow, saturation):
    """Per-pixel (R,G,B) colour multipliers for a point at fractional
    distance t (0=star, 1=tip) along a ray. The base colour is the star's
    own (already hue-rotated) colour; two more effects layer on top of it,
    then the whole thing is faded toward neutral white by `saturation`
    (0 = pure white spike regardless of the star's colour or the other two
    sliders, 100 = full colour):
    - chroma: a physically-styled two-tone gradient, blue-ish near the
      star, warm near the tip (real diffraction spreads longer wavelengths
      further).
    - rainbow: an artistic multi-hue cycle along the ray's length, for the
      flashier prism-like look some presets go for.
    """
    r_col, g_col, b_col = star_color
    warm = min(1.0, chroma / 100.0) * 1.8
    r_mult = 1.0 + warm * t
    g_mult = 1.0
    b_mult = 1.0 + warm * (1.0 - t) * 0.6

    if rainbow > 0:
        amt = min(1.0, rainbow / 100.0)
        freq = 1.6  # fixed number of colour cycles along the ray
        rb_r = 0.5 + 0.5 * np.cos(2 * np.pi * (t * freq + 0.00))
        rb_g = 0.5 + 0.5 * np.cos(2 * np.pi * (t * freq + 0.33))
        rb_b = 0.5 + 0.5 * np.cos(2 * np.pi * (t * freq + 0.66))
        r_mult = r_mult * (1 - amt) + (0.4 + 1.6 * rb_r) * amt
        g_mult = g_mult * (1 - amt) + (0.4 + 1.6 * rb_g) * amt
        b_mult = b_mult * (1 - amt) + (0.4 + 1.6 * rb_b) * amt

    r_full = r_col * r_mult
    g_full = g_col * g_mult
    b_full = b_col * b_mult

    sat = min(1.0, max(0.0, saturation / 100.0))
    r_final = 1.0 + (r_full - 1.0) * sat
    g_final = 1.0 + (g_full - 1.0) * sat
    b_final = 1.0 + (b_full - 1.0) * sat
    return r_final, g_final, b_final


def _soft_knee(x, knee=0.75):
    """Identity below `knee`, then a smooth exponential approach to 1.0
    above it - used instead of a hard clip at 1.0.

    A hard clip flattens the top of a Gaussian cross-section into a wide,
    flat-topped band wherever peak*perp_falloff exceeds 1 (exactly what
    happens across a growing width of the ray as the Intensity slider is
    pushed up), which reads as a blocky, segment-like bar instead of a
    naturally tapered, pointed spike. This keeps values already below the
    knee untouched (so normal/default Intensity looks exactly as before)
    and only softens the part that would otherwise have been clipped."""
    x = np.asarray(x, dtype=np.float32)
    span = 1.0 - knee
    over = x - knee
    return np.where(x > knee, knee + span * (1.0 - np.exp(-over / span)), x)


def _add_spike_ray(layer, cx, cy, angle_deg, length_px, thickness_px, peak,
                    star_color, chroma, rainbow, saturation):
    """Add one tapered, glowing half-ray from (cx, cy) outward at angle_deg
    into an (H,W,3) additive layer. The ray stays close to full brightness
    for most of its length and only tapers hard near the very tip (matching
    how dramatic diffraction-spike presets look, rather than a physically
    exact 1/r falloff that would read as barely visible)."""
    if length_px < 1.0 or peak <= 0:
        return
    h, w, _ = layer.shape
    pad = thickness_px + 1.0
    x0 = int(max(0, np.floor(cx - length_px - pad)))
    x1 = int(min(w, np.ceil(cx + length_px + pad)))
    y0 = int(max(0, np.floor(cy - length_px - pad)))
    y1 = int(min(h, np.ceil(cy + length_px + pad)))
    if x1 <= x0 or y1 <= y0:
        return

    yy, xx = np.mgrid[y0:y1, x0:x1]
    dx = xx - cx
    dy = yy - cy
    theta = np.radians(angle_deg)
    dir_x, dir_y = np.cos(theta), np.sin(theta)
    along = dx * dir_x + dy * dir_y
    perp = np.abs(-dx * dir_y + dy * dir_x)

    t = np.clip(along / max(length_px, 1e-6), 0.0, 1.0)
    # Rays taper slightly (thinner toward the tip than at the star's core).
    # The 0.3 floor used to be large enough to visibly override a genuinely
    # thin thickness_px at low preview scale - the same class of preview/
    # Process mismatch as the outer floor already removed from
    # render_spike_layer. Kept tiny here only to avoid a division by ~0.
    local_thickness = thickness_px * (1.0 - 0.35 * t)
    perp_falloff = np.exp(-(perp ** 2) / (2.0 * np.maximum(local_thickness, 0.02) ** 2))
    # Along the ray: a soft bulge right at the star, a long near-full-
    # brightness run, then a fade only in the last stretch toward the tip.
    along_falloff = np.where(
        along < 0,
        np.exp(-(along ** 2) / (2.0 * (thickness_px * 1.5) ** 2)),
        (1.0 - t) ** 0.55,
    )
    mask = along <= length_px
    base = _soft_knee(peak * perp_falloff * along_falloff * mask)

    r_mult, g_mult, b_mult = _spike_color_mult(t, star_color, chroma, rainbow, saturation)
    layer[y0:y1, x0:x1, 0] = np.maximum(layer[y0:y1, x0:x1, 0], base * r_mult)
    layer[y0:y1, x0:x1, 1] = np.maximum(layer[y0:y1, x0:x1, 1], base * g_mult)
    layer[y0:y1, x0:x1, 2] = np.maximum(layer[y0:y1, x0:x1, 2], base * b_mult)


def _add_soft_flare(layer, cx, cy, radius_px, peak, tail_len_px=0.0):
    """A large, very soft circular glow around the star in every direction
    (not just along the rays) - mimics sensor/optics bloom around bright
    stars. With tail_len_px > 0 a power-law tail (equal to the gaussian at
    2 sigma, so no seam) extends the glow out to that radius; 0 keeps the
    original gaussian-only glow bit for bit."""
    if radius_px < 1.0 or peak <= 0:
        return
    h, w, _ = layer.shape
    sigma = radius_px * 0.5
    # The old box only extended to radius_px+1 (~2 sigma), where the
    # Gaussian is still at ~14% of its peak - the hard edge of that square
    # bounding box then showed up as a visible square around the glow,
    # worse the bigger the star. 3 sigma decays to ~1%, small enough that
    # clipping it there reads as a clean circular falloff instead.
    pad = sigma * 3.0 + 1.0
    if tail_len_px > 0:
        pad = max(pad, tail_len_px + 1.0)
    x0 = int(max(0, np.floor(cx - pad)))
    x1 = int(min(w, np.ceil(cx + pad)))
    y0 = int(max(0, np.floor(cy - pad)))
    y1 = int(min(h, np.ceil(cy + pad)))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    falloff = np.exp(-(r ** 2) / (2.0 * sigma ** 2))
    contrib = peak * falloff
    if tail_len_px > 0:
        tail = peak * (1.0 + (r / sigma) ** 2) ** -1.25
        t = np.clip((r - 0.6 * tail_len_px) / (0.4 * tail_len_px), 0.0, 1.0)
        tail = tail * (1.0 - t * t * (3.0 - 2.0 * t))
        contrib = np.maximum(contrib, tail)
    layer[y0:y1, x0:x1, :] = np.maximum(layer[y0:y1, x0:x1, :], contrib[..., None])


def ring_width_for_radius(ring_radius_px, fwhm_px):
    """Gaussian width (sigma) of the ring flare, given its own radius. A real
    reference photo shows no separate ring shape at all - the halo around a
    star is one smooth, continuous gradient - so the width scales with the
    ring's OWN radius (a broad fraction of it) rather than a small fixed
    fraction of the star's fwhm; that turns what used to render as a crisp
    thin circle into a soft brightness bump that blends into the core and
    soft flare instead of reading as a separate ring."""
    return max(0.8, ring_radius_px * 0.55, fwhm_px * 0.15)


def _add_ring_flare(layer, cx, cy, ring_radius_px, ring_width_px, peak):
    """A soft brightening around the star at roughly this radius, blended
    into the surrounding glow rather than a crisp separate ring - see
    ring_width_for_radius for why the width scales the way it does."""
    if ring_radius_px < 1.0 or peak <= 0:
        return
    h, w, _ = layer.shape
    ring_width_px = max(ring_width_px, 0.5)
    # Same reasoning as _add_soft_flare's padding: the ring's own falloff
    # has a sigma of ring_width_px, so the old +1px pad left the Gaussian
    # only barely decayed at the box edge - visible as a faint square
    # halo around the ring on a big/bright-enough star.
    pad = ring_width_px * 3.0 + 1.0
    x0 = int(max(0, np.floor(cx - ring_radius_px - pad)))
    x1 = int(min(w, np.ceil(cx + ring_radius_px + pad)))
    y0 = int(max(0, np.floor(cy - ring_radius_px - pad)))
    y1 = int(min(h, np.ceil(cy + ring_radius_px + pad)))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    d = r - ring_radius_px
    falloff = np.exp(-(d ** 2) / (2.0 * ring_width_px ** 2))
    contrib = peak * falloff
    layer[y0:y1, x0:x1, :] = np.maximum(layer[y0:y1, x0:x1, :], contrib[..., None])


_ANCHOR_PARAM_KEYS = ("length", "intensity", "thickness", "soft_flare", "flare_tail",
                      "ring_flare", "chroma", "rainbow", "saturation")

# "Twinkle" look for a star below the Minimum diameter/Small anchor (see
# SPIKE_DEFAULTS["twinkle"]): deliberately weaker than any real anchor's own
# length/intensity (Small is length=2.0/intensity=40) so it reads as a hint,
# not a fully-rendered small star - just the bare rays, no flare/colour extras.
TWINKLE_LENGTH_MULT = 2.5        # x star diameter - long enough to clear the
                                  # star's own core (otherwise it's invisible,
                                  # swallowed by the core's own bright disc)
TWINKLE_INTENSITY_SCALE = 1.0    # intensity = twinkle slider (0-100) * this
TWINKLE_THICKNESS = 0.5


def _smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _interp_anchor_params(anchors_sorted, fwhm, keys=None):
    """Blend the size-dependent spike parameters (`keys`, the classic
    _ANCHOR_PARAM_KEYS by default; a missing key reads as 0) for a star of diameter
    `fwhm`, from `anchors_sorted` (2 or more size-anchor dicts - 3 for the
    Small/Medium/Large per-size tabs, 2 synthetic ones for Uniform mode's
    single slider set - sorted by their own "diam", so the user is free to
    type Small > Medium in the UI without the interpolation breaking).
    Diameter space is logarithmic -
    star sizes in a typical field cluster heavily near the small end, so
    linear spacing would put nearly every star right on top of the first
    anchor and make "Large" almost unreachable - and the blend itself eases
    in/out (smoothstep) rather than moving linearly, so two stars a pixel
    apart in size never show a visible kink at an anchor. Flat below the
    smallest anchor and above the largest: no extrapolation past what the
    user actually dialled in for that end of the range."""
    keys = _ANCHOR_PARAM_KEYS if keys is None else keys
    lo, hi = anchors_sorted[0], anchors_sorted[-1]
    if fwhm <= lo["diam"]:
        return {k: lo.get(k, 0.0) for k in keys}
    if fwhm >= hi["diam"]:
        return {k: hi.get(k, 0.0) for k in keys}
    for a, b in zip(anchors_sorted, anchors_sorted[1:]):
        if a["diam"] <= fwhm <= b["diam"]:
            span = np.log(max(b["diam"], 1e-6)) - np.log(max(a["diam"], 1e-6))
            t = 0.5 if span <= 1e-9 else (
                (np.log(fwhm) - np.log(max(a["diam"], 1e-6))) / span)
            t = _smoothstep(t)
            return {k: a.get(k, 0.0) + (b.get(k, 0.0) - a.get(k, 0.0)) * t for k in keys}
    return {k: hi.get(k, 0.0) for k in keys}  # unreachable if sorted


def _star_jitter_pair(x, y):
    """Deterministic pseudo-random (-1..1, -1..1) pair seeded by a star's
    own position (a cheap integer hash, not np.random - stable across
    Python versions/processes and doesn't need a RandomState object per
    star). The same star always jitters the same way across re-renders,
    zoom levels and Fit/Process, but neighbouring stars don't move in
    lockstep - used by the "Natural variation" control to break up the
    stamped/CGI look of many identical-size stars."""
    h = (int(x * 97) * 374761393 + int(y * 97) * 668265263) & 0xffffffff
    h = (h ^ (h >> 13)) * 1274126177 & 0xffffffff
    h ^= h >> 16
    a = (h & 0xffff) / 65535.0 * 2.0 - 1.0
    b = ((h >> 16) & 0xffff) / 65535.0 * 2.0 - 1.0
    return a, b


def render_spike_layer(out_shape, view_x0, view_y0, view_w, view_h, stars, cfg):
    """Render an additive (H,W,3) glow layer - spikes, soft flare and ring
    flare combined - for a [view_x0, view_y0, view_w, view_h] window of the
    full-resolution image, scaled to out_shape=(out_h, out_w). Used
    identically for the fit raster, a hi-res crop, and the final full-
    resolution render, so the effect has the same real-world size
    regardless of zoom. stars: list of (xpos, ypos, fwhm, amplitude, color,
    forced, override) in full-resolution pixels - color is the star's own
    normalized (r,g,b); forced=True bypasses the smallest anchor's diameter
    cutoff (used for stars the user explicitly turned on with Ctrl+Click
    even though they're smaller than that anchor); override, if not None,
    is a dict of the 8 _ANCHOR_PARAM_KEYS set by Shift+Click-editing that
    one star individually (see App._spike_star_overrides) - used exactly
    as given instead of interpolating from cfg's anchors, and (like forced)
    bypasses the diameter cutoff, since dialling in a custom look for a
    star is itself a clear signal it should have a spike.

    cfg is a dict (see App._spike_config): "anchors" is the size-anchor
    dicts (each with "diam" plus the 8 keys in _ANCHOR_PARAM_KEYS) that get
    interpolated per star by _interp_anchor_params; "rays", "rotation",
    "hue" and "sharpness" (0-100, default 100 = untouched - softens the
    whole effect for long focal lengths/average seeing) apply globally;
    "variation" (0-100) drives the per-star length/rotation jitter."""
    out_h, out_w = out_shape
    layer = np.zeros((out_h, out_w, 3), dtype=np.float32)
    if not stars or view_w <= 0:
        return layer

    anchors_sorted = sorted(cfg["anchors"], key=lambda a: a["diam"])
    min_diameter = anchors_sorted[0]["diam"]
    twinkle = max(0.0, min(100.0, cfg.get("twinkle", 0.0)))
    has_overrides = any(ov is not None for (*_rest, ov) in stars)
    if (not has_overrides and twinkle <= 0 and
            max(a["intensity"] for a in anchors_sorted) <= 0 and
            max(a["soft_flare"] for a in anchors_sorted) <= 0 and
            max(a["ring_flare"] for a in anchors_sorted) <= 0):
        return layer

    num_rays = cfg["rays"]
    rotation_deg = cfg["rotation"]
    hue = cfg["hue"]
    sharpness = cfg.get("sharpness", 100.0)
    jitter_amt = max(0.0, min(100.0, cfg.get("variation", 0.0))) / 100.0

    scale = out_w / float(view_w)
    max_amp = max((a for (_, _, _, a, _c, _f, _o) in stars), default=1.0) or 1.0

    for (x, y, fwhm, amp, color, forced, override) in stars:
        if override is not None:
            p = override
        elif fwhm < min_diameter and not forced:
            if twinkle <= 0:
                continue
            # A tiny fixed hint instead of nothing - see TWINKLE_* above.
            p = {"length": TWINKLE_LENGTH_MULT, "intensity": twinkle * TWINKLE_INTENSITY_SCALE,
                 "thickness": TWINKLE_THICKNESS, "soft_flare": 0.0, "flare_tail": 0.0,
                 "ring_flare": 0.0, "chroma": 0.0, "rainbow": 0.0, "saturation": 100.0}
        else:
            # Forced stars smaller than the smallest anchor use that
            # anchor's look exactly (clamped), never an extrapolation past
            # it - only the actual ray/flare geometry below still scales
            # with the star's real (smaller) fwhm, same as any other star.
            p = _interp_anchor_params(anchors_sorted, max(fwhm, min_diameter))

        margin = fwhm * max(p["length"], 6.0) + fwhm
        if not (view_x0 - margin <= x <= view_x0 + view_w + margin and
                view_y0 - margin <= y <= view_y0 + view_h + margin):
            continue
        cx = (x - view_x0) * scale
        cy = (y - view_y0) * scale
        star_color = _rotate_hue(color, hue)
        # Brightness follows the star's own amplitude, but relative to the
        # single brightest star in frame every other star would be crushed
        # near zero - a high floor keeps any qualifying star's effect
        # clearly visible, only the very faintest ones are noticeably dimmer.
        rel_amp = 0.55 + 0.45 * min(1.0, max(0.0, amp / max_amp))

        jx, jr = _star_jitter_pair(x, y)
        length_jitter = 1.0 + jx * jitter_amt * 0.12  # up to +-12% length
        rot_jitter_deg = jr * jitter_amt * 4.0          # up to +-4 degrees
        angles = [rotation_deg + rot_jitter_deg + i * (360.0 / num_rays)
                  for i in range(num_rays)]

        # Computed unconditionally (not just when intensity>0) because
        # soft_flare/ring_flare below both reference it too, to keep their
        # own size in proportion to however long the rays actually render -
        # see the notes at each of those.
        ray_len_px = fwhm * p["length"] * length_jitter * scale

        if p["intensity"] > 0:
            if ray_len_px >= 1.5:
                # No artificial minimum here: a 0.6px floor used to make
                # thin spikes look reassuringly thick in the heavily
                # downsampled Fit preview, but that same floor doesn't
                # apply at full resolution (scale=1) during Process, so the
                # saved result came out much thinner than what the preview
                # promised. Keeping this proportional to `scale` everywhere
                # is what makes Fit, 100% zoom and the final Process match.
                th_px = max(0.05, p["thickness"] * scale)
                peak = (p["intensity"] / 100.0) * rel_amp
                for ang in angles:
                    _add_spike_ray(layer, cx, cy, ang, ray_len_px, th_px, peak,
                                    star_color, p["chroma"], p["rainbow"], p["saturation"])

        if p["soft_flare"] > 0:
            # A real stellar halo/bloom (scattered light, sensor blooming)
            # is broader than the tight diffraction ring below and can
            # bleed a little past the spikes' own tips, so this cap is
            # generous rather than tight - it only kicks in for a
            # dramatically short Length, not a normal one.
            flare_radius_px = min(fwhm * 4.0 * scale,
                                   max(ray_len_px * 1.2, fwhm * 2.0 * scale))
            if flare_radius_px >= 1.0:
                flare_peak = (p["soft_flare"] / 100.0) * rel_amp * 0.8
                _add_soft_flare(layer, cx, cy, flare_radius_px, flare_peak,
                                p.get("flare_tail", 0.0) * fwhm * scale)

        if p["ring_flare"] > 0:
            # A real diffraction ring comes from the aperture itself (a
            # different mechanism than the support-vane spikes) and sits
            # close to the star - on the order of its own FWHM, not the
            # spike length. A radius fixed at fwhm alone looked fine next
            # to a long spike but read as a separate ring floating well
            # past a short one, so this caps it at a modest fraction of the
            # actual rendered ray length too - while never shrinking below
            # roughly the star's own size, since the ring exists even when
            # spikes are short or disabled.
            ring_radius_px = min(fwhm * 1.8 * scale,
                                  max(ray_len_px * 0.6, fwhm * 1.0 * scale))
            ring_width_px = ring_width_for_radius(ring_radius_px, fwhm * scale)
            if ring_radius_px >= 1.5:
                ring_peak = (p["ring_flare"] / 100.0) * rel_amp * 0.7
                _add_ring_flare(layer, cx, cy, ring_radius_px, ring_width_px, ring_peak)

                # A real Airy pattern isn't one ring - successive bright
                # rings sit at roughly 1.8x the radius of the one before
                # (spacing of the Bessel-function zeros that bound each
                # ring) and fade quickly, on the order of a quarter of the
                # previous ring's peak. A single, suspiciously clean circle
                # reads as synthetic; this second, fainter, wider one is
                # what makes it read as a real multi-ring diffraction
                # pattern instead - only drawn once the first ring is
                # already visible, and capped against the same rendered
                # ray length for the same reason as the first.
                ring2_radius_px = min(ring_radius_px * 1.8,
                                       max(ray_len_px * 0.9, fwhm * 1.4 * scale))
                if ring2_radius_px >= 1.5:
                    ring2_width_px = ring_width_px * 1.3
                    ring2_peak = ring_peak * 0.25
                    _add_ring_flare(layer, cx, cy, ring2_radius_px, ring2_width_px, ring2_peak)

    if sharpness < 100.0:
        # Expressed in full-res pixels then scaled, same convention as
        # length/thickness, so Fit, 100% zoom and Process all soften by the
        # same real amount rather than an amount that depends on zoom.
        blur_full_px = (100.0 - max(0.0, sharpness)) / 100.0 * 6.0
        blur_px = blur_full_px * scale
        if blur_px > 0.05:
            layer = _blur_layer_rgb(layer, blur_px)

    return np.clip(layer, 0.0, 1.0)


def apply_spikes(rgb, layer):
    """Screen-blend the additive (H,W,3) spike glow layer onto the image."""
    if layer is None:
        return rgb
    out = rgb + layer * (1.0 - rgb)
    return np.clip(out, 0.0, 1.0)


class SirilWorker:
    """Holds the connection to Siril and serializes all calls on a single thread."""

    def __init__(self):
        self.siril = s.SirilInterface()
        self.siril.connect()

    def cmd(self, *args):
        self.siril.cmd(*args)

    def log(self, msg):
        self.siril.log(msg)

    def get_wd(self):
        """Siril's current Home/working directory (the house-shaped icon)."""
        return os.path.normpath(self.siril.get_siril_wd())

    def get_shape(self):
        """(height, width) of the currently loaded image."""
        _channels, h, w = self.siril.get_image_shape()
        return h, w

    def is_image_loaded(self):
        """Whether Siril currently has a single image open - the script
        never issues its own 'load', so this must be true before anything
        else can work."""
        try:
            return bool(self.siril.is_image_loaded())
        except Exception:
            return False

    def get_active_filename(self):
        """Filename of the image currently open in Siril, for display only."""
        try:
            name = self.siril.get_image_filename()
            return name or "(unnamed)"
        except Exception:
            return "(unnamed)"

    def _findstar_raw(self, maxstars=2000):
        """One findstar + get_image_stars round-trip over whatever is
        currently selected in Siril (the whole image if no selection is
        active), returning plain (xpos, ypos, fwhm, amplitude) tuples in
        full-resolution pixels, xpos/ypos in Siril's top-down display
        convention. maxstars is hard-limited server-side to [100, 2000] -
        a value outside that range doesn't get clamped, it fails the whole
        findstar call (confirmed the hard way)."""
        self.cmd("findstar", f"-maxstars={maxstars}")
        stars = self.siril.get_image_stars()
        out = []
        if stars:
            for st in stars:
                xpos = _star_attr(st, "xpos", "x")
                ypos = _star_attr(st, "ypos", "y")
                fwhm_x = _star_attr(st, "fwhm_x", "fwhmx")
                fwhm_y = _star_attr(st, "fwhm_y", "fwhmy", default=fwhm_x)
                fwhm = (fwhm_x + fwhm_y) / 2.0 if (fwhm_x or fwhm_y) else 0.0
                amplitude = _star_attr(st, "amplitude", "A", default=1.0)
                if fwhm > 0:
                    out.append((xpos, ypos, fwhm, max(1e-6, amplitude)))
        self.clear_stars()
        return out

    def get_stars(self):
        """Detected stars of the currently loaded image as a plain list of
        (xpos, ypos, fwhm, amplitude) tuples in full-resolution pixels.

        maxstars is hard-limited by Siril itself to 2000 PER findstar CALL -
        confirmed on a real 6248x4176 Milky Way field that this is nowhere
        near enough: an independent pixel-level count found a whole region
        of the frame with thousands of plausible stars and zero of Siril's
        2000 landing in it (that region wasn't sparse - a denser cluster
        elsewhere in the same frame most likely absorbed the whole global
        budget). A single findstar call over the whole image structurally
        cannot give even coverage on a field this rich, no matter how high
        maxstars could go. So on a large image this tiles the frame into a
        grid, selecting and running findstar on each tile separately (each
        tile gets its own up-to-2000 budget) via boxselect, then merges and
        deduplicates the results - real per-tile PSF fits, not a pixel-
        heuristic guess. Falls back to a single whole-image call (the
        original behavior) if boxselect turns out not to actually restrict
        findstar in the caller's Siril version - verified by checking
        whether the first tile's own results actually fall inside it."""
        h, w = self.get_shape()
        target = 1800  # px per tile side - keeps each tile's real star
        # count comfortably under the 2000-per-call cap even on a very rich
        # field, without needing dozens of slow Siril round-trips.
        n_cols = max(1, round(w / target))
        n_rows = max(1, round(h / target))
        if n_cols * n_rows <= 1:
            # Small/typical image - behave exactly as before, no selection
            # juggling needed.
            return self._findstar_raw()

        tile_w = -(-w // n_cols)  # ceil
        tile_h = -(-h // n_rows)
        all_stars = []
        tiling_ok = True
        for row in range(n_rows):
            for col in range(n_cols):
                tx, ty = col * tile_w, row * tile_h
                tw, th = min(tile_w, w - tx), min(tile_h, h - ty)
                if tw <= 0 or th <= 0:
                    continue
                try:
                    self.cmd("boxselect", str(tx), str(ty), str(tw), str(th))
                    tile_stars = self._findstar_raw()
                except Exception as e:
                    self.log(f"frankSpikes: tiled findstar failed on tile "
                              f"({tx},{ty},{tw}x{th}): {e} - falling back to "
                              f"a single whole-image findstar call")
                    tiling_ok = False
                    break
                if row == 0 and col == 0 and tile_stars:
                    # Sanity check: if boxselect doesn't actually restrict
                    # findstar in this Siril version, the "tile" results
                    # would just be the whole image's stars again, mostly
                    # landing outside this first (small) tile's bounds.
                    margin = 5
                    inside = sum(1 for (x, y, *_r) in tile_stars
                                 if tx - margin <= x <= tx + tw + margin
                                 and ty - margin <= y <= ty + th + margin)
                    if inside / len(tile_stars) < 0.5:
                        self.log(f"frankSpikes: boxselect doesn't appear to "
                                  f"restrict findstar in this Siril version "
                                  f"({inside}/{len(tile_stars)} results actually "
                                  f"inside the first tile) - falling back to a "
                                  f"single whole-image findstar call")
                        tiling_ok = False
                        break
                all_stars.extend(tile_stars)
            if not tiling_ok:
                break

        try:
            self.cmd("boxselect", "-clear")
        except Exception:
            pass

        if not tiling_ok:
            return self._findstar_raw()

        deduped = _dedupe_stars(all_stars)
        self.log(f"frankSpikes: tiled findstar ({n_cols}x{n_rows} grid) found "
                  f"{len(all_stars)} raw detections, {len(deduped)} after "
                  f"deduplicating tile-boundary overlaps")
        return deduped

    def clear_stars(self):
        """Clears the star markers findstar leaves drawn on the image."""
        try:
            self.cmd("clearstar")
        except Exception:
            pass

    def fetch_full(self):
        """Full-resolution pixel data of the image currently active in
        Siril, as (H,W,3) float [0,1]. Fetched once (on Reload) and cached
        by the caller: the script never issues its own 'load', so this is
        the only place it ever reads pixels from Siril before the final
        Process/save."""
        data = self.siril.get_image_pixeldata(preview=False)
        return to_hwc(to_float01(data))

    def push_rgb(self, rgb_float01):
        """Overwrite the currently active image's pixels in Siril with the
        processed result - nothing is saved to disk here. Siril itself owns
        save/undo for that image from this point on (Ctrl+Z, File > Save),
        exactly like any other in-place Siril processing step - but only if
        an undo checkpoint of the pre-frankSpikes pixels is saved first,
        which set_image_pixeldata does not do on its own.

        rgb_float01 is expected in this script's own display orientation
        (row 0 = top, matching Siril's on-screen view) - flipped back here
        to Siril's native bottom-up row order before writing, the opposite
        of the flip fetch_full()'s caller applies on read."""
        rgb_float01 = rgb_float01[::-1, :, :]
        chw = np.transpose(np.clip(rgb_float01, 0, 1), (2, 0, 1)).astype(np.float32)
        with self.siril.image_lock():
            try:
                self.siril.undo_save_state("frankSpikes")
            except Exception:
                pass
            self.siril.set_image_pixeldata(chw)


class App:
    def __init__(self, root, worker: SirilWorker):
        self.root = root
        self.worker = worker
        self.queue = queue.Queue()

        self.workdir = tk.StringVar(value=self.worker.get_wd())
        self.active_filename = tk.StringVar(value="(none)")
        self.status = tk.StringVar(value="Reading the active image from Siril...")

        self.exposure = tk.DoubleVar(value=0)
        self.contrast = tk.DoubleVar(value=0)
        self.blacks = tk.DoubleVar(value=0)
        self.highlights = tk.DoubleVar(value=0)
        self.clarity = tk.DoubleVar(value=0)
        self.vibrance = tk.DoubleVar(value=0)
        self.saturation = tk.DoubleVar(value=0)
        self.temperature = tk.DoubleVar(value=0)
        self.tint = tk.DoubleVar(value=0)
        self.exposure_label = tk.StringVar(value="0")
        self.contrast_label = tk.StringVar(value="0")
        self.blacks_label = tk.StringVar(value="0")
        self.highlights_label = tk.StringVar(value="0")
        self.clarity_label = tk.StringVar(value="0")
        self.vibrance_label = tk.StringVar(value="0")
        self.saturation_label = tk.StringVar(value="0")
        self.temperature_label = tk.StringVar(value="0")
        self.tint_label = tk.StringVar(value="0")

        d = SPIKE_DEFAULTS
        self.spike_enabled = tk.BooleanVar(value=d["enabled"])
        self.spike_rays = tk.IntVar(value=d["rays"])
        self.spike_rotation = tk.DoubleVar(value=d["rotation"])
        self.spike_hue = tk.DoubleVar(value=d["hue"])
        self.spike_sharpness = tk.DoubleVar(value=d["sharpness"])
        self.spike_variation = tk.DoubleVar(value=d["variation"])
        self.spike_twinkle = tk.DoubleVar(value=d["twinkle"])
        self.spike_rotation_label = tk.StringVar(value=f"{d['rotation']:.0f}")
        self.spike_hue_label = tk.StringVar(value=f"{d['hue']:.0f}")
        self.spike_sharpness_label = tk.StringVar(value=f"{d['sharpness']:.0f}")
        self.spike_variation_label = tk.StringVar(value=f"{d['variation']:.0f}")
        self.spike_twinkle_label = tk.StringVar(value=f"{d['twinkle']:.0f}")

        # One dict per size anchor (Small/Medium/Large), each holding a
        # tk.DoubleVar + tk.StringVar label per key in SPIKE_ANCHOR_PARAM_DEFS
        # (built in a loop, not ~30 hand-written blocks - see that table's
        # comment). Order matches SPIKE_DEFAULTS["anchors"]/SPIKE_ANCHOR_TAB_LABELS,
        # but render_spike_layer always re-sorts by the "diam" Var's current
        # value, so the user is free to drag Small past Medium without harm.
        self.spike_anchors = []
        for anchor_defaults in d["anchors"]:
            av = {}
            for key, _label, _lo, _hi, _step, fmt in SPIKE_ANCHOR_PARAM_DEFS:
                val = anchor_defaults[key]
                av[key] = tk.DoubleVar(value=val)
                av[key + "_label"] = tk.StringVar(value=fmt.format(val))
            self.spike_anchors.append(av)

        # "Uniform" mode (shown to the user as "Simple"): one flat slider
        # set (no size tabs) - see SPIKE_UNIFORM_DEFAULTS and
        # _uniform_anchors(). "per_size" is the long-standing tabbed
        # Small/Medium/Large behavior. Uniform/Simple is the default - the
        # easier control for most users; Per size is the opt-in advanced one.
        self.spike_mode = tk.StringVar(value="uniform")
        self._last_spike_mode = "uniform"  # tracks the previous mode, so a
        # switch INTO "per_size" FROM "uniform" is only seeded once (see
        # _on_spike_mode_change) rather than clobbering hand-tuned per-size
        # anchors on every later toggle back to "Per size".
        ud = SPIKE_UNIFORM_DEFAULTS
        self.spike_uniform_min_diam = tk.DoubleVar(value=ud["min_diam"])
        self.spike_uniform_min_diam_label = tk.StringVar(value=f"{ud['min_diam']:.0f}")
        self.spike_uniform = {}
        for key, _label, _lo, _hi, _step, fmt in SPIKE_ANCHOR_PARAM_DEFS:
            if key == "diam":
                continue
            val = ud[key]
            self.spike_uniform[key] = tk.DoubleVar(value=val)
            self.spike_uniform[key + "_label"] = tk.StringVar(value=fmt.format(val))

        # Detected stars as (xpos, ypos, fwhm, amplitude, color), full-res px;
        # color is the star's own normalized (r,g,b), see sample_star_color().
        self._stars = []
        self._spike_disabled = set()   # indices into self._stars excluded by the user
        self._spike_forced = set()     # indices into self._stars forced on past min diameter
        # user-added (manual_id, xpos, ypos, fwhm, amplitude, color) - a
        # stable manual_id (not list position) identifies each one, since
        # Ctrl+Click deletion shifts list indices but must not silently
        # reassign an unrelated star's per-star override (self._spike_star_overrides
        # below) to whatever star happens to end up at the same index.
        self._spike_manual = []
        self._manual_id_counter = 0

        # Per-star manual overrides: {("auto", i) | ("manual", manual_id):
        # {each of _ANCHOR_PARAM_KEYS: value}} - set by dragging a slider
        # while that star is selected (Shift+Click), see _on_star_slider_change.
        # A star with an entry here ignores the Small/Medium/Large or Simple
        # size-based look entirely and renders with exactly these 8 values
        # (see render_spike_layer). Cleared on Reload and by "Reset manual
        # edits", same lifecycle as _spike_disabled/_spike_forced/_spike_manual.
        self._spike_star_overrides = {}
        self._selected_star_key = None  # the ("auto"|"manual", id) currently
        # selected for editing, or None - drives which slider panel shows
        # (see _update_spike_mode_ui) and the dashed-circle highlight.

        d_star = SPIKE_UNIFORM_DEFAULTS  # only used to seed the star-panel Vars' initial shape
        self.spike_star = {}
        for key, _label, _lo, _hi, _step, fmt in SPIKE_ANCHOR_PARAM_DEFS:
            if key == "diam":
                continue
            val = d_star[key]
            self.spike_star[key] = tk.DoubleVar(value=val)
            self.spike_star[key + "_label"] = tk.StringVar(value=fmt.format(val))
        self.spike_star_info = tk.StringVar(value="")
        self._spike_layer_key = None  # cache key: skip re-rendering the spike layer when its inputs didn't change

        self._pristine_full = None  # (H,W,3) float [0,1], fetched once from Siril
        self._src_preview_rgb = None  # raw (H,W,3) preview, before adjustments
        self.loaded = False

        self._preview_rgb = None  # (H,W,3) float [0,1] after adjustments, low-res
        self._base_preview_rgb = None  # same, before the spike layer is composited on top
        self._spike_layer_preview = None  # cached (ph,pw,3) spike glow layer for the Fit preview
        self._spike_preview_after_id = None
        self._spike_preview_gen = 0
        self._show_original = False  # True while Space is held over the preview
        self._tkimg = None
        self._nav_tkimg = None
        self._nav_geom = None  # (ox, oy, thumb_w, thumb_h) of the last-drawn thumbnail, for click mapping
        self.zoom_mode = "fit"  # "fit" or "manual"
        self.zoom_pct = 1.0
        self._display_zoom_pct = 1.0  # zoom_pct is relative to the fit preview raster; this is relative to the real image, for the label
        self.zoom_label = tk.StringVar(value="100%")
        # Preview-only display mode: shows just the additive spike layer on
        # black instead of blended onto the real photo, so its own shape/
        # colour/rings can be judged without the image underneath. Never
        # touches Process/import in Siril - see _on_hide_background_toggle.
        self.hide_background = tk.BooleanVar(value=False)

        self.full_shape = None  # (h, w) of the original image
        self.view_cx = 0.5
        self.view_cy = 0.5
        self._hires_rgb = None
        self._hires_wh = None
        self._hires_gen = 0
        self._hires_after_id = None
        self._hires_inflight = False  # a hi-res fetch thread is currently running
        self._spike_preview_inflight = False  # a spike-preview render thread is currently running
        self._siril_busy = False
        self._busy_count = 0  # how many background renders are in flight
        self._drag_last = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_queue)
        self.root.after(150, self._on_reload)

    def _on_close(self):
        """Safety net: get_stars() already clears the star overlay right
        after detection, but make sure closing the window never leaves
        every star selected on the image in Siril."""
        try:
            self.worker.clear_stars()
        except Exception:
            pass
        self.root.destroy()

    def _show_help(self):
        """A small popup with this script's own top-of-file docstring -
        one source of truth, no separate help text to keep in sync."""
        win = tk.Toplevel(self.root)
        win.title(f"frankSpikes {APP_VERSION} - Help")
        win.configure(bg=PALETTE["bg"])
        win.geometry("640x600")
        win.transient(self.root)

        frm = ttk.Frame(win)
        frm.pack(fill="both", expand=True, padx=10, pady=10)
        text = tk.Text(frm, wrap="word", background=PALETTE["input_bg"],
                        foreground=PALETTE["text"], insertbackground=PALETTE["text"],
                        relief="flat", padx=14, pady=14, font=FONT_BASE)
        scroll = ttk.Scrollbar(frm, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        text.insert("1.0", __doc__ or "(no help text available)")
        text.config(state="disabled")

        ttk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 10))

    # ---------- Busy indicator (progress bar) ----------
    # A shared counter rather than a plain flag: Reload/Process, the hi-res
    # zoom fetch and the spike-layer recompute can all be in flight at
    # once (e.g. panning while a spike slider's debounced render is still
    # running), and the spinner should only actually stop once every one
    # of them has finished - not whichever happens to land last.
    def _busy_begin(self):
        self._busy_count += 1
        if self._busy_count == 1:
            self.progress.start(12)
            # "watch" is Tk's cross-platform busy-cursor name (the Windows
            # hourglass/spinning-circle equivalent) - set on the root so it
            # shows over every widget (sliders, canvas, buttons), not just
            # wherever the mouse happens to already be.
            self.root.config(cursor="watch")

    def _busy_end(self):
        self._busy_count = max(0, self._busy_count - 1)
        if self._busy_count == 0:
            self.progress.stop()
            self.root.config(cursor="")

    # ---------- UI ----------
    def _make_scrollable_frame(self, parent):
        """Wraps a Canvas + vertical Scrollbar around a plain Frame, so its
        content becomes scrollable whenever the window is resized shorter
        than what the sidebar actually needs - the scrollbar only appears
        when it's actually needed, not all the time. Returns (outer, inner):
        grid/pack `outer` into the layout, put actual content into `inner`
        exactly as if it were a plain Frame."""
        outer = ttk.Frame(parent)
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(outer, background=PALETTE["bg"], highlightthickness=0)
        vbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")

        inner = ttk.Frame(canvas)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _sync(_e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            if inner.winfo_reqheight() > canvas.winfo_height():
                vbar.grid(row=0, column=1, sticky="ns")
            else:
                vbar.grid_remove()

        inner.bind("<Configure>", _sync)
        canvas.bind("<Configure>", _sync)

        def _on_wheel(event):
            if inner.winfo_reqheight() <= canvas.winfo_height():
                return  # nothing to scroll - let the event pass through
            delta = event.delta if event.delta else (120 if event.num == 4 else -120)
            canvas.yview_scroll(int(-delta / 120), "units")

        canvas._cosmetics_wheel_handler = _on_wheel  # picked up by _bind_wheel_recursive
        canvas._cosmetics_inner = inner
        return outer, inner, canvas

    def _bind_wheel_recursive(self, canvas):
        """Mouse-wheel scrolling only fires on the exact widget under the
        cursor in Tk - with real controls (sliders, buttons, labels...)
        covering almost the entire scrollable area, binding only the
        canvas itself would mean the wheel does nothing anywhere useful.
        Binds every descendant of the canvas's embedded frame instead."""
        handler = canvas._cosmetics_wheel_handler

        def _bind(widget):
            widget.bind("<MouseWheel>", handler, add="+")
            widget.bind("<Button-4>", handler, add="+")
            widget.bind("<Button-5>", handler, add="+")
            for child in widget.winfo_children():
                _bind(child)

        _bind(canvas._cosmetics_inner)

    def _build_ui(self):
        P = PALETTE
        setup_style(self.root)
        pad = {"padx": 8, "pady": 5}

        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # ---- Header ----
        frm_header = ttk.Frame(self.root)
        frm_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        frm_header.grid_columnconfigure(0, weight=1)

        title_box = ttk.Frame(frm_header)
        title_box.grid(row=0, column=0, sticky="w")
        ttk.Label(title_box, text=f"frankSpikes {APP_VERSION}", style="Header.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="Light, tone and color adjustments, plus realistic "
                                   "diffraction spikes, via Siril",
                  style="SubHeader.TLabel").pack(anchor="w")

        ttk.Button(frm_header, text="Help", style="Toolbar.TButton",
                   command=self._show_help).grid(row=0, column=1, sticky="e", padx=(0, 8))

        badge = ttk.Label(frm_header, text="\U0001F4D8 by Frank Sferlazza", style="Badge.TLabel",
                           cursor="hand2")
        badge.grid(row=0, column=2, sticky="e")
        badge.bind("<Button-1>", lambda _e: webbrowser.open(FACEBOOK_URL))

        # ---- Body: parameters (left) + preview (right) ----
        frm_main = ttk.Frame(self.root)
        frm_main.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 6))
        frm_main.grid_rowconfigure(1, weight=1)
        frm_main.grid_columnconfigure(1, weight=1)

        ctrl_outer, frm_ctrl, self._ctrl_canvas = self._make_scrollable_frame(frm_main)
        ctrl_outer.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 8))

        frm_light = ttk.LabelFrame(frm_ctrl, text="Light & Tones")
        frm_light.pack(fill="x", pady=(0, 10))
        frm_light.grid_columnconfigure(0, minsize=230)
        self._add_slider(frm_light, 0, "Exposure", self.exposure, self.exposure_label, -100, 100, step=1)
        self._add_slider(frm_light, 2, "Contrast", self.contrast, self.contrast_label, -100, 100, step=1)
        self._add_slider(frm_light, 4, "Blacks / Sky Background",
                          self.blacks, self.blacks_label, -100, 100, step=1)
        self._add_slider(frm_light, 6, "Highlights / Whites",
                          self.highlights, self.highlights_label, -100, 100, step=1)
        self._add_slider(frm_light, 8, "Clarity (local contrast)",
                          self.clarity, self.clarity_label, -100, 100, step=1)

        frm_color = ttk.LabelFrame(frm_ctrl, text="Color & Hue")
        frm_color.pack(fill="x")
        frm_color.grid_columnconfigure(0, minsize=230)
        self._add_slider(frm_color, 0, "Vibrance",
                          self.vibrance, self.vibrance_label, -100, 100, step=1)
        self._add_slider(frm_color, 2, "Saturation",
                          self.saturation, self.saturation_label, -100, 100, step=1)
        self._add_slider(frm_color, 4, "Temperature (cool / warm)",
                          self.temperature, self.temperature_label, -50, 50, step=0.5)
        self._add_slider(frm_color, 6, "Tint (green / magenta)",
                          self.tint, self.tint_label, -50, 50, step=0.5)

        self.btn_process = ttk.Button(frm_ctrl, text="Process and import in Siril",
                                       style="Accent.TButton",
                                       command=self._on_process, state="disabled")
        self.btn_process.pack(fill="x", pady=(18, 0))

        # ---- Navigator: thumbnail + draggable viewport rectangle ----
        frm_nav = ttk.LabelFrame(frm_ctrl, text="Navigator")
        frm_nav.pack(fill="x", pady=(14, 0))
        self.nav_canvas = tk.Canvas(frm_nav, background=P["trough"], highlightthickness=0,
                                     width=NAV_MAX_W, height=NAV_MAX_H)
        self.nav_canvas.pack(padx=10, pady=10)
        self.nav_canvas.bind("<ButtonPress-1>", self._on_nav_click)
        self.nav_canvas.bind("<B1-Motion>", self._on_nav_click)

        # ---- Zoom "pill" toolbar ----
        frm_toolbar = ttk.Frame(frm_main, style="Toolbar.TFrame")
        frm_toolbar.grid(row=0, column=1, sticky="ew", pady=(0, 6))
        for txt, cmd in (("−", self._zoom_out), ("Fit", self._zoom_fit),
                          ("100%", self._zoom_1to1), ("+", self._zoom_in)):
            ttk.Button(frm_toolbar, text=txt, style="Toolbar.TButton", width=5,
                       command=cmd).pack(side="left", padx=(0, 1), pady=6)
        ttk.Label(frm_toolbar, textvariable=self.zoom_label, style="ZoomPct.TLabel",
                  width=6, anchor="center").pack(side="left", padx=(10, 0))
        ttk.Checkbutton(frm_toolbar, text="Hide background (spikes only)",
                         variable=self.hide_background,
                         command=self._on_hide_background_toggle).pack(side="left", padx=(16, 0))
        ttk.Label(frm_toolbar, text="Fit: fast low-res preview — 100%/+/-: real full-resolution"
                                     " crop (drag, scroll wheel, or the scrollbars to pan)",
                  style="CardMuted.TLabel").pack(side="left", padx=(16, 0))

        # highlightthickness=0: with it >0, winfo_width()/height() include
        # the border in their count while canvas item coordinates and
        # mouse events don't - a small but real (2 * thickness) source of
        # drift between the click math and what's actually drawn.
        self.preview_canvas = tk.Canvas(frm_main, background=P["trough"], highlightthickness=0,
                                         width=600, height=500)
        self.preview_canvas.grid(row=1, column=1, sticky="nsew")
        self.preview_canvas.create_text(
            16, 16, anchor="nw", tags="placeholder", fill=P["muted"],
            text="(no preview yet)")
        self.preview_canvas.bind("<Configure>", self._on_canvas_resize)
        self.preview_canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.preview_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.preview_canvas.bind("<MouseWheel>", self._on_canvas_wheel)  # Windows/Mac
        self.preview_canvas.bind("<Button-4>", self._on_canvas_wheel)  # Linux, up
        self.preview_canvas.bind("<Button-5>", self._on_canvas_wheel)  # Linux, down
        # Bound on the canvas itself (which grabs keyboard focus on hover)
        # rather than the whole window, so holding Space doesn't also
        # invoke whatever Checkbutton/Radiobutton happens to have focus.
        self.preview_canvas.bind("<Enter>", lambda _e: self.preview_canvas.focus_set())
        self.preview_canvas.bind("<KeyPress-space>", self._on_space_press)
        self.preview_canvas.bind("<KeyRelease-space>", self._on_space_release)

        self.vbar = ttk.Scrollbar(frm_main, orient="vertical", command=self._on_vscroll)
        self.vbar.grid(row=1, column=2, sticky="ns")
        self.hbar = ttk.Scrollbar(frm_main, orient="horizontal", command=self._on_hscroll)
        self.hbar.grid(row=2, column=1, sticky="ew")

        # ---- Diffraction spikes panel: right of the image, not stacked
        # under A)/B) on the left, so the window doesn't grow very tall. ----
        frm_spikes_outer = ttk.LabelFrame(frm_main, text="✨ Diffraction Spikes")
        frm_spikes_outer.grid(row=0, column=3, rowspan=3, sticky="nsew", padx=(8, 0))
        frm_spikes_outer.grid_rowconfigure(0, weight=1)
        frm_spikes_outer.grid_columnconfigure(0, weight=1)
        spikes_scroll, frm_spikes, self._spikes_canvas = self._make_scrollable_frame(frm_spikes_outer)
        spikes_scroll.grid(row=0, column=0, sticky="nsew")
        frm_spikes.grid_columnconfigure(0, minsize=230)

        ttk.Checkbutton(frm_spikes, text="Enable spikes", variable=self.spike_enabled,
                         command=self._on_spike_slider).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 4))

        # ---- Mode: one flat slider set for every star (internal value
        # "uniform", shown to the user as "Simple") vs the tabbed
        # Small/Medium/Large controls below ("Per size"). Switching just
        # swaps which panel is shown - each keeps its own values. ----
        mode_box = ttk.Frame(frm_spikes, style="Card.TFrame")
        mode_box.grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(2, 2))
        ttk.Radiobutton(mode_box, text="Simple (one control for all stars)",
                         value="uniform", variable=self.spike_mode,
                         command=self._on_spike_mode_change).pack(anchor="w")
        ttk.Radiobutton(mode_box, text="Per size (separate Small/Medium/Large tabs)",
                         value="per_size", variable=self.spike_mode,
                         command=self._on_spike_mode_change).pack(anchor="w")

        ttk.Label(frm_spikes, text="Number of rays", style="Card.TLabel").grid(
            row=2, column=0, columnspan=3, sticky="w", padx=10, pady=(4, 0))
        rays_box = ttk.Frame(frm_spikes, style="Card.TFrame")
        rays_box.grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=(2, 0))
        ttk.Radiobutton(rays_box, text="4 (refractor / 2-vane spider)", value=4,
                         variable=self.spike_rays, command=self._on_spike_slider).pack(anchor="w")
        ttk.Radiobutton(rays_box, text="6 (3-vane spider, e.g. Newtonian)", value=6,
                         variable=self.spike_rays, command=self._on_spike_slider).pack(anchor="w")

        self._add_slider(frm_spikes, 4, "Rotation angle (0-90 deg)",
                          self.spike_rotation, self.spike_rotation_label, 0, 90,
                          step=1, on_change=self._on_spike_slider)
        self._add_slider(frm_spikes, 6, "Color hue (each spike keeps its star's colour)",
                          self.spike_hue, self.spike_hue_label, -180, 180,
                          step=5, on_change=self._on_spike_slider)
        self._add_slider(frm_spikes, 8, "Sharpness (lower = softer, for long focal lengths)",
                          self.spike_sharpness, self.spike_sharpness_label, 0, 100,
                          step=5, on_change=self._on_spike_slider)
        self._add_slider(frm_spikes, 10, "Natural variation (per-star jitter)",
                          self.spike_variation, self.spike_variation_label, 0, 100,
                          step=5, on_change=self._on_spike_slider)
        self._add_slider(frm_spikes, 12, "Twinkle (a tiny hint of spike below the minimum diameter)",
                          self.spike_twinkle, self.spike_twinkle_label, 0, 100,
                          step=5, on_change=self._on_spike_slider)

        # ---- Per-size-anchor look: a tab per anchor, each with the full
        # set of size-dependent controls, generated from SPIKE_ANCHOR_PARAM_DEFS
        # so this stays one loop instead of ~30 hand-written slider calls. ----
        self._spike_notebook = ttk.Notebook(frm_spikes)
        self._spike_notebook.grid(row=14, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 4))
        for tab_index, (tab_label, anchor_vars) in enumerate(
                zip(SPIKE_ANCHOR_TAB_LABELS, self.spike_anchors)):
            tab = ttk.Frame(self._spike_notebook, style="Card.TFrame")
            tab.grid_columnconfigure(0, minsize=200)
            self._spike_notebook.add(tab, text=tab_label)
            r = 0
            for key, label, _lo, _hi, step, _fmt in SPIKE_ANCHOR_PARAM_DEFS:
                lo, hi = spike_anchor_slider_range(tab_index, key)
                self._add_slider(tab, r, label, anchor_vars[key], anchor_vars[key + "_label"],
                                  lo, hi, step=step, on_change=self._on_spike_slider)
                r += 2

        # ---- Uniform look: the same 8 size-dependent controls as one tab
        # would have, plus the cutoff diameter, gridded in the same cell as
        # the notebook above - only one of the two is ever shown. ----
        self._spike_uniform_frame = ttk.Frame(frm_spikes, style="Card.TFrame")
        self._spike_uniform_frame.grid(row=14, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 4))
        self._spike_uniform_frame.grid_columnconfigure(0, minsize=200)
        u_lo, u_hi = SPIKE_ANCHOR_DIAM_RANGES[0]
        self._add_slider(self._spike_uniform_frame, 0, "Minimum star diameter (px)",
                          self.spike_uniform_min_diam, self.spike_uniform_min_diam_label,
                          u_lo, u_hi, step=1, on_change=self._on_spike_slider)
        r = 2
        for key, label, lo, hi, step, _fmt in SPIKE_ANCHOR_PARAM_DEFS:
            if key == "diam":
                continue
            self._add_slider(self._spike_uniform_frame, r, label, self.spike_uniform[key],
                              self.spike_uniform[key + "_label"], lo, hi, step=step,
                              on_change=self._on_spike_slider)
            r += 2

        # ---- Single-star editing: shown instead of the notebook/uniform
        # panel above whenever a star is Shift+Click-selected - same 8
        # sliders, but they read/write that one star's own override. ----
        self._spike_star_frame = ttk.Frame(frm_spikes, style="Card.TFrame")
        self._spike_star_frame.grid(row=14, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 4))
        self._spike_star_frame.grid_columnconfigure(0, minsize=200)
        ttk.Label(self._spike_star_frame, textvariable=self.spike_star_info,
                  style="Card.TLabel", justify="left", wraplength=210).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 4))
        r = 2
        for key, label, lo, hi, step, _fmt in SPIKE_ANCHOR_PARAM_DEFS:
            if key == "diam":
                continue
            self._add_slider(self._spike_star_frame, r, label, self.spike_star[key],
                              self.spike_star[key + "_label"], lo, hi, step=step,
                              on_change=self._on_star_slider_change)
            r += 2
        ttk.Button(self._spike_star_frame, text="Reset this star to its size-based look",
                   style="Warn.TButton", command=self._reset_selected_star_override).grid(
            row=r, column=0, columnspan=3, sticky="ew", padx=10, pady=(4, 2))
        ttk.Button(self._spike_star_frame, text="Deselect", style="Toolbar.TButton",
                   command=self._deselect_star).grid(
            row=r + 1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 4))

        self._spike_help_per_size = ("Each star's own diameter blends smoothly between the\n"
                       "Small/Medium/Large tabs above - stars below the Small\n"
                       "tab's diameter get no spike at all. Ctrl+Click a star in\n"
                       "the preview to remove/restore its spikes (or force one\n"
                       "below that diameter), or Ctrl+Click empty space to add\n"
                       "one. Judge Thickness at 100% zoom, not Fit - thin spikes\n"
                       "can vanish into a few pixels once downsampled.")
        self._spike_help_uniform = ("Every slider's effect grows smoothly with each star's\n"
                       "own size: essentially none right at the Minimum diameter,\n"
                       "the full dialled-in value from about 4x that diameter up.\n"
                       "Stars below the minimum get no spike at all. Ctrl+Click a\n"
                       "star in the preview to remove/restore its spikes (or force\n"
                       "one below that diameter), or Ctrl+Click empty space to add\n"
                       "one. Judge Thickness at 100% zoom, not Fit.")
        self._spike_help_star = ("These sliders set this one star's exact look, ignoring\n"
                       "the Small/Medium/Large or Simple size-based settings\n"
                       "entirely from now on. Shift+Click another star to switch,\n"
                       "or empty space / Deselect to stop editing a single star.")
        self._spike_help_label = ttk.Label(frm_spikes, style="CardMuted.TLabel", justify="left")
        self._spike_help_label.grid(
            row=15, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 2))
        ttk.Button(frm_spikes, text="Reset manual edits", style="Danger.TButton",
                   command=self._reset_spike_edits).grid(
            row=16, column=0, columnspan=3, sticky="ew", padx=10, pady=(2, 4))
        ttk.Button(frm_spikes, text="Defaults", style="Warn.TButton",
                   command=self._reset_spike_defaults).grid(
            row=17, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
        self._update_spike_mode_ui()

        # ---- Status bar ----
        frm_status = ttk.Frame(self.root, style="Card.TFrame")
        frm_status.grid(row=2, column=0, sticky="ew")
        frm_status.grid_columnconfigure(1, weight=1)

        ttk.Label(frm_status, textvariable=self.status, style="Status.TLabel").grid(
            row=0, column=0, sticky="w", padx=12, pady=8)
        self.progress = ttk.Progressbar(frm_status, mode="indeterminate")
        self.progress.grid(row=0, column=1, sticky="ew", padx=12, pady=8)
        ttk.Label(frm_status, text="Space Bar - Original view",
                  style="CardMuted.TLabel").grid(row=0, column=2, sticky="e", padx=12, pady=8)
        ttk.Label(frm_status, text=f"frankSpikes {APP_VERSION} — by Frank Sferlazza",
                  style="CardMuted.TLabel").grid(row=0, column=3, sticky="e", padx=12, pady=8)

        # Both sidebars are now built - fix each scrollable canvas's size
        # to its content's real natural size (a bare Canvas doesn't
        # auto-size to an embedded window the way a Frame would). Height
        # matters here too, not just width: leaving it at Tk's small
        # default would make main()'s window-sizing logic think the
        # sidebars need far less room than they do, and the window would
        # open already needing to scroll instead of only after the user
        # manually resizes it shorter. Also wires up wheel-scrolling
        # across every widget inside them.
        self.root.update_idletasks()
        for canvas in (self._ctrl_canvas, self._spikes_canvas):
            inner = canvas._cosmetics_inner
            canvas.configure(width=inner.winfo_reqwidth(), height=inner.winfo_reqheight())
            self._bind_wheel_recursive(canvas)

    def _add_slider(self, parent, row, label, var, label_var, lo, hi, step=1.0, on_change=None):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(
            row=row, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 0))
        cmd = on_change or self._on_tone_slider
        ttk.Scale(parent, from_=lo, to=hi, variable=var,
                  command=lambda _e: cmd()).grid(
            row=row + 1, column=0, sticky="ew", padx=(10, 4))
        ttk.Label(parent, textvariable=label_var, style="Card.TLabel", width=5).grid(
            row=row + 1, column=1, padx=(0, 2))

        def _bump(delta):
            new_val = round(min(hi, max(lo, var.get() + delta)), 4)
            var.set(new_val)
            cmd()

        spin = ttk.Frame(parent, style="Card.TFrame")
        spin.grid(row=row + 1, column=2, padx=(0, 10), sticky="ns")
        ttk.Button(spin, text="▲", style="Spin.TButton", width=2,
                   command=lambda: _bump(step)).pack(side="top", fill="x")
        ttk.Button(spin, text="▼", style="Spin.TButton", width=2,
                   command=lambda: _bump(-step)).pack(side="top", fill="x")

    # ---------- Reload from Siril (background thread) ----------
    def _on_reload(self):
        self.btn_process.config(state="disabled")
        self._busy_begin()
        self._siril_busy = True
        t = threading.Thread(target=self._reload_thread, daemon=True)
        t.start()

    def _reload_thread(self):
        try:
            self.worker.log(f"frankSpikes {APP_VERSION}")

            if not self.worker.is_image_loaded():
                self.queue.put(("error", "No image is currently open in Siril.\n\n"
                                          "Open the image you want to edit in Siril, "
                                          "then run this script again."))
                return

            filename = self.worker.get_active_filename()
            self.worker.log(f"active image={filename!r}")

            self.queue.put(("status", "Detecting stars for diffraction spikes..."))
            try:
                stars = self.worker.get_stars()
                if stars:
                    fwhms = sorted(s[2] for s in stars)
                    n = len(fwhms)
                    median_fwhm = fwhms[n // 2]
                    # Diagnostic for "many stars aren't getting spikes": the
                    # Minimum star diameter slider (default 20px) filters out
                    # any star whose own detected fwhm is below it - if most
                    # of this field's stars sit well under that, the cutoff
                    # itself, not detection, is why they're excluded. Logged
                    # unconditionally (not just on request) since this is
                    # exactly the number needed to tell the two apart, and
                    # it's cheap to compute.
                    below = {t: sum(1 for f in fwhms if f < t) for t in (5, 10, 20, 40)}
                    self.worker.log(
                        f"frankSpikes: {n} stars detected - fwhm min={fwhms[0]:.1f}px "
                        f"median={median_fwhm:.1f}px max={fwhms[-1]:.1f}px "
                        f"(below 5px: {below[5]}, below 10px: {below[10]}, "
                        f"below 20px: {below[20]}, below 40px: {below[40]}) - stars "
                        f"below the spike panel's Minimum diameter slider get no "
                        f"spike at all")
                else:
                    self.worker.log("frankSpikes: 0 stars detected")
            except Exception as e:
                self.worker.log(f"frankSpikes: star detection failed, spikes disabled: {e}")
                stars = []

            self.queue.put(("status", "Reading the active image from Siril..."))
            full_rgb = self.worker.fetch_full()
            full_shape = full_rgb.shape[:2]
            preview_rgb = downsample(full_rgb)

            # Confirmed empirically (not guessed - a user screenshot showed
            # spikes for a bottom-of-frame star rendering at the top, a
            # clean vertical mirror): get_image_stars()'s ypos is reported
            # in top-down (display) convention, while get_image_pixeldata()
            # - and so full_rgb here - is still in Siril's raw bottom-up
            # FITS row order at this point. Convert to that same raw
            # convention up front (unconditionally, not just when non-empty
            # - detect_saturated_stars below needs it too) so refine/
            # colour-sampling further down (which read pixels straight out
            # of full_rgb) use coordinates that actually land on the star;
            # the single flip applied to image+stars together further down
            # (raw -> display) then converts back, so the stored result
            # ends up in display convention as it should. An earlier
            # version tried to detect this per-image with a single star's
            # single-pixel brightness test instead of applying it
            # unconditionally - unreliable in a nebulous field, since both
            # candidate rows can plausibly be bright.
            fh, fw = full_shape
            stars = [(x, fh - 1.0 - y, fw_, a) for (x, y, fw_, a) in stars]

            try:
                extra = detect_saturated_stars(full_rgb, stars)
            except Exception as e:
                self.worker.log(f"frankSpikes: saturated-star supplement failed: {e}")
                extra = []
            if extra:
                self.worker.log(
                    f"frankSpikes: +{len(extra)} additional bright/saturated star(s) "
                    f"found directly in the pixel data - findstar's PSF fit rejects a "
                    f"clipped/flat-topped core, so these were missed regardless of the "
                    f"Minimum diameter slider or the maxstars cap")
                stars = stars + extra

            # What "Small"/"Medium"/"Large" should mean is inherently
            # image-dependent (a 6px star is huge for one setup, tiny for
            # another oversampled/binned one) - fixed pixel defaults tuned
            # on one reference image were always going to be wrong for a
            # different field's actual star sizes. Calibrated instead from
            # THIS field's own detected fwhm distribution: p5 (a size only
            # the smallest ~5% of real stars fall under - just above the
            # noise floor, not the single smallest outlier) for the cutoff/
            # Small anchor, p50 (median - literally what a typical star
            # here looks like) for Medium, p90 (clearly bigger/brighter
            # than most, but not chasing one freak saturated outlier) for
            # Large. Only the anchors' "diam" (where each look applies)
            # gets set this way - the 8 look parameters (intensity, length,
            # etc.) stay at their hand-tuned defaults, or whatever the user
            # has already dialled in.
            size_calibration = None
            if stars:
                fwhm_arr = np.array([s[2] for s in stars], dtype=np.float64)
                p5, p50, p90 = np.percentile(fwhm_arr, [5, 50, 90])
                size_calibration = {"small": float(p5), "medium": float(p50), "large": float(p90)}
                self.worker.log(
                    f"frankSpikes: calibrated star sizes for this image - "
                    f"Small={p5:.1f}px (p5) Medium={p50:.1f}px (median) "
                    f"Large={p90:.1f}px (p90)")

            if stars:
                # findstar's photometric centroid can be pulled slightly off
                # the star's actual visual peak by nearby nebulosity or a
                # neighbouring star - snap to the true local brightness peak
                # so spikes/flares centre on what the eye sees, not a fit
                # that structure around the star can bias.
                refined = []
                shifts = []
                for (x, y, fw_, a) in stars:
                    rx, ry = refine_star_position(full_rgb, x, y, fw_)
                    shifts.append(((rx - x) ** 2 + (ry - y) ** 2) ** 0.5)
                    refined.append((rx, ry, fw_, a))
                stars = refined
                if shifts:
                    self.worker.log(f"frankSpikes: position refinement shift - "
                                     f"max={max(shifts):.1f}px avg={sum(shifts)/len(shifts):.1f}px "
                                     f"(a large max here, relative to typical star fwhm, usually "
                                     f"means refinement latched onto nearby nebula/a neighbour "
                                     f"instead of the star itself)")

                # Real diffraction spikes take on their own star's colour,
                # not a flat white glow - sample it once now from the
                # full-resolution pixels while we have them.
                stars = [(x, y, fw_, a, sample_star_color(full_rgb, x, y, fw_))
                         for (x, y, fw_, a) in stars]

            # Siril always reads/displays FITS rows bottom-up, while PIL and
            # this script's Tkinter canvas assume row 0 is the top - without
            # this, the preview showed the image upside down relative to
            # Siril's own window. Flip the image and the (already mutually
            # aligned) stars together here so this script's own view of the
            # world matches what's on screen in Siril; push_rgb() flips the
            # processed result back before writing it, since Siril expects
            # pixel data in its own native row order.
            fh, fw = full_shape
            full_rgb = full_rgb[::-1, :, :].copy()
            preview_rgb = preview_rgb[::-1, :, :].copy()
            if stars:
                stars = [(x, fh - 1.0 - y, fw_, a, color) for (x, y, fw_, a, color) in stars]

            self.queue.put(("loaded", (filename, full_rgb, preview_rgb, full_shape, stars,
                                        size_calibration)))
            self.queue.put(("status", "Ready. Adjust the sliders."))
        except Exception as e:
            self.queue.put(("error", format_error(e)))

    # ---------- Live preview (pure numpy, no Siril calls) ----------
    def _update_all_labels(self):
        self.exposure_label.set(f"{self.exposure.get():.0f}")
        self.contrast_label.set(f"{self.contrast.get():.0f}")
        self.blacks_label.set(f"{self.blacks.get():.0f}")
        self.highlights_label.set(f"{self.highlights.get():.0f}")
        self.clarity_label.set(f"{self.clarity.get():.0f}")
        self.vibrance_label.set(f"{self.vibrance.get():.0f}")
        self.saturation_label.set(f"{self.saturation.get():.0f}")
        self.temperature_label.set(f"{self.temperature.get():.1f}")
        self.tint_label.set(f"{self.tint.get():.1f}")
        self.spike_rotation_label.set(f"{self.spike_rotation.get():.0f}")
        self.spike_sharpness_label.set(f"{self.spike_sharpness.get():.0f}")
        self.spike_hue_label.set(f"{self.spike_hue.get():.0f}")
        self.spike_variation_label.set(f"{self.spike_variation.get():.0f}")
        self.spike_twinkle_label.set(f"{self.spike_twinkle.get():.0f}")
        self.spike_uniform_min_diam_label.set(f"{self.spike_uniform_min_diam.get():.0f}")
        for key, _label, _lo, _hi, _step, fmt in SPIKE_ANCHOR_PARAM_DEFS:
            for av in self.spike_anchors:
                av[key + "_label"].set(fmt.format(av[key].get()))
            if key != "diam":
                self.spike_uniform[key + "_label"].set(fmt.format(self.spike_uniform[key].get()))
                self.spike_star[key + "_label"].set(fmt.format(self.spike_star[key].get()))

    def _on_tone_slider(self):
        """Light & Tones / Color & Hue sliders: cheap, so recompute and
        redraw immediately. Spikes are independent of these params, so the
        last computed spike layer is simply reused rather than recomputed -
        this used to be the main cause of sluggish dragging, since every
        single tick was re-rendering spikes from scratch regardless of
        which slider actually moved."""
        self._update_all_labels()
        if not self.loaded:
            return
        self._render_preview()
        if self.zoom_mode == "manual":
            self._schedule_hires_fetch()

    def _on_spike_slider(self):
        """Diffraction Spikes sliders: the spike layer itself is the
        expensive part (per-star geometry, optional supersampling/blur), so
        it's recomputed in the background and debounced rather than
        blocking the UI thread on every drag tick."""
        self._update_all_labels()
        if not self.loaded:
            return
        self._schedule_spike_preview()
        if self.zoom_mode == "manual":
            self._schedule_hires_fetch()

    def _on_hide_background_toggle(self):
        """'Hide background' - a preview-only display mode, not a render
        parameter: the cached layers don't change, only how they're
        composited, so this just recomposes/redraws (Fit) and re-fetches
        the hi-res crop (100%/+/-) instead of the full debounced re-render
        _on_spike_slider uses. Never affects Process/import in Siril -
        _process_thread always composites onto the real image regardless
        of this flag."""
        if not self.loaded:
            return
        self._compose_preview()
        self._redraw_canvas()
        if self.zoom_mode == "manual":
            self._schedule_hires_fetch()

    def _slider_values(self):
        return (self.exposure.get(), self.temperature.get(), self.tint.get(),
                self.contrast.get(), self.blacks.get(), self.highlights.get(),
                self.clarity.get(), self.vibrance.get(), self.saturation.get())

    def _spike_config(self):
        """The single config object render_spike_layer takes: the size-
        anchor dicts (current slider values, any order - the renderer sorts
        them) plus the global (non-size-dependent) controls. "anchors" comes
        from whichever mode is active - _uniform_anchors() in "uniform" mode,
        the 3 tabbed anchors in "per_size" mode."""
        if self.spike_mode.get() == "uniform":
            anchors = self._uniform_anchors()
        else:
            anchors = [{key: av[key].get() for key, *_ in SPIKE_ANCHOR_PARAM_DEFS}
                       for av in self.spike_anchors]
        return {
            "anchors": anchors,
            "rays": int(self.spike_rays.get()),
            "rotation": self.spike_rotation.get(),
            "hue": self.spike_hue.get(),
            "sharpness": self.spike_sharpness.get(),
            "variation": self.spike_variation.get(),
            "twinkle": self.spike_twinkle.get(),
        }

    def _uniform_anchors(self):
        """Two synthetic anchors that let "Uniform" mode reuse the exact
        same log-diameter/smoothstep blend as the per-size anchors (see
        _interp_anchor_params): zero effect right at the Minimum diameter
        (matching "no spike below cutoff", same as the smallest per-size
        anchor), the literal dialled-in slider values at
        SPIKE_UNIFORM_REF_MULT times that diameter and beyond - so every
        parameter's real impact scales with each star's own size from a
        single knob per parameter, with no separate interpolation path to
        maintain."""
        min_d = self.spike_uniform_min_diam.get()
        full = {k: self.spike_uniform[k].get() for k in _ANCHOR_PARAM_KEYS}
        zero = {k: 0.0 for k in _ANCHOR_PARAM_KEYS}
        return [
            {"diam": min_d, **zero},
            {"diam": min_d * SPIKE_UNIFORM_REF_MULT, **full},
        ]

    def _spike_min_diameter(self):
        """The current mode's cutoff diameter - below it a star gets no
        spike at all (see render_spike_layer)."""
        if self.spike_mode.get() == "uniform":
            return self.spike_uniform_min_diam.get()
        return min(av["diam"].get() for av in self.spike_anchors)

    def _effective_stars(self):
        """Detected stars minus any the user disabled, plus any manually
        added ones - the exact (x,y,fwhm,amp,color,forced,override) list
        that goes into rendering. `forced` bypasses the min-diameter
        cutoff: it's set for stars the user explicitly turned on with
        Ctrl+Click even though they're smaller than the current threshold,
        and always set for manually-added ones (there's no "detected size"
        to filter by). `override` is that star's manual per-star look (see
        self._spike_star_overrides) if Shift+Click editing set one, else
        None - render_spike_layer uses it verbatim instead of interpolating
        from the Small/Medium/Large or Simple size-based anchors."""
        out = []
        for i, (x, y, fwhm, amp, color) in enumerate(self._stars):
            if i in self._spike_disabled:
                continue
            override = self._spike_star_overrides.get(("auto", i))
            out.append((x, y, fwhm, amp, color, i in self._spike_forced, override))
        for (mid, x, y, fwhm, amp, color) in self._spike_manual:
            override = self._spike_star_overrides.get(("manual", mid))
            out.append((x, y, fwhm, amp, color, True, override))
        return out

    def _reset_spike_edits(self):
        self._spike_disabled.clear()
        self._spike_forced.clear()
        self._spike_manual.clear()
        self._spike_star_overrides.clear()
        self._deselect_star()
        if self.loaded:
            self._schedule_spike_preview()

    def _reset_spike_defaults(self):
        """Resets the spike sliders to SPIKE_DEFAULTS - leaves per-star
        Ctrl+Click edits and Shift+Click overrides (disabled/forced/manual/
        star_overrides) untouched, that's what "Reset manual edits" is for."""
        d = SPIKE_DEFAULTS
        self.spike_enabled.set(d["enabled"])
        self.spike_rays.set(d["rays"])
        self.spike_rotation.set(d["rotation"])
        self.spike_hue.set(d["hue"])
        self.spike_sharpness.set(d["sharpness"])
        self.spike_variation.set(d["variation"])
        self.spike_twinkle.set(d["twinkle"])
        for av, defaults in zip(self.spike_anchors, d["anchors"]):
            for key, *_ in SPIKE_ANCHOR_PARAM_DEFS:
                av[key].set(defaults[key])
        ud = SPIKE_UNIFORM_DEFAULTS
        self.spike_uniform_min_diam.set(ud["min_diam"])
        for key in _ANCHOR_PARAM_KEYS:
            self.spike_uniform[key].set(ud[key])
        self._on_spike_slider()

    def _on_spike_mode_change(self):
        new_mode = self.spike_mode.get()
        if new_mode == "per_size" and self._last_spike_mode == "uniform":
            # Carry the Uniform look over onto Small/Medium/Large instead of
            # leaving the per-size tabs at whatever (possibly stale/default)
            # values they last held - switching modes would otherwise feel
            # like a reset, and any earlier Ctrl+Click star edits are
            # untouched either way (only the sliders below are seeded).
            self._seed_per_size_from_uniform()
        self._last_spike_mode = new_mode
        self._update_spike_mode_ui()
        self._on_spike_slider()

    def _apply_size_calibration(self, size_calibration):
        """Sets the Small/Medium/Large tabs' and Uniform mode's diameter
        sliders to what this specific image's own detected stars call for
        (see _reload_thread's size_calibration comment for the p5/median/p90
        reasoning) - runs once, right after Reload/star-detection finishes,
        before the user has had any chance to touch a slider, so this never
        overwrites a manual edit. Only repositions where each anchor's look
        applies; the look itself (intensity, length, etc.) is untouched."""
        small, medium, large = (size_calibration["small"], size_calibration["medium"],
                                 size_calibration["large"])
        u_lo, u_hi = SPIKE_ANCHOR_DIAM_RANGES[0]
        self.spike_uniform_min_diam.set(min(u_hi, max(u_lo, small)))
        for tab_index, (av, value) in enumerate(zip(self.spike_anchors, (small, medium, large))):
            lo, hi = spike_anchor_slider_range(tab_index, "diam")
            av["diam"].set(min(hi, max(lo, value)))
        self._update_all_labels()

    def _seed_per_size_from_uniform(self):
        """One-time hand-off when switching Uniform -> Per size: sets the
        Small/Medium/Large anchors to approximate the look Uniform mode was
        just rendering, so the preview doesn't jump and the three tabs
        become a starting point the user can then diverge from ("make
        variations on their Per-size range") instead of overwriting their
        own later per-size edits on every toggle back - _on_spike_mode_change
        only calls this on the uniform->per_size transition, not on every
        re-selection of "Per size".

        Each tab's "diam" is set to its natural position on the Uniform
        curve (the cutoff, the geometric-mean midpoint, and the full-effect
        diameter). Its 8 look sliders are sampled from that same curve, but
        NOT at those exact diameters for the Small tab: fwhm == the cutoff
        is by construction the Uniform curve's zero-effect point (every
        slider pinned to 0), so sampling Small's look there previously left
        every slider in that tab at 0 - technically consistent with the
        curve, but reads as broken rather than "a small star's subtler
        look". Sampled a little past the cutoff instead, at 15% of the way
        (in log-diameter space) toward the full-effect diameter, matching
        how the original hand-tuned Small anchor default was never literally
        zero either. Medium (already the curve's own midpoint) and Large
        (already the curve's own full-effect point, non-degenerate) are
        unaffected by this and still sample exactly on-curve."""
        anchors_sorted = sorted(self._uniform_anchors(), key=lambda a: a["diam"])
        lo_d, hi_d = anchors_sorted[0]["diam"], anchors_sorted[-1]["diam"]
        mid_d = (lo_d * hi_d) ** 0.5  # geometric mean - matches the log-diameter blend's midpoint
        ratio = max(hi_d / max(lo_d, 1e-6), 1e-6)
        small_sample_d = lo_d * (ratio ** 0.15)
        for tab_index, (av, tab_diam, sample_d) in enumerate(zip(
                self.spike_anchors, (lo_d, mid_d, hi_d), (small_sample_d, mid_d, hi_d))):
            diam_lo, diam_hi = spike_anchor_slider_range(tab_index, "diam")
            av["diam"].set(min(diam_hi, max(diam_lo, tab_diam)))
            params = _interp_anchor_params(anchors_sorted, sample_d)
            for key in _ANCHOR_PARAM_KEYS:
                # Small/Medium's sliders have a narrower ceiling than the
                # Uniform curve's own full-range params dict can produce
                # (see SPIKE_ANCHOR_LOOK_SCALE) - clamp so the seeded value
                # never silently exceeds what that tab's slider can show.
                key_lo, key_hi = spike_anchor_slider_range(tab_index, key)
                av[key].set(min(key_hi, max(key_lo, params[key])))

    def _update_spike_mode_ui(self):
        """Shows whichever of the notebook (per-size tabs) / flat uniform
        panel / single-star panel applies right now, and swaps the matching
        help text - only one of the three control sets is ever visible at
        once. A star selection (Shift+Click) always wins over the Simple/
        Per-size mode choice, which stays remembered underneath and
        reappears as soon as the star is deselected."""
        if self._selected_star_key is not None:
            self._spike_notebook.grid_remove()
            self._spike_uniform_frame.grid_remove()
            self._spike_star_frame.grid()
            self._spike_help_label.config(text=self._spike_help_star)
        elif self.spike_mode.get() == "uniform":
            self._spike_notebook.grid_remove()
            self._spike_star_frame.grid_remove()
            self._spike_uniform_frame.grid()
            self._spike_help_label.config(text=self._spike_help_uniform)
        else:
            self._spike_uniform_frame.grid_remove()
            self._spike_star_frame.grid_remove()
            self._spike_notebook.grid()
            self._spike_help_label.config(text=self._spike_help_per_size)

    def _current_look_for_fwhm(self, fwhm):
        """The size-based (Simple or Per-size) look a star of this fwhm
        currently renders with, absent any per-star override - used to
        pre-fill the star-editing sliders with "what it looks like right
        now" instead of some arbitrary default when a star is first
        selected, so nudging a slider is a small change, not a jump."""
        anchors = self._spike_config()["anchors"]
        anchors_sorted = sorted(anchors, key=lambda a: a["diam"])
        min_diameter = anchors_sorted[0]["diam"]
        return _interp_anchor_params(anchors_sorted, max(fwhm, min_diameter))

    def _star_lookup(self, key):
        """(x, y, fwhm, amp, color) for a ("auto"|"manual", id) key, or
        None if it no longer exists (e.g. a manual star that got deleted
        while selected)."""
        kind, ident = key
        if kind == "auto":
            if 0 <= ident < len(self._stars):
                return self._stars[ident]
            return None
        for (mid, x, y, fwhm, amp, color) in self._spike_manual:
            if mid == ident:
                return (x, y, fwhm, amp, color)
        return None

    def _select_star(self, key):
        """Selects a star for individual editing (Shift+Click): shows its
        current look (its override if one exists, else the size-based look
        it's currently rendering with) in the star-panel sliders, without
        creating an override by itself - only actually moving a slider
        does that (see _on_star_slider_change)."""
        star = self._star_lookup(key)
        if star is None:
            return
        _x, _y, fwhm, _amp, _color = star
        self._selected_star_key = key
        override = self._spike_star_overrides.get(key)
        values = override if override is not None else self._current_look_for_fwhm(fwhm)
        for k in _ANCHOR_PARAM_KEYS:
            self.spike_star[k].set(values[k])
        state = "custom look" if override is not None else "size-based look"
        self.spike_star_info.set(f"Editing star (fwhm ≈ {fwhm:.1f}px) - showing its {state}")
        self._update_all_labels()
        self._update_spike_mode_ui()
        self._redraw_canvas()

    def _deselect_star(self):
        if self._selected_star_key is None:
            return
        self._selected_star_key = None
        self._update_spike_mode_ui()
        self._redraw_canvas()

    def _reset_selected_star_override(self):
        """"Reset this star to its size-based look" - drops its override
        (if any) and refreshes the sliders to show what it now falls back
        to, without deselecting it."""
        if self._selected_star_key is None:
            return
        had_override = self._spike_star_overrides.pop(self._selected_star_key, None) is not None
        self._select_star(self._selected_star_key)
        if had_override:
            self._schedule_spike_preview()

    def _on_star_slider_change(self):
        """A star-panel slider moved: snapshot all 8 current values as that
        star's override (the first touch turns "showing its current look"
        into "now permanently overridden" - see _select_star/full-override
        design), then re-render."""
        self._update_all_labels()
        if self._selected_star_key is None:
            return
        self._spike_star_overrides[self._selected_star_key] = {
            k: self.spike_star[k].get() for k in _ANCHOR_PARAM_KEYS}
        if not self.loaded:
            return
        self._schedule_spike_preview()
        if self.zoom_mode == "manual":
            self._schedule_hires_fetch()

    def _spike_supersample(self, ph, pw):
        """How much to render the spike layer oversized before area-
        averaging it down to the low-res Fit preview's (ph, pw). Evaluating
        a thin ray's gaussian profile directly on a sparse grid makes its
        apparent thickness AND brightness depend on where it happens to
        land between raster pixels (aliasing) - rendering a few times
        larger and properly downsampling avoids that, at a bounded cost."""
        fh, fw = self.full_shape
        scale = pw / max(fw, 1)
        # The thinnest actually-rendered thickness sets the aliasing risk -
        # a preview supersampled only enough for a thick "Large" spike would
        # still alias a thin "Small" one. In "uniform" mode the synthetic
        # zero-anchor's thickness is never actually rendered (it only marks
        # the cutoff where the ray fades out entirely), so the dialled-in
        # slider value itself is the right thinnest-case estimate there.
        if self.spike_mode.get() == "uniform":
            th = self.spike_uniform["thickness"].get() * scale
        else:
            th = min(av["thickness"].get() for av in self.spike_anchors) * scale
        if th >= 0.5:
            return 1
        return int(min(4, max(1, np.ceil(0.5 / max(th, 1e-3)))))

    def _render_preview(self):
        """Recompute only the cheap tone/colour grading and redraw, reusing
        whatever spike layer is already cached - the spike layer itself is
        recomputed separately (see _schedule_spike_preview), since it's the
        expensive part and doesn't depend on these sliders at all."""
        self._base_preview_rgb = apply_cosmetics(self._src_preview_rgb, *self._slider_values())
        self._compose_preview()
        self._redraw_canvas()

    def _compose_preview(self):
        rgb = np.zeros_like(self._base_preview_rgb) if self.hide_background.get() else self._base_preview_rgb
        if self.spike_enabled.get() and self._spike_layer_preview is not None:
            rgb = apply_spikes(rgb, self._spike_layer_preview)
        self._preview_rgb = rgb

    def _schedule_spike_preview(self):
        """Debounced, backgrounded spike-layer recompute for the Fit
        preview - mirrors _schedule_hires_fetch's pattern so a rapid drag
        across a spike slider doesn't queue up dozens of expensive renders,
        only the last one after a short pause."""
        if self._spike_preview_after_id is not None:
            self.root.after_cancel(self._spike_preview_after_id)
        self._spike_preview_after_id = self.root.after(150, self._start_spike_preview)

    def _start_spike_preview(self):
        self._spike_preview_after_id = None
        if not self.loaded or self._base_preview_rgb is None:
            return
        if self._spike_preview_inflight:
            # A previous render is still running - on a star-dense field
            # one of these can take well over a second, far longer than
            # the 150ms debounce, so without this guard a continuous drag
            # launches many overlapping threads that all eventually finish
            # one after another, keeping the busy spinner going for a
            # while after the user has already stopped touching anything.
            # Check back shortly instead of piling up another thread; once
            # free, this always picks up whatever the sliders currently
            # say, so nothing requested in the meantime gets lost.
            self._spike_preview_after_id = self.root.after(50, self._start_spike_preview)
            return
        self._spike_preview_gen += 1
        gen = self._spike_preview_gen

        if not self.spike_enabled.get():
            self._spike_layer_preview = None
            self._spike_layer_key = None
            self._compose_preview()
            self._redraw_canvas()
            return

        stars = self._effective_stars()
        if not stars:
            self._spike_layer_preview = None
            self._spike_layer_key = None
            self._compose_preview()
            self._redraw_canvas()
            return

        ph, pw = self._base_preview_rgb.shape[:2]
        fh, fw = self.full_shape
        params = self._spike_config()
        ss = self._spike_supersample(ph, pw)
        key = repr((stars, params, ss, ph, pw))
        if key == self._spike_layer_key:
            self._compose_preview()
            self._redraw_canvas()
            return
        self._spike_preview_inflight = True
        self._busy_begin()
        t = threading.Thread(target=self._spike_preview_thread,
                              args=(gen, ph, pw, fh, fw, stars, params, ss, key), daemon=True)
        t.start()

    def _spike_preview_thread(self, gen, ph, pw, fh, fw, stars, params, ss, key):
        # Always post something, success or failure - _poll_queue's
        # "spike_preview" handler pairs every message here with the
        # _busy_begin() this thread's launch made, so the busy spinner
        # would otherwise spin forever after a failed render.
        layer = None
        try:
            if ss > 1:
                layer = render_spike_layer((ph * ss, pw * ss), 0, 0, fw, fh, stars, params)
                layer = resize_layer(layer, pw, ph)
            else:
                layer = render_spike_layer((ph, pw), 0, 0, fw, fh, stars, params)
        except Exception as e:
            try:
                self.worker.log(f"frankSpikes: spike preview render failed: {e}")
            except Exception:
                pass
        self.queue.put(("spike_preview", (gen, layer, key)))

    # ---------- Zoom / pan / canvas ----------
    # In "fit" mode the low-resolution raster is always shown (that's fine:
    # the whole image squeezed into the window can't show more detail than
    # that anyway). In "manual" mode (+/-/100%) only the [x,y,w,h] crop
    # needed to fill the canvas is fetched from Siril in the background, at
    # full resolution: a real pixel-for-pixel zoom without having to
    # transfer the whole image on every move.

    def _on_canvas_resize(self, _event):
        self._redraw_canvas()
        if self.zoom_mode == "manual":
            self._schedule_hires_fetch()

    def _zoom_in(self):
        self.zoom_mode = "manual"
        self.zoom_pct = min(self.zoom_pct * 1.25, 8.0)
        self._redraw_canvas()
        self._schedule_hires_fetch()

    def _zoom_out(self):
        self.zoom_mode = "manual"
        self.zoom_pct = max(self.zoom_pct / 1.25, 0.1)
        self._redraw_canvas()
        self._schedule_hires_fetch()

    def _zoom_1to1(self):
        self.zoom_mode = "manual"
        self.zoom_pct = 1.0
        self._redraw_canvas()
        self._schedule_hires_fetch()

    def _zoom_fit(self):
        self.zoom_mode = "fit"
        self._hires_rgb = None
        self._hires_wh = None
        self._redraw_canvas()

    def _on_canvas_press(self, event):
        # Handled here (checking the modifier bits directly) rather than via
        # separate <Control-Button-1>/<Shift-Button-1> bindings: on some
        # Windows/Tk builds a plain <ButtonPress-1> binding on the same
        # widget still fires alongside the modifier-qualified one, which
        # made Ctrl+Click silently toggle a spike on and back off in the
        # same click - so every modifier is read from this single handler.
        if event.state & 0x0004:  # Control key held
            self._on_canvas_ctrl_click(event)
            return
        if event.state & 0x0001:  # Shift key held
            self._on_canvas_shift_click(event)
            return
        self._drag_last = (event.x, event.y)

    def _on_space_press(self, event):
        # Guard against key-repeat (holding the key fires repeated
        # KeyPress events on most platforms) triggering redundant redraws.
        if self._show_original or self.full_shape is None:
            return
        self._show_original = True
        self._redraw_canvas()

    def _on_space_release(self, event):
        if not self._show_original:
            return
        self._show_original = False
        self._redraw_canvas()

    def _on_canvas_drag(self, event):
        if self.zoom_mode != "manual" or self.full_shape is None or self._drag_last is None:
            return
        dx = event.x - self._drag_last[0]
        dy = event.y - self._drag_last[1]
        self._drag_last = (event.x, event.y)
        fh, fw = self.full_shape
        # dragging right must move the view to the left
        self.view_cx = min(1.0, max(0.0, self.view_cx - dx / max(1, fw * self.zoom_pct)))
        self.view_cy = min(1.0, max(0.0, self.view_cy - dy / max(1, fh * self.zoom_pct)))
        self._redraw_canvas()
        self._schedule_hires_fetch()

    def _on_canvas_wheel(self, event):
        if self.zoom_mode != "manual" or self.full_shape is None:
            return
        delta = event.delta if event.delta else (120 if event.num == 4 else -120)
        step = -delta / 120 * 60  # ~60px of scroll per notch
        fh, fw = self.full_shape
        shift_horizontal = bool(event.state & 0x0001)  # Shift key
        if shift_horizontal:
            self.view_cx = min(1.0, max(0.0, self.view_cx + step / max(1, fw * self.zoom_pct)))
        else:
            self.view_cy = min(1.0, max(0.0, self.view_cy + step / max(1, fh * self.zoom_pct)))
        self._redraw_canvas()
        self._schedule_hires_fetch()

    def _canvas_to_full(self, cx, cy):
        """Screen coordinates on the preview canvas -> full-resolution image
        pixel coordinates, using whichever raster (fit or hi-res crop) is
        actually on screen right now. Returns (None, None) if the click
        landed outside the displayed image."""
        canvas = self.preview_canvas
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        fh, fw = self.full_shape

        if self.zoom_mode == "fit":
            ph, pw = self._preview_rgb.shape[:2]
            # Must match _redraw_canvas's fit-branch sizing exactly (also
            # int(round(...)), not a bare float) - even a sub-pixel gap
            # between the two gets multiplied by fw/pw when converting back
            # to full-res coordinates, which can be a factor of several x
            # once PREVIEW_MAX_W is much smaller than the real image width,
            # turning a harmless rounding difference into a visibly
            # mis-clicked star position.
            disp_w = max(1, int(round(pw * self.zoom_pct)))
            disp_h = max(1, int(round(ph * self.zoom_pct)))
            ox, oy = cw / 2 - disp_w / 2, ch / 2 - disp_h / 2
            ix, iy = (cx - ox) / self.zoom_pct, (cy - oy) / self.zoom_pct
            if not (0 <= ix < pw and 0 <= iy < ph):
                return None, None
            return ix * fw / pw, iy * fh / ph

        x0, y0, crop_w, crop_h = self._compute_crop(cw, ch)
        actual_w, actual_h = self._hires_wh if self._hires_wh is not None else (crop_w, crop_h)
        # Same reasoning as the fit branch above - match _redraw_canvas's
        # manual-mode sizing exactly.
        disp_w = max(1, int(round(actual_w * self.zoom_pct)))
        disp_h = max(1, int(round(actual_h * self.zoom_pct)))
        ox, oy = cw / 2 - disp_w / 2, ch / 2 - disp_h / 2
        ix, iy = (cx - ox) / self.zoom_pct, (cy - oy) / self.zoom_pct
        if not (0 <= ix < actual_w and 0 <= iy < actual_h):
            return None, None
        return x0 + ix * crop_w / actual_w, y0 + iy * crop_h / actual_h

    def _full_to_canvas(self, fx, fy):
        """Inverse of _canvas_to_full: full-resolution image pixel
        coordinates -> screen coordinates on the preview canvas, using
        whichever raster (fit or hi-res crop) is actually on screen right
        now. Used only to position the selected-star highlight - unlike
        _canvas_to_full, out-of-view results aren't filtered out here
        (Tk simply won't draw an oval whose coordinates land off-canvas)."""
        canvas = self.preview_canvas
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        fh, fw = self.full_shape

        if self.zoom_mode == "fit":
            ph, pw = self._preview_rgb.shape[:2]
            disp_w = max(1, int(round(pw * self.zoom_pct)))
            disp_h = max(1, int(round(ph * self.zoom_pct)))
            ox, oy = cw / 2 - disp_w / 2, ch / 2 - disp_h / 2
            ix, iy = fx * pw / fw, fy * ph / fh
            return ix * self.zoom_pct + ox, iy * self.zoom_pct + oy

        x0, y0, crop_w, crop_h = self._compute_crop(cw, ch)
        actual_w, actual_h = self._hires_wh if self._hires_wh is not None else (crop_w, crop_h)
        disp_w = max(1, int(round(actual_w * self.zoom_pct)))
        disp_h = max(1, int(round(actual_h * self.zoom_pct)))
        ox, oy = cw / 2 - disp_w / 2, ch / 2 - disp_h / 2
        ix = (fx - x0) * actual_w / crop_w
        iy = (fy - y0) * actual_h / crop_h
        return ix * self.zoom_pct + ox, iy * self.zoom_pct + oy

    def _find_nearby_star(self, fx, fy):
        """Nearest detected or manually-added star within a small, fixed
        hit radius of (fx, fy), as ("auto", index) | ("manual", manual_id),
        or None. The manual half is that star's stable id (see
        self._spike_manual), not its current list position, so it stays
        valid as a dict key even after some other manual star gets deleted.

        The radius used to be max(6px, the star's own fwhm) - fwhm is the
        star's optical size, not a sensible click tolerance, so a big
        bright star (fwhm 30-40px, sometimes 100+ for a heavily saturated
        one) turned into a huge "sticky" zone around it: any click within
        that whole radius silently snapped to the star's own stored
        position and toggled it, instead of landing precisely where the
        user actually clicked. A fixed small radius means only a click
        genuinely close to a star's position hits it; anything else adds a
        new manual spike exactly at the click, as intended."""
        HIT_RADIUS_PX = 10.0
        best, best_d = None, None
        for i, (x, y, _fwhm, _amp, _color) in enumerate(self._stars):
            d = ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5
            if d <= HIT_RADIUS_PX and (best_d is None or d < best_d):
                best, best_d = ("auto", i), d
        for (mid, x, y, _fwhm, _amp, _color) in self._spike_manual:
            d = ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5
            if d <= HIT_RADIUS_PX and (best_d is None or d < best_d):
                best, best_d = ("manual", mid), d
        return best

    def _on_canvas_shift_click(self, event):
        """Shift+Click: select a star for individual editing, or deselect
        if the click didn't land on one (empty space, or outside the
        displayed image) - see _select_star/_deselect_star."""
        if not self.loaded or self.full_shape is None:
            return
        fx, fy = self._canvas_to_full(event.x, event.y)
        hit = self._find_nearby_star(fx, fy) if fx is not None else None
        if hit is not None:
            self._select_star(hit)
        else:
            self._deselect_star()

    def _on_canvas_ctrl_click(self, event):
        if not self.loaded or self.full_shape is None:
            return
        cw, ch = self.preview_canvas.winfo_width(), self.preview_canvas.winfo_height()
        fx, fy = self._canvas_to_full(event.x, event.y)
        if fx is None:
            self.worker.log(f"frankSpikes: Ctrl+Click at screen ({event.x},{event.y}) "
                             f"canvas={cw}x{ch} zoom_mode={self.zoom_mode} "
                             f"zoom_pct={self.zoom_pct:.4f} -> outside the displayed image, ignored")
            return
        hit = self._find_nearby_star(fx, fy)
        if hit is not None:
            kind, i = hit
            if kind == "manual":
                idx = next(idx for idx, m in enumerate(self._spike_manual) if m[0] == i)
                _mid, hx, hy, hfwhm, _a, _c = self._spike_manual[idx]
                self.worker.log(f"frankSpikes: Ctrl+Click at screen ({event.x},{event.y}) -> "
                                 f"full-res ({fx:.1f},{fy:.1f}) - removed MANUAL spike #{i} "
                                 f"at ({hx:.1f},{hy:.1f}) fwhm={hfwhm:.1f} "
                                 f"[distance from click: {((hx-fx)**2+(hy-fy)**2)**0.5:.1f}px]")
                del self._spike_manual[idx]
                self._spike_star_overrides.pop(("manual", i), None)
                if self._selected_star_key == ("manual", i):
                    self._deselect_star()
            else:
                hx, hy, fwhm, _amp, _color = self._stars[i]
                self.worker.log(f"frankSpikes: Ctrl+Click at screen ({event.x},{event.y}) -> "
                                 f"full-res ({fx:.1f},{fy:.1f}) - matched AUTO star #{i} at "
                                 f"({hx:.1f},{hy:.1f}) fwhm={fwhm:.1f} "
                                 f"[distance from click: {((hx-fx)**2+(hy-fy)**2)**0.5:.1f}px] "
                                 f"- toggling that star, NOT adding a new one at the click point")
                # A star findstar detected can still be below the current
                # min-diameter threshold, so "is it currently showing a
                # spike" depends on more than just the disabled set.
                showing = (i not in self._spike_disabled and
                           (fwhm >= self._spike_min_diameter() or i in self._spike_forced))
                if showing:
                    self._spike_disabled.add(i)
                    self._spike_forced.discard(i)
                else:
                    self._spike_disabled.discard(i)
                    self._spike_forced.add(i)
        else:
            default_fwhm = max(3.0, self._spike_min_diameter() * 1.5)
            self._manual_id_counter += 1
            self._spike_manual.append(
                (self._manual_id_counter, fx, fy, default_fwhm, 1.0, (1.0, 1.0, 1.0)))
            self.worker.log(f"frankSpikes: Ctrl+Click at screen ({event.x},{event.y}) "
                             f"canvas={cw}x{ch} zoom_mode={self.zoom_mode} "
                             f"zoom_pct={self.zoom_pct:.4f} -> full-res ({fx:.1f},{fy:.1f}) "
                             f"- added a NEW manual spike exactly there")
        self._schedule_spike_preview()
        if self.zoom_mode == "manual":
            self._schedule_hires_fetch()

    def _on_hscroll(self, *args):
        self._scroll_axis("x", args)

    def _on_vscroll(self, *args):
        self._scroll_axis("y", args)

    def _scroll_axis(self, axis, args):
        """Standard ttk.Scrollbar callback: args is either
        ('moveto', fraction) from dragging the thumb, or
        ('scroll', amount, 'units'|'pages') from clicking the arrows/trough."""
        if self.zoom_mode != "manual" or self.full_shape is None:
            return
        fh, fw = self.full_shape
        dim = fw if axis == "x" else fh
        cw, ch = self.preview_canvas.winfo_width(), self.preview_canvas.winfo_height()
        span_px = (cw if axis == "x" else ch) / self.zoom_pct
        span_frac = min(1.0, span_px / dim)
        cur = self.view_cx if axis == "x" else self.view_cy

        if args[0] == "moveto":
            new_center = float(args[1]) + span_frac / 2
        elif args[0] == "scroll":
            amount = float(args[1])
            step = span_frac if args[2] == "pages" else span_frac * 0.05
            new_center = cur + amount * step
        else:
            return

        new_center = min(1.0, max(0.0, new_center))
        if axis == "x":
            self.view_cx = new_center
        else:
            self.view_cy = new_center
        self._redraw_canvas()
        self._schedule_hires_fetch()

    def _compute_crop(self, cw, ch):
        """(x, y, w, h) in original-image pixels corresponding to what should
        fill the canvas at the current zoom/pan level."""
        fh, fw = self.full_shape
        crop_w = max(1, min(fw, int(round(cw / self.zoom_pct))))
        crop_h = max(1, min(fh, int(round(ch / self.zoom_pct))))
        x = int(round(self.view_cx * fw - crop_w / 2))
        y = int(round(self.view_cy * fh - crop_h / 2))
        x = max(0, min(fw - crop_w, x))
        y = max(0, min(fh - crop_h, y))
        return x, y, crop_w, crop_h

    def _raster_crop_view(self, cw, ch):
        """Instant, local fallback for manual mode: crop/scale the low-res
        raster around the current pan position, using the same framing a
        real full-res crop would have. Blurrier than the real thing, but it
        responds to drag/wheel/scrollbar immediately instead of waiting on a
        round-trip to Siril."""
        rh, rw = self._preview_rgb.shape[:2]
        fh, fw = self.full_shape
        scale_x, scale_y = rw / fw, rh / fh
        crop_w = max(1, min(rw, int(round(cw / self.zoom_pct * scale_x))))
        crop_h = max(1, min(rh, int(round(ch / self.zoom_pct * scale_y))))
        x = int(round(self.view_cx * rw - crop_w / 2))
        y = int(round(self.view_cy * rh - crop_h / 2))
        x = max(0, min(rw - crop_w, x))
        y = max(0, min(rh - crop_h, y))
        crop = self._preview_rgb[y:y + crop_h, x:x + crop_w]
        img = Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8))
        return img.resize((cw, ch), Image.NEAREST)

    def _schedule_hires_fetch(self):
        if self.full_shape is None or self._siril_busy:
            return
        if self._hires_after_id is not None:
            self.root.after_cancel(self._hires_after_id)
        self._hires_after_id = self.root.after(250, self._start_hires_fetch)

    def _start_hires_fetch(self):
        self._hires_after_id = None
        if self._siril_busy:
            return
        if self._hires_inflight:
            # Same reasoning as _start_spike_preview's matching guard: a
            # render-heavy crop on a star-dense field can take longer than
            # the debounce window, so without this, continuous panning/
            # zooming could launch overlapping fetch threads that keep the
            # busy spinner going well after the user stops interacting.
            self._hires_after_id = self.root.after(50, self._start_hires_fetch)
            return
        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return
        crop = self._compute_crop(cw, ch)
        self._hires_gen += 1
        gen = self._hires_gen
        vals = self._slider_values()
        spike_state = (self.spike_enabled.get(), self._effective_stars(), self._spike_config())
        full = self._pristine_full
        hide_bg = self.hide_background.get()
        self._hires_inflight = True
        self._busy_begin()
        t = threading.Thread(target=self._hires_fetch_thread,
                              args=(gen, crop, vals, spike_state, full, hide_bg), daemon=True)
        t.start()

    def _hires_fetch_thread(self, gen, crop, vals, spike_state, full, hide_bg):
        # Always post something, success or failure - see the matching note
        # in _spike_preview_thread on why this can't just return on error.
        rgb, actual_wh = None, None
        try:
            # The crop is sliced straight out of the pristine full-resolution
            # array we already hold in memory - no round trip to Siril, and
            # the returned size always matches the requested one exactly.
            req_x, req_y, req_w, req_h = crop
            rgb = full[req_y:req_y + req_h, req_x:req_x + req_w].copy()
            got_h, got_w = rgb.shape[:2]

            rgb = apply_cosmetics(rgb, *vals)
            if hide_bg:
                rgb = np.zeros_like(rgb)
            spike_enabled, stars, sparams = spike_state
            if spike_enabled and stars:
                layer = render_spike_layer((got_h, got_w), req_x, req_y, req_w, req_h,
                                            stars, sparams)
                rgb = apply_spikes(rgb, layer)
            actual_wh = (got_w, got_h)
        except Exception as e:
            # This is only a high-res preview: on failure we just stay on the
            # local raster fallback instead of popping an error at the user.
            rgb = None
            try:
                self.worker.log(f"frankSpikes: hi-res crop fetch failed: {e}")
            except Exception:
                pass
        self.queue.put(("hires", (gen, rgb, actual_wh)))

    def _original_crop_view(self, cw, ch):
        """Same crop/zoom framing _redraw_canvas's manual-mode hires view
        uses, but sliced straight from the untouched pristine full-res
        source instead of the edited one - instant (no background fetch
        needed, it's a plain slice) and used for the Space-bar 'before'
        toggle so it lines up exactly with whatever's currently on screen."""
        x, y, crop_w, crop_h = self._compute_crop(cw, ch)
        crop = self._pristine_full[y:y + crop_h, x:x + crop_w]
        disp_w = max(1, int(round(crop_w * self.zoom_pct)))
        disp_h = max(1, int(round(crop_h * self.zoom_pct)))
        img = Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8))
        return img.resize((disp_w, disp_h), Image.NEAREST if self.zoom_pct > 1.0 else Image.BILINEAR)

    def _redraw_canvas(self):
        canvas = self.preview_canvas
        if self._preview_rgb is None:
            return
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return

        if self.zoom_mode == "fit":
            source = self._src_preview_rgb if self._show_original else self._preview_rgb
            h, w = source.shape[:2]
            self.zoom_pct = min(cw / w, ch / h, 8.0)
            # self.zoom_pct above is relative to this low-res preview raster
            # (needed as-is for the resize/click-mapping math right below,
            # and it must stay in lockstep with _canvas_to_full's fit
            # branch) - but "100%" should mean the image's real native
            # resolution, not the size of this internal downsampled raster,
            # so the displayed label uses a separately-scaled value.
            fh, fw = self.full_shape
            self._display_zoom_pct = self.zoom_pct * (w / fw)
            img = Image.fromarray((np.clip(source, 0, 1) * 255).astype(np.uint8))
            # int(round(...)), not a bare int() truncation - _canvas_to_full
            # must compute the exact same size or a Ctrl+Click's screen->
            # full-res conversion drifts off whatever's actually on screen.
            disp_w = max(1, int(round(w * self.zoom_pct)))
            disp_h = max(1, int(round(h * self.zoom_pct)))
            # LANCZOS instead of BILINEAR: this raster already carries real
            # detail up to PREVIEW_MAX_W now, and BILINEAR was visibly
            # softening it further on top of that when scaled to fill the
            # canvas.
            img = img.resize((disp_w, disp_h), Image.LANCZOS)
            self._tkimg = ImageTk.PhotoImage(img)
            canvas.delete("all")
            canvas.create_image(cw // 2, ch // 2, image=self._tkimg, anchor="center")
            self.hbar.set(0.0, 1.0)
            self.vbar.set(0.0, 1.0)
        else:
            # Already native-resolution-relative here (100% really is 1
            # screen pixel per real image pixel), unlike the fit branch.
            self._display_zoom_pct = self.zoom_pct
            if self._show_original:
                img = self._original_crop_view(cw, ch)
            elif self._hires_rgb is not None:
                actual_w, actual_h = self._hires_wh
                disp_w = max(1, int(round(actual_w * self.zoom_pct)))
                disp_h = max(1, int(round(actual_h * self.zoom_pct)))
                img = Image.fromarray((np.clip(self._hires_rgb, 0, 1) * 255).astype(np.uint8))
                img = img.resize((disp_w, disp_h), Image.NEAREST if self.zoom_pct > 1.0 else Image.BILINEAR)
            else:
                img = self._raster_crop_view(cw, ch)
            self._tkimg = ImageTk.PhotoImage(img)
            canvas.delete("all")
            canvas.create_image(cw // 2, ch // 2, image=self._tkimg, anchor="center")

            x, y, crop_w, crop_h = self._compute_crop(cw, ch)
            fh, fw = self.full_shape
            self.hbar.set(x / fw, (x + crop_w) / fw)
            self.vbar.set(y / fh, (y + crop_h) / fh)

        self.zoom_label.set(f"{self._display_zoom_pct * 100:.0f}%")
        self._draw_selected_star_highlight()
        self._redraw_navigator()

    def _draw_selected_star_highlight(self):
        """Dashed circle around the Shift+Click-selected star, if any -
        drawn as an extra canvas item on top of the image _redraw_canvas
        just placed (canvas.delete("all") above already cleared any
        previous one, so this only ever adds at most one)."""
        if self._selected_star_key is None:
            return
        star = self._star_lookup(self._selected_star_key)
        if star is None:
            return
        x, y, fwhm, _amp, _color = star
        cx, cy = self._full_to_canvas(x, y)
        r = max(10.0, fwhm * 1.5 * self._display_zoom_pct)
        self.preview_canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline=PALETTE["accent_hover"], width=2, dash=(5, 3))

    def _redraw_navigator(self):
        """Small thumbnail of the whole image with a rectangle showing
        what's currently visible in the main preview - a real navigator,
        like Photoshop's. Click/drag inside it to pan the main view there."""
        canvas = self.nav_canvas
        if self._preview_rgb is None or self.full_shape is None:
            return
        ph, pw = self._preview_rgb.shape[:2]
        scale = min(NAV_MAX_W / pw, NAV_MAX_H / ph)
        thumb_w = max(1, int(round(pw * scale)))
        thumb_h = max(1, int(round(ph * scale)))
        img = Image.fromarray((np.clip(self._preview_rgb, 0, 1) * 255).astype(np.uint8))
        img = img.resize((thumb_w, thumb_h), Image.BILINEAR)
        self._nav_tkimg = ImageTk.PhotoImage(img)

        ox = (NAV_MAX_W - thumb_w) // 2
        oy = (NAV_MAX_H - thumb_h) // 2
        self._nav_geom = (ox, oy, thumb_w, thumb_h)

        canvas.delete("all")
        canvas.create_image(ox, oy, image=self._nav_tkimg, anchor="nw")

        # Viewport rectangle: same fractional [x0,x1] x [y0,y1] the main
        # scrollbars are set to - full coverage in Fit mode (the whole
        # image is visible), the current crop otherwise.
        if self.zoom_mode == "fit":
            fx0, fx1, fy0, fy1 = 0.0, 1.0, 0.0, 1.0
        else:
            cw = self.preview_canvas.winfo_width()
            ch = self.preview_canvas.winfo_height()
            if cw > 1 and ch > 1:
                x, y, crop_w, crop_h = self._compute_crop(cw, ch)
                fh, fw = self.full_shape
                fx0, fx1 = x / fw, (x + crop_w) / fw
                fy0, fy1 = y / fh, (y + crop_h) / fh
            else:
                fx0, fx1, fy0, fy1 = 0.0, 1.0, 0.0, 1.0

        rx0, rx1 = ox + fx0 * thumb_w, ox + fx1 * thumb_w
        ry0, ry1 = oy + fy0 * thumb_h, oy + fy1 * thumb_h
        canvas.create_rectangle(rx0, ry0, rx1, ry1, outline=PALETTE["accent"], width=2)

    def _on_nav_click(self, event):
        if self._nav_geom is None or self.full_shape is None or not self.loaded:
            return
        ox, oy, thumb_w, thumb_h = self._nav_geom
        fx = (event.x - ox) / max(1, thumb_w)
        fy = (event.y - oy) / max(1, thumb_h)
        fx = min(1.0, max(0.0, fx))
        fy = min(1.0, max(0.0, fy))
        self.view_cx, self.view_cy = fx, fy
        if self.zoom_mode == "fit":
            self.zoom_mode = "manual"
        self._redraw_canvas()
        self._schedule_hires_fetch()

    # ---------- Process (full resolution, background thread) ----------
    def _on_process(self):
        self.btn_process.config(state="disabled")
        self._busy_begin()
        self._siril_busy = True
        t = threading.Thread(target=self._process_thread, daemon=True)
        t.start()

    def _process_thread(self):
        try:
            vals = self._slider_values()
            spike_enabled = self.spike_enabled.get()
            stars = self._effective_stars()
            sparams = self._spike_config()

            if self._pristine_full is None:
                raise RuntimeError("No image loaded from Siril yet.")

            cur_shape = self.worker.get_shape()
            if cur_shape != self.full_shape:
                raise RuntimeError(
                    "The image active in Siril has changed since this script started "
                    f"(was {self.full_shape[1]}x{self.full_shape[0]}, now "
                    f"{cur_shape[1]}x{cur_shape[0]}). Run the script again.")

            self.queue.put(("status", "Process: applying adjustments..."))
            rgb_final = apply_cosmetics(self._pristine_full, *vals)

            if spike_enabled and stars:
                self.queue.put(("status", "Process: rendering diffraction spikes..."))
                fh, fw = self.full_shape
                layer = render_spike_layer((fh, fw), 0, 0, fw, fh, stars, sparams)
                rgb_final = apply_spikes(rgb_final, layer)

            self.queue.put(("status", "Process: applying to the active image in Siril..."))
            self.worker.push_rgb(rgb_final)

            self.queue.put(("status", "Done - applied to the active image in Siril. "
                                       "Keep adjusting and Process again if you want."))
            self.queue.put(("done", None))
        except Exception as e:
            self.queue.put(("error", format_error(e)))

    # ---------- Thread -> UI event queue ----------
    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "status":
                    self.status.set(payload)
                elif kind == "loaded":
                    (filename, self._pristine_full, self._src_preview_rgb,
                     self.full_shape, self._stars, size_calibration) = payload
                    self.active_filename.set(filename)
                    self._spike_disabled = set()
                    self._spike_forced = set()
                    self._spike_manual = []
                    self._manual_id_counter = 0
                    self._spike_star_overrides = {}
                    self._selected_star_key = None
                    self.loaded = True
                    self._siril_busy = False
                    self._hires_rgb = None
                    self._hires_wh = None
                    self.view_cx, self.view_cy = 0.5, 0.5
                    if size_calibration is not None:
                        self._apply_size_calibration(size_calibration)
                    self._busy_end()
                    self.btn_process.config(state="normal")
                    self._render_preview()
                    self._schedule_spike_preview()
                    if self.zoom_mode == "manual":
                        self._schedule_hires_fetch()
                elif kind == "hires":
                    gen, rgb, actual_wh = payload
                    self._hires_inflight = False
                    self._busy_end()
                    if rgb is not None and gen == self._hires_gen:
                        self._hires_rgb = rgb
                        self._hires_wh = actual_wh
                        self._redraw_canvas()
                elif kind == "spike_preview":
                    gen, layer, key = payload
                    self._spike_preview_inflight = False
                    self._busy_end()
                    if layer is not None and gen == self._spike_preview_gen:
                        self._spike_layer_preview = layer
                        self._spike_layer_key = key
                        self._compose_preview()
                        self._redraw_canvas()
                elif kind == "done":
                    self._busy_end()
                    self._siril_busy = False
                    self.btn_process.config(state="normal")
                    # Stays open on purpose: each Process call pushes an
                    # independent undo checkpoint in Siril (see push_rgb),
                    # so if the result isn't liked, the user can keep
                    # adjusting sliders and Process again as many times as
                    # they want - always re-applied from the untouched
                    # pristine source, never stacked on the previous result.
                elif kind == "error":
                    self._busy_end()
                    self._siril_busy = False
                    self.btn_process.config(state="normal")
                    messagebox.showerror("Error", payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)


def _make_dpi_aware():
    """On Windows, an app that doesn't declare DPI-awareness gets its
    click coordinates reported by Tk in a *scaled* coordinate space that
    doesn't line up 1:1 with real screen pixels whenever display scaling
    isn't 100% (125%/150% are extremely common) - every geometry formula
    in this script can be exactly right and a Ctrl+Click still lands off
    the star it looks like you clicked on. Must be called before the Tk
    root is created to take effect."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # per-process system DPI aware
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()  # older Windows fallback
    except Exception:
        pass


def main():
    _make_dpi_aware()
    try:
        worker = SirilWorker()
    except SirilConnectionError as e:
        print(f"Error connecting to Siril: {e}")
        return

    root = tk.Tk()
    root.title(f"frankSpikes {APP_VERSION} — by Frank Sferlazza")
    root.minsize(700, 500)
    # Kept as an attribute, not a local var: Tk only keeps a PhotoImage
    # alive as long as something in Python still references it, and a
    # bare local would be garbage-collected (silently reverting to the
    # default feather icon) as soon as main() moves on to mainloop().
    root._app_icon = ImageTk.PhotoImage(build_app_icon())
    root.iconphoto(True, root._app_icon)
    App(root, worker)
    # Size to the window's actual required content (computed only once all
    # widgets exist) rather than a fixed guess - a fixed guess is exactly
    # what let the bottom-right status bar labels get clipped once the
    # window had more content in it than when that guess was picked.
    # Height is then capped to what actually fits the screen: the two
    # sidebars' content (esp. the Diffraction Spikes column) can easily
    # need more vertical room than a laptop screen has, and each sidebar
    # already has its own working scrollbar (_make_scrollable_frame) for
    # exactly that case - growing the window past the screen instead just
    # forces the user to resize it manually before they can reach the
    # "Process" button or status bar.
    root.update_idletasks()
    req_w = max(1500, root.winfo_reqwidth())
    req_h = max(820, root.winfo_reqheight())
    max_h = max(700, root.winfo_screenheight() - 80)
    root.geometry(f"{req_w}x{min(req_h, max_h)}")
    root.mainloop()


if __name__ == "__main__":
    main()
