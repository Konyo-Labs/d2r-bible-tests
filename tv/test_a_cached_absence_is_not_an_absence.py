#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2814 — THE FLEET PANEL SAID "HE HAS NOT REPORTED" ABOUT A MACHINE THAT HAD.

Konyo, 2026-09-09, with screenshots. Two sentences from one panel, minutes apart:

    "the fleet is unreachable — The read operation timed out"
    "Dean has not reported which set pieces it holds yet"

MEASURED against the live beacon in the same minute as the second one:

    Dean   ver=v2745   online=TRUE   masks: sets=76ch, uniques=118ch
                                     tally: sets 128/135, uniques 249/403

He had reported BOTH ledgers. Three separate defects sat behind those two sentences.

1. A FAILED FETCH DESTROYED THE GOOD ANSWER. `fleet_presence()` caches 60s and on a timeout did
   `_FLEET_PRESENCE_CACHE["d"] = out` where `out` is the ERROR — so one 6s timeout replaced a
   roster that was working. The card had already rendered from the cached success; the modal, 60
   seconds wide, got the refusal. Strictly worse than no cache: without it the modal would simply
   have re-tried.

2. A STALE ROSTER WAS TREATED AS AN UNREACHABLE FLEET. The cross-reference refused outright on any
   fetch failure, while the card beside it was rendering that same machine's real numbers.

3. "HE HAS NOT REPORTED" WAS CONCLUDED FROM A CACHE. This is a claim about ANOTHER machine — the
   one kind this console cannot check by looking inward — and it was made from a record that can
   be arbitrarily old when a fetch has failed in between. An absence in a cached record is not an
   absence in the world.

