"""
frankSpikes - Siril GUI script (Python)
Author: Frank Sferlazza

Light/tone and color/hue adjustment tool for a single image, in the same
dark-themed style and with the same real full-resolution zoom/pan preview
as BB/NB Mixer.

Controls (left panel, "camera raw"-style, collapsible Base/Detail sections -
see TONE_PARAM_DEFS/apply_cosmetics):
Base
   - Temperature: blue/yellow color balance
   - Tint: green/magenta color balance (handy for removing the greenish
     light-pollution cast)
   - Exposure: brightens/darkens the whole image
   - Contrast: separates the subject from the background
   - Highlights: recovers or pushes just the brightest tonal region
     (e.g. a blown-out core), leaving midtones alone - a luminance-weighted
     mask, not a flat stretch (see Whites below for that)
   - Shadows: brightens or deepens just the darkest tonal region (e.g. the
     sky background), same masked approach as Highlights
   - Whites: sets the absolute white point - a flat stretch of the whole
     range, unlike Highlights above
   - Blacks: sets the absolute black point - a flat stretch of the whole
     range, unlike Shadows above
Detail
   - Texture: fine (small-radius) local contrast - grain/small-scale detail
   - Clarity: local (mid-tone) contrast on a large-radius unsharp mask,
     brings out nebula structure without touching global contrast
   - Dehaze: a much larger-radius local-contrast + saturation push, a
     simplified stand-in for removing (or, negative, adding) a soft haze/
     veil - real depth-aware dehazing needs more than a single image
   - Vibrance: boosts weaker colors more than already-saturated ones
     (protects reds like Ha from clipping), unlike a flat Saturation boost
   - Saturation: makes all colors more or less vivid, uniformly
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
     spike's length (seeded by the star's own position, so it never changes
     between re-renders) - breaks up the "stamped/CGI" look. Rotation is
     NOT jittered - a real spike's angle comes from the telescope's own
     spider vanes, identical for every star in the frame
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
   - Diffraction rainbow (per anchor): the physical colour pattern of a
     real spike - it starts in the star's own colour, then (further out)
     breaks into short coloured segments with dimmer gaps (a spider vane's
     wavelength-dependent diffraction nulls), washing back to neutral
     after a few segments. 0 = the star's own colour all the way out.
   - Rainbow segment spacing (global, px): the distance between those
     segments - set by the optics, so the same for every star (bigger
     stars, with longer spikes, simply show more of them).
   - Spikes keep their width along their whole length and fade with a
     long power-law tail (plus a slight, irregular brightness flicker),
     as in real photos, rather than tapering to a needle point.
   - Color saturation (per anchor): 0 keeps that size of star's spike rays
     pure white regardless of its own colour or the other color sliders.
   - Flare reach (per anchor, % of the spike length): how far the Soft
     flare and its rays extend. They start right at the star's visible
     edge (so even a short reach shows outside the core) and never reach
     past the spike tips; unlike the strengths, this keeps its value
     across Simple mode's size ramp.
   - Flare color saturation (per anchor): a separate 0-100 control for the
     Soft flare and Ring flare glow's own colour, independent of
     the spike rays' Color saturation above - 0 (the default) keeps the
     original pure white glow, 100 tints it fully toward the star's own
     colour.
   - Ring flare diameter (per anchor, x star diameter): the ring's own
     diameter relative to the star's, so it hugs the star - 1.6x (the
     default) sits just past its edge. Always kept outside the core and
     inside the spikes, second Airy ring included.
   - Flare rays (per anchor): breaks the Soft flare glow up into the
     soft, irregular streaks of a real sunburst - the same halo light
     redistributed into rays (more of them further out, as they branch),
     with the strongest ones hugging each main spike as faint secondary
     spikes. 0 = a plain round glow.
   - Flare ray symmetry (global): how strictly that ray pattern repeats in
     every wedge between main spikes - 100 = exactly (the spider geometry
     repeats around the aperture), 0 = fully irregular (scatter/seeing
     don't repeat); real photos sit in between.
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
   Close the window whenever you're happy with the result - if some
   edits haven't been applied to Siril yet, it asks before closing.
"""

import os
import sys
import math
import threading
import queue
import traceback
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageTk

# sirilpy is Siril's own bundled package, not something a plain "pip
# install" can ever provide (it isn't on PyPI) - a standalone install
# (see packaging/standalone/) never has it, and shouldn't need to: this
# makes the import optional, and gives main() the exact same
# SirilConnectionError a running-but-unreachable Siril would raise, so
# "sirilpy isn't installed" and "Siril isn't running" fall back to
# FileWorker (standalone mode) the exact same way instead of crashing
# before main() ever runs.
try:
    import sirilpy as s
    from sirilpy import SirilConnectionError
except ImportError:
    s = None

    class SirilConnectionError(Exception):
        pass

APP_VERSION = "2.4.1"
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
    # ---- Soft flare (grouped together) ----
    ("soft_flare", "Soft flare",                          0,   100, 5,   "{:.0f}"),
    ("flare_reach", "Flare reach (% of spike length)",    10,  100, 5,   "{:.0f}%"),
    ("flare_rays", "Flare rays (sunburst structure)",     0,   100, 5,   "{:.0f}"),
    # ---- Ring flare (grouped together) ----
    ("ring_flare", "Ring flare",                          0,   100, 5,   "{:.0f}"),
    ("ring_diam",  "Ring flare diameter (x star diameter)", 1.0, 6, 0.1, "{:.1f}x"),
    # Shared by both flares above (see _spike_color_mult's use in the
    # soft/ring flare block of render_spike_layer) - kept right after
    # them rather than off on its own.
    ("flare_saturation", "Flare color saturation",        0,   100, 5,   "{:.0f}"),
    ("rainbow",    "Diffraction rainbow",                 0,   100, 5,   "{:.0f}"),
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
_SPIKE_PARAM_DEFS_BY_KEY = {k: (label, lo, hi, step, fmt)
                            for k, label, lo, hi, step, fmt in SPIKE_ANCHOR_PARAM_DEFS}
# Which collapsible section (see App._make_collapsible/_build_grouped_anchor_
# sliders) each per-anchor slider belongs in - "diam" isn't in here, it's
# shown above both sections rather than inside either (it's a "which star
# size is this tab" selector, not really a Rays or Flare look parameter).
SPIKE_PARAM_GROUPS = ("rays", "flare")
SPIKE_PARAM_GROUP_TITLES = {"rays": "Rays", "flare": "Flares"}
_SPIKE_PARAM_GROUP = {
    "length": "rays", "intensity": "rays", "thickness": "rays",
    "rainbow": "rays", "saturation": "rays",
    "soft_flare": "flare", "flare_reach": "flare",
    "ring_flare": "flare", "ring_diam": "flare",
    "flare_saturation": "flare",
    "flare_rays": "flare",
}


def spike_anchor_slider_range(tab_index, key):
    """(lo, hi) a given per-size tab's slider for `key` actually spans -
    the same math _build_ui uses to construct the widgets, exposed so
    other code (the Uniform -> Per-size seeding hand-off, the per-image
    auto-calibration) can clamp values it sets into range instead of
    silently exceeding what the slider can display."""
    if key == "diam":
        return SPIKE_ANCHOR_DIAM_RANGES[tab_index]
    lo, hi = _SPIKE_ANCHOR_PARAM_FULL_RANGE[key]
    if key in _SPIKE_GEOMETRY_KEYS or key in _SPIKE_COLOUR_KEYS:
        return lo, hi
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

# A real diffraction spike's absolute (angular/pixel) size is set by the
# aperture and wavelength, essentially independent of focal length - but
# "Spike length" here is expressed "in star diameters" (the PSF's own
# size), and a shorter focal length spreads that same star over fewer
# pixels (a smaller plate scale), so the same physical spike spans MORE
# star-diameters at short focal length than at long. Two calibration
# points, log-log interpolated (and extrapolated a bit beyond them,
# clamped so it never goes absurd): a short (~300mm, e.g. a small
# refractor) focal length reads roughly 8x, a medium one (~800mm, e.g. a
# small SCT/Newtonian) roughly 3x - both from real reference photos, not a
# closed-form optical derivation (this whole tool is stylized/artistic,
# not physically exact).
_FOCAL_LENGTH_REF1_MM, _FOCAL_LENGTH_REF1_LEN = 300.0, 8.0
_FOCAL_LENGTH_REF2_MM, _FOCAL_LENGTH_REF2_LEN = 800.0, 3.0
_FOCAL_LENGTH_LEN_MIN, _FOCAL_LENGTH_LEN_MAX = 1.5, 10.0


def _focal_length_scale_factor(focal_mm, ref1_scale, ref2_scale, lo=None, hi=None):
    """Log-log interpolation (and, beyond the two references, extrapolation
    - clamped to [lo, hi] when given) between a scale factor at
    _FOCAL_LENGTH_REF1_MM (short) and one at _FOCAL_LENGTH_REF2_MM (medium)
    - the same two reference focal lengths _focal_length_to_spike_length
    uses, so every focal-length-derived default (Length, Thickness,
    Intensity, the Minimum diameter cutoff) moves on one consistent curve
    instead of each picking its own. A scale factor of 1.0 means "today's
    hand-tuned default, unchanged" - these are relative multipliers, not
    the absolute values _focal_length_to_spike_length returns. None for an
    invalid/unknown focal length, same as that function."""
    if not focal_mm or focal_mm <= 0:
        return None
    t = ((math.log(focal_mm) - math.log(_FOCAL_LENGTH_REF1_MM))
         / (math.log(_FOCAL_LENGTH_REF2_MM) - math.log(_FOCAL_LENGTH_REF1_MM)))
    log_scale = math.log(ref1_scale) + t * (math.log(ref2_scale) - math.log(ref1_scale))
    scale = math.exp(log_scale)
    if lo is not None:
        scale = max(lo, scale)
    if hi is not None:
        scale = min(hi, scale)
    return scale


def _focal_length_to_spike_length(focal_mm):
    """See the note above - returns None for an invalid/unknown focal
    length (0, negative, or missing), leaving the caller's hand-tuned
    defaults untouched."""
    return _focal_length_scale_factor(
        focal_mm, _FOCAL_LENGTH_REF1_LEN, _FOCAL_LENGTH_REF2_LEN,
        _FOCAL_LENGTH_LEN_MIN, _FOCAL_LENGTH_LEN_MAX)


# Thickness and Intensity aren't expressed "in star diameters" the way
# Length is, so they don't automatically track the smaller absolute star
# size a shorter focal length produces - Thickness (an absolute pixel
# width) is scaled down a little at short focal length so the now-longer
# default spike still reads as a thin, elegant needle rather than a thick
# bar; Intensity is scaled up a little to match the bolder, more dramatic
# look real short-focal-length wide-field photos tend to show. Both are
# mild (unlike Length's 8x/3x swing) since over- or under-shooting either
# is much more visually obvious than a length difference.
_FOCAL_LENGTH_THICKNESS_SCALE_REFS = (0.85, 1.0)
_FOCAL_LENGTH_INTENSITY_SCALE_REFS = (1.15, 1.0)
_FOCAL_LENGTH_THICKNESS_SCALE_BOUNDS = (0.6, 1.2)
_FOCAL_LENGTH_INTENSITY_SCALE_BOUNDS = (0.8, 1.6)
# The Minimum star diameter cutoff is already calibrated per-image from
# the real detected star sizes (see _reload_thread's size_calibration) -
# self-adjusting for a shorter focal length's smaller stars without any
# focal-length math at all. What focal length DOES still usefully inform:
# how choosy that cutoff should be. "Diffraction spikes belong on the
# biggest/brightest stars" holds at any focal length, but a short one
# packs proportionally more small stars into the same cutoff band (a
# coarser plate scale compresses the whole field's real size range into
# fewer pixels), so the same percentile-based cutoff lets relatively more
# of them through - scaled up a little here to stay selective.
_FOCAL_LENGTH_MIN_DIAM_SCALE_REFS = (1.3, 1.0)
_FOCAL_LENGTH_MIN_DIAM_SCALE_BOUNDS = (1.0, 1.6)


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
    # How strictly the soft flare's ray pattern ("flare_rays") repeats in
    # every wedge between main spikes: 100 = exactly (the spider geometry
    # repeats around the aperture), 0 = every copy independently perturbed
    # (scatter/seeing don't repeat). Reference photos sit in between -
    # irregular spacing, but the strongest rays still hug every spike.
    "flare_symmetry": 40.0,
    # Diffraction rainbow segment spacing, in full-resolution px: the
    # distance along a spike between successive nulls of the vane's own
    # diffraction pattern (P = wavelength * focal length / (vane width *
    # pixel size) - a property of the optics, so one value for every star
    # in the frame, NOT a fraction of each spike's length). Measured on
    # real reference photos: ~20-60px. See _diffraction_mult.
    "rainbow_period": 40.0,
    "anchors": [
        {"diam": 3.0, "length": 2.0, "intensity": 40.0, "thickness": 0.8,
         "soft_flare": 0.0, "flare_reach": 45.0, "ring_flare": 0.0, "ring_diam": 1.6,
         "flare_saturation": 55.0, "flare_rays": 0.0,
         "rainbow": 0.0, "saturation": 55.0},
        {"diam": 8.0, "length": 4.0, "intensity": 110.0, "thickness": 1.1,
         "soft_flare": 11.0, "flare_reach": 45.0, "ring_flare": 7.0, "ring_diam": 1.6,
         # flare_saturation matches this anchor's own (spike ray) saturation
         # - the soft/ring flare glow used to stay pure white by default
         # (flare_saturation=0) while only the thin rays picked up the
         # star's colour, so a colourful ray met a white halo right where
         # they overlap near the star - the exact spot most likely to catch
         # the eye. Matching them keeps the whole star - halo and spikes -
         # one coherent, visibly-tinted colour instead of a white core with
         # a colour fringe (confirmed: a yellow star's white-to-yellow seam
         # there read as a muddy sepia, not a clean yellow star).
         "flare_saturation": 85.0, "flare_rays": 35.0,
         # Every spike starts in the star's own colour; "rainbow" only
         # adds the physical diffraction segments further out (see
         # _diffraction_mult), whose spacing is the global
         # "rainbow_period" - so a Medium star, whose spike is only a
         # couple of periods long, shows just the first coloured band or
         # two, while a Large one shows more.
         "rainbow": 40.0, "saturation": 85.0},
        {"diam": 18.0, "length": 6.5, "intensity": 170.0, "thickness": 1.6,
         "soft_flare": 35.0, "flare_reach": 45.0, "ring_flare": 20.0, "ring_diam": 1.6,
         "flare_saturation": 95.0, "flare_rays": 45.0,
         "rainbow": 60.0, "saturation": 95.0},
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
    "soft_flare": 15.0, "flare_reach": 45.0, "ring_flare": 5.0, "ring_diam": 1.6,
    "flare_saturation": 75.0, "flare_rays": 40.0,
    "rainbow": 45.0, "saturation": 75.0,
}


