# -*- coding: utf-8 -*-
"""v3169 (#82) — "HAS NOT REPORTED" MUST NOT BE SAID ABOUT A MACHINE THAT REPORTED.

HIS CORRECTION, 2026-09-15. He sent the cross-reference panel reading

    "Dean has not reported which set pieces it holds yet - that is 'we have not heard from
     it', not 'it has none'. It publishes on its next heartbeat."

beside his own fleet card reading **DEAN · SETS 131/135 · UNIQUES 0/403 · RUNEWORDS 98/99**,
and said: *"dean already synced his sets something is regressed here"* and then, with a second
screenshot, *"i m saying that he has it even says it here"*.

MEASURED on his live /api/fleet at that moment - Dean's row carried
`tally.sets {have 131, total 135}` and `maskWhy {'sets': 'no board window'}`, `masks: None`.

SO THE SENTENCE WAS WRONG TWICE OVER:
  1. HE DID REPORT. The counts were on the wire. What was missing is the per-item MASK - the
     bitmask that lets the panel NAME pieces rather than count them. "has not reported" is a
     label that stopped being true of the number printed beside it. [[label-outlived-referent]]
  2. "IT PUBLISHES ON ITS NEXT HEARTBEAT" IS A PROMISE THAT CANNOT BE KEPT. The row already
     said why: no board window on that machine. It will fail identically on every heartbeat
     until one is open. A false "just wait" turns a fixable condition into an invisible one.

AND THE REASON WAS PUBLISHED BUT NEVER READ: `maskWhy` appeared ZERO times in control_ui.html.
[[the-unjoined-end]] [[zero-needs-a-denominator]]
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _dean(tally=None, mask_why=None):
    r = {"machine": "LAPTOP-QNFL860M", "nickname": "Dean", "os": "windows",
         "ver": "v3156", "masks": None, "t": 1789431849.587}
    if tally is not None:
        r["tally"] = tally
    if mask_why is not None:
        r["maskWhy"] = mask_why
    return r


class ReportedCountsIsNotNoReport(unittest.TestCase):

    def setUp(self):
        import control_app
        self.c = control_app
        self._orig = control_app.fleet_presence

    def tearDown(self):
        self.c.fleet_presence = self._orig

    def _compare(self, row, ledger="sets"):
        fleet = {"online": [], "offline": [row], "stale": False}
        self.c.fleet_presence = lambda *a, **k: fleet
        return self.c.fleet_compare("LAPTOP-QNFL860M", ledger)

    # the exact state he screenshotted
    def test_a_machine_that_reported_counts_is_not_called_unreported(self):
        out = self._compare(_dean(tally={"sets": {"have": 131, "total": 135}, "ok": True},
                                  mask_why={"sets": "no board window"}))
        why = out.get("why") or ""
        self.assertNotIn("has not reported", why,
                         "he read this beside a card showing SETS 131/135 and said 'he has it, "
                         "even says it here'")
        self.assertIn("131", why, "the count he can see must appear in the sentence about it")

    def test_the_reason_the_mask_is_missing_is_named(self):
        out = self._compare(_dean(tally={"sets": {"have": 131, "total": 135}, "ok": True},
                                  mask_why={"sets": "no board window"}))
        self.assertIn("no board window", out.get("why") or "",
                      "the server published maskWhy and the panel rendered it nowhere")
        self.assertEqual(out.get("maskWhy"), "no board window",
                         "and it must be on the record as a field, not only inside prose")

    def test_it_does_not_promise_a_heartbeat_that_cannot_deliver(self):
        out = self._compare(_dean(tally={"sets": {"have": 131, "total": 135}, "ok": True},
                                  mask_why={"sets": "no board window"}))
        # ⚠ THE FIRST CUT OF THIS ASSERTION WAS BLIND, and the red-proof is what caught it.
        # It looked for "publishes on its next heartbeat" while the fallback actually says
        # "publishes THE LIST on its next heartbeat" - a substring the code cannot emit, so the
        # law could not fail. Matching on "next heartbeat" is what the claim is really about:
        # when the machine has ALREADY given a reason, no beat is going to change it.
        # [[sabotage-is-usually-the-wrong-one]] [[source-reading-guard]]
        self.assertNotIn("next heartbeat", out.get("why") or "",
                         "a machine with no board window fails the same way on EVERY beat - "
                         "telling him to wait hides a condition he could fix")

    def test_counts_and_names_are_told_apart(self):
        out = self._compare(_dean(tally={"sets": {"have": 131, "total": 135}, "ok": True},
                                  mask_why={"sets": "no board window"}))
        self.assertEqual(out.get("theirHave"), 131)
        self.assertEqual(out.get("theirTotal"), 135)

    # and the ORIGINAL case must survive: a machine that truly said nothing
    def test_a_machine_that_reported_nothing_still_says_so(self):
        out = self._compare(_dean())
        why = out.get("why") or ""
        self.assertIn("has not reported", why,
                      "a genuinely silent machine must still be named as UNHEARD, not as zero")
        self.assertIn("not 'it has none'", why)
        self.assertIsNone(out.get("theirHave"))

    def test_a_zero_count_still_counts_as_reported(self):
        """Dean's uniques really are 0/403. A reported zero is a MEASUREMENT, not a silence -
        conflating the two is the whole shape this console keeps having to correct."""
        out = self._compare(_dean(tally={"uniques": {"have": 0, "total": 403}, "ok": True},
                                  mask_why={"uniques": "no board window"}),
                            ledger="uniques")
        self.assertNotIn("has not reported", out.get("why") or "")
        self.assertEqual(out.get("theirHave"), 0)


class TheFleetCardStaysOnTheTypeScale(unittest.TestCase):
    """v3172 (#82) — the flagship typography half of his ask.

    The card was HALF on the scale: .ftt-counts used var(--fs-*)/var(--ls-wide) tokens while four
    sibling rules carried raw letter-spacing literals (.04em x2, .03em, .02em). Three had EXACT
    tokens (--ls-snug .04em, --ls-tight .02em) so swapping them changed nothing visually and made
    the card consistent. The fourth, .03em on .fleet-meta.fleet-word, sat on NO step of the scale
    while its twin — the same verdict word rendered in the tooltip as .ftt-h .ftt-w — was .04em.
    Two trackings for one word, recorded by nobody. Now both are --ls-snug.

    ⚠ A TOKEN SWAP IS NOT AUTOMATICALLY FREE. LOCKED_TYPE_SYSTEM's own warning: an em is not a
    lookup, so replacing one can change the rendered size silently. Three of these were exact
    matches; the fourth is a deliberate 0.01em move, named in the CSS so it is not re-guessed.
    """

    def test_the_fleet_card_declares_no_raw_letter_spacing(self):
        import re
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            src = fh.read()
        raw = []
        for m in re.finditer(r"(?m)^[ \t]*([.#][^{\n]*(?:fleet|ftt)[^{\n]*)\{([^}]*)\}", src):
            for lm in re.finditer(r"letter-spacing:\s*(\.[0-9]+em|[0-9.]+em)", m.group(2)):
                raw.append("%s -> %s" % (m.group(1).strip()[:40], lm.group(1)))
        self.assertEqual(raw, [],
                         "the fleet card is back off the type scale: %s" % "; ".join(raw))

    def test_the_verdict_word_tracks_the_same_in_both_places(self):
        """The row word and the tooltip word are the same thing and must not drift apart again."""
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn(".fleet-meta.fleet-word { font-weight: var(--fw-semibold); "
                      "letter-spacing: var(--ls-snug); }", src)
        self.assertIn("letter-spacing: var(--ls-snug); text-transform: lowercase;", src,
                      "the tooltip verdict word must carry the same tracking as the row's")

RED_PROOF = [
    {"why": "v3169 - a machine whose counts are on the wire is told it 'has not reported' beside a card showing them",
     "file": "tv/control_app.py",
     "find": "        if isinstance(_have, int):\n            # counts ARE here",
     "replace": "        if False:\n            # counts ARE here",
     "matches": 1},
    {"why": "a reported ZERO is read as silence, so Dean's measured 0/403 uniques reads as unheard",
     "file": "tv/control_app.py",
     "find": "        if isinstance(_have, int):\n            # counts ARE here",
     "replace": "        if _have:\n            # counts ARE here",
     "matches": 1},
    {"why": "the published reason is dropped and the panel promises a heartbeat that fails identically on every beat",
     "file": "tv/control_app.py",
     "find": "\"own.\" % _mwhy) if _mwhy\n",
     "replace": "\"own.\" % _mwhy) if False\n",
     "matches": 1},
    {"why": "maskWhy lives only inside prose, never on the record as a field",
     "file": "tv/control_app.py",
     "find": "        out[\"maskWhy\"] = _mwhy or None\n",
     "replace": "        out[\"maskWhy\"] = None\n",
     "matches": 1},
    {"why": "the total the other machine reported is dropped, so counts cannot be told apart from names",
     "file": "tv/control_app.py",
     "find": "        out[\"theirTotal\"] = _total if isinstance(_total, int) else None\n",
     "replace": "        out[\"theirTotal\"] = None\n",
     "matches": 1},
    {"why": "a genuinely silent machine's count is filled in as 0 - UNKNOWN shown as zero",
     "file": "tv/control_app.py",
     "find": "        out[\"theirHave\"] = _have if isinstance(_have, int) else None\n",
     "replace": "        out[\"theirHave\"] = _have if isinstance(_have, int) else 0\n",
     "matches": 1},
    {"why": "v3172 - the fleet verdict word goes back to a raw .03em tracking that sits on no step of the scale",
     "file": "tv/control_ui.html",
     "find": ".fleet-meta.fleet-word { font-weight: var(--fw-semibold); letter-spacing: var(--ls-snug); }",
     "replace": ".fleet-meta.fleet-word { font-weight: var(--fw-semibold); letter-spacing: .03em; }",
     "matches": 1},
    {"why": "the tooltip's verdict word tracks differently from the row's - one word, two trackings",
     "file": "tv/control_ui.html",
     "find": "letter-spacing: var(--ls-snug); text-transform: lowercase;",
     "replace": "letter-spacing: var(--ls-wide); text-transform: lowercase;",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
