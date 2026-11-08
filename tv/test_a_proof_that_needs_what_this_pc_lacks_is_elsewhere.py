#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REG-1686 - A RED-PROOF THAT NEEDS WHAT THIS PC LACKS IS ELSEWHERE, NEVER BLIND.

MEASURED on his ALT 2026-10-01 ~16:45: the census filed test_the_character_builder_is_their_builder BLIND on proofs [9]
and [10] (20 of 22 PROVEN). Both tamper the builder's generator, and the one case that drives the generator skips on a PC
with no local D2R install - the ALT plays through a cloud client - in the clean run AND the tampered one, so the tampered
run stayed green about nothing. That single BLIND record shut every lock on the ALT (reel.route, printer.stream,
vault.sweep_start, frame.release all answered "1 instrument(s) are BLIND"), so the river stopped again.

Driven through the REAL heart2._prove_one / _prove_gate (only the law runs and the host probe are stand-ins):
  1. a proof that declares `"needs"` a capability this PC lacks is ELSEWHERE and its law is never run here;
  2. where the PC has it, the proof is judged exactly as before (it can still go BLIND);
  3. a capability name no probe knows is INVALID - a typo never excuses a proof;
  4. a gate is PROVEN when its other proofs are and the rest are ELSEWHERE; every proof ELSEWHERE is UNPROVABLE here;
     a BLIND among them stays BLIND;
  5. the builder law's [9] and [10] declare the install; the install probe is the ONE rule _pull itself checks.
  6. REG-2354 - a proof whose every law skipped in BOTH runs, on a PC with no node, for a gate that reaches for node, is
     ELSEWHERE; with node, with laws that ran, or with a gate that never names node, it is BLIND exactly as before.
     MEASURED on Dean's PC 2026-10-21: 53 of its 56 BLIND were that shape, and 0 of its 9 locks were permitted;
  7. "node" and "bash" answer from PATH, the question the laws' own skips ask;
  8. a BLIND filed under an older BLIND_RULE is owed again though its file is unchanged, a slice takes it off the list
     whatever it finds, and self_prove reads a census that still carries one as stale.
  9. REG-2359 (round 3) - 6's skips must be NODE's: a reason that is not node's (his D2R install, his footage), one such
     reason among node's, a skip the watch did not see, or no watch at all is BLIND as before, and the ELSEWHERE line
     says only what was measured. The reasons come from the run itself - gate_trace's skip watch, at any verbosity, the
     run's own process only - driven over a real fixture law.
 10. REG-2357 (round 3) - a proof of a law whose every case skips off POSIX, declaring no need, is INVALID where it can
     be judged (it files BLIND on Windows); declared, it is judged on POSIX and ELSEWHERE on Windows; a law with one
     case that runs on Windows is judged as before; a proof caught only by off-POSIX cases is said, never refused. The
     off-POSIX reader is driven over every skip shape it must tell apart.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _console_safe_enable  # noqa: E402  (its red-proofs carry non-ASCII)
_console_safe_enable()
import heart2 as H  # noqa: E402
import self_prove as SP  # noqa: E402

LINES = []


def _say(*a):
    LINES.append(" ".join(str(x) for x in a))


class _Sandbox(unittest.TestCase):

    def setUp(self):
        del LINES[:]
        root = tempfile.mkdtemp(prefix="elsewhere_")
        self.addCleanup(shutil.rmtree, root, True)
        self.tv = os.path.join(root, "tv")
        os.makedirs(self.tv)
        with io.open(os.path.join(self.tv, "subject.py"), "w", encoding="utf-8") as fh:
            fh.write("ANCHOR = 1\n")
        with io.open(os.path.join(self.tv, "test_law.py"), "w", encoding="utf-8") as fh:
            fh.write("pass\n")
        self.runs = []

    def proof(self, needs=None):
        pr = {"why": "a stand-in", "file": "subject.py", "find": "ANCHOR = 1\n", "replace": "ANCHOR = 2\n",
              "matches": 1}
        if needs is not None:
            pr["needs"] = needs
        return pr

    def judge(self, pr, lacks, tampered_red=True):
        def run_gate(sandbox_tv, filename, timeout=180, extra=(), script=None, widths=None):
            with io.open(os.path.join(sandbox_tv, "subject.py"), encoding="utf-8") as fh:
                tampered = "ANCHOR = 2" in fh.read()
            self.runs.append("tampered" if tampered else "clean")
            if tampered:
                return (not tampered_red), ("Ran 3 tests\nFAILED" if tampered_red else "Ran 3 tests\nOK")
            return True, "Ran 3 tests\nOK"
        probe = {"d2r-install": ("_elsewhere_probe", "have", "the D2R install")}
        sys.modules["_elsewhere_probe"] = types.SimpleNamespace(have=lambda: not lacks)
        self.addCleanup(sys.modules.pop, "_elsewhere_probe", None)
        with mock.patch.object(H, "_run_gate", run_gate), mock.patch.object(H, "PROOF_NEEDS_HOST", probe):
            return H._prove_one(self.tv, "test_law", "test_law.py", pr, 0, _say)


class AProofThatNeedsWhatThisPcLacks(_Sandbox):

    def test_it_is_elsewhere_and_its_law_never_runs_here(self):
        v = self.judge(self.proof("d2r-install"), lacks=True, tampered_red=False)
        self.assertEqual(v, H.ELSEWHERE, "a proof this PC cannot judge was filed %s" % v)
        self.assertEqual(self.runs, [], "the law was run for a proof this PC cannot judge: %r" % self.runs)
        self.assertTrue(any("ELSEWHERE" in l and "the D2R install" in l for l in LINES), LINES)

    def test_where_the_pc_has_it_it_is_judged_as_before(self):
        v = self.judge(self.proof("d2r-install"), lacks=False, tampered_red=True)
        self.assertEqual(v, H.PROVEN)
        self.assertIn("tampered", self.runs)
        v2 = self.judge(self.proof("d2r-install"), lacks=False, tampered_red=False)
        self.assertEqual(v2, H.BLIND, "a declared need softened a real BLIND on a PC that HAS the capability")

    def test_an_undeclared_capability_is_invalid(self):
        v = self.judge(self.proof("d2r-instal"), lacks=True, tampered_red=False)
        self.assertEqual(v, H.INVALID, "a mistyped capability excused a proof")

    def test_a_proof_with_no_need_is_untouched(self):
        v = self.judge(self.proof(), lacks=True, tampered_red=False)
        self.assertEqual(v, H.BLIND, "a proof that declared nothing was excused")