def compute_focal_calibration(focal_mm):
    """The single source of truth for every focal-length-derived spike
    default - used both by App._reload_thread (right after loading an
    image) and by the Magic Wand button (App._on_magic_wand, to reapply it
    on demand). Returns a dict with "length_scale"/"thickness_scale"/
    "intensity_scale"/"diam_scale", each either a float multiplier (1.0 =
    today's hand-tuned default, unchanged) or None if focal_mm is falsy/
    invalid - see _focal_length_to_spike_length and
    _focal_length_scale_factor for what each one means."""
    if not focal_mm or focal_mm <= 0:
        return {"length_scale": None, "thickness_scale": None,
                "intensity_scale": None, "diam_scale": None}
    target_uniform_length = _focal_length_to_spike_length(focal_mm)
    return {
        "length_scale": target_uniform_length / SPIKE_UNIFORM_DEFAULTS["length"],
        "thickness_scale": _focal_length_scale_factor(
            focal_mm, *_FOCAL_LENGTH_THICKNESS_SCALE_REFS, *_FOCAL_LENGTH_THICKNESS_SCALE_BOUNDS),
        "intensity_scale": _focal_length_scale_factor(
            focal_mm, *_FOCAL_LENGTH_INTENSITY_SCALE_REFS, *_FOCAL_LENGTH_INTENSITY_SCALE_BOUNDS),
        "diam_scale": _focal_length_scale_factor(
            focal_mm, *_FOCAL_LENGTH_MIN_DIAM_SCALE_REFS, *_FOCAL_LENGTH_MIN_DIAM_SCALE_BOUNDS),
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
    style.configure("CardHeading.TLabel", background=P["panel"], foreground=P["accent"],
                     font=FONT_CARD_TITLE)
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


# ---------------------------------------------------------------------------
# Left panel ("camera raw"-style) tone/color controls: Base and Detail
# groups for now (Tone Curve and HSL/Color Mixer are separate, larger
# additions - see the module's own history/commits). Table-driven, same
# pattern as SPIKE_ANCHOR_PARAM_DEFS/_SPIKE_PARAM_GROUP/
# _build_grouped_anchor_sliders: one definition drives the tk.Var setup,
# the collapsible-section UI and _update_all_labels, instead of one
# hand-written line per parameter in each of those three places.
# ---------------------------------------------------------------------------
TONE_PARAM_DEFS = [
    ("temperature", "Temperature (cool / warm)", -50, 50, 0.5, "{:.1f}"),
    ("tint",        "Tint (green / magenta)",     -50, 50, 0.5, "{:.1f}"),
    ("exposure",    "Exposure",                   -100, 100, 1, "{:.0f}"),
    ("contrast",    "Contrast",                   -100, 100, 1, "{:.0f}"),
    ("highlights",  "Highlights",                 -100, 100, 1, "{:.0f}"),
    ("shadows",     "Shadows",                    -100, 100, 1, "{:.0f}"),
    ("whites",      "Whites",                     -100, 100, 1, "{:.0f}"),
    ("blacks",      "Blacks",                     -100, 100, 1, "{:.0f}"),
    ("texture",     "Texture",                    -100, 100, 1, "{:.0f}"),
    ("clarity",     "Clarity",                    -100, 100, 1, "{:.0f}"),
    ("dehaze",      "Dehaze",                      -100, 100, 1, "{:.0f}"),
    ("vibrance",    "Vibrance",                   -100, 100, 1, "{:.0f}"),
    ("saturation",  "Saturation",                 -100, 100, 1, "{:.0f}"),
]
TONE_PARAM_GROUPS = ("base", "detail")
TONE_PARAM_GROUP_TITLES = {"base": "Base", "detail": "Detail"}
_TONE_PARAM_GROUP = {
    "temperature": "base", "tint": "base", "exposure": "base", "contrast": "base",
    "highlights": "base", "shadows": "base", "whites": "base", "blacks": "base",
    "texture": "detail", "clarity": "detail", "dehaze": "detail",
    "vibrance": "detail", "saturation": "detail",
}
TONE_DEFAULTS = {k: 0.0 for k, *_r in TONE_PARAM_DEFS}

# White balance solved as the exact inverse of apply_cosmetics' own
# temperature/tint formula (see compute_auto_tone) - kept as named
# constants so the two stay in lockstep if that formula's own 0.15/0.5
# factors are ever retuned.
_WB_TEMP_TINT_STEP = 0.15
_WB_TINT_CROSS_TERM = 0.5
# Levels (Blacks/Whites) solved as the exact inverse of apply_cosmetics'
# own black/white-point formula.
_LEVELS_STEP = 0.3
_AUTO_LEVELS_STRENGTH = 0.5  # 1.0 = textbook auto-levels (see compute_auto_tone)


def compute_auto_tone(rgb):
    """A conservative "auto white balance + auto levels" pass for the
    Magic Wand button - meant to correct an objective light-pollution
    color cast and a poorly-stretched black/white point, not to
    reinterpret the image artistically. Returns a dict with just
    "temperature"/"tint"/"blacks"/"whites" set (TONE_PARAM_DEFS keys, -100
    ..100 scale) - Highlights/Shadows/Texture/Clarity/Dehaze/Vibrance/
    Saturation are deliberately left for the caller to leave alone, since
    "should this nebula pop more" is a taste call this function has no
    business making ("rendendola naturale, senza snaturarla").

    White balance is gray-world (equalizing the R/G/B means) but only over
    the darkest quartile of pixels - a proxy for sky background, where any
    color cast is light pollution, not real nebula/star color; gray-
    -worlding the WHOLE image would just as happily wash out a genuine red
    Halpha region. Levels stretches the 0.5th/99.5th luminance percentiles
    toward (but not all the way to) black/white, gently rather than
    clipping real detail.

    Both are solved as the exact algebraic inverse of apply_cosmetics' own
    temperature/tint and blacks/whites formulas (evaluated at the
    background pixels' actual mean color, respectively the image's actual
    dark/bright percentiles) rather than an iterative fit - cheap, and
    exact for what it's targeting."""
    luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]

    bg_thresh = np.percentile(luma, 25)
    bg_mask = luma <= max(bg_thresh, 1e-6)
    if np.count_nonzero(bg_mask) < 100:
        bg_mask = np.ones_like(luma, dtype=bool)  # fallback: a tiny/flat image
    r_mean = float(np.mean(rgb[..., 0][bg_mask]))
    g_mean = float(np.mean(rgb[..., 1][bg_mask]))
    b_mean = float(np.mean(rgb[..., 2][bg_mask]))

    # Solve temp_shift/tint_shift so R'=B'=G' at the background's own mean
    # color - see apply_cosmetics' R'=R+temp+0.5*tint, G'=G-tint,
    # B'=B-temp+0.5*tint (temp/tint here are already /100*0.15, i.e.
    # "shift", not the raw slider value).
    temp_shift = (b_mean - r_mean) / 2.0
    tint_shift = (g_mean - r_mean - temp_shift) / 1.5
    temperature = max(-50.0, min(50.0, temp_shift / _WB_TEMP_TINT_STEP * 100.0))
    tint = max(-50.0, min(50.0, tint_shift / _WB_TEMP_TINT_STEP * 100.0))

    # 0.1/99.9 rather than the more common 0.5/99.5: a sparse star field
    # (plenty of real astro images - most of the frame is background, only
    # a small fraction of pixels are actual stars) can have well under
    # 0.5% genuinely bright pixels, which would otherwise put the "white
    # point" percentile back in the background noise instead of on any
    # real star - 99.9 only needs 0.1% to register correctly. Damped to
    # half-strength on top of that: solving for the percentile to land
    # EXACTLY at 0/1 is the textbook "auto levels" formula, but it's too
    # heavy-handed as a one-click default - a well-exposed image that's
    # merely a bit low-contrast (most real, already-processed frames)
    # would otherwise get pushed all the way to a hard clip. Half strength
    # nudges toward better levels without overriding a deliberate prior
    # stretch.
    lo_pct, hi_pct = np.percentile(luma, [0.1, 99.9])
    bp = max(-_LEVELS_STEP, min(_LEVELS_STEP, float(lo_pct))) * _AUTO_LEVELS_STRENGTH
    blacks = bp / _LEVELS_STEP * 100.0
    wp = (float(hi_pct) - bp) / max(1e-6, 1.0 - bp)
    wp = 1.0 - (1.0 - wp) * _AUTO_LEVELS_STRENGTH
    wp = max(1e-6, min(1.5, wp))
    whites = (1.0 - wp) / _LEVELS_STEP * 100.0
    whites = max(-100.0, min(100.0, whites))

    return {"temperature": temperature, "tint": tint, "blacks": blacks, "whites": whites}



# ---------------------------------------------------------------------------
# Magic Wands - two buttons, one job each: the Camera RAW one (left panel)
# only touches the tone sliders, the spike one (spike panel, also run
# automatically when an image loads) only the spike sliders.
# Tone: a conservative finishing pass for an ALREADY-PROCESSED image -
# analyse it (background cast/level, saturated cores, noise, colour) and set:
#   Temperature/Tint and Blacks/Whites from an automatic white balance on
#   the sky and black/white points (compute_auto_tone; the black point
#   solved after Shadows so the sky stays dark), plus Highlights -5..-15
#   (protect cores), Shadows +5..+12 and Texture +5..+10 (less when
#   noisy), Clarity/Dehaze 0, Vibrance +8..+15, Saturation 0.
# Spikes (Per size mode - see magic_wand_spikes), scaled by the declared or
#   estimated focal length: Minimum diameter 3 (short) -> 10px
#   (long, but only the ~12% biggest stars ever pass), Sharpness 95 -> 55, Length 12x -> 8x, Intensity 130 -> 165,
#   Thickness 0.6 -> 1.0, plus fixed Natural variation 15, Twinkle 15,
#   Diffraction rainbow 40, Color saturation 70, Soft flare 15, Flare
#   reach 40%.
# Everything is measured on the untouched source, so pressing it twice
# gives the same result. Pure functions below; App._on_magic_wand and
# App._apply_spike_wand apply them.
# ---------------------------------------------------------------------------

# Focal-length scale of the spike mapping: t = 0 at/below the short end,
# 1 at/above the long end, log-interpolated in between.
MAGIC_WAND_FOCAL_SHORT_MM = 50.0
MAGIC_WAND_FOCAL_LONG_MM = 1000.0
# Representative focal lengths for an ESTIMATED field type (no FOCALLEN).
_FIELD_TYPE_FOCAL_MM = {"wide": 35.0, "medium": 300.0, "long": 1200.0}
_FIELD_TYPE_LABEL = {"wide": "wide field / astro-landscape (< 100mm)",
                     "medium": "medium field (100-750mm)",
                     "long": "long-focal deep sky (> 750mm)"}


def _field_type_for_focal(focal_mm):
    if focal_mm < 100.0:
        return "wide"
    if focal_mm <= 750.0:
        return "medium"
    return "long"


def estimate_field_type(focal_mm, stars, image_shape):
    """(field_type, focal_mm, source, reasons): the declared focal length
    (FITS FOCALLEN) when there is one, otherwise a rough guess from the
    detected stars - how big they are (median FWHM in px) and how densely
    they fill the frame, plus whether the bottom of the frame is nearly
    starless (a landscape foreground). A pixel-based guess can't know the
    real plate scale or seeing, so it's reported as an estimate of the
    field TYPE, with its representative focal length, not a measurement."""
    if focal_mm and focal_mm > 0:
        ftype = _field_type_for_focal(float(focal_mm))
        return ftype, float(focal_mm), "declared", [f"FOCALLEN = {focal_mm:.0f}mm in the file header"]
    h, w = image_shape[:2]
    reasons = []
    if not stars:
        return "medium", _FIELD_TYPE_FOCAL_MM["medium"], "estimated", ["no stars detected - assuming a medium field"]
    fwhm = np.array([s[2] for s in stars], dtype=np.float64)
    ys = np.array([s[1] for s in stars], dtype=np.float64)
    med = float(np.median(fwhm))
    density = len(stars) / max(h * w / 1e6, 1e-6)
    n_top = int(np.count_nonzero(ys < 0.25 * h))
    n_bottom = int(np.count_nonzero(ys > 0.75 * h))
    reasons.append(f"median star FWHM {med:.1f}px, {density:.0f} detected stars per megapixel")
    if n_top >= 20 and n_bottom < 0.25 * n_top:
        reasons.append(f"nearly starless bottom quarter ({n_bottom} stars vs {n_top} at the top) "
                       f"- looks like a landscape foreground")
        ftype = "wide"
    elif med <= 3.0 and density >= 250:
        reasons.append("many small, tightly packed stars")
        ftype = "wide"
    elif med >= 5.0 or density < 60:
        reasons.append("large and/or sparse stars")
        ftype = "long"
    else:
        ftype = "medium"
    return ftype, _FIELD_TYPE_FOCAL_MM[ftype], "estimated", reasons


def _subsample(rgb, max_px=2_000_000):
    h, w = rgb.shape[:2]
    step = max(1, int(np.ceil(np.sqrt(h * w / max_px))))
    return rgb[::step, ::step]


def analyze_image_tone(full_rgb):
    """Measurements the Camera RAW part of the Magic Wand is based on, all
    on the untouched (H,W,3) float01 source: background (the darkest 40%
    of pixels - mostly sky) level and colour cast, the share of near-
    saturated pixels (star/galaxy/nebula cores), background noise relative
    to its level (on a full-resolution crop - a downsampled preview hides
    it), and the mean colour saturation of the brighter (subject) pixels."""
    rgb = _subsample(np.asarray(full_rgb, dtype=np.float32))
    luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    p40, p60 = np.percentile(luma, [40, 60])
    bg = luma <= p40
    bg_rgb = [float(np.mean(rgb[..., c][bg])) for c in range(3)]
    bg_level = float(np.median(luma[bg]))
    ref = max(bg_level, 0.02)
    r, g, b = bg_rgb
    # relative to the sky level, and zeroed when negligible in absolute
    # terms (a "40% cast" on a nearly black sky is invisible)
    green_cast = (g - (r + b) / 2.0) / ref if abs(g - (r + b) / 2.0) > 0.004 else 0.0
    warm_cast = (r - b) / ref if abs(r - b) > 0.004 else 0.0
    hi_frac = float(np.mean(luma > 0.90))
    clip_frac = float(np.mean(luma >= 0.995))
    maxc, minc = rgb.max(axis=-1), rgb.min(axis=-1)
    subject_sat = float(np.mean((maxc - minc)[luma > p60])) if np.any(luma > p60) else 0.0

    # noise: robust sigma of the fine high-pass on the background of a
    # full-resolution central crop
    full = np.asarray(full_rgb, dtype=np.float32)
    fh, fw = full.shape[:2]
    ch, cw = min(fh, 1024), min(fw, 1024)
    y0, x0 = (fh - ch) // 2, (fw - cw) // 2
    crop = full[y0:y0 + ch, x0:x0 + cw]
    cl = 0.299 * crop[..., 0] + 0.587 * crop[..., 1] + 0.114 * crop[..., 2]
    hp = cl - _gaussian_blur(cl, 2)
    cbg = cl <= np.percentile(cl, 40)
    vals = hp[cbg] if np.count_nonzero(cbg) > 50 else hp.ravel()
    sigma = 1.4826 * float(np.median(np.abs(vals - np.median(vals))))
    noise_rel = sigma / ref

    # Tint that would fully neutralise the background's green cast (the
    # inverse of apply_cosmetics' tint formula), for the report only.
    neutral_tint = (g - (r + b) / 2.0) / 1.5 / _WB_TEMP_TINT_STEP * 100.0
    neutral_temp = (b - r) / 2.0 / _WB_TEMP_TINT_STEP * 100.0
    return {"bg_level": bg_level, "bg_rgb": bg_rgb, "green_cast": green_cast,
            "warm_cast": warm_cast, "hi_frac": hi_frac, "clip_frac": clip_frac,
            "noise_rel": noise_rel, "subject_sat": subject_sat,
            "neutral_tint": neutral_tint, "neutral_temperature": neutral_temp}


def _lerp01(x, lo, hi):
    """0 at/below lo, 1 at/above hi, linear in between."""
    return float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))


def magic_wand_tone(a, rgb):
    """Camera RAW slider values for the Magic Wand, in two layers:
    - the objective corrections compute_auto_tone makes: Temperature/Tint
      neutralising the sky background's colour cast (light pollution, not
      real nebula/star colour) and Blacks/Whites setting the black/white
      points;
    - the finishing moves from analyze_image_tone's measurements, each in a
      narrow conservative range: Highlights -5..-15 (protect cores),
      Shadows +5..+12 and Texture +5..+10 (less when noisy), Vibrance
      +8..+15, Clarity/Dehaze/Saturation 0.
    Blacks/Whites are solved AFTER Highlights/Shadows (on the image as they
    leave it): this app's Shadows lifts everything below mid-grey, sky
    included, so the black point has to re-anchor the sky - Shadows then
    only opens up the faint signal above it instead of washing the
    background out. rgb is the (subsampled) untouched source.
    NB this app's Blacks raises the black point for POSITIVE values
    (darker sky), the opposite of Lightroom's sign."""
    noisy = _lerp01(a["noise_rel"], 0.08, 0.35)
    finishing = {
        "highlights": float(-round(5 + 10 * _lerp01(a["hi_frac"], 0.0005, 0.02))),
        "shadows": float(round(12 - 7 * noisy)),
        "texture": float(round(10 - 5 * noisy)),
        "clarity": 0.0,
        "dehaze": 0.0,
        "vibrance": float(round(15 - 7 * _lerp01(a["subject_sat"], 0.05, 0.30))),
        "saturation": 0.0,
    }
    wb = compute_auto_tone(rgb)
    tone = {"temperature": round(wb["temperature"], 1), "tint": round(wb["tint"], 1)}
    shaped = apply_cosmetics(rgb, {**tone, "highlights": finishing["highlights"],
                                   "shadows": finishing["shadows"]})
    levels = compute_auto_tone(shaped)
    tone["blacks"] = float(round(levels["blacks"]))
    tone["whites"] = float(round(levels["whites"]))
    tone.update(finishing)
    return tone


