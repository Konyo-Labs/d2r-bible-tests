# -*- coding: utf-8 -*-
"""v3881 (REG-3388, #255) - AN INVENTORY TITLE THE OCR NEVER READ IS UNKNOWN, NEVER "NO TITLE".

stash_eye.inventory_title_visible is the vault gate's second way in (a tooltip covers the stash tabs; the INVENTORY title on
the far right still says both panels are open). It returned False whenever the OCR did not read - OCR off, no worker on that
OS (the console demos print "no OCR worker for this OS" on a runner), or an exception. The reader-parity bench (#255) then
scored those Falses as AGREEMENTS between the Mac and a Windows PC, which is a comparison of two things nobody measured.

Now: ocr_fast returning None, or an exception, answers None (UNKNOWN) and says why in _INV_TITLE_LAST; a read with no title
is still False and a read with one True. The console's caller tests truthiness, so it refuses on None exactly as on False -
no admission changes. The bench records UNKNOWN, which is never an agreement. RED_PROOF below. [[unknown-stays-unknown]]
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
os.environ.setdefault("TV_STUB", "1")
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()   # v3881 pre-flight - its mkdtemp scratch is collected (test_a_test_run_leaves_no_scratch_dirs)
import stash_eye as se  # noqa: E402
import tv_diablo as tvd  # noqa: E402


def _frame():
    from PIL import Image
    d = tempfile.mkdtemp(prefix="tvd_inv_")
    p = os.path.join(d, "f_1.jpg")
    Image.new("RGB", (1440, 936), (20, 16, 12)).save(p, "JPEG", quality=90)
    return p


class _Ocr(object):
    def __init__(self, answer):
        self.answer, self.calls = answer, 0

    def __call__(self, path):
        self.calls += 1
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


class AnUnreadTitleIsUnknown(unittest.TestCase):

    def setUp(self):
        self.keep = tvd.ocr_fast
        self.f = _frame()

    def tearDown(self):
        tvd.ocr_fast = self.keep

    def _ask(self, answer):
        tvd.ocr_fast = _Ocr(answer)
        return se.inventory_title_visible(self.f)

    def test_an_ocr_that_did_not_read_is_unknown(self):
        """* THE POINT: no read is not 'no title'"""
        self.assertIsNone(self._ask(None))
        self.assertIn("did not read", se._INV_TITLE_LAST["why"])
        self.assertIsNone(self._ask(RuntimeError("worker died")))
        self.assertIn("RuntimeError", se._INV_TITLE_LAST["why"])

    def test_baseline_a_read_still_answers_yes_and_no(self):
        """BASELINE - the reader still measures: a read title is True, a read without one is False"""
        self.assertIs(self._ask({"raw_lines": ["INVENT&RY"], "lines": []}), True)
        self.assertIsNone(se._INV_TITLE_LAST["why"])
        self.assertIs(self._ask({"raw_lines": ["GOLD 12345"], "lines": []}), False)

    def test_the_console_still_refuses_on_unknown(self):
        """the caller tests truthiness: None refuses the second way in exactly as False did"""
        import io
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertEqual(src.count("                if inventory_title_visible(str(frame_path)):\n"), 1)

    def test_the_bench_never_counts_an_unread_title_as_agreement(self):
        import reader_parity as rp
        tvd.ocr_fast = _Ocr(None)
        out = rp.run_eyes(self.f, tempfile.mkdtemp(prefix="tvd_inv_w_"))
        self.assertIsInstance(out.get("inv_title"), dict, out.get("inv_title"))
        self.assertIn("unknown", out["inv_title"])
        self.assertIsNone(rp._same(out["inv_title"], out["inv_title"]), "two unread titles counted as agreeing")


RED_PROOF = [
    {"why": "REG-3388 - an OCR that did not read answers 'no inventory title' again",
     "file": "tv/stash_eye.py",
     "find": '            _INV_TITLE_LAST["why"] = "the OCR did not read the title band (off, no worker on this OS, or an error)"\n'
             '            return None\n',
     "replace": '            _INV_TITLE_LAST["why"] = "the OCR did not read the title band (off, no worker on this OS, or an error)"\n'
                '            return False\n', "matches": 1},
    {"why": "REG-3388 - an exception reading the band answers 'no inventory title' again",
     "file": "tv/stash_eye.py",
     "find": '        _INV_TITLE_LAST["why"] = "the title band could not be read (%s)" % type(e).__name__\n        return None\n',
     "replace": '        _INV_TITLE_LAST["why"] = "the title band could not be read (%s)" % type(e).__name__\n        return False\n',
     "matches": 1},
    {"why": "REG-3388 - the bench folds an unread title into False (two PCs that never read 'agree')",
     "file": "tv/reader_parity.py",
     "find": '        return {"unknown": (getattr(se, "_INV_TITLE_LAST", {}) or {}).get("why") or "not read"} if v is None else bool(v)\n',
     "replace": '        return bool(v)\n', "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
