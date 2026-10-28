# -*- coding: utf-8 -*-
"""A LOCAL COMPANION APP BEING ABSENT ON A CLOUD RUNNER IS NOT A PRODUCT DEFECT.

`bible.html` probes the TV DIABLO console (127.0.0.1:17771/17772) to see whether it is running.
On a GitHub runner it never is, so every end-to-end audit recorded

    REQ: net::ERR_CONNECTION_REFUSED fetch http://127.0.0.1:17772/api/status

and scored **7/8 categories** — with `320/320 items opened · 0 fails · 0 page errors` printed
directly beside it. Routine G had therefore been RED on nothing but the absence of a desktop app,
across every run back to at least 2026-09-16 10:53.

`end_to_end_audit.js` already states the principle one line above the fix, about external hosts:
*"a gate that cries wolf gets ignored on the day it is right."* That is not a hypothetical here —
the swallowed-exception ratchet was correctly red for ten consecutive runs on three real defects
(REG-1034) and was walked past every time, because red had stopped meaning anything.

⚠ THE BUCKET IS NARROW ON PURPOSE AND STILL PRINTED. Only the console's two ports, only on
loopback. Any other local port still gates, because a probe to a port the page should not be
touching is a real finding. It prints on its own line as `CON:` with its own count and lands in
the JSON as `console_probe_failures` — recorded, not hidden. The difference between this and
suppression is that suppression makes the number disappear.

⚠ THIS GATE EXTRACTS THE REGEXES FROM THE AUDIT ITSELF rather than restating them. A test that
re-declares the pattern it is checking proves only that I can type it twice, and drifts silently
the moment the real one changes. [[copy-drift]] [[source-reading-guard]]
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

AUDIT = os.path.join(REPO, "end_to_end_audit.js")


def _line_with(src, needle):
    for ln in src.splitlines():
        if needle in ln and not ln.strip().startswith("//"):
            return ln.strip()
    return None


class TestAMissingCompanionIsNotARegression(unittest.TestCase):

    def setUp(self):
        if not os.path.isfile(AUDIT):
            self.skipTest("end_to_end_audit.js is absent — nothing to pin")
        with io.open(AUDIT, encoding="utf-8") as f:
            self.src = f.read()

    def test_the_audit_declares_a_console_bucket(self):
        self.assertIn("isConsoleProbe", self.src,
                      "the audit has no console bucket, so an absent desktop app fails a cloud run")
        self.assertIn("console_probe_failures", self.src,
                      "the bucket must reach the JSON report — a category nobody can read later "
                      "is a suppression, not a classification")
        self.assertIn("CON:", self.src,
                      "it must still PRINT. Recorded-not-gated is only honest while it is visible")

    def test_the_gated_list_excludes_the_console_and_nothing_more(self):
        ln = _line_with(self.src, "const uniqFailed")
        self.assertIsNotNone(ln, "the gated-failures line moved — re-anchor this gate")
        self.assertIn("!isConsoleProbe", ln,
                      "the gated list still counts the console probe: %s" % ln)
        self.assertIn("!isExternal", ln,
                      "the external bucket was lost while adding the console one — that would "
                      "make network weather fail the audit again: %s" % ln)

    @unittest.skipIf(shutil.which("node") is None, "node unavailable — a skip is NOT a pass")
    def test_the_real_patterns_classify_eight_urls_correctly(self):
        """★ Runs the audit's OWN regex lines. Narrow bucket, or it hides real findings."""
        ext = _line_with(self.src, "const isExternal")
        ports = _line_with(self.src, "const CONSOLE_PORTS")
        probe = _line_with(self.src, "const isConsoleProbe")
        for name, ln in (("isExternal", ext), ("CONSOLE_PORTS", ports), ("isConsoleProbe", probe)):
            self.assertIsNotNone(ln, "could not extract %s from the audit" % name)
        cases = [
            ("http://127.0.0.1:17772/api/status", "console"),
            ("http://127.0.0.1:17771/api/tz", "console"),
            ("http://localhost:17772/api/status", "console"),
            ("http://127.0.0.1:9224/json", "GATED"),
            ("http://127.0.0.1:17999/api/status", "GATED"),
            ("https://fonts.gstatic.com/x.woff2", "external"),
            ("file:///tmp/bible.html", "GATED"),
            ("http://127.0.0.1:177720/api/status", "GATED"),
        ]
        harness = "\n".join([ext, ports, probe, "const cases = %s;" % json.dumps(cases), """
const out = cases.map(([u, want]) => [u, want,
  isConsoleProbe(u) ? 'console' : (isExternal(u) ? 'external' : 'GATED')]);
console.log(JSON.stringify(out));
"""])
        d = tempfile.mkdtemp(prefix="companion_")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "h.js")
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(harness)
        r = subprocess.run(["node", p], capture_output=True)
        self.assertEqual(r.returncode, 0,
                         "the audit's own patterns would not run:\n%s"
                         % r.stderr.decode("utf-8", "replace")[:500])
        got = json.loads(r.stdout.decode("utf-8", "replace"))
        bad = [(u, want, g) for u, want, g in got if want != g]
        self.assertEqual(bad, [],
                         "the audit misclassifies these — a bucket that is too WIDE hides real "
                         "failures, one too NARROW keeps Routine G permanently red: %r" % bad)

RED_PROOF = [
    {"why": "the console bucket widens to every loopback port, so a probe the page should not be making is hidden",
     "file": "end_to_end_audit.js",
     "find": "  const CONSOLE_PORTS = /^https?:\\/\\/(127\\.0\\.0\\.1|localhost):(17771|17772)\\b/i;\n",
     "replace": "  const CONSOLE_PORTS = /^https?:\\/\\/(127\\.0\\.0\\.1|localhost):\\d+/i;\n",
     "matches": 1, "needs": "node"},
    {"why": "the gated list counts the console probe again, so an absent desktop app fails every cloud audit",
     "file": "end_to_end_audit.js",
     "find": "  const uniqFailed   = allFailed.filter(u => !isExternal(_url(u)) && !isConsoleProbe(_url(u)));\n",
     "replace": "  const uniqFailed   = allFailed.filter(u => !isExternal(_url(u)));\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