# Share of detected stars the Magic Wand lets through its size cutoff: the
# spike effect is for the stars that stand out, not the whole field.
MAGIC_WAND_SPIKED_FRACTION = 0.12
# In Simple mode a star at this multiple of the Minimum diameter gets 10%
# of the full look (log-diameter smoothstep ramp from 0 at 1x to full at
# SPIKE_UNIFORM_REF_MULT x, see _interp_anchor_params) - "a noticeable
# spike" for the Magic Wand's crowding limit.
_SIMPLE_NOTICEABLE_MULT = SPIKE_UNIFORM_REF_MULT ** 0.196


def _magic_wand_cutoff(fwhm, target):
    """(cutoff, note): the smallest star size that lets at most
    MAGIC_WAND_SPIKED_FRACTION of the stars through (the renderer spikes
    fwhm >= cutoff), raised to the focal-length target when that's more
    selective, but never above the biggest star. Chosen among the DISTINCT
    sizes present - detectors report sizes in coarse steps, and a cutoff
    equal to a size shared by most of the field would let all of them in.
    If no size is rare enough (every star the same size), nothing stands
    out: the cutoff goes just past the biggest star, leaving Twinkle."""
    fwhm = np.asarray(fwhm, dtype=np.float64)
    n = len(fwhm)
    distinct = np.unique(fwhm)
    ok = [c for c in distinct if np.count_nonzero(fwhm >= c) <= MAGIC_WAND_SPIKED_FRACTION * n]
    if not ok:
        return float(distinct[-1]) + 1.0, "no star stands out in size - only Twinkle hints"
    c = float(ok[0])
    if target > c:
        c = min(target, float(distinct[-1]))
    return c, None


def magic_wand_spikes(focal_mm, stars, current_rotation):
    """Spike settings from the (declared or estimated) focal length and the
    image's own stars: (globals, anchors, simple, info) - `anchors` for Per
    size mode, `simple` for Simple mode (the App writes whichever mode is
    active). Per size fits this best: its Small tab diameter is the cutoff (stars below it get no spike,
    stars at it already get Small's own look) independently of where the
    full look is reached - in Simple mode one number is both the cutoff
    and the start of a ramp from zero to full at 4x it, so "only the
    standout stars" and "clearly visible spikes on them" can't both hold.
    Focal length sets the look (short -> long): cutoff target 3 -> 10px,
    Sharpness 95 -> 55, Length 12x -> 8x, Intensity 130 -> 165, Thickness
    0.6 -> 1.0; Medium and Large get those values, Small (the smallest
    spiked stars) about half the length/intensity. Each value is clamped
    to its tab's slider range (see spike_anchor_slider_range)."""
    t = _lerp01(np.log(focal_mm), np.log(MAGIC_WAND_FOCAL_SHORT_MM), np.log(MAGIC_WAND_FOCAL_LONG_MM))
    target = 3.0 + 7.0 * t
    rotation = current_rotation if 0.0 <= current_rotation <= 45.0 else 30.0
    globals_ = {"sharpness": float(round(95 - 40 * t)), "variation": 15.0,
                "twinkle": 15.0, "rotation": float(rotation)}
    look = {"length": round(12.0 - 4.0 * t, 1),
            "intensity": float(5 * round((130 + 35 * t) / 5)),
            "thickness": round(0.6 + 0.4 * t, 1),
            "rainbow": 40.0, "saturation": 70.0,
            "soft_flare": 15.0, "flare_reach": 40.0}
    small_look = dict(look, length=round(look["length"] * 0.5, 1),
                      intensity=float(5 * round(look["intensity"] * 0.5 / 5)),
                      rainbow=20.0, soft_flare=8.0)

    if stars:
        fwhm = np.array([s[2] for s in stars], dtype=np.float64)
        cutoff, note = _magic_wand_cutoff(fwhm, target)
        top = float(fwhm.max())
        n_spiked = int(np.count_nonzero(fwhm >= cutoff))
        n_stars = len(fwhm)
    else:
        cutoff, note, top, n_spiked, n_stars = target, None, target * 3.0, 0, 0
    large_d = max(top, cutoff * 2.0)
    diams = (cutoff, (cutoff * large_d) ** 0.5, large_d)

    anchors, clamped = [], set()
    for tab, (d, lk) in enumerate(zip(diams, (small_look, look, look))):
        vals = {"diam": d, **lk}
        out = {}
        for k, v in vals.items():
            lo, hi = spike_anchor_slider_range(tab, k)
            cv = float(np.clip(v, lo, hi))
            if k != "diam" and abs(cv - v) > 1e-9:
                clamped.add(f"{SPIKE_ANCHOR_TAB_LABELS[tab]} {k}")
            # the cutoff rounds UP, so rounding never lets more stars in
            out[k] = (math.ceil(cv * 10.0 - 1e-9) / 10.0 if (k == "diam" and tab == 0)
                      else round(cv, 1))
        anchors.append(out)
    if stars:   # counted against the final (rounded) cutoff the renderer will use
        n_spiked = int(np.count_nonzero(fwhm >= anchors[0]["diam"]))

    # Simple mode: one slider set with the full look, and a Minimum
    # diameter that is both the cutoff and where the ramp to that look
    # starts (0 at it, half strength at 2x, full at SPIKE_UNIFORM_REF_MULT
    # x). Between two limits on this image's own star sizes, the focal
    # length target is used as far as they allow: not so low that more
    # than MAGIC_WAND_SPIKED_FRACTION of the stars get a noticeable
    # (>= 10% strength, i.e. >= ~1.31x the minimum) spike, not so high
    # that the biggest 2% of stars miss half strength - visibility wins if
    # the two conflict (a narrow size spread).
    lo_d, hi_d = SPIKE_ANCHOR_DIAM_RANGES[0]
    if stars and note is None:
        # whole px (the slider's step): each limit rounded on its own safe
        # side, so rounding can't undo it
        crowd_floor = math.ceil(float(np.percentile(fwhm, 100 * (1 - MAGIC_WAND_SPIKED_FRACTION)))
                                / _SIMPLE_NOTICEABLE_MULT - 1e-9)
        visible_cap = max(1, math.floor(float(np.percentile(fwhm, 98)) / 2.0))
        simple_min = min(max(round(target), crowd_floor), visible_cap)
        simple_note = ("star sizes are too similar for Simple mode to pick only the standouts - "
                       "Per size mode does it better" if crowd_floor > visible_cap else None)
    else:
        simple_min = math.ceil(cutoff)
        simple_note = None
    simple_min = float(np.clip(simple_min, lo_d, hi_d))
    simple = {"min_diam": simple_min}
    for k, v in look.items():
        lo, hi = _SPIKE_ANCHOR_PARAM_FULL_RANGE[k]
        simple[k] = round(float(np.clip(v, lo, hi)), 1)
    simple_spiked = (int(np.count_nonzero(fwhm >= simple_min * _SIMPLE_NOTICEABLE_MULT))
                     if stars else 0)
    simple_half = int(np.count_nonzero(fwhm >= 2.0 * simple_min)) if stars else 0

    info = {"target": target, "cutoff": anchors[0]["diam"], "n_spiked": n_spiked,
            "n_stars": n_stars, "note": note, "clamped": sorted(clamped),
            "simple_spiked": simple_spiked, "simple_half": simple_half,
            "simple_note": simple_note}
    return globals_, anchors, simple, info


def compute_tone_wand(full_rgb):
    """What the Camera RAW Magic Wand sets (see magic_wand_tone), plus a
    human-readable report. full_rgb: the untouched source (H,W,3) float01."""
    a = analyze_image_tone(full_rgb)
    tone = magic_wand_tone(a, _subsample(np.asarray(full_rgb, dtype=np.float32)))

    lines = ["IMAGE ANALYSIS"]
    if a["bg_level"] > 0.20:
        sky = f"washed out (level {a['bg_level']:.2f})"
    elif a["bg_level"] < 0.02:
        sky = f"very dark (level {a['bg_level']:.3f})"
    else:
        sky = f"level {a['bg_level']:.2f}"
    lines.append(f"- Sky background: {sky} -> black point Blacks {tone['blacks']:+.0f}, "
                 f"white point Whites {tone['whites']:+.0f} (set after Shadows, so the sky stays dark)")
    casts = []
    if a["green_cast"] > 0.03:
        casts.append(f"green ({a['green_cast'] * 100:.0f}% of the sky level)")
    if abs(a["warm_cast"]) > 0.10:
        casts.append(f"{'orange' if a['warm_cast'] > 0 else 'blue'} ({abs(a['warm_cast']) * 100:.0f}%)")
    lines.append("- Colour cast: " + (", ".join(casts) if casts else "none to speak of")
                 + f" -> neutralised on the sky: Temperature {tone['temperature']:+.1f}, "
                   f"Tint {tone['tint']:+.1f}")
    lines.append(f"- Bright cores: {a['hi_frac'] * 100:.2f}% of pixels above 90% "
                 f"-> Highlights {tone['highlights']:+.0f}, Whites {tone['whites']:+.0f}")
    lines.append(f"- Background noise: {a['noise_rel'] * 100:.0f}% of the sky level "
                 f"-> Shadows {tone['shadows']:+.0f}, Texture {tone['texture']:+.0f}")
    lines.append(f"- Colour: mean subject saturation {a['subject_sat']:.2f} -> Vibrance {tone['vibrance']:+.0f}")
    return {"tone": tone, "analysis": a, "report": "\n".join(lines)}


def compute_spike_wand(stars, focal_mm, image_shape, current_rotation=30.0, mode="uniform"):
    """What the spike Magic Wand sets (see estimate_field_type and
    magic_wand_spikes), plus a human-readable report. stars: the detected
    (x, y, fwhm, ...) list in display px; focal_mm: FITS FOCALLEN or None;
    image_shape: (h, w, ...) of the image; mode: the spike mode the
    result will be written to ("uniform" = Simple, or "per_size"), which
    only changes what the report describes."""
    ftype, f_mm, source, reasons = estimate_field_type(focal_mm, stars, image_shape)
    spike_globals, anchors, simple, info = magic_wand_spikes(f_mm, stars, current_rotation)

    lines = ["FOCAL LENGTH"]
    head = (f"{f_mm:.0f}mm (declared)" if source == "declared"
            else f"estimated: {_FIELD_TYPE_LABEL[ftype]}, ~{f_mm:.0f}mm")
    lines.append(f"- {head}")
    for reason in reasons:
        lines.append(f"  {reason}")
    lines.append("")
    sm, md, lg = anchors
    if mode == "per_size":
        lines.append("SPIKES (Per size mode)")
        if info["note"]:
            lines.append(f"- {info['note']}")
        lines.append(f"- Minimum star diameter (Small tab) {sm['diam']:.1f}px: {info['n_spiked']} of "
                     f"{info['n_stars']} stars get a spike (focal length suggests {info['target']:.0f}px; "
                     f"at most {MAGIC_WAND_SPIKED_FRACTION * 100:.0f}% of the stars)")
        lines.append(f"- Medium {md['diam']:.1f}px / Large {lg['diam']:.1f}px: Length {lg['length']:.1f}x, "
                     f"Intensity {lg['intensity']:.0f}, Thickness {lg['thickness']:.1f} "
                     f"(Small: half length/intensity)")
        look = lg
    else:
        lines.append("SPIKES (Simple mode)")
        for note in (info["note"], info["simple_note"]):
            if note:
                lines.append(f"- {note}")
        lines.append(f"- Minimum star diameter {simple['min_diam']:.0f}px: {info['simple_spiked']} of "
                     f"{info['n_stars']} stars get a noticeable spike, {info['simple_half']} at half strength or "
                     f"more (focal length suggests {info['target']:.0f}px; full effect from "
                     f"{simple['min_diam'] * SPIKE_UNIFORM_REF_MULT:.0f}px)")
        lines.append(f"- Length {simple['length']:.1f}x, Intensity {simple['intensity']:.0f}, "
                     f"Thickness {simple['thickness']:.1f}")
        look = simple
    lines.append(f"- Rainbow {look['rainbow']:.0f}, Color saturation {look['saturation']:.0f}, "
                 f"Soft flare {look['soft_flare']:.0f}, Flare reach {look['flare_reach']:.0f}%")
    lines.append(f"- Sharpness {spike_globals['sharpness']:.0f}, Variation {spike_globals['variation']:.0f}, "
                 f"Twinkle {spike_globals['twinkle']:.0f}, Rotation {spike_globals['rotation']:.0f}")
    if info["clamped"] and mode == "per_size":
        lines.append("- Limited by the tab's slider range: " + ", ".join(info["clamped"]))
    return {"spike_globals": spike_globals, "spike_anchors": anchors, "spike_simple": simple,
            "spike_info": info, "mode": mode,
            "field_type": ftype, "focal_mm": f_mm, "focal_source": source,
            "report": "\n".join(lines)}


def apply_cosmetics(rgb, p):
    """Full light/tone/color pass on an (H,W,3) float [0,1] image. `p` is a
    dict keyed by TONE_PARAM_DEFS' own keys, each on a -100..100 scale (0 =
    no change - every stage below is gated on its own param being nonzero,
    so all-defaults is an exact identity, not just a near-no-op: cheap, and
    what test_process_thread_ignores_hide_background relies on). Order:
    exposure, white balance (temperature/tint), contrast, Highlights/
    Shadows (tone-region masked, unlike Whites/Blacks below), Whites/Blacks
    (hard clip-point stretch), Texture/Clarity/Dehaze (all local-contrast
    variants at different radii), then Vibrance and Saturation last (act on
    the final color balance).

    Deliberately stops there: an earlier version also had a per-channel
    Tone Curve and a per-hue-band HSL Color Mixer, removed after real use
    showed they added exactly the kind of per-color decision-making this
    tool is meant to spare the user from - see Magic Wand
    (App._on_magic_wand) for the "make it look right without touching 24
    individual sliders" alternative."""
    out = rgb.astype(np.float32).copy()

    exposure = p.get("exposure", 0.0)
    if exposure:
        stops = exposure / 100.0 * 2.0
        out = out * (2.0 ** stops)

    temperature, tint = p.get("temperature", 0.0), p.get("tint", 0.0)
    if temperature or tint:
        temp_shift = temperature / 100.0 * 0.15
        tint_shift = tint / 100.0 * 0.15
        out[..., 0] = out[..., 0] + temp_shift + tint_shift * 0.5   # R: warm + magenta
        out[..., 1] = out[..., 1] - tint_shift                       # G: green <-> magenta axis
        out[..., 2] = out[..., 2] - temp_shift + tint_shift * 0.5    # B: cool + magenta
        out = np.clip(out, 0.0, 1.0)

    contrast = p.get("contrast", 0.0)
    if contrast:
        c_factor = 1.0 + contrast / 100.0
        out = (out - 0.5) * c_factor + 0.5

    highlights, shadows = p.get("highlights", 0.0), p.get("shadows", 0.0)
    if highlights or shadows:
        # Tone-REGION controls (unlike Whites/Blacks below, which are a
        # flat clip-point stretch over the whole range): a luminance-based
        # weight mask that's ~1 only in the extreme highlights (resp.
        # shadows) and fades to 0 by mid-grey, so only that tonal region
        # moves - the classic "recover blown skies without flattening the
        # midtones" behaviour, as opposed to Whites/Blacks' simpler global
        # stretch.
        luma = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
        if highlights:
            mask_hi = np.clip((luma - 0.5) / 0.5, 0.0, 1.0) ** 1.5
            out = out + (mask_hi * (highlights / 100.0) * 0.5)[..., None]
        if shadows:
            mask_lo = np.clip((0.5 - luma) / 0.5, 0.0, 1.0) ** 1.5
            out = out + (mask_lo * (shadows / 100.0) * 0.5)[..., None]
        out = np.clip(out, 0.0, 1.0)

    blacks, whites = p.get("blacks", 0.0), p.get("whites", 0.0)
    if blacks or whites:
        bp = float(np.clip(blacks / 100.0 * 0.3, -0.9, 0.9))
        out = (out - bp) / max(1e-6, 1.0 - bp)
        wp = 1.0 - float(np.clip(whites / 100.0 * 0.3, -0.9, 0.9))
        out = out / max(1e-6, wp)
        out = np.clip(out, 0.0, 1.0)

    texture = p.get("texture", 0.0)
    if texture:
        # Fine (high-frequency) detail - a much smaller unsharp radius than
        # Clarity below, so it affects grain/fine structure rather than
        # broad mid-tone shape.
        h, w = out.shape[:2]
        radius = max(1, int(round(min(h, w) * 0.003)))
        luma = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
        detail = luma - _gaussian_blur(luma, radius)
        out = out + (detail * (texture / 100.0))[..., None]
        out = np.clip(out, 0.0, 1.0)

    clarity = p.get("clarity", 0.0)
    if clarity:
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

    dehaze = p.get("dehaze", 0.0)
    if dehaze:
        # A simplified stand-in for real (depth-aware) dehazing: haze
        # flattens both local contrast and saturation, so this pushes a
        # much larger-radius unsharp mask than Clarity (haze is a very
        # low-frequency veil, not mid-tone structure) together with a
        # saturation nudge in the same direction - negative values soften
        # and desaturate instead, for an artistic "add atmosphere" effect.
        h, w = out.shape[:2]
        radius = max(3, int(round(min(h, w) * 0.03)))
        amt = dehaze / 100.0
        luma = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
        detail = luma - _gaussian_blur(luma, radius)
        out = out + (detail * amt * 1.3)[..., None]
        out = np.clip(out, 0.0, 1.0)
        luma2 = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
        sat_factor = 1.0 + amt * 0.4
        out = luma2[..., None] + (out - luma2[..., None]) * sat_factor
        out = np.clip(out, 0.0, 1.0)

    vibrance = p.get("vibrance", 0.0)
    if vibrance:
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

    saturation = p.get("saturation", 0.0)
    if saturation:
        luma = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
        s_factor = 1.0 + saturation / 100.0
        out = luma[..., None] + (out - luma[..., None]) * s_factor
        out = np.clip(out, 0.0, 1.0)

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
    # Half-max radius interpolated between whole-pixel ring centres (the
    # peak itself at radius 0) - taking the first ring below half as-is
    # (its outer edge, a whole number) used to report even-integer sizes,
    # about twice too big for small stars (a 3.2px star read as 6px).
    half_r = float(r)
    prev_r, prev_v = 0.0, float(peak)
    for radius in range(1, r):
        ring = patch[(rad >= radius - 1) & (rad < radius)]
        if not ring.size:
            continue
        cur_r = float(np.mean(rad[(rad >= radius - 1) & (rad < radius)]))
        cur_v = float(ring.mean())
        if cur_v < half:
            span = prev_v - cur_v
            frac = (prev_v - half) / span if span > 1e-9 else 0.5
            half_r = prev_r + float(np.clip(frac, 0.0, 1.0)) * (cur_r - prev_r)
            break
        prev_r, prev_v = cur_r, cur_v
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


