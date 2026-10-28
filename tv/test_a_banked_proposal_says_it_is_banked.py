#!/usr/bin/env python3
"""A BANKED PROPOSAL SAYS SO ON THE BUTTON — #226 §1a.

THE AUDIT (issue #226, 2026-09-15): *"Vault panel stale register (#218 panel-half · STILL-REAL).
Heart/doctor/witness WIRED. `_vaultPaint` still uses stored `owned.length` for OWNED header and
`register N ✓` — no display re-grade."*

WHAT WAS ACTUALLY WRONG, measured on the shipped file: the age WAS painted — into `_vAge`, a
caption a few lines above, correctly including "restored from disk, not from this session". The
COUNT sat on the button. So the console told the truth in one element and offered an action in
another, and the one he clicks was the one that said nothing.

A vault proposal is a SNAPSHOT: graded against the witness rules and the ledger as they stood
when that sweep ran. Re-grading it in the panel would put a second copy of the witness logic in
JS — the drift this repo refuses — so the fix is not to recompute the number but to stop
presenting a banked one as fresh. [[copy-drift]] [[stale-reading]]

⚠ `resultFromDisk` IS THE STRONGER SIGNAL, NOT THE CLOCK. A proposal restored from disk was never
made in this session at all: it can read four minutes old and still describe a sweep from a
process that no longer exists.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable
    enable()
except Exception:
    pass

UI = os.path.join(HERE, "control_ui.html")
START = "    var ap = document.getElementById('vault-apply');"
END = "    }"


def _block():
    """Both ends anchored — a window past the region reads as ABSENT and this law would pass on a
    file that no longer contains the button. [[source-reading-guard]]"""
    with io.open(UI, encoding="utf-8") as fh:
        src = fh.read()
    i = src.find(START)
    assert i >= 0, "the vault register button is gone from control_ui.html"
    j = src.find("\n    }\n", i)
    assert j > i, "the button block no longer closes as expected"
    return src[i:j]


class ABankedProposalSaysItIsBanked(unittest.TestCase):

    def setUp(self):
        self.blk = _block()
        # strip comments: the prose beside this code discusses every term it asserts
        self.code = re.sub(r"/\*.*?\*/", " ", self.blk, flags=re.S)
        self.code = re.sub(r"(?m)^\s*//.*$", " ", self.code)

    def test_the_button_reads_the_proposals_own_timestamp(self):
        print("   resultTs on the button: %s" % ("resultTs" in self.code))
        self.assertIn("resultTs", self.code,
                      "the register button never looks at when the proposal was made")

    def test_restored_from_disk_counts_as_stale_on_its_own(self):
        """Not the clock — a disk-restored proposal was never made in this session."""
        # ⚠ PRESENCE IS NOT BEHAVIOUR. The first cut asserted only that the token appeared in
        # the block — and it appears in the wording too, so a sabotage that removed it from the
        # STALENESS TEST and left it in the label sailed through. Pin the expression that decides.
        m = re.search(r"_pStale\s*=\s*([^;]+);", self.code)
        self.assertIsNotNone(m, "nothing decides whether the proposal is stale")
        expr = m.group(1)
        print("   _pStale expr: %s" % expr.strip()[:90])
        self.assertIn("resultFromDisk", expr,
                      "a proposal restored from an earlier session is offered as if this session "
                      "had just produced it — the clock alone cannot see that, because a disk "
                      "proposal can read four minutes old and describe a dead process")

    def test_the_label_itself_changes_not_only_a_caption(self):
        """The caption already told the truth. The button is what he clicks."""
        self.assertIn("ap.textContent", self.code, "the button label is gone")
        m = re.search(r"ap\.textContent\s*=\s*([^;]+);", self.code)
        self.assertIsNotNone(m, "the button label is no longer assigned")
        expr = m.group(1)
        print("   label expr: %s" % expr.strip()[:90])
        self.assertNotEqual(expr.strip(), "'register ' + owned.length + ' ✓'",
                            "the label is the bare count again, so a proposal from an earlier "
                            "session is offered exactly like one made a moment ago")
        self.assertIn("_pWhen", expr, "the label carries no staleness")

    def test_it_also_marks_the_button_and_explains_on_hover(self):
        self.assertIn("vault-apply-stale", self.code,
                      "nothing marks the button when the proposal is banked")
        self.assertIn("ap.title", self.code,
                      "hovering the button explains nothing about what it will register")

    def test_the_stale_class_is_actually_styled(self):
        """A class nobody styles is a flag nobody can see. [[plumbing-with-no-tap]]"""
        with io.open(UI, encoding="utf-8") as fh:
            src = fh.read()
        # ⚠ TWO SPELLINGS, ONE CLASS. The stylesheet writes `.vault-apply-stale` and the JS
        # writes the bare string into classList.toggle — counting only the dotted form finds the
        # rule and misses the use, which is how the first cut of this test failed on correct code.
        rule = ".vault-apply-stale" in src
        used = "'vault-apply-stale'" in src or '"vault-apply-stale"' in src
        print("   styled: %s | set by the panel: %s" % (rule, used))
        self.assertTrue(rule, "the stale class is set but never styled — a flag nobody can see")
        self.assertTrue(used, "the stale class is styled but the panel never sets it")

    def test_it_does_not_re_grade_in_javascript(self):
        """A second copy of the witness logic in the panel is the drift this fix avoids. The
        panel may report staleness; it may not invent a new verdict."""
        for banned in ("KEEP_CONF_FLOOR", "KEEP_MIN_WITNESSES", "wilson", "Wilson"):
            self.assertNotIn(banned, self.code,
                             "the panel is re-deriving the witness rules in JS (%r) — that is a "
                             "second definition of his ownership bar" % banned)
        print("   no witness constants re-derived in the panel")

RED_PROOF = [
    {"why": "#226 1a - a proposal restored from an earlier session counts as fresh again: only the clock decides",
     "file": "tv/control_ui.html",
     "find": "      var _pStale = !!(st && st.resultFromDisk) || (_pAge !== null && _pAge > 30 * 60000);\n",
     "replace": "      var _pStale = (_pAge !== null && _pAge > 30 * 60000);\n",
     "matches": 1},
    {"why": "#226 1a - the register button goes back to the bare count, so a banked proposal is offered like a fresh one",
     "file": "tv/control_ui.html",
     "find": "      ap.textContent = 'register ' + owned.length + ' ✓' + _pWhen;\n",
     "replace": "      ap.textContent = 'register ' + owned.length + ' ✓';\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
