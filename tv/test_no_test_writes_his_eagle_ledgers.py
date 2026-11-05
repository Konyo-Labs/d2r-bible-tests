# -*- coding: utf-8 -*-
"""v3470 — no test process may write HIS eagle ledgers.

⚠⚠ WHAT IT COST: seven doctor suites drove console_doctor / unknown_age with fake checks and never
redirected TV_UNKNOWN_AGE / TV_EAGLE_SLOW, so every run appended 'exploder' (813), 'exploding check'
(803) and 'costly-one' to his live tv/.unknown_age.json and tv/.eagle_slow.json, and run_gates'
live-state watcher did not name either file, so CI filed it as "also touched" and moved on.
[[feedback-fixtures-never-touch-live-data]] — the guard goes on the FIXTURE.

Reads the gate files as AST (the compiler, never a regex over prose) and DRIVES the helper and the
real unknown_age writer against a temp path. RED_PROOF below.
"""
import ast
import glob
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

GATES = ["test_the_doctor_times_each_check.py", "test_the_screen_bills_the_same_rows_the_engine_does.py",
         "test_control.py", "test_board_tally_alarm.py", "test_a_periodic_check_is_still_watched_unattended.py",
         "test_health_engine.py", "test_a_skipped_periodic_check_still_emits_a_row.py",
         "test_bake_seed.py"]   # v3475 — drives bake(), which now writes a receipt
LIVE = (".unknown_age.json", ".eagle_slow.json")

#: REG-1257 — THE LIST ABOVE IS A MEMORY, AND MEMORY MISSED ONE. test_a_pass_says_which_check_it_is_in
#: (#229) drove a real console_doctor.run(), whose last step is unknown_age.attach(), and was never added
#: to GATES - CI on 6dab59f1 caught it writing .unknown_age.json. So the law now FINDS every suite that
#: calls a ledger writer, by the compiler: module aliases resolved from the imports, then the calls.
DRIVES = {"console_doctor": {"run", "_persist_slow"}, "unknown_age": {"attach"}}


def _drives_a_ledger(path):
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    alias = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name in DRIVES:
                    alias[a.asname or a.name] = a.name
    hits = set()
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id in alias
                and n.func.attr in DRIVES[alias[n.func.value.id]]):
            hits.add("%s.%s" % (alias[n.func.value.id], n.func.attr))
    return sorted(hits)


def _sets_the_ledger_itself(path):
    """A suite that points TV_UNKNOWN_AGE somewhere itself (a string CONSTANT in code, never prose)."""
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    return any(isinstance(n, ast.Constant) and n.value == "TV_UNKNOWN_AGE" for n in ast.walk(tree))


def _calls_redirect_at_module_level(path):
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    for node in tree.body:                      # MODULE level only — a call inside a def may never run
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            f = node.value.func
            if isinstance(f, ast.Attribute) and f.attr == "redirect":
                return True
    return False


class NoTestWritesHisEagleLedgers(unittest.TestCase):

    def test_every_suite_that_drives_the_doctor_redirects_at_import(self):
        missing = [g for g in GATES if not _calls_redirect_at_module_level(os.path.join(HERE, g))]
        self.assertEqual(missing, [], "these suites drive the doctor and never redirect his ledgers: %r"
                         % missing)

    def test_premise_the_finder_finds_every_known_driver(self):
        found = set(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "test_*.py")) if _drives_a_ledger(p))
        known = [g for g in GATES if g != "test_bake_seed.py"]      # bake() writes a receipt, not these ledgers
        self.assertEqual([g for g in known if g not in found], [],
                         "the finder misses suites known to drive the doctor - it would miss a new one too")

    def test_every_suite_that_drives_a_ledger_writer_redirects(self):
        bad = []
        for p in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
            hits = _drives_a_ledger(p)
            if hits and not (_calls_redirect_at_module_level(p) or _sets_the_ledger_itself(p)):
                bad.append("%s (%s)" % (os.path.basename(p), ", ".join(hits)))
        self.assertEqual(bad, [], "these suites call a ledger writer and never redirect his ledgers: %r" % bad)

    def test_the_helper_points_every_unset_ledger_outside_the_tree(self):
        import fixture_ledgers as FL
        saved = dict((v, os.environ.pop(v, None)) for v, _ in FL.VARS)
        try:
            got = FL.redirect()
            for var, path in got.items():
                self.assertFalse(os.path.abspath(path).startswith(os.path.abspath(HERE) + os.sep),
                                 "%s still points INTO tv/: %s" % (var, path))
        finally:
            for v, val in saved.items():
                if val is None:
                    os.environ.pop(v, None)
                else:
                    os.environ[v] = val

    def test_a_redirected_write_never_touches_the_live_file(self):
        import unknown_age as UA
        live = os.path.join(HERE, ".unknown_age.json")
        before = os.stat(live).st_mtime if os.path.exists(live) else None
        d = tempfile.mkdtemp(prefix="ua-law-")
        saved = os.environ.get("TV_UNKNOWN_AGE")
        try:
            os.environ["TV_UNKNOWN_AGE"] = os.path.join(d, "age.json")
            UA.attach([{"check": "a fixture check that must never reach him", "state": "unknown"}])
            self.assertTrue(os.path.exists(os.path.join(d, "age.json")),
                            "BASELINE: the redirected write did not happen, so nothing was measured")
        finally:
            if saved is None:
                os.environ.pop("TV_UNKNOWN_AGE", None)
            else:
                os.environ["TV_UNKNOWN_AGE"] = saved
            import shutil
            shutil.rmtree(d, ignore_errors=True)
        after = os.stat(live).st_mtime if os.path.exists(live) else None
        self.assertEqual(before, after, "a redirected write still moved his live ledger")

    def test_the_live_state_watcher_names_both_ledgers(self):
        import run_gates as RG
        for n in LIVE:
            self.assertIn(n, RG._LIVE_STATE, "run_gates would file a write to %s as 'also touched', "
                          "never as the suite writing his state" % n)


