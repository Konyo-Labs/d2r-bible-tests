# -*- coding: utf-8 -*-
"""THE EAGLE'S COLUMN COULD NEVER HAVE BEEN ANYTHING BUT EMPTY, AND THE TABLE SAID SO ABOUT THE
EAGLE RATHER THAN ABOUT ITSELF.

`organ_matrix` asks each organ what it names. For the eagle it did `__import__("control_app")` and
called `eagle_state()` — on a FRESHLY IMPORTED module, where `_EAGLE` is still the literal it is
defined as: `{"checked": None, "rows": [], "say": "not measured yet"}`. That dict is only ever
filled by the RUNNING console's background loop, in another process. So the answer was [] every
time, for every tree, no matter how well the eagle worked.

MEASURED 2026-09-12: the live console published 58 eagle rows on /api/status in the same minute the
table printed "eagle answered, and named nothing at all — which cannot tell 'watches nothing' apart
from 'had nothing to say just now'". It was neither. Nobody had asked the process that knows. After
pointing the reader at the console the same organ reports 59 names.

⚠⚠ AND THE FAILURE WAS INVISIBLE BECAUSE IT LOOKED LIKE A FINDING. An empty answer from an organ
reads as a verdict about the organ; it was a verdict about the reader. That is why this law exists
and why it checks the READER, not the eagle. [[feedback-suspect-the-instrument]]
[[the-unjoined-end]] [[zero-needs-a-denominator]]

⚠ The second half matters as much as the first: when the console is NOT running, this must answer
UNKNOWN with a reason, never an empty set. "The console was down" and "the eagle watches nothing"
are opposite facts and only one of them is a defect. [[unknown-stays-unknown]]
"""
import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

SRC = os.path.join(HERE, "organ_matrix.py")


class TestTheEagleIsAskedWhereItLives(unittest.TestCase):

    def setUp(self):
        self.tree = ast.parse(io.open(SRC, encoding="utf-8").read())

    def _fn(self, name):
        for n in ast.walk(self.tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name:
                return n
        return None

    def test_the_eagle_is_not_asked_through_a_cold_import(self):
        """THE LAW. Parsed, not grepped: a mention of eagle_state in a comment must not satisfy or
        defeat this. [[source-reading-guard]]"""
        cov = self._fn("organ_coverage")
        self.assertIsNotNone(cov, "organ_coverage() is gone — this law is reading the wrong file")
        bad = []
        for n in ast.walk(cov):
            if not isinstance(n, ast.Call):
                continue
            fname = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
            if fname != "_ask":
                continue
            lits = [a.value for a in n.args if isinstance(a, ast.Constant)
                    and isinstance(a.value, str)]
            if "eagle_state" in lits or "control_app" in lits:
                bad.append(lits)
        self.assertEqual(
            bad, [],
            "the eagle is asked through _ask(), which does a COLD __import__ of control_app. "
            "`_EAGLE` is only filled by the running console in another process, so that path "
            "returns [] forever and the table blames the eagle for the reader's reach: %s" % bad)

    def test_a_live_reader_exists_and_reaches_the_console(self):
        """Not just 'the cold path is gone' — something must actually ask the running process."""
        live = self._fn("_ask_live_eagle")
        self.assertIsNotNone(
            live, "_ask_live_eagle() is gone, so nothing asks the process that holds the eagle")
        body = ast.dump(live)
        self.assertIn("urlopen", body,
                      "_ask_live_eagle() no longer reaches the console over HTTP, so it cannot be "
                      "reading the eagle the running process holds")

    def test_an_unreachable_console_is_UNKNOWN_and_never_an_empty_set(self):
        """The half that decides whether a silence reads as a defect. Driven, not inspected."""
        import organ_matrix as OM
        import urllib.request as rq
        real = rq.urlopen

        def boom(*a, **k):
            raise IOError("refused by this test on purpose")

        rq.urlopen = boom
        try:
            names, why = OM._ask_live_eagle()
        finally:
            rq.urlopen = real
        self.assertIsNone(
            names,
            "with the console unreachable the reader returned %r instead of None. An empty set "
            "reads as 'the eagle names nothing', which is a claim about the ORGAN made from a "
            "failure of the READER — the exact defect this law exists for." % (names,))
        self.assertTrue(str(why).strip(),
                        "it answered UNKNOWN but gave no reason, so nobody can tell why")


RED_PROOF = [
    {
        "why": "puts the eagle back on the cold-import path, where _EAGLE is the unfilled literal "
               "and the answer is [] forever no matter how well the eagle works",
        "file": "organ_matrix.py",
        "find": 'out["eagle"] = _ask_live_eagle()',
        "replace": 'out["eagle"] = _ask("control_app", "eagle_state",\n'
                   '                        lambda r: _names_from((r or {}).get("rows")))',
        "matches": 1,
    },
    {
        "why": "makes an unreachable console answer an EMPTY SET instead of UNKNOWN, so a reader "
               "that could not reach the eagle reads as an eagle that watches nothing",
        "file": "organ_matrix.py",
        "find": "        return None, (\"the running console did not answer on %s (%s), and a cold import of \"",
        "replace": "        return set(), (\"the running console did not answer on %s (%s), and a cold import of \"",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
