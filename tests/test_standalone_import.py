"""Regression test for the bug behind the standalone package failing:
frankSpikes.py used to do an unconditional top-level `import sirilpy`,
which crashes immediately (before main() even runs, let alone its own
SirilConnectionError fallback) in a standalone venv, since sirilpy is
Siril's own bundled package and isn't on PyPI - `pip install -r
requirements.txt` can never provide it. See the optional import at the
top of frankSpikes.py and _make_worker()."""
import unittest
from _harness import fs


class TestMakeWorkerWithoutSirilpy(unittest.TestCase):
    def test_falls_back_to_fileworker_when_sirilpy_is_missing(self):
        original_s = fs.s
        try:
            fs.s = None  # simulates sirilpy not being importable at all
            worker = fs._make_worker()
            self.assertIsInstance(worker, fs.FileWorker)
            self.assertTrue(worker.standalone)
        finally:
            fs.s = original_s

    def test_sirilconnectionerror_is_a_real_exception_class_even_without_sirilpy(self):
        # frankSpikes.py defines a fallback SirilConnectionError when the
        # real sirilpy import fails - this just confirms the module-level
        # symbol behaves like a normal exception class regardless of which
        # branch defined it (the stubbed sirilpy in _harness.py, or the
        # fallback), so `except SirilConnectionError` always works.
        self.assertTrue(issubclass(fs.SirilConnectionError, BaseException))
        with self.assertRaises(fs.SirilConnectionError):
            raise fs.SirilConnectionError("test")


if __name__ == "__main__":
    unittest.main()