class EveryGateTheRunnerStartsHasItsOwnLedgers(unittest.TestCase):
    """v3864 (card 75) - v3864's first GitHub run created tv/.eagle_slow.json and tv/.unknown_age.json on shard 3 (live-state-
    untouched red), named against a gate that touches neither. run_gates.law_env now points each of the three ledgers at its own
    temp file for every gate, unless the caller set one - and a law that pops what it set (test_cf_handoff did) puts back the
    runner's, never nothing."""

    def test_a_gate_gets_temp_ledgers_and_a_callers_own_is_kept(self):
        import run_gates as RG
        env = RG.law_env(False, base={"PATH": os.environ.get("PATH", "")})
        for var, _stem in RG.LAW_LEDGERS:
            got = env.get(var)
            self.assertTrue(got, "a gate starts with %s unset - its writes land in his live tv/" % var)
            self.assertFalse(os.path.abspath(got).startswith(HERE + os.sep), "%s points into tv/: %r" % (var, got))
        other = RG.law_env(False, base={"PATH": os.environ.get("PATH", "")})
        self.assertNotEqual(env["TV_EAGLE_SLOW"], other["TV_EAGLE_SLOW"], "two gates share one temp ledger")
        mine = RG.law_env(False, base={"PATH": os.environ.get("PATH", ""), "TV_EAGLE_SLOW": "/fixture/slow.json"})
        self.assertEqual(mine["TV_EAGLE_SLOW"], "/fixture/slow.json", "the caller's own ledger was overridden")

    def test_a_law_puts_back_the_ledger_it_found(self):
        src = io.open(os.path.join(HERE, "test_cf_handoff.py"), encoding="utf-8").read()
        for var in ("TV_UNKNOWN_AGE", "TV_EAGLE_SLOW"):
            self.assertIn('        self._was = os.environ.get("%s")' % var, src, "test_cf_handoff no longer keeps the %s it found" % var)
            self.assertIn('            os.environ["%s"] = self._was\n' % var, src, "test_cf_handoff deletes the %s it found" % var)


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "v3864 (card 75) - a gate starts with no ledger redirect, so a law that forgets fixture_ledgers writes his live tv/",
     "file": "tv/run_gates.py",
     "find": "        if not env.get(_var):\n            env[_var] = _law_ledger_path(_stem)\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "v3864 (card 75) - test_cf_handoff pops the ledger it found, so every test after it in that process writes his live file",
     "file": "tv/test_cf_handoff.py",
     "find": "        if self._was is None:\n            os.environ.pop(\"TV_EAGLE_SLOW\", None)\n        else:\n            os.environ[\"TV_EAGLE_SLOW\"] = self._was\n",
     "replace": "        os.environ.pop(\"TV_EAGLE_SLOW\", None)\n",
     "matches": 1},
    {
        "why": "REG-1257 - the #229 pass law drives a real doctor pass unredirected again (CI caught it writing .unknown_age.json)",
        "file": "test_a_pass_says_which_check_it_is_in.py",
        "find": "_fx_ledgers.redirect()\n",
        "replace": "pass\n",
        "matches": 1,
    },
    {
        "why": "test_control stops redirecting: every pre-push appends fixture checks to his ledgers again",
        "file": "test_control.py",
        "find": "_fx_ledgers.redirect()\n",
        "replace": "pass\n",
        "matches": 1,
    },
    {
        "why": "the helper points nowhere new: a test process writes the tree's own ledger files",
        "file": "fixture_ledgers.py",
        "find": "            p = os.path.join(tempfile.gettempdir(), \"tvd_fixture_%s_%d.json\" % (stem, os.getpid()))\n",
        "replace": "            p = os.path.join(os.path.dirname(os.path.abspath(__file__)), \".%s.json\" % stem)\n",
        "matches": 1,
    },
    {
        "why": "the watcher forgets the ledger again: CI files a write to it as 'also touched'",
        "file": "run_gates.py",
        # v3475 — RE-ANCHORED (REG-1163, on my own proof): the receipt joined this line.
        "find": "               \".unknown_age.json\", \".eagle_slow.json\",\n",
        "replace": "               \".eagle_slow.json\",\n",
        "matches": 1,
    },
]
