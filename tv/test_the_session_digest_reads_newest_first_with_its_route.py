# -*- coding: utf-8 -*-
"""v3857 item 20 (#230): the Sessions list and the shared digest read newest-first by when each session STARTED, and
one scenario journal - a farm run, a stash visit, a chronicle panel - comes out of the digest with its farmed, stashed
and chronicle names where the owner tab and the shadow both read them.

Elad 2026-11-03: a long early run that ended last sat above a later session, so the list read out of order against
its own start-time labels. REG-2736 still holds: the moment is the CAPTURE time, so a re-read never jumps a reel up.

RED_PROOF below: each one, applied, turns this law red."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()

H = 3600 * 1000


def _journal():
    rows = []
    # EARLY: starts first, picks up a Shako and stashes it, and is still writing after LATE has begun (it ends last)
    rows.append({"ts": 1 * H, "captureTs": 1 * H, "sessionId": "EARLY", "scene": "inventory", "names": ["Shako"]})
    rows.append({"ts": 1 * H + 60000, "captureTs": 1 * H + 60000, "sessionId": "EARLY", "names": ["Shako"],
                 "scene": "stash", "stashTab": "personal"})
    # v3859 - a chronicle find is the green line on the item's own tooltip (session_route)
    rows.append({"ts": 5 * H, "captureTs": 5 * H, "sessionId": "EARLY", "scene": "inventory",
                 "names": ["Harlequin Crest", "Eligible for Chronicle"]})
    # LATE: starts after EARLY, ends before it
    rows.append({"ts": 2 * H, "captureTs": 2 * H, "sessionId": "LATE", "names": ["Ber Rune"], "scene": "inventory"})
    rows.append({"ts": 2 * H + 60000, "captureTs": 2 * H + 60000, "sessionId": "LATE", "names": ["Ber Rune"],
                 "scene": "inventory"})
    return rows


class TheDigestReadsNewestFirst(unittest.TestCase):

    def test_the_list_is_by_start(self):
        import replay as rp
        g = rp.split_sessions(_journal())
        ids = [next(r["sessionId"] for r in x) for x in g]
        print("split order: %s" % ids)
        self.assertEqual(["LATE", "EARLY"], ids, "the session that STARTED last must be on top")

    def test_the_digest_carries_the_same_order_and_the_route(self):
        import shadow_sessions as ss
        d = ss.digest(_journal(), "/nonexistent-hist", lambda r: True, 6 * H, make=lambda *a, **k: None)
        ses = d.get("sessions") or []
        ids = [s.get("sessionId") for s in ses]
        print("digest order: %s" % ids)
        self.assertEqual(["LATE", "EARLY"], ids, "the shared digest must read in the Sessions tab's order")
        self.assertTrue(all(ses[i]["t0"] >= ses[i + 1]["t0"] for i in range(len(ses) - 1)),
                        "digest t0s are not newest-first")
        early = ses[1]
        flat = lambda v: repr(v)
        self.assertIn("Shako", flat(early.get("farmed")), "the farm run's name is not in farmed")
        self.assertEqual({"bases": [["Shako", 1]]}, early.get("stashed"), "stashed is not what this run put away")
        self.assertEqual(["Harlequin Crest"], early.get("chronicleNames"), "the chronicle panel's name is missing")
        self.assertEqual(1, early.get("chroniclesFound"))
        self.assertNotIn("Ber Rune", flat(early.get("stashed")), "another session's pickup was called stashed")


RED_PROOF = [
    {"why": "the list goes back to ordering by where a session ENDED",
     "file": "tv/replay.py",
     "find": "    sessions.sort(key=lambda g: min(session_moments(g) or [0]))\n",
     "replace": "    sessions.sort(key=lambda g: max(session_moments(g) or [0]))\n",
     "matches": 1},
    {"why": "stashed is every farmed item, not what this run put away",
     "file": "tv/shadow_sessions.py",
     "find": "         \"stashed\": rt[\"stashed\"],\n",
     "replace": "         \"stashed\": rt[\"farmed\"],\n",
     "matches": 1},
    {"why": "the digest's chronicle names stop coming from the route",
     "file": "tv/shadow_sessions.py",
     "find": "         \"chronicleNames\": rt[\"chronicle\"][:MAX_NAMES] if rt[\"chronicle\"] is not None else None,\n",
     "replace": "         \"chronicleNames\": [],\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
