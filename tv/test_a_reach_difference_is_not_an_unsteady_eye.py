# -*- coding: utf-8 -*-
"""#168 — "at ONE payload" was a claim agreement() never checked.

MEASURED on two real pairs it called unsteady:
    v3413   8,622 chars (cannot-tell)  vs  25,074 chars (findings)   — 2.9x
    v3451   7,744 chars (clean)        vs  76,810 chars (findings)   — 9.9x
An eye shown a TENTH of the change answering differently from one shown all of it is not an
unsteady instrument — it is the CAP doing what the cap does. Blaming the eye points the reader at
the wrong subject, which is exactly the conclusion that stops anyone looking at the cap.
⚠ The data was in the rows all along: `sentCode`/`chars` appeared NOWHERE in agreement()'s body.
"""
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

import second_eye_ledger as L      # noqa: E402
import console_doctor as D         # noqa: E402


def _row(verdict, chars, model="grok-4.7", version="vTEST"):
    return {"version": version, "verdict": verdict, "model": model, "reached": True,
            "family": L.family_of(model), "sentCode": {"chars": chars, "fences": 0, "unsent": []},
            "absent": [], "reach": None}


class AReachDifferenceIsNotAnUnsteadyEye(unittest.TestCase):

    def _agree(self, rows):
        real = L._rows
        try:
            L._rows = lambda *a, **k: rows
            return L.agreement("vTEST")
        finally:
            L._rows = real

    def test_a_2x_payload_split_is_INCOMPARABLE_not_DISAGREE(self):
        a = self._agree([_row("clean", 7744), _row("findings", 76810)])
        self.assertEqual(a["state"], "INCOMPARABLE",
                         "two looks 9.9x apart were called a disagreement: %s" % a.get("say"))
        self.assertEqual(a.get("payloadRatio"), 9.9)
        for n in ("76810", "7744"):
            self.assertIn(n, a["say"], "the say does not NAME both payload sizes: %s" % a["say"])

    def test_COMPARABLE_payloads_that_differ_still_read_DISAGREE(self):
        """⚠ THE HALF THAT MUST NOT MOVE. If every disagreement became INCOMPARABLE this would be
        an exemption, not a distinction — and the unsteady-eye finding would be gone."""
        a = self._agree([_row("clean", 40000), _row("findings", 44000)])
        self.assertEqual(a["state"], "DISAGREE",
                         "a 1.1x pair was excused as incomparable: %s" % a.get("say"))
        self.assertIn("ONE payload", a["say"])

    def test_UNKNOWN_payload_sizes_do_not_claim_ONE_payload(self):
        """[[unknown-stays-unknown]] — nobody measured, so neither claim is earned."""
        r1, r2 = _row("clean", 7744), _row("findings", 76810)
        r2["sentCode"] = None
        a = self._agree([r1, r2])
        self.assertEqual(a["state"], "DISAGREE", "unmeasured sizes were called INCOMPARABLE")
        self.assertNotIn("at ONE payload", a["say"],
                         "it still asserts ONE payload with a size it never measured: %s" % a["say"])
        self.assertIn("UNKNOWN size", a["say"])

    def test_a_SMALL_third_look_cannot_hide_a_real_disagreement(self):
        """⚠⚠ THE CURE ALMOST KILLED THE PATIENT, and the cross-family eye caught it pre-push.

        max/min over EVERY look lets one small look set the state for the whole version. MEASURED
        on v3401, which has three reached looks:
              8,885 chars  cannot-tell
             33,447 chars  cannot-tell
             33,447 chars  clean        <- IDENTICAL payload, DIFFERENT verdict
        Two looks at exactly the same size disagree — the sharpest finding this function makes —
        and max/min across all three is 3.8x, so the version was labelled INCOMPARABLE and the
        real finding vanished. The question is PER-PAIR, not per-version.
        """
        a = self._agree([_row("cannot-tell", 8885),
                         _row("cannot-tell", 33447),
                         _row("clean", 33447)])
        self.assertEqual(
            a["state"], "DISAGREE",
            "two looks at an IDENTICAL payload disagreed and a third smaller look buried it as "
            "INCOMPARABLE — the fix swallowed the very defect it sits beside: %s" % a.get("say"))

    def test_every_disagreeing_pair_split_still_reads_INCOMPARABLE(self):
        """The other half: when NO disagreeing pair is comparable, it really is a payload split."""
        a = self._agree([_row("clean", 5000), _row("clean", 5200), _row("findings", 60000)])
        self.assertEqual(a["state"], "INCOMPARABLE",
                         "every disagreeing pair was a >2x split and it was still called an "
                         "unsteady eye: %s" % a.get("say"))

    def test_the_census_COUNTS_the_new_state(self):
        """v3459 added a state and the census counted DISAGREE and ECHO only, so seven versions
        were counted by NOTHING and `disagreed` falling read as the instrument settling down."""
        import second_eye_ledger as _L
        c = _L.agreement_census()
        self.assertIn("incomparable", c,
                      "agreement_census does not report INCOMPARABLE, so versions in that state "
                      "are counted by nothing and the disagreement count silently improves")
        total = (c.get("disagreed", 0) + c.get("echoed", 0) + c.get("incomparable", 0))
        self.assertLessEqual(total, c.get("recent", 0),
                             "the census counts more versions than it looked at")

    def test_INCOMPARABLE_is_in_the_named_vocabulary(self):
        """A state no reader has heard of is the unjoined end this repo keeps paying for."""
        self.assertIn("INCOMPARABLE", L.AGREEMENT_STATES)

    def test_the_doctor_calls_it_MISSING_and_never_UNKNOWN(self):
        """UNKNOWN means nobody could ask. This is a MEASUREMENT — the ratio is on the row."""
        import inspect, ast
        src = inspect.getsource(D._check_the_second_eye_was_asked_twice)
        t = ast.parse(src.lstrip()); fn = t.body[0]
        if (fn.body and isinstance(fn.body[0], ast.Expr)
                and isinstance(getattr(fn.body[0], "value", None), ast.Constant)):
            fn.body = fn.body[1:]
        code = ast.unparse(fn)
        self.assertIn("INCOMPARABLE", code,
                      "the doctor has no branch for INCOMPARABLE, so it falls through to UNKNOWN "
                      "— a measured fact reported as 'nobody could ask'")