class AnAllSkippedProofOnAPcWithNoNode(_Sandbox):
    """REG-2354 - MEASURED on Dean's PC 2026-10-21: no node on PATH, and 53 of the 56 gates its census filed BLIND were JS
    laws whose every law skipped in the clean run AND the tampered one ("the tamper was never judged"). One BLIND shuts
    every lock on a PC: 0 of 9 permitted there, 135 reels on disk, not one ever tombstoned."""

    ALL = "Ran 4 tests in 0.002s\n\nOK (skipped=4)"
    SOME = "Ran 4 tests in 0.002s\n\nOK (skipped=2)"
    GONE = "node is absent - this law is UNMEASURED, not passing"
    NODE_GONE = [("__main__.A.test_a", GONE), ("__main__.A.test_b", GONE), ("__main__.A.test_c", GONE),
                 ("__main__.B.test_d", "no node on PATH")]
    #: a law like T5's reader-cap law: one class needs node, the other runs only on POSIX
    NODE_AND_POSIX = ("import os, shutil, unittest\nNODE = shutil.which('node')\n"
                      "@unittest.skipIf(NODE is None, 'node is absent')\nclass A(unittest.TestCase):\n"
                      "    def test_a(self): pass\n    def test_b(self): pass\n    def test_c(self): pass\n"
                      "@unittest.skipUnless(os.name == 'posix', 'no shell on Windows')\nclass P(unittest.TestCase):\n"
                      "    def test_p(self): pass\n")

    def skipping(self, node, tail=None, names_node=True, reasons="node", posix=True, src=None):
        """`reasons`: what the skip watch says the run's own process skipped, [(case, reason)] (REG-2359) - "node" is
        four that name node; None is a run no watch could read. `posix`: whether this PC is POSIX."""
        with io.open(os.path.join(self.tv, "test_law.py"), "w", encoding="utf-8") as fh:
            fh.write(src or ("NODE = shutil.which('node')\n" if names_node else "pass\n"))
        out = tail or self.ALL
        said = self.NODE_GONE if reasons == "node" else reasons

        def run_gate(sandbox_tv, filename, timeout=180, extra=(), script=None, widths=None):
            with io.open(os.path.join(sandbox_tv, "subject.py"), encoding="utf-8") as fh:
                self.runs.append("tampered" if "ANCHOR = 2" in fh.read() else "clean")
            H._LAST_SKIPS[threading.get_ident()] = None if said is None else list(said)
            return True, out
        probe = {"node": ("_elsewhere_probe", "have", "Node.js on PATH"),
                 "posix": ("_elsewhere_probe", "posix", "a POSIX process table")}
        sys.modules["_elsewhere_probe"] = types.SimpleNamespace(have=lambda: node, posix=lambda: posix)
        self.addCleanup(sys.modules.pop, "_elsewhere_probe", None)
        with mock.patch.object(H, "_run_gate", run_gate), mock.patch.object(H, "PROOF_NEEDS_HOST", probe):
            return H._prove_one(self.tv, "test_law", "test_law.py", self.proof(), 0, _say)

    def test_it_is_elsewhere_on_a_pc_with_no_node(self):
        v = self.skipping(node=False)
        self.assertEqual(v, H.ELSEWHERE, "a tamper no law judged was filed %s on a PC with no node" % v)
        self.assertEqual(self.runs, ["clean", "tampered"], "PREMISE: both runs were asked")
        self.assertTrue(any("ELSEWHERE" in l and "never judged" in l for l in LINES), LINES)

    def test_a_pc_with_node_still_files_it_blind(self):
        self.assertEqual(self.skipping(node=True), H.BLIND,
                         "a law that skips everything on a PC that HAS node was excused")

    def test_a_gate_that_never_reaches_for_node_is_still_blind(self):
        self.assertEqual(self.skipping(node=False, names_node=False), H.BLIND,
                         "a law that opts out for some other reason was excused by node's absence")

    def test_laws_that_ran_and_stayed_green_are_still_blind(self):
        self.assertEqual(self.skipping(node=False, tail=self.SOME), H.BLIND,
                         "laws that RAN and stayed green were excused because others skipped")

    # REG-2359 (the round-3 review) - the COUNTS were the whole rule: a gate that mentions node, on a PC without it, whose
    # every case skipped for ANY reason - his D2R install, his footage - was excused. Each skip must be for what this PC
    # lacks: node, by its reason, or POSIX, by a case that runs only there.
    def test_a_law_that_skipped_for_another_reason_is_still_blind(self):
        v = self.skipping(node=False, reasons=[(c, "the D2R install is not on this PC") for c, _r in self.NODE_GONE])
        self.assertEqual(v, H.BLIND, "a law that skipped for want of his D2R install was excused by node's absence")

    def test_one_skip_that_is_not_nodes_keeps_it_blind(self):
        v = self.skipping(node=False, reasons=self.NODE_GONE[:3] + [("__main__.B.test_d", "his footage is not here")])
        self.assertEqual(v, H.BLIND, "a run with a skip that was not node's was excused")

    def test_a_skip_the_watch_did_not_see_keeps_it_blind(self):
        self.assertEqual(self.skipping(node=False, reasons=self.NODE_GONE[:3]), H.BLIND,
                         "a run whose skips the watch saw only 3 of 4 of was excused on the 3 it saw")
        self.assertEqual(self.skipping(node=False, reasons=None), H.BLIND,
                         "a run no skip watch could read was excused on its counts alone")
        self.assertEqual(self.skipping(node=False, reasons=[]), H.BLIND)

    def test_a_case_that_runs_only_on_posix_is_excused_only_where_posix_is_not(self):
        """T5's reader-cap law on Dean's PC (Windows, no node): its node class skips for node, its POSIX class for being
        on Windows - every case skipped for what that PC lacks."""
        skips = self.NODE_GONE[:3] + [("__main__.P.test_p", "no shell on Windows")]
        self.assertEqual(self.skipping(node=False, posix=False, reasons=skips, src=self.NODE_AND_POSIX), H.ELSEWHERE,
                         "a law whose every skip was for what this PC lacks (node, POSIX) was filed BLIND")
        self.assertTrue(any("1 case(s) run only on POSIX" in l for l in LINES), LINES)
        self.assertEqual(self.skipping(node=False, posix=True, reasons=skips, src=self.NODE_AND_POSIX), H.BLIND,
                         "on a POSIX PC a POSIX-only case that skipped was excused as if POSIX were missing")
        self.assertEqual(self.skipping(node=False, posix=False, src=self.NODE_AND_POSIX,
                                       reasons=self.NODE_GONE[:3] + [("__main__.A.test_x", "no shell on Windows")]),
                         H.BLIND, "a skip of a case that is not POSIX-only was excused as POSIX's")
        self.assertEqual(self.skipping(node=False, posix=False, src=self.NODE_AND_POSIX,
                                       reasons=[(c, "no shell on Windows") for c in
                                                ("__main__.P.test_p",) * 4]), H.BLIND,
                         "a run with no node skip at all was excused for want of node")

    def test_the_line_says_only_what_was_measured(self):
        """REG-2359 (round 4, the review) - the line said 'every case skipped in BOTH runs, each for what this PC lacks',
        and only the TAMPERED run's reasons are read. It now says both runs' counts (each from its own tail) and the
        tampered run's reasons, and claims no reason of the clean run's."""
        self.assertEqual(self.skipping(node=False), H.ELSEWHERE)
        line = [l for l in LINES if "ELSEWHERE" in l][-1]
        for words in ("both runs skipped every case", "clean run: 4 of 4 skipped", "tampered run: 4 of 4 skipped",
                      "the tampered run's 4 skip reason(s)", "4 name node", "node is absent", "no node on PATH",
                      "never judged here"):
            self.assertIn(words, line, "the ELSEWHERE line does not say %r: %s" % (words, line))
        self.assertNotIn("BOTH runs, each for", line, "the line claims the clean run's reasons were read: %s" % line)
        self.assertNotIn("POSIX", line, "the line names POSIX skips the run did not have: %s" % line)
        self.assertNotIn("is proven on", line, "the ELSEWHERE line claims a proof that was never made: %s" % line)
        self.assertNotIn("runs the page's own JavaScript", line, "the line claims what this law runs: %s" % line)


