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
