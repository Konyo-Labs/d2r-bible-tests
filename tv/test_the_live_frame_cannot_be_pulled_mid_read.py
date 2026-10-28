#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2799 — THE LIVE FRAME WAS STAT-ED IN ONE PLACE AND OPENED IN ANOTHER, AND THE CAPTURE MOVES IT.

⚠⚠ WHAT IT COST, 2026-09-08. He pressed MINI AUTO and it refused. The reason, once v2798's toast
finally made refusals visible where he was standing:

    "the grid could not be located on this frame: unreadable:
     [Errno 2] No such file or directory: '.../tv/frames/eye…'"

`_mini_cells_from_live_frame` picked the newest EXISTING label out of
(eye.jpg, live.jpg, live.png, live.bmp) with `os.path.isfile`, then handed the PATH to
`vault_corpus.inventory_lattice()`, which opens it LATER. The capture promotes eye.jpg by replacing
it, so between the stat and that open there is a window where the file does not exist.

That is why MINI AUTO alternated between two different complaints — "the newest frame is Ns old"
and "the grid could not be located" — depending purely on whether a promote was in flight. Two
faces of ONE missing file. MEASURED with no capture running: eye.jpg ABSENT, live.jpg present and
274s old; with a capture running, eye.jpg exists and is newest, and the race is live.

=== ⛔ WHY READING THE BYTES WAS NOT ENOUGH, AND I NEARLY SHIPPED THAT ===
My first cut read the bytes here and then passed the PATH onward anyway — plumbing with no tap. The
read would prove the file existed a moment ago and the readers would still race it. Checked and
confirmed: `inventory_lattice(frame_path)` and `inventory_occupancy(frame_path, lat)` BOTH open what
they are given and neither accepts bytes. So the bytes are written to a private snapshot and the
SNAPSHOT is what travels. [[the-unjoined-end]]

