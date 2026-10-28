# -*- coding: utf-8 -*-
"""v2712 — THE WRITE THAT RUNS ON EVERY SHIP LEFT HIS 6 MB BOARD AT ZERO BYTES.

His diagnosis, 2026-09-05: *"it happens i think in a form of stale render ... something like
unsyncs and it needs a restart or something to fetch it"* — given about panels that render NOTHING
and say nothing, and that never reproduce afterwards.

THE MECHANISM, MEASURED. `bump_version.bump()` wrote all four version stamps with
`io.open(path, "w").write(text)`. That call TRUNCATES ON OPEN, so between the truncate and the
write completing the file on disk is EMPTY. bible.html is 6 MB and his console EXECS THE WORKING
TREE — it re-reads that file per request — so a page load landing in that window parses nothing.

    truncate-then-write    188 reads,  9 TORN  (4.8%)   every torn size == 0 bytes
    tmp + os.replace       203 reads,  0 TORN  (0.0%)

The torn reads were not partial parses. They were an EMPTY FILE. That is exactly the symptom, and
it explains why every attempt to reproduce it FAILED: a settled tree is fine, so reproducing on one
measures the wrong moment. [[feedback-blind-fixture-green-gate]] [[execs-the-working-tree]]

=== WHY THIS GATE IS DETERMINISTIC AND NOT A RACE ===
The obvious test — two threads, count torn reads — is exactly the test that goes green on a fast
machine for the wrong reason and reads as proof. A concurrency gate whose CONTROL can silently
fail to reproduce the defect is a gate that certifies nothing on the day it matters, and this repo
has been bitten by the green-that-lies often enough to know better. [[regression-guard]]

So the property is proven WITHOUT a race, both ways:
  * the CONTROL opens the old call and observes size 0 before one byte of content is written —
    the defect, demonstrated with no timing dependence at all;
  * the FIX observes the target at the instant before the swap and finds the OLD file intact.

⚠ WHAT THIS DOES NOT COVER, stated so it is not mistaken for more: atomicity is PER FILE. A crash
between two of the four stamps still leaves the set disagreeing. That is a different defect and
nothing here fixes it. [[unknown-stays-unknown]]
"""
import io
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import bump_version as BV

BIG = "x" * 200000


