# -*- coding: utf-8 -*-
"""v3312 (#65/#66) — EVERY SURFACE CAN SAY WHICH DOOR OPENED A REEL, AND UNKNOWN STAYS UNKNOWN.

Konyo: *"the shadow reels that get shadow recorder they too need to be within the river and seen
visually just like the others"*.

⚠⚠ THE FIRST HALF WAS ALREADY TRUE AND IT TOOK THREE WRONG INSTRUMENTS TO ESTABLISH THAT.
Shadow reaches its reel THROUGH `start_agent` (control_app.py:24134), so a shadow reel is an
ordinary reel — same hist dir, same index, same seal — and nothing in shelf_driver / river /
river_walk / reel_retention filters by door. They have always flowed every joint.

WHAT WAS MISSING IS THAT NO SURFACE COULD SAY WHICH ONES THEY WERE. river.py mentioned `door`
ZERO times. So shadow flowed INVISIBLY and "shadow contributed N" had no answer — which is exactly
how an evening of play producing ZERO shadow reels stayed hidden until he noticed the absence
himself (control_app.py:5887, corroborate.py:364).

MEASURED on tv/sessions.jsonl (5,169 rows): shadow 761 · onair 759 · mini 2, with 1,522 rows
carrying BOTH `sessionId` and `door`. Of his 19 reels: onair 7 · shadow 1 · **11 with no door row
at all**, because they predate the stamp.

⚠⚠ THOSE 11 ARE UNKNOWN AND MUST NEVER BECOME "onair". Absence of a record is not evidence of the
common case, and a manufactured provenance is worse than a missing one because nothing can tell it
apart from a real one afterwards. [[unknown-stays-unknown]] [[manual-tally-is-witness]]

⚠ ONE READER, NOT TWO. The river and the shelf both need this and v3308 is the standing lesson: the
eagle partition was written twice, drifted within an hour, and the screen said 9 while the engine
said 7. `reel_door` is the single definition. [[copy-drift]]

── #66, THE SAME THREAD ─────────────────────────────────────────────────────────────────────────
Pressing ON AIR while SHADOW rolls used to answer "already on air" — true about a reel, misleading
about WHOSE, and the reply carried `mode` while omitting the door. There is NO race: shadow refuses
to start on top of anything, and this branch spawns nothing. The defect was the SENTENCE.
⚠ It must keep refusing nothing and killing nothing: the fold runs at seal (v2071), so pre-empting
a rolling reel ORPHANS its frames.

── v3859, ELAD'S RULING 2026-11-03 17:26 IDT ──────────────────────────────────────────────────────
"when clicking ONAIR it should just say already airing". The v3312 sentence ("a SHADOW reel is
already rolling ... stop it first") is retired: the shadow reader is always on now, so there is no
"stop it first" to offer. Pressing ON AIR over ANY rolling reel (shadow, mini or hand) says exactly
"already airing" - no second reel, nothing stopped, the rolling reel's door unchanged - and the
reply still carries door/askedFor/doorMatches for the record. DRIVEN, not just grepped, below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import reel_door as rd                                   # noqa: E402


class TestAReelSaysWhichDoorOpenedIt(unittest.TestCase):

    # ── the reader ───────────────────────────────────────────────────────────────────────────
    def test_a_doorless_reel_is_UNKNOWN_and_never_the_common_door(self):
        """⚠ THE ONE THAT MATTERS. 11 of his 19 reels predate the stamp."""
        dmap = {"s_1": "shadow", "s_2": "onair"}
        self.assertIsNone(
            rd.door_of("reel_s_999", dmap),
            "a reel with no door row resolved to a door. Absence of a record is not evidence of "
            "the common case, and once invented the provenance cannot be told from a real one.")
        counts = rd.split(["reel_s_1", "reel_s_2", "reel_s_999", "reel_s_998"], dmap)
        self.assertEqual(
            counts.get("unknown"), 2,
            "doorless reels were not counted as unknown: %r. Folding them into a door is "
            "manufacturing provenance." % (counts,))
        self.assertEqual(counts.get("shadow"), 1)
        self.assertEqual(counts.get("onair"), 1)

    def test_an_unreadable_journal_is_UNKNOWN_not_an_empty_map(self):
        """A journal that cannot be read must not read as 'no reel has a door'."""
        m, why = rd.door_map(os.path.join(HERE, "_no_such_journal_.jsonl"))
        self.assertEqual(m, {})
        self.assertTrue(why, "an unreadable journal returned an empty map with NO reason, so the "
                             "caller cannot tell 'nobody recorded a door' from 'nobody could "
                             "look'. [[zero-needs-a-denominator]]")
        self.assertIn("not on this machine", why)

    def test_the_say_line_names_the_unknowns_out_loud(self):
        s = rd.say({"onair": 7, "shadow": 1, "unknown": 11})
        self.assertIn("shadow 1", s)
        self.assertIn("11 UNKNOWN", s,
                      "the summary hides the unattributed reels, so a reader would take 8 as the "
                      "whole population: %r" % s)
        self.assertIn("not assumed onair", s,
                      "the line does not say WHY they are unknown, so the next reader may fill "
                      "them in: %r" % s)

    # ── the river ────────────────────────────────────────────────────────────────────────────
    def test_the_river_reports_the_split_and_never_dies_on_it(self):
        import river
        rows = river.trace()
        cap = [r for r in rows if r.get("joint") == "capture"]
        self.assertTrue(cap, "the river has no capture joint")
        cap = cap[0]
        self.assertIn(
            "doorsSay", cap,
            "the capture joint carries no door split, so the river still cannot say how many "
            "reels came by the shadow door — which is the whole of his ask.")
        self.assertTrue(str(cap.get("doorsSay") or "").strip(),
                        "doorsSay is empty; an empty string is not a reading")
        # ⚠ the split is DECORATION on a joint that graded itself. It must never change the grade.
        self.assertIn(cap["state"], ("carries", "dry", "unbuilt", "unknown", "CARRIES", "DRY",
                                     "UNBUILT", "UNKNOWN"),
                      "the capture joint's state is no longer a known verdict: %r" % cap["state"])

    def test_a_machine_with_NO_history_still_says_the_split_is_unknown(self):
        """⚠ #123 — DRIVEN on the branch every CI runner takes. j_capture's early return skipped the
        door split, so the key VANISHED where there is no history — red on CI, green on his Mac,
        same commit. A missing field reads as a dropped one; an UNKNOWN sentence reads as measured."""
        import river
        real = river._hist_dir
        river._hist_dir = lambda *a, **k: None
        try:
            cap = river.j_capture()
        finally:
            river._hist_dir = real
        self.assertEqual(str(cap.get("state")).upper(), "UNKNOWN",
                         "premise: with no history the capture joint must grade UNKNOWN: %r" % cap)
        self.assertIn("doorsSay", cap, "the door split vanished on a machine with no history")
        self.assertIn("UNKNOWN", cap.get("doorsSay") or "",
                      "the split on a no-history machine does not say it is UNKNOWN: %r"
                      % cap.get("doorsSay"))

    # ── #66, the reply ───────────────────────────────────────────────────────────────────────
    def test_the_already_rolling_reply_names_the_door(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn(
            '"door": _rolling, "askedFor": _asked, "doorMatches": _same', src,
            "the already-rolling reply does not carry the door, so pressing ON AIR under a SHADOW "
            "reel is answered 'already on air' with nothing explaining why the session is stamped "
            "shadow. The reply carried `mode` and omitted the one field that mattered.")
        self.assertIn(
            "_rolling = _door_of_origin(_agent_origin)", src,
            "the reply maps origin->door inline instead of calling _door_of_origin, whose own "
            "docstring says the two vocabularies are 'joined HERE and nowhere else'. A second "
            "mapping is how the pair drifts until one side grows a fourth value. [[copy-drift]]")
        self.assertNotIn(
            "stop_agent(farewell=False)\n            return {\"ok\": True, \"msg\": \"a %s reel", src,
            "the reply now STOPS a rolling reel. It must refuse nothing and kill nothing: the fold "
            "runs at seal, so pre-empting a rolling reel orphans its frames.")

    # ── v3859, the reply is "already airing" whoever opened the reel ──────────────────────────
    def _drive_on_air_over(self, rolling_origin, asked_origin="hand"):
        import control_app as ca
        stops, spawns = [], []

        class _Alive(object):
            pid = 4242
            def poll(self):
                return None
        saved = {k: getattr(ca, k) for k in ("_stop_inflight", "_agent_adoptable", "_agent_alive",
                 "_port_listener_pid", "_agent_proc", "_agent_adopted_pid", "_agent_origin",
                 "_agent_mode", "_bridge_ping", "stop_agent", "_kill_pid")}
        saved_popen = ca.subprocess.Popen
        try:
            ca._stop_inflight = False
            ca._agent_adoptable = lambda *a, **k: None
            ca._agent_alive = lambda *a, **k: True
            ca._port_listener_pid = lambda *a, **k: 4242
            ca._agent_proc = _Alive()
            ca._agent_adopted_pid = None
            ca._agent_origin = rolling_origin
            ca._agent_mode = "live"
            ca._bridge_ping = lambda *a, **k: {"ok": True}
            ca.stop_agent = lambda *a, **k: stops.append((a, k))
            ca._kill_pid = lambda *a, **k: stops.append(("kill", a))
            ca.subprocess.Popen = lambda *a, **k: spawns.append(a) or (_ for _ in ()).throw(
                AssertionError("a second reel was spawned"))
            r = ca.start_agent(origin=asked_origin)
            after_origin = ca._agent_origin
        finally:
            ca.subprocess.Popen = saved_popen
            for k, v in saved.items():
                setattr(ca, k, v)
        return r, stops, spawns, after_origin

    def test_on_air_over_any_rolling_reel_says_only_already_airing(self):
        for rolling, door in (("shadow", "shadow"), ("mini", "mini"), ("hand", "onair")):
            r, stops, spawns, after = self._drive_on_air_over(rolling)
            self.assertEqual(r.get("msg"), "already airing",
                             "ON AIR over a rolling %s reel did not just say 'already airing': %r"
                             % (rolling, r))
            self.assertNotIn("stop it first", str(r), "the retired v3312 sentence is back: %r" % r)
            self.assertTrue(r.get("ok"), r)
            self.assertEqual(stops, [], "ON AIR stopped a rolling %s reel: %r" % (rolling, stops))
            self.assertEqual(spawns, [], "ON AIR spawned a second reel over %s" % rolling)
            self.assertEqual(after, rolling, "the rolling reel's door was rewritten mid-reel")
            self.assertEqual(r.get("door"), door, r)
            self.assertEqual(r.get("askedFor"), "onair", r)
            self.assertEqual(r.get("doorMatches"), door == "onair", r)

    def test_on_air_over_a_mini_countdown_says_already_airing(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index('        if path == "/api/on":')
        blk = src[i:src.index("_pre_on = capture_preflight", i)]
        self.assertIn('"msg": ALREADY_AIRING', blk,
                      "ON AIR during a MINI countdown no longer says 'already airing'")
        self.assertNotIn("seal the current session first", blk,
                         "ON AIR during a MINI countdown still tells him to seal first")
        self.assertIn('ALREADY_AIRING = "already airing"', src)


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "resolving a doorless reel to a door manufactures provenance that was never recorded",
        "file": "tv/reel_door.py",
        "find": "    return (dmap or {}).get(sid)",
        "replace": '    return (dmap or {}).get(sid, "onair")',
        "matches": 1,
    },
    {
        "why": "folding unknown into a door hides the 11 reels that predate the stamp",
        "file": "tv/reel_door.py",
        "find": '            out["unknown"] += 1',
        "replace": '            out["onair"] = out.get("onair", 0) + 1',
        "matches": 1,
    },
    {
        "why": "a say line that drops the unknown count lets a reader take 8 as the whole population",
        "file": "tv/reel_door.py",
        "find": '        head += " · %d UNKNOWN (recorded before the door stamp; not assumed onair)" % unk',
        "replace": '        head += ""',
        "matches": 1,
    },
    {
        "why": "dropping the door from the already-rolling reply restores the misleading answer",
        "file": "tv/control_app.py",
        "find": '                    "door": _rolling, "askedFor": _asked, "doorMatches": _same,',
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#123 - the no-history early return drops the door split again: the key vanishes on every CI runner and a reader cannot tell 'unknown' from 'dropped'",
        "file": "river.py",
        "find": "        j[\"doors\"], j[\"doorsSay\"] = None, (\"which door opened each reel is UNKNOWN — there is no \"\n                                           \"history directory to split\")\n",
        "replace": "",
        "matches": 1
    },
    {
        "why": "v3859 - the retired v3312 sentence comes back for a reel another door opened",
        "file": "tv/control_app.py",
        "find": '                    "msg": ALREADY_AIRING,\n',
        "replace": '                    "msg": (ALREADY_AIRING if _same else "a %s reel is already rolling - stop it first" % _rolling),\n',
        "matches": 1
    },
    {
        "why": "v3859 - ON AIR pre-empts the rolling reel instead of only saying already airing",
        "file": "tv/control_app.py",
        "find": "            _same = (_rolling == _asked)\n",
        "replace": "            _same = (_rolling == _asked)\n            stop_agent(farewell=False)\n",
        "matches": 1
    },
    {
        "why": "v3859 - the rolling reel's door is rewritten to whoever pressed ON AIR",
        "file": "tv/control_app.py",
        "find": "            _same = (_rolling == _asked)\n",
        "replace": "            _same = (_rolling == _asked)\n            _agent_origin = origin\n",
        "matches": 1
    },
    {
        "why": "v3859 - ON AIR during a MINI countdown tells him to seal first again",
        "file": "tv/control_app.py",
        "find": '                self._json(200, {"ok": False, "mode": "mini", "msg": ALREADY_AIRING,',
        "replace": '                self._json(200, {"ok": False, "mode": "mini", "msg": "seal the current session first",',
        "matches": 1
    },
]
