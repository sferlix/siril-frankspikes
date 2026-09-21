# Physical Spikes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a physics-based spike layer (analytic for small stars, FFT-stamped for large ones) that overlays the existing spikes, plus a long tail for the existing Soft flare, without changing the existing rendering.

**Architecture:** `render_physical_layer` is a new function next to `render_spike_layer`; the App renders both layers in one background thread with per-layer cache keys and composes them with two screen blends. The classic set gains one key (`flare_tail`, default 0); the physical set has its own parameter table, config, per-star overrides and UI frame.

**Tech Stack:** Python 3, numpy, Pillow, tkinter (no new dependencies; tests use stdlib `unittest`).

**Spec:** `docs/superpowers/specs/2026-09-21-physical-spikes-design.md`

## Global Constraints

- Everything stays in the single file `frankSpikes.py`; tests live in `tests/` and are not part of the installed script.
- Dependencies: numpy and Pillow only (no scipy).
- With the physical set off and `flare_tail = 0`, `render_spike_layer` output is bit-identical to tag `v2.0.0`.
- Physical set is disabled by default (`enabled = False`); `flare_tail` default is `0.0`.
- Template cache is an LRU of 4 entries, lock-protected (spec says 8; 4 keeps memory near 130 MB).
- Version string becomes `2.1.0`.
- Run tests from the repo root: `python -m unittest discover -s tests -v`.
- Commits end with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

## File Structure

- Modify: `frankSpikes.py` — tail in `_add_soft_flare`; new "Physical spikes" section placed after `apply_spikes` and before `class SirilWorker`; App state/pipeline/UI changes.
- Create: `tests/_harness.py` (sirilpy stub, module import, v2.0.0 baseline loader, star-field helper).
- Create: `tests/test_regression.py`, `tests/test_tail.py`, `tests/test_phys_primitives.py`, `tests/test_phys_analytic.py`, `tests/test_phys_fft.py`, `tests/test_phys_layer.py`, `tests/test_app_smoke.py`.
- Modify: `README.md`.

---

### Task 1: Test harness and baseline regression

**Files:**
- Create: `tests/_harness.py`
- Create: `tests/test_regression.py`

**Interfaces:**
- Produces: `_harness.fs` (current module), `_harness.base` (v2.0.0 module), `_harness.star_field(n, w, h, seed)` → list of 7-tuples `(x, y, fwhm, amp, color, forced, override)`.

- [ ] **Step 1: Write the harness**

```python
# tests/_harness.py
import os, sys, types, subprocess, tempfile, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if "sirilpy" not in sys.modules:
    _m = types.ModuleType("sirilpy")
    _m.SirilConnectionError = Exception
    _m.SirilInterface = object
    sys.modules["sirilpy"] = _m
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np
import frankSpikes as fs


def _load_baseline():
    src = subprocess.check_output(["git", "show", "v2.0.0:frankSpikes.py"], cwd=ROOT)
    path = os.path.join(tempfile.gettempdir(), "frankSpikes_v2_0_0.py")
    with open(path, "wb") as fh:
        fh.write(src)
    spec = importlib.util.spec_from_file_location("frankSpikes_v2", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = _load_baseline()


def star_field(n=60, w=800, h=600, seed=1):
    rng = np.random.default_rng(seed)
    sizes = [2.5, 4.0, 6.0, 9.0, 14.0, 22.0, 40.0]
    probs = [0.25, 0.25, 0.2, 0.15, 0.08, 0.05, 0.02]
    stars = []
    for _ in range(n):
        fwhm = float(rng.choice(sizes, p=probs))
        color = tuple(float(c) for c in rng.uniform(0.6, 1.0, 3))
        stars.append((float(rng.uniform(0, w)), float(rng.uniform(0, h)), fwhm,
                      float(rng.uniform(0.2, 1.0)), color, False, None))
    return stars
```

- [ ] **Step 2: Write the regression test**

```python
# tests/test_regression.py
import copy, unittest
import numpy as np
from _harness import fs, base, star_field

OVERRIDE_OLD = {"length": 5.0, "intensity": 150.0, "thickness": 1.2, "soft_flare": 30.0,
                "ring_flare": 15.0, "chroma": 30.0, "rainbow": 10.0, "saturation": 40.0}


def _new_anchor(a):
    return dict(a, flare_tail=0.0)


class TestClassicUnchanged(unittest.TestCase):
    def _check(self, anchors_old, view=(0, 0, 800, 600), out_shape=(600, 800)):
        old = {"anchors": anchors_old, "rays": 4, "rotation": 30.0, "hue": 0.0,
               "sharpness": 100.0, "variation": 15.0}
        new = copy.deepcopy(old)
        new["anchors"] = [_new_anchor(a) for a in anchors_old]
        stars_old = star_field()
        stars_old[3] = stars_old[3][:6] + (OVERRIDE_OLD,)
        stars_new = [s[:6] + ((dict(s[6], flare_tail=0.0) if s[6] else None),) for s in stars_old]
        a = base.render_spike_layer(out_shape, *view, stars_old, old)
        b = fs.render_spike_layer(out_shape, *view, stars_new, new)
        self.assertTrue(np.array_equal(a, b))
        self.assertGreater(float(a.max()), 0.0)

    def test_per_size_defaults(self):
        self._check(copy.deepcopy(base.SPIKE_DEFAULTS["anchors"]))

    def test_uniform_anchors(self):
        full = {k: base.SPIKE_UNIFORM_DEFAULTS[k] for k in base._ANCHOR_PARAM_KEYS}
        zero = {k: 0.0 for k in base._ANCHOR_PARAM_KEYS}
        d = base.SPIKE_UNIFORM_DEFAULTS["min_diam"]
        self._check([{"diam": d, **zero}, {"diam": d * 4.0, **full}])

    def test_scaled_view(self):
        self._check(copy.deepcopy(base.SPIKE_DEFAULTS["anchors"]),
                    view=(100, 50, 400, 300), out_shape=(150, 200))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run**

Run: `python -m unittest discover -s tests -v`
Expected: 3 tests OK (the new module ignores the extra `flare_tail` key until Task 2 uses it).

- [ ] **Step 4: Commit**

```bash
git add tests
git commit -m "Add test harness and v2.0.0 regression tests" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Soft flare tail (`flare_tail`)

**Files:**
- Modify: `frankSpikes.py` (`SPIKE_ANCHOR_PARAM_DEFS`, `SPIKE_DEFAULTS`, `SPIKE_UNIFORM_DEFAULTS`, `_ANCHOR_PARAM_KEYS`, `_interp_anchor_params`, `_add_soft_flare`, call site in `render_spike_layer`)
- Create: `tests/test_tail.py`

**Interfaces:**
- Produces: `_add_soft_flare(layer, cx, cy, radius_px, peak, tail_len_px=0.0)`; `_interp_anchor_params(anchors_sorted, fwhm, keys=None)` (keys defaults to `_ANCHOR_PARAM_KEYS`, missing values read as 0.0); anchor key `flare_tail`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tail.py
import unittest
import numpy as np
from _harness import fs


