# -*- coding: utf-8 -*-
"""REG-3287 - THE FAULT-EVIDENCE ROW COUNTS ONLY THE CONSOLE FAULTS THAT ARE SENT WITH A PRE-RESCUE SNAPSHOT.

MEASURED 11-06 on his Mac's /api/status: the eagle row "fault evidence" read MISSING - "5 console-reported fault(s) in 14
days and NOT ONE carries a pre-rescue snapshot. The measurement or the route has stopped". All five were
'theatre-open-no-sessions' from 10-28 (/api/sessions did not answer): a kind control_ui.html never sends a snapshot
with, because there is no stage to measure when the list never came. Only the paint faults carry `before`. Held here:
  * the kinds console_doctor.SNAPSHOT_KINDS names are exactly the ui_fault posts in control_ui.html that send `before`;
  * the row is UNKNOWN on non-paint faults (never MISSING), MISSING when a paint fault arrives without a snapshot, OK
    when it carries one.
REG-3775 (11-12): the server's own rescue ("console-rescued-by-server", recorded with before=) is a snapshot sender too -
3 such rows on his Mac in 14 days, and the row read UNKNOWN; the kinds are held to BOTH senders now.
Fixtures only (the ledger read is stubbed). RED_PROOF below.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import console_doctor as CD  # noqa: E402


def _ui_fault_posts(src):
    """{kind: sends_before} for every fetch('/api/ui_fault', ... JSON.stringify({...})) in the page, by brace count."""
    out = {}
    for m in re.finditer(r"fetch\(\s*'/api/ui_fault'", src):
        i = src.find("JSON.stringify(", m.end())
        if i < 0 or i - m.end() > 300:
            continue
        j, depth = i + len("JSON.stringify("), 1
        while j < len(src) and depth:
            depth += {"(": 1, ")": -1}.get(src[j], 0)
            j += 1
        body = src[i:j]
        k = re.search(r"kind\s*:\s*'([\w-]+)'", body)
        if k:
            out[k.group(1)] = out.get(k.group(1), False) or bool(re.search(r"\bbefore\s*:", body))
    return out


def _server_records(src):
    """REG-3775 - {kind: sends_before} for every ui_fault_record("<kind>", ...) call in control_app.py, by paren count (the
    relay that records the page's own posts names no literal kind and is left out - the page's half is read above)."""
    out = {}
    for m in re.finditer(r"ui_fault_record\(", src):
        if src[max(0, m.start() - 4):m.start()] == "def ":
            continue
        j, depth = m.end(), 1
        while j < len(src) and depth:
            depth += {"(": 1, ")": -1}.get(src[j], 0)
            j += 1
        body = src[m.end():j - 1]
        k = re.match(r'\s*"([\w-]+)"', body)
        if k:
            out[k.group(1)] = out.get(k.group(1), False) or ("before=" in body)
    return out


class TheRowCountsOnlyPaintFaults(unittest.TestCase):

    def test_the_kinds_are_the_pages_own_snapshot_senders(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            posts = _ui_fault_posts(fh.read())
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            served = _server_records(fh.read())
        self.assertGreater(len(posts), 5, "PREMISE: the page's ui_fault posts were not found: %r" % posts)
        self.assertIn("theatre-open-no-sessions", posts, "PREMISE: the measured kind is no longer posted")
        self.assertGreater(len(served), 5, "PREMISE: the server's ui_fault_record calls were not found: %r" % served)
        senders = sorted(set(k for k, b in posts.items() if b) | set(k for k, b in served.items() if b))
        self.assertEqual(senders, sorted(CD.SNAPSHOT_KINDS),
                         "the doctor's snapshot kinds and the page's + the server's snapshot senders differ")

    def test_the_servers_rescue_with_its_snapshot_is_evidence(self):
        """REG-3775 - his Mac 11-12: 3 server rescues in 14 days, each with `before`, and the row read UNKNOWN"""
        t = CD.EVIDENCE_SINCE_MS + 1000
        bare = {"kind": "console-rescued-by-server", "where": "_console_rescue_loop", "at": t}
        self.assertEqual(self._row([dict(bare, before={"elsNow": 1})])[0], CD.OK)
        self.assertEqual(self._row([bare])[0], CD.MISSING, "a server rescue with no snapshot read as evidence")

    def _row(self, rows):
        import control_app as CA
        real = CA.ui_faults_recent
        CA.ui_faults_recent = lambda hours=24: (rows, None)
        try:
            return CD._check_a_ui_fault_keeps_its_evidence()
        finally:
            CA.ui_faults_recent = real

    def test_a_fault_that_carries_no_stage_is_not_a_missing_snapshot(self):
        t = CD.EVIDENCE_SINCE_MS + 1000
        rows = [{"kind": "theatre-open-no-sessions", "where": "control_ui thOpen", "at": t + i} for i in range(5)]
        state, why = self._row(rows)
        self.assertEqual(state, CD.UNKNOWN, "5 sessions-did-not-answer faults read as a stopped snapshot: %r" % why)

    def test_a_paint_fault_without_its_snapshot_is_missing_and_with_it_ok(self):
        t = CD.EVIDENCE_SINCE_MS + 1000
        bare = {"kind": "theatre-stuck-black", "where": "control_ui thOpen / self-heal", "at": t}
        self.assertEqual(self._row([bare])[0], CD.MISSING)
        self.assertEqual(self._row([dict(bare, before={"w": 1})])[0], CD.OK)


RED_PROOF = [
    {"why": "REG-3775 - the server's snapshot-carrying rescue is left out again: 3 rescues, row UNKNOWN for 14 days",
     "file": "tv/console_doctor.py",
     "find": "SNAPSHOT_KINDS = (\"theatre-stuck-black\", \"console-rescued-by-server\")\n",
     "replace": "SNAPSHOT_KINDS = (\"theatre-stuck-black\",)\n",
     "matches": 1},
    {"why": "REG-3287 - the row counts every console fault, so five sessions-did-not-answer rows read as a stopped snapshot",
     "file": "tv/console_doctor.py",
     "find": "            and str((r or {}).get(\"kind\") or \"\") in SNAPSHOT_KINDS]      # REG-3287 - only the kinds that carry one\n",
     "replace": "            ]\n",
     "matches": 1},
    {"why": "REG-3287 - the doctor's kinds drift from the page's snapshot senders",
     "file": "tv/console_doctor.py",
     "find": "SNAPSHOT_KINDS = (\"theatre-stuck-black\", \"console-rescued-by-server\")\n",
     "replace": "SNAPSHOT_KINDS = (\"theatre-stuck-black\", \"console-rescued-by-server\", \"theatre-open-no-sessions\")\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
