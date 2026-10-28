# -*- coding: utf-8 -*-
"""#212 (REG-2865) - A LOCK WHOSE DOOR LIVES IN control_app IS GUARDED BY THE LAWS THAT EXERCISE ITS OWN CODE.

REG-2750 (#156) made a lock go STALE only through its own guard laws: the gates that name it, or import or open its door
module or the lock machinery. vault.sweep_start's door module is control_app, and so are prune.reports' and
console.pixel_rescue's. Measured on the batch-3841 tree (1,234 gates): importing or opening control_app made 489 laws guard
the sweep, 490 the prune report and 488 the pixels' reload, while 104 laws name the sweep's own code. After every ship,
hundreds of laws nowhere near the sweep were owed; they never re-prove while he plays (a proof waits for an idle PC), so
the paid sweep stayed shut and the vault ledger went unwritten - the Mac's for hours, the ALT's for days (#212, GrokBot
#230 6475742100).

Now, in a module listed in self_arming.BROAD_DOORS, a law guards a lock only through that lock's LOCK_MARKS: its door
functions and their state, its routes and stores, the modules it reads with, its name in any spelling. A lock with no
marks keeps the import rule, and so does every small door module (sweep_wilson, disk_report_wilson ...): broad in the
safe direction. After (1,235 gates, this law among them): 195 / 83 / 85 guards, and all 105 laws on the sweep's code
still guard it. BLIND still closes every lock (his 2026-09-12 ruling) - untouched.

Driven on the gate files on disk and a fixture census (TV_HEART_CENSUS), so his census is never read. RED_PROOF below.
"""
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx  # noqa: E402
_fx.contain()
import heart2 as H  # noqa: E402
import self_arming as SA  # noqa: E402

FILES = dict(H.gate_files())
SHAS = H.gate_shas()
SWEEP = "vault.sweep_start"
BROAD = ("vault.sweep_start", "prune.reports", "console.pixel_rescue")
#: a law that imports control_app for the Fleet row and touches none of the three locks' code
UNRELATED = "test_his_own_fleet_row_shows_the_version_it_runs"
#: the names of the sweep's own code #212 counted (vault_sweep covers _vault_sweep_run and /api/vault_sweep)
SWEEP_CODE = ("vault_sweep", "sweep_wilson", "vault.sweep_start", "vault_accum", "vault_retro")
_IMPORTS_CA = re.compile(r"(?m)^\s*(?:from\s+control_app\s+import\b|import\s+control_app\b)")


def _text(name):
    f = FILES[name]
    with open(f if os.path.isabs(f) else os.path.join(H.HERE, f), encoding="utf-8") as fh:
        return fh.read()


TEXT = dict((n, _text(n)) for n in FILES)
DECLARING = set(n for n in FILES if H.red_proofs_in(FILES[n]))


_MEMO = {}


def _guards(lock):
    if lock not in _MEMO:
        _MEMO[lock] = set(n for n in FILES if SA._guards_lock(TEXT[n], lock, SA.LOCK_DOORS[lock]))
    return set(_MEMO[lock])


def _door_function(lock):
    """The top-level def in control_app whose body asks may(<lock>) - the lock's door, read off the file."""
    with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    asks = [i for i, ln in enumerate(lines) if ('may("%s")' % lock) in ln.split("#", 1)[0]]   # code, not comments
    if len(asks) != 1:
        raise AssertionError("PREMISE: control_app asks may(%r) %d times, not once" % (lock, len(asks)))
    for i in range(asks[0], -1, -1):
        m = re.match(r"def (\w+)\(", lines[i])
        if m:
            return m.group(1)
    raise AssertionError("PREMISE: no def encloses may(%r)" % lock)


class ABroadDoorCountsOnlyItsOwnCode(unittest.TestCase):

    def test_the_premise_the_unrelated_law_reaches_control_app(self):
        self.assertIn(UNRELATED, FILES, "PREMISE: the unrelated law is gone - pick another control_app law")
        self.assertTrue(_IMPORTS_CA.search(TEXT[UNRELATED]), "PREMISE: %s no longer imports control_app" % UNRELATED)
        self.assertIn(UNRELATED, DECLARING, "PREMISE: %s declares no proof, so it is never owed" % UNRELATED)

    def test_an_unrelated_control_app_law_guards_none_of_the_three(self):
        for lock in BROAD:
            self.assertNotIn(UNRELATED, _guards(lock),
                             "%s guards %s only because it imports control_app" % (UNRELATED, lock))

    def test_most_control_app_laws_guard_none_of_the_three(self):
        importers = set(n for n in DECLARING if _IMPORTS_CA.search(TEXT[n]))
        free = importers - _guards(SWEEP) - _guards("prune.reports") - _guards("console.pixel_rescue")
        self.assertGreater(len(importers), 100, "PREMISE: hardly any law imports control_app (%d)" % len(importers))
        self.assertGreater(len(free), len(importers) // 2,
                           "%d of %d control_app laws still guard a broad lock" % (len(importers) - len(free), len(importers)))

    def test_every_law_on_the_sweeps_own_code_guards_it(self):
        sweep_laws = set(n for n in FILES if any(t in TEXT[n] for t in SWEEP_CODE))
        self.assertGreater(len(sweep_laws), 40, "PREMISE: the tree has %d laws on the sweep's code" % len(sweep_laws))
        missed = sorted(sweep_laws - _guards(SWEEP))
        self.assertEqual(missed, [], "laws on the sweep's own code no longer guard it: %s" % missed[:5])

    def test_the_function_that_asks_each_lock_is_one_of_its_marks(self):
        for lock in BROAD:
            fn = _door_function(lock)
            self.assertTrue(SA._guards_lock("import control_app as ca\nca.%s()\n" % fn, lock, SA.LOCK_DOORS[lock]),
                            "a law driving %s (the door that asks %s) does not guard it" % (fn, lock))

    def test_small_door_modules_and_unmarked_locks_keep_the_import_rule(self):
        self.assertTrue(SA._guards_lock("import sweep_wilson\n", SWEEP, SA.LOCK_DOORS[SWEEP]))
        self.assertTrue(SA._guards_lock("import self_arming\n", SWEEP, SA.LOCK_DOORS[SWEEP]))
        self.assertFalse(SA._guards_lock("import control_app\n", SWEEP, SA.LOCK_DOORS[SWEEP]))
        self.assertTrue(SA._guards_lock("import control_app\n", "a.lock_with_no_marks", ("control_app",)),
                        "a lock in a broad module with no marks of its own lost every guard")


