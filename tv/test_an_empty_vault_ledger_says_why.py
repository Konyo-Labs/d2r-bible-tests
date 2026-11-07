# -*- coding: utf-8 -*-
"""REG-3353 (#47) - AN EMPTY VAULT LEDGER SAYS WHY IT IS EMPTY, NEVER A BARE ZERO.

Board #47: "ALT vault_ledger empty - the Windows console never feeds it". MEASURED on the ALT 11-07 ~09:50 IST (v3876,
read-only GETs): /api/vault_ledger said "0 grounded row(s) and 0 sighting(s) still short of a second witness" for ~42 h. That
reads as "nothing was found". Two other facts were true and the route named neither:
  * no vault sweep could start - vault.sweep_start OPEN but not permitted, "26 of its own guard law(s) changed or are
    unproven" (the self-prove lane worked laws that guard nothing first - REG-3351);
  * the last sweep's classifier answered about none of its 2 stash stills (both readers timed out).

The route now adds `emptyWhy` and ends `say` with it when the ledger holds no row and was read whole: the sweep lock's own
refusal, the last sweep's own why with its age, or that a sweep is reading now. The view itself stays a read of its two
stores (it asks no lock), and a ledger with rows, or one that would not read, is served exactly as before.
Every store here is a fixture; the lock and the sweep are seams. [[unknown-stays-unknown]] RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
os.environ.setdefault("TV_CONTROL_PORT", "9")      # the compile reads CONTROL_PORT at import: off his live console

import control_app as ca  # noqa: E402

SHUT = (False, "the heart2 PROOF census is STALE (fixture). For vault.sweep_start (#156, per-lock): 26 of its own guard "
               "law(s) changed or are unproven since it ran (corroborate-selftest); the rest of the tree does not decide this lock.")
LAST = {"running": False, "resultTs": 1794000000000,
        "result": {"why": "2 still screen(s) were examined and the classifier answered about NONE of them"}}


def _view(owned=0, seen=0, say=None):
    return {"ok": True, "totals": {"owned": owned, "sightings": seen},
            "say": say or ("%d grounded row(s) and %d sighting(s) still short of a second witness." % (owned, seen))}


class AnEmptyLedgerSaysWhy(unittest.TestCase):

    def test_a_shut_sweep_lock_is_named(self):
        """* THE POINT: the ALT's 42 h - the ledger is empty because no sweep may start, and it says so"""
        w = ca._vault_empty_why(may_fn=lambda lock: SHUT, sweep_fn=lambda: LAST, now=1794000000 + 42 * 3600)
        self.assertIn("no vault sweep may start on this PC", w)
        self.assertIn("26 of its own guard law(s)", w)
        self.assertIn("the last vault sweep (42 h ago)", w)
        self.assertIn("classifier answered about NONE", w)

    def test_the_route_ends_its_say_with_the_why(self):
        v = ca._vault_ledger_explained(_view(), why_fn=lambda: "no vault sweep may start on this PC - fixture")
        self.assertEqual(v["emptyWhy"], "no vault sweep may start on this PC - fixture")
        self.assertTrue(v["say"].startswith("0 grounded row(s) and 0 sighting(s)"), v["say"])
        self.assertTrue(v["say"].endswith("Empty because no vault sweep may start on this PC - fixture."), v["say"])

    def test_a_sweep_reading_now_says_so(self):
        w = ca._vault_empty_why(may_fn=lambda lock: (True, "ok"), sweep_fn=lambda: {"running": True})
        self.assertEqual(w, "a vault sweep is reading now")

    def test_a_pc_that_never_swept_says_so(self):
        w = ca._vault_empty_why(may_fn=lambda lock: (True, "ok"), sweep_fn=lambda: {"running": False})
        self.assertEqual(w, "no vault sweep has run on this PC yet")

    def test_a_lock_that_cannot_be_asked_is_said_never_guessed(self):
        def boom(lock):
            raise RuntimeError("fixture")
        w = ca._vault_empty_why(may_fn=boom, sweep_fn=lambda: {"running": False})
        self.assertIn("could not be told (RuntimeError)", w)


class ALedgerWithRowsIsServedAsBefore(unittest.TestCase):

    def test_rows_ask_nothing_and_change_nothing(self):
        asked = []
        for v0 in (_view(owned=3), _view(seen=2)):
            v = ca._vault_ledger_explained(v0, why_fn=lambda: asked.append(1) or "x")
            self.assertIs(v, v0)
        self.assertEqual(asked, [], "a ledger with rows asked why it is empty")

    def test_an_unreadable_ledger_keeps_its_incomplete_say(self):
        v0 = _view(say="could not read accum — what follows is INCOMPLETE, not empty")
        v = ca._vault_ledger_explained(v0, why_fn=lambda: "x")
        self.assertIs(v, v0, "an INCOMPLETE ledger was called empty")


class TheRouteServesTheExplainedView(unittest.TestCase):

    def test_the_route_wraps_the_view(self):
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        at = src.index('if path == "/api/vault_ledger":')
        blk = src[at:src.index("if path ==", at + 10)]
        self.assertIn("self._json(200, _vault_ledger_explained(vault_ledger_view()))", blk)

    def test_the_view_itself_asks_no_lock(self):
        """the view stays a read of its two stores: a law that drives it on fixture stores never reaches the live census"""
        d = tempfile.mkdtemp(prefix="emptyledger_")
        self.addCleanup(shutil.rmtree, d, True)
        ap, sp = os.path.join(d, "vault_accum.json"), os.path.join(d, "vault_seen.json")
        for p, blob in ((ap, {"owned": []}), (sp, {"rows": []})):
            with io.open(p, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(blob))
        with mock.patch.object(ca, "VAULT_LEDGER_PATH", ap), mock.patch.object(ca, "_VAULT_SEEN_PATH", sp), \
                mock.patch.object(ca, "_vault_empty_why", side_effect=AssertionError("the view asked a lock")):
            v = ca.vault_ledger_view()
        self.assertNotIn("emptyWhy", v)


RED_PROOF = [
    {
        "why": "REG-3353 - the route serves the bare view again: an empty ledger says 0 rows and never why",
        "file": "control_app.py",
        "find": "            self._json(200, _vault_ledger_explained(vault_ledger_view()))\n",
        "replace": "            self._json(200, vault_ledger_view())\n",
        "matches": 1,
    },
    {
        "why": "REG-3353 - a shut sweep lock is not named: the empty ledger hides that no sweep may start",
        "file": "control_app.py",
        "find": "        if not ok:\n            parts.append(\"no vault sweep may start on this PC - %s\"",
        "replace": "        if False:\n            parts.append(\"no vault sweep may start on this PC - %s\"",
        "matches": 1,
    },
    {
        "why": "REG-3353 - the empty why is never appended to the say",
        "file": "control_app.py",
        "find": "            return dict(v, emptyWhy=w, say=\"%s Empty because %s.\" % (str(v.get(\"say\") or \"\").rstrip(), w))\n",
        "replace": "            return dict(v, emptyWhy=w)\n",
        "matches": 1,
    },
    {
        "why": "REG-3353 - a ledger WITH rows is told it is empty too",
        "file": "control_app.py",
        "find": "        if t.get(\"owned\") or t.get(\"sightings\") or \"INCOMPLETE\" in str(v.get(\"say\") or \"\"):\n            return v\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "REG-3353 - the last sweep loses its age: a two-day-old answer reads as now",
        "file": "control_app.py",
        "find": "            parts.append(\"the last vault sweep%s: %s\" % (_age,",
        "replace": "            parts.append(\"the last vault sweep%s: %s\" % (\"\",",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
