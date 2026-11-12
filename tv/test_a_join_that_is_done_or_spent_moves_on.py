# -*- coding: utf-8 -*-
"""REG-2004 - A JOIN THAT IS DONE, OR WHOSE ONE RE-READ IS SPENT, MOVES ON. #168, his 10-02 keep-16 ruling.

MEASURED on his Mac 2026-10-07 18:5x (read-only): the drain sat BLOCKED behind JOIN 9 (oldest 8.2 days), and the stuck
note printed reel_router.OWES's standing text - "the seal does not carry them. Code. No lane can fix that; an edit can"
- while #152 slice 4's join re-read lane had 3 queued and 16 tried. extract_gap ruled all 13 on-shelf JOIN reels
RECOVERABLE, and they split two ways:
  * 6 had seals frame_authority CERTIFIED (sealVerdict COVERED: name, location, provenance taken) - the RECOVERABLE
    branch never asked `_cert`, so a FINISHED join read as owed for ever;
  * 7 had their ONE re-read (0.5-21 h earlier) and the seal still recorded an empty examination - nothing could ever
    move them. His ruling: everything but the newest 16 (and the fixtures) is extracted, tallied and tombstoned FIFO,
    "no station may hold a reel for ever", JOIN included.
Applied by hand to his shelf the new rule moves all 13 (6 joined + 7 spent past the shield); none is left waiting.

WHAT THIS LAW DRIVES (real code each time):
  * extract_gap.gap(): a sealed, named, CERTIFIED reel is JOINED; the same reel uncertified is still RECOVERABLE;
  * reel_router._owes_of: JOINED owes nothing (the engine's word forwarded); RECOVERABLE still owes the join;
  * reel_route_lane.plan(): JOINED routes; a RECOVERABLE whose re-read is spent AND that sits past the newest-16
    shield routes; the same reel inside the shield, unspent, a fixture, or with spent/pinned unreadable WAITS;
  * control_app: _join_reread_spent is tried-minus-queued, _route_pinned_reels fails closed while the scan runs, the
    triage tick hands both to the lane, and the JOIN stuck note says the join lane's own state.
"""
import io
import os
import sys
import unittest
import unittest.mock as mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import control_app as CA  # noqa: E402
import extract_gap as EG  # noqa: E402
import frame_authority as FA  # noqa: E402
import reel_retention as RT  # noqa: E402
import reel_route_lane as LANE  # noqa: E402
import reel_router as RR  # noqa: E402

REEL = "reel_s_1500000000107_17"


def _gap(certified):
    sid = EG._session_of(REEL)
    with mock.patch.object(FA, "sealed_sessions", lambda *a, **k: ({sid: {"seal": 1}}, True)), \
            mock.patch.object(FA, "seal_covers_extraction", lambda seal: (certified, "the law's seal")), \
            mock.patch.object(FA, "seal_verdict", lambda seal: ("COVERED" if certified else "EMPTY", "the law's verdict")), \
            mock.patch.object(EG, "_named_sessions", lambda: ({sid: {"names": 5, "panel": 3}}, "")):
        rep = EG.gap(river={"rows": [{"reel": REEL}]})
    return [r for r in rep.get("rows") or [] if r.get("reel") == REEL][0]


def _shelf(n_newer, say):
    """REEL (oldest) at JOIN with `say`, plus `n_newer` newer EMPTY reels in front of it."""
    reels = [{"reel": REEL, "station": "JOIN", "extractSay": say, "why": "the law's join"}]
    for i in range(n_newer):
        reels.append({"reel": "reel_s_16%011d_%d" % (i + 1, i), "station": "EMPTY", "why": "newer"})
    return {"ok": True, "reels": reels, "shelf": len(reels)}


def _routed(rep, spent, pinned, shield=RT.recent_shield):
    return [r["reel"] for r in LANE.plan(rep, spent=spent, pinned=pinned, shield=shield)["route"] if r["from"] == "JOIN"]


