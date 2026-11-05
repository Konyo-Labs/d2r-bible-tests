# -*- coding: utf-8 -*-
"""v3849 (b) - slow Mac endpoints: a slow answer is worked out beside the request, never inside it.

/api/chronicle_scan (~316 s cold), /api/vault_scan (~82 s) and /api/eagle answer at once through
control_app._answer_soon: the kept answer while its signature holds, the last answer marked stale while
ONE thread refreshes it, or "still working it out". A failure is said, never swallowed.
"""
import faulthandler
faulthandler.dump_traceback_later(60, exit=True)   # a request that waits on its own lock fails, never hangs
import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable
enable()

import control_app as ca

HERE = os.path.dirname(os.path.abspath(__file__))
APP = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
UI = open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()


def _wait(pred, s=5.0):
    t = time.time() + s
    while time.time() < t:
        if pred():
            return True
        time.sleep(0.01)
    return False


class TestASlowAnswerIsWorkedOutBesideTheRequest(unittest.TestCase):
    def setUp(self):
        ca._SOON.clear()

    def test_a_cold_ask_answers_at_once_and_one_thread_works(self):
        gate, calls = threading.Event(), []

        def slow():
            calls.append(1)
            gate.wait(5)
            return {"ok": True, "totals": {"reels": 3}}
        t0 = time.time()
        a = ca._answer_soon("k1", "s1", slow)
        b = ca._answer_soon("k1", "s1", slow)
        self.assertLess(time.time() - t0, 1.0)
        self.assertTrue(a["pending"] and b["pending"])
        self.assertIn("still working it out", a["note"])
        gate.set()
        self.assertTrue(_wait(lambda: not ca._SOON["k1"]["running"]))
        self.assertEqual(len(calls), 1)
        c = ca._answer_soon("k1", "s1", slow)
        self.assertEqual(c["totals"], {"reels": 3})
        self.assertTrue(c["cached"])

    def test_a_moved_signature_serves_the_last_answer_stale_while_it_refreshes(self):
        ca._answer_soon("k2", "s1", lambda: {"ok": True, "n": 1})
        self.assertTrue(_wait(lambda: ca._SOON["k2"]["res"] is not None))
        gate = threading.Event()

        def slow():
            gate.wait(5)
            return {"ok": True, "n": 2}
        d = ca._answer_soon("k2", "s2", slow)
        self.assertEqual(d["n"], 1)
        self.assertTrue(d["stale"])
        gate.set()
        self.assertTrue(_wait(lambda: ca._SOON["k2"]["sig"] == "s2"))
        self.assertEqual(ca._answer_soon("k2", "s2", slow)["n"], 2)

    def test_a_failure_is_said_not_swallowed(self):
        def boom():
            raise RuntimeError("disk gone")
        ca._answer_soon("k3", "s1", boom)
        self.assertTrue(_wait(lambda: not ca._SOON["k3"]["running"]))
        e = ca._answer_soon("k3", "s1", boom)
        self.assertIs(e["ok"], False)
        self.assertIn("disk gone", e["why"])

    def test_an_age_kept_answer_expires(self):
        ca._answer_soon("k4", None, lambda: {"ok": True, "n": 1}, max_age_s=60)
        self.assertTrue(_wait(lambda: ca._SOON["k4"]["res"] is not None))
        self.assertTrue(ca._answer_soon("k4", None, lambda: {"ok": True}, max_age_s=60)["cached"])
        late = ca._answer_soon("k4", None, lambda: {"ok": True, "n": 9}, max_age_s=60, now=time.time() + 120)
        self.assertTrue(late["stale"])

    def test_the_three_routes_ask_through_it(self):
        self.assertEqual(APP.count('_answer_soon("chronicle_scan", _hist_signature('), 1)
        self.assertEqual(APP.count('_answer_soon("vault_scan", _hist_signature('), 1)
        # v3864 - the eagle's full pass runs in a child (REG-2987) inside the same answer-soon (never waited on by the route)
        self.assertEqual(APP.count('_answer_soon("eagle", None, _eagle_full, max_age_s=60)'), 1)
        self.assertEqual(UI.count("if (j.pending) {"), 1)


RED_PROOF = [
    {"matches": 1, "why": "the route waits on the work again", "file": "tv/control_app.py",
     "find": "            threading.Thread(target=_work, name=\"tvd-answer-soon-\" + key, daemon=True).start()",
     "replace": "            _work()"},
    {"matches": 1, "why": "a second ask starts a second thread", "file": "tv/control_app.py",
     "find": "        if not st[\"running\"]:\n            st[\"running\"], st[\"started\"] = True, now",
     "replace": "        if True:\n            st[\"running\"], st[\"started\"] = True, now"},
    {"matches": 1, "why": "a moved signature still reads as fresh", "file": "tv/control_app.py",
     "find": "            (sig is not None and st[\"sig\"] == sig) or",
     "replace": "            (sig is not None) or"},
    {"matches": 1, "why": "a failure is swallowed into pending", "file": "tv/control_app.py",
     "find": "        if st[\"err\"] and not st[\"running\"] and st[\"res\"] is None:", "replace": "        if False:"},
    {"matches": 1, "why": "age never expires", "file": "tv/control_app.py",
     "find": "now - st[\"at\"] <= max_age_s))", "replace": "True))"},
    {"matches": 1, "why": "the chronicle route blocks again", "file": "tv/control_app.py",
     "find": "self._json(200, _answer_soon(\"chronicle_scan\", _hist_signature(os.environ.get(\"TV_HIST\") or HIST_DIR), chronicle_scan_cost))",
     "replace": "self._json(200, chronicle_scan_cost())"},
    {"matches": 1, "why": "the eagle panel counts a pending answer as zero checks", "file": "tv/control_ui.html",
     "find": "      if (j.pending) {", "replace": "      if (false) {"},
]

if __name__ == "__main__":
    unittest.main()