def render(tail_len_px=None, radius=20.0, peak=0.8, size=241):
    layer = np.zeros((size, size, 3), dtype=np.float32)
    if tail_len_px is None:
        fs._add_soft_flare(layer, size // 2, size // 2, radius, peak)
    else:
        fs._add_soft_flare(layer, size // 2, size // 2, radius, peak, tail_len_px)
    return layer[..., 0]


class TestTail(unittest.TestCase):
    def test_zero_tail_is_identical_to_no_argument(self):
        self.assertTrue(np.array_equal(render(None), render(0.0)))

    def test_identical_inside_two_sigma(self):
        a, b = render(None), render(60.0)
        yy, xx = np.mgrid[:241, :241]
        r = np.hypot(xx - 120, yy - 120)
        inside = r <= 20.0          # sigma = 10 -> 2 sigma
        self.assertTrue(np.array_equal(a[inside], b[inside]))

    def test_tail_is_longer_and_monotonic(self):
        row = render(60.0)[120, 120:]
        self.assertTrue(np.all(np.diff(row) <= 1e-6))
        self.assertGreater(row[30], render(None)[120, 150])

    def test_zero_past_tail_length(self):
        row = render(60.0)[120, 120:]
        self.assertEqual(float(row[61:].max()), 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest tests.test_tail -v` from repo root (or `python -m unittest discover -s tests -p "test_tail.py" -v`)
Expected: FAIL (`_add_soft_flare` takes 5 positional arguments).

- [ ] **Step 3: Implement**

In `frankSpikes.py`:

1. `SPIKE_ANCHOR_PARAM_DEFS`: insert after the `soft_flare` row:
```python
    ("flare_tail", "Soft flare tail length (x star diameter)", 0, 30, 0.5, "{:.1f}x"),
```
2. `SPIKE_DEFAULTS["anchors"]`: add `"flare_tail": 0.0,` to each of the three anchor dicts; `SPIKE_UNIFORM_DEFAULTS`: add `"flare_tail": 0.0,`.
3. `_ANCHOR_PARAM_KEYS`:
```python
_ANCHOR_PARAM_KEYS = ("length", "intensity", "thickness", "soft_flare", "flare_tail",
                      "ring_flare", "chroma", "rainbow", "saturation")
```
4. `_interp_anchor_params`: change the signature and the reads:
```python
def _interp_anchor_params(anchors_sorted, fwhm, keys=None):
    keys = _ANCHOR_PARAM_KEYS if keys is None else keys
    lo, hi = anchors_sorted[0], anchors_sorted[-1]
    if fwhm <= lo["diam"]:
        return {k: lo.get(k, 0.0) for k in keys}
    if fwhm >= hi["diam"]:
        return {k: hi.get(k, 0.0) for k in keys}
    for a, b in zip(anchors_sorted, anchors_sorted[1:]):
        if a["diam"] <= fwhm <= b["diam"]:
            ...  # unchanged span/t computation
            return {k: a.get(k, 0.0) + (b.get(k, 0.0) - a.get(k, 0.0)) * t for k in keys}
    return {k: hi.get(k, 0.0) for k in keys}
```
5. `_add_soft_flare`:
```python
def _add_soft_flare(layer, cx, cy, radius_px, peak, tail_len_px=0.0):
    ...
    sigma = radius_px * 0.5
    pad = sigma * 3.0 + 1.0
    if tail_len_px > 0:
        pad = max(pad, tail_len_px + 1.0)
    ...  # bounding box code unchanged
    falloff = np.exp(-(r ** 2) / (2.0 * sigma ** 2))
    contrib = peak * falloff
    if tail_len_px > 0:
        tail = peak * (1.0 + (r / sigma) ** 2) ** -1.25
        t = np.clip((r - 0.6 * tail_len_px) / (0.4 * tail_len_px), 0.0, 1.0)
        tail = tail * (1.0 - t * t * (3.0 - 2.0 * t))
        contrib = np.maximum(contrib, tail)
    layer[y0:y1, x0:x1, :] = np.maximum(layer[y0:y1, x0:x1, :], contrib[..., None])
```
6. Call site in `render_spike_layer`:
```python
                _add_soft_flare(layer, cx, cy, flare_radius_px, flare_peak,
                                p.get("flare_tail", 0.0) * fwhm * scale)
```

- [ ] **Step 4: Run all tests**

Run: `python -m unittest discover -s tests -v`
Expected: all pass, including the regression tests (the anchors now carry `flare_tail = 0.0`).

- [ ] **Step 5: Commit**

```bash
git add frankSpikes.py tests/test_tail.py
git commit -m "Add Soft flare tail length (default 0 = unchanged)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```


### Task 3: Physics primitives (J1, Airy with obstruction, spike geometry)

**Files:**
- Modify: `frankSpikes.py` — new section inserted after `apply_spikes` and before `class SirilWorker`.
- Create: `tests/test_phys_primitives.py`

**Interfaces:**
- Produces:
  - `PHYS_LAMBDA_REF = 530.0`, `PHYS_LAMBDA_RGB = (600.0, 530.0, 450.0)`, `PHYS_FWHM_PER_LAMD = 1.03`
  - `_smoothstep_arr(t)` → ndarray
  - `_bessel_j1(x)` → ndarray (float64)
  - `_airy_obstructed_intensity(rho, eps)` → ndarray, peak 1 at `rho = 0` (`rho` in λ/D)
  - `_phys_channel_scales(dispersion)` → list of 3 floats (R, G, B)
  - `_phys_spike_lines(aperture, blades, rotation_deg)` → list of dicts `{"angle", "kind", "gain", "lat"}`
  - `_phys_spike_along(a, ln, eps, vane_frac)` → ndarray

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_phys_primitives.py
import unittest
import numpy as np
from _harness import fs


def j1_ref(x):
    t = np.linspace(0.0, np.pi, 200001)
    f = np.cos(t - x * np.sin(t))
    return float(np.sum((f[1:] + f[:-1]) * np.diff(t)) / 2.0 / np.pi)


class TestBessel(unittest.TestCase):
    def test_matches_numeric_integral(self):
        for x in (0.001, 0.5, 1.0, 2.9, 3.0, 3.1, 5.0, 10.0, 50.0, 100.0, 200.0):
            self.assertAlmostEqual(float(fs._bessel_j1(np.array([x]))[0]), j1_ref(x), delta=5e-7, msg=str(x))

    def test_odd(self):
        self.assertAlmostEqual(float(fs._bessel_j1(np.array([-2.0]))[0]), -j1_ref(2.0), delta=5e-7)


class TestAiry(unittest.TestCase):
    def test_peak_and_first_zero(self):
        self.assertAlmostEqual(float(fs._airy_obstructed_intensity(np.array([0.0]), 0.0)[0]), 1.0, places=6)
        self.assertLess(float(fs._airy_obstructed_intensity(np.array([1.2197]), 0.0)[0]), 1e-3)

    def test_first_ring_levels(self):
        rho = np.linspace(1.3, 2.0, 2000)
        for eps, want in ((0.0, 0.0174), (0.3, 0.0473), (0.55, 0.1082)):
            got = float(fs._airy_obstructed_intensity(rho, eps).max())
            self.assertAlmostEqual(got, want, delta=0.1 * want, msg=str(eps))


class TestGeometry(unittest.TestCase):
    def _angles(self, lines):
        return sorted(round(l["angle"] % 360.0, 3) for l in lines)

    def test_ray_counts(self):
        self.assertEqual(len(fs._phys_spike_lines("spider4", 6, 0.0)), 4)
        self.assertEqual(len(fs._phys_spike_lines("spider3", 6, 0.0)), 6)
        for n, want in ((5, 10), (6, 6), (7, 14), (8, 8), (9, 18)):
            self.assertEqual(len(fs._phys_spike_lines("polygon", n, 0.0)), want, msg=str(n))

    def test_spider4_angles_follow_rotation(self):
        self.assertEqual(self._angles(fs._phys_spike_lines("spider4", 6, 20.0)), [20.0, 110.0, 200.0, 290.0])

    def test_channel_scales(self):
        r, g, b = fs._phys_channel_scales(100.0)
        self.assertAlmostEqual(g, 1.0)
        self.assertAlmostEqual(r, 600.0 / 530.0, places=6)
        self.assertAlmostEqual(b, 450.0 / 530.0, places=6)
        self.assertEqual(fs._phys_channel_scales(0.0), [1.0, 1.0, 1.0])

    def test_vane_plateau_matches_formula(self):
        ln = fs._phys_spike_lines("spider4", 6, 0.0)[0]
        w, eps = 0.0156, 0.3
        P = (4 * w / (np.pi * (1 + eps))) ** 2
        got = float(fs._phys_spike_along(np.array([10.0]), ln, eps, w)[0])
        self.assertAlmostEqual(got, P / (1 + (np.pi * w * 10.0) ** 2), delta=1e-9)

    def test_near_field_turned_off(self):
        ln = fs._phys_spike_lines("spider4", 6, 0.0)[0]
        self.assertEqual(float(fs._phys_spike_along(np.array([0.5]), ln, 0.3, 0.01)[0]), 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest discover -s tests -p "test_phys_primitives.py" -v`
Expected: FAIL/ERROR (`_bessel_j1` not defined).

- [ ] **Step 3: Implement** (new section in `frankSpikes.py`, after `apply_spikes`)

```python
# ---------------------------------------------------------------------------
# Physical spikes (second layer; see docs/superpowers/specs/2026-09-21-physical-spikes-design.md)
# ---------------------------------------------------------------------------
PHYS_LAMBDA_REF = 530.0
PHYS_LAMBDA_RGB = (600.0, 530.0, 450.0)
PHYS_FWHM_PER_LAMD = 1.03     # Airy core FWHM in units of lambda/D


def _smoothstep_arr(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _bessel_j1(x):
    """Bessel J1 with the Abramowitz & Stegun 9.4.4 / 9.4.6 polynomials (numpy
    only, so no scipy dependency inside Siril's Python)."""
    x = np.asarray(x, dtype=np.float64)
    ax = np.abs(x)
    out = np.empty_like(ax)
    small = ax <= 3.0
    t = (ax[small] / 3.0) ** 2
    out[small] = ax[small] * (0.5 + t * (-0.56249985 + t * (0.21093573 + t * (
        -0.03954289 + t * (0.00443319 + t * (-0.00031761 + t * 0.00001109))))))
    big = ~small
    xb = ax[big]
    y = 3.0 / xb
    f1 = 0.79788456 + y * (0.00000156 + y * (0.01659667 + y * (0.00017105 + y * (
        -0.00249511 + y * (0.00113653 + y * -0.00020033)))))
    th = xb - 2.35619449 + y * (0.12499612 + y * (0.00005650 + y * (-0.00637879 + y * (
        0.00074348 + y * (0.00079824 + y * -0.00029166)))))
    out[big] = f1 * np.cos(th) / np.sqrt(xb)
    return np.sign(x) * out


def _airy_obstructed_intensity(rho, eps):
    """Airy pattern intensity (peak 1) of a circular aperture with central
    obstruction ratio `eps`, at radius `rho` in lambda/D units."""
    x = np.maximum(np.pi * np.asarray(rho, dtype=np.float64), 1e-9)
    a = 2.0 * _bessel_j1(x) / x
    if eps > 0.0:
        b = 2.0 * _bessel_j1(eps * x) / (eps * x)
        a = (a - eps * eps * b) / (1.0 - eps * eps)
    return a * a


def _phys_channel_scales(dispersion):
    """Per-channel (R,G,B) scale of the diffraction pattern: proportional to
    wavelength, blended toward 1 by dispersion (100 = physical)."""
    d = dispersion / 100.0
    return [1.0 + d * (lam / PHYS_LAMBDA_REF - 1.0) for lam in PHYS_LAMBDA_RGB]


# Edge-diffraction gain constants for polygon apertures, set by the calibration
# test against the FFT (tests/test_phys_fft.py). 1.0 until calibrated.
PHYS_EDGE_KAPPA_EVEN = 1.0
PHYS_EDGE_KAPPA_ODD = 1.0
PHYS_VANE_LAT = 0.376         # sigma of the lateral profile per unit (D / vane length)


def _phys_spike_lines(aperture, blades, rotation_deg):
    """Half-rays of the diffraction pattern as dicts: angle (deg, image
    coordinates), kind ("vane"|"edge"), gain (intensity multiplier), lat
    (lateral sigma in lambda/D before the obstruction correction)."""
    rot = float(rotation_deg)
    lines = []
    if aperture == "spider4":
        for k in range(4):
            lines.append({"angle": rot + 90.0 * k, "kind": "vane", "gain": 1.0, "lat": PHYS_VANE_LAT})
    elif aperture == "spider3":
        for k in range(6):
            lines.append({"angle": rot + 60.0 * k, "kind": "vane", "gain": 0.25, "lat": 2.0 * PHYS_VANE_LAT})
    else:
        n = int(blades)
        edge = np.sin(np.pi / n)
        area = (n / 8.0) * np.sin(2.0 * np.pi / n)
        kappa = PHYS_EDGE_KAPPA_ODD if n % 2 else PHYS_EDGE_KAPPA_EVEN
        gain = kappa * (edge / area) ** 2
        for k in range(n):
            ang = rot + 90.0 + 360.0 * k / n
            lines.append({"angle": ang, "kind": "edge", "gain": gain, "lat": PHYS_VANE_LAT / edge})
            if n % 2:
                lines.append({"angle": ang + 180.0, "kind": "edge", "gain": gain, "lat": PHYS_VANE_LAT / edge})
    return lines


def _phys_spike_along(a, ln, eps, vane_frac):
    """Intensity (relative to the star's peak) along a spike at distance `a`
    (lambda/D units, >= 0): vane plateau P/(1+(a/a_w)^2) or edge K/(pi a)^2,
    switched on beyond the Airy near field."""
    turn_on = _smoothstep_arr((a - 1.0) / 2.0)
    if ln["kind"] == "vane":
        plateau = (4.0 * vane_frac / (np.pi * (1.0 + eps))) ** 2 * ln["gain"]
        a_w = 1.0 / (np.pi * vane_frac)
        prof = plateau / (1.0 + (a / a_w) ** 2)
    else:
        prof = ln["gain"] / (np.pi * np.maximum(a, 1e-3)) ** 2
    return prof * turn_on
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m unittest discover -s tests -v`
Expected: all pass. If a Bessel or ring-level assertion fails, fix the code/constants, not the tolerances.

- [ ] **Step 5: Commit**

```bash
git add frankSpikes.py tests/test_phys_primitives.py
git commit -m "Add physical-spike primitives: J1, obstructed Airy, spike geometry" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

### Task 4: Analytic branch drawing (rings, spikes, streaks)

**Files:**
- Modify: `frankSpikes.py` (physical section)
- Create: `tests/test_phys_analytic.py`

**Interfaces:**
- Consumes: everything from Task 3.
- Produces (canvas convention: `cv` is an `(h, w, 3)` float32 array whose pixel `(i, j)` is layer pixel `(oy + i, ox + j)`; `cx, cy` are in layer coordinates; `p` is a dict of the physical keys from `PHYS_PARAM_DEFS`, see Task 7 for the table; `flux` is a float in [0.03, 1]):
  - `_phys_clip_box(x0, y0, x1, y1, w, h)` → `(ix0, iy0, ix1, iy1)` ints or `None`
  - `_phys_mask(r, fwhm_px, extent_px)` → ndarray (core exclusion × extent fade)
  - `_phys_draw_analytic(cv, ox, oy, cx, cy, fwhm_px, u, p, lines, star_color, flux, blades=6)` → None (draws rings and spikes with `np.maximum`)
  - `_phys_draw_streaks(cv, ox, oy, cx, cy, fwhm_px, u, p, star_color, flux, sx, sy)` → None (`sx, sy` = star position used to seed the hash)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_phys_analytic.py
import unittest
import numpy as np
from _harness import fs

P0 = {"depth": 90.0, "extent": 30.0, "spikes": 100.0, "vane": 1.0, "rings": 100.0,
      "obstruction": 30.0, "dispersion": 0.0, "color": 0.0, "streaks": 0.0, "streak_len": 8.0}
FWHM = 6.0
U = FWHM / fs.PHYS_FWHM_PER_LAMD
SIZE = 601
C = SIZE // 2


def draw(p, aperture="spider4", blades=6, rot=0.0):
    cv = np.zeros((SIZE, SIZE, 3), np.float32)
    lines = fs._phys_spike_lines(aperture, blades, rot)
    fs._phys_draw_analytic(cv, 0, 0, float(C), float(C), FWHM, U, p, lines, (1.0, 1.0, 1.0), 1.0, blades)
    return cv


def arcs(v):
    on = v > 0.5 * v.max()
    return int(np.sum(on & ~np.roll(on, 1)))


def ring_samples(cv, radius, ch=1):
    th = np.radians(np.arange(360))
    ys = np.round(C + radius * np.sin(th)).astype(int)
    xs = np.round(C + radius * np.cos(th)).astype(int)
    return cv[ys, xs, ch]


class TestAnalytic(unittest.TestCase):
    def test_depth_zero_draws_nothing(self):
        self.assertEqual(float(draw(dict(P0, depth=0.0)).max()), 0.0)

    def test_spike_ray_counts(self):
        only_spikes = dict(P0, rings=0.0)
        self.assertEqual(arcs(ring_samples(draw(only_spikes, "spider4"), 8 * FWHM)), 4)
        self.assertEqual(arcs(ring_samples(draw(only_spikes, "spider3"), 8 * FWHM)), 6)
        self.assertEqual(arcs(ring_samples(draw(only_spikes, "polygon", 5), 8 * FWHM)), 10)
        self.assertEqual(arcs(ring_samples(draw(only_spikes, "polygon", 7), 8 * FWHM)), 14)

    def test_rotation_moves_spikes(self):
        v = ring_samples(draw(dict(P0, rings=0.0), "spider4", rot=20.0), 8 * FWHM)
        self.assertLessEqual(abs(int(np.argmax(v)) - 20), 3)

    def test_first_ring_radius(self):
        cv = draw(dict(P0, spikes=0.0))
        row = cv[C, C:, 1]
        lo, hi = int(1.3 * U), int(2.0 * U)
        peak = (lo + int(np.argmax(row[lo:hi]))) / U
        self.assertAlmostEqual(peak, 1.63, delta=0.12)

    def test_dispersion_widens_red_rings(self):
        cv = draw(dict(P0, spikes=0.0, dispersion=100.0))
        lo, hi = int(1.2 * U), int(2.6 * U)
        r_red = lo + int(np.argmax(cv[C, C + lo:C + hi, 0]))
        r_blue = lo + int(np.argmax(cv[C, C + lo:C + hi, 2]))
        self.assertAlmostEqual(r_red / r_blue, 600.0 / 450.0, delta=0.08)

    def test_core_is_excluded(self):
        cv = draw(P0)
        self.assertLess(float(cv[C, C, 1]), 0.05)


class TestStreaks(unittest.TestCase):
    def test_streaks_deterministic_and_outside_core(self):
        def go():
            cv = np.zeros((SIZE, SIZE, 3), np.float32)
            fs._phys_draw_streaks(cv, 0, 0, float(C), float(C), FWHM, U, dict(P0, streaks=100.0),
                                  (1.0, 1.0, 1.0), 1.0, 100.0, 200.0)
            return cv
        a, b = go(), go()
        self.assertTrue(np.array_equal(a, b))
        self.assertGreater(float(a.max()), 0.05)
        yy, xx = np.mgrid[:SIZE, :SIZE]
        far = np.hypot(xx - C, yy - C) > 4 * FWHM
        self.assertGreater(float(a[far].max()), 0.0)

    def test_zero_streaks_draws_nothing(self):
        cv = np.zeros((SIZE, SIZE, 3), np.float32)
        fs._phys_draw_streaks(cv, 0, 0, float(C), float(C), FWHM, U, dict(P0, streaks=0.0),
                              (1.0, 1.0, 1.0), 1.0, 1.0, 2.0)
        self.assertEqual(float(cv.max()), 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest discover -s tests -p "test_phys_analytic.py" -v`
Expected: ERROR (`_phys_draw_analytic` not defined).

- [ ] **Step 3: Implement** (append to the physical section)

```python
def _phys_clip_box(x0, y0, x1, y1, w, h):
    ix0, iy0 = int(max(0, np.floor(x0))), int(max(0, np.floor(y0)))
    ix1, iy1 = int(min(w, np.ceil(x1) + 1)), int(min(h, np.ceil(y1) + 1))
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    return ix0, iy0, ix1, iy1


def _phys_mask(r, fwhm_px, extent_px):
    """Core exclusion (the star already has its own core) times a smooth fade
    to zero at the spike extent."""
    core = _smoothstep_arr((r - 0.5 * fwhm_px) / (0.6 * fwhm_px))
    ext = 1.0 - _smoothstep_arr((r - 0.75 * extent_px) / (0.25 * extent_px))
    return core * ext


def _phys_display(I, G, norm):
    return np.arcsinh(G * I) / norm


def _phys_color_mult(p, star_color):
    k = min(1.0, max(0.0, p["color"] / 100.0))
    return [(1.0 - k) + k * float(star_color[c]) for c in range(3)]


def _phys_strip_box(cx, cy, angle_deg, length, half_w, w, h):
    th = np.radians(angle_deg)
    c, s = np.cos(th), np.sin(th)
    nx, ny = -s * half_w, c * half_w
    xs = (cx + nx, cx - nx, cx + c * length + nx, cx + c * length - nx)
    ys = (cy + ny, cy - ny, cy + s * length + ny, cy + s * length - ny)
    return _phys_clip_box(min(xs), min(ys), max(xs), max(ys), w, h)


def _phys_draw_analytic(cv, ox, oy, cx, cy, fwhm_px, u, p, lines, star_color, flux, blades=6):
    """Closed-form rings + spikes of one star into canvas `cv` (see spec 4.3)."""
    if p["depth"] <= 0.0:
        return
    ch, cw = cv.shape[:2]
    eps = min(0.95, max(0.0, p["obstruction"] / 100.0))
    vane = max(p["vane"] / 100.0, 1e-4)
    scales = _phys_channel_scales(p["dispersion"])
    G = 10.0 ** (6.0 * p["depth"] / 100.0)
    norm = np.arcsinh(G)
    mult = _phys_color_mult(p, star_color)
    X = max(p["extent"] * fwhm_px, 1.0)
    rings_gain, spikes_gain = p["rings"] / 100.0, p["spikes"] / 100.0
    lx, ly = cx - ox, cy - oy

    if rings_gain > 0.0:
        R = min(X, 24.0 * u * max(scales))
        box = _phys_clip_box(lx - R, ly - R, lx + R, ly + R, cw, ch)
        if box is not None:
            x0, y0, x1, y1 = box
            yy, xx = np.mgrid[y0:y1, x0:x1]
            r = np.hypot(xx - lx, yy - ly)
            mask = _phys_mask(r, fwhm_px, X) * (1.0 - _smoothstep_arr((r - 0.8 * R) / (0.2 * R)))
            for c in range(3):
                sc = scales[c]
                I = rings_gain * _airy_obstructed_intensity(r / (u * sc), eps) / (sc * sc) * flux
                v = _phys_display(I, G, norm) * mask * mult[c]
                sub = cv[y0:y1, x0:x1, c]
                np.maximum(sub, v.astype(np.float32), out=sub)

    if spikes_gain > 0.0:
        for ln in lines:
            sigq = ln["lat"] / (1.0 - eps) if ln["kind"] == "vane" else ln["lat"]
            half_w = 4.5 * sigq * u * max(scales) + 1.0
            box = _phys_strip_box(lx, ly, ln["angle"], X, half_w, cw, ch)
            if box is None:
                continue
            x0, y0, x1, y1 = box
            yy, xx = np.mgrid[y0:y1, x0:x1]
            dx, dy = xx - lx, yy - ly
            r = np.hypot(dx, dy)
            mask = _phys_mask(r, fwhm_px, X)
            th = np.radians(ln["angle"])
            ca, sa = np.cos(th), np.sin(th)
            for c in range(3):
                sc = scales[c]
                uc = u * sc
                a = (dx * ca + dy * sa) / uc
                q = (-dx * sa + dy * ca) / uc
                along = _phys_spike_along(np.maximum(a, 0.0), ln, eps, vane) * (a > 0.0)
                I = spikes_gain * along * np.exp(-(q * q) / (2.0 * sigq * sigq)) / (sc * sc) * flux
                v = _phys_display(I, G, norm) * mask * mult[c]
                sub = cv[y0:y1, x0:x1, c]
                np.maximum(sub, v.astype(np.float32), out=sub)


def _phys_hash01(x, y, i, salt):
    a, b = _star_jitter_pair(x * (1.0 + 0.137 * salt) + 13.7 * i, y * (1.0 + 0.071 * salt) + 7.3 * i)
    return 0.5 * (a + 1.0) if salt % 2 == 0 else 0.5 * (b + 1.0)


def _phys_draw_streaks(cv, ox, oy, cx, cy, fwhm_px, u, p, star_color, flux, sx, sy):
    """Thin dust/scratch streaks with deterministic random angle, length and
    brightness (seeded by the star's own position). Display units, not
    multiplied by depth."""
    amount = p["streaks"] / 100.0
    if amount <= 0.0:
        return
    ch, cw = cv.shape[:2]
    lx, ly = cx - ox, cy - oy
    mult = _phys_color_mult(p, star_color)
    sigma = max(0.6, 0.15 * u)
    n = int(round(amount * 14.0))
    for i in range(n):
        ang = 360.0 * _phys_hash01(sx, sy, i, 0)
        length = (0.4 + 0.6 * _phys_hash01(sx, sy, i, 1)) * p["streak_len"] * fwhm_px
        bright = 0.3 + 0.7 * _phys_hash01(sx, sy, i, 2)
        peak = 0.5 * amount * flux * bright
        box = _phys_strip_box(lx, ly, ang, length, 4.0 * sigma + 1.0, cw, ch)
        if box is None:
            continue
        x0, y0, x1, y1 = box
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dx, dy = xx - lx, yy - ly
        th = np.radians(ang)
        along = dx * np.cos(th) + dy * np.sin(th)
        perp = -dx * np.sin(th) + dy * np.cos(th)
        t = np.clip(along / max(length, 1e-6), 0.0, 1.0)
        prof = np.exp(-(perp * perp) / (2.0 * sigma * sigma)) * (1.0 - t) ** 1.2 * (along > 0.0)
        prof = prof * _smoothstep_arr((np.hypot(dx, dy) - 0.5 * fwhm_px) / (0.6 * fwhm_px))
        for c in range(3):
            sub = cv[y0:y1, x0:x1, c]
            np.maximum(sub, (peak * prof * mult[c]).astype(np.float32), out=sub)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m unittest discover -s tests -v`
Expected: all pass. If `test_first_ring_radius` or the arc counts fail, debug the drawing code (mask, half-width, angle sign) rather than loosening thresholds.

- [ ] **Step 5: Commit**

```bash
git add frankSpikes.py tests/test_phys_analytic.py
git commit -m "Add analytic physical rings, spikes and streaks" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

### Task 5: FFT template, cache and stamping (large stars)

**Files:**
- Modify: `frankSpikes.py` (add `import collections` next to the other imports; physical section)
- Create: `tests/test_phys_fft.py`

**Interfaces:**
- Consumes: Task 3 (`_airy_obstructed_intensity`, `_phys_spike_lines`, `_phys_spike_along`) and Task 4 (`_phys_clip_box`, `_phys_mask`, `_phys_display`, `_phys_color_mult`, `_smoothstep_arr`).
- Produces:
  - `_PHYS_TPL_N = 1024`, `_PHYS_TPL_D = 64.0`, `_PHYS_TPL_LAMD = 16.0`
  - `_phys_pupil(N, D, eps, aperture, blades, rotation_deg, vane_frac, with_vanes=True)` → `(N, N)` float32
  - `_phys_template(aperture, blades, rotation_deg, eps, vane_frac, dispersion)` → dict `{"N": int, "ring": [4 arrays], "spk": [4 arrays]}`; each array `(N/2^l, N/2^l, 3)` float32, relative intensity per RGB channel, peak of the green ring = 1 at the centre pixel `(N/2, N/2)`; cached (LRU 4, lock-protected)
  - `_phys_bilinear(arr, fx, fy)` → `(h, w, 3)`
  - `_phys_draw_fft(cv, ox, oy, cx, cy, fwhm_px, u, p, tpl, star_color, flux)` → None

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_phys_fft.py
import unittest
import numpy as np
from _harness import fs

P = {"depth": 90.0, "extent": 30.0, "spikes": 100.0, "vane": 1.0, "rings": 100.0,
     "obstruction": 30.0, "dispersion": 0.0, "color": 0.0, "streaks": 0.0, "streak_len": 8.0}


def dex(a, b):
    return abs(np.log10(max(a, 1e-30) / max(b, 1e-30)))


class TestTemplate(unittest.TestCase):
    def test_shapes_centre_and_cache(self):
        t1 = fs._phys_template("spider4", 6, 0.0, 0.3, 0.01, 0.0)
        self.assertEqual(t1["ring"][0].shape, (1024, 1024, 3))
        self.assertEqual(t1["spk"][1].shape, (512, 512, 3))
        self.assertEqual(len(t1["ring"]), 4)
        self.assertAlmostEqual(float(t1["ring"][0][512, 512, 1]), 1.0, places=3)
        self.assertIs(t1, fs._phys_template("spider4", 6, 0.0, 0.3, 0.01, 0.0))

    def test_lru_is_bounded(self):
        for rot in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0):
            fs._phys_template("spider4", 6, rot, 0.3, 0.01, 0.0)
        self.assertLessEqual(len(fs._phys_tpl_cache), 4)

    def test_dispersion_scales_channels(self):
        t = fs._phys_template("spider4", 6, 0.0, 0.0, 0.01, 100.0)
        ring = t["ring"][0]
        r_red = 16 + int(np.argmax(ring[512, 512 + 16:512 + 48, 0]))
        r_blue = 16 + int(np.argmax(ring[512, 512 + 16:512 + 48, 2]))
        self.assertGreater(r_red, r_blue)


class TestCalibration(unittest.TestCase):
    """Analytic spike model vs the FFT template (spec 8, item 6)."""

    def test_vane_spike_level(self):
        t = fs._phys_template("spider4", 6, 0.0, 0.3, 0.01, 0.0)
        spk = t["spk"][0][:, :, 1]
        ln = fs._phys_spike_lines("spider4", 6, 0.0)[0]          # +x
        for lo, hi in ((8, 12), (12, 18), (18, 26)):
            fft_val = float(spk[510:515, 512 + 16 * lo:512 + 16 * hi].mean())
            a = np.linspace(lo, hi, 60)
            model = float(fs._phys_spike_along(a, ln, 0.3, 0.01).mean())
            self.assertLess(dex(fft_val, model), 0.35, msg=f"a={lo}-{hi} fft={fft_val:.2e} model={model:.2e}")

    def test_spider3_gain(self):
        t = fs._phys_template("spider3", 6, 0.0, 0.3, 0.01, 0.0)
        spk = t["spk"][0][:, :, 1]
        ln = fs._phys_spike_lines("spider3", 6, 0.0)[0]          # +x
        lo, hi = 12, 22
        fft_val = float(spk[510:515, 512 + 16 * lo:512 + 16 * hi].mean())
        model = float(fs._phys_spike_along(np.linspace(lo, hi, 60), ln, 0.3, 0.01).mean())
        self.assertLess(dex(fft_val, model), 0.35, msg=f"fft={fft_val:.2e} model={model:.2e}")

    def test_polygon_edge_level(self):
        for n in (5, 6, 7, 8):
            t = fs._phys_template("polygon", n, 0.0, 0.0, 0.01, 0.0)
            spk = t["spk"][0][:, :, 1]
            ln = fs._phys_spike_lines("polygon", n, 0.0)[0]      # angle 90 -> +y
            lo, hi = 8, 24
            fft_val = float(spk[512 + 16 * lo:512 + 16 * hi, 510:515].mean())
            model = float(fs._phys_spike_along(np.linspace(lo, hi, 80), ln, 0.0, 0.01).mean())
            self.assertLess(dex(fft_val, model), 0.35, msg=f"n={n} fft={fft_val:.2e} model={model:.2e}")


class TestStamp(unittest.TestCase):
    def test_draw_is_symmetric_and_visible(self):
        t = fs._phys_template("spider4", 6, 0.0, 0.3, 0.01, 0.0)
        size = 801
        cv = np.zeros((size, size, 3), np.float32)
        fwhm = 16.0
        fs._phys_draw_fft(cv, 0, 0, 400.0, 400.0, fwhm, fwhm / fs.PHYS_FWHM_PER_LAMD, P, t,
                          (1.0, 1.0, 1.0), 1.0)
        self.assertGreater(float(cv.max()), 0.05)
        for d in (30, 60, 120):
            self.assertAlmostEqual(float(cv[400, 400 + d, 1]), float(cv[400, 400 - d, 1]), delta=2e-3)
        self.assertLess(float(cv[400, 400, 1]), 0.05)      # core excluded

    def test_small_scale_uses_mip(self):
        t = fs._phys_template("spider4", 6, 0.0, 0.3, 0.01, 0.0)
        cv = np.zeros((301, 301, 3), np.float32)
        fs._phys_draw_fft(cv, 0, 0, 150.0, 150.0, 4.0, 4.0 / fs.PHYS_FWHM_PER_LAMD, P, t, (1.0, 1.0, 1.0), 1.0)
        self.assertGreater(float(cv.max()), 0.02)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest discover -s tests -p "test_phys_fft.py" -v`
Expected: ERROR (`_phys_template` not defined).

- [ ] **Step 3: Implement**

Add `import collections` to the imports at the top of `frankSpikes.py`, then append to the physical section:

```python
_PHYS_TPL_N = 1024
_PHYS_TPL_D = 64.0
_PHYS_TPL_LAMD = _PHYS_TPL_N / _PHYS_TPL_D          # template px per lambda/D at 530 nm
_PHYS_TPL_LAMBDAS = np.linspace(430.0, 670.0, 8)
_PHYS_TPL_MAX = 4
_PHYS_TPL_LEVELS = 4
_PHYS_SENSOR = ((600.0, 40.0), (535.0, 40.0), (455.0, 30.0))   # (centre, sigma) of R, G, B
_phys_tpl_cache = collections.OrderedDict()
_phys_tpl_lock = threading.Lock()


def _phys_pupil(N, D, eps, aperture, blades, rotation_deg, vane_frac, with_vanes=True):
    """Soft-edged pupil transmission on an N x N grid (aperture diameter D px)."""
    y, x = np.mgrid[:N, :N].astype(np.float32)
    x -= N / 2.0
    y -= N / 2.0
    r = np.hypot(x, y)
    soft = lambda d: np.clip(d + 0.5, 0.0, 1.0)
    if aperture == "polygon":
        n = int(blades)
        apothem = D / 2.0 * np.cos(np.pi / n)
        ins = np.full_like(r, 1e9)
        for k in range(n):
            phi = np.radians(rotation_deg + 90.0 + 360.0 * k / n)
            ins = np.minimum(ins, apothem - (x * np.cos(phi) + y * np.sin(phi)))
        pup = soft(ins)
    else:
        pup = soft(D / 2.0 - r)
    if eps > 0.0:
        pup = pup * soft(r - eps * D / 2.0)
    if with_vanes and aperture != "polygon":
        w = vane_frac * D
        base = rotation_deg if aperture == "spider4" else rotation_deg + 90.0
        step, count = (90.0, 4) if aperture == "spider4" else (120.0, 3)
        for k in range(count):
            t = np.radians(base + step * k)
            along = x * np.cos(t) + y * np.sin(t)
            perp = -x * np.sin(t) + y * np.cos(t)
            cover = np.clip(np.minimum(perp + 0.5, w / 2.0) - np.maximum(perp - 0.5, -w / 2.0), 0.0, 1.0)
            pup = pup * (1.0 - cover * (along > 0.0))
    return pup.astype(np.float32)


def _phys_mips(a):
    out = [a]
    for _ in range(_PHYS_TPL_LEVELS - 1):
        b = out[-1]
        out.append(0.25 * (b[0::2, 0::2] + b[1::2, 0::2] + b[0::2, 1::2] + b[1::2, 1::2]))
    return out


def _phys_build_template(aperture, blades, rotation_deg, eps, vane_frac, dispersion):
    N, D = _PHYS_TPL_N, _PHYS_TPL_D
    d = dispersion / 100.0
    lams = _PHYS_TPL_LAMBDAS if d > 0.0 else np.array([PHYS_LAMBDA_REF])
    wts = np.array([[np.exp(-0.5 * ((l - c) / s) ** 2) for l in lams] for c, s in _PHYS_SENSOR])
    wts /= wts.sum(axis=1, keepdims=True)
    yy, xx = np.mgrid[:N, :N].astype(np.float32)
    r = np.hypot(xx - N / 2.0, yy - N / 2.0)
    ref_peak = float(_phys_pupil(N, D, eps, aperture, blades, rotation_deg, vane_frac, False).sum())
    full = np.zeros((N, N, 3), np.float32)
    ring = np.zeros((N, N, 3), np.float32)
    for i, lam in enumerate(lams):
        lam_eff = PHYS_LAMBDA_REF + d * (lam - PHYS_LAMBDA_REF)
        pup = _phys_pupil(N, D * PHYS_LAMBDA_REF / lam_eff, eps, aperture, blades, rotation_deg, vane_frac)
        F = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(pup)))
        I = ((F.real ** 2 + F.imag ** 2) / max(float(pup.sum()), 1e-9) / ref_peak).astype(np.float32)
        rho = r / (_PHYS_TPL_LAMD * lam_eff / PHYS_LAMBDA_REF)
        ir = (_airy_obstructed_intensity(rho, eps) * (PHYS_LAMBDA_REF / lam_eff) ** 2).astype(np.float32)
        for c in range(3):
            full[..., c] += wts[c, i] * I
            ring[..., c] += wts[c, i] * ir
    spk = np.maximum(full - ring, 0.0)
    return {"N": N, "ring": _phys_mips(ring), "spk": _phys_mips(spk)}


def _phys_template(aperture, blades, rotation_deg, eps, vane_frac, dispersion):
    key = (aperture, int(blades) if aperture == "polygon" else 0, round(float(rotation_deg), 2),
           round(float(eps), 3), round(float(vane_frac), 5), round(float(dispersion), 1))
    with _phys_tpl_lock:
        tpl = _phys_tpl_cache.get(key)
        if tpl is not None:
            _phys_tpl_cache.move_to_end(key)
            return tpl
    tpl = _phys_build_template(aperture, blades, rotation_deg, eps, vane_frac, dispersion)
    with _phys_tpl_lock:
        _phys_tpl_cache[key] = tpl
        while len(_phys_tpl_cache) > _PHYS_TPL_MAX:
            _phys_tpl_cache.popitem(last=False)
    return tpl


def _phys_bilinear(arr, fx, fy):
    h, w = arr.shape[:2]
    x0 = np.floor(fx).astype(np.intp)
    y0 = np.floor(fy).astype(np.intp)
    tx = (fx - x0).astype(np.float32)[..., None]
    ty = (fy - y0).astype(np.float32)[..., None]
    x0c, x1c = np.clip(x0, 0, w - 1), np.clip(x0 + 1, 0, w - 1)
    y0c, y1c = np.clip(y0, 0, h - 1), np.clip(y0 + 1, 0, h - 1)
    return ((arr[y0c, x0c] * (1 - tx) + arr[y0c, x1c] * tx) * (1 - ty)
            + (arr[y1c, x0c] * (1 - tx) + arr[y1c, x1c] * tx) * ty)


def _phys_draw_fft(cv, ox, oy, cx, cy, fwhm_px, u, p, tpl, star_color, flux):
    """Stamp one large star from the FFT template (see spec 4.4)."""
    if p["depth"] <= 0.0:
        return
    ch, cw = cv.shape[:2]
    Nt = tpl["N"]
    ratio = u / _PHYS_TPL_LAMD                     # image px per template px
    R_t = 0.49 * Nt * ratio
    X = max(p["extent"] * fwhm_px, 1.0)
    R = min(X, R_t)
    lx, ly = cx - ox, cy - oy
    box = _phys_clip_box(lx - R, ly - R, lx + R, ly + R, cw, ch)
    if box is None:
        return
    x0, y0, x1, y1 = box
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dx, dy = xx - lx, yy - ly
    r = np.hypot(dx, dy)
    level = int(np.clip(np.floor(np.log2(max(1.0 / ratio, 1.0))), 0, len(tpl["ring"]) - 1))
    div = 2.0 ** level
    fx = (dx / ratio + Nt / 2.0 + 0.5) / div - 0.5
    fy = (dy / ratio + Nt / 2.0 + 0.5) / div - 0.5
    ring = _phys_bilinear(tpl["ring"][level], fx, fy)
    spk = _phys_bilinear(tpl["spk"][level], fx, fy)
    I = (p["rings"] / 100.0 * ring + p["spikes"] / 100.0 * spk) * flux
    G = 10.0 ** (6.0 * p["depth"] / 100.0)
    norm = np.arcsinh(G)
    mask = _phys_mask(r, fwhm_px, X) * (1.0 - _smoothstep_arr((r - 0.85 * R) / (0.15 * R)))
    mult = _phys_color_mult(p, star_color)
    for c in range(3):
        v = (_phys_display(I[..., c], G, norm) * mask * mult[c]).astype(np.float32)
        sub = cv[y0:y1, x0:x1, c]
        np.maximum(sub, v, out=sub)
```

- [ ] **Step 4: Run and calibrate**

Run: `python -m unittest discover -s tests -p "test_phys_fft.py" -v`
Expected: template/stamp tests pass. If a calibration test fails, its message prints `fft=` and `model=`. Fix the model constants, not the tolerance: for polygons set `PHYS_EDGE_KAPPA_EVEN` / `PHYS_EDGE_KAPPA_ODD` to `old_kappa * fft / model` (average the ratios over the even n values 6, 8 and the odd n values 5, 7); for the vane cases adjust `PHYS_VANE_LAT` only if the lateral width test in Task 6 disagrees. Re-run until all pass.

- [ ] **Step 5: Commit**

```bash
git add frankSpikes.py tests/test_phys_fft.py
git commit -m "Add FFT PSF template, cache and stamping for large stars" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

### Task 6: `render_physical_layer` (parameter tables, branch blend, streaks)

**Files:**
- Modify: `frankSpikes.py` — constants after `SPIKE_UNIFORM_DEFAULTS`; `render_physical_layer` at the end of the physical section.
- Create: `tests/test_phys_layer.py`

**Interfaces:**
- Consumes: Tasks 2–5 (`_interp_anchor_params(anchors_sorted, fwhm, keys)`, `_phys_spike_lines`, `_phys_draw_analytic`, `_phys_draw_fft`, `_phys_draw_streaks`, `_phys_template`, `_phys_clip_box`, `_smoothstep_arr`).
- Produces:
  - `PHYS_PARAM_DEFS` (key, label, lo, hi, step, fmt), `_PHYS_PARAM_KEYS` (tuple of keys in table order)
  - `PHYS_DEFAULTS` = `{"enabled", "aperture", "blades", "rotation", "fft_from", "anchors": [3 dicts of the 10 keys]}`
  - `PHYS_UNIFORM_DEFAULTS` = dict of the 10 keys
  - `render_physical_layer(out_shape, view_x0, view_y0, view_w, view_h, stars, cfg)` → `(H, W, 3)` float32 in [0, 1]. `stars` are the 7-tuples of the classic renderer; `cfg` = `{"anchors": [dicts with "diam" + the 10 keys], "aperture": "spider4"|"spider3"|"polygon", "blades": int, "rotation": float, "fft_from": float}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_phys_layer.py
import time
import unittest
import numpy as np
from _harness import fs, star_field

FULL = {"depth": 85.0, "extent": 20.0, "spikes": 100.0, "vane": 1.0, "rings": 100.0,
        "obstruction": 30.0, "dispersion": 100.0, "color": 60.0, "streaks": 0.0, "streak_len": 8.0}


def cfg(fft_from=15.0, **over):
    a = dict(FULL, **over)
    return {"anchors": [dict(a, diam=3.0), dict(a, diam=8.0), dict(a, diam=18.0)],
            "aperture": "spider4", "blades": 6, "rotation": 0.0, "fft_from": fft_from}


def one_star(fwhm, x=300.0, y=300.0, forced=False, override=None):
    return [(x, y, fwhm, 1.0, (1.0, 0.9, 0.8), forced, override)]


def render(stars, c, shape=(600, 600)):
    return fs.render_physical_layer(shape, 0, 0, shape[1], shape[0], stars, c)


class TestLayer(unittest.TestCase):
    def test_tables(self):
        self.assertEqual(len(fs._PHYS_PARAM_KEYS), 10)
        for a in fs.PHYS_DEFAULTS["anchors"]:
            self.assertEqual(set(a), set(fs._PHYS_PARAM_KEYS))
        self.assertEqual(set(fs.PHYS_UNIFORM_DEFAULTS), set(fs._PHYS_PARAM_KEYS))
        self.assertFalse(fs.PHYS_DEFAULTS["enabled"])

    def test_empty_and_range(self):
        self.assertEqual(float(render([], cfg()).max()), 0.0)
        out = render(one_star(9.0), cfg(fft_from=200.0))
        self.assertEqual(out.dtype, np.float32)
        self.assertGreater(float(out.max()), 0.05)
        self.assertLessEqual(float(out.max()), 1.0)

    def test_below_min_diameter_is_skipped_unless_forced(self):
        self.assertEqual(float(render(one_star(1.5), cfg()).max()), 0.0)
        self.assertGreater(float(render(one_star(1.5, forced=True), cfg()).max()), 0.0)

    def test_override_used_verbatim(self):
        out = render(one_star(1.5, override=dict(FULL, depth=0.0)), cfg())
        self.assertEqual(float(out.max()), 0.0)

    def test_streaks_work_without_depth(self):
        out = render(one_star(9.0), cfg(depth=0.0, streaks=100.0))
        self.assertGreater(float(out.max()), 0.02)

    def test_analytic_and_fft_agree_in_total_light(self):
        star = one_star(14.0)
        a = render(star, cfg(fft_from=200.0))
        f = render(star, cfg(fft_from=8.0))
        ratio = float(f.sum()) / float(a.sum())
        self.assertGreater(ratio, 0.75, msg=f"ratio={ratio:.2f}")
        self.assertLess(ratio, 1.33, msg=f"ratio={ratio:.2f}")

    def test_blend_zone_is_between_the_branches(self):
        # fft_from=15 -> blend zone 9.4..15: fwhm 12 must sit between pure analytic and pure FFT
        star = one_star(12.0)
        a = float(render(star, cfg(fft_from=200.0)).sum())
        f = float(render(star, cfg(fft_from=8.0)).sum())
        b = float(render(star, cfg(fft_from=15.0)).sum())
        lo, hi = min(a, f), max(a, f)
        self.assertGreaterEqual(b, 0.9 * lo)
        self.assertLessEqual(b, 1.1 * hi)

    def test_view_offset_matches_full_frame(self):
        star = one_star(9.0, x=420.0, y=380.0)
        c = cfg(fft_from=200.0)
        full = render(star, c, (600, 600))
        crop = fs.render_physical_layer((200, 200), 320, 280, 200, 200, star, c)
        self.assertTrue(np.allclose(full[280:480, 320:520], crop, atol=1e-6))

    def test_speed_300_analytic_stars(self):
        stars = [s for s in star_field(300, 1200, 900, seed=3)]
        t0 = time.time()
        out = fs.render_physical_layer((900, 1200), 0, 0, 1200, 900, stars, cfg(fft_from=200.0))
        dt = time.time() - t0
        print(f"[speed] 300 stars, 1200x900 analytic: {dt:.2f}s")
        self.assertGreater(float(out.max()), 0.0)
        self.assertLess(dt, 30.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest discover -s tests -p "test_phys_layer.py" -v`
Expected: ERROR (`_PHYS_PARAM_KEYS` not defined).

- [ ] **Step 3: Implement the tables** (in `frankSpikes.py`, right after `SPIKE_UNIFORM_DEFAULTS`)

```python
# Physical spikes (second layer): one row per size-dependent parameter.
PHYS_PARAM_DEFS = [
    ("depth",       "Depth (brightness of the layer)",      0,   100, 5,   "{:.0f}"),
    ("extent",      "Spike extent (x star diameter)",       1,   60,  1,   "{:.0f}x"),
    ("spikes",      "Spike strength",                       0,   200, 5,   "{:.0f}"),
    ("vane",        "Vane thickness (% of aperture)",       0.2, 5,   0.1, "{:.1f}"),
    ("rings",       "Ring strength",                        0,   200, 5,   "{:.0f}"),
    ("obstruction", "Central obstruction (%)",              0,   60,  1,   "{:.0f}"),
    ("dispersion",  "Chromatic dispersion",                 0,   200, 5,   "{:.0f}"),
    ("color",       "Star colour influence",                0,   100, 5,   "{:.0f}"),
    ("streaks",     "Dust/scratch streaks (amount)",        0,   100, 5,   "{:.0f}"),
    ("streak_len",  "Streak length (x star diameter)",      1,   30,  1,   "{:.0f}x"),
]
_PHYS_PARAM_KEYS = tuple(k for k, *_ in PHYS_PARAM_DEFS)
PHYS_TAB_LABELS = SPIKE_ANCHOR_TAB_LABELS
PHYS_DEFAULTS = {
    "enabled": False,
    "aperture": "spider4",
    "blades": 6,
    "rotation": 0.0,
    "fft_from": 15.0,
    "anchors": [
        {"depth": 70.0, "extent": 8.0, "spikes": 100.0, "vane": 1.0, "rings": 60.0,
         "obstruction": 30.0, "dispersion": 100.0, "color": 60.0, "streaks": 0.0, "streak_len": 6.0},
        {"depth": 80.0, "extent": 14.0, "spikes": 100.0, "vane": 1.0, "rings": 80.0,
         "obstruction": 30.0, "dispersion": 100.0, "color": 60.0, "streaks": 0.0, "streak_len": 8.0},
        {"depth": 85.0, "extent": 25.0, "spikes": 100.0, "vane": 1.0, "rings": 100.0,
         "obstruction": 30.0, "dispersion": 100.0, "color": 60.0, "streaks": 0.0, "streak_len": 10.0},
    ],
}
PHYS_UNIFORM_DEFAULTS = {"depth": 80.0, "extent": 15.0, "spikes": 100.0, "vane": 1.0, "rings": 80.0,
                         "obstruction": 30.0, "dispersion": 100.0, "color": 60.0, "streaks": 0.0,
                         "streak_len": 8.0}
# In Simple mode only these scale from 0 at the cutoff diameter to the slider value.
PHYS_FADE_KEYS = ("depth", "streaks")
```

- [ ] **Step 4: Implement `render_physical_layer`** (end of the physical section)

```python
def render_physical_layer(out_shape, view_x0, view_y0, view_w, view_h, stars, cfg):
    """Physical spike layer (rings, spikes, streaks) for a window of the
    full-resolution image, scaled to out_shape=(out_h, out_w). Same star
    tuples and the same size-class/cutoff logic as render_spike_layer; small
    stars use the closed-form model, large ones the FFT template, with a
    log-diameter cross-fade in between (see the design spec)."""
    out_h, out_w = out_shape
    layer = np.zeros((out_h, out_w, 3), dtype=np.float32)
    if not stars or view_w <= 0:
        return layer
    anchors_sorted = sorted(cfg["anchors"], key=lambda a: a["diam"])
    min_diameter = anchors_sorted[0]["diam"]
    scale = out_w / float(view_w)
    max_amp = max((s[3] for s in stars), default=1.0) or 1.0
    fft_from = float(cfg.get("fft_from", 15.0))
    use_fft = fft_from < 200.0
    lo_t = fft_from / 1.6
    aperture, blades, rot = cfg["aperture"], int(cfg["blades"]), float(cfg["rotation"])
    lines = _phys_spike_lines(aperture, blades, rot)

    for (x, y, fwhm, amp, color, forced, override) in stars:
        if override is not None:
            p = override
        elif fwhm < min_diameter and not forced:
            continue
        else:
            p = _interp_anchor_params(anchors_sorted, max(fwhm, min_diameter), _PHYS_PARAM_KEYS)
        if p["depth"] <= 0.0 and p["streaks"] <= 0.0:
            continue
        margin = fwhm * max(p["extent"], p["streak_len"], 6.0) + fwhm
        if not (view_x0 - margin <= x <= view_x0 + view_w + margin and
                view_y0 - margin <= y <= view_y0 + view_h + margin):
            continue
        cx, cy = (x - view_x0) * scale, (y - view_y0) * scale
        fwhm_px = fwhm * scale
        u = fwhm_px / PHYS_FWHM_PER_LAMD
        flux = min(1.0, max(0.03, amp / max_amp))
        color = tuple(color)

        if p["depth"] > 0.0:
            if use_fft and fwhm >= lo_t:
                w_fft = 1.0 if fwhm >= fft_from else float(_smoothstep_arr(
                    (np.log(fwhm) - np.log(lo_t)) / (np.log(fft_from) - np.log(lo_t))))
            else:
                w_fft = 0.0
            if w_fft <= 0.0:
                _phys_draw_analytic(layer, 0, 0, cx, cy, fwhm_px, u, p, lines, color, flux, blades)
            else:
                tpl = _phys_template(aperture, blades, rot, p["obstruction"] / 100.0,
                                     p["vane"] / 100.0, p["dispersion"])
                if w_fft >= 1.0:
                    _phys_draw_fft(layer, 0, 0, cx, cy, fwhm_px, u, p, tpl, color, flux)
                else:
                    R = max(p["extent"] * fwhm_px, 1.0) + 2.0
                    box = _phys_clip_box(cx - R, cy - R, cx + R, cy + R, out_w, out_h)
                    if box is not None:
                        bx0, by0, bx1, by1 = box
                        ca = np.zeros((by1 - by0, bx1 - bx0, 3), np.float32)
                        cf = np.zeros_like(ca)
                        _phys_draw_analytic(ca, bx0, by0, cx, cy, fwhm_px, u, p, lines, color, flux, blades)
                        _phys_draw_fft(cf, bx0, by0, cx, cy, fwhm_px, u, p, tpl, color, flux)
                        sub = layer[by0:by1, bx0:bx1]
                        np.maximum(sub, w_fft * cf + (1.0 - w_fft) * ca, out=sub)

        if p["streaks"] > 0.0:
            _phys_draw_streaks(layer, 0, 0, cx, cy, fwhm_px, u, p, color, flux, x, y)

    return np.clip(layer, 0.0, 1.0)
```

- [ ] **Step 5: Run and calibrate**

Run: `python -m unittest discover -s tests -v`
Expected: all pass. If `test_analytic_and_fft_agree_in_total_light` fails, the message prints the ratio: scale the analytic branch with the constants that set spike/ring level (`PHYS_VANE_LAT`, kappas) or the ring/spike core exclusion, then re-run Task 5's calibration tests too. Note the speed line printed by `test_speed_300_analytic_stars`.

- [ ] **Step 6: Commit**

```bash
git add frankSpikes.py tests/test_phys_layer.py
git commit -m "Add render_physical_layer with analytic/FFT branches, blend and streaks" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

### Task 7: App state, config, star lists and two-layer pipeline

**Files:**
- Modify: `frankSpikes.py` — `App.__init__`, `_update_all_labels`, `_reset_spike_edits`, `_reset_spike_defaults`, `_select_star`, `_compose_preview`, `_start_spike_preview`, `_spike_preview_thread`, `_start_hires_fetch`, `_hires_fetch_thread`, `_process_thread`, `_poll_queue`; new methods.
- Create: `tests/test_app_smoke.py`

**Interfaces:**
- Consumes: Task 6 tables and `render_physical_layer`.
- Produces (all on `App`):
  - Vars: `phys_enabled` (Boolean), `phys_aperture` (String), `phys_blades`/`phys_rotation`/`phys_fft_from` (Double) each with a `*_label` StringVar, `phys_anchors` (3 dicts `key` / `key + "_label"`), `phys_uniform` (dict same shape), `phys_star` (dict same shape).
  - State: `_phys_star_overrides` (dict keyed like `_spike_star_overrides`), `_phys_layer_preview`, `_spike_layer_key`, `_phys_layer_key`.
  - `_phys_uniform_anchors()` → 2 anchor dicts; `_phys_config()` → cfg for `render_physical_layer`; `_effective_phys_stars()` → 7-tuples; `_current_phys_look_for_fwhm(fwhm)` → dict; `_on_phys_star_slider_change()`; `_reset_selected_phys_override()`; `_reset_phys_defaults()`.
  - `_poll_queue` "spike_preview" payload becomes `(gen, classic_layer_or_None, phys_layer_or_None, classic_key_or_None, phys_key_or_None)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_app_smoke.py
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
        self.root.destroy()


class TestPhysState(AppCase):
    def test_config_simple_mode(self):
        cfg = self.app._phys_config()
        self.assertEqual(len(cfg["anchors"]), 2)
        lo, hi = sorted(cfg["anchors"], key=lambda a: a["diam"])
        self.assertEqual(lo["depth"], 0.0)
        self.assertEqual(lo["streaks"], 0.0)
        self.assertAlmostEqual(hi["diam"], lo["diam"] * fs.SPIKE_UNIFORM_REF_MULT)
        self.assertEqual(hi["depth"], fs.PHYS_UNIFORM_DEFAULTS["depth"])
        self.assertEqual(lo["vane"], hi["vane"])
        self.assertEqual(cfg["aperture"], "spider4")

    def test_config_per_size_uses_classic_diameters(self):
        self.app.spike_mode.set("per_size")
        cfg = self.app._phys_config()
        self.assertEqual(len(cfg["anchors"]), 3)
        self.assertEqual([a["diam"] for a in cfg["anchors"]],
                         [av["diam"].get() for av in self.app.spike_anchors])

    def test_star_lists_have_independent_overrides(self):
        a = self.app
        a._stars = [(10.0, 10.0, 6.0, 0.5, (1, 1, 1)), (50.0, 50.0, 9.0, 0.7, (1, 1, 1)),
                    (90.0, 90.0, 7.0, 0.6, (1, 1, 1))]
        a._spike_disabled = {2}
        a._spike_manual = [(1, 30.0, 30.0, 8.0, 0.5, (1, 1, 1))]
        a._spike_star_overrides = {("auto", 0): {"length": 1.0}}
        a._phys_star_overrides = {("auto", 1): {"depth": 5.0}}
        classic, phys = a._effective_stars(), a._effective_phys_stars()
        self.assertEqual(len(classic), 3)
        self.assertEqual(len(phys), 3)
        self.assertIsNotNone(classic[0][6])
        self.assertIsNone(phys[0][6])
        self.assertIsNone(classic[1][6])
        self.assertIsNotNone(phys[1][6])
        self.assertTrue(classic[2][5] and phys[2][5])        # manual star is forced in both

    def test_defaults_reset_covers_physical_set(self):
        a = self.app
        a.phys_uniform["depth"].set(10.0)
        a.phys_rotation.set(33.0)
        a._reset_spike_defaults()
        self.assertEqual(a.phys_uniform["depth"].get(), fs.PHYS_UNIFORM_DEFAULTS["depth"])
        self.assertEqual(a.phys_rotation.get(), fs.PHYS_DEFAULTS["rotation"])

    def test_reset_edits_clears_physical_overrides(self):
        self.app._phys_star_overrides[("auto", 0)] = {"depth": 1.0}
        self.app._reset_spike_edits()
        self.assertEqual(self.app._phys_star_overrides, {})

    def test_select_star_fills_physical_sliders(self):
        a = self.app
        a._stars = [(10.0, 10.0, 12.0, 0.5, (1, 1, 1))]
        a._phys_star_overrides[("auto", 0)] = dict(fs.PHYS_UNIFORM_DEFAULTS, depth=33.0)
        a._select_star(("auto", 0))
        self.assertEqual(a.phys_star["depth"].get(), 33.0)


class TestPipeline(AppCase):
    def test_compose_applies_both_layers_in_order(self):
        a = self.app
        base = np.full((20, 20, 3), 0.1, np.float32)
        l1 = np.full((20, 20, 3), 0.2, np.float32)
        l2 = np.full((20, 20, 3), 0.3, np.float32)
        a._base_preview_rgb, a._spike_layer_preview, a._phys_layer_preview = base, l1, l2
        a.spike_enabled.set(True)
        a.phys_enabled.set(True)
        a._compose_preview()
        self.assertTrue(np.allclose(a._preview_rgb, fs.apply_spikes(fs.apply_spikes(base, l1), l2)))
        a.phys_enabled.set(False)
        a._compose_preview()
        self.assertTrue(np.allclose(a._preview_rgb, fs.apply_spikes(base, l1)))

    def test_preview_thread_renders_both_layers(self):
        a = self.app
        a.loaded = True
        a.full_shape = (60, 80)
        a._base_preview_rgb = np.zeros((60, 80, 3), np.float32)
        a._stars = [(40.0, 30.0, 12.0, 1.0, (1.0, 1.0, 1.0))]
        a.phys_enabled.set(True)
        a._start_spike_preview()
        for _ in range(400):
            self.root.update()
            if a._phys_layer_preview is not None and a._spike_layer_preview is not None:
                break
            time.sleep(0.05)
        self.assertEqual(a._phys_layer_preview.shape, (60, 80, 3))
        self.assertGreater(float(a._phys_layer_preview.max()), 0.0)
        self.assertGreater(float(a._spike_layer_preview.max()), 0.0)
        self.assertIsNotNone(a._phys_layer_key)

    def test_disabling_physical_drops_its_layer(self):
        a = self.app
        a.loaded = True
        a.full_shape = (60, 80)
        a._base_preview_rgb = np.zeros((60, 80, 3), np.float32)
        a._stars = [(40.0, 30.0, 12.0, 1.0, (1.0, 1.0, 1.0))]
        a._phys_layer_preview = np.ones((60, 80, 3), np.float32)
        a._phys_layer_key = "stale"
        a.phys_enabled.set(False)
        a.spike_enabled.set(False)
        a._start_spike_preview()
        self.assertIsNone(a._phys_layer_preview)
        self.assertIsNone(a._phys_layer_key)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest discover -s tests -p "test_app_smoke.py" -v`
Expected: ERROR/FAIL (`phys_*` attributes do not exist). If it reports SKIP for "no display", run on a machine with a display; Windows dev machine has one.

- [ ] **Step 3: Implement state in `App.__init__`**

Insert right after `self.spike_star_info = tk.StringVar(value="")`:

```python
        # ---- Physical spikes (second layer) ----
        pd = PHYS_DEFAULTS
        self.phys_enabled = tk.BooleanVar(value=pd["enabled"])
        self.phys_aperture = tk.StringVar(value=pd["aperture"])
        self.phys_blades = tk.DoubleVar(value=float(pd["blades"]))
        self.phys_rotation = tk.DoubleVar(value=pd["rotation"])
        self.phys_fft_from = tk.DoubleVar(value=pd["fft_from"])
        self.phys_blades_label = tk.StringVar(value=f"{pd['blades']:.0f}")
        self.phys_rotation_label = tk.StringVar(value=f"{pd['rotation']:.0f}")
        self.phys_fft_from_label = tk.StringVar(value=f"{pd['fft_from']:.0f}")

        def _phys_vars(values):
            out = {}
            for key, _label, _lo, _hi, _step, fmt in PHYS_PARAM_DEFS:
                out[key] = tk.DoubleVar(value=values[key])
                out[key + "_label"] = tk.StringVar(value=fmt.format(values[key]))
            return out

        self.phys_anchors = [_phys_vars(a) for a in pd["anchors"]]
        self.phys_uniform = _phys_vars(PHYS_UNIFORM_DEFAULTS)
        self.phys_star = _phys_vars(PHYS_UNIFORM_DEFAULTS)
        self._phys_star_overrides = {}     # same keys as _spike_star_overrides, independent values
        self._phys_layer_preview = None
        self._spike_layer_key = None       # cache keys: skip re-rendering a layer whose inputs did not change
        self._phys_layer_key = None
```

- [ ] **Step 4: Implement config and star-list methods** (add to `App`, e.g. after `_uniform_anchors`)

```python
    def _phys_uniform_anchors(self):
        """Simple mode for the physical set: depth and streaks scale from 0 at
        the shared cutoff to their slider value at 4x the cutoff; everything
        else is constant (see spec 4.2)."""
        min_d = self.spike_uniform_min_diam.get()
        full = {k: self.phys_uniform[k].get() for k in _PHYS_PARAM_KEYS}
        zero = dict(full, **{k: 0.0 for k in PHYS_FADE_KEYS})
        return [{"diam": min_d, **zero}, {"diam": min_d * SPIKE_UNIFORM_REF_MULT, **full}]

    def _phys_config(self):
        if self.spike_mode.get() == "uniform":
            anchors = self._phys_uniform_anchors()
        else:
            anchors = [dict({k: av[k].get() for k in _PHYS_PARAM_KEYS}, diam=cav["diam"].get())
                       for av, cav in zip(self.phys_anchors, self.spike_anchors)]
        return {
            "anchors": anchors,
            "aperture": self.phys_aperture.get(),
            "blades": int(round(self.phys_blades.get())),
            "rotation": self.phys_rotation.get(),
            "fft_from": self.phys_fft_from.get(),
        }

    def _effective_phys_stars(self):
        """Same star selection as _effective_stars() (shared disable/force/
        manual edits), with the physical set's own per-star overrides."""
        out = []
        for i, (x, y, fwhm, amp, color) in enumerate(self._stars):
            if i in self._spike_disabled:
                continue
            out.append((x, y, fwhm, amp, color, i in self._spike_forced,
                        self._phys_star_overrides.get(("auto", i))))
        for (mid, x, y, fwhm, amp, color) in self._spike_manual:
            out.append((x, y, fwhm, amp, color, True, self._phys_star_overrides.get(("manual", mid))))
        return out

    def _current_phys_look_for_fwhm(self, fwhm):
        anchors = sorted(self._phys_config()["anchors"], key=lambda a: a["diam"])
        return _interp_anchor_params(anchors, max(fwhm, anchors[0]["diam"]), _PHYS_PARAM_KEYS)

    def _on_phys_star_slider_change(self):
        self._update_all_labels()
        if self._selected_star_key is None:
            return
        self._phys_star_overrides[self._selected_star_key] = {
            k: self.phys_star[k].get() for k in _PHYS_PARAM_KEYS}
        if not self.loaded:
            return
        self._schedule_spike_preview()
        if self.zoom_mode == "manual":
            self._schedule_hires_fetch()

    def _reset_selected_phys_override(self):
        if self._selected_star_key is None:
            return
        had = self._phys_star_overrides.pop(self._selected_star_key, None) is not None
        self._select_star(self._selected_star_key)
        if had:
            self._schedule_spike_preview()

    def _reset_phys_defaults(self):
        pd = PHYS_DEFAULTS
        self.phys_enabled.set(pd["enabled"])
        self.phys_aperture.set(pd["aperture"])
        self.phys_blades.set(float(pd["blades"]))
        self.phys_rotation.set(pd["rotation"])
        self.phys_fft_from.set(pd["fft_from"])
        for av, defaults in zip(self.phys_anchors, pd["anchors"]):
            for k in _PHYS_PARAM_KEYS:
                av[k].set(defaults[k])
        for k in _PHYS_PARAM_KEYS:
            self.phys_uniform[k].set(PHYS_UNIFORM_DEFAULTS[k])
```

- [ ] **Step 5: Wire labels, resets and selection**

1. `_update_all_labels` — append:
```python
        self.phys_blades_label.set(f"{self.phys_blades.get():.0f}")
        self.phys_rotation_label.set(f"{self.phys_rotation.get():.0f}")
        self.phys_fft_from_label.set(f"{self.phys_fft_from.get():.0f}")
        for key, _label, _lo, _hi, _step, fmt in PHYS_PARAM_DEFS:
            for av in self.phys_anchors:
                av[key + "_label"].set(fmt.format(av[key].get()))
            self.phys_uniform[key + "_label"].set(fmt.format(self.phys_uniform[key].get()))
            self.phys_star[key + "_label"].set(fmt.format(self.phys_star[key].get()))
```
2. `_reset_spike_edits` — add `self._phys_star_overrides.clear()` next to `self._spike_star_overrides.clear()`.
3. `_reset_spike_defaults` — call `self._reset_phys_defaults()` just before the final `self._on_spike_slider()`.
4. `_select_star` — after the loop that fills `self.spike_star`, add:
```python
        pov = self._phys_star_overrides.get(key)
        pvals = pov if pov is not None else self._current_phys_look_for_fwhm(fwhm)
        for k in _PHYS_PARAM_KEYS:
            self.phys_star[k].set(pvals[k])
```
5. `_poll_queue`, "loaded" branch — next to `self._spike_star_overrides = {}` add `self._phys_star_overrides = {}`.

- [ ] **Step 6: Two-layer preview pipeline**

Replace `_compose_preview`:
```python
    def _compose_preview(self):
        rgb = self._base_preview_rgb
        if self.spike_enabled.get() and self._spike_layer_preview is not None:
            rgb = apply_spikes(rgb, self._spike_layer_preview)
        if self.phys_enabled.get() and self._phys_layer_preview is not None:
            rgb = apply_spikes(rgb, self._phys_layer_preview)
        self._preview_rgb = rgb
```
Replace `_start_spike_preview` (keep the debounce/inflight guard at the top exactly as it is now) with:
```python
        self._spike_preview_gen += 1
        gen = self._spike_preview_gen
        ph, pw = self._base_preview_rgb.shape[:2]
        fh, fw = self.full_shape

        stars = self._effective_stars() if self.spike_enabled.get() else []
        want_c = bool(stars)
        if not want_c:
            self._spike_layer_preview = None
            self._spike_layer_key = None
        pstars = self._effective_phys_stars() if self.phys_enabled.get() else []
        want_p = bool(pstars)
        if not want_p:
            self._phys_layer_preview = None
            self._phys_layer_key = None

        params = self._spike_config() if want_c else None
        ss = self._spike_supersample(ph, pw) if want_c else 1
        pparams = self._phys_config() if want_p else None
        ckey = repr((stars, params, ss, ph, pw)) if want_c else None
        pkey = repr((pstars, pparams, ph, pw)) if want_p else None
        need_c = want_c and ckey != self._spike_layer_key
        need_p = want_p and pkey != self._phys_layer_key
        if not (need_c or need_p):
            self._compose_preview()
            self._redraw_canvas()
            return
        self._spike_preview_inflight = True
        self._busy_begin()
        t = threading.Thread(
            target=self._spike_preview_thread,
            args=(gen, ph, pw, fh, fw, stars, params, ss, pstars, pparams, need_c, need_p, ckey, pkey),
            daemon=True)
        t.start()
```
Replace `_spike_preview_thread`:
```python
    def _spike_preview_thread(self, gen, ph, pw, fh, fw, stars, params, ss,
                              pstars, pparams, need_c, need_p, ckey, pkey):
        # Always post something, success or failure (see _poll_queue's pairing with _busy_begin).
        layer = player = None
        try:
            if need_c:
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
        try:
            if need_p:
                player = render_physical_layer((ph, pw), 0, 0, fw, fh, pstars, pparams)
        except Exception as e:
            try:
                self.worker.log(f"frankSpikes: physical spike preview render failed: {e}")
            except Exception:
                pass
        self.queue.put(("spike_preview", (gen, layer, player,
                                          ckey if layer is not None else None,
                                          pkey if player is not None else None)))
```
Replace the `"spike_preview"` branch of `_poll_queue`:
```python
                elif kind == "spike_preview":
                    gen, layer, player, ckey, pkey = payload
                    self._spike_preview_inflight = False
                    self._busy_end()
                    if gen == self._spike_preview_gen:
                        if layer is not None:
                            self._spike_layer_preview = layer
                            self._spike_layer_key = ckey
                        if player is not None:
                            self._phys_layer_preview = player
                            self._phys_layer_key = pkey
                        if layer is not None or player is not None:
                            self._compose_preview()
                            self._redraw_canvas()
```

- [ ] **Step 7: Hi-res crop and Process**

1. In `_start_hires_fetch`: `spike_state = (self.spike_enabled.get(), self._effective_stars(), self._spike_config(), self.phys_enabled.get(), self._effective_phys_stars(), self._phys_config())`.
2. In `_hires_fetch_thread`: replace the spike block with
```python
            spike_enabled, stars, sparams, phys_enabled, pstars, pparams = spike_state
            if spike_enabled and stars:
                layer = render_spike_layer((got_h, got_w), req_x, req_y, req_w, req_h, stars, sparams)
                rgb = apply_spikes(rgb, layer)
            if phys_enabled and pstars:
                player = render_physical_layer((got_h, got_w), req_x, req_y, req_w, req_h, pstars, pparams)
                rgb = apply_spikes(rgb, player)
```
3. In `_process_thread`: after reading `sparams`, add `phys_enabled = self.phys_enabled.get(); pstars = self._effective_phys_stars(); pparams = self._phys_config()`; after the classic block add
```python
            if phys_enabled and pstars:
                self.queue.put(("status", "Process: rendering physical spikes..."))
                fh, fw = self.full_shape
                player = render_physical_layer((fh, fw), 0, 0, fw, fh, pstars, pparams)
                rgb_final = apply_spikes(rgb_final, player)
```

- [ ] **Step 8: Run all tests**

Run: `python -m unittest discover -s tests -v`
Expected: all pass (regression tests still bit-identical).

- [ ] **Step 9: Commit**

```bash
git add frankSpikes.py tests/test_app_smoke.py
git commit -m "Wire the physical layer into App state, star lists and the render pipeline" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

### Task 8: UI — Physical spikes frame, mode switching, star panel

**Files:**
- Modify: `frankSpikes.py` — `_build_ui` (new frame, three grid rows move down by one), `_update_spike_mode_ui`.
- Modify: `tests/test_app_smoke.py` (add a UI test class)

**Interfaces:**
- Consumes: Task 7 vars and methods.
- Produces: `App._phys_notebook`, `App._phys_uniform_frame`, `App._phys_star_frame` (all gridded in the same cell of the "Physical spikes (beta)" frame; exactly one is visible), plus the widgets that write the Task 7 vars.

- [ ] **Step 1: Write the failing test** (append to `tests/test_app_smoke.py`)

```python
def shown(widget):
    return widget.winfo_manager() != ""


class TestPhysUI(AppCase):
    def test_simple_mode_shows_uniform_frame(self):
        a = self.app
        a.spike_mode.set("uniform")
        a._update_spike_mode_ui()
        self.assertTrue(shown(a._phys_uniform_frame))
        self.assertFalse(shown(a._phys_notebook))
        self.assertFalse(shown(a._phys_star_frame))

    def test_per_size_mode_shows_notebook_with_three_tabs(self):
        a = self.app
        a.spike_mode.set("per_size")
        a._update_spike_mode_ui()
        self.assertTrue(shown(a._phys_notebook))
        self.assertEqual(len(a._phys_notebook.tabs()), 3)
        self.assertFalse(shown(a._phys_uniform_frame))

    def test_selecting_a_star_shows_both_star_panels(self):
        a = self.app
        a._stars = [(10.0, 10.0, 12.0, 0.5, (1, 1, 1))]
        a._select_star(("auto", 0))
        self.assertTrue(shown(a._phys_star_frame))
        self.assertTrue(shown(a._spike_star_frame))
        self.assertFalse(shown(a._phys_uniform_frame))
        a._deselect_star()
        self.assertFalse(shown(a._phys_star_frame))
        self.assertTrue(shown(a._phys_uniform_frame))

    def test_moving_a_physical_star_slider_creates_an_override(self):
        a = self.app
        a._stars = [(10.0, 10.0, 12.0, 0.5, (1, 1, 1))]
        a._select_star(("auto", 0))
        a.phys_star["depth"].set(42.0)
        a._on_phys_star_slider_change()
        self.assertEqual(a._phys_star_overrides[("auto", 0)]["depth"], 42.0)
        self.assertNotIn(("auto", 0), a._spike_star_overrides)
        a._reset_selected_phys_override()
        self.assertNotIn(("auto", 0), a._phys_star_overrides)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m unittest discover -s tests -p "test_app_smoke.py" -v`
Expected: the new `TestPhysUI` tests ERROR (`_phys_uniform_frame` missing).

- [ ] **Step 3: Build the frame**

In `_build_ui`, immediately before the `self._spike_help_per_size = (...)` block, insert:

```python
        # ---- Physical spikes: a second, physics-based layer combined (screen)
        # with the classic spikes above. Follows the same Simple / Per size
        # selector and the same Shift+Click star selection. ----
        frm_phys = ttk.LabelFrame(frm_spikes, text="Physical spikes (beta)")
        frm_phys.grid(row=13, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 4))
        frm_phys.grid_columnconfigure(0, minsize=210)
        ttk.Checkbutton(frm_phys, text="Enable physical spikes", variable=self.phys_enabled,
                         command=self._on_spike_slider).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(6, 2))
        ttk.Label(frm_phys, text="Aperture", style="Card.TLabel").grid(
            row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(4, 0))
        ap_box = ttk.Frame(frm_phys, style="Card.TFrame")
        ap_box.grid(row=2, column=0, columnspan=3, sticky="w", padx=10)
        for text, val in (("Spider, 4 vanes (4 spikes)", "spider4"),
                          ("Spider, 3 vanes (6 spikes)", "spider3"),
                          ("Diaphragm blades (polygon)", "polygon")):
            ttk.Radiobutton(ap_box, text=text, value=val, variable=self.phys_aperture,
                             command=self._on_spike_slider).pack(anchor="w")
        self._add_slider(frm_phys, 3, "Blades (polygon only; odd = twice as many spikes)",
                          self.phys_blades, self.phys_blades_label, 5, 9, step=1,
                          on_change=self._on_spike_slider)
        self._add_slider(frm_phys, 5, "Rotation angle (0-90 deg)",
                          self.phys_rotation, self.phys_rotation_label, 0, 90, step=1,
                          on_change=self._on_spike_slider)
        self._add_slider(frm_phys, 7, "Use FFT model from star diameter (px, 200 = never)",
                          self.phys_fft_from, self.phys_fft_from_label, 3, 200, step=1,
                          on_change=self._on_spike_slider)

        self._phys_notebook = ttk.Notebook(frm_phys)
        self._phys_notebook.grid(row=9, column=0, columnspan=3, sticky="ew", padx=4, pady=(8, 4))
        for tab_label, av in zip(PHYS_TAB_LABELS, self.phys_anchors):
            tab = ttk.Frame(self._phys_notebook, style="Card.TFrame")
            tab.grid_columnconfigure(0, minsize=200)
            self._phys_notebook.add(tab, text=tab_label)
            r = 0
            for key, label, lo, hi, step, _fmt in PHYS_PARAM_DEFS:
                self._add_slider(tab, r, label, av[key], av[key + "_label"], lo, hi, step=step,
                                  on_change=self._on_spike_slider)
                r += 2

        self._phys_uniform_frame = ttk.Frame(frm_phys, style="Card.TFrame")
        self._phys_uniform_frame.grid(row=9, column=0, columnspan=3, sticky="ew", padx=4, pady=(8, 4))
        self._phys_uniform_frame.grid_columnconfigure(0, minsize=200)
        r = 0
        for key, label, lo, hi, step, _fmt in PHYS_PARAM_DEFS:
            self._add_slider(self._phys_uniform_frame, r, label, self.phys_uniform[key],
                              self.phys_uniform[key + "_label"], lo, hi, step=step,
                              on_change=self._on_spike_slider)
            r += 2

        self._phys_star_frame = ttk.Frame(frm_phys, style="Card.TFrame")
        self._phys_star_frame.grid(row=9, column=0, columnspan=3, sticky="ew", padx=4, pady=(8, 4))
        self._phys_star_frame.grid_columnconfigure(0, minsize=200)
        ttk.Label(self._phys_star_frame, text="Physical look of the selected star",
                  style="Card.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(4, 2))
        r = 2
        for key, label, lo, hi, step, _fmt in PHYS_PARAM_DEFS:
            self._add_slider(self._phys_star_frame, r, label, self.phys_star[key],
                              self.phys_star[key + "_label"], lo, hi, step=step,
                              on_change=self._on_phys_star_slider_change)
            r += 2
        ttk.Button(self._phys_star_frame, text="Reset this star's physical look",
                   style="Warn.TButton", command=self._reset_selected_phys_override).grid(
            row=r, column=0, columnspan=3, sticky="ew", padx=10, pady=(4, 4))
```

Then move the three widgets after it down one grid row: `self._spike_help_label` `row=13` → `row=14`, "Reset manual edits" `row=14` → `row=15`, "Defaults" `row=15` → `row=16`.

- [ ] **Step 4: Mode switching**

Replace `_update_spike_mode_ui` with:

```python
    def _update_spike_mode_ui(self):
        """Shows whichever of the notebook (per-size tabs) / flat uniform
        panel / single-star panel applies right now, for BOTH the classic set
        and the physical set, and swaps the matching help text. A star
        selection (Shift+Click) always wins over the Simple/Per-size mode."""
        if self._selected_star_key is not None:
            self._spike_notebook.grid_remove()
            self._spike_uniform_frame.grid_remove()
            self._spike_star_frame.grid()
            self._phys_notebook.grid_remove()
            self._phys_uniform_frame.grid_remove()
            self._phys_star_frame.grid()
            self._spike_help_label.config(text=self._spike_help_star)
        elif self.spike_mode.get() == "uniform":
            self._spike_notebook.grid_remove()
            self._spike_star_frame.grid_remove()
            self._spike_uniform_frame.grid()
            self._phys_notebook.grid_remove()
            self._phys_star_frame.grid_remove()
            self._phys_uniform_frame.grid()
            self._spike_help_label.config(text=self._spike_help_uniform)
        else:
            self._spike_uniform_frame.grid_remove()
            self._spike_star_frame.grid_remove()
            self._spike_notebook.grid()
            self._phys_uniform_frame.grid_remove()
            self._phys_star_frame.grid_remove()
            self._phys_notebook.grid()
            self._spike_help_label.config(text=self._spike_help_per_size)
```

- [ ] **Step 5: Run all tests**

Run: `python -m unittest discover -s tests -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add frankSpikes.py tests/test_app_smoke.py
git commit -m "Add the Physical spikes UI frame with Simple/Per size/per-star panels" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: Visual check, docs and release

**Files:**
- Create: `tests/render_demo.py` (developer script, prints the output path)
- Modify: `frankSpikes.py` (version, module docstring, Help text)
- Modify: `README.md`

- [ ] **Step 1: Demo renderer for a visual check**

```python
# tests/render_demo.py
"""Renders a synthetic star field with the classic layer, the physical layer,
and both, into demo_spikes.png next to this file (developer aid, not shipped)."""
import os
import numpy as np
from PIL import Image
from _harness import fs, star_field

W, H = 1200, 800
stars = [s for s in star_field(150, W, H, seed=5) if s[2] >= 4.0]
stars += [(300.0, 250.0, 26.0, 1.0, (1.0, 0.85, 0.7), False, None),
          (800.0, 500.0, 40.0, 1.0, (0.8, 0.9, 1.0), False, None)]
yy, xx = np.mgrid[:H, :W]
sky = np.full((H, W, 3), 0.03, np.float32)
for (x, y, fwhm, amp, color, _f, _o) in stars:
    sig = fwhm / 2.355
    g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sig ** 2))
    sky = np.clip(sky + (np.clip(3 * amp * g, 0, 1))[..., None] * np.array(color, np.float32), 0, 1)

ccfg = {"anchors": [dict(a) for a in fs.SPIKE_DEFAULTS["anchors"]], "rays": 4, "rotation": 30.0,
        "hue": 0.0, "sharpness": 100.0, "variation": 15.0}
pcfg = {"anchors": [dict(a, diam=c["diam"]) for a, c in zip(fs.PHYS_DEFAULTS["anchors"], ccfg["anchors"])],
        "aperture": "spider4", "blades": 6, "rotation": 30.0, "fft_from": 15.0}
classic = fs.render_spike_layer((H, W), 0, 0, W, H, stars, ccfg)
phys = fs.render_physical_layer((H, W), 0, 0, W, H, stars, pcfg)
panels = [fs.apply_spikes(sky, classic), fs.apply_spikes(sky, phys),
          fs.apply_spikes(fs.apply_spikes(sky, classic), phys)]
out = np.concatenate(panels, axis=0)
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_spikes.png")
Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(path)
print(path)
```

Run: `python tests/render_demo.py` and inspect the image (three stacked panels: classic, physical, both). Expected: physical spikes visible on the large stars with coloured rings, no square edges, no visible seam around the 9–15 px stars.

- [ ] **Step 2: Version, docstring, Help**

1. `APP_VERSION = "2.1.0"`.
2. In the module docstring's "Diffraction Spikes" section append: `   - Soft flare tail length: a long, power-law tail on the Soft flare (0 = unchanged).` and a paragraph `Physical spikes (beta): a second layer, combined with the classic one, with rings/spikes from aperture physics, chromatic dispersion, blades, obstruction and dust/scratch streaks; global, per size class or per star.`
3. In `_show_help`, add to the help text string a paragraph: `Physical spikes (beta): tick Enable physical spikes to add a second, physics-based layer on top of the classic one. Depth is its brightness; Spike extent, Vane thickness (thinner = dimmer and longer), Ring strength, Central obstruction, Chromatic dispersion and Dust/scratch streaks shape it. It follows Simple / Per size, and Shift+Click a star to give it its own physical look.`

- [ ] **Step 3: README**

Add to the "Diffraction Spikes" list: the Soft flare tail slider, and a "Physical spikes (beta)" bullet with the parameter list and the note that it is combined (screen) with the classic layer, is off by default, and that classic rendering is unchanged when it is off and the tail is 0.

- [ ] **Step 4: Full verification**

Run: `python -m unittest discover -s tests -v`
Expected: all tests pass; note the `[speed]` line.

- [ ] **Step 5: Commit**

```bash
git add frankSpikes.py README.md tests/render_demo.py
git commit -m "Bump to 2.1.0: document Physical spikes and the Soft flare tail" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-Review (spec coverage)

- Spec 3 (tail): Task 2. Spec 4.1–4.2 (architecture, parameters, Simple/Per size): Tasks 6, 7, 8. Spec 4.3 analytic: Tasks 3–4. Spec 4.4 FFT/blend: Tasks 5–6. Spec 4.5 display/colour: Tasks 4–6. Spec 4.6 streaks: Tasks 4, 6. Spec 5 overrides: Tasks 7–8. Spec 6 UI: Task 8. Spec 7 threading/cache keys: Task 7. Spec 8 tests: Tasks 1–9 (regression, tail, J1, ray counts, ring levels, calibration, seam, smoke). Spec 9 release: Task 9.
- Known deviation from the spec: template LRU is 4 entries, not 8 (memory); the spec is updated in the same commit as this plan.
- Type consistency: `_interp_anchor_params(anchors_sorted, fwhm, keys)`, `_phys_template(aperture, blades, rotation_deg, eps, vane_frac, dispersion)` (eps and vane as fractions), `_phys_draw_*` argument order, and the `_poll_queue` payload tuple are used identically in every task.