# ---------------------------------------------------------------------------
# Standalone (no Siril) mode: FITS/TIFF/JPG/PNG file I/O and star detection, used by
# FileWorker in place of sirilpy's pixeldata/get_image_stars calls. Kept as
# free functions (not methods) so they're independently testable, and all
# three extra imports (astropy, photutils, tifffile) are lazy - a Siril-
# connected session never needs them, so a missing package there shouldn't
# break anything; a standalone one gets a clear ImportError message instead
# of a confusing failure deep in a background thread.
# ---------------------------------------------------------------------------

def _normalize_float01(arr):
    """Best-effort 0-1 rescale for a float FITS/TIFF array that isn't
    already in that range (e.g. a linear/calibrated master still in raw ADU
    counts) - frankSpikes expects an already display-ready image, the same
    assumption the Siril-connected mode makes about its own pixeldata (see
    to_float01). Left untouched if it already looks normalized."""
    lo, hi = float(np.nanmin(arr)), float(np.nanmax(arr))
    if hi <= 1.5 and lo >= -0.05:
        return arr
    span = hi - lo
    if span <= 0:
        return np.zeros_like(arr)
    return ((arr - lo) / span).astype(np.float32)


def _load_fits(path):
    """Loads a FITS file into the same "raw" (row 0 = bottom, FITS' own
    native order) (H,W,3) float01 contract SirilWorker.fetch_full() returns
    - see FileWorker's class docstring for why this matters."""
    from astropy.io import fits
    with fits.open(path) as hdul:
        data = None
        for hdu in hdul:
            if getattr(hdu, "data", None) is not None:
                data = hdu.data
                break
    if data is None:
        raise ValueError("No image data found in this FITS file.")
    data = np.asarray(data)
    out = to_hwc(to_float01(data))
    if np.issubdtype(data.dtype, np.floating):
        out = _normalize_float01(out)
    return out


def _read_fits_focal_length(path):
    """The telescope's focal length in mm, from the standard FOCALLEN FITS
    keyword - None if missing/zero/unparsable (not every FITS file carries
    it) or on any error, so the caller falls back to the hand-tuned
    defaults. Reads only the header (no pixel data), so this is cheap even
    on a large file."""
    try:
        from astropy.io import fits
        with fits.open(path) as hdul:
            for hdu in hdul:
                fl = hdu.header.get("FOCALLEN")
                if fl:
                    fl = float(fl)
                    return fl if fl > 0 else None
    except Exception:
        pass
    return None


def _save_fits(path, rgb_display, bit_depth):
    """rgb_display is (H,W,3) float01 in display convention (row 0 = top,
    the same convention App hands to SirilWorker.push_rgb) - FITS' own
    on-disk convention is row 0 = bottom, so this flips once before writing,
    mirroring SirilWorker.push_rgb's own display -> raw flip."""
    from astropy.io import fits
    raw = rgb_display[::-1, :, :]
    chw = np.transpose(np.clip(raw, 0.0, 1.0), (2, 0, 1))
    if bit_depth == 16:
        data = (chw * 65535.0 + 0.5).astype(np.uint16)
    else:
        data = chw.astype(np.float32)
    fits.PrimaryHDU(data=data).writeto(path, overwrite=True)


def _load_tiff(path):
    """Loads a TIFF file into the same "raw" (H,W,3) float01 contract
    _load_fits() above does - TIFF's own native raster order is row 0 = top
    (the opposite of FITS), so it's flipped once here to match."""
    import tifffile
    arr = np.asarray(tifffile.imread(path))
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    elif arr.ndim == 3:
        if arr.shape[-1] == 1:
            arr = np.repeat(arr, 3, axis=-1)
        elif arr.shape[-1] == 4:
            arr = arr[..., :3]  # drop alpha
        elif arr.shape[-1] != 3:
            raise ValueError(f"Unsupported TIFF channel layout: {arr.shape}")
    else:
        raise ValueError(f"Unsupported TIFF shape: {arr.shape}")
    out = to_float01(arr)
    if np.issubdtype(arr.dtype, np.floating):
        out = _normalize_float01(out)
    return out[::-1, :, :]  # top-down (native) -> raw (bottom-up), see docstring


def _save_tiff(path, rgb_display, bit_depth):
    """rgb_display is (H,W,3) float01 in display convention (row 0 = top) -
    already TIFF's own native raster order, so no flip is needed here
    (unlike _save_fits above)."""
    import tifffile
    arr = np.clip(rgb_display, 0.0, 1.0)
    if bit_depth == 16:
        data = (arr * 65535.0 + 0.5).astype(np.uint16)
    elif bit_depth == 8:
        data = (arr * 255.0 + 0.5).astype(np.uint8)
    else:
        data = arr.astype(np.float32)
    tifffile.imwrite(path, data)


# Everyday 8-bit formats, read/written with Pillow (already a dependency) -
# handy for a quick edit of a finished, already-stretched JPG/PNG. Being
# 8-bit (16-bit only for greyscale PNG) and without FITS headers, there's no
# focal length to calibrate the spike defaults from.
_FITS_EXTS = (".fit", ".fits", ".fts")
_TIFF_EXTS = (".tif", ".tiff")
_RASTER_EXTS = (".jpg", ".jpeg", ".png")
_SUPPORTED_EXTS_MSG = ".fits/.fit/.fts, .tif/.tiff, .jpg/.jpeg or .png"


def _load_raster(path):
    """Loads a JPG/PNG into the same "raw" (H,W,3) float01 contract as
    _load_tiff() - also stored row 0 = top on disk, so flipped the same
    way. Honours the EXIF orientation tag (phone/camera JPGs), drops alpha,
    and keeps a 16-bit greyscale PNG's full range."""
    from PIL import ImageOps
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ("I;16", "I;16L", "I;16B", "I"):
            arr = np.clip(np.asarray(im), 0, 65535).astype(np.uint16)
            arr = np.stack([arr, arr, arr], axis=-1)
        else:
            arr = np.asarray(im.convert("RGB"))
    return to_float01(arr)[::-1, :, :]  # top-down (native) -> raw (bottom-up)


