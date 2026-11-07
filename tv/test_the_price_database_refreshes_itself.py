# -*- coding: utf-8 -*-
"""#96 / #88 (his 11-06: "so slowly after time the prices just slowly calliberate themselves to average out base don
perfect tier or normal tier") - THE PRICE DATABASE REFRESHES ITSELF, ONE DUE ITEM A PASS, NEVER BESIDE HIS GAME.

d2jsp_price_db.fresh_refresh was written in v3849 and nothing called it. tvd-price-refresh (d2jsp_refresh.run_once) asks
the stalest due item once a pass through the desk's own quote and folds it through the console's one DB writer; it asks
nothing while checks run, while the prover would stand aside (he plays, a sweep reads, a push grades), over a database that
will not read, or when nothing is due; a sign-in that is off is said, never opened. Held here: every arm of run_once with
handed-in doors, and the lane's wiring in every registry a console lane lives in. RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import d2jsp_price_db as P  # noqa: E402
import d2jsp_refresh as R  # noqa: E402

NOW = time.mktime(time.strptime("2026-11-07", "%Y-%m-%d"))
DAY = 86400.0


def _db(items):
    db = P.empty()
    for name, read_ago, post_ago in items:
        db["items"][P.key_of(name)] = {"item": name, "readAt": NOW - read_ago * DAY, "posts": {
            "https://forums.d2jsp.org/topic.php?t=%d" % abs(hash(name)): {
                "fg": 20, "day": time.strftime("%Y-%m-%d", time.localtime(NOW - post_ago * DAY)),
                "link": "https://forums.d2jsp.org/topic.php?t=1", "w": 1, "perfect": False, "src": "mac", "seenAt": 0}}}
    return db


class ThePriceDatabaseRefreshesItself(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="price-refresh-")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.path = os.path.join(self.d, "d2jsp_price_db.json")
        P.save(self.path, _db([("Shako", 5, 1), ("Gull", 9, 2), ("Arachnid Mesh", 1, 1)]))
        self.asked, self.folded = [], []

    def _run(self, **kw):
        a = dict(quote=lambda n: (self.asked.append(n) or {"reason": "read", "item": n}),
                 fold=lambda r: (self.folded.append(r) or {}), stand_aside=lambda: False, now=NOW, checks=lambda: False)
        a.update(kw)
        return R.run_once(self.path, **a)

    def test_it_asks_the_stalest_due_item_once_and_folds_it(self):
        r = self._run()
        self.assertEqual(self.asked, ["Gull"], "not the stalest due item, or more than one a pass: %r" % self.asked)
        self.assertEqual([x["item"] for x in self.folded], ["Gull"], "the answer was not folded into the database")
        self.assertTrue(r["worked"])
        self.assertEqual(r["owed"], 2, "Arachnid Mesh (read a day ago, a fresh post) was counted due")

    def test_it_asks_nothing_while_checks_run_or_beside_his_game(self):
        for kw, word in ((dict(checks=lambda: True), "checks"), (dict(checks=lambda: None), "UNKNOWN"),
                         (dict(stand_aside=lambda: True), "playing")):
            self.asked[:] = []
            r = self._run(**kw)
            self.assertEqual(self.asked, [], "the forum was asked while %s" % word)
            self.assertFalse(r["worked"])
            self.assertIn(word, r["why"])

    def test_an_unreadable_database_or_nothing_due_asks_nothing(self):
        with io.open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        r = self._run()
        self.assertEqual((self.asked, r["worked"]), ([], False))
        self.assertIn("UNKNOWN", r["why"])
        P.save(self.path, _db([("Shako", 0.5, 1)]))
        r = self._run()
        self.assertEqual((self.asked, r["owed"]), ([], 0))

    def test_a_sign_in_that_is_off_is_said_and_nothing_is_folded(self):
        r = self._run(quote=lambda n: {"reason": "need-login", "item": n})
        self.assertIn("sign-in is off", r["why"])
        self.assertEqual(self.folded, [], "a need-login answer was folded as a reading")

    def test_a_raising_door_never_raises_out_of_the_pass(self):
        r = self._run(quote=lambda n: (_ for _ in ()).throw(OSError("boom")))
        self.assertIn("raised OSError", r["why"])

    def test_a_read_time_that_will_not_parse_is_unknown_and_asked_first(self):
        """swallow_ratchet (v3878 pre-flight): an unparseable readAt was turned into 0.0 - a made-up time; it is None
        (UNKNOWN) and still asked first"""
        db = _db([("Shako", 5, 1), ("Gull", 9, 2)])
        db["items"][P.key_of("Shako")]["readAt"] = "not a time"
        due = R.stale_items(db, NOW + 30 * DAY)
        self.assertEqual(due[0][1], "Shako", due)
        self.assertIsNone(due[0][2], "an unreadable read time was handed on as a number: %r" % (due[0],))

    def test_the_lane_is_wired_in_every_registry(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            app = fh.read()
        self.assertIn('        ("tvd-price-refresh", _price_refresh_loop),', app, "the console never starts the lane")
        self.assertIn('fold=_d2jsp_db_fold, stand_aside=_sp_yield_here)', app,
                      "the lane does not fold through the one DB writer, or does not stand aside for his game")
        self.assertIn('"tvd-price-refresh",', app[app.index("_HARNESS_ONLY_SKIP = ("):app.index("_LANES_STOOD_DOWN = set()")],
                      "a harness would search the forum on a timer")
        import auto_scope as AS
        import loop_corroborate as LC
        import shelf_driver as SD
        self.assertEqual(AS.LANE_FN.get("tvd-price-refresh"), "_price_refresh_loop", "the scope's lane-to-loop map misses it")
        self.assertIn("tvd-price-refresh", AS.LANES, "the lane's scope sheet is missing")
        self.assertEqual(AS.LANES["tvd-price-refresh"].get("forbids"), ["delete"])
        self.assertIn("tvd-price-refresh", SD.NOT_SHELF_LANES)
        with io.open(os.path.join(HERE, "loop_corroborate.py"), encoding="utf-8") as fh:
            self.assertIn('"_price_refresh_loop": ("tvd-price-refresh",', fh.read(), "nobody corroborates the lane's beat")
        self.assertEqual((R.FIRST_S, R.EVERY_S), (900.0, 1200.0))


RED_PROOF = [
    {
        "why": "v3878 - one item whose read time will not parse raises out of stale_items and stops the lane for all",
        "file": "d2jsp_refresh.py",
        "find": "        try:\n            due, _why = P.is_stale(db, k, now, key=k)\n        except (TypeError, ValueError):\n            due = True",
        "replace": "        if True:\n            due, _why = P.is_stale(db, k, now, key=k)\n        else:\n            due = True",
        "matches": 1,
    },
    {
        "why": "v3878 swallow_ratchet - an unparseable read time becomes a made-up 0.0 again",
        "file": "d2jsp_refresh.py",
        "find": "                ra = None                              # a read time that will not parse is UNKNOWN",
        "replace": "                ra = 0.0                               # a read time that will not parse is UNKNOWN",
        "matches": 1,
    },
    {"why": "#96 - the refresh asks beside his game (the stand-aside judge is ignored)",
     "file": "tv/d2jsp_refresh.py",
     "find": "            if stand_aside():\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "#96 - the refresh asks while checks run",
     "file": "tv/d2jsp_refresh.py",
     "find": "        if busy is None or busy:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "#96 - the freshest item is asked first, never the stalest",
     "file": "tv/d2jsp_refresh.py",
     "find": "    out.sort(key=lambda r: (r[2], r[0]))\n",
     "replace": "    out.sort(key=lambda r: (r[2], r[0]), reverse=True)\n",
     "matches": 1},
    {"why": "#96 - the console never starts the lane, so nothing ever refreshes a price",
     "file": "tv/control_app.py",
     "find": "        (\"tvd-price-refresh\", _price_refresh_loop),\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
