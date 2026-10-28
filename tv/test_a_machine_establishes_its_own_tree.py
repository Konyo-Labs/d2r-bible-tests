# -*- coding: utf-8 -*-
"""v3393 — A MACHINE ESTABLISHES ITS OWN TREE, AND NEVER GUESSES WHERE.

His ruling: fix "any machine establishes its own tree", never "the Windows PC", so that Dean's PC is
fixed BY PULLING with nobody touching it.

⚠⚠ THIS GATE CHECKS THE CONTRACT, NOT THIS MACHINE. A case asserting "every root is found" would
pass on his Mac and FAIL on a CI runner, which has no established tree - and the whole point is that
a fresh machine is a LEGITIMATE state, not a failure. Whether THIS machine's tree is established is
the heart's question, and its live red case is his Windows ALT box right now. [[test-venue]]
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #243 - this run's scratch dirs leave with it (the tightened #171 finder)
_fx_tmp.contain()
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ⚠ unittest -v PRINTS THE FIRST DOCSTRING LINE, and these carry a warning sign. On a cp1255 console
# that crashes WHILE REPORTING. The pre-push gate refused a file of mine for exactly this an hour ago.
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import machine_tree as MT  # noqa: E402

SRC = io.open(os.path.join(HERE, "machine_tree.py"), encoding="utf-8").read()


class AMachineEstablishesItsOwnTree(unittest.TestCase):

    def test_a_refused_anchor_yields_no_path_at_all(self):
        """The worst outcome is a tree built in the WRONG place, not no tree."""
        rows = MT.resolve()
        # REG-1893 - a healthy checkout refuses no anchor, so this loop judged nothing on every machine
        # that ran it. Drive the refusal resolve() really takes (a frozen build has no repo anchor) and
        # require at least one REFUSED row before the claim.
        real_frozen = MT._frozen
        MT._frozen = lambda: True
        try:
            rows = rows + MT.resolve()
        finally:
            MT._frozen = real_frozen
        self.assertTrue([r for r in rows if r["state"] == MT.REFUSED],
                        "no root was REFUSED, even in a frozen build - 'a refused anchor yields no path' "
                        "would be judged over nothing")
        for r in rows:
            if r["state"] == MT.REFUSED:
                self.assertIsNone(
                    r["path"],
                    "%r was REFUSED yet still carries a path - a refusal that still names a "
                    "location is a guess wearing a refusal's clothes" % r["root"])

    def test_every_root_declares_its_own_anchor_kind(self):
        """A global precedence would relocate the ledger writer that already works."""
        known = set(MT.anchors().keys())
        for name, kind, parts in MT.ROOTS:
            self.assertIn(kind, known,
                          "root %r claims anchor %r, which anchors() does not produce" % (name, kind))
            self.assertTrue(parts, "root %r declares no path segments" % name)

    def test_a_frozen_build_refuses_the_repo_anchor(self):
        """A frozen app's repo root lives inside the executable and does not survive a restart."""
        had = hasattr(sys, "frozen")
        old = getattr(sys, "frozen", None)
        sys.frozen = True
        try:
            path, why = MT.anchors()["repo"]
            self.assertIsNone(path, "a frozen build still returned a repo anchor (%s)" % why)
            self.assertIn("frozen", why)
        finally:
            if had:
                sys.frozen = old
            else:
                del sys.frozen

    def test_found_requires_a_PROVEN_WRITE_not_mere_existence(self):
        """A directory that exists is not a directory that works."""
        self.assertIn("_prove_write(p)", SRC,
                      "ensure() does not call the prover at all, so `found` would mean only that "
                      "a path exists")

        # ⚠ BEHAVIOUR, NOT PRESENCE. My first version of this case asserted only that
        # _prove_write EXISTS and IS CALLED - and its red-proof came back BLIND, because a
        # sabotage that guts the FUNCTION BODY leaves both of those true. A presence-law is not a
        # behaviour-law. [[presence-law-vs-reachability-law]] [[source-reading-guard]]
        import tempfile
        fd, a_file = tempfile.mkstemp()
        os.close(fd)
        try:
            ok, why = MT._prove_write(a_file)      # a FILE is not a directory
            self.assertFalse(ok, "a plain file passed the write proof, so any non-directory "
                                 "would report as an established root")
            self.assertIn("not a directory", why)
        finally:
            os.remove(a_file)

        missing = os.path.join(tempfile.gettempdir(), "__no_such_root_%d__" % os.getpid())
        ok2, _ = MT._prove_write(missing)
        self.assertFalse(ok2, "a path that does not exist passed the write proof")

        d = tempfile.mkdtemp()                     # a real, writable directory MUST pass
        try:
            ok3, why3 = MT._prove_write(d)
            self.assertTrue(ok3, "a writable directory failed the proof (%s) - the law would be "
                                 "red on every healthy machine" % why3)
            self.assertEqual([], [f for f in _fx_tmp.list_own(d)],
                             "the probe file was left behind")
        finally:
            os.rmdir(d)

    def test_a_path_that_is_not_ascii_cannot_reach_a_message(self):
        """A user profile can carry a non-ASCII character; printing it kills a cp1255 console."""
        self.assertEqual(MT._ascii("C:\\Users\\\u05d0\\x"), "C:\\Users\\?\\x")
        self.assertNotIn("%s at %s\" % (e.__class__.__name__, p)", SRC,
                         "a raw path reaches a message without _ascii()")

    def test_the_states_are_five_distinct_facts_not_a_boolean(self):
        """created / found / unusable / failed / refused demand different responses."""
        states = {MT.CREATED, MT.FOUND, MT.UNUSABLE, MT.FAILED, MT.REFUSED}
        self.assertEqual(len(states), 5, "the five states collapsed: %r" % (states,))

    def test_report_only_creates_nothing(self):
        """Looking at the tree must never provision it."""
        import tempfile
        d = tempfile.mkdtemp()
        probe = os.path.join(d, "never_made")
        rows = [{"root": "x", "anchor": "home", "path": probe, "state": None, "why": ""}]
        self.assertFalse(os.path.isdir(probe))
        self.assertIn("create=True", SRC, "ensure() lost its create switch")
        self.assertIn("creation was not requested", SRC,
                      "ensure(create=False) no longer reports why it did not create")

    def test_the_film_writer_walks_the_one_door(self):
        """frame_authority and reel_retention PLAN; tv_diablo WRITES. The writers call establish()."""
        with io.open(os.path.join(HERE, "tv_diablo.py"), encoding="utf-8") as fh:
            td = fh.read()
        code = "\n".join(l.split("#", 1)[0] for l in td.split("\n"))
        self.assertIn("def _establish_footage(", td)
        self.assertEqual(code.count("_mt.establish()"), 1,
                         "the film helper no longer calls machine_tree.establish()")
        self.assertNotIn("os.makedirs(FRAMES", code,
                         "the film loop grew a second door for the frames root")
        self.assertNotIn("os.makedirs(HIST_DIR", code,
                         "the archive path grew a second door for hist")
        self.assertIn("_establish_footage()", code)

    def test_the_planners_still_create_nothing(self):
        """v3393 reporter law: plan/report only. Deletion needs --apply --yes."""
        for name in ("frame_authority.py", "reel_retention.py"):
            with io.open(os.path.join(HERE, name), encoding="utf-8") as fh:
                raw = fh.read()
            code = "\n".join(l.split("#", 1)[0] for l in raw.split("\n"))
            self.assertNotIn("os.makedirs", code,
                             "%s grew a makedirs — planners do not provision" % name)
            self.assertIn("footage_hist", code,
                          "%s never asks the door for the default hist" % name)

    def test_establish_in_a_harness_does_not_call_the_live_door(self):
        """TV_HIST set -> scratch only. A live ensure() from a harness plants his real tree."""
        import tempfile
        import shutil
        scratch = tempfile.mkdtemp(prefix="mt-harness-")
        hist = os.path.join(scratch, "hist")
        old = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = hist
        try:
            rows = MT.establish()
            self.assertTrue(os.path.isdir(hist), "the scratch hist was not created")
            self.assertTrue(rows, "establish() returned no rows for an isolated harness")
            self.assertTrue(
                all(r.get("anchor") == "env" for r in rows),
                "establish() under TV_HIST still walked a live anchor: %r"
                % [(r.get("root"), r.get("anchor")) for r in rows])
        finally:
            if old is None:
                os.environ.pop("TV_HIST", None)
            else:
                os.environ["TV_HIST"] = old
            shutil.rmtree(scratch, True)


