# -*- coding: utf-8 -*-
"""#96 / #88 (his 11-06: "so slowly after time the prices just slowly calliberate themselves to average out base don
perfect tier or normal tier") - THE PRICE DATABASE REFRESHES ITSELF ONLY WHERE A PRICE CHECK ASKS. ITS TIMER LANE IS RETIRED.

v3878 built tvd-price-refresh (d2jsp_refresh.run_once on control_app._price_refresh_loop): the stalest due item, one every
20 minutes, on its own timer. Job E (Claude's #230 6849292433) - RETIRED by his 11-13 ruling: "yea you can", and on a
background re-read, "it doesnt need to redo things for now.. it can do it in the future". This law used to hold every arm
of run_once (stalest first, nan read times, the stand-asides, need-login) and the lane's wiring in every registry; those
arms went with the code they held. What it holds now, honestly:
  * the refresh still exists and has ONE caller: the price check's plan hands d2jsp_price_db.fresh_refresh the item it
    reads (only=) and the one-a-minute pace (pace=) - so a stale price still moves, on his click;
  * nothing else refreshes: d2jsp_refresh keeps no run_once / stale_items / timer, and the lane is not started, not stood
    down, not scoped, not corroborated and not excused from the shelf (test_a_retired_price_refresh_lane_stays_retired
    holds every place a reader would look for the words of the ruling).
RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import d2jsp_refresh as R  # noqa: E402


def _read(name):
    with io.open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return fh.read()


def _fn(src, head):
    a = src.index(head)
    b = src.index("\ndef ", a + 1)
    return src[a:b]


class ThePriceDatabaseRefreshesOnlyWhereAPriceCheckAsks(unittest.TestCase):

    def test_the_price_check_is_the_refreshers_one_caller(self):
        plan = _fn(_read("control_app.py"), "def _d2jsp_price_check_plan(")
        self.assertIn("_PDB.fresh_refresh(db, chosen.append, now, env=env, only=[key, item], pace=", plan,
                      "the price check no longer refreshes the stale item it reads - nothing would ever move a price")

    def test_nothing_else_refreshes_on_a_timer(self):
        for gone in ("run_once", "stale_items", "FIRST_S", "EVERY_S", "LANE", "CHECK_ITEM", "CHECK_EVERY_S", "check_due"):
            self.assertFalse(hasattr(R, gone), "d2jsp_refresh.%s is back - the retired timer refresh returned" % gone)
        self.assertIn("RETIRED by his 11-13 ruling", R.__doc__ or "", "the module no longer says why its lane is gone")

    def test_the_lane_is_retired_in_every_registry(self):
        """was test_the_lane_is_wired_in_every_registry: each registry that held the lane now holds that it is gone"""
        app = _read("control_app.py")
        roster = app[app.index("_HARNESS_ONLY_SKIP = ("):app.index("_LANES_STOOD_DOWN = set()")]
        self.assertFalse('"tvd-price-refresh"' in roster, "a harness stands the retired lane down, as if it still ran")
        self.assertFalse('("tvd-price-refresh",' in app, "the console starts the retired lane again")
        self.assertFalse("def _price_refresh_loop(" in app, "the retired loop is back")
        import auto_scope as AS
        import loop_corroborate as LC
        import shelf_driver as SD
        self.assertNotIn("tvd-price-refresh", AS.LANE_FN, "the scope maps a lane that is retired")
        self.assertNotIn("tvd-price-refresh", AS.LANES, "the scope keeps a sheet for a lane that is retired")
        self.assertNotIn("tvd-price-refresh", SD.NOT_SHELF_LANES, "the shelf excuses a lane that is retired")
        self.assertNotIn("_price_refresh_loop", LC.SURFACES)
        self.assertNotIn("_price_refresh_loop", LC.LOOPS, "a corroborator still waits for the retired loop")
        self.assertNotIn('"_price_refresh_loop": ("tvd-price-refresh",', _read("loop_corroborate.py"),
                         "a corroborator still waits for the retired lane's beat")


RED_PROOF = [
    {"why": "Job E - the price check stops refreshing the item it reads (the refresher has no caller at all)",
     "file": "tv/control_app.py",
     "find": "        r = _PDB.fresh_refresh(db, chosen.append, now, env=env, only=[key, item], pace=_D2JSP_REFRESH_PACE)\n",
     "replace": "        r = {\"say\": None, \"fetched\": []}\n",
     "matches": 1},
    {"why": "Job E - the retired lane's thread is started again",
     "file": "tv/control_app.py",
     "find": "        # re-read is built: a price check refreshes the item it reads, on his click, one search a minute.\n",
     "replace": "        # re-read is built: a price check refreshes the item it reads, on his click, one search a minute.\n"
                "        (\"tvd-price-refresh\", _prune_loop),\n",
     "matches": 1},
    {"why": "Job E - d2jsp_refresh grows its timer pass back",
     "file": "tv/d2jsp_refresh.py",
     "find": "CHECK_NAME = \".d2jsp_check.json\"\n",
     "replace": "CHECK_NAME = \".d2jsp_check.json\"\nEVERY_S = 1200.0\n",
     "matches": 1},
    {"why": "Job E - the scope maps the retired lane again",
     "file": "tv/auto_scope.py",
     "find": "    # Job E - \"tvd-price-refresh\" -> _price_refresh_loop RETIRED (his 11-13 ruling): no lane, no loop\n",
     "replace": "    \"tvd-price-refresh\": \"_price_refresh_loop\",\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