★ THE RULE: serve the last good roster with its AGE rather than an error, and make a miss earn one
authoritative re-read before the sentence is allowed to be said.
[[stale-reading]] [[unknown-stays-unknown]] [[zero-needs-a-denominator]]
"""
import os
import ast
import io
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

APP = os.path.join(HERE, "control_app.py")


def _src():
    with io.open(APP, encoding="utf-8") as fh:
        return fh.read()


def _fn(tree, name):
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    return None


class TestACachedAbsenceIsNotAnAbsence(unittest.TestCase):

    def setUp(self):
        self.src = _src()
        self.tree = ast.parse(self.src)

    def test_the_cache_keeps_a_slot_for_the_last_good_answer(self):
        """Without goodD there is nowhere for a good roster to survive a failed fetch.

        ⚠⚠ v2847 — THIS LAW WAS BLIND, AND ITS OWN RED-PROOF SAID SO FOR AS LONG AS IT EXISTED.
        It read `assertIn('"goodD"', self.src)` over the WHOLE of control_app.py. The proof strips
        both slots from the INITIALIZER — the only place their absence matters — and the names go
        on appearing by design in `fleet_presence()` (`_FLEET_PRESENCE_CACHE["goodT"] = now`) and in
        `fleet_presence_last_good()` (`.get("goodD")`). So the substring was found, the law passed,
        and the slot it exists to guard was gone:

            test_a_cached_absence_is_not_an_absence[0]  BLIND ← stayed GREEN through its own
                                                        defeat (1 match(es))

        `assertIn` where a COUNT or a STRUCTURE was needed — the same shape five other laws in this
        repo have been caught in, each staying green through its own defeat because the literal
        occurs more than once on purpose.

        ⚠ AND IT GUARDS SOMETHING LIVE: v2843 built the panel's stale-roster fallback on exactly
        these two slots. A law that cannot see them removed is a law that would have let that
        fallback be deleted silently. [[source-reading-guard]] [[feedback-blind-fixture-green-gate]]
        """
        tree = ast.parse(self.src)
        inits = [n.value for n in ast.walk(tree)
                 if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "_FLEET_PRESENCE_CACHE"
                         for t in n.targets)]
        self.assertEqual(
            len(inits), 1,
            "expected exactly one assignment binding _FLEET_PRESENCE_CACHE to its literal; found "
            "%d. With none this law has lost its subject; with several it would grade whichever it "
            "met first." % len(inits))
        self.assertIsInstance(
            inits[0], ast.Dict,
            "_FLEET_PRESENCE_CACHE is no longer bound to a dict literal, so its slots cannot be "
            "read here and this law would be asserting nothing")
        keys = [k.value for k in inits[0].keys if isinstance(k, ast.Constant)]
        for key in ("goodD", "goodT"):
            self.assertIn(
                key, keys,
                "the presence cache INITIALIZER has no %r slot — it declares %r. A failed fetch "
                "then overwrites the last good roster and the panel loses data it already had, "
                "which is the blank card this whole gate exists to prevent." % (key, keys))

    def test_a_failed_fetch_does_not_replace_the_good_answer(self):
        """The error must not be written over the roster."""
        fn = _fn(self.tree, "fleet_presence")
        self.assertIsNotNone(fn, "fleet_presence is gone")
        body = ast.get_source_segment(self.src, fn) or ""
        self.assertIn("goodD", body,
                      "fleet_presence never consults its last-good slot — a timeout still "
                      "destroys the roster")
        self.assertIn("staleAgeS", body,
                      "a served-from-cache roster carries no age, so a caller cannot tell it "
                      "from a live one — that is the stale-reading defect")

    def test_the_cross_reference_survives_a_stale_roster(self):
        """A stale roster is not an unreachable fleet."""
        fn = _fn(self.tree, "fleet_xref") or _fn(self.tree, "fleet_cross_reference")
        if fn is None:
            # resolve by the sentence it prints rather than by a name that may drift
            self.assertIn("the fleet is unreachable", self.src)
            i = self.src.index("the fleet is unreachable")
            region = self.src[max(0, i - 1200):i + 400]
        else:
            region = ast.get_source_segment(self.src, fn) or ""
        self.assertIn("_fleet_stale", region,
                      "the refusal does not distinguish a STALE roster from an unreachable "
                      "fleet, so a cached-but-real answer is thrown away")

    def test_a_missing_mask_earns_one_authoritative_reread(self):
        """The decisive law. 'He has not reported' must not be said from a cache."""
        self.assertIn("fleet_presence(force=True)", self.src,
                      "nothing ever forces a fresh read, so 'he has not reported which pieces it "
                      "holds' is concluded from a record that may predate his publishing them — "
                      "measured wrong on 2026-09-09 against a beacon carrying both masks")
        # ⚠ THE ENCLOSING FUNCTION, NOT A BYTE WINDOW. The first cut of this assertion read
        # `self.src[i-3000:i]` and went red on correct code, because the function's docstring is
        # longer than the guess. A window measured in characters measures my guess, not the file —
        # committed here, in the gate written to stop exactly this class of error.
        # [[source-window-shortcut]]
        owner = None
        # ⚠ SPLIT ONCE. ast.get_source_segment re-splits the WHOLE 2.8 MB source on every call: 822 functions before the
        # owner x 0.72 s on his Mac = ~590 s, so this law timed out at 300 s locally (19 s on CI). The lines slice to the
        # same function body.
        _lines = self.src.splitlines(True)
        for n in ast.walk(self.tree):
            if isinstance(n, ast.FunctionDef):
                seg = "".join(_lines[n.lineno - 1:n.end_lineno])
                if "has not reported which" in seg:
                    owner = (n, seg)
                    break
        self.assertIsNotNone(owner, "no function prints the 'has not reported' sentence")
        _n, seg = owner
        self.assertIn("force=True", seg,
                      "the forced re-read is not in the same function that prints the sentence, "
                      "so the claim is still made from the cached view")
        # ⚠ LINE NUMBERS FROM THE PARSE, NOT string.index(). The first cut compared
        # `seg.index(...)` offsets and failed on correct code: "has not reported which" occurs in a
        # COMMENT ~50 lines above the assignment that actually composes the sentence, so it
        # measured the wrong occurrence of a string that appears twice. Third time tonight that a
        # first-occurrence match has been the wrong one. [[source-reading-guard]]
        _reread = [c.lineno for c in ast.walk(_n)
                   if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                   and c.func.id == "fleet_presence"
                   and any(k.arg == "force" for k in (c.keywords or []))]
        _says = [a.lineno for a in ast.walk(_n)
                 if isinstance(a, ast.Assign)
                 and "has not reported which" in "".join(_lines[a.lineno - 1:a.end_lineno])]
        self.assertTrue(_reread, "no forced re-read call inside the function")
        # v3866 - THE RE-READ MUST BE THE LEDGER'S OWN. v3866 added a second forced read in this function (the jewels'
        # mask, REG-3221), and with the ledger's own re-read deleted this law stayed GREEN on the jewels' call (the proof
        # shard found it BLIND). So the call must sit inside the `if their_mask is None:` block that guards the sentence.
        _own = [c.lineno for i in ast.walk(_n)
                if isinstance(i, ast.If) and "their_mask is None" in _lines[i.lineno - 1]
                for c in ast.walk(i)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "fleet_presence"
                and any(k.arg == "force" for k in (c.keywords or []))]
        self.assertTrue(_own, "the ledger's own missing mask is never re-read by force - another forced read in this "
                              "function (the jewels') does not stand in for it")
        self.assertTrue(_says, "nothing in this function ASSIGNS the sentence")
        self.assertLess(min(_reread), min(_says),
                        "the forced re-read is at line %d and the sentence is composed at line %d "
                        "— the panel would state an absence it had not re-checked"
                        % (min(_reread), min(_says)))


# ══ THE EXECUTABLE RED-PROOF ═════════════════════════════════════════════════════════════════
RED_PROOF = [
    {
        "why": "removing the last-good slot returns a timeout to destroying the roster",
        "file": "control_app.py",
        "find": '_FLEET_PRESENCE_CACHE = {"t": 0.0, "d": None, "goodT": 0.0, "goodD": None}',
        "replace": '_FLEET_PRESENCE_CACHE = {"t": 0.0, "d": None}',
        "matches": 1,
    },
    {
        "why": "without the forced re-read the panel again claims an absence it only cached",
        "file": "control_app.py",
        "find": "            _fresh = fleet_presence(force=True)\n            _forced = True\n",
        "replace": "            _fresh = None\n            _forced = True\n",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
