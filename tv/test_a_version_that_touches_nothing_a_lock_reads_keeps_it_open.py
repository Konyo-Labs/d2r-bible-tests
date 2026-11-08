# -*- coding: utf-8 -*-
"""#103 item 3 (REG-3484) - A VERSION THAT TOUCHES NOTHING A LOCK READS KEEPS THAT LOCK OPEN.

His question, 11-07 ~01:45 IST: "if the river proves itself already why does every proof going forward not related to it
need to continue proofing it over and over again for it to unlock?" - and 11-08: "for fleet the river should be flowing
for all pcs". MEASURED 11-09 on main, v3878-v3886: whenever a version owed a lock anything, the same few BROAD laws held
all nine shut - test_control (486 classes), test_ledger_authority and the lock-machinery laws - because the whole file
imports the lock machinery, so any edit anywhere in one owed every lock on every PC until it was proven again there. Of
test_control's 486 classes 1-15 touch a river lock; over the five versions that changed it, the three river locks' own
part of it was byte-identical in four.

A law guarding NET_NARROW_MIN_LOCKS or more locks now keeps a lock shut only when THAT LOCK'S PART changed since the proof
this PC banked (self_arming.lock_index / lock_parts; heart2 banks `lockShas` beside `gateShas`): its module code, the
classes that touch the lock (by name, or through a door module imported under another name), the classes the red memory
saw catch the lock's sabotages, the red-proofs aimed at its code, and the lock's own door modules and machinery. A
focused law, a census with no part recorded and a console whose index child has not answered keep the whole-file rule.

Driven on fixture gates (heart2.gate_files patched) and a fixture census (TV_HEART_CENSUS), so his census is never read;
one case measures the premise on the real test_control. RED_PROOF below. [[heart-first]] [[the-unjoined-end]]
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
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import fixture_tmp as _fx  # noqa: E402
_fx.contain()
import heart2 as H  # noqa: E402
import self_arming as SA  # noqa: E402
import audit_child as AC  # noqa: E402

FRAME, PRINTER = "frame.release", "printer.stream"
BROAD_N, FOCUSED_N = "test_fx_broad_law", "test_fx_focused_law"

_BROAD = '''"""a fixture broad law: the whole file imports the lock machinery"""
import unittest
import self_arming as SA
import reel_retention as rr


def _helper():
    return %(helper)r


class Unrelated(unittest.TestCase):
    def test_x(self):
        self.assertEqual(%(unrelated)r, %(unrelated)r)
%(added_class)s

class FrameGuard(unittest.TestCase):
    def test_plan(self):
        self.assertTrue(rr.plan(%(frame)r))


class PrinterGuard(unittest.TestCase):
    def test_name(self):
        self.assertEqual("printer.stream".split(".")[0], %(printer)r)


class Catcher(unittest.TestCase):
    def test_c(self):
        self.assertEqual(%(catcher)r, %(catcher)r)


RED_PROOF = [
    {"why": "the river", "file": "tv/reel_retention.py", "find": %(red_find)r, "replace": "x", "matches": 1},
%(added_red)s]
'''
_ADDED_CLASS = '''

class AddedLater(unittest.TestCase):
    def test_new(self):
        self.assertEqual(1, 1)
'''
_ADDED_RED = '''    {"why": "a page", "file": "bible.html", "find": "a", "replace": "b", "matches": 1},
'''
_FOCUSED = '''"""a fixture focused law: the river's door alone"""
import unittest
import reel_retention as rr


class OnlyTheRiver(unittest.TestCase):
    def test_plan(self):
        self.assertTrue(rr.plan(%(frame)r))


RED_PROOF = [{"why": "the river", "file": "tv/reel_retention.py", "find": "def plan(", "replace": "x", "matches": 1}]
'''
#: a class the proved file had and the file on disk does not
_GONE = '''

class GoneNow(unittest.TestCase):
    def test_g(self):
        self.assertEqual(2, 2)