RED_PROOF = [
    {"why": "#168 - two looks 9.9x apart in payload are called an unsteady eye; the cap is never blamed",
     "file": "tv/second_eye_ledger.py",
     "find": "    if _ratio is not None and _ratio >= _PAYLOAD_SPLIT and _real_split:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3461 - one small third look sets the state for the whole version and buries a same-payload disagreement",
     "file": "tv/second_eye_ledger.py",
     "find": "        _real_split = not _comparable_disagreement\n",
     "replace": "        _real_split = True\n",
     "matches": 1},
    {"why": "every disagreement is excused as a payload split, so the unsteady-eye finding is gone",
     "file": "tv/second_eye_ledger.py",
     "find": "_PAYLOAD_SPLIT = 2.0\n",
     "replace": "_PAYLOAD_SPLIT = 1.0\n",
     "matches": 1},
    {"why": "looks whose sizes nobody measured are still said to be 'at ONE payload'",
     "file": "tv/second_eye_ledger.py",
     "find": "    _one = (\"at ONE payload\" if _ratio is not None\n",
     "replace": "    _one = (\"at ONE payload\" if True\n",
     "matches": 1},
    {"why": "the census does not count INCOMPARABLE, so the disagreement count silently improves",
     "file": "tv/second_eye_ledger.py",
     "find": "            \"incomparable\": len(incomparable),\n",
     "replace": "",
     "matches": 1},
    {"why": "INCOMPARABLE is missing from the named vocabulary, so a reader has never heard of it",
     "file": "tv/second_eye_ledger.py",
     "find": "AGREEMENT_STATES = (\"NONE\", \"SINGLE\", \"AGREE\", \"ECHO\", \"DISAGREE\",\n                    \"INCOMPARABLE\")\n",
     "replace": "AGREEMENT_STATES = (\"NONE\", \"SINGLE\", \"AGREE\", \"ECHO\", \"DISAGREE\")\n",
     "matches": 1},
    {"why": "the doctor has no INCOMPARABLE branch, so a measured payload split falls through to UNKNOWN",
     "file": "tv/console_doctor.py",
     "find": "    if st == \"INCOMPARABLE\":\n        return MISSING, ((a.get(\"say\") or \"two looks over payloads too different to compare\")\n                         + \" · the half that is missing is MINE to take: one more look at \"\n                           \"COMPARABLE reach, recorded as its own ledger row\") + tail\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
