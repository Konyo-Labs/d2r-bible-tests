# -*- coding: utf-8 -*-
"""v2742 — THE TWO MODULES AT THE CENTRE OF THE RIVER WERE WATCHED BY NOTHING.

Konyo: *"all connected to the heart of the console obviously so they flag themselves and wilson
score whatever is logically needed"*.

MEASURED the heart's real coverage BEFORE adding anything, because a fourth watcher over a
well-watched module is decoration while the centre goes unguarded:

    module            corroborate invariants     console_doctor checks
    reel_router                 0                        0     <- the STATION ASSIGNER
    printer                     0                        0     <- the STORYLINE
    reel_story                  7                        0
    one_funnel                  8                        0
    frame_authority            15                        0
    reel_retention             13                        1

`reel_router` assigns one station per reel — the whole stamp — and was watched by no invariant,
checked by no doctor row, and read by no console code at all (`grep -c reel_router
tv/control_app.py` -> 0). Built, correct, covered by its own suite, and invisible to every
supervision layer in the repo. That is the shape of every defect this heart exists to catch, in the
module that describes the pipeline.

=== WHAT THIS FILE PINS, AND WHY EACH IS SHAPED THE WAY IT IS ===

1. THE DOCTOR ROW IS RED TODAY, ON PURPOSE. 24 of 40 reels sit at a station owing work no automatic
   lane delivers (PRINTER 11 · STATION 7 · EMPTY 6). A check that could only ever be green measures
   nothing, so this file asserts the row CAN fail rather than asserting it passes.

2. IT MUST EXCLUDE THE BY-DESIGN STATIONS. JOIN (4) owes a code change and CAPTURE (12) owes a
   capture change (REG-340). Counting those makes the row read 40 of 40, which is true and useless
   — a row that cries wolf gets ignored, and a distrusted instrument is a switched-off one.

3. THE INVARIANT USES `==`, NOT `<=`. A router stationing FEWER reels than the shelf holds is
   silently dropping some; MORE means it invented one. Both are defects, so neither half may be
   quietly conceded.

4. ⛔ NO WILSON SCORE ON A STATE. A wilson lock belongs on a claim that can be ATTACKED. "The river
   is moving" is a READING — manufacturing attacks to give it a number is the inflation
   `_hardening_gap` refuses, and this file asserts no such lock was created.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import console_doctor as D  # noqa: E402
import corroborate as C  # noqa: E402

DOC = io.open(os.path.join(HERE, "console_doctor.py"), encoding="utf-8").read()


RED_PROOF = [
    {
        "why": 'the law requires this text in corroborate.py, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'corroborate.py',
        # ⚠ the tamper must still PARSE. Replacing the whole `("router-and-shelf-agree",`
        # left `return _HEART2_TAMPERED_` followed by the call's remaining arguments, so
        # heart2 reported INVALID (unexpected indent) rather than RED — a sabotage that
        # cannot compile proves nothing about the law. Rename the witness, keep the syntax.
        "find": 'return ("router-and-shelf-agree",',
        "replace": 'return ("_HEART2_TAMPERED_",',
        "matches": 1,
    },
]

class _Router(object):
    """Stands in for reel_router.route() so every verdict can be forced without his shelf."""

    def __init__(self, payload):
        self.payload = payload

    def __call__(self, *a, **k):
        return self.payload


def _verdict(payload, delivery=None):
    """REG-3201 - the per-reel delivery (control_app's lane stores) is a seam too: a fixture's reels are asked of the
    fixture, never of his live lanes. None = UNKNOWN, which keeps the station-level reading."""
    import reel_router as RR
    fn = dict(D.CHECKS)["the river"]
    real, RR.route = RR.route, _Router(payload)
    real_dl, D._river_delivery = D._river_delivery, (delivery or (lambda st, reels: None))
    try:
        return fn()
    finally:
        RR.route = real
        D._river_delivery = real_dl


def _reels(*specs):
    return {"ok": True, "reels": [{"reel": "r%d" % i, "station": s, "owes": o}
                                  for i, (s, o) in enumerate(specs)]}


class TheRiverIsWatched(unittest.TestCase):

    # ── both watchers exist and are REGISTERED ────────────────────────────────────────────────
    def test_the_doctor_row_is_registered(self):
        """⚠ A check defined and not in CHECKS runs never — this repo's most repeated defect in its
        smallest form. [[the-unjoined-end]]"""
        self.assertIn("the river", dict(D.CHECKS),
                      "the river doctor row is not registered, so it never runs")

    def test_the_invariant_is_registered(self):
        names = [b()[0] for b in C.BUILDERS]
        self.assertIn("router-and-shelf-agree", names,
                      "the router/shelf invariant is not in BUILDERS, so the corroborator never "
                      "evaluates it")

    # ── ⚠⚠ IT MUST BE ABLE TO FAIL ────────────────────────────────────────────────────────────
    def test_a_stuck_reel_is_MISSING_and_NAMES_the_stations(self):
        st, say = _verdict(_reels(("PRINTER", "SEAL — the names were read; no seal to put them in"),
                                  ("STATION", "a paid read"),
                                  ("PRINTER", "SEAL")))
        self.assertEqual(D.MISSING, st, "reels owing work no lane delivers were graded as fine")
        self.assertIn("PRINTER", say, "the message does not name WHICH station is stuck — a count "
                                      "alone is not actionable")
        self.assertIn("3 of 3", say)

    def test_a_river_that_MOVES_is_OK(self):
        """The other direction, and it matters as much: if every stationed reel has a lane, this
        must go green. A row that can only ever be red is as useless as one that can only be green."""
        st, _ = _verdict(_reels(("STATION", ""), ("PRINTER", None)))
        self.assertEqual(D.OK, st, "a river with nothing owed was still graded as stuck")

    # ── ⚠ THE BY-DESIGN SPLIT, WITHOUT WHICH IT CRIES WOLF ────────────────────────────────────
    def test_JOIN_and_CAPTURE_are_NOT_counted_as_stuck(self):
        """JOIN owes a CODE change and CAPTURE owes a CAPTURE change (REG-340). Counting them makes
        the row read 40 of 40 — true, useless, and ignored within a week."""
        st, say = _verdict(_reels(("JOIN", "sealed AND the names are on disk. Code."),
                                  ("CAPTURE", "the capture must change")))
        self.assertEqual(D.OK, st,
                         "by-design stations were counted as stuck: %s" % say)

    def test_the_by_design_list_carries_a_REASON_for_each(self):
        """An exemption with no reason is an exemption nobody can audit, and it silently grows."""
        for k, v in D._BY_DESIGN_STATIONS.items():
            self.assertTrue(v and len(v) > 20,
                            "%s is exempted with no real reason given" % k)

    # ── UNKNOWN is never collapsed into OK ────────────────────────────────────────────────────
    def test_an_unreadable_router_is_UNKNOWN_not_OK(self):
        for bad in ({"ok": False, "why": "simulated"}, {"ok": True, "reels": []}, None):
            st, _ = _verdict(bad)
            self.assertEqual(D.UNKNOWN, st,
                             "a router that answered %r was not treated as UNMEASURED" % (bad,))

    # ── the invariant's shape ─────────────────────────────────────────────────────────────────
    def test_the_invariant_demands_EQUALITY(self):
        """`<=` would silently permit a router that drops reels — the more likely direction, and
        the one that makes every station count a claim about a shelf nobody else sees."""
        spec = C._inv_the_router_and_the_shelf_count_the_SAME_reels()
        self.assertEqual("==", spec[-1],
                         "the router/shelf invariant no longer demands equality, so one of the two "
                         "directions is being conceded")

    def test_either_side_unreadable_is_UNKNOWN(self):
        spec = C._inv_the_router_and_the_shelf_count_the_SAME_reels()
        left, right = spec[4], spec[6]
        import reel_router as RR
        import reel_story as RS
        for mod, attr in ((RR, "route"), (RS, "story")):
            real = getattr(mod, attr)
            setattr(mod, attr, _Router({"ok": False, "why": "simulated"}))
            try:
                self.assertIsNone(left() if mod is RR else right(),
                                  "an unreadable %s produced a COUNT, which would make this "
                                  "invariant hold or fail on a number nobody measured" % attr)
            finally:
                setattr(mod, attr, real)

    # ── ⛔ NO WILSON LOCK ON A STATE ───────────────────────────────────────────────────────────
    def test_no_wilson_lock_was_invented_for_the_river_state(self):
        """A wilson score belongs on a claim that can be ATTACKED. "The river is moving" is a
        reading — giving it a score means manufacturing attacks, which inflates n and makes a
        state read as proven. That is the exact cheat `_hardening_gap` exists to refuse."""
        try:
            import self_arming as SA
        except Exception:
            self.skipTest("self_arming unavailable")
        proves = getattr(SA, "PROVES", {}) or {}
        for bad in ("river.moving", "river.state", "the.river"):
            self.assertNotIn(bad, proves,
                             "%s was declared as a lock. The river's motion is a STATE the doctor "
                             "reads, not a claim attacks can refute." % bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