class VersionStampsAreWrittenAtomically(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="atomicwrite-")
        self.p = os.path.join(self.dir, "board.html")
        io.open(self.p, "w", encoding="utf-8").write("OLD" + BIG)

    def test_CONTROL_the_old_call_empties_the_file_before_content_lands(self):
        """The defect itself, with no race. If this ever stops being true the gate is moot."""
        fh = io.open(self.p, "w", encoding="utf-8")
        try:
            size = os.path.getsize(self.p)
        finally:
            fh.write("NEW" + BIG)
            fh.close()
        self.assertEqual(
            size, 0,
            "the truncate-then-write call no longer empties the file, so the premise of this gate "
            "is gone — re-derive it before trusting anything here"
        )

    def test_atomic_write_leaves_the_OLD_bytes_intact_until_the_swap(self):
        """A reader at the worst possible instant still gets a whole file."""
        seen = {}
        real = os.replace

        def spy(src, dst):
            # what a reader polling `dst` would get one instruction before the swap
            seen["at_swap"] = io.open(dst, encoding="utf-8").read()
            seen["tmp_dir"] = os.path.dirname(src)
            return real(src, dst)

        os.replace = spy
        try:
            BV.atomic_write(self.p, "NEW" + BIG)
        finally:
            os.replace = real

        self.assertIn("at_swap", seen,
                      "atomic_write never called os.replace — it is not atomic at all")
        self.assertEqual(
            seen["at_swap"], "OLD" + BIG,
            "at the instant before the swap the target held %d chars instead of the whole old "
            "file. A reader in that window gets a partial or empty page, which is the defect."
            % len(seen["at_swap"])
        )
        self.assertEqual(io.open(self.p, encoding="utf-8").read(), "NEW" + BIG,
                         "the new content did not land")

    def test_the_temp_lives_beside_the_target(self):
        """os.replace is only atomic on the SAME filesystem. A temp in /tmp silently is not."""
        seen = {}
        real = os.replace
        os.replace = lambda s, d: (seen.__setitem__("src", s), real(s, d))[1]
        try:
            BV.atomic_write(self.p, "NEW")
        finally:
            os.replace = real
        self.assertEqual(
            os.path.dirname(seen["src"]), os.path.dirname(self.p),
            "the temp file is written to %r while the target is in %r. os.replace is atomic only "
            "within one filesystem; across a boundary it degrades to a copy and the guarantee is "
            "gone, silently." % (os.path.dirname(seen["src"]), os.path.dirname(self.p))
        )

    def test_no_stray_temp_is_left_behind(self):
        BV.atomic_write(self.p, "NEW")
        leftovers = [f for f in _fx_tmp.list_own(self.dir) if f.endswith(".tmp")]
        self.assertEqual(leftovers, [],
                         "a .tmp survived the write: %r. These are not in .gitignore by wildcard, "
                         "so one left behind shows up as an untracked file in every later status."
                         % leftovers)

    def test_newline_handling_survived_the_refactor(self):
        """The JSON stamp is written with newline='\\n'; the rest with ''. Both must still hold."""
        j = os.path.join(self.dir, "s.json")
        BV.atomic_write(j, '{\n  "ver": "v1"\n}\n', "\n")
        raw = open(j, "rb").read()
        self.assertNotIn(b"\r\n", raw, "the JSON stamp gained CRLF line endings")

    def test_THE_SHIP_PATH_ACTUALLY_CALLS_IT(self):
        """⚠ The helper existing proves nothing. Two halves built and never joined is this repo's
        single most repeated defect, and a well-tested helper nobody calls is its purest form.
        [[the-unjoined-end]]"""
        src = io.open(BV.__file__.replace(".pyc", ".py"), encoding="utf-8").read()
        m = re.search(r"\n    for path, text in pending:(.*?)\n    _drop_stale_bytecode", src, re.S)
        self.assertIsNotNone(
            m, "the four-stamp write loop is not where this gate expects it — the gate cannot "
               "grade the ship path, which is a FAILURE and not a pass"
        )
        # ⚠⚠ JUDGE THE CODE, NOT THE PROSE — and this gate tripped on its OWN comment the first
        # time it ran. The v2712 comment inside that loop EXPLAINS the fix by naming the forbidden
        # call, `io.open(path, "w")`, and the check below found it in the very sentence forbidding
        # it. That is [[source-reading-guard]] exactly — "the comment that trips the guard is
        # usually the one describing the fix" — and it is the SECOND time in one session, after
        # test_live_version_is_not_the_working_tree hit the identical shape on its own docstring.
        loop = re.sub(r"(?m)#.*$", " ", m.group(1))
        self.assertIn("atomic_write", loop,
                      "the ship's write loop does not call atomic_write. The helper is tested and "
                      "unused, and every bump still empties bible.html: %r" % loop.strip()[:200])
        self.assertNotRegex(
            loop, r"io\.open\([^)]*['\"]w['\"]",
            "the ship's write loop still opens a stamp for writing directly, which truncates it"
        )


RED_PROOF = [
    {
        'why': 'The ship path must call atomic_write for the four version stamps, not open them for writing directly. A plain io.open(path,"w") TRUNCATES on open, so his 6 MB bible.html is 0 bytes on disk until the write completes — and his console EXECS the working tree, so a page load in that window renders nothing (measured historically: 9 torn reads of 188, every torn size 0 bytes). This tamper re-joins the loop to the truncating call, which is the original defect verbatim: the helper still exists and is still fully tested, and only the JOIN is cut — the purest form of this repo\'s most repeated defect (two halves built and never met).  MEASURED: untampered GREEN — `python3 tv/test_version_stamps_are_written_atomically.py` -> Ran 6 tests, OK (exi; tampered (all 1) RED — FAILED (failures=1); the red law is test_THE_SHIP_PATH_ACTUALLY_CALLS_IT (assertIn "; reddened law test_version_stamps_are_written_atomically.VersionStampsAreWrittenAtom; ALONE FAILS ALONE — fresh process, `python3 -m unittest test_version_stamps_are_written_atomically.VersionStampsAreW.',
        'file': 'bump_version.py',
        'find': 'atomic_write(path, text, nl)',
        'replace': 'io.open(path, "w", encoding="utf-8", newline=nl).write(text)',
        'matches': 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