class AJoinThatIsDoneOrSpentMovesOn(unittest.TestCase):

    def test_a_certified_seal_is_joined_and_an_uncertified_one_still_owes(self):
        self.assertEqual(_gap(certified=False)["state"], EG.RECOVERABLE, "premise: the uncertified baseline moved")
        self.assertEqual(_gap(certified=True)["state"], EG.JOINED,
                         "a seal that certifies name, location and provenance still reads as an owed join (REG-2004)")

    def test_the_router_says_a_joined_reel_owes_nothing(self):
        owed, why = RR._owes_of("JOIN", {"extractSay": EG.JOINED})
        self.assertEqual(owed, RR.NOTHING_OWED, "a JOINED reel still prints the standing 'Code.' gate: %s" % why)
        owed, _w = RR._owes_of("JOIN", {"extractSay": EG.RECOVERABLE})
        self.assertNotEqual(owed, RR.NOTHING_OWED, "an owed join was downgraded to nothing")

    def test_a_joined_reel_is_routed(self):
        self.assertEqual(_routed(_shelf(0, EG.JOINED), spent=set(), pinned=[]), [REEL])

    def test_a_spent_reread_past_the_shield_is_routed_and_inside_it_waits(self):
        past = _shelf(RT.KEEP_RECENT, EG.RECOVERABLE)          # 16 newer reels: REEL is outside the shield
        inside = _shelf(RT.KEEP_RECENT - 1, EG.RECOVERABLE)    # 15 newer: REEL is one of the newest 16
        self.assertEqual(_routed(inside, spent={REEL}, pinned=[]), [], "a reel inside the newest 16 lost its wait")
        self.assertEqual(_routed(past, spent={REEL}, pinned=[]), [REEL],
                         "a spent re-read past the shield has nowhere to go (REG-2004, his keep-16 ruling)")
        self.assertEqual(_routed(past, spent=set(), pinned=[]), [], "a join that never had its re-read was routed")

    def test_a_fixture_or_an_unreadable_set_never_routes(self):
        past = _shelf(RT.KEEP_RECENT, EG.RECOVERABLE)
        self.assertEqual(_routed(past, spent={REEL}, pinned=[REEL]), [], "a fixture reel was routed")
        self.assertEqual(_routed(past, spent=None, pinned=[]), [], "an unreadable re-read store routed a reel")
        self.assertEqual(_routed(past, spent={REEL}, pinned=None), [], "a fixture list still scanning routed a reel")
        self.assertEqual(_routed(past, spent={REEL}, pinned=[], shield=None), [], "no shield handed in routed a reel")

    def test_a_queued_join_whose_survey_found_no_panel_is_spent(self):
        """REG-3817 (his 11-13 ruling) - the work ALT's river stuck on joins whose re-read never ran under 1 GB free RAM"""
        import shelf_driver as SD
        with mock.patch.dict(CA._VAULT_AUTOREAD, {"joinTried": {REEL: 1, "reel_e": 2, "reel_b": 3},
                                                  "joinQueued": {"reel_e": 2, "reel_b": 3}}), \
                mock.patch.object(SD, "_proven_empty", lambda r: r == "reel_e"):
            spent = CA._join_reread_spent()
        self.assertIn("reel_e", spent, "a join whose survey found no panel still waits for a re-read that would read nothing")
        self.assertNotIn("reel_b", spent, "a join the survey could not prove empty was released without its re-read")
        self.assertIn(REEL, spent, "BASELINE: tried-and-not-queued is still spent")

    def test_the_console_builds_both_sets_and_the_join_note_is_the_lanes(self):
        with mock.patch.dict(CA._VAULT_AUTOREAD, {"joinTried": {REEL: 1, "reel_b": 2}, "joinQueued": {"reel_b": 2}}):
            self.assertEqual(CA._join_reread_spent(), {REEL}, "spent is not tried-minus-queued")
            why = CA._river_stuck_why("JOIN")
        self.assertIs(CA._route_shield_fn(), RT.recent_shield, "the tick does not hand the deleter's own shield")
        self.assertIn("the join lane: 1 queued for their one re-read, 1 have had it", why)
        self.assertNotIn("Code.", why, "the JOIN note still prints the gate's standing slogan")
        with mock.patch.object(FA, "test_referenced_reels_nowait", lambda: None):
            self.assertIsNone(CA._route_pinned_reels(), "a fixture scan still running read as 'no fixtures'")
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            code = "\n".join(l.split("#", 1)[0] for l in fh.read().split("\n"))
        self.assertEqual(code.count("spent=_join_reread_spent(), pinned=_route_pinned_reels(),"), 1,
                         "the triage tick no longer hands the route lane its spent and fixture sets")


RED_PROOF = [
    {"why": "REG-2004 - a certified seal reads RECOVERABLE again: a finished join is owed for ever",
     "file": "tv/extract_gap.py",
     "find": "        elif has_seal and n and _cert:\n",
     "replace": "        elif False:\n",
     "matches": 1},
    {"why": "REG-2004 - the router prints the standing 'Code.' gate for a JOINED reel",
     "file": "tv/reel_router.py",
     "find": '    if say == "JOINED":\n',
     "replace": '    if say == "JOINED-NEVER":\n',
     "matches": 1},
    {"why": "REG-2004 - the route lane never routes a JOINED reel",
     "file": "tv/reel_route_lane.py",
     "find": "            if _say in (_hold, _done):\n",
     "replace": "            if _say == _hold:\n",
     "matches": 1},
    {"why": "REG-2004 - a spent re-read never leaves JOIN: the dam is back",
     "file": "tv/reel_route_lane.py",
     "find": "            elif _say == _rec and r.get(\"reel\") in _spent:\n",
     "replace": "            elif False:\n",
     "matches": 1},
    {"why": "REG-2004 - the newest-16 shield is ignored, so a reel he can still see is routed on its spent re-read",
     "file": "tv/reel_route_lane.py",
     "find": "    return set(str(r) for r in reels if str(r) in spent and str(r) not in shield and str(r) not in pin)\n",
     "replace": "    return set(str(r) for r in reels if str(r) in spent and str(r) not in pin)\n",
     "matches": 1},
    {"why": "REG-2004 - a fixture list still scanning reads as 'no fixtures', so a fixture reel can be routed",
     "file": "tv/reel_route_lane.py",
     "find": "    if spent is None or pinned is None or not callable(shield):\n",
     "replace": "    if spent is None or not callable(shield):\n",
     "matches": 1},
    {"why": "REG-2004 - the JOIN stuck note goes back to the gate's 'No lane can fix that' slogan",
     "file": "tv/control_app.py",
     "find": "        if _jq is not None and _js is not None:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3817 - a queued join whose survey found no panel waits forever for a re-read that would read nothing",
     "file": "tv/control_app.py",
     "find": "        spent |= set(str(r) for r in queued if _sd_spent._proven_empty(r))\n",
     "replace": "        pass\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
