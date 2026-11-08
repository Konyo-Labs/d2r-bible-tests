"""v2460 — the console and the worker must agree on WHICH LEDGERS EXIST.

⚠ THE DEFECT THIS EXISTS FOR. `_masks_for_wire()` has said "every ledger this machine can build,
not a hardcoded one" since v2329, and the worker that RECEIVES those masks stored exactly one:

    const sets = one(m.sets);
    return sets ? { sets: sets } : null;

So a uniques mask would have been discarded on arrival, and the uniques cross-reference could never
have worked end to end no matter what the boards published. Grok measured the board side and I
confirmed it from the live record — both of us were looking at the wrong end. One half generalised,
the other left naming a single ledger, and nothing compared them. [[the-unjoined-end]] [[copy-drift]]

This pins the RULE — the two ends carry the same set — never the roster. Adding a third ledger is
allowed; adding it to only one end is not.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
WORKER = os.path.join(os.path.dirname(HERE), "functions", "api", "console.js")


def _worker_ledgers():
    """-> set | None. The allow-list the worker actually iterates, read from CODE.

    ⚠ Comments are stripped first. This file's own header names both ledgers while explaining the
    bug, and a grep over raw text would find them and vouch for a worker that stores neither.
    [[source-reading-guard]]
    """
    try:
        src = io.open(WORKER, encoding="utf-8", errors="replace").read()
    except Exception:
        return None
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"(?m)//.*$", " ", src)
    m = re.search(r"const\s+LEDGERS\s*=\s*\[([^\]]*)\]", src)
    if not m:
        return None
    return set(re.findall(r"'([a-z]+)'|\"([a-z]+)\"", m.group(1)) and
               [a or b for a, b in re.findall(r"'([a-z]+)'|\"([a-z]+)\"", m.group(1))])


RED_PROOF = [
    {
        "why": "v2460's defect exactly: the worker stores fewer ledgers than the console can "
               "publish, so a uniques mask is DISCARDED on arrival and every surface downstream "
               "says 'we have not heard from that machine' however correct its board is",
        "file": "functions/api/console.js",
        "find": "const LEDGERS = ['sets', 'uniques', 'colossal', 'facets'];",
        "replace": "const LEDGERS = ['sets', 'colossal', 'facets'];",
        "matches": 1,
    },
    {
        "why": "the reverse direction — a key the console can never produce, which reads in the "
               "schema as a feature that exists and will never carry data",
        "file": "functions/api/console.js",
        "find": "const LEDGERS = ['sets', 'uniques', 'colossal', 'facets'];",
        "replace": "const LEDGERS = ['sets', 'uniques', 'colossal', 'facets', 'runewords'];",
        "matches": 1,
    },
]


class TheTwoEndsCarryTheSameLedgers(unittest.TestCase):

    def test_the_worker_declares_a_ledger_list_at_all(self):
        """A worker that names one ledger inline cannot be compared to anything, and that is how
        this stayed invisible: there was no list to disagree with."""
        got = _worker_ledgers()
        self.assertIsNotNone(
            got, "no LEDGERS allow-list found in functions/api/console.js — if the ledgers are "
                 "named inline again, nothing can check that both ends agree")
        self.assertTrue(got, "the worker's LEDGERS list is empty, so it would store no mask at all")

    def test_every_ledger_the_console_can_publish_is_stored_by_the_worker(self):
        import fleet_mask
        py = set(getattr(fleet_mask, "LEDGERS", ()) or ())
        self.assertTrue(py, "fleet_mask declares no ledgers — the instrument is broken, not the code")
        js = _worker_ledgers() or set()
        missing = sorted(py - js)
        self.assertEqual(
            missing, [],
            "the console can publish %s and the worker stores only %s — a mask for %s would be "
            "discarded on arrival, and every surface downstream would say 'we have not heard one' "
            "however correct the board is" % (sorted(py), sorted(js), missing))

    def test_the_worker_does_not_store_a_ledger_the_console_never_sends(self):
        """The reverse direction is not fatal but it is a lie in the schema: a key the console
        cannot produce reads as a feature that exists."""
        import fleet_mask
        py = set(getattr(fleet_mask, "LEDGERS", ()) or ())
        js = _worker_ledgers() or set()
        self.assertEqual(sorted(js - py), [],
                         "the worker stores %s, which no console can send" % sorted(js - py))


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    unittest.main(verbosity=2)