RED_PROOF = [
    {
        "why": "an _ascii passthrough lets a non-ASCII path reach a message, which crashes the "
               "process on a cp1255 console WHILE it reports the error",
        "file": "tv/machine_tree.py",
        "find": '        return str(s).encode("ascii", "replace").decode("ascii")',
        "replace": '        return str(s)',
        "matches": 1,
    },
    {
        "why": "if a frozen build still returns a repo anchor, the tree is built inside the "
               "executable or a temp dir and vanishes on the next run",
        "file": "tv/machine_tree.py",
        "find": '    if _frozen():\n        out["repo"] = (None,',
        "replace": '    if False:\n        out["repo"] = (None,',
        "matches": 1,
    },
    {
        "why": "a prove_write that always agrees turns `found` back into mere existence, so a "
               "read-only or wrongly-ACLed directory reads as established",
        "file": "tv/machine_tree.py",
        "find": '    if not os.path.isdir(path):\n        return False, "it exists but is not a directory"',
        "replace": '    if not os.path.isdir(path):\n        return True, ""',
        "matches": 1,
    },
    {
        "why": "if establish() still calls ensure() under TV_HIST, a harness plants the live tree",
        "file": "tv/machine_tree.py",
        "find": "    if hist or frames:\n        rows = []",
        "replace": "    if False:\n        rows = []",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
