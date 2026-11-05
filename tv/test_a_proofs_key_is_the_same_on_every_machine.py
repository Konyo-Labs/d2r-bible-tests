# -*- coding: utf-8 -*-
"""REG-3191 - A PROOF'S KEY IS THE SAME ON EVERY MACHINE, SO AN IMPORTED PROOF OVER IDENTICAL BYTES IS SERVED HERE.

MEASURED on his Mac 2026-11-05 at v3864 (9d9485ea6): GitHub's 22 proof shards held 8,577 PROVEN entries; the import banked
2,928 (+87 already here) and dropped the rest as "a key this tree never gives" (REG-2596), and frame.release stayed shut on
guard laws CI had proved over the very same bytes. For the 209 proofs of frame.release's eight vault/control guards, the
keys his Mac gave matched GitHub's for 78 - exactly the proofs NOT keyed through REG-2602's stamp mask. Keyed on his Mac
with HOME=/home/runner, test_vault_l1_router_files_every_item's ten keys were GitHub's ten byte for byte: the mask asked
stamp_leak.leak_problem, whose last check refuses free text holding THIS machine's home path or user name, so every ship
row naming GitHub's "runners" was a leak on GitHub (kept raw) and inert on his Mac (masked). Two keys for one set of bytes.
heart2._inert now asks the leak check WITHOUT the machine part (stamp_leak.leak_problem(t, machine=False)): measured
again, 209 of 209 agree under a Mac, a GitHub and a Windows home, and every key his Mac gave before is unchanged.
Held here, on a fixture repo keyed by the real _VerdictCache:
  * one proof keyed under two homes - the runner's and another - gives ONE key, while a stamp line names the runner;
  * the line is still MASKED (a coherent bump still keeps the key), never kept raw on both;
  * the bump's own leak check still refuses this machine's identity (a published note never carries it).
Fixtures only: a temp repo, HOME/USERPROFILE patched for the call. RED_PROOF below.
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import heart2 as H  # noqa: E402
import stamp_leak  # noqa: E402

LAW = "test_fixture_law.py"
PROOF = {"why": "a fixture proof", "file": "control_app.py", "find": "SALT = 1", "replace": "SALT = 2", "matches": 1}
#: the free text of a real ship note shape that names GitHub's machines - inert words, and a GitHub home's user name
NOTE = "the proof shards run on GitHub runners inside 25 dollars"
HOMES = ("/home/runner", "/home/elsewhere")


def _surfaces(ver, note=NOTE):
    return {
        "bible.html": ("<html><head>\n  <title>Konyo Bible %s · TV</title>\n"
                       '<meta name="d2r-build" content="%s">\n'
                       '<meta name="d2r-build-date" content="2026-11-05">\n'
                       '<meta name="d2r-build-note" content="%s">\n</head><body><script>\n'
                       "var a = 1;\n"
                       "  window.D2R_BUILD = { id:'%s', name:'%s - n', date:'2026-11-05', note:'%s' };\n"
                       "</script></body></html>\n") % (ver, ver, note, ver, ver, note),
        "tv/control_app.py": ('DOCS = ("RESUME_HERE.md", "TASKS.md", "BLUEPRINT.md")\n'
                              'def status():\n    return {\n        "ver": "%s",\n    }\nSALT = 1\n') % ver,
        "tv/tv_diablo.py": 'VERSION = "%s"   # the build\n' % ver,
        "tv/WINDOWS_SHIP.json": '{\n  "ver": "%s",\n  "note": "%s: %s",\n  "x": 1\n}\n' % (ver, ver, note),
        "RESUME_HERE.md": ("# resume\n<!-- fp: ver=%s -->\n| version stamp | %s |\n"
                           "*Derived 2026-11-05 10:24 by `tv/resume_state.py`. Everything outside these markers is "
                           "narrative a machine cannot measure, written by hand.*\nnarrative\n") % (ver, ver),
        "TASKS.md": u"# tasks\n| ver | sha | what |\n| **%s** | `abcdef12` | %s — %s |\nan open task\n" % (ver, ver, note),
    }


def _home(home):
    """THIS machine's home, for the call: expanduser reads HOME on POSIX and USERPROFILE on Windows."""
    return mock.patch.dict(os.environ, {"HOME": home, "USERPROFILE": home})