class TheSkipWatchSaysWhyEachCaseSkipped(unittest.TestCase):
    """REG-2359 - the reasons come from the run itself: gate_trace's skip watch writes one line per case the run's OWN
    process skipped, at any verbosity (at verbosity 1 a log carries only an `s`), and never a child's."""

    LAW = (
        "import subprocess, sys, unittest\n"
        "CHILD = ('import unittest\\nclass C(unittest.TestCase):\\n    @unittest.skip(\"a child skip about node\")\\n'\n"
        "         '    def test_c(self): pass\\nunittest.main()\\n')\n"
        "@unittest.skipIf(True, 'node is absent - this law is UNMEASURED, not passing')\n"
        "class A(unittest.TestCase):\n"
        "    def test_a(self): pass\n"
        "    def test_b(self): pass\n"
        "class B(unittest.TestCase):\n"
        "    def test_child(self):\n"
        "        r = subprocess.run([sys.executable, '-c', CHILD], capture_output=True, text=True)\n"
        "        self.assertIn('skipped=1', r.stderr)\n"
        "    def test_s(self):\n"
        "        self.skipTest('no node on PATH')\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n")

    def test_a_real_run_says_the_reason_of_each_of_its_own_skips(self):
        d = tempfile.mkdtemp(prefix="skipwatch_")
        self.addCleanup(shutil.rmtree, d, True)
        tv = os.path.join(d, "tv")
        os.makedirs(tv)
        with io.open(os.path.join(tv, "law_gate.py"), "w", encoding="utf-8") as fh:
            fh.write(self.LAW)
        ok, tail = H._run_gate_once(tv, "law_gate.py", timeout=120)
        skips = H._LAST_SKIPS.get(threading.get_ident())
        self.assertIs(ok, True, "PREMISE: the fixture law is green with 3 of its 4 cases skipped: %s" % tail)
        self.assertIn("skipped=3", tail)
        gone = "node is absent - this law is UNMEASURED, not passing"
        self.assertEqual(skips, [("__main__.A.test_a", gone), ("__main__.A.test_b", gone),
                                 ("__main__.B.test_s", "no node on PATH")],
                         "the skip watch did not say which case of the run's own process skipped and why (or said a "
                         "child's skip): %r" % (skips,))
        self.assertEqual(H._skipped_for_want(tail, skips), (skips, []))


#: REG-2357 - every skip shape the off-POSIX reader must tell apart, one case each
SHAPES = r'''
import os, shutil, signal, sys, unittest
_POSIX = os.name == "posix" and hasattr(signal, "SIGKILL")
posix_only = unittest.skipUnless(os.name == "posix", "a named decorator")


@unittest.skipUnless(_POSIX, "a module-level name")
class ByName(unittest.TestCase):
    def test_a(self): pass
    def test_b(self): pass


class ByMethod(unittest.TestCase):
    @unittest.skipIf(sys.platform.startswith("win"), "startswith")
    def test_win_prefix(self): pass

    @unittest.skipIf(os.name == "nt", "os.name")
    def test_nt(self): pass

    @unittest.skipUnless(hasattr(os, "killpg"), "an os attribute Windows lacks")
    def test_killpg(self): pass

    @posix_only
    def test_named(self): pass

    @unittest.skipIf(sys.platform == "darwin", "skips on the Mac, runs on Windows")
    def test_not_mac(self): pass

    @unittest.skip("skips everywhere")
    def test_everywhere(self): pass

    @unittest.skipUnless(shutil.which("bash"), "a condition no reader can evaluate")
    def test_unknown(self): pass

    def test_plain(self): pass
'''

