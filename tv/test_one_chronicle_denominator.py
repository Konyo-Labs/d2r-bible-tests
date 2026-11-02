# -*- coding: utf-8 -*-
"""v2714 — THE CHRONICLE DENOMINATOR WAS RE-DERIVED AT ELEVEN SITES AND THEY DISAGREED IN PUBLIC.

Konyo, 2026-09-06: *"this needs a unified and sharing logic.. no reason for it to render something
in the roster or fleet different from the consoles main tabs Uniques/Sets/runewords"*. He raised it
because the numbers on his own screen did not agree, and he was right.

MEASURED on his live console, `GET /api/fleet`, twice, six minutes apart, same machine, same board:

    10:33:26   uniques {have: 169, total: 398}
    10:39:39   uniques {have: 292, total: 403}
    Dean       uniques {have: 0,   total: 398}
    his board's own Chronicle meter:            258 / 403

THREE numerators and TWO denominators under ONE field name, and nothing on any surface said which
question had been answered. The denominators are not three bugs — they are three questions:

    403   the spawnable file-row count that morning, six of them quest items
    392   funiScan().total — the carded roster after his v2680 one-tally-per-sunder ruling
    398   produced by NEITHER, and no array on the page is that size

2026-11-02 he joined the pin to the chronicle number. The pin is 397 uniques. The function
returns that pin. A second subtraction of the six quest items would print 391.

=== WHAT THIS PINS ===
`x.chronTotal || x.total` appeared at ELEVEN sites. Nine of them ask the same question and now call
ONE function, `window.d2rChronTotal`. Two are left alone ON PURPOSE and this file protects that too:

    _darkN   = chronTotal - total    the still-dark rows — genuinely needs BOTH numbers
    _uniLeft = chronTotal - found    already uses chronTotal alone, with no fallback

A blanket unification would have destroyed the distinction the function exists to protect, which is
why this gate counts the survivors instead of demanding zero. [[copy-drift]]

⚠ AND IT PINS THE FALLBACK'S *COUNTER*, NOT JUST THE FALLBACK. Returning null would put NaN on his
screen, so the guess is kept — but in one place, and it counts itself. `window.__d2rChronFallbacks`
is the measurement that can finally answer where 398 came from. An unmeasured fallback is exactly
how eleven sites came to disagree without anyone noticing. [[unknown-stays-unknown]]
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

BIBLE = os.path.join(ROOT, "bible.html")

#: the two sites that legitimately hold chronTotal and the carded total apart
DELIBERATE = ("_darkN", "_uniLeft")


RED_PROOF = [
    {
        "why": 'the law requires this text in bible.html, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'bible.html',
        "find": 'chronTotal:397',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
]

def _src():
    return io.open(BIBLE, encoding="utf-8").read()


def _decomment(s):
    """-> s with /* */ and // comments blanked, so PROSE cannot satisfy or trip a CODE check.

    This file's own header quotes `x.chronTotal || x.total` while forbidding it — the exact shape
    that has tripped two guards in this repo already. [[source-reading-guard]]
    """
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return re.sub(r"(?m)//.*$", " ", s)


class OneChronicleDenominator(unittest.TestCase):

    def setUp(self):
        self.raw = _src()
        self.code = _decomment(self.raw)

    def test_there_is_exactly_one_definition(self):
        n = len(re.findall(r"window\.d2rChronTotal\s*=\s*function", self.code))
        self.assertEqual(
            n, 1,
            "there are %d definitions of the chronicle denominator. Two definitions is the defect "
            "this file exists to prevent — it is how eleven sites came to disagree." % n
        )

    def test_it_is_defined_before_every_caller(self):
        """⚠ 26 script blocks. A call that runs before the defining block has parsed is a dead
        render, and this repo has paid for that four times. [[console-ui-two-script-blocks]]"""
        d = self.code.index("window.d2rChronTotal = function")
        calls = [m.start() for m in re.finditer(r"window\.d2rChronTotal\(", self.code)]
        self.assertTrue(calls, "nothing calls d2rChronTotal — the helper is unused")
        early = [c for c in calls if c < d]
        self.assertEqual(
            early, [],
            "%d call site(s) appear BEFORE the definition. Across 26 script blocks that is a "
            "TypeError on a page his console serves live." % len(early)
        )

    def test_no_site_re_derives_it(self):
        """The law: nine questions, one answer. Only the two deliberate holdouts may survive."""
        hits = re.findall(r"[A-Za-z0-9_.]*chronTotal\s*\|\|\s*[A-Za-z0-9_.]*total", self.code)
        self.assertLessEqual(
            len(hits), len(DELIBERATE),
            "%d site(s) still re-derive `chronTotal || total`: %r. Each one is a second definition "
            "of his progress that can silently swap the denominator." % (len(hits), hits[:6])
        )

    def test_the_two_deliberate_sites_are_still_there(self):
        """⚠ ANTI-OVER-CORRECTION. A blanket replace would have unified these two away, and the
        gate would have gone green while the dark-row count silently became zero."""
        # ⚠⚠ PIN THE SUBTRACTION, NOT THE NAME. The first cut asserted `_darkN in code`, and a
        # sabotage that replaced the whole line with `var _darkN=0;` LEFT IT GREEN — the token
        # survives, the arithmetic does not. A law satisfied by a variable still being spelled the
        # same way measures nothing. Found by the sabotage pass, which is what it is for.
        # [[sabotage-is-usually-the-wrong-one]] [[regression-guard]]
        pats = {
            "_darkN":   r"_darkN\s*=\s*\(?\s*[A-Za-z0-9_.]*chronTotal[^;]*\)?\s*-\s*[A-Za-z0-9_.]*total",
            "_uniLeft": r"_uniLeft\s*=\s*\(?\s*[A-Za-z0-9_.]*chronTotal[^;]*\)?\s*-\s*[A-Za-z0-9_.]*found",
        }
        for name in DELIBERATE:
            self.assertIn(name, self.code, "%s is gone entirely." % name)
            self.assertRegex(
                self.code, pats[name],
                "%s no longer SUBTRACTS the two totals. It holds chronTotal and the carded total "
                "apart on purpose — the still-dark rows are exactly their difference — so a %s "
                "that no longer does the arithmetic reports 0 forever while the name still reads "
                "correct." % (name, name)
            )

    def test_the_fleet_payload_uses_it(self):
        """The surface he actually complained about. [[the-unjoined-end]]"""
        m = re.search(r"uniques:\s*fu\s*\?\s*pair\(([^)]*)\)", self.code)
        self.assertIsNotNone(m, "the fleet payload's uniques line is not where this gate expects "
                                "it — fix this test before trusting its verdict")
        self.assertIn("d2rChronTotal", m.group(1),
                      "the FLEET payload still computes its own denominator: %r. That is the exact "
                      "surface he raised — the roster disagreeing with the tabs." % m.group(1))

    def test_the_fallback_counts_itself(self):
        """A fallback nobody counts is how eleven sites disagreed unnoticed."""
        body = self.code[self.code.index("window.d2rChronTotal = function"):][:1400]
        self.assertIn("__d2rChronFallbacks", body,
                      "the fallback does not increment a counter, so whether it EVER fires on his "
                      "machine stays unmeasurable — which is how 398 got onto a screen with no author")

    def test_the_pinned_total_is_the_chronicle_number(self):
        """His ruling, 2026-11-02. The pin and the chronicle number are 397."""
        self.assertIn("chronTotal:397", self.code.replace(" ", ""),
                      "funiScan no longer pins chronTotal at 397.")
        self.assertNotIn("chronTotal:403", self.code.replace(" ", ""),
                         "the file-row count is back in the pin. The chronicle number is 397.")
        body = self.code[self.code.index("window.d2rChronTotal = function"):][:800]
        self.assertNotIn("_CHRON_QUESTS", body,
                         "d2rChronTotal subtracts the quest list, so the screen prints 391")
        self.assertNotIn("return t - q", body)
        self.assertIn("return t;", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
