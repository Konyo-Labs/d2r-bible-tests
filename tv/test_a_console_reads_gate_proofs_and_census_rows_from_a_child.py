# -*- coding: utf-8 -*-
"""REG-2985 (#172 phase C) - A CONSOLE READS THE GATE FILES' RED-PROOF LISTS AND THE SWALLOW CENSUS ROWS FROM A SHORT-LIVED
CHILD, PER FILE STAMP, AND PARSES NONE OF THEM IN ITS OWN HEAP.

MEASURED 2026-10-29 (a scratch console of his Mac on his data, Python 3.9, no .git, 300 s, every ast.parse counted by
caller): after phase B the console still called ast.parse 4,508 times over 118 MB of source in its own process.
  - swallow_census._file_rows: 1,488 files (the doctor's swallowed-reads row);
  - heart2.red_proofs_in: 2,473 parses of 1,237 gate files. They were read once by slice_owed (the self-arming owed list,
    no memo) and once by health_engine's attack tally (its own memo);
  - lane_liveness.stamping_functions: the whole of control_app.py, on every health pass (3 times).
RSS rose in spikes to 550-1,028 MB. macOS hands them back within seconds. The ALT's console (Python 3.12, 7.9 GB) holds
1,118 MB working set and 1,565 MB private. With the first two answered from a separate process the same console made 540
parses (33 MB) and peaked at 376 MB.

Now:
  - audit_child derives every gate file's list ("red_proofs") and every file's census rows under a root ("swallow") in a
    child, and keeps each per file on its stamp (mtime_ns, size);
  - a console reads them (audit_child.red_proofs_for / swallow_rows_for), asks the child at most once per ASK_EVERY_S on a
    miss, and derives itself only what is still missing;
  - a stale entry is never served;
  - heart2.red_proofs_in keeps one memo per file stamp for every caller in a process;
  - lane_liveness parses control_app.py once per stamp;
  - a law, the gate, CI and a CLI spawn nothing and parse as before.
Real modules in a fixture world (TV_HIST is a temp dir, so the caches live there, never in his tree). RED_PROOF below.
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
_WORLD = tempfile.mkdtemp(prefix="audit_child_c_world_")
os.environ["TV_HIST"] = _WORLD          # before anything resolves a cache root
import audit_child as AC  # noqa: E402
import frame_ref as FR  # noqa: E402
import heart2 as H2  # noqa: E402
import lane_liveness as LL  # noqa: E402
import swallow_census as SC  # noqa: E402

_REAL_PARSE = ast.parse
SWALLOW = "def f():\n    try:\n        return open('x').read()\n    except Exception:\n        return {}\n"


def _counted(fn):
    calls = {"n": 0}

    def parse(*a, **k):
        calls["n"] += 1
        return _REAL_PARSE(*a, **k)
    with mock.patch.object(ast, "parse", parse):
        out = fn()
    return out, calls["n"]


def _cold():
    """A fresh console start: no memo, no child-written cache, no child state."""
    H2._RP_MEMO.clear()
    SC._FILE_ROWS.clear()
    AC._DISK.clear()
    AC.STATE.clear()
    for c in (AC.RP_CACHE, AC.SW_CACHE):
        p = os.path.join(AC._cache_root(), c)
        if os.path.exists(p):
            os.remove(p)


def _gates(n=3):
    """A few registered gate files that declare a RED_PROOF list (read in this process, with no console mark)."""
    FR.mark_console_path(False)
    out = []
    for _name, f in H2.gate_files(say=lambda *a, **k: None):
        if len(out) >= n:
            break
        got = H2.red_proofs_in(f)
        if got:
            out.append((f, got))
    H2._RP_MEMO.clear()
    return out


class AConsoleReadsGateProofsAndCensusRowsFromAChild(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        assert os.path.realpath(AC._cache_root()).startswith(os.path.realpath(_WORLD)), \
            "PREMISE: the child's caches are not inside the fixture world: %s" % AC._cache_root()
        cls.gates = _gates()
        assert len(cls.gates) == 3, "PREMISE: fewer than 3 gate files declare a RED_PROOF list"
        cls.root = tempfile.mkdtemp(prefix="swallow_root_", dir=_WORLD)
        for i in range(3):
            with open(os.path.join(cls.root, "m%d.py" % i), "w", encoding="utf-8") as fh:
                fh.write(SWALLOW * (i + 1))

    def tearDown(self):
        FR.mark_console_path(False)

    def test_a_console_parses_no_gate_file_and_reads_the_childs_lists(self):
        # before: the same asks with no console mark parse every file in this process (the number on record)
        _cold()
        FR.mark_console_path(False)
        _b, before = _counted(lambda: [H2.red_proofs_in(f) for f, _p in self.gates])
        _cold()
        FR.mark_console_path(True)
        got, n = _counted(lambda: [H2.red_proofs_in(f) for f, _p in self.gates])
        self.assertEqual((before, n), (3, 0), "parses in the asking process, before -> after: %d -> %d" % (before, n))
        self.assertEqual(got, [p for _f, p in self.gates], "the child's lists are not the ones this process derives")
        st = AC.status()["audits"]["red_proofs"]
        self.assertEqual((st["runs"], st["lastOk"]), (1, True), st)
        # a second ask, memo forgotten: the disk cache answers, nothing is spawned
        H2._RP_MEMO.clear()
        _got2, n2 = _counted(lambda: [H2.red_proofs_in(f) for f, _p in self.gates])
        self.assertEqual((n2, AC.status()["audits"]["red_proofs"]["runs"]), (0, 1), "a warm cache spawned or parsed again")

    def test_a_console_reads_the_census_rows_and_a_stale_row_is_never_served(self):
        _cold()
        FR.mark_console_path(False)
        _b, before = _counted(lambda: SC.scan(self.root))
        _cold()
        FR.mark_console_path(True)
        out, n = _counted(lambda: SC.scan(self.root))
        self.assertEqual((before, n), (3, 0), "census parses in the asking process, before -> after: %d -> %d" % (before, n))
        self.assertEqual(len(out["rows"]), 6, "PREMISE: the fixture holds 1+2+3 swallows: %r" % out["rows"])
        self.assertEqual(AC.status()["audits"]["swallow"]["runs"], 1)
        # he edits one file: its stamp moves, the child's row for it is stale and is never served
        p = os.path.join(self.root, "m0.py")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(SWALLOW * 5)
        st = os.stat(p)
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 5000000000))
        SC._FILE_ROWS.clear()
        out2, n2 = _counted(lambda: SC.scan(self.root))
        self.assertEqual(len(out2["rows"]), 10, "a stale census row was served after the file changed: %r" % len(out2["rows"]))
        self.assertEqual(n2, 1, "PREMISE: the changed file was not derived here (asked the child again within ASK_EVERY_S?)")

    def test_a_cached_list_is_served_only_for_the_gate_files_current_stamp(self):
        """An edited law file is never answered from the old parse: the child's entry carries another stamp."""
        _cold()
        f, real = self.gates[0]
        st = os.stat(os.path.join(H2.HERE, f))
        old = [{"why": "an old parse of this file", "file": "bible.html", "find": "a", "replace": "b", "matches": 1}]
        self.assertTrue(AC._write_cache(AC.RP_CACHE, {"v": 1, "files": {f: [st.st_mtime_ns - 1, int(st.st_size), old]}}))
        FR.mark_console_path(True)
        AC._row("red_proofs")["askedAt"] = time.time()          # the child was asked just now: this file is derived here
        got, n = _counted(lambda: H2.red_proofs_in(f))
        self.assertEqual(got, real, "an old parse was served for a file whose stamp moved")
        self.assertEqual(n, 1, "PREMISE: the file was not derived in this process")

    def test_a_law_spawns_nothing_and_keeps_one_parse_per_stamp(self):
        _cold()
        FR.mark_console_path(False)
        f = self.gates[0][0]
        _a, n1 = _counted(lambda: H2.red_proofs_in(f))
        _b, n2 = _counted(lambda: H2.red_proofs_in(f))
        self.assertEqual((n1, n2), (1, 0), "not one parse per stamp in one process: %r" % ((n1, n2),))
        self.assertEqual(AC.status()["audits"]["red_proofs"]["runs"], 0, "a law spawned a child")

    def test_a_failed_child_fails_open_and_says_so(self):
        _cold()
        FR.mark_console_path(True)

        def _boom(*a, **k):
            raise subprocess.TimeoutExpired(a[0] if a else "x", AC.TIMEOUT_S)
        with mock.patch.object(AC.subprocess, "run", _boom):
            out, n = _counted(lambda: SC.scan(self.root))
        self.assertGreater(n, 0, "PREMISE: with the child gone the console did not derive at all")
        st = AC.status()["audits"]["swallow"]
        self.assertIs(st["lastOk"], False, st)
        self.assertIn("derived it itself", st["say"])

    def test_the_lane_stamps_parse_control_app_once_per_stamp(self):
        LL._STAMP_MEMO.clear()
        a, n1 = _counted(LL.stamping_functions)
        b, n2 = _counted(LL.stamping_functions)
        self.assertEqual((n1, n2), (1, 0), "control_app.py was parsed again for the same stamp: %r" % ((n1, n2),))
        self.assertEqual(a, b)
        self.assertNotIn("__failed__", a)