ALL_POSIX = (
    "import os, unittest\n"
    "@unittest.skipUnless(os.name == 'posix', 'POSIX signals')\n"
    "class A(unittest.TestCase):\n"
    "    def test_a(self): pass\n"
    "    def test_b(self): pass\n")
SOME_POSIX = ALL_POSIX + "class B(unittest.TestCase):\n    def test_c(self): pass\n"


class ALawWhoseEveryCaseSkipsOffPosixSaysSo(_Sandbox):
    """REG-2357 (the round-3 review) - test_a_killed_run_is_never_a_red held its 17 cases in three classes, each
    skipUnless(_POSIX), and declared no need on its 26 proofs: on Windows every case skipped in both runs and all 26
    filed BLIND, and one BLIND shuts every lock on that PC. Such a proof is refused where it CAN be judged."""

    def gate(self, src):
        with io.open(os.path.join(self.tv, "test_law.py"), "w", encoding="utf-8") as fh:
            fh.write(src)

    def judge_on(self, platform, pr, caught=None, tampered_red=True):
        def run_gate(sandbox_tv, filename, timeout=180, extra=(), script=None, widths=None):
            with io.open(os.path.join(sandbox_tv, "subject.py"), encoding="utf-8") as fh:
                tampered = "ANCHOR = 2" in fh.read()
            self.runs.append("tampered" if tampered else "clean")
            if tampered and caught is not None:
                H._LAST_RED[threading.get_ident()] = list(caught)
            if tampered:
                return (not tampered_red), ("Ran 3 tests\nFAILED" if tampered_red else "Ran 3 tests\nOK")
            return True, "Ran 3 tests\nOK"
        # v3886 (#107, windows-latest: "'ELSEWHERE' != 'PROVEN' : posix") - the "posix" probe reads os.name, which the
        # platform below never reached: on a Windows runner the simulated Mac still lacked POSIX. The simulated PC is one PC.
        with mock.patch.object(H, "_run_gate", run_gate), mock.patch.object(H.sys, "platform", platform), \
                mock.patch.object(H, "_host_is_posix", lambda: not platform.startswith("win")):
            return H._prove_one(self.tv, "test_law", "test_law.py", pr, 0, _say)

    def test_the_reader_tells_each_skip_shape_apart(self):
        off, every = H.posix_only_cases(SHAPES)
        self.assertEqual(len(every), 10, "PREMISE: every case is counted: %s" % sorted(every))
        self.assertEqual(sorted(off), ["ByMethod.test_killpg", "ByMethod.test_named", "ByMethod.test_nt",
                                       "ByMethod.test_win_prefix", "ByName.test_a", "ByName.test_b"],
                         "the off-POSIX cases are wrong (a skip on the Mac, a skip everywhere or an unknown condition "
                         "is never off-POSIX)")
        self.assertIsNone(H.posix_only_cases("def broken(:\n"), "a source that will not parse was read as one")

    def test_a_proof_of_such_a_law_that_declares_nothing_is_invalid(self):
        self.gate(ALL_POSIX)
        v = self.judge_on("darwin", self.proof())
        self.assertEqual(v, H.INVALID, "a proof of a law whose every case skips off POSIX, declaring no need, was "
                                       "filed %s - on Windows it files BLIND and shuts every lock there" % v)
        self.assertEqual(self.runs, [], "the law was run for a proof refused on its declaration")
        self.assertTrue(any("skips off POSIX" in l and "posix-signals" in l for l in LINES), LINES)

    def test_declared_it_is_judged_on_posix_and_elsewhere_on_windows(self):
        self.gate(ALL_POSIX)
        for need in ("posix-signals", "posix", "macos"):
            del self.runs[:]
            self.assertEqual(self.judge_on("darwin", self.proof(need)), H.PROVEN, need)
            self.assertIn("tampered", self.runs, need)
        del self.runs[:]
        self.assertEqual(self.judge_on("win32", self.proof("posix-signals")), H.ELSEWHERE)
        self.assertEqual(self.runs, [], "Windows ran a proof it can never judge")

    def test_a_reader_that_cannot_read_refuses_nothing(self):
        """The reader is asked inside _prove_one, where a raise is recorded BLIND - and one BLIND shuts every lock."""
        self.gate(ALL_POSIX)
        H._POSIX_ONLY_MEMO.clear()
        self.addCleanup(H._POSIX_ONLY_MEMO.clear)
        with mock.patch.object(H, "posix_only_cases", mock.Mock(side_effect=RecursionError("too deep to parse"))):
            v = self.judge_on("darwin", self.proof())
        self.assertEqual(v, H.PROVEN, "a reader that raised refused, or crashed, a proof it could not read: %s" % v)

    def test_a_law_with_a_case_that_runs_on_windows_is_judged_as_before(self):
        self.gate(SOME_POSIX)
        self.assertEqual(self.judge_on("darwin", self.proof()), H.PROVEN)

    def test_a_proof_caught_only_by_off_posix_cases_is_said(self):
        self.gate(SOME_POSIX)
        self.assertEqual(self.judge_on("darwin", self.proof(), caught=["A.test_a"]), H.PROVEN,
                         "the note changed the verdict - it is said, never a refusal")
        self.assertTrue(any("REG-2357" in l and "A.test_a" in l and "skips off POSIX" in l for l in LINES),
                        "a proof whose only catching case skips off POSIX was not said: %s" % LINES)
        del LINES[:]
        self.judge_on("darwin", self.proof(), caught=["A.test_a", "B.test_c"])
        self.judge_on("darwin", self.proof("posix"), caught=["A.test_a"])
        self.assertFalse(any("REG-2357" in l for l in LINES), "said with a catching case that runs on Windows, or with "
                                                              "the need declared: %s" % LINES)


