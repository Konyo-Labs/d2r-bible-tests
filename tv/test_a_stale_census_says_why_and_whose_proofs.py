# -*- coding: utf-8 -*-
"""v3855 C6 (Elad 2026-11-02) - A STALE PROOF CENSUS SAYS WHY ON THE FLEET, AND WHOSE FRESH PROOFS IT BORROWS.

The ALT (a take-only PC, PROOF_FLEET_TAKES_ONLY) borrows Dean's, then the Mac's, fresh proofs through the proof carrier,
as designed (PROOF_CARRIER_ACCEPTS). The beacon sent only census + key, so the Fleet row said "locks shut" with no reason.
Now the beacon's heart carries `why` (the lane's say, owed count, the carrier's say/doctor) and `takesFrom`, and the Fleet
row prints both. Pure: heart_stale_why; static: the beacon and the row read it.
"""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import control_app as CA  # noqa: E402

SP = {"say": "the gates changed since this PC last proved them", "owed": 31,
      "carrier": {"takesFrom": ["Dean", "Konyo"], "say": "a peer may already have proved them"}}  # v3859: never the owed words, or the carrier says them for the lane


class StaleCensusSaysWhy(unittest.TestCase):
    def test_current_says_nothing(self):
        self.assertEqual(CA.heart_stale_why("current", SP), (None, ["Dean", "Konyo"]))

    def test_stale_names_reason_owed_and_peers(self):
        why, peers = CA.heart_stale_why("stale", SP)
        self.assertEqual(peers, ["Dean", "Konyo"])
        for w in ("census stale", "gates changed", "31 law(s) owed", "borrows fresh proofs from Dean, Konyo", "peer may already"):
            self.assertIn(w, why)

    def test_missing_pieces_are_unknown_not_dropped(self):
        why, peers = CA.heart_stale_why("missing", {})
        self.assertEqual(peers, [])
        self.assertIn("UNKNOWN", why)
        self.assertIn("borrows from no PC", why)

    def test_the_alt_is_still_wired_to_borrow(self):
        self.assertIn("Konyo · ALT", CA.PROOF_FLEET_TAKES_ONLY)
        self.assertEqual(CA.PROOF_CARRIER_ACCEPTS["Konyo · ALT"][0], "Dean")

    def test_beacon_and_fleet_row_carry_it(self):
        src = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.assertIn('out["heart"]["why"] = _hw', src)
        ui = open(os.path.join(HERE, "control_ui.html"), "rb").read().decode("utf-8", "replace")
        self.assertIn("(hs && hs.why ? ' \\u2014 ' + hs.why : '')", ui)
        self.assertIn("' \\u00b7 borrows ' + escC(hs.takesFrom.join('/'))", ui)


RED_PROOF = [
    {"why": "the beacon drops the reason", "file": "tv/control_app.py",
     "find": '    out["heart"]["why"] = _hw\n', "replace": "", "matches": 1},
    {"why": "the owed count is not said", "file": "tv/control_app.py",
     "find": '        parts.append("%d law(s) owed" % owed)', "replace": "        pass", "matches": 1},
    {"why": "a stale census reads as current", "file": "tv/control_app.py",
     "find": '    if census in (None, "current"):\n        return None, takes', "replace": "    if True:\n        return None, takes", "matches": 1},
    {"why": "the Fleet row hides the borrowing", "file": "tv/control_ui.html",
     "find": "' \\u00b7 borrows ' + escC(hs.takesFrom.join('/'))", "replace": "'' + escC('')", "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
