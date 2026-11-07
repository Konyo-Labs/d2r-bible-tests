#!/usr/bin/env python3
"""#103-C - A PC THAT PROVES ITSELF TAKES THE LAWS THAT KEEP A LOCK SHUT FIRST, AND SAYS SO.

His question, 11-07 ~01:45 IST: "if the river proves itself already why does every proof going forward not related to it
need to continue proofing it over and over again for it to unlock?". MEASURED on the ALT 11-07 ~09:50 IST (v3876): the
vault autoread loop FLOWING every 45 s and vault.sweep_start OPEN-not-permitted for ~42 h - "26 of its own guard law(s)
changed or are unproven" - while the self-prove lane worked 71 owed laws cheapest-first, so the sweep lock's guards waited
behind laws that guard nothing, and his ALT's vault ledger stayed empty (#47).

A lock that answers per lock (#156, self_arming.LOCK_DOORS) opens the moment ITS guards are proven, and only when the slice
holding them writes the census. So:
  * self_arming.owed_guard_rank ranks every owed law that guards a door lock - rank 0 = a guard of the lock that opens
    after the fewest proofs - through ONE guard rule shared with the per-lock answer (_lock_guard);
  * self_prove.plan_slice makes those guards a slice of their own (nothing else in it), the lock with the fewest owed
    guards first, cheapest first within it; a recorded BLIND still goes before all of it (REG-1673);
  * the tick ranks only a census it read itself (a census handed in is never ranked against this PC's real one) and
    says which locks the slice is for.

Everything runs on fixture gate files and fixture censuses; nothing reads or writes this machine's real census.
[[heart-first]] [[unknown-stays-unknown]] [[copy-drift]]
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402  #173 - its scratch is its own, so listing it keeps the law keyable
_fx_tmp.contain()

import self_arming as SA  # noqa: E402
import self_prove as SP  # noqa: E402


class _Memo(unittest.TestCase):
    """A clean per-lock memo per case: the memo is keyed by gate NAME, so a fixture must never meet another's sources."""

    def setUp(self):
        self._memo = dict(SA._LOCK_MEMO)
        SA._LOCK_MEMO.update(src={}, guard={})
        self.addCleanup(self._restore)
        self.d = tempfile.mkdtemp(prefix="lockfirst_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def _restore(self):
        SA._LOCK_MEMO.clear()
        SA._LOCK_MEMO.update(self._memo)

    def gate(self, name, text):
        p = os.path.join(self.d, name + ".py")
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def rank(self, owed, blind=(), files=None):
        with mock.patch.object(SA, "_owed_and_blind", lambda: (set(owed), set(blind), files or {})):
            return SA.owed_guard_rank()


class TheShutLocksGuardsAreRanked(_Memo):

    def files(self):
        # printer.stream's door is the printer module; reel.route's is reel_route_lane: two locks, 1 and 3 owed guards
        return {
            "p_one": self.gate("p_one", "import printer\n"),
            "r_one": self.gate("r_one", "import reel_route_lane\n"),
            "r_two": self.gate("r_two", "from reel_route_lane import x\n"),
            "r_three": self.gate("r_three", "# names the lock 'reel.route'\nLOCK = \"reel.route\"\n"),
            "nothing": self.gate("nothing", "import json\n"),
        }

    def test_the_lock_with_the_fewest_owed_guards_ranks_first(self):
        """* THE POINT: printer.stream opens after one proof, reel.route after three - printer's guard is rank 0"""
        f = self.files()
        r = self.rank(f.keys(), files=f)
        self.assertEqual(r["rank"].get("p_one"), 0, r)
        self.assertEqual({r["rank"].get(n) for n in ("r_one", "r_two", "r_three")}, {1}, r)
        self.assertEqual(r["locks"], [["printer.stream", 1], ["reel.route", 3]], r)

    def test_a_law_that_guards_no_door_lock_has_no_rank(self):
        f = self.files()
        r = self.rank(f.keys(), files=f)
        self.assertNotIn("nothing", r["rank"], "a law that guards no lock was ranked - proving it opens nothing")

    def test_a_law_guarding_two_locks_takes_the_sooner_one(self):
        f = self.files()
        f["both"] = self.gate("both", "import printer\nimport reel_route_lane\n")
        r = self.rank(f.keys(), files=f)
        self.assertEqual(r["locks"][0], ["printer.stream", 2], r)
        self.assertEqual(r["rank"]["both"], 0, "a guard of two locks was ranked by the later one: %s" % r)

    def test_a_recorded_blind_ranks_nothing(self):
        """REG-1673 - a BLIND shuts every lock and is proved first, alone - the rank never competes with it"""
        f = self.files()
        r = self.rank(f.keys(), blind=["nothing"], files=f)
        self.assertEqual(r["rank"], {}, "a census holding a BLIND was ranked: %s" % r)
        self.assertIn("BLIND", r["why"])

    def test_an_unreadable_census_ranks_nothing_and_says_why(self):
        with mock.patch.object(SA, "_owed_and_blind", lambda: (None, None, "no proof census on this PC")):
            r = SA.owed_guard_rank()
        self.assertEqual(r["rank"], {})
        self.assertIn("no proof census on this PC", r["why"])

    def test_an_unreadable_law_is_counted_a_guard(self):
        """broad in the safe direction, as the per-lock answer is: a law that will not read guards every door lock"""
        r = self.rank(["gone"], files={"gone": os.path.join(self.d, "missing.py")})
        self.assertEqual(r["rank"].get("gone"), 0, r)

    def test_the_rank_and_the_per_lock_answer_ask_one_guard_rule(self):
        """the per-lock answer and the rank name the SAME owed guards for a lock (one rule, [[copy-drift]])"""
        f = self.files()
        owed = set(f)
        with mock.patch.object(SA, "_owed_and_blind", lambda: (owed, set(), f)), \
                mock.patch.object(SA, "heart_block_kind", lambda why: "stale"):
            ok, why = SA._lock_heart("reel.route", gwhy="the heart2 PROOF census is STALE (fixture)")
            r = SA.owed_guard_rank()
        self.assertFalse(ok)
        self.assertIn("3 of its own guard law(s)", why)
        self.assertEqual(dict(r["locks"])["reel.route"], 3)

    def test_it_never_raises(self):
        def boom():
            raise RuntimeError("fixture")
        with mock.patch.object(SA, "_owed_and_blind", boom):
            r = SA.owed_guard_rank()
        self.assertEqual(r["rank"], {})
        self.assertIn("RuntimeError", r["why"])


class TheSliceTakesTheGuardsFirst(unittest.TestCase):

    OWED = [("cheap", 0), ("guard_b", 0), ("mid", 0), ("guard_a", 0), ("guard_c", 0)]
    COSTS = {"cheap": 1, "mid": 5, "guard_a": 40, "guard_b": 10, "guard_c": 2}

    def test_a_slice_of_guards_holds_nothing_else(self):
        """* THE POINT: a cheap law that guards nothing never rides in the guards' slice - it would hold their census"""
        got = SP.plan_slice(self.OWED, self.COSTS, budget_s=10 ** 6, first={"guard_a": 0, "guard_b": 0, "guard_c": 1})
        self.assertEqual(set(got), {"guard_a", "guard_b", "guard_c"}, got)

    def test_the_sooner_lock_goes_first_even_when_dearer(self):
        """rank before cost: guard_a and guard_b open the sooner lock, so they precede the cheaper guard_c"""
        got = SP.plan_slice(self.OWED, self.COSTS, budget_s=10 ** 6, first={"guard_a": 0, "guard_b": 0, "guard_c": 1})
        self.assertEqual(got, ["guard_b", "guard_a", "guard_c"], got)

    def test_the_budget_still_bounds_the_guards_slice(self):
        got = SP.plan_slice(self.OWED, self.COSTS, budget_s=51, first={"guard_a": 0, "guard_b": 0, "guard_c": 1})
        self.assertEqual(got, ["guard_b", "guard_a"], got)

    def test_a_recorded_blind_still_goes_first_and_alone(self):
        got = SP.plan_slice(self.OWED, self.COSTS, budget_s=10 ** 6, blind=["mid"], first={"guard_a": 0})
        self.assertEqual(got, ["mid"], "the guards' slice beat a recorded BLIND: %s" % got)

    def test_a_rank_naming_nothing_owed_keeps_the_old_order(self):
        got = SP.plan_slice(self.OWED, self.COSTS, budget_s=10 ** 6, first={"not_owed": 0})
        self.assertEqual(got, ["cheap", "guard_c", "mid", "guard_b", "guard_a"], got)
        self.assertEqual(SP.plan_slice(self.OWED, self.COSTS, budget_s=10 ** 6),
                         ["cheap", "guard_c", "mid", "guard_b", "guard_a"])


class TheTickRanksOnlyItsOwnCensus(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="lockfirst_lane_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.path = os.path.join(self.d, ".self_prove.json")
        self.spawned = []
        SP._STARTED.update(pid=None, birth=None)
        self.addCleanup(SP._STARTED.update, pid=None, birth=None)

    def _spawn(self, log_path, names=None):
        self.spawned.append(names)
        return 999_999_3

    def _census(self, owed):
        return {"state": "stale", "why": "fixture", "fingerprint": "fp1", "owed": len(owed),
                "owedGates": [(n, 1) for n in owed], "owedWhy": "fixture: %d owed" % len(owed)}

    def _tick(self, census, lock_rank=None):
        with mock.patch.object(SP, "_gate_costs", lambda path=None: {}):
            return SP.tick(now_s=1000.0, busy=3.0, tree=("installed", "a clean installed tree"), census=census,
                           path=self.path, spawn_fn=self._spawn, env={}, playing=False, free=8000, lock_rank=lock_rank)

    def test_the_tick_proves_the_shut_locks_guards_first_and_says_which(self):
        rank = lambda: {"rank": {"g3": 0}, "locks": [["vault.sweep_start", 1]], "why": "fixture"}  # noqa: E731
        r = self._tick(self._census(["g1", "g2", "g3"]), lock_rank=rank)
        self.assertEqual(r["key"], "start")
        self.assertEqual(self.spawned, [["g3"]], "the shut lock's guard was not proved first and alone: %s" % self.spawned)
        mem = json.load(io.open(self.path, encoding="utf-8"))
        self.assertIn("vault.sweep_start (1 owed guard(s))", mem.get("lockFirst") or "", mem)
        self.assertIn("the guards of the shut lock(s) first", mem.get("lastWhy") or "", mem)

    def test_a_census_handed_in_is_never_ranked_against_this_pcs(self):
        """a fixture census must not reach this PC's real census through the rank ([[fixtures-never-touch-live-data]])"""
        asked = []
        with mock.patch.object(SA, "owed_guard_rank", lambda: asked.append(1) or {"rank": {"g3": 0}, "locks": []}):
            self._tick(self._census(["g1", "g2", "g3"]))
        self.assertEqual(asked, [], "the tick ranked a handed-in census against the real one")
        self.assertEqual(self.spawned, [["g1", "g2", "g3"]], self.spawned)

    def test_a_rank_that_raises_keeps_the_old_order(self):
        def boom():
            raise RuntimeError("fixture")
        r = self._tick(self._census(["g1", "g2"]), lock_rank=boom)
        self.assertEqual(r["key"], "start")
        self.assertEqual(self.spawned, [["g1", "g2"]], self.spawned)


class TheSliceSaysWhichLocks(unittest.TestCase):

    def test_the_words_name_the_locks_the_slice_is_for(self):
        lf = {"rank": {"a": 0, "b": 1}, "locks": [["printer.stream", 1], ["reel.route", 3]]}
        w = SP.lock_first_words(["a", "b", "x"], lf)
        self.assertIn("printer.stream (1 owed guard(s))", w)
        self.assertIn("reel.route (3 owed guard(s))", w)
        self.assertIn("2 of this slice's 3 gate(s)", w)

    def test_a_slice_holding_no_guard_says_nothing(self):
        self.assertEqual(SP.lock_first_words(["x"], {"rank": {"a": 0}, "locks": [["printer.stream", 1]]}), "")
        self.assertEqual(SP.lock_first_words([], None), "")


RED_PROOF = [
    {
        "why": "#103-C - the guards' slice lets a cheap law that guards nothing ride in it, so the lock waits on it too",
        "file": "self_prove.py",
        "find": "            owed, rank = _guards, first\n",
        "replace": "            rank = first\n",
        "matches": 1,
    },
    {
        "why": "#103-C - the slice is ordered by cost alone: a cheap guard of a later lock goes before the sooner lock's",
        "file": "self_prove.py",
        "find": "key=lambda t: (rank.get(str(t[0]), 0), est(t), t[0])",
        "replace": "key=lambda t: (est(t), t[0])",
        "matches": 1,
    },
    {
        "why": "#103-C - the lock with the MOST owed guards ranks first: the lock that could open soonest waits longest",
        "file": "self_arming.py",
        "find": "        per.sort(key=lambda t: (t[0], t[1]))\n",
        "replace": "        per.sort(key=lambda t: (-t[0], t[1]))\n",
        "matches": 1,
    },
    {
        "why": "#103-C - a census holding a BLIND is ranked, so the guards' slice competes with the BLIND rule",
        "file": "self_arming.py",
        "find": "        if blind:\n            out[\"why\"] = \"the census records a BLIND - it is proved first, alone (REG-1673)\"\n",
        "replace": "        if False:\n            out[\"why\"] = \"the census records a BLIND - it is proved first, alone (REG-1673)\"\n",
        "matches": 1,
    },
    {
        "why": "#103-C - a law guarding two locks is ranked by the later one (the last write wins)",
        "file": "self_arming.py",
        "find": "                out[\"rank\"].setdefault(n, pos)\n",
        "replace": "                out[\"rank\"][n] = pos\n",
        "matches": 1,
    },
    {
        "why": "#103-C - the tick never hands the rank to the planner: the guards wait behind cheaper laws again",
        "file": "self_prove.py",
        "find": "blind=census.get(\"blind\"), first=_lf[\"rank\"])   # REG-1673",
        "replace": "blind=census.get(\"blind\"), first=None)   # REG-1673",
        "matches": 1,
    },
    {
        "why": "#103-C - a census handed in is ranked against this PC's real census (a fixture reaches live data)",
        "file": "self_prove.py",
        "find": "    _rank_here = lock_rank is not None or census is None",
        "replace": "    _rank_here = True",
        "matches": 1,
    },
    {
        "why": "#103-C - the lane no longer says which locks its slice is for",
        "file": "self_prove.py",
        "find": "            mem[\"lockFirst\"] = _for_locks\n",
        "replace": "            mem[\"lockFirst\"] = \"\"\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
