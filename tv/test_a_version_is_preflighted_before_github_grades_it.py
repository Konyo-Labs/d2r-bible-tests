# -*- coding: utf-8 -*-
"""v3865 (his ask 2026-11-05: "we need to integrate or implement something for this not to re-run another 40 minutes
everytime") - A VERSION IS PRE-FLIGHTED ON THIS PC BEFORE GITHUB GRADES IT.

Measured that day: every GitHub round costs ~40-60 min and a red one costs a second round; v3864's first run came back
with 16 reds, 14 of its 17 agent-suite reds in laws that cost <= 20 s on CI, and its second run with 9 BLIND proofs that a
local prove reproduced in minutes. tv/preflight.py runs every cheap NON-BROWSER law, proves the laws changed since GitHub
last graded the version, and runs the hook's anchor census; ship_when_green refuses the ci push on a red
(test_a_push_trusts_github_only_for_the_exact_commit holds that half). This law holds the pre-flight itself:
  * a law that drives a browser - in its own file or a test module it imports - is never run here (his rule: browser
    suites run on GitHub only), and a law over the cost cap is GitHub's; neither is counted as passed;
  * any red - a law, an anchor, an owed proof - makes the pre-flight red; an unreadable cost table is UNKNOWN, never green;
  * the changed laws are measured from what GitHub last graded for the version, and past PROVE_MAX they are GitHub's.
Fixtures only (temp dirs, fake runners). RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import preflight as PF  # noqa: E402


def _w(d, name, body):
    with io.open(os.path.join(d, name + ".py"), "w", encoding="utf-8") as fh:
        fh.write(body)


# v3881 (REG-3384) - the pre-flight's console-demos step is its own law's subject (test_the_preflight_runs_the_console_demos_the_main_push_would); here it is held out like the laws and the proofs
_NO_DEMOS = lambda: (False, "not under test here")  # noqa: E731
_NO_EYE_OWED = lambda: ("same", "v3883 - this law is not about the second eye (its own law drives that step)")


class ItChoosesWhatThisPCMayRun(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="preflight-law-")
        _w(self.d, "test_cheap", "import unittest\n")
        _w(self.d, "test_slow", "import unittest\n")
        _w(self.d, "test_harness_board", "def board():\n    return H.Board().open()\n")
        _w(self.d, "test_rides_a_board", "import test_harness_board as T\nT.board()\n")          # the browser one import away
        _w(self.d, "test_two_deep", "import test_rides_a_board as R\n")                          # and two
        _w(self.d, "launcher", "ARGS = ['--remote-debugging-port=9224']\n")
        _w(self.d, "test_imports_launch_code", "import launcher\n")                              # containing is not calling
        self.costs = {"test_cheap": 1.0, "test_slow": 45.0, "test_harness_board": 2.0, "test_rides_a_board": 1.0,
                      "test_two_deep": 1.0, "test_imports_launch_code": 1.0, "swallow_ratchet": 3.0}

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_browser_laws_and_slow_laws_are_githubs(self):
        s = PF.select(self.costs, self.d, cap_s=20, _registry={})
        self.assertEqual(s["run"], ["test_cheap", "test_imports_launch_code"], s)
        self.assertEqual(s["browser"], ["test_harness_board", "test_rides_a_board", "test_two_deep"], s)
        self.assertEqual(s["slow"], ["test_slow"], s)
        self.assertEqual(s["other"], ["swallow_ratchet"], s)
        placed = sorted(sum((v for k, v in s.items() if k != "argv"), []))
        self.assertEqual(placed, sorted(self.costs), "a gate was dropped or counted twice")

    def test_a_registered_gate_whose_name_is_not_its_file_runs_by_its_command(self):
        """v3866 (GitHub's first v3865 round) - test_no_pinned_footage and swallow_ratchet were 'other' and never ran
        here: two of that round's six reds came through. A registered python gate runs by its argv; one whose script
        drives a browser is still GitHub's; one the registry does not hold stays 'other', counted."""
        _w(self.d, "swallow_census", "print('ok')\n")
        costs = dict(self.costs, render_gate=2.0, node_gate=1.0)
        reg = {"swallow_ratchet": (["python3", os.path.join(self.d, "swallow_census.py"), "--check"], None, ()),
               "render_gate": (["python3", os.path.join(self.d, "test_harness_board.py")], None, ())}
        s = PF.select(costs, self.d, cap_s=20, _registry=reg)
        self.assertIn("swallow_ratchet", s["run"], s)
        self.assertEqual(s["argv"]["swallow_ratchet"][0][1:], [os.path.join(self.d, "swallow_census.py"), "--check"])
        self.assertIn("render_gate", s["browser"], "a registered gate whose script drives a browser ran here")
        self.assertEqual(s["other"], ["node_gate"], s)
        placed = sorted(sum((v for k, v in s.items() if k != "argv"), []))
        self.assertEqual(placed, sorted(costs), "a gate was dropped or counted twice")

    def test_a_law_that_opens_the_render_harness_is_a_browser_law(self):
        """REG-3310 - RC._Tab(...) and _chrome_up() start render_check's headless Chrome, and BROWSER_CALLS named neither:
        15 laws that open it ran in every pre-flight on his Mac since v3865 (measured: the v3875 pre-flight's
        test_a_roster_name_opens_its_row_with_the_eyes was the parent of a --remote-debugging-port Chrome)."""
        _w(self.d, "test_opens_a_tab", "import render_check as RC\nt = RC._Tab('about:blank')\n")
        _w(self.d, "test_starts_chrome", "import render_check as R\nR._chrome_up()\n")
        _w(self.d, "test_rides_the_tab", "import test_opens_a_tab\n")
        for n in ("test_opens_a_tab", "test_starts_chrome", "test_rides_the_tab"):
            self.assertTrue(PF.drives_browser(n, self.d), "%s opens the render harness's Chrome and would run on his Mac" % n)
        self.assertFalse(PF.drives_browser("test_cheap", self.d), "premise: a plain law is not a browser law")

    def test_a_slow_law_runs_here_after_the_fast_ones(self):
        """REG-3308 (v3875's GitHub round) - test_a_source_window_must_reach_its_subject costs 44 s on CI, so it was
        GitHub's, went red there, and cost a round this PC finds in under a minute. A slow law that drives no browser runs
        here after the fast ones; a slow browser law stays GitHub's."""
        _w(self.d, "test_slow_harness", "def board():\n    return H.Board().open()\n")
        costs = {"test_cheap": 1.0, "test_slow": 45.0, "test_slow_harness": 60.0}
        with io.open(os.path.join(self.d, "gate_costs.json"), "w", encoding="utf-8") as fh:
            json.dump(costs, fh)
        seen, said = [], []
        code, _r = PF.preflight(here=self.d, _demos_due=_NO_DEMOS, _render_due=_NO_DEMOS, _second_eye=_NO_EYE_OWED, say=said.append, _laws=lambda n: (seen.extend(n) or []),
                                _prove=lambda: ([], [], None), _anchors=lambda: (True, ""), _registry={})
        self.assertEqual(seen, ["test_cheap", "test_slow"], "the slow law was left to GitHub, or ran before the fast ones")
        self.assertNotIn("test_slow_harness", seen, "a slow BROWSER law ran on his Mac")
        self.assertTrue(any("1 slower - run here too" in l for l in said), said)

    def test_a_registered_law_the_cost_table_never_measured_runs_here(self):
        """REG-3299 (v3875's GitHub round) - the population was tv/gate_costs.json, which lags the registry: 36 registered
        gates were never run here and the pre-flight still said GREEN; test_every_picture_the_console_asks_for_is_shipped
        was one, red on this PC in 4 s, and GitHub spent a round on it. An uncosted registered law runs here; one whose
        script drives a browser stays GitHub's."""
        _w(self.d, "test_new_law", "import unittest\n")
        reg = {"test_new_law": (["python3", os.path.join(self.d, "test_new_law.py")], None, ()),
               "test_cheap": (["python3", os.path.join(self.d, "test_cheap.py")], None, ()),
               "new_browser_gate": (["python3", os.path.join(self.d, "test_harness_board.py")], None, ())}
        run, argv, browser = PF.uncosted(self.costs, self.d, _registry=reg)
        self.assertEqual(run, ["test_new_law"], "a law the cost table already places was added twice, or the new one dropped")
        self.assertEqual(argv["test_new_law"][0][1], os.path.join(self.d, "test_new_law.py"))
        self.assertEqual(browser, ["new_browser_gate"], "an uncosted browser gate would run on his Mac")
        with io.open(os.path.join(self.d, "gate_costs.json"), "w", encoding="utf-8") as fh:
            json.dump({"test_cheap": 1.0}, fh)
        seen, said = [], []
        code, _r = PF.preflight(here=self.d, _demos_due=_NO_DEMOS, _render_due=_NO_DEMOS, _second_eye=_NO_EYE_OWED, say=said.append, _laws=lambda n: (seen.extend(n) or []),
                                _prove=lambda: ([], [], None), _anchors=lambda: (True, ""), _registry=reg)
        self.assertIn("test_new_law", seen, "the pre-flight never ran a registered law the cost table has not measured")
        self.assertNotIn("new_browser_gate", seen)
        self.assertTrue(any("no measured CI cost" in l for l in said), said)

    def test_a_declared_skip_is_said_never_a_pass_or_a_red(self):
        _w(self.d, "skipper", "import sys\nprint('SKIPPED - no human-eyes ledger on this venue')\nsys.exit(1)\n")
        _w(self.d, "breaker", "import sys\nprint('it broke')\nsys.exit(1)\n")
        sk = (["python3", os.path.join(self.d, "skipper.py")], self.d, ("no human-eyes ledger",))
        br = (["python3", os.path.join(self.d, "breaker.py")], self.d, ("no human-eyes ledger",))
        self.assertEqual(PF.run_one("human-eyes", self.d, dict(os.environ), argv=sk)[1], "skip")
        self.assertEqual(PF.run_one("breaker", self.d, dict(os.environ), argv=br)[1], "red",
                         "a failure that is not the declared skip read as one")

    def test_an_unreadable_cost_table_is_unknown(self):
        p = os.path.join(self.d, "gate_costs.json")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        self.assertIsNone(PF.read_costs(p))
        code, _r = PF.preflight(here=self.d, _demos_due=_NO_DEMOS, _render_due=_NO_DEMOS, _second_eye=_NO_EYE_OWED, say=lambda *_: None, _laws=lambda n: [], _prove=lambda: ([], [], None),
                                _anchors=lambda: (True, ""))
        self.assertEqual(code, 2, "a pre-flight that chose nothing said green")


class AnyRedStopsIt(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="preflight-law-")
        _w(self.d, "test_a", "x = 1\n")
        _w(self.d, "test_b", "x = 1\n")
        with io.open(os.path.join(self.d, "gate_costs.json"), "w", encoding="utf-8") as fh:
            json.dump({"test_a": 1.0, "test_b": 2.0}, fh)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _pf(self, laws=None, owed=(), anchors_ok=True, why=None):
        seen = []

        def _laws(names):
            seen.extend(names)
            return [(n, (laws or {}).get(n, "ok"), "tail of %s" % n) for n in names]
        code, reds = PF.preflight(here=self.d, _demos_due=_NO_DEMOS, _render_due=_NO_DEMOS, _second_eye=_NO_EYE_OWED, say=lambda *_: None, _laws=_laws,
                                  _prove=lambda: (list(owed), ["test_a"], why), _anchors=lambda: (anchors_ok, "anchor tail"))
        return code, reds, seen

    def test_green_only_when_everything_is(self):
        code, reds, seen = self._pf()
        self.assertEqual((code, reds), (0, []))
        self.assertEqual(seen, ["test_a", "test_b"], "PREMISE: the chosen laws were not the ones run")

    def test_a_red_law_an_anchor_or_an_owed_proof_is_red(self):
        for kw, word in (({"laws": {"test_b": "red"}}, "RED test_b"), ({"laws": {"test_a": "time"}}, "TIME test_a"),
                         ({"anchors_ok": False}, "red-proof anchors"),
                         ({"owed": ["test_a[2]  BLIND - stayed GREEN"]}, "BLIND")):
            with self.subTest(**{k: str(v) for k, v in kw.items()}):
                code, reds, _ = self._pf(**kw)
                self.assertEqual(code, 1, reds)
                self.assertTrue(any(word in r for r in reds), reds)

    def test_unproved_changed_laws_are_unknown_never_green(self):
        code, reds, _ = self._pf(why="neither ci branch nor origin/main resolves")
        self.assertEqual(code, 2, "changed laws nobody proved read as a clean pre-flight")


class TheChangedLawsAreMeasuredFromWhatGitHubLastGraded(unittest.TestCase):

    def _git(self, have):
        def g(*args):
            if args[0] == "rev-parse":
                return (args[-1] in have), (args[-1] if args[-1] in have else "")
            if args[0] == "merge-base":
                return True, ""
            if args[0] == "diff":
                return True, "tv/test_x.py\nbible.html\n"
            return False, ""
        return g

    def test_the_base_is_the_versions_last_graded_head_else_main(self):
        self.assertEqual(PF.prove_base("v3865", self._git({"origin/ci/claude-v3865", "origin/main"})), "origin/ci/claude-v3865")
        self.assertEqual(PF.prove_base("v3865", self._git({"origin/main"})), "origin/main")
        self.assertIsNone(PF.prove_base("v3865", self._git(set())))

    def test_past_the_budget_the_proving_is_githubs_and_said(self):
        said, ran = [], []
        owed, names, why = PF.prove_changed("v3865", here=tempfile.gettempdir(), prove_max=3, say=said.append,
                                            _git_=self._git({"origin/main"}), _gates=lambda ch: ["test_p%d" % i for i in range(5)],
                                            _run=lambda *a, **k: ran.append(a) or subprocess.CompletedProcess(a, 0, "", ""))
        self.assertEqual((owed, names, why, ran), ([], [], None, []), "over the budget it proved here anyway")
        self.assertTrue(any("GitHub proves them" in l for l in said), said)
        owed, names, why = PF.prove_changed("v3865", here=tempfile.gettempdir(), prove_max=10, say=said.append,
                                            _git_=self._git({"origin/main"}), _gates=lambda ch: ["test_p1", "test_p2"],
                                            _run=lambda *a, **k: subprocess.CompletedProcess(
                                                a, 1, "     test_p2[0]   BLIND <- stayed GREEN\n", ""))
        self.assertEqual(names, ["test_p1", "test_p2"])
        self.assertEqual(len(owed), 1, "a BLIND proof was not owed: %r" % owed)


class NoPreflightStillRunsTheVersionLaws(unittest.TestCase):
    """v3887 (REG-3472) - v3886 fixed the pre-flight's reds in a commit that also rewrote its history list, shipped with
    --no-preflight, and GitHub's agent suite went red after 32 minutes: three lines over test_the_bump_carries_its_changelog_
    entry's 120 characters, a law that runs here in seconds. The version-wide laws read every commit of the version, so the
    explicit skip skips everything else and never them."""

    def _vc(self, laws=None, anchors_ok=True):
        seen = []

        def _laws(names):
            seen.extend(names)
            return [(n, (laws or {}).get(n, "ok"), "tail of %s" % n) for n in names]
        code, reds = PF.version_check(say=lambda *_: None, _laws=_laws, _anchors=lambda: (anchors_ok, "anchor tail"))
        return code, reds, seen

    def test_the_version_laws_are_real_registered_laws(self):
        import run_gates as RG
        names = set(getattr(g, "name", None) or (g[0] if isinstance(g, (list, tuple)) else g.get("name")) for g in RG.GATES)
        for n in PF.VERSION_LAWS:
            self.assertTrue(os.path.isfile(os.path.join(HERE, n + ".py")), "PREMISE: %s is not a law on disk" % n)
            self.assertIn(n, names, "%s is not a registered gate - GitHub never runs it, so it guards nothing" % n)
        self.assertIn("test_the_bump_carries_its_changelog_entry", PF.VERSION_LAWS, "the law v3886 lost a round to is not run")

    def test_green_only_when_both_laws_and_the_census_are(self):
        code, reds, seen = self._vc()
        self.assertEqual((code, reds), (0, []))
        self.assertEqual(seen, PF.VERSION_LAWS, "PREMISE: the version laws were not the ones run")
        for kw, want in (({"laws": {"test_the_bump_carries_its_changelog_entry": "red"}}, 1), ({"anchors_ok": False}, 1),
                         ({"laws": {"test_every_ship_lists_all_its_items": "time"}}, 2)):
            with self.subTest(**{k: str(v) for k, v in kw.items()}):
                self.assertEqual(self._vc(**kw)[0], want, "a red or a timed-out version law did not stop the ship")

    def test_a_law_with_no_verdict_is_named_beside_a_red(self):
        """v3888 (REG-3488, the second eye on v3887, reproduced) - a red returned at once and the timed-out law beside it
        was neither said nor listed: the ship still refused, and the message read as if that law had passed"""
        said = []

        def _laws(names):
            return [(n, {"test_the_bump_carries_its_changelog_entry": "red", "test_every_ship_lists_all_its_items": "time"}
                     .get(n, "ok"), "tail of %s" % n) for n in names]
        code, reds = PF.version_check(say=said.append, _laws=_laws, _anchors=lambda: (True, ""))
        self.assertEqual(code, 1, "a red version law did not stop the ship")
        self.assertIn("UNKNOWN TIME test_every_ship_lists_all_its_items", " ".join(reds), "the timed-out law left the red lines")
        self.assertIn("also UNKNOWN (no verdict): TIME test_every_ship_lists_all_its_items", " ".join(said),
                      "the message hides the law that did not reach a verdict")

    def _ship(self, vcode, preflight=False):
        import ship_when_green as SW
        sha, calls, asked = "a" * 40, [], []

        def run(argv, **kw):
            calls.append(list(argv))
            if argv[:3] == ["git", "rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, sha + "\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")
        rc = SW.ship("v3887", run=run, fetch=lambda s: [], sleep=lambda s: None, clock=lambda: 0.0, say=lambda *_: None,
                     wait_s=0, preflight=preflight, version_check=lambda v, say: (asked.append(v), vcode)[1])
        return rc, [c for c in calls if "push" in c], asked

    def test_the_explicit_skip_still_asks_the_version_laws_and_a_red_pushes_nothing(self):
        """* THE POINT"""
        rc, pushes, asked = self._ship(1)
        self.assertEqual(asked, ["v3887"], "--no-preflight shipped without asking the version-wide laws")
        self.assertEqual((rc, pushes), (1, []), "a red version law still sent the ci branches to GitHub")
        rc, pushes, asked = self._ship(2)
        self.assertEqual((rc, pushes), (2, []), "an UNKNOWN version law read as green")
        rc, pushes, asked = self._ship(0)
        self.assertTrue(pushes, "PREMISE: a green version check never reached the ci push - the case cannot see the stop")

    def test_the_full_preflight_is_not_doubled(self):
        rc, pushes, asked = self._ship(0, preflight=lambda v, say: 0)
        self.assertEqual(asked, [], "the full pre-flight ran and the version laws ran again beside it")


RED_PROOF = [
    {"why": "v3888 (REG-3488) - a timed-out version law beside a red is dropped from the message again",
     "file": "tv/preflight.py",
     "find": "        _un = (\"; also UNKNOWN (no verdict): %s\" % \", \".join(unknown)) if unknown else \"\"\n",
     "replace": "        _un = \"\"\n",
     "matches": 1},
    {"why": "v3887 (REG-3472) - --no-preflight skips the version-wide laws again (v3886 lost a GitHub round to a 120-char line)",
     "file": "tv/ship_when_green.py",
     "find": "        vcode = (version_check or _version_check)(version, say)\n",
     "replace": "        vcode = 0\n",
     "matches": 1},
    {"why": "v3887 (REG-3472) - a broken red-proof anchor no longer stops a --no-preflight ship",
     "file": "tv/preflight.py",
     "find": "    reds, unknown = ([] if a_ok else [\"red-proof anchors: \" + a_tail.replace(\"\\n\", \" | \")[:300]]), []\n",
     "replace": "    reds, unknown = [], []\n",
     "matches": 1},
    {"why": "v3887 (REG-3472) - a red version law reads as UNKNOWN-and-stop rather than RED (the ship says the wrong word)",
     "file": "tv/preflight.py",
     "find": "        if v == \"red\":\n            reds.append(\"RED %s: %s\" % (n, tail.replace(\"\\n\", \" | \")[:300]))\n",
     "replace": "        if False:\n            pass\n",
     "matches": 1},
    {"why": "REG-3310 - a law that opens the render harness's Chrome (RC._Tab, _chrome_up) runs on his Mac again",
     "file": "tv/preflight.py",
     "find": "                               r\"|launch_chrome|\\b_Tab\\(|\\b_chrome_up\\(|\\b(?:RC|rc|R|render_check)\\.check\\(\")",
     "replace": "                               r\"|launch_chrome|\\bTab_never_named\\(\")",
     "matches": 1},
    {"why": "REG-3308 - the laws over the cap are GitHub's again, and a 44-second law costs a round",
     "file": "tv/preflight.py",
     "find": "    s[\"run\"] = s[\"run\"] + list(s[\"slow\"])\n",
     "replace": "    s[\"run\"] = s[\"run\"]\n",
     "matches": 1},
    {'why': 'REG-3299 - a registered law the cost table never measured is never run here again',
     'file': 'tv/preflight.py',
     'find': '    s["run"] = s["run"] + un_run\n',
     'replace': '    s["run"] = s["run"]\n',
     'matches': 1},
    {"why": "v3866 - a registered gate whose name is not its file's is never run here again (94 gates, two reds slipped)",
     "file": "tv/preflight.py",
     "find": "            hit = reg.get(g)\n",
     "replace": "            hit = None\n",
     "matches": 1},
    {"why": "v3866 - a skip a gate declares reads as a red (or a pass) here",
     "file": "tv/preflight.py",
     "find": "    if r.returncode != 0 and any(re.search(p, tail, re.I) for p in skip_ok):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3865 - a law that drives a browser one import away is run on his PC",
     "file": "tv/preflight.py",
     "find": "        if drives_browser(m, here, depth - 1, seen):\n            return True\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "v3865 - a law over the cost cap is run here (the pre-flight grows to the hour it exists to save)",
     "file": "tv/preflight.py",
     "find": "        elif costs[g] > cap_s:\n",
     "replace": "        elif False:\n",
     "matches": 1},
    {"why": "v3865 - a red law is not a red pre-flight",
     "file": "tv/preflight.py",
     "find": "            elif v != \"ok\":\n                reds.append(",
     "replace": "            elif False:\n                reds.append(",
     "matches": 1},
    {"why": "v3865 - a broken anchor is not a red pre-flight",
     "file": "tv/preflight.py",
     "find": "    if not a_ok:\n        reds.append(",
     "replace": "    if False:\n        reds.append(",
     "matches": 1},
    {"why": "v3865 - an owed BLIND proof is not red",
     "file": "tv/preflight.py",
     "find": "        reds += owed\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "v3865 - an unreadable cost table reads as a green pre-flight",
     "file": "tv/preflight.py",
     "find": "        return 2, []\n    s = select(",
     "replace": "        return 0, []\n    s = select(",
     "matches": 1},
    {"why": "v3865 - over the proving budget it proves here anyway",
     "file": "tv/preflight.py",
     "find": "    if len(names) > prove_max:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3865 - a re-push measures its changed laws from main, not from what GitHub last graded (the whole version again)",
     "file": "tv/preflight.py",
     "find": "    refs = ([\"origin/ci/claude-%s\" % version] if version else []) + [\"origin/main\"]\n",
     "replace": "    refs = [\"origin/main\"]\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
