# Physical spikes — design

Date: 2026-09-21 · Target version: 2.1.0 · Single file: `frankSpikes.py`

## 1. Goal

Add a **second, physics-based spike layer** that can be combined with the existing
(artistic) spikes, plus one change to the existing Soft flare (a long tail).
The existing effects keep rendering exactly as in 2.0.0 so the user can compare
both on real photos and mix them.

Out of scope: blooming, internal-reflection ghosts.

## 2. Correction to the earlier analysis

The earlier note claimed a spike falls as r^-2. A direct FFT check shows that is only the
far-field limit. For a thin straight vane of width `w` (fraction of aperture `D`), obstruction `ε`:

```
plateau   P = ( 4 w / (π (1+ε)) )²            (relative to the star's peak)
envelope  E(a) = 1 / (1 + (a / a_w)²),  a_w = 1 / (π w)      (a in λ/D units)
spike     I(a) = P · E(a)          for a ≳ 3 λ/D  (Airy lobes dominate closer in)
```

Measured (FFT, ε=0.3, w/D=1.56%): plateau 2.3e-4 predicted vs 2.0–4.1e-4 measured for
a = 5–30 λ/D (ratio 1.15–2.1, fringe-limited); the Airy halo away from spikes falls as
a^-3.14 (theory −3). So the physical spike is: a fast drop from the Airy lobes into a
*plateau whose level is set by vane thickness*, then a soft 1/a² tail — not a hard cliff and
not a global 1/r². Vane thickness is therefore the physical knob for both level and length.
Straight polygon edges (diaphragm blades) have no plateau: `I ≈ K/(a²)` from the start.

## 3. Change to an existing effect: Soft flare tail

New per-class/per-star key `flare_tail` (× star diameter, 0–30, default **0**), added to
`SPIKE_ANCHOR_PARAM_DEFS` right after `soft_flare`, so it appears automatically in Simple,
Per size and the per-star panel.

`_add_soft_flare` gains `tail_len_px=0.0`. When `tail_len_px <= 0` the function runs the same
code as before (bit-identical output). Otherwise:

```
tail(r) = peak · (1 + (r/σ)²)^-1.25 · fade(r),   σ = radius_px/2
fade(r) = 1 - smoothstep((r - 0.6 L) / (0.4 L)),  L = tail_len_px
out     = max(gauss(r), tail(r))          # equal at r = 2σ, so no seam
```

Bounding box padding becomes `max(3σ, L) + 1` (this also removes the square edge visible with
strong stretch when the tail is on). `soft_flare = 0` still disables the whole halo.

## 4. Physical layer

### 4.1 Architecture

* `render_physical_layer(out_shape, view_x0, view_y0, view_w, view_h, stars, cfg)` → `(H,W,3)`
  float layer in display units (0..1). Separate from `render_spike_layer`.
* Composition: `apply_spikes(apply_spikes(rgb, classic_layer), physical_layer)` (screen twice).
* Own config (`_phys_config()`), own enable checkbox (default **off**), own per-star overrides.
* Shared with the classic effect: Ctrl+Click disable/force, manual stars, Simple/Per size mode,
  the class diameters (Small/Medium/Large) and the minimum-diameter cutoff.
* Star tuples for the physical layer are `(x, y, fwhm, amp, color, forced, override)` like the
  classic ones but built by `_effective_phys_stars()` with `_phys_star_overrides`.

### 4.2 Parameters

Per class (Small/Medium/Large), per Simple set, and per star (`PHYS_PARAM_DEFS`):

| key | label | range | default |
|---|---|---|---|
| `depth` | Depth (brightness of the layer) | 0–100 | 80 |
| `extent` | Spike extent (× star diameter) | 1–60 | 20 |
| `spikes` | Spike strength | 0–200 | 100 |
| `vane` | Vane thickness (% of aperture) | 0.2–5 | 1.0 |
| `rings` | Ring strength | 0–200 | 100 |
| `obstruction` | Central obstruction (%) | 0–60 | 30 |
| `dispersion` | Chromatic dispersion | 0–200 | 100 |
| `color` | Star colour influence | 0–100 | 60 |
| `streaks` | Dust/scratch streaks (amount) | 0–100 | 0 |
| `streak_len` | Streak length (× star diameter) | 1–30 | 8 |

Global (one telescope): `aperture` ∈ {spider 4 vanes, spider 3 vanes, polygon}, `blades`
5–9 (polygon only), `rotation` 0–90°, `fft_from` (star diameter in px above which the FFT
branch is used, 3–200; 200 ≈ never).

Simple mode: `depth` and `streaks` scale from 0 at the cutoff to the slider value at 4× the
cutoff (same smoothstep-in-log-diameter blend as the classic set); the other keys are constant.
Per size: three tabs, diameters taken from the classic anchors.

### 4.3 Analytic branch (stars with fwhm < `fft_from` / 1.6)

Per star, `u = fwhm·scale/1.03` px per λ/D. Per channel `c ∈ (R,G,B)`: wavelength scale
`s_c = 1 + d·(λ_c/530 − 1)`, `d = dispersion/100`, `λ = (600, 530, 450)`; `ρ = r/(u·s_c)`;
amplitude factor `1/s_c²`.

* **Rings:** `I_ring = rings/100 · [ (2J1(x)/x − ε² 2J1(εx)/(εx)) / (1−ε²) ]²`, `x = πρ`
  (J1 by the Abramowitz–Stegun 9.4.4/9.4.6 polynomials, numpy only).