class TheSweepGoesStaleOnlyThroughItsOwnLaws(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="broad_door_")
        self.path = os.path.join(self.d, ".heart2.json")
        self._env = os.environ.get("TV_HEART_CENSUS")
        os.environ["TV_HEART_CENSUS"] = self.path
        SA._LOCK_MEMO.update(key=None)
        self.sweep_law = sorted(n for n in (_guards(SWEEP) & DECLARING) if "sweep" in n)[0]

    def tearDown(self):
        if self._env is None:
            os.environ.pop("TV_HEART_CENSUS", None)
        else:
            os.environ["TV_HEART_CENSUS"] = self._env
        SA._LOCK_MEMO.update(key=None)

    def census(self, owed=(), blind=()):
        """Every gate proven against the files on disk but `owed` (a sha that no longer matches) and `blind` (filed BLIND);
        a fingerprint the tree does not have, so the global rule reads STALE."""
        shas = dict(SHAS)
        for n in owed:
            shas[n] = "0" * 16
        st = {"gatesFingerprint": "f" * 32, "gateShas": shas, "provedGates": sorted(FILES), "blind": list(blind),
              "proved": len(FILES), "declared": len(DECLARING), "total": len(FILES), "sliceOwed": len(owed)}
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(st, fh)
        SA._LOCK_MEMO.update(key=None)

    def test_an_unrelated_law_owed_leaves_the_sweep_watched(self):
        self.census(owed=[UNRELATED])
        self.assertFalse(SA._heart_says_watched()[0], "PREMISE: the fixture census is not stale to the global rule")
        for lock in BROAD:
            ok, why = SA._lock_heart(lock)
            self.assertTrue(ok, "%s closed over a Fleet law: %s" % (lock, why))
        self.assertNotIn(SA._HEART_STALE_PHRASE, SA.may(SWEEP)[1],
                         "may() still refuses the paid sweep over a law that does not exercise it")

    def test_a_sweep_law_owed_makes_the_sweep_stale(self):
        self.census(owed=[self.sweep_law])
        ok, why = SA._lock_heart(SWEEP)
        self.assertFalse(ok, "a changed sweep law (%s) left the paid sweep watched" % self.sweep_law)
        self.assertIn(self.sweep_law, why)

    def test_a_BLIND_anywhere_still_closes_the_sweep(self):
        self.census(owed=[UNRELATED], blind=[UNRELATED])
        self.assertIsNone(SA._lock_heart(SWEEP), "a recorded BLIND was answered per lock")
        self.assertFalse(SA.may(SWEEP)[0], "the paid sweep opened beside a recorded BLIND")


RED_PROOF = [
    {"why": "REG-2865 - importing control_app guards every broad lock again (489 laws owe the paid sweep)",
     "file": "self_arming.py",
     "find": "        if marks and stem in BROAD_DOORS:\n            continue\n",
     "replace": "        if False:\n            continue\n",
     "matches": 1},
    {"why": "REG-2865 - a lock in a broad module with no marks loses every import guard",
     "file": "self_arming.py",
     "find": "        if marks and stem in BROAD_DOORS:\n            continue\n",
     "replace": "        if stem in BROAD_DOORS:\n            continue\n",
     "matches": 1},
    {"why": "REG-2865 - a lock's marks are never read, so laws on the sweep's own code stop guarding it",
     "file": "self_arming.py",
     "find": "    for mark in marks:\n        if mark in text:\n            return True\n",
     "replace": "    for mark in ():\n        if mark in text:\n            return True\n",
     "matches": 1},
    {"why": "REG-2865 - the function that asks the sweep's lock (chronicle_sweep_start) is not one of its marks",
     "file": "self_arming.py",
     "find": "\"VAULT_SWEEP\", \"chronicle_sweep\", \"_chron_sweep\",",
     "replace": "\"VAULT_SWEEP\", \"_chron_sweep\",",
     "matches": 1},
    {"why": "REG-2865 - the sweep's ledger (vault_accum) and readers (vault_retro) are not its marks",
     "file": "self_arming.py",
     "find": "\"_VAULT_JOB\", \"_CHRON_JOB\", \"vault_accum\",\n                          \"VAULT_LEDGER_PATH\", \"vault_retro\",",
     "replace": "\"_VAULT_JOB\", \"_CHRON_JOB\",\n                          \"VAULT_LEDGER_PATH\",",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