RED_PROOF = [
    {"why": "REG-2985 - a console parses every gate file in its own heap again (the child's lists are not read)",
     "file": "tv/heart2.py",
     "find": "            got = _ac.red_proofs_for(filename, key)\n",
     "replace": "            got = None\n",
     "matches": 1},
    {"why": "REG-2985 - a console parses every census file in its own heap again",
     "file": "tv/swallow_census.py",
     "find": "        got = _ac.swallow_rows_for(p, root, key)\n",
     "replace": "        got = None\n",
     "matches": 1},
    {"why": "REG-2985 - a stale child row is served after the file changed",
     "file": "tv/audit_child.py",
     "find": "    return isinstance(e, list) and len(e) == 3 and e[:2] == want\n",
     "replace": "    return isinstance(e, list) and len(e) == 3\n",
     "matches": 1},
    {"why": "REG-2985 - red_proofs_in parses the same file again for every caller (no memo)",
     "file": "tv/heart2.py",
     "find": "        if hit is not None and hit[0] == key:\n            return hit[1]\n        try:\n            import audit_child as _ac\n",
     "replace": "        if False:\n            return hit[1]\n        try:\n            import audit_child as _ac\n",
     "matches": 1},
    {"why": "REG-2985 - the lane stamps parse control_app.py on every health pass again",
     "file": "tv/lane_liveness.py",
     "find": "    if _key is not None and _hit is not None and _hit[0] == _key:\n",
     "replace": "    if False:\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