'''
#: the file on disk: everything as proved, plus a class and a red-proof that touch no lock
CURRENT = dict(helper="h1", unrelated="u1", frame="f1", printer="printer", catcher="c1", red_find="def plan(", added=True)


def _broad(**over):
    p = dict(CURRENT)
    p.update(over)
    q = dict(p, added_class=_ADDED_CLASS if p["added"] else "", added_red=_ADDED_RED if p["added"] else "")
    return _BROAD % q


class _Fixture(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="lock_part_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.files = {}
        self._put(BROAD_N, _broad())
        self._put(FOCUSED_N, _FOCUSED % {"frame": "f1"})
        self.census_path = os.path.join(self.d, ".heart2.json")
        gates = lambda say=print: sorted(self.files.items())
        for p in (mock.patch.object(H, "gate_files", gates), mock.patch.object(H, "STATE", self.census_path),
                  mock.patch.dict(os.environ, {"TV_HEART_CENSUS": self.census_path})):
            p.start()
            self.addCleanup(p.stop)
        SA._LOCK_MEMO.update(key=None)
        self.addCleanup(SA._LOCK_MEMO.update, key=None)

    def _put(self, name, text):
        f = os.path.join(self.d, name + ".py")
        with io.open(f, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.files[name] = f

    def census(self, proven=None, catchers=None, door=None, record=True, focused_proven=None, extra_rec=None):
        """Every fixture gate proven; the broad law proven against `proven` (its text then), so it is OWED now; the
        census stamped with a fingerprint the tree does not have, so the global rule reads STALE and each lock answers
        from its own guards (#156)."""
        proven = _broad() if proven is None else proven
        foc = focused_proven if focused_proven is not None else (_FOCUSED % {"frame": "f1"})
        shas = {BROAD_N: SA._sha16(proven), FOCUSED_N: SA._sha16(foc)}
        st = {"gatesFingerprint": "f" * 32, "gateShas": shas, "provedGates": sorted(self.files), "blind": [],
              "proved": 2, "declared": 2, "total": 2, "sliceOwed": 1}
        if record:
            st["lockShas"] = {BROAD_N: {"v": SA.LOCK_PART_VERSION, "sha": shas[BROAD_N],
                                        "locks": SA.lock_parts(SA.lock_index(proven), catchers, door=door)}}
        if extra_rec:
            st["lockShas"].update(extra_rec)
        with io.open(self.census_path, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        SA._LOCK_MEMO.update(key=None)

    def lock(self, lock):
        r = SA._lock_heart(lock)
        self.assertIsNotNone(r, "PREMISE: %s gave no per-lock answer (the global rule is not STALE?)" % lock)
        return r


class TheFixtureIsWhatItSays(_Fixture):

    def test_premise_one_broad_law_and_one_focused(self):
        broad = SA.lock_index(_broad())
        self.assertGreaterEqual(len(broad["all"]), SA.NET_NARROW_MIN_LOCKS, "PREMISE: the fixture law is not broad")
        self.assertEqual(SA.lock_index(_FOCUSED % {"frame": "f1"})["all"], [FRAME], "PREMISE: the focused law moved")
        cls = broad["cls"]
        self.assertEqual(cls["FrameGuard"][1], [FRAME], "an alias (rr.) did not make FrameGuard a guard of the river")
        self.assertEqual(cls["PrinterGuard"][1], [PRINTER])
        self.assertEqual(cls["Unrelated"][1], [], "a class that names no lock guards one")
        self.assertEqual(cls["Catcher"][1], [])

    def test_premise_the_broad_law_is_owed_and_the_global_rule_is_stale(self):
        self.census(proven=_broad(added=False))
        owed, _blind, _files = SA._owed_and_blind()
        self.assertEqual(owed, {BROAD_N}, "PREMISE: the fixture census owes %r" % (owed,))
        self.assertFalse(SA._heart_says_watched()[0], "PREMISE: the fixture census is not stale to the global rule")

    def test_premise_on_the_real_tree_a_river_lock_is_a_small_part_of_test_control(self):
        """The measurement the fix rests on: test_control guards every lock by file, and a river lock's part is a
        sliver of its classes (1-15 of 486 measured 11-09)"""
        with io.open(os.path.join(HERE, "test_control.py"), encoding="utf-8") as fh:
            idx = SA.lock_index(fh.read())
        self.assertIsNotNone(idx, "test_control did not parse")
        self.assertGreaterEqual(len(idx["all"]), SA.NET_NARROW_MIN_LOCKS, "PREMISE: test_control is no longer broad")
        n = len(idx["cls"])
        for lock in (FRAME, PRINTER, "reel.route"):
            mine = sum(1 for v in idx["cls"].values() if lock in v[1])
            self.assertLess(mine, n / 4.0, "%s's part is %d of test_control's %d classes - narrowing buys nothing"
                            % (lock, mine, n))


class AVersionThatTouchesNothingALockReadsKeepsItOpen(_Fixture):

    def test_a_change_outside_every_locks_part_keeps_them_open(self):
        """* THE POINT - the law gained a class and a red-proof that touch no lock: it is owed, and no lock is shut by it"""
        self.census(proven=_broad(added=False))
        for lock in (FRAME, PRINTER):
            ok, why = self.lock(lock)
            self.assertTrue(ok, "%s stayed shut over a change outside its part: %s" % (lock, why))
            self.assertIn("changed only outside its part: %s (#103)" % BROAD_N, why, "the open lock does not say why")
        self.assertNotIn(SA._HEART_STALE_PHRASE, SA.may(FRAME)[1], "may() still refuses the river over it")
        self.assertEqual(SA.owed_guard_rank()["rank"], {}, "the prover still ranks it as a shut lock's guard")

    def test_baseline_with_no_part_recorded_the_whole_file_rule_stands(self):
        """BASELINE: the same change, and a census from before #103 item 3 - every lock the law guards is shut"""
        self.census(proven=_broad(added=False), record=False)
        for lock in (FRAME, PRINTER):
            ok, why = self.lock(lock)
            self.assertFalse(ok, "%s opened with no part recorded" % lock)
            self.assertIn(BROAD_N, why)

    def test_a_change_to_a_class_that_touches_the_lock_shuts_only_that_lock(self):
        self.census(proven=_broad(frame="f0"))
        ok, why = self.lock(FRAME)
        self.assertFalse(ok, "the river opened though the class that guards it changed")
        self.assertIn(BROAD_N, why, "the reason does not name the law")
        self.assertTrue(self.lock(PRINTER)[0], "a change to the river's class shut printer.stream too")

    def test_a_change_to_the_modules_own_code_shuts_every_lock(self):
        self.census(proven=_broad(helper="h0"))
        for lock in (FRAME, PRINTER):
            self.assertFalse(self.lock(lock)[0], "%s opened though the law's module code changed" % lock)

    def test_a_changed_red_proof_aimed_at_the_lock_shuts_it(self):
        self.census(proven=_broad(red_find="def plan(x"))
        self.assertFalse(self.lock(FRAME)[0], "the river opened though a red-proof aimed at its code changed")
        self.assertTrue(self.lock(PRINTER)[0], "a river red-proof shut printer.stream")

    def test_a_class_seen_catching_the_locks_sabotage_holds_it(self):
        """a class that names nothing of the river but CAUGHT its sabotage (recorded from the red memory) is in its part"""
        self.census(proven=_broad(catcher="c0"), catchers={FRAME: ["Catcher"]})
        self.assertFalse(self.lock(FRAME)[0], "the river opened though the class that catches its sabotage changed")
        self.assertTrue(self.lock(PRINTER)[0])

    def test_baseline_the_same_catcher_change_unrecorded_is_outside(self):
        """BASELINE for the case above: unrecorded, that class is outside the river's part"""
        self.census(proven=_broad(catcher="c0"))
        self.assertTrue(self.lock(FRAME)[0], "PREMISE: the Catcher class is in the river's part by its own text")

    def test_a_removed_catcher_holds_the_lock(self):
        """the proved file had a class recorded as catching the river's sabotage; the file on disk no longer has it"""
        self.census(proven=_broad() + _GONE, catchers={FRAME: ["GoneNow"]})
        self.assertFalse(self.lock(FRAME)[0], "the river opened though a class recorded as its catcher is gone")

    def test_baseline_the_same_removal_unrecorded_is_outside(self):
        self.census(proven=_broad() + _GONE)
        self.assertTrue(self.lock(FRAME)[0], "PREMISE: the removed class is in the river's part by its own text")

    def test_the_locks_own_door_changed_shuts_it(self):
        old = lambda stem: "old-bytes" if stem == "reel_retention" else SA._door_sha(stem)
        self.census(proven=_broad(added=False), door=old)
        self.assertFalse(self.lock(FRAME)[0], "the river opened though its own code changed since its guard was proven")
        self.assertTrue(self.lock(PRINTER)[0], "the river's door shut printer.stream")

    def test_a_focused_law_keeps_the_whole_file_rule(self):
        rec = {FOCUSED_N: {"v": SA.LOCK_PART_VERSION, "sha": SA._sha16(_FOCUSED % {"frame": "f0"}),
                           "locks": {FRAME: {"d": SA.lock_part_digest(SA.lock_index(_FOCUSED % {"frame": "f1"}), FRAME),
                                             "c": []}}}}
        self.census(focused_proven=_FOCUSED % {"frame": "f0"}, extra_rec=rec)
        ok, why = self.lock(FRAME)
        self.assertFalse(ok, "a focused law was narrowed to a part")
        self.assertIn(FOCUSED_N, why)

    def test_a_record_for_other_bytes_is_not_believed(self):
        self.census(proven=_broad(added=False))
        with io.open(self.census_path, encoding="utf-8") as fh:
            st = json.load(fh)
        st["lockShas"][BROAD_N]["sha"] = "0" * 16
        with io.open(self.census_path, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        SA._LOCK_MEMO.update(key=None)
        self.assertFalse(self.lock(FRAME)[0], "a part recorded for other bytes opened the river")


class TheConsoleAsksAChild(_Fixture):

    def test_a_pending_index_keeps_the_lock_shut_and_is_asked_again(self):
        self.census(proven=_broad(added=False))
        answers = [None]
        with mock.patch.object(AC, "wanted", lambda: True), \
                mock.patch.object(AC, "lock_index_for", lambda f, key: answers[0]), \
                mock.patch.object(SA, "lock_index", side_effect=AssertionError("the console parsed a gate in its heap")):
            self.assertFalse(self.lock(FRAME)[0], "the river opened before the index child answered")
        # the child has answered now: the same census, asked again, opens (the pending answer was not memoised)
        with io.open(self.files[BROAD_N], encoding="utf-8") as fh:
            idx = SA.lock_index(fh.read())
        with mock.patch.object(AC, "wanted", lambda: True), \
                mock.patch.object(AC, "lock_index_for", lambda f, key: idx):
            self.assertTrue(self.lock(FRAME)[0], "a pending answer was memoised - the river stays shut until the "
                                                 "census changes")


class TheCensusBanksThePartWithTheProof(_Fixture):

    def test_a_banked_broad_law_records_its_part_and_its_catchers(self):
        with mock.patch.object(H, "_red_peek", lambda key: ["Catcher.test_c"]):
            H._write_state({BROAD_N: H.PROVEN, FOCUSED_N: H.PROVEN}, stamp=False)
        with io.open(self.census_path, encoding="utf-8") as fh:
            st = json.load(fh)
        ls = st.get("lockShas") or {}
        self.assertIn(BROAD_N, ls, "the census banked the broad law without its part")
        self.assertEqual(ls[BROAD_N]["sha"], st["gateShas"][BROAD_N], "the part is recorded for other bytes")
        self.assertNotIn(FOCUSED_N, ls, "a focused law was given a part")
        self.assertIn("Catcher", ls[BROAD_N]["locks"][FRAME]["c"], "the class that caught the river's sabotage is not recorded")
        self.assertNotIn("Catcher", ls[BROAD_N]["locks"][PRINTER]["c"], "a river catcher was filed under printer.stream")

    def test_an_unmeasured_law_records_no_part(self):
        H._write_state({BROAD_N: H.PROVEN}, stamp=False)
        H._write_state({BROAD_N: H.BLIND}, stamp=False, unmeasured=[BROAD_N])
        with io.open(self.census_path, encoding="utf-8") as fh:
            st = json.load(fh)
        self.assertNotIn(BROAD_N, st.get("lockShas") or {}, "a law nobody measured kept a part")

    def test_the_banked_part_opens_the_lock_after_an_unrelated_edit(self):
        """end to end: banked by the census writer, then the file gains a class that touches no lock"""
        self._put(BROAD_N, _broad(added=False))
        H._write_state({BROAD_N: H.PROVEN, FOCUSED_N: H.PROVEN}, stamp=False)
        self._put(BROAD_N, _broad())
        with io.open(self.census_path, encoding="utf-8") as fh:
            st = json.load(fh)
        st["gatesFingerprint"] = "f" * 32
        with io.open(self.census_path, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        SA._LOCK_MEMO.update(key=None)
        self.assertTrue(self.lock(FRAME)[0], "the census writer's part did not open the river after an unrelated edit")


RED_PROOF = [
    {"why": "#103 item 3 (REG-3484) - a broad law holds every lock again whatever part of it changed",
     "file": "tv/self_arming.py",
     "find": "            same = _lock_part_unchanged(name, lock, t, files)\n",
     "replace": "            same = False\n",
     "matches": 1},
    {"why": "#103 item 3 - the law's module code is outside every lock's part (a shared helper changes unseen)",
     "file": "tv/self_arming.py",
     "find": "(LOCK_PART_VERSION, lock, (index or {}).get(\"m\"))",
     "replace": "(LOCK_PART_VERSION, lock, \"\")",
     "matches": 1},
    {"why": "#103 item 3 - a class seen catching the lock's sabotage is outside its part",
     "file": "tv/self_arming.py",
     "find": "    for c in sorted(mine | set(extra or ())):\n",
     "replace": "    for c in sorted(mine):\n",
     "matches": 1},
    {"why": "#103 item 3 - a red-proof aimed at the lock's code is outside its part",
     "file": "tv/self_arming.py",
     "find": "        for s in sorted(s for s, lks in red if lock in (lks or ())):\n",
     "replace": "        for s in ():\n",
     "matches": 1},
    {"why": "#103 item 3 - the lock's own door modules are outside its part (its code changes unseen)",
     "file": "tv/self_arming.py",
     "find": "    for stem in _part_door_stems(lock):\n",
     "replace": "    for stem in ():\n",
     "matches": 1},
    {"why": "#103 item 3 - a focused law is narrowed to a part too",
     "file": "tv/self_arming.py",
     "find": "            or len(idx.get(\"all\") or ()) < NET_NARROW_MIN_LOCKS:\n        return False\n    return lock_part_digest",
     "replace": "            or False:\n        return False\n    return lock_part_digest",
     "matches": 1},
    {"why": "#103 item 3 - a console whose index child has not answered opens the lock",
     "file": "tv/self_arming.py",
     "find": "                return True                       # the index child has not answered: counted, and asked again later\n",
     "replace": "                return False\n",
     "matches": 1},
    {"why": "#103 item 3 - the census banks a proof without its part (nothing ever opens)",
     "file": "tv/heart2.py",
     "find": "    _ls = _lock_shas_merge(prior, results, _unm, _gs, _shas, dict(gates))\n",
     "replace": "    _ls = {}\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