def _save_raster(path, rgb_display):
    """rgb_display is (H,W,3) float01 in display convention (row 0 = top),
    already JPG/PNG's own raster order. Always 8-bit; JPG at quality 95
    with no chroma subsampling so fine coloured spikes don't bleed."""
    data = (np.clip(rgb_display, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    im = Image.fromarray(data, "RGB")
    if os.path.splitext(path)[1].lower() in (".jpg", ".jpeg"):
        im.save(path, quality=95, subsampling=0)
    else:
        im.save(path)


def _detect_stars_standalone(raw_rgb, max_stars=6000):
    """Star detection for standalone (no-Siril) mode, replacing Siril's own
    'findstar' command. photutils' DAOStarFinder does the actual general-
    purpose peak finding (the same job findstar does); it doesn't report a
    usable per-star FWHM itself (its own output columns are sharpness/
    roundness, not size), so _measure_bright_star_profile - already used
    above for the saturated-star supplement - measures a real fwhm/
    amplitude from each candidate's own pixel profile instead, keeping
    star-size semantics identical regardless of which detector found it.

    raw_rgb is in the same raw (row 0 = bottom) convention as
    FileWorker.fetch_full()'s return value; returns (x, y, fwhm, amplitude)
    tuples with y in that SAME raw convention - the y-flip to the display
    convention get_stars() must return happens in FileWorker.get_stars(),
    not here, matching how SirilWorker keeps that flip out of this
    lower-level detection step too."""
    from astropy.stats import sigma_clipped_stats
    from photutils.detection import DAOStarFinder

    luma = (0.299 * raw_rgb[..., 0] + 0.587 * raw_rgb[..., 1]
            + 0.114 * raw_rgb[..., 2]).astype(np.float64)
    _mean, median, std = sigma_clipped_stats(luma, sigma=3.0, maxiters=5)
    if not (std > 0):
        return []
    # photutils renamed the "cap the candidate count" kwarg (brightest ->
    # n_brightest) and the result table's centroid columns (xcentroid/
    # ycentroid -> x_centroid/y_centroid) across major versions still in
    # use (2.x on Siril's own bundled venv, 3.x+ elsewhere) - handled
    # dynamically rather than pinning to one version's naming.
    try:
        finder = DAOStarFinder(fwhm=3.0, threshold=5.0 * std, n_brightest=max_stars)
    except TypeError:
        finder = DAOStarFinder(fwhm=3.0, threshold=5.0 * std, brightest=max_stars)
    table = finder(luma - median)
    if table is None or len(table) == 0:
        return []
    xcol = "x_centroid" if "x_centroid" in table.colnames else "xcentroid"
    ycol = "y_centroid" if "y_centroid" in table.colnames else "ycentroid"

    h, w = luma.shape
    out = []
    for row in table:
        x, y = float(row[xcol]), float(row[ycol])
        xi, yi = min(w - 1, max(0, int(round(x)))), min(h - 1, max(0, int(round(y))))
        peak = float(luma[yi, xi])
        fwhm, amplitude = _measure_bright_star_profile(luma, x, y, peak)
        if fwhm > 0:
            out.append((x, y, fwhm, amplitude))
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


def _spike_color_mult(star_color, saturation):
    """(R,G,B) colour multipliers for the star's own (already hue-rotated)
    colour, faded toward neutral white by `saturation` (0 = pure white
    regardless of the star's colour, 100 = full colour). Used for the
    spike rays' base colour (before _diffraction_mult's rainbow segments)
    and for the soft/ring flare tint."""
    sat = min(1.0, max(0.0, saturation / 100.0))
    return tuple(1.0 + (c - 1.0) * sat for c in star_color)


# Polychromatic diffraction model behind the "rainbow" control. A spider
# vane of finite width w diffracts light into a spike whose brightness
# along its length follows sinc^2(pi * r / P_lambda), with nulls every
# P_lambda = lambda * f / w (in px) - wavelength dependent, so blue's
# nulls fall closer to the star than red's. Summed over the visible
# spectrum that gives exactly what reference photos show: the spike
# starts in the star's own colour (every wavelength still in phase), then
# breaks into short coloured segments with dimmer gaps (yellow -> red ->
# magenta -> blue -> cyan -> green -> yellow ... outward, measured on real
# photos), washing back to neutral after 2-3 orders as the orders overlap.
_DIFFR_LAMBDAS = np.linspace(420.0, 680.0, 14)
_DIFFR_LAMBDA_REF = 550.0


def _diffr_gauss(x, mu, sigma):
    return np.exp(-0.5 * ((x - mu) / sigma) ** 2)


# Rough sRGB response per sampled wavelength (R also has the small violet
# lobe that makes the far blue end read as purple), each channel's weights
# normalised to sum to 1 - so "every wavelength at full strength" is
# exactly (1,1,1), i.e. the star's own colour untouched.
_DIFFR_RGB_WEIGHTS = np.stack([
    _diffr_gauss(_DIFFR_LAMBDAS, 600.0, 35.0) + 0.15 * _diffr_gauss(_DIFFR_LAMBDAS, 445.0, 18.0),
    _diffr_gauss(_DIFFR_LAMBDAS, 540.0, 38.0),
    _diffr_gauss(_DIFFR_LAMBDAS, 455.0, 25.0),
], axis=1)
_DIFFR_RGB_WEIGHTS = (_DIFFR_RGB_WEIGHTS / _DIFFR_RGB_WEIGHTS.sum(axis=0)).astype(np.float32)
# Brightness left at a single wavelength's null (a pure sinc^2 would drop
# to 0 - reference photos only dip to roughly half of the neighbouring
# segments once the spectrum is summed, sensor/seeing blur included).
DIFFR_NULL_FLOOR = 0.3
# How many orders stay distinctly coloured before blurring back to
# neutral (reference photos: 2-3).
DIFFR_ORDERS = 2.5


def _diffraction_mult(dist_px, period_px, amount, saturation):
    """Per-pixel (R,G,B) multipliers (each an array shaped like dist_px)
    for the diffraction rainbow at distance dist_px from the star along a
    spike. period_px is the null spacing at 550nm in the same px units as
    dist_px. amount (0-100) blends from no effect (1,1,1) to the full
    physical modulation; saturation (0-100, the ray's Color saturation)
    scales only its hue part - at 0 the segments stay, but grey."""
    ones = np.ones_like(dist_px, dtype=np.float32)
    if amount <= 0 or period_px <= 0:
        return ones, ones, ones
    a = min(1.0, amount / 100.0)
    x = np.maximum(dist_px, 0.0)[..., None] / (period_px * _DIFFR_LAMBDAS / _DIFFR_LAMBDA_REF)
    # sinc^2 main lobe near the star, then sin^2 (the sidelobes with their
    # 1/x^2 decay divided out - the overall fade along the spike is the
    # separate power-law envelope in _add_spike_ray, not this) - the two
    # meet continuously at x = 1/pi.
    m = np.where(x < 1.0 / np.pi, np.sinc(x) ** 2, np.sin(np.pi * x) ** 2)
    # Higher orders blur toward their mean (0.5): real light is a
    # continuum, not 14 samples, so the colours wash out instead of
    # re-aligning into spurious bright bands further out.
    wash = 1.0 / (1.0 + (x / DIFFR_ORDERS) ** 2)
    m = np.where(x < 1.0, m, 0.5 + (m - 0.5) * wash)
    m = DIFFR_NULL_FLOOR + (1.0 - DIFFR_NULL_FLOOR) * m
    rgb = np.tensordot(m.astype(np.float32), _DIFFR_RGB_WEIGHTS, axes=([-1], [0]))
    rgb = 1.0 + a * (rgb - 1.0)
    lum = rgb.mean(axis=-1, keepdims=True)
    sat = min(1.0, max(0.0, saturation / 100.0))
    rgb = lum + (rgb - lum) * sat
    return rgb[..., 0], rgb[..., 1], rgb[..., 2]


def _spike_flicker(dist_full_px, seed, amount):
    """Slow, irregular brightness fluctuation along a spike (reference
    photos: roughly +-20-40% around the smooth falloff) - a few
    incommensurate sine waves in full-resolution px (so it doesn't change
    with zoom) with phases from `seed` (deterministic per star and ray)."""
    if amount <= 0:
        return 1.0
    pa, pb = _star_jitter_pair(seed, seed * 0.37 + 11.0)
    pc, _ = _star_jitter_pair(seed * 1.91 + 5.0, seed)
    n = (np.sin(2 * np.pi * dist_full_px / 23.0 + pa * np.pi) +
         0.8 * np.sin(2 * np.pi * dist_full_px / 41.0 + pb * np.pi) +
         0.6 * np.sin(2 * np.pi * dist_full_px / 67.0 + pc * np.pi)) / 1.6
    return np.maximum(0.0, 1.0 + amount * n)


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


# Spike brightness along its length: a power law (1 + r/r0)^-k measured on
# reference photos (k ~ 0.7-2 in display space), r0 a fraction of the
# spike's own length, then a smooth fade over the last part so it still
# ends at Length instead of trailing off forever.
SPIKE_FALLOFF_EXP = 1.0
SPIKE_FALLOFF_R0_FRAC = 0.2
SPIKE_TIP_FADE_START = 0.55
# Width along the spike: real spikes don't taper to a point - they keep
# their width, even broadening slightly (reference photos: +20-40% at the
# tip), and just fade out.
SPIKE_WIDTH_GROWTH = 0.3
# Along-spike brightness fluctuation amplitude (see _spike_flicker).
SPIKE_FLICKER = 0.2


def _add_spike_ray(layer, cx, cy, angle_deg, length_px, thickness_px, peak,
                    star_color, rainbow, saturation, period_px=0.0,
                    px_scale=1.0, flicker_seed=0.0, flicker=0.0):
    """Add one glowing half-ray from (cx, cy) outward at angle_deg into an
    (H,W,3) additive layer. Brightness follows the power-law falloff above
    (brightest at the star, long faint tail, fading out at length_px),
    width stays constant/slightly growing, and - with rainbow > 0 and
    period_px > 0 (null spacing in the layer's own px) - the diffraction
    rainbow segments of _diffraction_mult. px_scale (layer px per full-
    resolution px) keeps the flicker pattern fixed in the real image
    regardless of zoom; flicker_seed makes it differ per star/ray."""
    if length_px < 1.0 or peak <= 0:
        return
    h, w, _ = layer.shape
    pad = thickness_px * (1.0 + SPIKE_WIDTH_GROWTH) * 3.0 + 1.0
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
    local_thickness = thickness_px * (1.0 + SPIKE_WIDTH_GROWTH * t)
    perp_falloff = np.exp(-(perp ** 2) / (2.0 * np.maximum(local_thickness, 0.02) ** 2))
    r0 = max(SPIKE_FALLOFF_R0_FRAC * length_px, 1e-3)
    envelope = (1.0 + np.maximum(along, 0.0) / r0) ** -SPIKE_FALLOFF_EXP
    fade_t = np.clip((t - SPIKE_TIP_FADE_START) / (1.0 - SPIKE_TIP_FADE_START), 0.0, 1.0)
    envelope = envelope * (1.0 - fade_t * fade_t * (3.0 - 2.0 * fade_t))
    # Behind the star: a soft bulge only, as before.
    along_falloff = np.where(
        along < 0,
        np.exp(-(along ** 2) / (2.0 * (thickness_px * 1.5) ** 2)),
        envelope * _spike_flicker(np.maximum(along, 0.0) / max(px_scale, 1e-6),
                                  flicker_seed, flicker),
    )
    mask = along <= length_px
    base = _soft_knee(peak * perp_falloff * along_falloff * mask)

    sr, sg, sb = _spike_color_mult(star_color, saturation)
    if rainbow > 0 and period_px > 0:
        # Depends only on `along`: evaluate the (14-wavelength) model once
        # on a fine 1D table and interpolate, instead of per pixel of the
        # whole bounding box (~6x slower at full resolution otherwise).
        grid = np.linspace(0.0, length_px, max(8, int(length_px * 4) + 1), dtype=np.float32)
        tr, tg, tb = _diffraction_mult(grid, period_px, rainbow, saturation)
        a_clip = np.clip(along, 0.0, length_px)
        dr = np.interp(a_clip, grid, tr)
        dg = np.interp(a_clip, grid, tg)
        db = np.interp(a_clip, grid, tb)
    else:
        dr = dg = db = 1.0
    layer[y0:y1, x0:x1, 0] = np.maximum(layer[y0:y1, x0:x1, 0], base * sr * dr)
    layer[y0:y1, x0:x1, 1] = np.maximum(layer[y0:y1, x0:x1, 1], base * sg * dg)
    layer[y0:y1, x0:x1, 2] = np.maximum(layer[y0:y1, x0:x1, 2], base * sb * db)


# Ray structure inside the soft flare (the "Flare rays" control). Measured
# on reference photos (Downloads/esempi): the sunburst around a bright star
# isn't a set of evenly spaced lines on black but a 15-40% modulation of
# the soft halo itself - 24-48 soft streaks (2-4 px, several degrees wide
# near the core), irregularly spaced (gap CV ~0.35-0.6) with very uneven
# brightness (CV ~0.5-0.7), more of them further out (rays branch), and
# the strongest ones hugging the main spikes (within ~10 deg, 1.5-3x
# brighter) as faint secondary spikes. FLARE_RAY_COUNT is the total
# number of base rays around the star (split evenly into one set per main
# spike wedge, so the symmetric part can repeat every wedge).
FLARE_RAY_COUNT = 48
# Max table resolution (radial bands x angle samples) - smaller flares use
# less (about 2 samples per px of the outer circumference), which is all
# the pixel grid can show anyway.
FLARE_RAY_BANDS = 10
FLARE_RAY_ANGLE_SAMPLES = 1440  # 0.25 deg


def _flare_ray_table(n_spikes, rotation_deg, symmetry, seed, radius_px, fwhm_px):
    """(bands, angle samples) table of the flare's angular ray pattern,
    normalised to mean 1 in every band, plus the band radii (px).
    symmetry (0-1): 1 = the same rays repeat exactly in every wedge between
    main spikes (the spider geometry repeats around the aperture), 0 =
    every copy is independently perturbed (scatter/seeing don't repeat)."""
    rng = np.random.default_rng(seed)
    n_spikes = max(1, int(n_spikes))
    wedge = 360.0 / n_spikes
    k = max(2, FLARE_RAY_COUNT // n_spikes)
    # One wedge's worth of base rays: offset from its spike (deg),
    # amplitude, width (px), start/end radius (fraction of radius_px).
    base = []
    # Stratified: one ray per equal slot (jittered inside it), so they
    # spread all around the star like a real sunburst instead of randomly
    # clumping into a few diffuse bundles.
    for slot in range(k):
        branch = rng.random() < 0.3
        base.append([(slot + rng.uniform(0.15, 0.85)) * wedge / k, rng.lognormal(0.0, 0.6),
                     fwhm_px * rng.uniform(0.02, 0.05),
                     rng.uniform(0.15, 0.5) if branch else 0.0,
                     rng.uniform(0.6, 1.0)])
        if branch and len(base) > 1:
            # a branch sits right next to an existing ray
            base[-1][0] = (base[rng.integers(0, len(base) - 1)][0] +
                           rng.choice((-1.0, 1.0)) * rng.uniform(1.0, 3.0)) % wedge
    med = float(np.median([b[1] for b in base]))
    # Secondary spikes: the rays that already fall within ~9 deg of a main
    # spike are made a little stronger (reference photos: ~1.4x overall,
    # jitter and branching already add some of that) - boosting
    # existing rays rather than adding extra ones, which would double the
    # ray density there and turn the flare into a few diffuse spikes
    # instead of an even sunburst.
    for b in base:
        if min(b[0], wedge - b[0]) < 9.0:
            b[1] *= rng.uniform(1.05, 1.3)
    spacing = wedge / len(base)
    rays = []
    for i in range(n_spikes):
        spike = rotation_deg + i * wedge
        for off, amp, width, r0, r1 in base:
            j_ang = rng.uniform(-0.8, 0.8) * spacing
            j_amp = rng.lognormal(0.0, 0.6)
            j_r0 = rng.uniform(0.0, 0.4) if r0 > 0 else 0.0
            j_r1 = rng.uniform(0.6, 1.0)
            s = symmetry
            rays.append((spike + off + (1.0 - s) * j_ang,
                         amp ** s * (j_amp * (amp / max(med, 1e-6)) ** 0.5) ** (1.0 - s),
                         width, s * r0 + (1.0 - s) * j_r0, s * r1 + (1.0 - s) * j_r1))

    n_b = int(np.clip(radius_px / 6.0, 4, FLARE_RAY_BANDS))
    n_t = int(np.clip(4.0 * np.pi * radius_px, 180, FLARE_RAY_ANGLE_SAMPLES))
    bands = np.linspace(0.08, 1.0, n_b) * radius_px
    theta = np.linspace(0.0, 360.0, n_t, endpoint=False, dtype=np.float32)
    ang, amp, width, r0, r1 = (np.array(c, dtype=np.float32)[:, None] for c in zip(*rays))
    f = (bands / max(radius_px, 1e-6))[None, :]                  # (1, bands)
    # smooth start (branches appear) and end (rays fade out) - (rays, bands)
    win = (np.clip((f - r0) / 0.12, 0.0, 1.0) *
           np.clip((r1 - f) / 0.25 + 1.0, 0.0, 1.0) * np.clip((1.0 - f) / 0.2 + 1.0, 0.0, 1.0))
    # width in px grows slightly outward; as an angle it narrows
    sig = np.degrees(np.maximum(width, 0.5) * (1.0 + 0.5 * f) / np.maximum(bands[None, :], 1e-6))
    # capped at 3 deg: wider rays near the core merge into broad wedges
    sig = np.clip(sig, max(0.25, 360.0 / n_t), 3.0)
    d = (theta[None, :] - ang + 180.0) % 360.0 - 180.0             # (rays, angles)
    table = np.einsum("rb,rbt->bt", amp * win,
                      np.exp(-0.5 * (d[:, None, :] / sig[:, :, None]) ** 2)).astype(np.float32)
    table /= np.maximum(table.mean(axis=1, keepdims=True), 1e-6)
    return table, bands


def _flare_ray_field(r, theta_deg, table, bands):
    """Bilinear lookup of _flare_ray_table at polar coordinates (r px,
    theta deg)."""
    n_b, n_t = table.shape
    fb = np.interp(r, bands, np.arange(n_b, dtype=np.float32))
    b0 = np.floor(fb).astype(np.int32)
    b1 = np.minimum(b0 + 1, n_b - 1)
    wb = fb - b0
    ft = (theta_deg % 360.0) / 360.0 * n_t
    t0 = np.floor(ft).astype(np.int32) % n_t
    t1 = (t0 + 1) % n_t
    wt = ft - np.floor(ft)
    top = table[b0, t0] * (1 - wt) + table[b0, t1] * wt
    bot = table[b1, t0] * (1 - wt) + table[b1, t1] * wt
    return top * (1 - wb) + bot * wb


def _add_soft_flare(layer, cx, cy, core_px, reach_px, peak,
                     color_mult=(1.0, 1.0, 1.0), rays=0.0, n_spikes=4,
                     rotation_deg=0.0, symmetry=0.5, seed=0, fwhm_px=1.0):
    """The star's scattered-light flare: a soft power-law glow around the
    star in every direction (sensor/optics bloom), ending smoothly at
    reach_px - plus, with rays > 0 (0-100), the soft irregular streaks of
    a real sunburst (see _flare_ray_table), which start right at the
    star's visible edge (core_px) so they show just outside the core even
    for a short reach, rather than hiding inside it. color_mult (r,g,b),
    from _spike_color_mult, tints it toward the star's own colour. The
    main spikes' count/rotation place the secondary spikes, symmetry (0-1)
    is how strictly the pattern repeats every wedge, seed makes it differ
    per star, fwhm_px sets the ray width."""
    if reach_px < 1.0 or peak <= 0:
        return
    h, w, _ = layer.shape
    pad = reach_px + 1.0
    x0 = int(max(0, np.floor(cx - pad)))
    x1 = int(min(w, np.ceil(cx + pad)))
    y0 = int(max(0, np.floor(cy - pad)))
    y1 = int(min(h, np.ceil(cy + pad)))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    core = max(core_px, 0.5)
    # smooth end over the outer 45% of the reach - reaches exactly 0 at
    # reach_px, so no square box edge and never past the spike tips
    t = np.clip((r - 0.55 * reach_px) / (0.45 * reach_px), 0.0, 1.0)
    end = 1.0 - t * t * (3.0 - 2.0 * t)
    glow = (1.0 + (r / core) ** 2) ** -0.7 * end
    contrib = peak * glow
    if rays > 0:
        a = min(1.0, rays / 100.0)
        table, bands = _flare_ray_table(n_spikes, rotation_deg, symmetry, seed, reach_px, fwhm_px)
        theta = np.degrees(np.arctan2(yy - cy, xx - cx))
        field = _flare_ray_field(r, theta, table, bands)
        # Rays emerge at the core edge and fade with a slower power law
        # than the glow, so they're what's visible across the whole band.
        rise = np.clip((r - 0.6 * core) / (0.8 * core), 0.0, 1.0)
        rise = rise * rise * (3.0 - 2.0 * rise)
        span = max(0.5 * (reach_px - core), 1e-3)
        ray_profile = rise * (1.0 + np.maximum(r - core, 0.0) / span) ** -1.0 * end
        # Part of the glow's light goes into the rays (the same scattered
        # light, structured), the rest stays a smooth halo underneath.
        contrib = _soft_knee(contrib * (1.0 - 0.6 * a) + a * peak * field * ray_profile)
    r_mult, g_mult, b_mult = color_mult
    layer[y0:y1, x0:x1, 0] = np.maximum(layer[y0:y1, x0:x1, 0], contrib * r_mult)
    layer[y0:y1, x0:x1, 1] = np.maximum(layer[y0:y1, x0:x1, 1], contrib * g_mult)
    layer[y0:y1, x0:x1, 2] = np.maximum(layer[y0:y1, x0:x1, 2], contrib * b_mult)


def ring_width_for_radius(ring_radius_px, fwhm_px):
    """Gaussian width (sigma) of the ring flare, given its own radius. A real
    reference photo shows no separate ring shape at all - the halo around a
    star is one smooth, continuous gradient - so the width scales with the
    ring's OWN radius (a broad fraction of it) rather than a small fixed
    fraction of the star's fwhm; that turns what used to render as a crisp
    thin circle into a soft brightness bump that blends into the core and
    soft flare instead of reading as a separate ring."""
    return max(0.8, ring_radius_px * 0.55, fwhm_px * 0.15)


def _add_ring_flare(layer, cx, cy, ring_radius_px, ring_width_px, peak,
                     color_mult=(1.0, 1.0, 1.0)):
    """A soft brightening around the star at roughly this radius, blended
    into the surrounding glow rather than a crisp separate ring - see
    ring_width_for_radius for why the width scales the way it does.
    color_mult, as in _add_soft_flare, tints it toward the star's colour;
    (1,1,1) (the default) keeps the original pure-white ring bit for bit."""
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
    r_mult, g_mult, b_mult = color_mult
    layer[y0:y1, x0:x1, 0] = np.maximum(layer[y0:y1, x0:x1, 0], contrib * r_mult)
    layer[y0:y1, x0:x1, 1] = np.maximum(layer[y0:y1, x0:x1, 1], contrib * g_mult)
    layer[y0:y1, x0:x1, 2] = np.maximum(layer[y0:y1, x0:x1, 2], contrib * b_mult)


# Geometry (where the flares sit), not strength: these keep their dialled-
# in value across Simple mode's size ramp and Small/Medium's narrower
# slider ceilings (SPIKE_ANCHOR_LOOK_SCALE) - ramping a flare's reach from
# 0 at the minimum diameter collapsed mid-size stars' flares into their
# own core. Their fallback values when a dict doesn't have them:
_SPIKE_GEOMETRY_KEYS = ("flare_reach", "ring_diam")
SPIKE_FLARE_REACH_DEFAULT = 45.0   # % of the spike length
SPIKE_RING_DIAM_DEFAULT = 1.6      # x star diameter - just past the star's edge
# Colour purity, not strength: how much of the star's own colour the rays
# and flares show is a property of the star, not something a smaller star
# should get less range for, so these also keep the full slider range on
# every Per size tab (no SPIKE_ANCHOR_LOOK_SCALE ceiling).
_SPIKE_COLOUR_KEYS = ("saturation", "flare_saturation")

_ANCHOR_PARAM_KEYS = ("length", "intensity", "thickness", "soft_flare", "flare_reach",
                      "flare_rays", "ring_flare", "ring_diam",
                      "flare_saturation", "rainbow", "saturation")

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
    lockstep - used by the "Natural variation" control (length only, not
    rotation - see render_spike_layer) to break up the stamped/CGI look of
    many identical-size stars."""
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
    is a dict of the _ANCHOR_PARAM_KEYS set by Shift+Click-editing that
    one star individually (see App._spike_star_overrides) - used exactly
    as given instead of interpolating from cfg's anchors, and (like forced)
    bypasses the diameter cutoff, since dialling in a custom look for a
    star is itself a clear signal it should have a spike.

    cfg is a dict (see App._spike_config): "anchors" is the size-anchor
    dicts (each with "diam" plus the keys in _ANCHOR_PARAM_KEYS) that get
    interpolated per star by _interp_anchor_params; "rays", "rotation",
    "hue" and "sharpness" (0-100, default 100 = untouched - softens the
    whole effect for long focal lengths/average seeing) apply globally;
    "variation" (0-100) drives the per-star length jitter (not rotation -
    see the note above the jitter/angles computation below)."""
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
    flare_symmetry = max(0.0, min(100.0, cfg.get("flare_symmetry",
                                                  SPIKE_DEFAULTS["flare_symmetry"]))) / 100.0

    scale = out_w / float(view_w)
    # Same for every star (see SPIKE_DEFAULTS' "rainbow_period"), in the
    # layer's own px.
    rainbow_period_px = max(0.0, cfg.get("rainbow_period", SPIKE_DEFAULTS["rainbow_period"])) * scale
    max_amp = max((a for (_, _, _, a, _c, _f, _o) in stars), default=1.0) or 1.0

    for (x, y, fwhm, amp, color, forced, override) in stars:
        if override is not None:
            p = override
        elif fwhm < min_diameter and not forced:
            if twinkle <= 0:
                continue
            # A tiny fixed hint instead of nothing - see TWINKLE_* above.
            p = {"length": TWINKLE_LENGTH_MULT, "intensity": twinkle * TWINKLE_INTENSITY_SCALE,
                 "thickness": TWINKLE_THICKNESS, "soft_flare": 0.0,
                 "flare_reach": SPIKE_FLARE_REACH_DEFAULT, "flare_rays": 0.0, "ring_flare": 0.0,
                 "ring_diam": SPIKE_RING_DIAM_DEFAULT, "flare_saturation": 0.0,
                 "rainbow": 0.0, "saturation": 100.0}
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

        # Rotation is NOT jittered per star: a real diffraction spike's
        # angle comes from the telescope's own spider-vane orientation, the
        # same physical hardware for every star in the frame - it can't
        # vary from star to star within one photo, only Length legitimately
        # does (seeing/PSF variation).
        jx, _jr = _star_jitter_pair(x, y)
        length_jitter = 1.0 + jx * jitter_amt * 0.12  # up to +-12% length
        angles = [rotation_deg + i * (360.0 / num_rays) for i in range(num_rays)]

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
                for i, ang in enumerate(angles):
                    _add_spike_ray(layer, cx, cy, ang, ray_len_px, th_px, peak,
                                    star_color, p["rainbow"], p["saturation"],
                                    period_px=rainbow_period_px, px_scale=scale,
                                    flicker_seed=(x * 7.13 + y * 3.71 + i * 101.0) % 10007.0,
                                    flicker=SPIKE_FLICKER)

        if p["soft_flare"] > 0 or p["ring_flare"] > 0:
            # Soft flare and ring flare share one saturation
            # control (see SPIKE_ANCHOR_PARAM_DEFS' "flare_saturation")
            # rather than a separate knob each - they're all the same
            # scattered/diffracted starlight, so they'd always be tinted
            # together anyway. Reuses _spike_color_mult's own blend so 0
            # means the same pure white as before this control existed.
            flare_color_mult = _spike_color_mult(star_color, p.get("flare_saturation", 0.0))
        else:
            flare_color_mult = (1.0, 1.0, 1.0)

        # Both flares live in a band from the star's own visible edge
        # (core_px) out to a reach set as a fraction of the rendered spike
        # length - never past the spike tips (a flare poking out beyond the
        # spikes reads as a separate, oversized disc), and never so short
        # that it disappears inside the star's own core (the reach is
        # floored at core_px + 1.5 star diameters).
        core_px = 0.5 * fwhm * scale
        min_reach_px = core_px + 1.5 * fwhm * scale
        max_reach_px = max(ray_len_px, min_reach_px)

        if p["soft_flare"] > 0:
            reach_frac = p.get("flare_reach", SPIKE_FLARE_REACH_DEFAULT) / 100.0
            reach_px = min(max_reach_px, max(min_reach_px, reach_frac * ray_len_px))
            if reach_px >= 1.0:
                flare_peak = (p["soft_flare"] / 100.0) * rel_amp * 0.8
                # Seeded by the star's position so its sunburst is its own
                # but never changes between re-renders/zoom levels.
                seed = [int(x * 97) & 0xffffffff, int(y * 97) & 0xffffffff]
                _add_soft_flare(layer, cx, cy, core_px, reach_px, flare_peak,
                                flare_color_mult,
                                rays=p.get("flare_rays", 0.0), n_spikes=num_rays,
                                rotation_deg=rotation_deg, symmetry=flare_symmetry,
                                seed=seed, fwhm_px=fwhm * scale)

        if p["ring_flare"] > 0:
            # A diffraction ring hugs the star (a real Airy ring sits just
            # outside the core), so its size is its own DIAMETER in star
            # diameters - 1.6x (the default) sits just past the star's own
            # edge - kept outside the core and inside the spikes.
            ring_diam = p.get("ring_diam", SPIKE_RING_DIAM_DEFAULT)
            ring_radius_px = max(core_px * 1.15, 0.5 * ring_diam * fwhm * scale)
            # (its soft width is ~0.55x its radius - see
            # ring_width_for_radius - so 0.42x the spike length keeps even
            # its outer shoulder inside the spike tips)
            ring_radius_px = min(ring_radius_px, max(0.42 * ray_len_px, core_px * 1.15))
            ring_width_px = ring_width_for_radius(ring_radius_px, fwhm * scale)
            if ring_radius_px >= 1.5:
                ring_peak = (p["ring_flare"] / 100.0) * rel_amp * 0.7
                _add_ring_flare(layer, cx, cy, ring_radius_px, ring_width_px, ring_peak,
                                 flare_color_mult)

                # A real Airy pattern isn't one ring - successive bright
                # rings sit at roughly 1.8x the radius of the one before
                # (spacing of the Bessel-function zeros that bound each
                # ring) and fade quickly, on the order of a quarter of the
                # previous ring's peak. A single, suspiciously clean circle
                # reads as synthetic; this second, fainter, wider one is
                # what makes it read as a real multi-ring diffraction
                # pattern instead - also kept inside the spikes.
                ring2_width_px = ring_width_px * 1.3
                ring2_radius_px = min(ring_radius_px * 1.8,
                                       max(ray_len_px - 3.0 * ring2_width_px, 0.0))
                if ring2_radius_px > ring_radius_px * 1.2:
                    ring2_peak = ring_peak * 0.25
                    _add_ring_flare(layer, cx, cy, ring2_radius_px, ring2_width_px, ring2_peak,
                                     flare_color_mult)

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

    standalone = False  # see FileWorker - App branches on this, not isinstance()

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

    def get_focal_length(self):
        """The telescope's focal length in mm, from the FITS header Siril
        already parsed for this image - None if missing/zero (an unusual
        but real case: not every FITS file carries this keyword) or on any
        error, so the caller can fall back to the hand-tuned defaults."""
        try:
            fl = float(self.siril.get_image_keywords().focal_length)
            return fl if fl > 0 else None
        except Exception:
            return None

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


class FileWorker:
    """Standalone (no Siril) mode: same interface as SirilWorker (duck-typed
    - App only ever calls through self.worker, never checks which class it
    is, except via the `standalone` flag), but reads/writes FITS, TIFF, JPG or PNG
    files directly instead of talking to a running Siril instance, and uses
    photutils in place of Siril's own 'findstar'.

    Follows SirilWorker's exact raw/display convention split so the rest of
    the app (particularly App._reload_thread, which converts stars raw<->
    display around the pixel-level saturated-star/colour-sampling steps -
    see the comment there) needs no changes at all: fetch_full() returns
    pixel data in "raw" order (row 0 = bottom - FITS' own native order;
    _load_tiff/_load_fits normalize either source format to this), while
    get_stars() returns star y in "display" order (row 0 = top), exactly
    like Siril's own get_image_stars()."""

    standalone = True

    def __init__(self):
        self.path = None
        self._raw_rgb = None    # (H,W,3) float01, raw (row 0 = bottom) order
        self._shape = None      # (h, w)
        self._src_ext = None    # source file extension, used to pick a Save As default
        self._focal_length = None  # mm, from the FITS header - None if unavailable (TIFF/JPG/PNG)
        self.last_rgb = None    # most recent Process() result, display order - cached
        # for File > Save As (re-saving without recomputing) since App.push_rgb
        # can't itself open a file dialog (called from a background thread).

    def cmd(self, *args):
        pass  # no Siril command channel in standalone mode

    def log(self, msg):
        print(msg)

    def get_wd(self):
        return os.path.dirname(self.path) if self.path else os.path.expanduser("~")

    def get_shape(self):
        return self._shape

    def is_image_loaded(self):
        return self._raw_rgb is not None

    def get_active_filename(self):
        return os.path.basename(self.path) if self.path else "(none)"

    def open_path(self, path):
        """Loads a FITS, TIFF, JPG or PNG file - raises on failure
        (an unsupported extension, a missing optional dependency, or a file
        the library itself can't parse), left to the caller (App._on_open_file,
        on the main thread) to report via a message box."""
        ext = os.path.splitext(path)[1].lower()
        if ext in _FITS_EXTS:
            arr = _load_fits(path)
        elif ext in _TIFF_EXTS:
            arr = _load_tiff(path)
        elif ext in _RASTER_EXTS:
            arr = _load_raster(path)
        else:
            raise ValueError(f"Unsupported file type {ext!r} - expected {_SUPPORTED_EXTS_MSG}")
        self.path = path
        self._raw_rgb = arr
        self._shape = arr.shape[:2]
        self._src_ext = ext
        self._focal_length = _read_fits_focal_length(path) if ext in _FITS_EXTS else None

    def get_focal_length(self):
        return self._focal_length

    def get_stars(self):
        h, _w = self._shape
        raw_stars = _detect_stars_standalone(self._raw_rgb)
        return [(x, h - 1.0 - y, fwhm, amp) for (x, y, fwhm, amp) in raw_stars]

    def clear_stars(self):
        pass  # no on-image star markers to clear outside Siril

    def fetch_full(self):
        return self._raw_rgb

    def push_rgb(self, rgb_float01):
        """No live image to overwrite in standalone mode - just cache the
        result (display order, same as SirilWorker.push_rgb receives) for
        App to save to disk once the user picks a path."""
        self.last_rgb = np.clip(rgb_float01, 0.0, 1.0).astype(np.float32)

    def save_rgb(self, rgb_float01, path, bit_depth=None):
        """Writes rgb_float01 (display order, row 0 = top) to `path` as
        FITS, TIFF, JPG or PNG, picked by its extension. bit_depth defaults to 32
        (float) for FITS - the standard lossless astro interchange depth -
        and 16 (unsigned) for TIFF; JPG/PNG are always 8-bit (bit_depth is
        ignored for them)."""
        ext = os.path.splitext(path)[1].lower()
        if bit_depth is None:
            bit_depth = 32 if ext in (".fit", ".fits", ".fts") else 16
        if ext in _FITS_EXTS:
            _save_fits(path, rgb_float01, bit_depth)
        elif ext in _TIFF_EXTS:
            _save_tiff(path, rgb_float01, bit_depth)
        elif ext in _RASTER_EXTS:
            _save_raster(path, rgb_float01)
        else:
            raise ValueError(f"Unsupported file type {ext!r} - expected {_SUPPORTED_EXTS_MSG}")


class App:
    def __init__(self, root, worker: SirilWorker):
        self.root = root
        self.worker = worker
        self.queue = queue.Queue()

        self.workdir = tk.StringVar(value=self.worker.get_wd())
        self.active_filename = tk.StringVar(value="(none)")
        self.status = tk.StringVar(
            value="Open an image to get started (File > Open...)." if worker.standalone
            else "Reading the active image from Siril...")

        if worker.standalone:
            menubar = tk.Menu(root)
            file_menu = tk.Menu(menubar, tearoff=False)
            file_menu.add_command(label="Open...", accelerator="Ctrl+O",
                                    command=self._on_open_file)
            file_menu.add_command(label="Save As...", accelerator="Ctrl+S",
                                    command=self._on_save_as_menu)
            menubar.add_cascade(label="File", menu=file_menu)
            root.config(menu=menubar)
            root.bind("<Control-o>", lambda _e: self._on_open_file())
            root.bind("<Control-s>", lambda _e: self._on_save_as_menu())

        # One dict for every left-panel (Base/Detail/...) tone/color
        # control, keyed by TONE_PARAM_DEFS' own keys plus "<key>_label" -
        # same shape/pattern as self.spike_uniform, built in a loop instead
        # of one hand-written Var pair per parameter.
        self.tone = {}
        for key, _label, _lo, _hi, _step, fmt in TONE_PARAM_DEFS:
            self.tone[key] = tk.DoubleVar(value=TONE_DEFAULTS[key])
            self.tone[key + "_label"] = tk.StringVar(value=fmt.format(TONE_DEFAULTS[key]))

        d = SPIKE_DEFAULTS
        self.spike_enabled = tk.BooleanVar(value=d["enabled"])
        self.spike_rays = tk.IntVar(value=d["rays"])
        self.spike_rotation = tk.DoubleVar(value=d["rotation"])
        self.spike_hue = tk.DoubleVar(value=d["hue"])
        self.spike_sharpness = tk.DoubleVar(value=d["sharpness"])
        self.spike_variation = tk.DoubleVar(value=d["variation"])
        self.spike_twinkle = tk.DoubleVar(value=d["twinkle"])
        self.spike_flare_symmetry = tk.DoubleVar(value=d["flare_symmetry"])
        self.spike_rainbow_period = tk.DoubleVar(value=d["rainbow_period"])
        self.spike_rotation_label = tk.StringVar(value=f"{d['rotation']:.0f}")
        self.spike_hue_label = tk.StringVar(value=f"{d['hue']:.0f}")
        self.spike_sharpness_label = tk.StringVar(value=f"{d['sharpness']:.0f}")
        self.spike_variation_label = tk.StringVar(value=f"{d['variation']:.0f}")
        self.spike_twinkle_label = tk.StringVar(value=f"{d['twinkle']:.0f}")
        self.spike_flare_symmetry_label = tk.StringVar(value=f"{d['flare_symmetry']:.0f}")
        self.spike_rainbow_period_label = tk.StringVar(value=f"{d['rainbow_period']:.0f}")

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

        # Open/closed state of the "Rays"/"Flare" collapsible sections (see
        # _make_collapsible), keyed by a per-panel string so e.g. collapsing
        # Small's Flare section doesn't affect Medium/Large or Simple mode.
        # Persists for the rest of the session, not saved across restarts.
        self._collapsible_state = {}

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
        # Standalone "unsaved changes" tracking (see _has_unsaved_changes):
        # the edit signature the file on disk matches (taken right after
        # loading, then after every successful save), and the one the last
        # Process result was rendered with.
        self._saved_sig = None
        self._processed_sig = None
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

    def _edit_signature(self):
        """Everything the user can change about the result - tone sliders,
        the spike settings actually rendered and per-star edits - as one
        comparable value (see _has_unsaved_changes)."""
        tone = sorted((k, v.get()) for k, v in self.tone.items() if not k.endswith("_label"))
        return repr((tone, self.spike_enabled.get(), self._spike_config(),
                     sorted(self._spike_disabled), sorted(self._spike_forced),
                     self._spike_manual,
                     sorted(self._spike_star_overrides.items(), key=repr)))

    def _has_unsaved_changes(self):
        """An image is open and its current edits differ from the last ones
        that actually left this window - saved to disk (standalone) or
        applied to the image in Siril with Process (Siril mode; closing
        before that loses them) - or from the untouched image, if nothing
        was saved/applied yet."""
        return (self.loaded and self._saved_sig is not None
                and self._edit_signature() != self._saved_sig)

    def _confirm_discard(self, action):
        """True if it's fine to go ahead with `action` (e.g. "Close"),
        asking first when there are unsaved changes."""
        if not self._has_unsaved_changes():
            return True
        if self.worker.standalone:
            what, without = "haven't been saved", "without saving"
        else:
            what = ('haven\'t been applied to the image in Siril yet '
                    '("Process and import in Siril")')
            without = "without applying them"
        return messagebox.askyesno(
            "Unsaved changes",
            f'"{self.active_filename.get()}" has changes that {what}.\n\n'
            f"{action} {without}?",
            icon="warning", default="no")

    def _on_close(self):
        """Safety net: get_stars() already clears the star overlay right
        after detection, but make sure closing the window never leaves
        every star selected on the image in Siril."""
        if not self._confirm_discard("Close"):
            return
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

        self._build_grouped_tone_sliders(frm_ctrl)

        ttk.Button(frm_ctrl, text="✨ Magic Wand", style="Accent.TButton",
                   command=self._on_magic_wand).pack(fill="x", pady=(14, 0))
        ttk.Label(frm_ctrl, text="Auto-balances color and tone (Camera RAW sliders only - "
                                  "the spikes have their own Magic Wand)",
                  style="Muted.TLabel", wraplength=210, justify="left").pack(
            fill="x", pady=(2, 0))

        ttk.Button(frm_ctrl, text="Reset", style="Warn.TButton",
                   command=self._reset_tone_defaults).pack(fill="x", pady=(10, 0))

        process_label = ("Process and Save As..." if self.worker.standalone
                         else "Process and import in Siril")
        self.btn_process = ttk.Button(frm_ctrl, text=process_label,
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
        ttk.Label(frm_toolbar, text="Hold Space: original, as imported from Siril — "
                                     "release: your edits",
                  style="CardMuted.TLabel").pack(side="left", padx=(16, 0))
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

        # ---- General: every global (not per-size-anchor) control, in one
        # collapsible section rather than scattered loose sliders - Number
        # of rays, Rotation, Color hue, Sharpness, Natural variation,
        # Twinkle, Rainbow segment spacing, plus Minimum star diameter (Simple mode
        # only). Minimum star diameter still leads the section - which
        # stars get a spike at all is the most fundamental choice - shown/
        # hidden by _update_spike_mode_ui alongside the notebook/uniform/
        # star panels below, independently of this section's own collapsed
        # state. ----
        general_content = self._make_collapsible(frm_spikes, 2, "General", "general")

        self._spike_min_diam_frame = ttk.Frame(general_content, style="Card.TFrame")
        self._spike_min_diam_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
        self._spike_min_diam_frame.grid_columnconfigure(0, minsize=200)
        u_lo, u_hi = SPIKE_ANCHOR_DIAM_RANGES[0]
        self._add_slider(self._spike_min_diam_frame, 0, "Minimum star diameter (px)",
                          self.spike_uniform_min_diam, self.spike_uniform_min_diam_label,
                          u_lo, u_hi, step=1, on_change=self._on_spike_slider)

        ttk.Label(general_content, text="Number of rays", style="Card.TLabel").grid(
            row=2, column=0, columnspan=3, sticky="w", padx=10, pady=(4, 0))
        rays_box = ttk.Frame(general_content, style="Card.TFrame")
        rays_box.grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=(2, 0))
        ttk.Radiobutton(rays_box, text="4 (refractor / 2-vane spider)", value=4,
                         variable=self.spike_rays, command=self._on_spike_slider).pack(anchor="w")
        ttk.Radiobutton(rays_box, text="6 (3-vane spider, e.g. Newtonian)", value=6,
                         variable=self.spike_rays, command=self._on_spike_slider).pack(anchor="w")

        self._add_slider(general_content, 4, "Rotation angle (0-90 deg)",
                          self.spike_rotation, self.spike_rotation_label, 0, 90,
                          step=1, on_change=self._on_spike_slider)
        self._add_slider(general_content, 6, "Color hue (each spike keeps its star's colour)",
                          self.spike_hue, self.spike_hue_label, -180, 180,
                          step=5, on_change=self._on_spike_slider)
        self._add_slider(general_content, 8, "Sharpness (lower = softer, for long focal lengths)",
                          self.spike_sharpness, self.spike_sharpness_label, 0, 100,
                          step=5, on_change=self._on_spike_slider)
        self._add_slider(general_content, 10, "Natural variation (per-star length jitter)",
                          self.spike_variation, self.spike_variation_label, 0, 100,
                          step=5, on_change=self._on_spike_slider)
        self._add_slider(general_content, 12, "Twinkle (a tiny hint of spike below the minimum diameter)",
                          self.spike_twinkle, self.spike_twinkle_label, 0, 100,
                          step=5, on_change=self._on_spike_slider)
        # Global, not per size: the diffraction rainbow's segment spacing
        # comes from the optics (see SPIKE_DEFAULTS' "rainbow_period"), so
        # it's the same for every star - each size's own "Diffraction
        # rainbow" slider only sets how strongly it shows.
        self._add_slider(general_content, 14, "Rainbow segment spacing (px)",
                          self.spike_rainbow_period, self.spike_rainbow_period_label, 5, 200,
                          step=1, on_change=self._on_spike_slider)
        # "Flare ray symmetry" lives in each panel's Flare section instead
        # (see _build_grouped_anchor_sliders) - it's about the flare, even
        # though (like Number of rays above) it's a single global value,
        # not a per-size one.

        # ---- Per-size-anchor look: a tab per anchor, each with "diam"
        # (which star size this tab applies to) followed by the Rays/Flare
        # collapsible sections - see _build_grouped_anchor_sliders, which
        # keeps this, the Uniform panel below and the per-star panel
        # further down in sync by construction. ----
        self._spike_notebook = ttk.Notebook(frm_spikes)
        self._spike_notebook.grid(row=18, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 4))
        diam_label, _lo, _hi, diam_step, _fmt = _SPIKE_PARAM_DEFS_BY_KEY["diam"]
        for tab_index, (tab_label, anchor_vars) in enumerate(
                zip(SPIKE_ANCHOR_TAB_LABELS, self.spike_anchors)):
            tab = ttk.Frame(self._spike_notebook, style="Card.TFrame")
            tab.grid_columnconfigure(0, minsize=200)
            self._spike_notebook.add(tab, text=tab_label)
            diam_lo, diam_hi = spike_anchor_slider_range(tab_index, "diam")
            self._add_slider(tab, 0, diam_label, anchor_vars["diam"],
                              anchor_vars["diam_label"], diam_lo, diam_hi,
                              step=diam_step, on_change=self._on_spike_slider)
            self._build_grouped_anchor_sliders(tab, anchor_vars, self._on_spike_slider,
                                                 tab_index=tab_index, key_prefix=f"tab{tab_index}_")

        # ---- Uniform look: the same Rays/Flare sections as one tab would
        # have (the cutoff diameter itself lives above, in
        # _spike_min_diam_frame - see the note there), gridded in the same
        # cell as the notebook above - only one of the two is ever shown. ----
        self._spike_uniform_frame = ttk.Frame(frm_spikes, style="Card.TFrame")
        self._spike_uniform_frame.grid(row=18, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 4))
        self._spike_uniform_frame.grid_columnconfigure(0, minsize=200)
        self._build_grouped_anchor_sliders(self._spike_uniform_frame, self.spike_uniform,
                                             self._on_spike_slider, key_prefix="uniform_")

        # ---- Single-star editing: shown instead of the notebook/uniform
        # panel above whenever a star is Shift+Click-selected - same
        # sliders, but they read/write that one star's own override. ----
        self._spike_star_frame = ttk.Frame(frm_spikes, style="Card.TFrame")
        self._spike_star_frame.grid(row=18, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 4))
        self._spike_star_frame.grid_columnconfigure(0, minsize=200)
        ttk.Label(self._spike_star_frame, textvariable=self.spike_star_info,
                  style="Card.TLabel", justify="left", wraplength=210).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 4))
        star_frame = ttk.Frame(self._spike_star_frame, style="Card.TFrame")
        star_frame.grid_columnconfigure(0, minsize=200)
        star_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
        self._build_grouped_anchor_sliders(star_frame, self.spike_star,
                                             self._on_star_slider_change, key_prefix="star_")
        # star_frame occupies exactly row 1 of _spike_star_frame's own grid
        # regardless of its internal (collapsible-section) row count, so
        # the buttons below it just need the next two rows, not that count.
        ttk.Button(self._spike_star_frame, text="Reset this star to its size-based look",
                   style="Warn.TButton", command=self._reset_selected_star_override).grid(
            row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(4, 2))
        ttk.Button(self._spike_star_frame, text="Deselect", style="Toolbar.TButton",
                   command=self._deselect_star).grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 4))

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
            row=19, column=0, columnspan=3, sticky="w", padx=10, pady=(8, 2))
        ttk.Button(frm_spikes, text="✨ Magic Wand", style="Accent.TButton",
                   command=self._on_spike_magic_wand).grid(
            row=20, column=0, columnspan=3, sticky="ew", padx=10, pady=(2, 0))
        ttk.Label(frm_spikes, text="Spikes only: picks the standout stars and sizes their "
                                   "spikes to this image's focal length (also run when an "
                                   "image is opened)",
                  style="CardMuted.TLabel", wraplength=300, justify="left").grid(
            row=21, column=0, columnspan=3, sticky="w", padx=10, pady=(2, 8))
        ttk.Button(frm_spikes, text="Reset manual edits", style="Danger.TButton",
                   command=self._reset_spike_edits).grid(
            row=22, column=0, columnspan=3, sticky="ew", padx=10, pady=(2, 4))
        ttk.Button(frm_spikes, text="Defaults", style="Warn.TButton",
                   command=self._reset_spike_defaults).grid(
            row=23, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
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

    def _make_collapsible(self, parent, row, title, state_key, use_pack=False):
        """A titled section whose content (the returned frame - sliders go
        in it, at their own locally-numbered rows starting from 0) can be
        shown/hidden by clicking the header. `state_key` must be unique
        across the whole app - open/closed state is remembered in
        self._collapsible_state for the rest of the session (e.g.
        collapsing "Flare" on the Small tab keeps it collapsed if you
        switch to Medium, or back to Simple mode, without having to redo
        it). By default header/content are gridded at `row`/`row+1` of
        `parent`'s own grid; with use_pack=True (for a parent, like the
        left tone panel's column, that stacks sections with pack() instead
        of grid()) they're pack()ed at the bottom instead, and `row` is
        ignored - sections must then be created in the order they should
        appear."""
        is_open = self._collapsible_state.get(state_key, True)
        header = ttk.Frame(parent, style="Card.TFrame", cursor="hand2")
        arrow_var = tk.StringVar(value="▾" if is_open else "▸")
        arrow_lbl = ttk.Label(header, textvariable=arrow_var, style="Card.TLabel")
        arrow_lbl.pack(side="left")
        title_lbl = ttk.Label(header, text=title, style="CardHeading.TLabel")
        title_lbl.pack(side="left", padx=(4, 0))
        ttk.Separator(header, orient="horizontal").pack(side="left", fill="x",
                                                          expand=True, padx=(8, 0))

        content = ttk.Frame(parent, style="Card.TFrame")
        content.grid_columnconfigure(0, minsize=200)

        if use_pack:
            header.pack(fill="x", padx=8, pady=(8, 0))
            # after=header: pack() with no position option always appends
            # at the end of the packing order, so re-showing a collapsed
            # section after a later one was already packed would otherwise
            # jump it to the bottom instead of back into place.
            content.pack(fill="x", padx=8, pady=(2, 4), after=header)
        else:
            header.grid(row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=(8, 0))
            content.grid(row=row + 1, column=0, columnspan=3, sticky="ew", padx=8, pady=(2, 4))
        if not is_open:
            content.pack_forget() if use_pack else content.grid_remove()

        def _toggle(_evt=None):
            now_open = not self._collapsible_state.get(state_key, True)
            self._collapsible_state[state_key] = now_open
            arrow_var.set("▾" if now_open else "▸")
            if use_pack:
                if now_open:
                    content.pack(fill="x", padx=8, pady=(2, 4), after=header)
                else:
                    content.pack_forget()
            else:
                if now_open:
                    content.grid()
                else:
                    content.grid_remove()

        for widget in (header, arrow_lbl, title_lbl):
            widget.bind("<Button-1>", _toggle)
        return content

    def _build_grouped_anchor_sliders(self, parent, vars_dict, on_change,
                                        tab_index=None, key_prefix=""):
        """Fills `parent` with one collapsible section per SPIKE_PARAM_GROUPS
        entry ("Rays", "Flare"), each holding that group's sliders from
        SPIKE_ANCHOR_PARAM_DEFS (skipping "diam", which the caller places
        separately - see the note on _SPIKE_PARAM_GROUP). Used identically
        for a per-size tab, the Simple/Uniform panel and the per-star
        override panel, so the three stay in sync by construction rather
        than by hand-copying the same grouping three times. tab_index, if
        not None, selects that tab's own narrower slider range (see
        spike_anchor_slider_range) instead of each param's full range.
        Returns the next free row in `parent`'s own grid, for whatever the
        caller places below (e.g. the star panel's Reset/Deselect buttons)."""
        r = 0
        for group in SPIKE_PARAM_GROUPS:
            content = self._make_collapsible(parent, r, SPIKE_PARAM_GROUP_TITLES[group],
                                              f"{key_prefix}{group}")
            r += 2
            cr = 0
            for key, label, lo, hi, step, _fmt in SPIKE_ANCHOR_PARAM_DEFS:
                if key == "diam" or _SPIKE_PARAM_GROUP.get(key) != group:
                    continue
                if tab_index is not None:
                    lo, hi = spike_anchor_slider_range(tab_index, key)
                self._add_slider(content, cr, label, vars_dict[key],
                                  vars_dict[key + "_label"], lo, hi, step=step,
                                  on_change=on_change)
                cr += 2
            if group == "flare":
                # A single global value (like "Number of rays" in General),
                # not a per-size/per-star one - always bound to the same
                # Var and always re-renders via _on_spike_slider, regardless
                # of which panel (tab/Uniform/per-star) this Flare section
                # belongs to, so it stays in sync everywhere it's shown.
                self._add_slider(content, cr, "Flare ray symmetry (0 = irregular, 100 = repeats every spike)",
                                  self.spike_flare_symmetry, self.spike_flare_symmetry_label,
                                  0, 100, step=5, on_change=self._on_spike_slider)
                cr += 2
        return r

    def _build_grouped_tone_sliders(self, parent):
        """Fills `parent` (frm_ctrl, the left panel's own scrollable
        column - pack()ed, not grid()ed, hence use_pack=True) with one
        collapsible section per TONE_PARAM_GROUPS entry ("Base", "Dettaglio
        e presenza"), each holding that group's sliders from
        TONE_PARAM_DEFS. Same pattern as _build_grouped_anchor_sliders."""
        for group in TONE_PARAM_GROUPS:
            content = self._make_collapsible(parent, 0, TONE_PARAM_GROUP_TITLES[group],
                                              f"tone_{group}", use_pack=True)
            cr = 0
            for key, label, lo, hi, step, _fmt in TONE_PARAM_DEFS:
                if _TONE_PARAM_GROUP.get(key) != group:
                    continue
                self._add_slider(content, cr, label, self.tone[key],
                                  self.tone[key + "_label"], lo, hi, step=step,
                                  on_change=self._on_tone_slider)
                cr += 2

    # ---------- Standalone mode: Open/Save (main thread - file dialogs
    # can't be opened from a background thread) ----------
    def _on_open_file(self):
        if not self._confirm_discard("Open another image"):
            return
        path = filedialog.askopenfilename(
            title="Open image",
            filetypes=[("Images", "*.fits *.fit *.fts *.tif *.tiff *.jpg *.jpeg *.png"),
                       ("FITS", "*.fits *.fit *.fts"),
                       ("TIFF", "*.tif *.tiff"),
                       ("JPEG", "*.jpg *.jpeg"),
                       ("PNG", "*.png"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            self.worker.open_path(path)
        except Exception as e:
            messagebox.showerror(
                "Open failed",
                f"{format_error(e)}\n\nStandalone mode needs the astropy, "
                f"photutils and tifffile packages (pip install astropy "
                f"photutils tifffile) in addition to numpy/Pillow.")
            return
        self._on_reload()

    def _prompt_save_as(self, rgb_display):
        """Runs on the main thread (queued from _process_thread, which
        can't safely touch Tk itself) right after a standalone-mode Process
        finishes - the equivalent of Siril mode's "applies directly to the
        active image", since there's no live image here to apply to."""
        base = os.path.splitext(self.active_filename.get())[0]
        src_ext = self.worker._src_ext
        default_ext = src_ext if src_ext in _FITS_EXTS + _TIFF_EXTS + _RASTER_EXTS else ".fits"
        path = filedialog.asksaveasfilename(
            title="Save processed image",
            initialfile=f"{base}_frankSpikes{default_ext}",
            defaultextension=default_ext,
            filetypes=[("FITS", "*.fits *.fit *.fts"), ("TIFF", "*.tif *.tiff"),
                       ("JPEG", "*.jpg *.jpeg"), ("PNG", "*.png")])
        if not path:
            self.status.set("Process complete - not saved.")
            return
        try:
            self.worker.save_rgb(rgb_display, path)
            self.status.set(f"Saved: {path}")
            # the file now matches the edits that result was rendered with
            self._saved_sig = self._processed_sig
        except Exception as e:
            messagebox.showerror("Save failed", format_error(e))

    def _on_save_as_menu(self):
        """File > Save As... - re-saves the last Process() result without
        recomputing, e.g. to export a second copy in another format."""
        if self.worker.last_rgb is None:
            messagebox.showinfo("Save", 'Click "Process" first to generate '
                                         'a result to save.')
            return
        self._prompt_save_as(self.worker.last_rgb)

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
                if self.worker.standalone:
                    self.queue.put(("no_image", None))
                else:
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

            self.queue.put(("status", "Reading the image..." if self.worker.standalone
                                       else "Reading the active image from Siril..."))
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

            # Scales the default spike Length (per-anchor and Simple/
            # Uniform alike) to this image's own telescope focal length -
            # see _focal_length_to_spike_length. None (no/invalid FOCALLEN
            # keyword) leaves the hand-tuned defaults untouched, same
            # "only ever calibrate once at load, never overwrite a user
            # edit" rule as size_calibration below.
            try:
                focal_length = self.worker.get_focal_length()
            except Exception as e:
                self.worker.log(f"frankSpikes: couldn't read focal length: {e}")
                focal_length = None
            focal_calib = compute_focal_calibration(focal_length)
            length_scale = focal_calib["length_scale"]
            thickness_scale = focal_calib["thickness_scale"]
            intensity_scale = focal_calib["intensity_scale"]
            diam_scale = focal_calib["diam_scale"]
            if focal_length:
                self.worker.log(
                    f"frankSpikes: focal length={focal_length:.0f}mm -> default spike "
                    f"length scaled x{length_scale:.2f}, thickness x{thickness_scale:.2f}, "
                    f"intensity x{intensity_scale:.2f}, minimum-diameter cutoff "
                    f"x{diam_scale:.2f}")

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
            # Large - then, if diam_scale is known (see above), scaled up a
            # little further so the cutoff stays choosy about which stars
            # are "big enough" for a spike even at a focal length whose
            # whole real size range is compressed into fewer pixels. Only
            # the anchors' "diam" (where each look applies) gets set this
            # way - the other look parameters (soft flare, color, etc. -
            # Length/Thickness/Intensity are the exceptions, see above)
            # stay at their hand-tuned defaults, or whatever the user has
            # already dialled in.
            size_calibration = None
            if stars:
                fwhm_arr = np.array([s[2] for s in stars], dtype=np.float64)
                p5, p50, p90 = np.percentile(fwhm_arr, [5, 50, 90])
                ds = diam_scale or 1.0
                size_calibration = {"small": float(p5) * ds, "medium": float(p50) * ds,
                                     "large": float(p90) * ds}
                self.worker.log(
                    f"frankSpikes: calibrated star sizes for this image - "
                    f"Small={p5:.1f}px (p5) Medium={p50:.1f}px (median) "
                    f"Large={p90:.1f}px (p90)"
                    + (f", scaled x{ds:.2f} for focal length" if diam_scale else ""))

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
                                        size_calibration, length_scale, thickness_scale,
                                        intensity_scale)))
            self.queue.put(("status", "Ready. Adjust the sliders."))
        except Exception as e:
            self.queue.put(("error", format_error(e)))

    # ---------- Live preview (pure numpy, no Siril calls) ----------
    def _update_all_labels(self):
        for key, _label, _lo, _hi, _step, fmt in TONE_PARAM_DEFS:
            self.tone[key + "_label"].set(fmt.format(self.tone[key].get()))
        self.spike_rotation_label.set(f"{self.spike_rotation.get():.0f}")
        self.spike_sharpness_label.set(f"{self.spike_sharpness.get():.0f}")
        self.spike_hue_label.set(f"{self.spike_hue.get():.0f}")
        self.spike_variation_label.set(f"{self.spike_variation.get():.0f}")
        self.spike_twinkle_label.set(f"{self.spike_twinkle.get():.0f}")
        self.spike_rainbow_period_label.set(f"{self.spike_rainbow_period.get():.0f}")
        self.spike_flare_symmetry_label.set(f"{self.spike_flare_symmetry.get():.0f}")
        self.spike_uniform_min_diam_label.set(f"{self.spike_uniform_min_diam.get():.0f}")
        for key, _label, _lo, _hi, _step, fmt in SPIKE_ANCHOR_PARAM_DEFS:
            for av in self.spike_anchors:
                av[key + "_label"].set(fmt.format(av[key].get()))
            if key != "diam":
                self.spike_uniform[key + "_label"].set(fmt.format(self.spike_uniform[key].get()))
                self.spike_star[key + "_label"].set(fmt.format(self.spike_star[key].get()))

    def _on_tone_slider(self):
        """Base/Detail (left panel) sliders: cheap, so recompute and
        redraw immediately - see the note on apply_cosmetics gating every
        stage on its own param being nonzero, which is what keeps this
        cheap even as more stages are added. Spikes are independent of
        these params, so the last computed spike layer is simply reused
        rather than recomputed - this used to be the main cause of
        sluggish dragging, since every single tick was re-rendering spikes
        from scratch regardless of which slider actually moved.

        While zoomed in (zoom_mode == "manual"), only the visible crop is
        recomputed - the Fit raster covers the WHOLE image and isn't even
        on screen right now (_redraw_canvas's manual branch draws from
        _hires_rgb, not _preview_rgb), so redoing it on every drag tick
        was pure wasted work, worse the larger the image. It catches up in
        one shot as soon as the framing/zoom actually changes back to Fit
        (see _zoom_fit) or the view pans/zooms again (both already
        re-fetch a fresh crop/raster on their own)."""
        self._update_all_labels()
        if not self.loaded:
            return
        if self.zoom_mode == "manual":
            self._schedule_hires_fetch()
        else:
            self._render_preview()

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
        """The single dict apply_cosmetics takes: Base/Detail params, each
        under its own TONE_PARAM_DEFS key."""
        return {key: self.tone[key].get() for key, *_r in TONE_PARAM_DEFS}

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
            "flare_symmetry": self.spike_flare_symmetry.get(),
            "rainbow_period": self.spike_rainbow_period.get(),
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
        zero = {k: (full[k] if k in _SPIKE_GEOMETRY_KEYS else 0.0) for k in _ANCHOR_PARAM_KEYS}
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

    def _reset_tone_defaults(self):
        """Resets every left-panel control (Base, Detail) back to 0/no-
        change - the Diffraction Spikes panel's own "Reset manual edits"/
        "Defaults" buttons are unaffected, this is just the tone/color
        side."""
        for key, _label, _lo, _hi, _step, _fmt in TONE_PARAM_DEFS:
            self.tone[key].set(TONE_DEFAULTS[key])
        self._on_tone_slider()

    def _on_magic_wand(self):
        """Camera RAW Magic Wand (left panel): analyses the untouched
        source image and sets ONLY the tone sliders (see compute_tone_wand),
        then shows what it found and why. The spikes have their own Magic
        Wand (_on_spike_magic_wand)."""
        if not self.loaded or self._pristine_full is None:
            return
        tw = compute_tone_wand(self._pristine_full)
        for key, value in tw["tone"].items():
            self.tone[key].set(value)
        self._update_all_labels()
        self._on_tone_slider()
        self.worker.log("frankSpikes Magic Wand (Camera RAW):\n" + tw["report"])
        messagebox.showinfo("Magic Wand - Camera RAW", tw["report"])

    def _apply_spike_wand(self):
        """Sets ONLY the spike sliders from this image's focal length and
        detected stars (see compute_spike_wand) and returns the report -
        in whichever mode is active (Simple's single slider set, or the
        Per size tabs), never switching it. Leaves the ray count, the
        flare rays/ring/symmetry settings and per-star edits as they are.
        Run on the button and automatically once an image has loaded."""
        try:
            focal_length = self.worker.get_focal_length()
        except Exception as e:
            self.worker.log(f"frankSpikes: couldn't read focal length: {e}")
            focal_length = None
        shape = self._pristine_full.shape if self._pristine_full is not None else self.full_shape
        mode = self.spike_mode.get()
        sw = compute_spike_wand(self._stars, focal_length, shape,
                                current_rotation=self.spike_rotation.get(), mode=mode)
        if mode == "per_size":
            for av, values in zip(self.spike_anchors, sw["spike_anchors"]):
                for key, value in values.items():
                    av[key].set(value)
        else:
            self.spike_uniform_min_diam.set(sw["spike_simple"]["min_diam"])
            for key, value in sw["spike_simple"].items():
                if key != "min_diam":
                    self.spike_uniform[key].set(value)
        g = sw["spike_globals"]
        self.spike_sharpness.set(g["sharpness"])
        self.spike_variation.set(g["variation"])
        self.spike_twinkle.set(g["twinkle"])
        self.spike_rotation.set(g["rotation"])
        self._update_all_labels()
        self._on_spike_slider()
        self.worker.log("frankSpikes Magic Wand (spikes):\n" + sw["report"])
        return sw["report"]

    def _on_spike_magic_wand(self):
        """Spike Magic Wand button (spike panel)."""
        if not self.loaded:
            return
        report = self._apply_spike_wand()
        messagebox.showinfo("Magic Wand - Spikes", report)

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
        self.spike_flare_symmetry.set(d["flare_symmetry"])
        self.spike_rainbow_period.set(d["rainbow_period"])
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

    def _apply_anchor_param_scale(self, key, scale):
        """Scales one look parameter (by its SPIKE_ANCHOR_PARAM_DEFS key) -
        per-anchor and Simple/Uniform alike - by `scale`, clamped to each
        slider's own range. Shared by _apply_length_calibration/
        _apply_thickness_calibration/_apply_intensity_calibration below
        (see _reload_thread's focal-length-derived scale factors). Same
        timing/guarantee as _apply_size_calibration: runs once right after
        Reload, before the user has touched anything, and never touches
        any OTHER look parameter."""
        lo, hi = _SPIKE_ANCHOR_PARAM_FULL_RANGE[key]
        uniform_val = SPIKE_UNIFORM_DEFAULTS[key] * scale
        self.spike_uniform[key].set(min(hi, max(lo, uniform_val)))
        for tab_index, (av, defaults) in enumerate(
                zip(self.spike_anchors, SPIKE_DEFAULTS["anchors"])):
            lo_t, hi_t = spike_anchor_slider_range(tab_index, key)
            av[key].set(min(hi_t, max(lo_t, defaults[key] * scale)))
        self._update_all_labels()

    def _apply_length_calibration(self, length_scale):
        self._apply_anchor_param_scale("length", length_scale)

    def _apply_thickness_calibration(self, thickness_scale):
        self._apply_anchor_param_scale("thickness", thickness_scale)

    def _apply_intensity_calibration(self, intensity_scale):
        self._apply_anchor_param_scale("intensity", intensity_scale)

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
            self._spike_min_diam_frame.grid_remove()
            self._spike_star_frame.grid()
            self._spike_help_label.config(text=self._spike_help_star)
        elif self.spike_mode.get() == "uniform":
            self._spike_notebook.grid_remove()
            self._spike_star_frame.grid_remove()
            self._spike_uniform_frame.grid()
            self._spike_min_diam_frame.grid()
            self._spike_help_label.config(text=self._spike_help_uniform)
        else:
            self._spike_uniform_frame.grid_remove()
            self._spike_star_frame.grid_remove()
            self._spike_min_diam_frame.grid_remove()
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
        self._base_preview_rgb = apply_cosmetics(self._src_preview_rgb, self._slider_values())
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
        if self.loaded:
            # Refreshes the Fit raster (skipped on every tone-slider tick
            # while zoomed in - see _on_tone_slider) with whatever the
            # sliders currently say, in one shot, right as it becomes
            # visible again.
            self._render_preview()
        else:
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

            rgb = apply_cosmetics(rgb, vals)
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
        self._processed_sig = self._edit_signature()
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
            rgb_final = apply_cosmetics(self._pristine_full, vals)

            if spike_enabled and stars:
                self.queue.put(("status", "Process: rendering diffraction spikes..."))
                fh, fw = self.full_shape
                layer = render_spike_layer((fh, fw), 0, 0, fw, fh, stars, sparams)
                rgb_final = apply_spikes(rgb_final, layer)

            if self.worker.standalone:
                self.queue.put(("status", "Process: rendering finished..."))
                self.worker.push_rgb(rgb_final)
                self.queue.put(("processed_standalone", rgb_final))
            else:
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
                     self.full_shape, self._stars, size_calibration,
                     length_scale, thickness_scale, intensity_scale) = payload
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
                    if length_scale is not None:
                        self._apply_length_calibration(length_scale)
                    if thickness_scale is not None:
                        self._apply_thickness_calibration(thickness_scale)
                    if intensity_scale is not None:
                        self._apply_intensity_calibration(intensity_scale)
                    # Spike sliders from the spike Magic Wand (on top of
                    # the calibration above) - never allowed to break a load.
                    try:
                        self._apply_spike_wand()
                    except Exception as e:
                        self.worker.log(f"frankSpikes: spike Magic Wand failed: {format_error(e)}")
                    # the freshly opened file, with the automatic
                    # calibration above, counts as "nothing to save"
                    self._saved_sig = self._edit_signature()
                    self._processed_sig = None
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
                    # now in Siril: the edits that result was rendered with
                    # are no longer at risk when the window closes
                    self._saved_sig = self._processed_sig
                    # Stays open on purpose: each Process call pushes an
                    # independent undo checkpoint in Siril (see push_rgb),
                    # so if the result isn't liked, the user can keep
                    # adjusting sliders and Process again as many times as
                    # they want - always re-applied from the untouched
                    # pristine source, never stacked on the previous result.
                elif kind == "processed_standalone":
                    self._busy_end()
                    self._siril_busy = False
                    self.btn_process.config(state="normal")
                    self._prompt_save_as(payload)
                elif kind == "no_image":
                    self._busy_end()
                    self.status.set("Open an image (File > Open...) to get started.")
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


def _make_worker():
    """SirilWorker if sirilpy is installed AND a running Siril accepts the
    connection, FileWorker (standalone mode) otherwise - both "sirilpy
    isn't installed at all" (a standalone install - see the optional
    import at the top of this file) and "Siril isn't running right now"
    fall back the exact same way, via the same SirilConnectionError."""
    try:
        if s is None:
            raise SirilConnectionError("sirilpy is not installed")
        return SirilWorker()
    except SirilConnectionError:
        # FileWorker needs nothing beyond numpy to construct, so this
        # can't fail the same way SirilWorker() just did.
        return FileWorker()


def main():
    _make_dpi_aware()
    worker = _make_worker()

    root = tk.Tk()
    title_suffix = " (standalone)" if worker.standalone else ""
    root.title(f"frankSpikes {APP_VERSION}{title_suffix} — by Frank Sferlazza")
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
