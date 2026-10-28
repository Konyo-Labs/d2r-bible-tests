# -*- coding: utf-8 -*-
"""A FUNCTION THAT ANSWERS A QUESTION NOBODY ASKS IS NOT BUILT — IT IS DECORATION.

#100 bucketed 26 verdict-shaped functions: 6 to JOIN, 12 correctly unjoined, the rest unknown.
These are the last two of the six, and both had exactly ONE reference in the whole tree — their
own test. Written, reasoned, tested, and unreachable.

⚠⚠ AND IN BOTH CASES THE LIVE PATH CARRIED THE DEFECT THE FUNCTION WAS WRITTEN TO PREVENT.

`_chron_lane_detail()` says it in its docstring: *"The lane LIST is what the gate scores; this is
what a human is owed when grok is missing. 'You switched it off' and 'there is no Grok CLI here'
are different facts and only one of them is a problem."* Meanwhile BOTH sweep doors refused with a
flat *"the primary (Claude) lane is unavailable"* — the sentence that sends someone reinstalling a
CLI they had deliberately switched off. Measured on this machine the moment it was joined:
`grok: present=false, why="you switched it off (mode=off)"`.

`story_of(state)` says it too: *"A state this table does not know returns its own name rather than
a default … instead of quietly joining PENDING, which is exactly how a retired item comes back to
life."* Meanwhile the ONLY place states are resolved for the page indexed `_SEC[state]` directly
and raised KeyError.

[[plumbing-with-no-tap]] [[the-unjoined-end]] [[unknown-stays-unknown]]
"""
import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass


def _prod_callers(mod_file, fname):
    """Call sites of fname in a PRODUCTION module, excluding its own definition. -> int

    ⚠ COUNTED BY PARSING, not by grepping a name that also appears in prose. Several of these
    functions are named in comments explaining why they exist, and a comment is not a caller —
    that is the whole distinction this file is about. [[source-reading-guard]]
    """
    src = io.open(os.path.join(HERE, mod_file), encoding="utf-8").read()
    n = 0
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call):
            f = node.func
            name = getattr(f, "id", None) or getattr(f, "attr", None)
            if name == fname:
                n += 1
    return n


class AWrittenAnswerHasAReader(unittest.TestCase):

    def test_the_lane_detail_is_asked_by_production(self):
        n = _prod_callers("control_app.py", "_chron_lane_detail")
        self.assertGreaterEqual(
            n, 2,
            "_chron_lane_detail has %d production call site(s). Both sweep doors refuse when a "
            "lane is missing, and without it that refusal cannot say whether the lane is OFF or "
            "ABSENT — which is the only reason the function exists" % n)

    def test_the_refusal_carries_it(self):
        """Pinned on the refusal itself, because a call somewhere else would not help him."""
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        hits = src.count('"laneDetail": _chron_lane_detail()')
        self.assertEqual(
            2, hits,
            "%d of the 2 lane refusals carry laneDetail — a door that refuses without saying "
            "which kind of absent sends him reinstalling something he turned off" % hits)

    def test_story_of_is_asked_by_production(self):
        n = _prod_callers("board_sync.py", "story_of")
        self.assertGreaterEqual(
            n, 1,
            "story_of has no production caller, so the page resolves states by indexing _SEC "
            "directly — which raises KeyError on an unknown state instead of rendering it as the "
            "odd row a person notices")

    def test_an_unknown_state_is_rendered_not_filed(self):
        import board_sync as B
        title, order = B.story_of("a-state-nobody-added-here")
        self.assertIn("does not know", title,
                      "an unknown state no longer announces itself: %r" % title)
        self.assertNotEqual(-200, order,
                            "an unknown state took PENDING's section order — that is the quiet "
                            "filing this function exists to refuse, and how a retired item comes "
                            "back to life")

    def test_a_known_state_is_unchanged(self):
        """The opposite error: making unknowns loud must not disturb the seven real stages."""
        import board_sync as B
        self.assertEqual(("5 · COMPLETED", -120), B.story_of("done"))
        self.assertEqual(("1 · PENDING", -200), B.story_of("pending"))