class NodeAndBashAnswerFromPath(unittest.TestCase):
    """REG-2354 - the capability is the question the laws' own skips ask (shutil.which), never a guess."""

    def test_a_pc_without_them_lacks_them(self):
        with mock.patch.object(H.shutil, "which", lambda name, *a, **k: None):
            self.assertIs(H.host_lacks("node")[0], True, "a PC with no node on PATH claimed node")
            self.assertIs(H.host_lacks("bash")[0], True, "a PC with no bash on PATH claimed bash")

    def test_a_pc_with_them_has_them(self):
        with mock.patch.object(H.shutil, "which", lambda name, *a, **k: "/bin/" + name):
            self.assertIs(H.host_lacks("node")[0], False)
            self.assertIs(H.host_lacks("bash")[0], False)


class ABlindFiledUnderAnOlderRuleIsJudgedAgain(unittest.TestCase):
    """REG-2355 - a gate is owed only when its OWN file changes, and self_prove stops for good once the census reads
    current, so the BLINDs Dean's census filed under the old rule would have stood for ever under the fixed one."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="blind_rule_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.gates = []
        for n in ("g1", "g2", "g3"):
            f = os.path.join(self.d, "test_%s.py" % n)
            with io.open(f, "w", encoding="utf-8") as fh:
                fh.write('RED_PROOF = [{"why": "fixture %s", "file": "nowhere.py", "find": "a", "replace": "b", '
                         '"matches": 1}]\n' % n)
            self.gates.append((n, f))
        self.state = os.path.join(self.d, ".heart2.json")
        for p in (mock.patch.object(H, "gate_files", lambda say=print: list(self.gates)),
                  mock.patch.object(H, "STATE", self.state)):
            p.start()
            self.addCleanup(p.stop)

    def old_census(self, blind):
        """a census as the old rule left it: every gate proved against its file, `blind` filed, no blindRule"""
        st = {"gateShas": H.gate_shas(self.gates), "blind": list(blind), "provedGates": [], "partial": True,
              "gatesFingerprint": H.gates_fingerprint(self.gates)}
        with io.open(self.state, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        return st

    def census(self):
        with io.open(self.state, encoding="utf-8") as fh:
            return json.load(fh)

    def owed(self, st):
        return [n for n, _k in H.slice_owed(gates=self.gates, state=st)["owed"]]

    def test_an_unchanged_gate_filed_blind_under_the_old_rule_is_owed(self):
        self.assertEqual(self.owed(self.old_census(["g2", "g3"])), ["g2", "g3"],
                         "a BLIND the old rule filed is not owed - the fixed rule would never reach it")

    def test_a_census_under_this_rule_owes_only_what_is_left(self):
        st = dict(self.old_census(["g2", "g3"]), blindRule=H.BLIND_RULE, blindRuleOwed=["g3"])
        self.assertEqual(self.owed(st), ["g3"])

    def test_a_slice_shrinks_what_is_left_whatever_it_found(self):
        self.old_census(["g2", "g3"])
        H._write_state({"g2": H.BLIND}, stamp=False)        # judged again and still BLIND: it leaves the list all the same
        c = self.census()
        self.assertEqual(c.get("blindRule"), H.BLIND_RULE)
        self.assertEqual(c.get("blindRuleOwed"), ["g3"],
                         "a gate judged under the new rule is still owed - a slice of only those lands none and is "
                         "booked a failure, for ever")
        H._write_state({"g3": H.UNPROVABLE}, stamp=False)
        c = self.census()
        self.assertEqual(c.get("blindRuleOwed"), [])
        self.assertEqual(c.get("blind"), ["g2"], "a gate judged ELSEWHERE kept its old BLIND")
        self.assertEqual(self.owed(c), [])

    def test_self_prove_reads_a_current_census_with_old_rule_blinds_as_stale(self):
        self.old_census(["g2"])
        st = SP.census_state()
        self.assertEqual(st["state"], "stale", "a census still carrying an old-rule BLIND read current: %s" % st)
        self.assertEqual(st["owed"], 1)


class TheGateCountsWhatWasJudgedHere(unittest.TestCase):

    def gate(self, verdicts):
        with mock.patch.object(H, "_prove_gate_proofs", lambda *a, **k: list(verdicts)), \
                mock.patch.object(H, "_closing_clean", lambda name, v, say: v), \
                mock.patch.object(H, "_PUSH", None):
            return H._prove_gate("sb", "g", "g.py", [{}] * len(verdicts), _say)[0]

    def test_proven_with_the_rest_elsewhere_is_proven(self):
        self.assertEqual(self.gate([H.PROVEN, H.ELSEWHERE, H.PROVEN]), H.PROVEN)

    def test_every_proof_elsewhere_is_unprovable_here(self):
        self.assertEqual(self.gate([H.ELSEWHERE, H.ELSEWHERE]), H.UNPROVABLE,
                         "a gate with nothing judged on this PC was filed PROVEN")

    def test_a_blind_among_them_stays_blind(self):
        self.assertEqual(self.gate([H.BLIND, H.ELSEWHERE]), H.BLIND)


class ThePushPathCountsTheSameWay(unittest.TestCase):
    """#145 (the #231 eye on v3546) - _prove_gate returns _prove_gate_push's verdict first whenever a push is running,
    and _push_gate_verdict knew BLIND, INVALID, NOT RUN and UNPROVABLE only: a gate whose every proof was ELSEWHERE fell
    through to PROVEN and was banked by a push on a PC that judged none of it. The rule is the same on both paths."""

    def test_every_proof_elsewhere_is_unprovable_at_push_time_too(self):
        self.assertEqual(H._push_gate_verdict([H.ELSEWHERE, H.ELSEWHERE]), H.UNPROVABLE,
                         "a push banked a gate no proof had judged on this PC")

    def test_a_mix_and_a_stop_are_as_before(self):
        self.assertEqual(H._push_gate_verdict([H.PROVEN, H.ELSEWHERE]), H.PROVEN)
        self.assertEqual(H._push_gate_verdict([H.ELSEWHERE, None]), H.NOT_RUN)
        self.assertEqual(H._push_gate_verdict([H.BLIND, H.ELSEWHERE]), H.BLIND)


class ASliceBankerNeverOutlivesItsRun(unittest.TestCase):
    """#145 (the #231 eye on v3545) - prove() installed the slice banker on _GATE_HOOK and cleared it only on the line
    after _prove_gates returned: a raise left it installed, closed over that slice's blank set, and a later push in the
    same process would call it at every finished gate. Cleared in a finally, and a push clears it on entry."""

    ONLY = ["test_a_proof_that_needs_what_this_pc_lacks_is_elsewhere"]

    def setUp(self):
        self._hook = H._GATE_HOOK.get("fn")
        self.addCleanup(H._GATE_HOOK.__setitem__, "fn", self._hook)

    def test_a_slice_that_raises_leaves_no_banker_behind(self):
        def boom(*a, **k):
            raise RuntimeError("a lane died")
        with mock.patch.object(H, "_prove_gates", boom), mock.patch.object(H, "_write_state", lambda *a, **k: None):
            with self.assertRaises(RuntimeError):
                H.prove(only=self.ONLY, say=_say, stamp=False)
        self.assertIsNone(H._GATE_HOOK.get("fn"), "a raising slice left its banker installed for the next run")

    def test_a_push_never_banks_through_a_left_over_banker(self):
        seen = []
        H._GATE_HOOK["fn"] = lambda *a, **k: seen.append("leaked")
        def push(have, say, stopped=None, cache=None, blank=None):
            seen.append(H._GATE_HOOK.get("fn"))
            return {}, {}
        with mock.patch.object(H, "_prove_push", push), mock.patch.object(H, "open_cache", lambda say: None), \
                mock.patch.object(H, "_write_state", lambda *a, **k: None):
            H.prove(only=self.ONLY, say=_say, push=True)
        self.assertEqual(seen, [None], "the push ran with another run's banker on the hook: %r" % seen)


class ThePlatformCapabilitiesAreTheProbes(unittest.TestCase):
    """REG-1688 - "macos" and "posix-signals" answer from the platform the prover runs on, never from a guess."""

    def test_windows_lacks_both(self):
        with mock.patch.object(H.sys, "platform", "win32"):
            self.assertIs(H.host_lacks("macos")[0], True, "a Windows PC claimed macOS")
            self.assertIs(H.host_lacks("posix-signals")[0], True, "a Windows PC claimed SIGTERM reaches a handler")

    def test_macos_has_both(self):
        with mock.patch.object(H.sys, "platform", "darwin"):
            self.assertIs(H.host_lacks("macos")[0], False)
            self.assertIs(H.host_lacks("posix-signals")[0], False)

    def test_linux_has_signals_but_is_not_macos(self):
        with mock.patch.object(H.sys, "platform", "linux"):
            self.assertIs(H.host_lacks("macos")[0], True)
            self.assertIs(H.host_lacks("posix-signals")[0], False)


class TheBuilderDeclaresItsInstall(unittest.TestCase):

    def test_the_two_generator_proofs_declare_the_install(self):
        proofs = H.red_proofs_in(os.path.join(HERE, "test_the_character_builder_is_their_builder.py"))
        gen = [i for i, p in enumerate(proofs) if p.get("file") == "char_builder_db.py"
               and "generator" in str(p.get("why"))]
        self.assertGreaterEqual(len(gen), 2, "PREMISE: the generator proofs are not where they were")
        for i in gen:
            self.assertEqual(proofs[i].get("needs"), "d2r-install",
                             "builder proof [%d] tampers the generator but does not declare the install" % i)

    def test_the_install_probe_is_the_one_rule_pull_checks(self):
        import affix_lexicon as AL
        self.assertIn("install_present", AL._pull.__code__.co_names,
                      "_pull checks the install with its own copy of the rule, not install_present")
        self.assertEqual(H.PROOF_NEEDS_HOST["d2r-install"][:2], ("affix_lexicon", "install_present"))


RED_PROOF = [
    {"why": "REG-1686 - a proof this PC cannot judge is run anyway and files BLIND (the ALT's shut river)",
     "file": "heart2.py",
     "find": "        if _lacks:\n            say(\"     %-52s %s — it needs %s, which this PC does not have; it is proven on a PC that does\"\n",
     "replace": "        if False:\n            say(\"     %-52s %s — it needs %s, which this PC does not have; it is proven on a PC that does\"\n",
     "matches": 1},
    {"why": "REG-1686 - a mistyped capability excuses a proof",
     "file": "heart2.py",
     "find": "        if _lacks is None and _words.startswith(\"an undeclared capability\"):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-1686 - a gate with nothing judged here is filed PROVEN",
     "file": "heart2.py",
     "find": "    if verdicts and all(v == ELSEWHERE for v in verdicts):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-1686 - _pull keeps its own copy of the install rule",
     "file": "affix_lexicon.py",
     "find": "    if not install_present():\n        return None\n",
     "replace": "    if not (os.path.exists(EXTRACT) and os.path.isdir(os.path.join(D2R, \"Data\"))):\n        return None\n",
     "matches": 1},
    {"why": "REG-1688 - every PC claims macOS: a Windows prover judges the macOS-only film loop and files it BLIND",
     "file": "heart2.py",
     "find": "    return sys.platform == \"darwin\"\n",
     "replace": "    return True\n",
     "matches": 1},
    {"why": "REG-1688 - Windows claims a SIGTERM reaches the handler, so the farewell proof is judged where it cannot run",
     "file": "heart2.py",
     "find": "    return not sys.platform.startswith(\"win\")\n",
     "replace": "    return True\n",
     "matches": 1},
    {"why": "#145 - at push time a gate whose every proof is ELSEWHERE is banked PROVEN",
     "file": "heart2.py",
     "find": "    if got and all(v == ELSEWHERE for v in got):\n        return UNPROVABLE\n",
     "replace": "    if False:\n        return UNPROVABLE\n",
     "matches": 1},
    {"why": "#145 - a slice that raises leaves its banker installed",
     "file": "heart2.py",
     "find": "            _GATE_HOOK[\"fn\"] = None     # #145 (the v3545 eye) - a raise must not leave this slice's banker installed\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "#145 - a push runs with whatever banker the last run left on the hook",
     "file": "heart2.py",
     "find": "        _GATE_HOOK[\"fn\"] = None         # #145 (the v3545 eye) - a push banks once at the end, never through a slice's banker\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "REG-2354 - an all-skipped tamper on a PC with no node is filed BLIND again, and every lock there shuts",
     "file": "heart2.py",
     "find": "        if (not widths and _skipped_every_law(tail) and _skipped_every_law(tail2)\n",
     "replace": "        if (False and _skipped_every_law(tail) and _skipped_every_law(tail2)\n",
     "matches": 1},
    {"why": "REG-2354 - every PC claims node, so a PC without it judges JS laws it cannot run and files them BLIND",
     "file": "heart2.py",
     "find": "    return shutil.which(\"node\") is not None\n",
     "replace": "    return True\n",
     "matches": 1},
    {"why": "REG-2354 - every PC claims bash, so the hooks law's proof is judged where its only catching law skips",
     "file": "heart2.py",
     "find": "    return shutil.which(\"bash\") is not None\n",
     "replace": "    return True\n",
     "matches": 1},
    {"why": "REG-2355 - a BLIND filed under the old rule is never owed again, so the fixed rule never reaches it",
     "file": "heart2.py",
     "find": "        elif _rule_blind and n in _rule_blind:\n",
     "replace": "        elif False:\n",
     "matches": 1},
    {"why": "REG-2355 - a gate judged under the new rule stays owed: a slice of only those lands none, a failure for ever",
     "file": "heart2.py",
     "find": "    _rule_left = sorted(b for b in blind_rule_owed(prior) if b not in (results or {}) and b in blind)\n",
     "replace": "    _rule_left = sorted(b for b in blind_rule_owed(prior) if b in blind)\n",
     "matches": 1},
    {"why": "REG-2355 - a census that already reads current keeps its old-rule BLINDs for ever",
     "file": "self_prove.py",
     "find": "    elif _rule_owed(_h2, st):\n",
     "replace": "    elif False:\n",
     "matches": 1},
    # REG-2357 (the round-3 review) - a law whose every case skips off POSIX, with proofs that declared no need, filed
    # BLIND on Windows (test_a_killed_run_is_never_a_red, all 26)
    {"why": "REG-2357 - a proof of a law whose every case skips off POSIX may declare nothing, and files BLIND on Windows",
     "file": "heart2.py",
     "find": "        if _po and _po[1] and _po[0] == _po[1]:  # POSIX-ONLY-LAW\n",
     "replace": "        if False:  # POSIX-ONLY-LAW\n",
     "matches": 1},
    {"why": "REG-2357 - the reader evaluates os.name as POSIX on Windows too, so nothing ever skips off POSIX",
     "file": "heart2.py",
     "find": "            return \"nt\" if win else \"posix\"\n",
     "replace": "            return \"posix\"\n",
     "matches": 1},
    {"why": "REG-2357 - a case that skips on the Mac too (everywhere) is called off-POSIX",
     "file": "heart2.py",
     "find": "                    and not any(_skips_under(d, \"darwin\", names) is True for d in decos):  # POSIX-ONLY-CASE\n",
     "replace": "                    and True:  # POSIX-ONLY-CASE\n",
     "matches": 1},
    {"why": "REG-2357 - \"posix-signals\" is not taken as a POSIX need, so the declaration the killed-run law makes is refused",
     "file": "heart2.py",
     "find": "_OFF_POSIX_NEEDS = frozenset((\"posix\", \"posix-signals\", \"macos\"))\n",
     "replace": "_OFF_POSIX_NEEDS = frozenset((\"posix\", \"macos\"))\n",
     "matches": 1},
    {"why": "REG-2357 - a proof caught only by off-POSIX cases is never said, so the next one ships BLIND on Windows",
     "file": "heart2.py",
     "find": "        if not got or not all(i in got[0] for i in ids):  # POSIX-ONLY-CATCH\n",
     "replace": "        if True:  # POSIX-ONLY-CATCH\n",
     "matches": 1},
    # REG-2359 (the round-3 review) - the node rule read only skip COUNTS: each skip must be for what this PC lacks
    {"why": "REG-2359 - the skips are never asked: a law that skipped for want of his D2R install is excused by node's "
            "absence",
     "file": "heart2.py",
     "find": "            _want = _skipped_for_want(tail2, _skips, (_posix_only_of(sandbox, filename) or (frozenset(),))[0],\n",
     "replace": "            _want = ([(\"\", \"node\")], []) or _skipped_for_want(tail2, _skips, (_posix_only_of(sandbox, filename) or (frozenset(),))[0],\n",
     "matches": 1},
    {"why": "REG-2359 - the gate's POSIX-only cases are never read, so a law like T5's reader-cap law files BLIND on Dean's "
            "PC again",
     "file": "heart2.py",
     "find": "            _want = _skipped_for_want(tail2, _skips, (_posix_only_of(sandbox, filename) or (frozenset(),))[0],\n",
     "replace": "            _want = _skipped_for_want(tail2, _skips, frozenset(),\n",
     "matches": 1},
    {"why": "REG-2359 - this PC is never asked whether it is POSIX, so a POSIX-only skip is never excused on Windows",
     "file": "heart2.py",
     "find": "                                      host_lacks(\"posix\")[0] is True)  # REG-2359 - the skips are node's\n",
     "replace": "                                      False)  # REG-2359 - the skips are node's\n",
     "matches": 1},
    {"why": "REG-2359 - a run is excused on the skips the watch happened to see, not every skip it reported",
     "file": "heart2.py",
     "find": "    if not _sk or int(_sk.group(1)) != len(skips):  # SKIPS-ALL-SEEN\n",
     "replace": "    if not _sk:  # SKIPS-ALL-SEEN\n",
     "matches": 1},
    {"why": "REG-2359 - one skip for another reason rides along with node's and the run is excused",
     "file": "heart2.py",
     "find": "    if not node or len(node) + len(posix) != len(skips):  # SKIPS-ALL-WANTED\n",
     "replace": "    if not node:  # SKIPS-ALL-WANTED\n",
     "matches": 1},
    {"why": "REG-2359 - a run with no skip for node at all is excused for want of node",
     "file": "heart2.py",
     "find": "    if not node or len(node) + len(posix) != len(skips):  # SKIPS-ALL-WANTED\n",
     "replace": "    if len(node) + len(posix) != len(skips):  # SKIPS-ALL-WANTED\n",
     "matches": 1},
    {"why": "REG-2359 - a POSIX-only case that skipped on a POSIX PC is excused as if POSIX were missing",
     "file": "heart2.py",
     "find": "    posix = [s for s in skips if s not in node and posix_gone and _case_key(s[0]) in off_posix]  # SKIP-OFF-POSIX-CASE\n",
     "replace": "    posix = [s for s in skips if s not in node and _case_key(s[0]) in off_posix]  # SKIP-OFF-POSIX-CASE\n",
     "matches": 1},
    {"why": "REG-2359 - any skip on a PC without POSIX is excused as POSIX's, POSIX-only case or not",
     "file": "heart2.py",
     "find": "    posix = [s for s in skips if s not in node and posix_gone and _case_key(s[0]) in off_posix]  # SKIP-OFF-POSIX-CASE\n",
     "replace": "    posix = [s for s in skips if s not in node and posix_gone]  # SKIP-OFF-POSIX-CASE\n",
     "matches": 1},
    {"why": "REG-2359 - unittest's case id is never matched to the source's (`__main__.P.test_p` vs `P.test_p`)",
     "file": "heart2.py",
     "find": "    return \".\".join(parts[-2:]) if len(parts) >= 2 else str(case or \"\")\n",
     "replace": "    return str(case or \"\")\n",
     "matches": 1},
    {"why": "REG-2359 - heart2 never arms the skip watch, so no run can say why its cases skipped",
     "file": "heart2.py",
     "find": "    env[\"TV_GATE_SKIPS\"] = \"1\"                # REG-2359 - and the run's own process writes the reason of every skip\n",
     "replace": "    env[\"TV_GATE_SKIPS_OFF\"] = \"1\"            # REG-2359 - and the run's own process writes the reason of every skip\n",
     "matches": 1},
    {"why": "REG-2359 - the skip watch's lines are never read back from the run",
     "file": "heart2.py",
     "find": "        _LAST_SKIPS[threading.get_ident()] = _skips_in(_watch) if _watch else None   # REG-2359 - why each case skipped\n",
     "replace": "        _LAST_SKIPS[threading.get_ident()] = None   # REG-2359 - why each case skipped\n",
     "matches": 1},
    {"why": "REG-2359 - the hook records no skip at all",
     "file": "gate_trace/sitecustomize.py",
     "find": "                emit(\"O\", \"case=%s reason=%s\" % (case, \" \".join(str(reason).split())[:300]))  # SKIP-WATCH-SAID\n",
     "replace": "                pass  # SKIP-WATCH-SAID\n",
     "matches": 1},
    {"why": "REG-2359 - the hook never says WHICH case skipped, so a POSIX-only case can never be told from any other",
     "file": "gate_trace/sitecustomize.py",
     "find": "                case = \"\".join(str(test.id() if hasattr(test, \"id\") else test).split())[:200] or \"-\"\n",
     "replace": "                case = \"-\"\n",
     "matches": 1},
    {"why": "REG-2359 - the hook never wraps unittest's skip, so a verbosity-1 law's reasons are never seen",
     "file": "gate_trace/sitecustomize.py",
     "find": "                    watch_skips()  # SKIP-WATCH-ARM\n",
     "replace": "                    pass  # SKIP-WATCH-ARM\n",
     "matches": 1},
    {"why": "REG-2359 - a child of the run inherits the skip watch: a fixture suite's skips are counted as the law's own",
     "file": "gate_trace/sitecustomize.py",
     "find": "    skips = os.environ.pop(\"TV_GATE_SKIPS\", None) == \"1\"  # SKIP-WATCH-OWN\n",
     "replace": "    skips = os.environ.get(\"TV_GATE_SKIPS\", None) == \"1\"  # SKIP-WATCH-OWN\n",
     "matches": 1},
    {"why": "REG-2359 - the ELSEWHERE line claims both runs' skip reasons were read, when only the tampered run's are",
     "file": "heart2.py",
     "find": "the skip watch read the tampered run's %d skip \"\n",
     "replace": "every case skipped in BOTH runs, each for what this PC lacks: %d skip \"\n",
     "matches": 1},
    {"why": "REG-2359 - the ELSEWHERE line drops the clean run's own count, so its 'both runs' is a claim, not a reading",
     "file": "heart2.py",
     "find": "                % (label, ELSEWHERE, _skip_count(tail, \"clean\"), _skip_count(tail2, \"tampered\"),\n",
     "replace": "                % (label, ELSEWHERE, \"\", _skip_count(tail2, \"tampered\"),\n",
     "matches": 1},
    {"why": "REG-2357 - a source the reader cannot parse raises inside _prove_one, and the proof is recorded BLIND",
     "file": "heart2.py",
     "find": "            except Exception:  # POSIX-READER-NEVER-RAISES: a source too deep to parse refuses and excuses nothing\n",
     "replace": "            except ZeroDivisionError:  # POSIX-READER-NEVER-RAISES: a source too deep to parse refuses and excuses nothing\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