class AProofsKeyIsTheSameOnEveryMachine(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pk_reg3191_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.tv = os.path.join(self.root, "tv")
        os.makedirs(self.tv)
        for mod in ("gate_ledger.py", "stamp_leak.py"):
            shutil.copy(os.path.join(HERE, mod), os.path.join(self.tv, mod))
        with open(os.path.join(self.tv, LAW), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("import control_app\nimport tv_diablo\nPAGE = '../bible.html'\n")
        self.write(_surfaces("v100"))

    def write(self, files):
        for rel, text in files.items():
            with open(os.path.join(self.root, *rel.split("/")), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)

    def key(self, home):
        """a fresh cache each time, as a second machine keys it -> (key, inputs)"""
        with _home(home):
            c = H._VerdictCache(path=os.path.join(self.root, "cache.json"), say=lambda *a, **k: None)
            k, rels, why = c.key_for(self.tv, LAW[:-3], LAW, PROOF)
        self.assertIsNone(why, "PREMISE: the fixture law is unkeyable: %s" % why)
        self.assertIn("bible.html", rels, "PREMISE: bible.html is not an input of the fixture law")
        return k, rels

    def test_the_premise_a_runners_home_reads_its_own_name_as_a_leak(self):
        with _home(HOMES[0]):
            self.assertTrue(stamp_leak.leak_problem(NOTE), "PREMISE: the note no longer names this machine's user, so "
                                                            "this law would hold nothing")
        with _home(HOMES[1]):
            self.assertIsNone(stamp_leak.leak_problem(NOTE))

    def test_one_proof_gives_one_key_under_two_homes(self):
        a, b = self.key(HOMES[0])[0], self.key(HOMES[1])[0]
        self.assertEqual(a, b, "the same bytes gave two keys on two machines - an imported proof is dropped (REG-2596) "
                               "and never served here")

    def test_the_named_line_is_still_masked_on_both(self):
        for home in HOMES:
            with _home(home):
                got = H._stamp_masked("bible.html", _surfaces("v100")["bible.html"].encode("utf-8"))
            self.assertIn(b"\0STAMP:meta-note", got[0], "under %s the note line was kept raw, not masked" % home)
            self.assertIn(NOTE, got[1])

    def test_a_coherent_bump_keeps_the_key_under_a_runners_home(self):
        before = self.key(HOMES[0])[0]
        self.write(_surfaces("v101"))
        self.assertEqual(self.key(HOMES[0])[0], before, "a bump moved the key: the stamp lines are not masked there")

    def test_the_bump_still_refuses_this_machines_identity(self):
        with _home(HOMES[0]):
            self.assertEqual(stamp_leak.leak_problem("a note from runner"), "this machine's identity (home or user name)",
                             "the bump's own leak check no longer refuses this machine's user name")
            self.assertIsNone(stamp_leak.leak_problem("a note from runner", machine=False))


RED_PROOF = [
    {"why": "REG-3191 - the stamp mask asks the machine's identity again, so one set of bytes gives two keys",
     "file": "tv/heart2.py",
     "find": "            if stamp_leak.free_text_problem(t) or stamp_leak.leak_problem(t, machine=False):\n",
     "replace": "            if stamp_leak.free_text_problem(t) or stamp_leak.leak_problem(t):\n",
     "matches": 1},
    {"why": "REG-3191 - leak_problem's machine=False still reads this machine's home and user name",
     "file": "tv/stamp_leak.py",
     "find": "    if not machine:\n        return None\n",
     "replace": "    if False:\n        return None\n",
     "matches": 1},
    {"why": "REG-3191 - the bump's own leak check stops refusing this machine's identity",
     "file": "tv/stamp_leak.py",
     "find": "def leak_problem(text, machine=True):\n",
     "replace": "def leak_problem(text, machine=False):\n",
     "matches": 1},
    {"why": "REG-3191 - the mask keeps every free-text line raw, so the fix 'agrees' by masking nothing",
     "file": "tv/heart2.py",
     "find": "            if stamp_leak.free_text_problem(t) or stamp_leak.leak_problem(t, machine=False):\n                return False\n    return True\n",
     "replace": "            if stamp_leak.free_text_problem(t) or stamp_leak.leak_problem(t, machine=False):\n                return False\n    return False\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
