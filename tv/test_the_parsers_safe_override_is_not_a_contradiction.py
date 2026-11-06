# -*- coding: utf-8 -*-
"""REG-3288 - THE VERDICT ROW KNOWS THE PARSER'S DOCUMENTED SAFE DIRECTION.

MEASURED 11-06 on his Mac's /api/status: the eagle row "verdict matches the answer" read MISSING - "2 of 1412 look(s)
judged by v3376 store a verdict their own answer denies: v3377(stored findings, said clean), v3578(stored findings,
said clean)". Both answers state "verdict: clean" and both carry a block the parser reads as a defect CLAIM ("disagree",
"fails"), and second_eye_run._verdict_for keeps "findings" over a stated "clean" on purpose: "a declaration alone can
never clear a real defect claim". Held here, through the real row with the ledger stubbed:
  * stated clean, stored findings, a block that claims a defect -> not a contradiction (said as the safe direction);
  * stated clean, stored findings, NO claiming block -> MISSING (the parser denied its own answer);
  * stated findings, stored clean -> MISSING (the dangerous direction is never excused).
RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import console_doctor as CD  # noqa: E402
import second_eye_ledger as L  # noqa: E402

FN = [f for n, f in CD.CHECKS if n == "verdict matches the answer"][0]


def _row(v, stored, said, findings):
    return {"version": v, "judgedBy": L.PARSER_GEN, "verdict": stored, "answerHead": "verdict: %s\n\nthe body" % said,
            "findings": findings}


class TheSafeOverrideIsNotAContradiction(unittest.TestCase):
    def _run(self, rows):
        real = L._rows
        L._rows = lambda *a, **k: rows
        try:
            return FN()
        finally:
            L._rows = real

    def test_a_claimed_defect_kept_over_a_stated_clean_is_the_safe_direction(self):
        state, why = self._run([_row("v1", "findings", "clean", ["the fallback FAILS when the file is missing"])])
        self.assertEqual(state, CD.OK, why)
        self.assertIn("safe direction", why)

    def test_findings_with_no_claim_over_a_stated_clean_is_a_contradiction(self):
        state, why = self._run([_row("v2", "findings", "clean", ["the diff renames one helper"])])
        self.assertEqual(state, CD.MISSING, why)
        self.assertIn("v2(stored findings, said clean)", why)

    def test_a_stated_finding_stored_clean_is_never_excused(self):
        state, why = self._run([_row("v3", "clean", "findings", ["the fallback FAILS when the file is missing"])])
        self.assertEqual(state, CD.MISSING, why)


RED_PROOF = [
    {"why": "REG-3288 - the parser's documented override reads as the parser denying its own answer",
     "file": "tv/console_doctor.py",
     "find": "            overruled += 1\n            continue\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-3288 - the exemption no longer needs a claiming block, so a bare contradiction is excused",
     "file": "tv/console_doctor.py",
     "find": "                and any(R._claims_a_defect(f) for f in (r.get(\"findings\") or []))):\n",
     "replace": "                and True):\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
