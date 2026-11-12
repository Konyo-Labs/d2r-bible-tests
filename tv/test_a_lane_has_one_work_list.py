# -*- coding: utf-8 -*-
"""v3295 — A LANE HAS ONE WORK LIST, AND EVERY INSTRUMENT READS THAT ONE.

The vault lane's work list is `OWED_BY ∩ READ_CLEARS`. That expression was written out by hand in
THREE separate places, and the copies drifted:

  · control_app._vault_autoread_candidates  — correct since v2878
  · control_app's "awaiting a sweep" count  — correct, with its own UNKNOWN policy
  · river_walk's PRINTER probe              — STALE: counted the single tag `vault-owes`

So the river printed *"the lane's queue is EMPTY: ... this reel waits for a seal nothing will
write"* while the lane was in fact holding 3 `panels-never-banked` reels. An instrument and the
thing it measures disagreeing about what the lane is FOR — and the instrument was the one being
believed, because it is the one that renders.

⚠ THE THIRD COPY WAS FOUND BY THE GREP THAT WROTE THIS LAW, NOT BY THE INVESTIGATION. Two copies
were known when the fix started; the sweep for "is anyone else recomputing this" turned up a third.
That is the argument for the STRUCTURAL half below: a law that only checked the two known callers
would have shipped green over the third. [[copy-drift]] [[the-unjoined-end]]

TWO HALVES, and they fail for different reasons on purpose:

  1. STRUCTURAL — no production module iterates `OWED_BY.items()` at all. The single definition is
     `shelf_driver.lane_read_tags(lane)`. This is deliberately stricter than "don't duplicate the
     intersection": ANY hand-rolled walk of that map is a future copy waiting to drift, and the
     cheap way to keep one definition is to make the map's iteration itself off-limits outside its
     own module.

  2. BEHAVIOURAL — the set actually contains the tag whose absence caused this. Asserting the
     structure alone would go green over a `lane_read_tags` that returned the wrong set, which is
     the same defect one layer down. [[presence-law-vs-reachability-law]]

⚠ THIS LAW STRIPS COMMENTS BEFORE READING (frame_authority._executable_only). Load-bearing: the
modules under test carry comments that spell out `OWED_BY ∩ READ_CLEARS` in prose to explain the
rule, and a law reading raw source would fail on its own documentation. That is REG-1070.

⚠ TEST FILES ARE EXEMPT BY DESIGN. A law that pinned `lane_read_tags` by CALLING it would be
circular — it would agree with whatever the function returned. The laws that check this set
recompute it independently on purpose, and that is the only correct way for them to disagree.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# Its docstrings and failure messages carry non-ASCII, and a unittest failure PRINTS them. On a
# cp1255 console that crash happens while REPORTING, so a clean tree exits non-zero for a reason
# that has nothing to do with the law. Caught by test_control's encoding-safety gate.
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

from frame_authority import _executable_only  # noqa: E402

#: The one module allowed to walk the map: it is where the map lives.
OWNER = "shelf_driver.py"

#: A hand-rolled walk of the tag->lane map. This is the shape that drifted three ways.
WALKS_THE_MAP = re.compile(r"OWED_BY\s*\.\s*items\s*\(")


def _production_modules():
    """Every shipped .py in tv/ except the map's owner and the laws. Sorted, for a stable report."""
    out = []
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".py"):
            continue
        if name == OWNER or name.startswith("test_"):
            continue
        out.append(name)
    return out


class TestALaneHasOneWorkList(unittest.TestCase):

    def test_no_production_module_walks_the_tag_map(self):
        """STRUCTURAL: only shelf_driver iterates OWED_BY; everyone else calls lane_read_tags."""
        offenders = []
        scanned = 0
        for name in _production_modules():
            path = os.path.join(HERE, name)
            try:
                with io.open(path, encoding="utf-8") as fh:
                    src = fh.read()
            except Exception:
                continue
            scanned += 1
            # REG-3796 - the real path, never ".js": the JavaScript branch strips /* */ and // but never #, and a
            # slash-star in a string ran to the next star-slash - 45% of console_doctor.py was invisible to this scan.
            body = _executable_only(src, path)   # REG-3796 - the real .py path: comments AND docstrings go, # included
            for m in WALKS_THE_MAP.finditer(body):
                line = body[:m.start()].count("\n") + 1
                offenders.append("%s (stripped line %d)" % (name, line))

        # A zero needs a denominator: if nothing was scanned the clean result is meaningless.
        self.assertGreater(
            scanned, 10,
            "only %d production modules were scanned — this law measured almost nothing, so its "
            "PASS is not evidence. [[zero-needs-a-denominator]]" % scanned)

        self.assertEqual(
            offenders, [],
            "%d production module(s) walk OWED_BY by hand instead of calling "
            "shelf_driver.lane_read_tags(): %s\n"
            "That is the copy that drifted in v3295 — river_walk counted only `vault-owes` and "
            "printed 'the lane's queue is EMPTY' while the lane held 3 panels-never-banked reels. "
            "One definition, or the copies disagree about what the lane is for."
            % (len(offenders), ", ".join(offenders)))

    def test_the_vault_work_list_still_holds_the_tag_that_was_dropped(self):
        """BEHAVIOURAL: structure alone would go green over a function returning the wrong set."""
        import shelf_driver as sd

        tags = sd.lane_read_tags("vault")

        self.assertIn(
            "panels-never-banked", tags,
            "the vault lane's work list has lost `panels-never-banked` — the exact tag whose "
            "absence made river_walk report an EMPTY queue while 3 reels waited in it.")
        self.assertIn(
            "vault-owes", tags,
            "the vault lane's work list has lost `vault-owes`.")

        # v2878's ruling, and it is a REFUSAL rather than an omission: the sweep already ran and
        # produced rows, so what is missing is a durable BANK. Queuing it spends paid reads, the
        # hold does not clear, and the reel retires as "still owed" having banked nothing.
        self.assertNotIn(
            "rows-not-banked", tags,
            "`rows-not-banked` is back in the vault lane's READ list. It is owed a BANK, not a "
            "READ — queuing it spends his money and clears nothing. [[v2878]]")

        # The lane must not be able to answer for a lane that does not exist.
        self.assertEqual(
            set(sd.lane_read_tags("no-such-lane")), set(),
            "lane_read_tags() answered for a lane that does not exist, so a typo'd lane name "
            "would read as a real lane owning nothing.")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "putting river_walk's inline recomputation back re-creates the copy that drifted",
        "file": "tv/river_walk.py",
        "find": '            _tags = _sd.lane_read_tags("vault")',
        "replace": ('            _tags = frozenset(t for t, _ln in _sd.OWED_BY.items()\n'
                    '                              if _ln == "vault" and t in _sd.READ_CLEARS)'),
        "matches": 1,
    },
    {
        "why": "narrowing the one definition back to a single tag drops panels-never-banked again",
        "file": "tv/shelf_driver.py",
        "find": ('    return frozenset(t for t, owner in OWED_BY.items()\n'
                 '                     if owner == lane and t in READ_CLEARS)'),
        "replace": ('    return frozenset(t for t, owner in OWED_BY.items()\n'
                    '                     if owner == lane and t == "vault-owes")'),
        "matches": 1,
    },
]