=== ⚠ NOT A WIDER AGE BOUND ===
The obvious "fix" is to relax the 10s freshness rule. That would be treating a race as slowness: the
file's ABSENCE was the event, never its age, and widening the bound would have hidden it for good.
[[feedback-threshold-above-the-ceiling]]
"""
import ast
import inspect
import io
import os
import shutil
import sys
import tempfile
import textwrap
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

# #173 - every temp file this law's subject makes lands in a WATCH dir inside the run's own scratch, so the census
# lists only what THIS run made (fixture_tmp), never a temp dir other runs share - and the law can be keyed.
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
_WATCH = tempfile.mkdtemp(prefix="watch-")
tempfile.tempdir = _WATCH
for _v in ("TMPDIR", "TEMP", "TMP"):
    os.environ[_v] = _WATCH

import control_app as CA  # noqa: E402

FN = "_mini_cells_from_live_frame"


class TheLiveFrameCannotBePulledMidRead(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.frames = os.path.join(self.d, "frames")
        os.makedirs(self.frames, exist_ok=True)
        self._here = CA.HERE
        CA.HERE = self.d          # the function joins HERE/"frames"/<label>

    def tearDown(self):
        CA.HERE = self._here
        shutil.rmtree(self.d, ignore_errors=True)

    def _write(self, label, data=b"\xff\xd8\xff\xe0not-a-real-jpeg"):
        p = os.path.join(self.frames, label)
        io.open(p, "wb").write(data)
        return p

    # ── ⚠ THE LAW MUST NOT BE PINNED TO A LITERAL ARITY ─────────────────────────────────────
    # v2807 gave the subject a THIRD return value (the panel the pixels actually showed, so the
    # hover stops sweeping the panel the button NAMED). Its sibling law
    # `test_a_refused_frame_leaves_no_snapshot_behind.py` was re-anchored in that same commit;
    # this one was not, so every `cells, why = ...(...)` here died with "too many values to
    # unpack" and the race law above graded NOTHING for two ships. The fix at one site instead of
    # to the class. [[sweep-dont-ask]] [[regression-guard]]
    # So: read the arity off the FUNCTION (parsed, never grepped), demand every return path agree,
    # and name only the first two positions — which are this law's actual subject.
    def _subject_arity(self):
        fn = getattr(CA, FN)
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        body = tree.body[0]
        inner = {id(n) for d in ast.walk(body)
                 if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and d is not body
                 for n in ast.walk(d)}
        arities, bare = set(), 0
        for n in ast.walk(body):
            if not isinstance(n, ast.Return) or id(n) in inner:
                continue
            if isinstance(n.value, ast.Tuple):
                arities.add(len(n.value.elts))
            else:
                bare += 1
        self.assertTrue(arities or bare,
                        "%s has no return statements at all — re-point this law" % FN)
        self.assertEqual(bare, 0,
                         "%s has %d return(s) that are not tuples — a caller unpacking them "
                         "would crash" % (FN, bare))
        self.assertEqual(len(arities), 1,
                         "%s returns tuples of DIFFERENT lengths %s — whichever path a caller "
                         "does not exercise will raise ValueError in front of him"
                         % (FN, sorted(arities)))
        n = arities.pop()
        self.assertGreaterEqual(n, 2, "%s no longer returns (cells, why, ...)" % FN)
        return n

    def _call(self, *a, **kw):
        """Call the subject, prove it returned the shape its own source promises, hand back
        (cells, why) — the two positions this law is about."""
        res = getattr(CA, FN)(*a, **kw)
        want = self._subject_arity()
        self.assertIsInstance(res, tuple, "%s returned %r, not a tuple" % (FN, type(res).__name__))
        self.assertEqual(len(res), want,
                         "%s returned %d value(s) but its source returns %d — a caller unpacking "
                         "this crashes" % (FN, len(res), want))
        return res[0], res[1]

    # ── the instrument first ────────────────────────────────────────────────────────────────
    def test_the_function_is_still_here(self):
        """⚠ A law that cannot find its subject passes having examined nothing."""
        self.assertTrue(hasattr(CA, FN), "%s is gone or renamed — re-point this law" % FN)
        self.assertGreaterEqual(
            self._subject_arity(), 2,
            "%s no longer returns (cells, why, ...) — every unpack in this law is aimed at air" % FN)

    def test_no_frame_at_all_is_UNKNOWN_not_empty(self):
        """⛔ 'no items are on screen' and 'nobody could read the screen' are opposite facts."""
        cells, why = self._call()
        self.assertIsNone(cells, "it returned cells with no frame on disk")
        self.assertIn("capture", (why or "").lower(),
                      "the refusal does not point at the capture: %r" % why)

    # ── ⚠⚠ THE LAW ──────────────────────────────────────────────────────────────────────────
    def test_the_READER_never_receives_the_LIVE_path(self):
        """★★★ THE DEFECT. If the reader is handed the live path, the capture can pull it out from
        under the open — which is exactly what he hit."""
        self._write("eye.jpg")
        seen = {}

        class _FakeVC(object):
            @staticmethod
            def inventory_lattice(p):
                seen["path"] = p
                return {"ok": True}

            @staticmethod
            def inventory_occupancy(p, lat):
                seen["path2"] = p
                return {"ok": True, "grid": [[1, 0], [0, 0]]}

        real = sys.modules.get("vault_corpus")
        sys.modules["vault_corpus"] = _FakeVC
        try:
            self._call()
        finally:
            if real is not None:
                sys.modules["vault_corpus"] = real
            else:
                sys.modules.pop("vault_corpus", None)
        self.assertIn("path", seen, "the lattice reader was never called — this law graded nothing")
        live = os.path.join(self.frames, "eye.jpg")
        self.assertNotEqual(
            os.path.realpath(seen["path"]), os.path.realpath(live),
            "the reader was handed the LIVE frame path. The capture replaces that file mid-promote, "
            "so the open races it — reproduce by deleting the file between the stat and the read.")
        self.assertEqual(seen.get("path"), seen.get("path2"),
                         "the two readers were given DIFFERENT files, so the lattice and the "
                         "occupancy describe different pictures")

    def test_a_frame_that_VANISHES_is_skipped_not_fatal(self):
        """⚠ The whole point: one label disappearing costs one candidate, not the attempt."""
        self._write("live.jpg")
        gone = os.path.join(self.frames, "eye.jpg")
        io.open(gone, "wb").write(b"x")
        os.utime(gone, None)          # newest, so it is tried FIRST
        os.unlink(gone)               # ...and is gone by the time it is read
        cells, why = self._call()
        # live.jpg survives, so it must get past the vanish and refuse on AGE or on the lattice —
        # never on "no live frame", which would mean the survivor was discarded too
        self.assertNotIn("there is no live frame", (why or ""),
                         "a vanished candidate took the surviving one with it: %r" % why)

    def test_no_snapshot_is_left_behind_on_ANY_path(self):
        """⛔ Every refusal passes through the cleanup. A snapshot per press fills his disk, and
        this repo has already paid for an ENOSPC."""
        self._write("eye.jpg")
        before = set(f for f in _fx_tmp.list_own(tempfile.gettempdir()) if f.startswith("minigrid."))
        for _ in range(3):
            self._call()
        after = set(f for f in _fx_tmp.list_own(tempfile.gettempdir()) if f.startswith("minigrid."))
        self.assertEqual(after - before, set(),
                         "snapshots survived the call: %s" % sorted(after - before))


RED_PROOF = [
    {
        'why': 'The whole point of _mini_cells_from_live_frame is that the PIXEL READERS never receive the live frame path — the capture promotes eye.jpg by replacing it, so an open that races the promote returns [Errno 2] and MINI AUTO refuses with "the grid could not be located". The fix reads the bytes once and hands vault_corpus a private temp snapshot. This tamper hands the lattice reader `frame` (the live path) again, restoring exactly the shipped defect: the reader is back on a file the capture can pull out from under it. It deletes the real thing (the argument at the call site), not a comment or a message string.  MEASURED: untampered OK — `python3 tv/test_the_live_frame_cannot_be_pulled_mid_read.py` => Ran 5 tests, OK (0.1; tampered (all 1) FAILED (failures=1) — Ran 5 tests; the single failure is test_the_READER_never_receives_th; reddened law test_the_live_frame_cannot_be_pulled_mid_read.TheLiveFrameCannotBePull; ALONE FAILED alone — `python3 -m unittest test_the_live_frame_cannot_be_pulled_mid_read.TheLiveFrameCannotBePulledMi.',
        'file': 'control_app.py',
        'find': '_vc.inventory_lattice(_snap)',
        'replace': '_vc.inventory_lattice(frame)',
        'matches': 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
