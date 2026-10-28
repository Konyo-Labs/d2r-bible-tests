# -*- coding: utf-8 -*-
"""#128 (REG-2916) - A LANE THAT FORBIDS DELETE CLEARS ONLY WHAT IT DECLARES, AND THE DECLARATION IS CHECKED AGAINST ITS CODE.

auto_scope.undeclared_reach_abilities reported three lanes - tvd-shadow-watch, tvd-stash-watch and tvd-version-drift - as
promising never to delete while their reach can delete, with nothing permitting it; only tvd-ledger-backup carried a clause
(`rotates`). Read in the code, every delete call in their depth-3 reach is the console's own bookkeeping: the agent and capture
pid files, the live eye frame, a temporary launcher picture the lane took itself and the 'closed on purpose' marker. None
is a reel, his footage, a ledger or the vault.

Each lane now declares those functions in a `clears` clause, and auto_scope.CLEARS names the exact target each one removes.
clears_report reads every delete call in the lane's reach out of the syntax tree: the row is permitted only when every call is
a declared function removing a declared target. A new delete, a new target or a new deleting function anywhere in the reach
is a gap again - the checker was not loosened; the declaration was made to match the code.

Driven on control_app itself (the same depth-3 walk the reporter uses). RED_PROOF below: each widens one lane's reach.
"""
import os
import sys
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

import auto_scope as AS  # noqa: E402

THREE = ("tvd-shadow-watch", "tvd-stash-watch", "tvd-version-drift")


def _ca():
    import control_app as ca
    return ca


class _Lane(object):
    LANE = None

    def test_its_reach_deletes_only_what_it_declares(self):
        r = AS.clears_report(_ca(), self.LANE)
        self.assertTrue(r["checked"], "%s: the reach could not be walked: %s" % (self.LANE, r["why"]))
        self.assertEqual(r["gaps"], [], "%s deletes something its declaration does not name: %s" % (self.LANE, r["gaps"]))
        self.assertEqual(r["stale"], [], "%s declares a function its reach no longer touches: %s" % (self.LANE, r["stale"]))
        self.assertTrue(r["permitted"])

    def test_the_reporter_no_longer_calls_it_undeclared(self):
        rows = [x for x in AS.undeclared_reach_abilities(_ca()) if x["lane"] == self.LANE]
        self.assertTrue(rows, "PREMISE: %s's reach no longer deletes at all - re-read this law" % self.LANE)
        self.assertEqual([x for x in rows if not x["permitted"]], [],
                         "%s is still reported as reaching an undeclared delete" % self.LANE)

    def test_its_never_line_does_not_say_nothing_is_removed(self):
        never = AS.LANES[self.LANE]["never"]
        self.assertNotIn("nothing on disk is written or removed", never)
        self.assertIn("the only files it removes", never.lower(), "%s's promise does not say what it does clear" % self.LANE)


class TheShadowWatch(_Lane, unittest.TestCase):
    LANE = "tvd-shadow-watch"


class TheStashWatch(_Lane, unittest.TestCase):
    LANE = "tvd-stash-watch"


class TheVersionDrift(_Lane, unittest.TestCase):
    LANE = "tvd-version-drift"


class TheCheckerCanSayNo(unittest.TestCase):
    """The declaration is checked, not trusted: take one target away and the row is a break again."""

    def test_a_target_the_table_does_not_name_is_a_gap(self):
        saved = AS.CLEARS["_stop_capture"]
        AS.CLEARS["_stop_capture"] = dict(saved, targets=())
        try:
            r = AS.clears_report(_ca(), "tvd-stash-watch")
        finally:
            AS.CLEARS["_stop_capture"] = saved
        self.assertFalse(r["permitted"])
        self.assertTrue(any("_stop_capture deletes CAP_PID_PATH" in g for g in r["gaps"]), r["gaps"])

    def test_the_reporter_asks_the_check_not_the_clause(self):
        saved = AS.CLEARS["_stop_capture"]
        AS.CLEARS["_stop_capture"] = dict(saved, targets=())
        try:
            rows = [x for x in AS.undeclared_reach_abilities(_ca()) if x["lane"] == "tvd-stash-watch"]
        finally:
            AS.CLEARS["_stop_capture"] = saved
        self.assertTrue(rows and not any(x["permitted"] for x in rows),
                        "a clause whose table no longer covers the reach still granted the row: %r" % rows)

    def test_a_lane_with_no_clause_stays_undeclared(self):
        saved = AS.LANES
        AS.LANES = dict(saved, **{"tvd-stash-watch": dict(saved["tvd-stash-watch"], clears=None)})
        try:
            rows = [x for x in AS.undeclared_reach_abilities(_ca()) if x["lane"] == "tvd-stash-watch"]
        finally:
            AS.LANES = saved
        self.assertTrue(rows and not any(x["permitted"] for x in rows), rows)

    def test_every_table_entry_is_some_lanes_clause(self):
        """An entry no lane declares would excuse the next function to grow that name."""
        used = set(f for spec in AS.LANES.values() for f in (spec.get("clears") or []))
        self.assertEqual(sorted(set(AS.CLEARS) - used), [], "CLEARS names functions no lane declares")
        self.assertEqual(sorted(used - set(AS.CLEARS)), [], "a lane declares a function CLEARS does not describe")

    def test_the_delete_reader_reads_calls_not_prose(self):
        src = ("def f(p):\n"
               "    # os.remove(HIS_LEDGER) is only a comment\n"
               "    os.remove(PID_PATH)\n"
               "    shutil.rmtree(d, ignore_errors=True)\n"
               "    q.unlink()\n")
        self.assertEqual(AS.delete_targets(src), ["PID_PATH", "d", "q"])


RED_PROOF = [
    {"why": "REG-2916 - the shadow watch's launcher picture clause widens: it removes the console log instead of its own picture",
     "file": "tv/control_app.py",
     "find": "    finally:\n        if path:\n            try:\n                os.remove(path)\n",
     "replace": "    finally:\n        if path:\n            try:\n                os.remove(LOG_PATH)\n",
     "matches": 1},
    {"why": "REG-2916 - the stash watch's own loop gains an undeclared delete",
     "file": "tv/control_app.py",
     "find": "            _lane_tick('tvd-stash-watch', _STASH_WATCH_POLL_S)\n",
     "replace": "            _lane_tick('tvd-stash-watch', _STASH_WATCH_POLL_S)\n            os.remove(VAULT_LEDGER_PATH) if False else None\n",
     "matches": 1},
    {"why": "REG-2916 - the version drift's marker clearing widens to the console's log",
     "file": "tv/control_app.py",
     "find": "        os.remove(path or _exit_on_purpose_path())\n",
     "replace": "        os.remove(LOG_PATH)\n",
     "matches": 1},
    {"why": "REG-2916 - a lane's clause is granted without checking its reach against the table",
     "file": "tv/auto_scope.py",
     "find": "                                           or (bool(spec.get(\"clears\")) and clears_report(mod, lane)[\"permitted\"]))),\n",
     "replace": "                                           or bool(spec.get(\"clears\")))),\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