* **Spike lines:** spider 4 → 4 half-rays at `rot + k·90°`; spider 3 → 6 half-rays at
  `rot + k·60°` with plateau `P/4` and lateral width ×2; polygon `n` → edge normals at
  `rot + 90° + k·360°/n`, doubled to 2n rays when `n` is odd. Lateral profile
  `exp(−q²/2σ_q²)`, `σ_q = 0.376/(1−ε)` for vanes, `0.376/sin(π/n)` for edges. Along profile:
  vanes `P·E(a)`, edges `K_n/(π a)²`; both multiplied by `smoothstep((a−1)/2)` so the Airy
  lobes own the near field. Edge gain constants are set by the calibration test (§8).
* **Core exclusion:** whole term × `smoothstep((r − 0.5·fwhm·scale)/(0.6·fwhm·scale))`.
* **Extent fade:** × `1 − smoothstep((r − 0.75 X)/(0.25 X))`, `X = extent·fwhm·scale`.

### 4.4 FFT branch (stars with fwhm ≥ `fft_from`)

A polychromatic PSF template is computed once per parameter key and cached (LRU, 4 entries,
lock-protected): grid `N=1024`, pupil `D=64` px (λ/D = 16 px), 8 wavelengths 430–670 nm
mapped through the dispersion (`λ_eff = 530 + d(λ−530)`), pupil scaled by `530/λ_eff`, RGB via
Gaussian sensor responses (600/535/455 nm), soft-edged pupil (circle or n-gon, obstruction,
vanes). Key = (aperture, blades, rotation, obstruction, vane, dispersion).

Template channels are `g_r·I_ring + g_s·max(I_full − I_ring, 0)` where `I_ring` is the analytic
Airy for the same obstruction/dispersion (so `rings`/`spikes` sliders work in both branches)
and `I_full` is the FFT of the full pupil. A mip pyramid (2×2 area averages, 3 levels) avoids
aliasing when a star is smaller than the template scale. Each star is stamped by bilinear
sampling only inside the visible window, with the same core exclusion and extent fade.
Between `fft_from/1.6` and `fft_from` both branches are rendered and mixed with
`w = smoothstep(log-diameter)`.

### 4.5 Display mapping and colour

`I_abs = I_rel · flux`, `flux = clamp(amp/max_amp, 0.03, 1)`. Display value
`v = asinh(G·I_abs)/asinh(G)`, `G = 10^(6·depth/100)`; `depth ≤ 0` skips the star.
Channel colour multiplier: `m_c = (1 − k) + k·star_color_c`, `k = color/100`.
Layers are merged with `np.maximum` per star and clipped to [0,1].

### 4.6 Streaks

For every rendered star, `n = round(streaks/100 · 14)` thin rays with angle, length
(`0.4–1.0 × streak_len·fwhm`) and brightness (`0.3–1.0`) from a deterministic hash of
`(x, y, i)`. Profile: Gaussian across (`σ = max(0.6 px, 0.15u)`), `(1−t)^1.2` along, peak
`0.5 · streaks/100 · flux`. Same in both branches; not multiplied by depth.

## 5. Scope and overrides

* Global (Simple), per class (Per size) and per single star (Shift+Click) — like the classic set.
* `self._phys_star_overrides` mirrors `_spike_star_overrides` (same keys, cleared on Reload and
  "Reset manual edits"); the star panel shows a classic section and a physical section with
  separate reset buttons. Moving a physical slider snapshots all physical keys for that star.

## 6. UI

New `LabelFrame` "Physical spikes (beta)" below the classic sliders in the right panel:
enable checkbox, aperture radio + blades + rotation + FFT-from slider, then a notebook
(Per size) or flat frame (Simple) generated from `PHYS_PARAM_DEFS`, following the shared
Simple/Per size selector. Defaults button also resets this set.

## 7. Threading and performance

One background thread computes both layers; each layer has a cache key (config + star
list + view); only the layer whose key changed is recomputed. Template building happens in
that thread. Same code path for Fit preview, hi-res crop and Process, so they match.
Budget: 1000 stars analytic ≤ ~3 s at full frame on the dev machine; FFT template ≤ 2 s.

## 8. Tests (`tests/`, stdlib `unittest`, sirilpy stubbed, not shipped)

1. Regression: new module vs `git show v2.0.0:frankSpikes.py`, physical set off and
   `flare_tail = 0` → `np.array_equal` on Simple, Per size and override configs.
2. Tail: identical inside `2σ`, monotonic beyond, zero past `L`, box has no square edge.
3. J1 polynomials vs numerical Bessel integral (error < 2e-7).
4. Ray count: spider 4 → 4, spider 3 → 6, polygon 5/6/7 → 10/6/14 (angular histogram).
5. Airy with obstruction: first ring 1.74% (ε=0), ≈4.7% (ε=0.3), ≈10.8% (ε=0.55) ±10%.
6. Calibration (analytic vs FFT): spike axis a∈[5,25] and ring peaks within ±0.3 dex.
7. Branch seam: total luminance across the `fft_from` blend zone changes < 25%.
8. Smoke: build the Tk UI with a stub worker, read `_phys_config()`, render a layer.

## 9. Release

Version 2.1.0, README section for the new set and tail slider, in-app Help text updated.
