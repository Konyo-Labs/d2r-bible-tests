# -*- coding: utf-8 -*-
"""v3342 (#93) — A RIDER IS WATCHED WITHOUT CLAIMING A THREAD.

`tvd-read-names-feeder` shipped in v3323 with its own lane name and its own lifetime counters, and
NOTHING has surfaced it since. His #28 ruling was explicit — the feeder gets "built AND watched in
the same version, never the watch alone" — and v3323 shipped the build and broke the watch in the
same stroke.

THE CAUSE, MEASURED, AND IT WAS NOT A MISSING FEATURE:

    _lane_stamps(control_app.py):
        strings            21   tvd-read-names-feeder PRESENT      <- the stamp was always SEEN
        tick_by_encloser   21   no encloser maps to it             <- and always DISCARDED

    ast over the live source — defs that stamp more than one lane: exactly ONE
        def _vault_autoread_loop
            line 24289   tvd-vault-autoread
            line 24311   tvd-read-names-feeder
        tick_by_encloser['_vault_autoread_loop'] = 'tvd-vault-autoread'   <- setdefault kept the first

A `{def: ONE stamp}` map cannot hold a loop that beats for two lanes, so the second was parsed at
every census and dropped on the floor. [[one-to-one-store-for-a-one-to-many-fact]]

⚠ AND A LAW WAS SHOUTING ABOUT IT THE WHOLE TIME. test_every_lane_stamps_its_own_beat asserted
`exactly one` beat per def and has been RED in CI on every run since v3323 —
`['tvd-vault-autoread (_vault_autoread_loop) stamps 2'] != []` — for EIGHTEEN versions. A
permanently-red gate stops carrying information, and this is what that costs. [[regression-guard]] §2

WHY A RIDER AND NOT A VESSEL. The census enumerates THREADS (LOOP 20 / TASK 10 / FOREIGN 2) and the
feeder has none — it runs inside vault-autoread's tick. heart.py's NOT_A_VESSEL says one-shot work
"inherits its caller's vessel" because "giving each its own would make the roster claim more runs
without you than there are", and that reasoning is sound and is NOT overruled here. But a rider is
not nothing either: it has its own name, its own counters, and its own reason to exist — v3323 kept
the names apart deliberately, because the tick it rides SPENDS money on paid sweeps while the feeder
banks names already read and costs nothing, so "one supervisor row must never answer for two lanes".

So: a third shelf. Supervised on its own row, counted in nobody's vessel total, NAMING the vessel it
rides. [[heart-first]] [[the-unjoined-end]] [[unknown-stays-unknown]]
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import lane_census as LC  # noqa: E402


class TestARiderIsWatchedWithoutClaimingAThread(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = LC.census()
        cls.riders = [r for r in cls.rows if r.get("kind") == "RIDER"]

    # ── the root cause ────────────────────────────────────────────────────────────────────────
    def test_the_stamp_map_keeps_every_beat_a_def_makes(self):
        """BEHAVIOURAL. setdefault kept the FIRST and the feeder's beat never survived the parse."""
        import io
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        tb = LC._lane_stamps(src)["tick_by_encloser"]
        self.assertTrue(tb, "the stamp map is empty — nothing below means anything")
        multi = {fn: n for fn, n in tb.items() if isinstance(n, (list, tuple)) and len(n) > 1}
        self.assertTrue(
            multi,
            "no def maps to MORE THAN ONE stamp. Either the map went back to holding a single "
            "name per def — which is the defect that hid tvd-read-names-feeder for 18 versions — "
            "or every value is a bare string again. Got: %r" % (list(tb.items())[:2],))
        self.assertIn(
            "tvd-read-names-feeder", [s for v in multi.values() for s in v],
            "the feeder's beat is not among the stamps any def keeps, so nothing can surface it.")

    # ── the rider row ─────────────────────────────────────────────────────────────────────────
    def test_the_census_emits_a_rider_for_the_extra_beat(self):
        """The feeder must reach the census as its own row, not as a second name on someone else's."""
        # #91 (2026-09-30) — the loop now carries a SECOND rider, the character learner, with its own name and its
        # own counters for the same reason the feeder has them: one supervisor row must never answer for two jobs.
        # v3890 (#184) - and a THIRD, the chronicle line lane (tv/chronicle_line.py): its own name and its own ledger.
        self.assertEqual(
            sorted(r.get("lane") for r in self.riders), ["tvd-char-learner", "tvd-chronicle-lines", "tvd-read-names-feeder"],
            "expected exactly the three RIDER rows on this tree and got %d. Measured: precisely one def "
            "(_vault_autoread_loop) stamps four lanes. %r"
            % (len(self.riders), [r.get("lane") for r in self.riders]))

    def test_a_rider_names_the_vessel_it_rides(self):
        """⚠ LOAD-BEARING. A row that claims a lane without saying whose thread carries it is the
        roster claiming more runs than there are — exactly what NOT_A_VESSEL exists to prevent."""
        self.assertTrue(self.riders, "no rider rows at all — nothing below means anything")
        for r in self.riders:
            self.assertEqual(
                r.get("rides"), "tvd-vault-autoread",
                "the rider %s does not name the vessel it rides (%r), so a reader cannot tell whether it "
                "runs at all or what would have to be alive for it to run." % (r.get("lane"), r.get("rides")))
            self.assertTrue(r.get("supervised"), "a rider with a heartbeat is supervised")
            self.assertEqual(r.get("credit"), "heartbeat",
                             "a rider is credited by its BEAT, not by a roster row it does not have")

    def test_a_lane_with_one_beat_produces_no_rider(self):
        """⚠ THE BASELINE, and without it this law would pass over a census that riders everything.
        [[regression-guard]] §5 — a case that cannot fail is measuring the fixture."""
        lanes_with_riders = set(r.get("fn") for r in self.riders)
        self.assertNotIn(
            "_drift_loop", lanes_with_riders,
            "a single-stamp lane grew a rider, so 'rider' has stopped meaning 'an extra beat'.")
        self.assertLess(
            len(self.riders), len([r for r in self.rows if r.get("kind") == "LOOP"]),
            "there are at least as many riders as vessels, which cannot be right on this tree.")

    # ── the join: a rider nobody counts and nobody shows is still invisible ───────────────────
    def test_a_rider_is_not_counted_as_a_vessel(self):
        """⚠⚠ THE ONE THAT MATTERS. The first cut of this change DID count it: vessels went 20 -> 21
        with the rider reported UNKNOWN, which is a thread claimed that does not exist."""
        import heart as H
        rep = H.vessels()
        kinds = set(str(v.get("kind")) for v in (rep.get("vessels") or []))
        self.assertNotIn(
            "RIDER", kinds,
            "a RIDER appears among the vessels. It owns no thread; counting it inflates the roster "
            "and is the lie heart.NOT_A_VESSEL exists to prevent.")
        c = rep.get("counts") or {}
        self.assertEqual(
            c.get("UNKNOWN"), 0,
            "a vessel is UNKNOWN (%r) — a rider leaking into the vessel loop lands exactly there, "
            "because the census kind is not LOOP." % (c.get("UNKNOWN"),))

    def test_the_heart_shows_riders_on_their_own_shelf(self):
        """A correct census row that no surface reads leaves the feeder exactly as hidden as before."""
        import heart as H
        rep = H.vessels()
        self.assertIn(
            "riders", rep,
            "heart.vessels() has no `riders` key, so the rider is computed and thrown away — the "
            "same fate the feeder's own beat had for 18 versions. [[the-unjoined-end]]")
        names = [str(x.get("name")) for x in (rep.get("riders") or [])]
        self.assertIn(
            "tvd-read-names-feeder", names,
            "the feeder is not on the heart's rider shelf (%r). His #28 asked for it to be BUILT "
            "AND WATCHED; this is the watched half." % (names,))

    # ── v3343: the last two hops. A shelf the route drops and the screen never reads ──────────
    def test_the_route_forwards_riders_to_the_screen(self):
        """⚠⚠ v3342 STOPPED HERE AND THIS LAW LET IT. It asserted `riders` exists in
        heart.vessels() and went no further — at exactly the boundary this repo's most repeated
        defect lives on. heart_state() hand-picks its keys, so the rider was computed and dropped
        one hop later: the same fate its own beat had for 18 versions, moved along by one layer."""
        import io as _io, os as _os, re as _re
        with _io.open(_os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            raw = fh.read()
        code = "\n".join(_re.sub(r"#.*$", "", l) for l in raw.split("\n"))
        self.assertIn(
            '"riders": rep.get("riders")', code,
            "the /api/heart route does not forward `riders`, so heart.vessels() computes the rider "
            "and nothing downstream ever receives it. Comments are stripped before this check "
            "because the line above it explains exactly this. [[the-unjoined-end]]")

    def test_the_console_actually_renders_the_rider(self):
        """⚠ A forwarded key no screen reads is the same invisibility, one hop further along.
        ANCHORED ON THE LIVE EXPRESSION, never the bare word `riders` — that appears in the comment
        explaining the line, and a positive assertion satisfied by its own comment passes GREEN,
        which is the quiet direction. [[source-reading-guard]] §4b"""
        import io as _io, os as _os
        from frame_authority import _executable_only
        with _io.open(_os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            raw = fh.read()
        body = _executable_only(raw, ".js")
        self.assertGreater(
            float(len(body)) / max(1, len(raw)), 0.50,
            "the comment strip kept only %.1f%% of control_ui.html — every count below is "
            "meaningless. [[zero-needs-a-denominator]]" % (100.0 * len(body) / max(1, len(raw))))
        # ⚠⚠ ANCHOR ON THE WHOLE LIVE CONDITION, NOT THE NAME. A first cut asserted `"d.riders" in
        # body` and came back BLIND with a CORRECT match count of 1: the sabotage
        # `(d.riders && d.riders.length)` -> `(false && d.riders.length)` disables the render while
        # LEAVING the substring `d.riders` in place, so the guard was satisfied by a fragment that
        # outlives the thing it guards. That is the law being weak, not the sabotage being wrong —
        # the one case where a correct count does mean rewrite the law.
        # [[regression-guard]] §5a [[source-reading-guard]] §4c
        self.assertIn(
            "d.riders && d.riders.length", body,
            "the heart panel does not GUARD on d.riders before rendering, so either the rider is "
            "never drawn or an empty list prints an empty parenthetical. His #28 asked for the "
            "feeder to be WATCHED, and watched means it reaches HIS SCREEN.")
        self.assertIn(
            "d.riders.map(", body,
            "the panel never maps over the riders, so no rider is named on screen — a count with "
            "no names cannot say WHICH lane is riding or what it rides.")
        self.assertIn(
            "rides", body,
            "the rendered sentence does not name what each rider RIDES, so it reads as a lane with "
            "a thread of its own — the claim heart.NOT_A_VESSEL exists to prevent.")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        # ⚠ THE FIRST CUT OF THIS PROOF WAS INERT, AND THE MATCH COUNT WAS RIGHT (1). It changed
        # `setdefault(stack[-1], [])` to `setdefault(stack[-1], [nm])`, which produces the IDENTICAL
        # map: on the first call the default list already holds nm so the append is skipped, and on
        # every later call setdefault returns the EXISTING list and the default is never evaluated.
        # Verdict came back BLIND, and a correct count with a green law usually means a weak law —
        # here it meant an inert sabotage. Measured both shapes side by side before touching the
        # law. [[regression-guard]] §5a — suspect the sabotage. [[source-reading-guard]] §4d
        "why": "keeping only the first stamp puts the feeder back where it sat for 18 versions",
        "file": "tv/lane_census.py",
        "find": "                    if nm not in _seen:",
        "replace": "                    if not _seen:",
        "matches": 1,
    },
    {
        "why": "dropping the rider emission leaves the extra beat parsed and discarded",
        "file": "tv/lane_census.py",
        "find": '            if _extra == _own:',
        "replace": '            if True:',
        "matches": 1,
    },
    {
        "why": "counting a rider as a vessel claims a thread it does not have - vessels 20 becomes 21",
        "file": "tv/heart.py",
        "find": '        if kind == "RIDER":',
        "replace": '        if False:',
        "matches": 1,
    },
    {
        "why": "removing the riders shelf makes a correct census row reach no surface at all",
        "file": "tv/heart.py",
        "find": '        "riders": riders,',
        "replace": '        "ridersX": riders,',
        "matches": 1,
    },
    {
        "why": "the route dropping the key is exactly where v3342 stopped - computed, then discarded",
        "file": "tv/control_app.py",
        "find": '        "riders": rep.get("riders") or [],',
        "replace": '        "ridersX": rep.get("riders") or [],',
        "matches": 1,
    },
    {
        "why": "a key the screen never reads is the same invisibility one hop further along",
        "file": "tv/control_ui.html",
        "find": "      + _hrtEsc((d.riders && d.riders.length)",
        "replace": "      + _hrtEsc((false && d.riders.length)",
        "matches": 1,
    },
]
