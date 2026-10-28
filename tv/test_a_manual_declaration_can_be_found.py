#!/usr/bin/env python3
"""A MANUAL DECLARATION CAN BE FOUND — the writer had no reachable reader.

HIS RULING behind ledger_authority.manual_accept: *"the manual is also a bypass we said like
witnesses are not needed for a manual toggle me or dean.. or user."* And #166: *"manual anything
is enough witness obivously."*

THE GAP, measured. `manual_accept` writes an append-only record keyed by WORLD. `manual_for`
finds the latest record for one world+ledger, and `classify_row(tally, world=None, ...)` passes
that world through. control_app.grail_tally called it as `classify_row(out)` — world=None — so a
declaration made for a real world could never be matched. A door with a writer and no reader.

⚠ AND MY FIRST DIAGNOSIS WAS WRONG IN A WAY WORTH PINNING. I checked whether the world was
available by calling board_ownership() inside my OWN process, where it answers {ok, why} alone
because _BOARD_WIN is None by construction, and concluded `route` did not exist. Asked of the LIVE
console it returns {"id": …, "p": "main", "m": "owner", "pfx": ""}, which world_key resolves.
Measuring in the wrong process is the same error as reading a live figure off a fresh import.

⚠ THE WORLD MUST STAY OPTIONAL. When the board window is shut the tally still runs, and the
verdict must behave exactly as before rather than inventing a world — world_key refuses an empty
id on purpose, precisely so a guessed world cannot match every id-less board at once.
[[the-unjoined-end]] [[unknown-stays-unknown]]
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

import ledger_authority as LA


def _call_kwargs(fn_name, callee):
    """The keywords grail_tally passes to classify_row, parsed. [[source-reading-guard]]"""
    with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    fn = None
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == fn_name:
            fn = n
    assert fn is not None, "%s is gone from control_app" % fn_name
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == callee:
            out.append([k.arg for k in n.keywords])
    return out


class AManualDeclarationCanBeFound(unittest.TestCase):

    def test_the_tally_tells_the_authority_which_world_it_is_about(self):
        # #240 — the world now travels in two hops: grail_tally hands it to the seal, and the seal
        # asks the authority AFTER `ok` is decided (asked earlier, every verdict read ok:False).
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        gt = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "grail_tally")
        hop1 = [[k.arg for k in n.keywords] for n in ast.walk(gt)
                if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_seal_tally_verdict"]
        print("   _seal_tally_verdict calls in grail_tally: %r" % (hop1,))
        self.assertTrue(any("world" in kw for kw in hop1),
                        "grail_tally no longer hands its world to the seal")
        calls = _call_kwargs("_seal_tally_verdict", "classify_row")
        print("   classify_row calls in the seal: %r" % (calls,))
        self.assertTrue(calls, "the seal no longer classifies its row at all")
        self.assertTrue(any("world" in kw for kw in calls),
                        "classify_row is called without a world, so manual_for looks up world=None "
                        "and a declaration made on a real board can never be found — the writer "
                        "keeps working and nothing can read it")

    def test_world_key_resolves_a_real_board_route(self):
        """The shape the console actually publishes, not one invented for the test."""
        route = {"id": "0123456789abcdef0123456789abcdef", "p": "main", "m": "owner", "pfx": ""}
        key = LA.world_key(route)
        print("   world_key(route) -> %r" % (key,))
        self.assertTrue(key, "the live board's route shape does not resolve to a world key")
        self.assertIn("|", key, "a world key is install id + profile")

    def test_an_id_less_world_is_refused(self):
        """⚠ THE HOLE ITS OWN LAW CAUGHT ONCE: a profile with no install id must NOT resolve, or
        one declaration matches every id-less board at once."""
        for bad in ({"p": "main"}, {"id": "", "p": "main"}, {}, None):
            self.assertFalse(LA.world_key(bad),
                             "world_key accepted %r — that declaration would match every "
                             "id-less world" % (bad,))
        print("   id-less worlds refused: 4 of 4")

    def test_a_shut_board_still_classifies(self):
        """world stays optional: no board window means world=None, not a guessed one."""
        row = LA.classify_row({"uniques": 1, "sets": 0, "runewords": 0}, world=None)
        print("   shut-board verdict: %s" % (type(row).__name__,))
        self.assertIsNotNone(row, "the verdict collapsed when no world was available")

RED_PROOF = [
    {"why": "the seal classifies its row with no world, so manual_for looks up world=None and a real declaration is never found",
     "file": "tv/control_app.py",
     "find": "            out[\"ledgerVerdict\"] = _LA.classify_row(out, world=world)\n",
     "replace": "            out[\"ledgerVerdict\"] = _LA.classify_row(out)\n",
     "matches": 1},
    {"why": "grail_tally stops handing its world to the seal, so the reader half is unjoined one hop earlier",
     "file": "tv/control_app.py",
     "find": "    return _seal_tally_verdict(out, \"the board answered but carried no counts\", world=_world)\n",
     "replace": "    return _seal_tally_verdict(out, \"the board answered but carried no counts\")\n",
     "matches": 1},
    {"why": "a profile with no install id resolves to a world, so one declaration matches every id-less board at once",
     "file": "tv/ledger_authority.py",
     "find": "    if not ident or not prof:\n        return \"\"\n",
     "replace": "    if not prof:\n        return \"\"\n",
     "matches": 1},
    {"why": "the world key drops the profile, so a declaration for main also answers his ladder world",
     "file": "tv/ledger_authority.py",
     "find": "    return \"%s|%s\" % (ident, prof)\n",
     "replace": "    return ident\n",
     "matches": 1},
    {"why": "with the board window shut there is no world, and the verdict collapses instead of classifying as before",
     "file": "tv/ledger_authority.py",
     "find": "    tbl = table if table is not None else seed_table()\n    t = tally if isinstance(tally, dict) else {}\n",
     "replace": "    if world is None:\n        return None\n    tbl = table if table is not None else seed_table()\n    t = tally if isinstance(tally, dict) else {}\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
