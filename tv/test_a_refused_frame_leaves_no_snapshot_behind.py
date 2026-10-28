#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2801 — THE REFUSAL PATH WROTE AN 8.6 MB FILE AND THEN LEFT IT THERE.

`_mini_cells_from_live_frame` copies the live frame to a private temp file so the capture cannot
replace it mid-read (v2799, REG-728). That snapshot was created BEFORE the two cheapest refusals in
the function:

    _fd, _snap = mkstemp(...)          # 8.6 MB written
    _sf.write(raw)
    age = time.time() - frame_mt
    if age > 10:  return None, "...stale..."      <- returns, snapshot stays on disk
    try: import vault_corpus
    except:       return None, "..."              <- returns, snapshot stays on disk
    try:   ...lattice / occupancy...
    finally: os.unlink(_snap)

and the comment on that `finally` asserted, in as many words, **"EVERY return above passes through
here"**. Two of them did not. [[feedback-comments-vs-code]]

⚠ THE STALE PATH IS THE COMMON PATH, WHICH IS WHAT MAKES IT EXPENSIVE. Grok drove this endpoint on
his console and got `"the newest frame is 3124s old"` — the refusal that leaks — over and over. A
button pressed while the capture is off is not an edge case; it is what the button does most of the
time. Every press would have cost one frame-sized file, forever, in a repo that has ALREADY paid for
an ENOSPC once (20.5 GB in four minutes, 2026-09-03).

★ MEASURED BEFORE FIXING: **0 leaked files on his Mac.** Not because the code was right — because
his console still runs v2796 and this rewrite had never executed there. Latent, not manifest. That
number is the whole reason this is a note and not an incident report, and it is also why a source
reading found it when `df` never would have. [[unknown-stays-unknown]]

THE LAW IS BEHAVIOURAL, NOT TEXTUAL. It calls the real function against a real temp tree and counts
the files left in the system temp dir afterwards. A law that merely asserted "the age check comes
before the mkstemp" would pass the moment someone added a THIRD early return below it — and that is
exactly how this defect was introduced in the first place. [[source-reading-guard]]
"""
import os
import sys
import glob
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# #173 - every temp file this law's subject makes lands in a WATCH dir inside the run's own scratch, so the census
# lists only what THIS run made (fixture_tmp), never a temp dir other runs share - and the law can be keyed.
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
_WATCH = tempfile.mkdtemp(prefix="watch-")
tempfile.tempdir = _WATCH
for _v in ("TMPDIR", "TEMP", "TMP"):
    os.environ[_v] = _WATCH

import control_app as CA  # noqa: E402


def _snapshots():
    """Every MINI AUTO snapshot currently sitting in the system temp dir."""
    return set(_fx_tmp.match_own(os.path.join(tempfile.gettempdir(), "minigrid.*")))


class TestRefusedFrameLeavesNoSnapshot(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="minileak.")
        os.makedirs(os.path.join(self.d, "frames"))
        self._here = CA.HERE
        CA.HERE = self.d
        self.before = _snapshots()

    def tearDown(self):
        CA.HERE = self._here
        # never let the gate itself leave litter behind
        for f in _snapshots() - self.before:
            try:
                os.unlink(f)
            except OSError:
                pass
        shutil.rmtree(self.d, ignore_errors=True)

    def _frame(self, name, blob, age_s):
        p = os.path.join(self.d, "frames", name)
        with open(p, "wb") as fh:
            fh.write(blob)
        st = os.stat(p)
        os.utime(p, (st.st_atime, st.st_mtime - age_s))
        return p

    def _leaked(self):
        return sorted(os.path.basename(f) for f in (_snapshots() - self.before))

    # ── the path Grok actually hit, thousands of seconds stale ────────────────
    def test_a_stale_frame_is_refused_without_writing_a_snapshot(self):
        self._frame("eye.jpg", b"\xff\xd8\xff" + b"\x00" * 200000, age_s=3124)
        cells, why, _saw = CA._mini_cells_from_live_frame("stash")
        self.assertIsNone(cells, "a 3124s-old frame was accepted for hovering")
        self.assertIn("old", (why or "").lower(),
                      "the refusal did not say the frame was stale: %r" % why)
        self.assertEqual(self._leaked(), [],
                         "the stale refusal left a snapshot behind: %s" % self._leaked())

    # ── the finally-block path: a frame fresh enough to read, impossible to parse ──
    def test_an_unreadable_frame_still_removes_its_snapshot(self):
        self._frame("eye.jpg", b"not an image at all" * 500, age_s=0)
        cells, why, _saw = CA._mini_cells_from_live_frame("stash")
        self.assertIsNone(cells, "garbage bytes were accepted as a readable grid")
        self.assertTrue((why or "").strip(),
                        "the frame was refused with no reason at all")
        self.assertEqual(self._leaked(), [],
                         "an unreadable frame left a snapshot behind: %s" % self._leaked())

    # ── and the case where no snapshot should ever be created ────────────────
    def test_no_frame_at_all_is_a_reason_not_a_crash(self):
        cells, why, _saw = CA._mini_cells_from_live_frame("stash")
        self.assertIsNone(cells)
        self.assertIn("no live frame", (why or "").lower(),
                      "an absent capture was not named as such: %r" % why)
        self.assertEqual(self._leaked(), [],
                         "a missing frame somehow produced a snapshot: %s" % self._leaked())

    # ── THE INSTRUMENT CHECK. If _snapshots() cannot see a file this law is
    #    green for the wrong reason, and every assertion above is theatre.
    def test_the_leak_detector_can_actually_see_a_leak(self):
        fd, p = tempfile.mkstemp(prefix="minigrid.", suffix=".jpg")
        os.close(fd)
        try:
            self.assertIn(os.path.basename(p), self._leaked(),
                          "the detector cannot see a snapshot that is definitely there — "
                          "every other assertion in this file is meaningless")
        finally:
            os.unlink(p)


# ══ THE EXECUTABLE RED-PROOF ═════════════════════════════════════════════════════════════════
# Heart 2.0 re-runs this in a sandbox and DISTRUSTS the law if it stays green. The hand-proof that
# produced this gate lives in the docstring above and cannot be re-run; this can.
RED_PROOF = [{
    "why": "the finally that removes the snapshot is the whole fix — break it and the leak returns",
    "file": "control_app.py",
    "find": """    finally:
        # \u26a0 REACHED BY EVERY PATH THAT CREATED THE SNAPSHOT""",
    "replace": """    finally:
        pass
    if False:
        # \u26a0 REACHED BY EVERY PATH THAT CREATED THE SNAPSHOT""",
    "matches": 1,
}]


if __name__ == "__main__":
    unittest.main(verbosity=2)