class TheJoinReachesThePageNotJustTheNextLine(unittest.TestCase):
    """⚠⚠ v3219's JOINS WERE ONE HOP, AND A CROSS-FAMILY LOOK SAID SO.

    Grok, reviewing v3219: *"The production edits are a one-hop join (helper → dict / helper →
    next local). The hop that matters — dict → screen, helper → build() row — is still open, and
    the tests are… "* — and it was right on both counts:

      · `story_of` was called, and the SAME LOOP then did `order[state]`, keyed only from
        `SECTIONS`. So an unknown state stopped raising at `_SEC[state]` and raised one line down
        instead. The whole point of `story_of` is that an unknown state REACHES THE PAGE; it
        cannot reach a page the builder crashes before drawing.
      · the same lane refusal lived in `chronicle_sweep_now.py` too, still flat — so the person
        debugging from a terminal was the one left without the answer.

    ⚠ AND THE v3219 GATE COULD NOT SEE EITHER: `story_of >= 1 caller` was satisfied by the new
    line while `build()` still crashed. A gate that cannot fail on the defect it was written about
    is measuring the alphabet. [[review-after-ship]] [[copy-drift]] [[regression-guard]]
    """

    def setUp(self):
        self.bs = io.open(os.path.join(HERE, "board_sync.py"), encoding="utf-8").read()

    def test_the_section_counter_is_fail_open(self):
        """The line Grok named. `order` is keyed from SECTIONS; an unknown state must not KeyError."""
        i = self.bs.find('"order": order')
        self.assertGreater(i, 0, "the row no longer carries a section order at all")
        self.assertNotIn('"order": order[state]', self.bs,
                         "the row reads order[state] directly again — an unknown state raises "
                         "KeyError one line after story_of politely rendered it")
        self.assertNotIn("\n        order[state] += 1", self.bs,
                         "the counter increments order[state] directly again, which is the same "
                         "KeyError with a different line number")

    def test_the_counter_and_the_room_agree_on_failing_open(self):
        """`_ROOM.get(state, 40)` was ALWAYS fail-open; the counter beside it was not. One rule."""
        self.assertIn("_ROOM.get(state", self.bs,
                      "the room lookup stopped failing open — that was the working half")
        self.assertTrue("order.get(state" in self.bs or "order.setdefault(state" in self.bs,
                        "the section counter does not fail open while its neighbour does, which "
                        "is how an unknown state crashed a builder that had just been taught to "
                        "render it")

    def test_the_cli_refusal_carries_the_detail_too(self):
        """copy-drift: one refusal, two files, and v3219 joined only the one with an API."""
        cli = io.open(os.path.join(HERE, "chronicle_sweep_now.py"), encoding="utf-8").read()
        self.assertIn("the primary (Claude) lane is unavailable", cli,
                      "the CLI refusal moved — re-anchor this before assuming it was fixed")
        self.assertIn("_chron_lane_detail", cli,
                      "the CLI copy of the lane refusal still prints the flat sentence, so the "
                      "person debugging from a terminal cannot tell OFF from ABSENT")

RED_PROOF = [
    {"why": "an unknown storyline state is quietly filed as PENDING again, which is how a retired item comes back to life",
     "file": "tv/board_sync.py",
     "find": "    return (\"? · %s — a state the storyline does not know\" % str(state).upper(), -10)\n",
     "replace": "    return _SEC[\"pending\"][:2]\n",
     "matches": 1},
    {"why": "the vault sweep's lane refusal stops saying whether the lane is OFF or ABSENT, sending him to reinstall a CLI he turned off",
     "file": "tv/control_app.py",
     "find": "            return {\"ok\": False, \"laneMissing\": True,\n                    \"why\": \"the primary (Claude) lane is unavailable — nothing to sweep with\",\n                    \"lanes\": lanes, \"laneDetail\": _chron_lane_detail()}\n",
     "replace": "            return {\"ok\": False, \"laneMissing\": True,\n                    \"why\": \"the primary (Claude) lane is unavailable — nothing to sweep with\",\n                    \"lanes\": lanes}\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
