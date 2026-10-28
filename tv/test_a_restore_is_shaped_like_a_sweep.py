# -*- coding: utf-8 -*-
"""A RESTORE PROPOSAL MUST BE SHAPED LIKE A SWEEP — THIS DOOR HAD NEVER APPLIED ANYTHING.

`ledger_restore.proposal_from()` built `add[half][name] = []` — a DICT keyed by name. The board's
`chronicleApply` in bible.html does `(add.uniques || []).forEach(...)`, and a plain object has no
`forEach`. So every restore that ever reached the board died with
*"(add.uniques || []).forEach is not a function"* and wrote NOTHING.

MEASURED 2026-09-16 on his live board, restoring 85 uniques + 50 sets after an install-id change
wiped his visible ledger: the call REACHED bible.html — the TypeError quotes bible.html's own
v2690 comment back — and every count was unchanged afterwards. With the shape corrected, the same
proposal moved foundLog 363 -> 445, setPieces 83 -> 133, chronFound 280 -> 309.

⚠⚠ WHY NOTHING CAUGHT IT FOR 478 VERSIONS. `plan()` is read-only and its counts were always
correct, so the dry run, the plan endpoint and every test of them looked right. The only half that
was wrong was the half that crosses into the board, and nothing on the Python side of that boundary
could see it. Two halves, each correct on its own, joined at neither. [[the-unjoined-end]]

⚠ THE SHAPE IS NOT INVENTED HERE. A real sweep already ships `"wouldAdd": {lg: [{"name": n, ...}]}`
at two call sites in control_app.py, and `proposal_from`'s own docstring promises "the same
vocabulary a sweep uses". It said so and did the other thing — so this pins the PROMISE, not a
number. [[regression-guard]] [[source-reading-guard]]
"""
import ast
import io
import json
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

import ledger_restore as LR


def _plan(uni, sets):
    return {"ok": True, "file": "ledger_test.json",
            "stores": {"foundLog": {"half": "uniques", "missing": list(uni)},
                       "setPieces": {"half": "sets", "missing": list(sets)}}}


class TestARestoreIsShapedLikeASweep(unittest.TestCase):

    def test_each_half_is_a_list_the_board_can_forEach(self):
        """The defect exactly: an object has no forEach, so the board threw and wrote nothing."""
        wa = (LR.proposal_from(_plan(["Shako", "Mara's Kaleidoscope"], ["Tal Rasha's Fine-Spun Cloth"]))
              or {}).get("wouldAdd") or {}
        self.assertTrue(wa, "proposal_from returned nothing for a plan with two real gaps")
        for half in ("uniques", "sets"):
            self.assertIn(half, wa, "the %s half vanished from the proposal" % half)
            self.assertIsInstance(
                wa[half], list,
                "wouldAdd.%s is %s, not a list — bible.html calls .forEach on it and a plain "
                "object has none, which is the live defect this pins"
                % (half, type(wa[half]).__name__))

    def test_every_row_carries_a_name_the_board_reads(self):
        """bible.html reads `row && (row.name || row)`. A row with neither is a silent skip."""
        wa = (LR.proposal_from(_plan(["Shako"], ["Angelic Halo (ring)"])) or {}).get("wouldAdd") or {}
        seen = 0
        for half, rows in wa.items():
            for row in rows:
                seen += 1
                name = row.get("name") if isinstance(row, dict) else row
                self.assertTrue(
                    isinstance(name, str) and name.strip(),
                    "a %s row carries no readable name (%r) — the board would skip it in silence"
                    % (half, row))
        # ⚠ a denominator, so a vacuous pass cannot wear a green tick [[zero-needs-a-denominator]]
        self.assertEqual(seen, 2, "expected 2 rows to inspect, inspected %d" % seen)

    def test_it_survives_json_round_trip_to_the_board(self):
        """The proposal crosses into JS as JSON. A shape that only holds in Python is no shape."""
        prop = LR.proposal_from(_plan(["Shako"], []))
        rt = json.loads(json.dumps(prop))
        self.assertIsInstance(rt["wouldAdd"]["uniques"], list)
        self.assertEqual(rt["wouldAdd"]["uniques"][0]["name"], "Shako")

    def test_no_gap_still_means_no_proposal(self):
        """The opposite error: a restore with nothing to add must stay None, not ship an empty add."""
        self.assertIsNone(LR.proposal_from(_plan([], [])),
                          "a plan with no missing names produced a proposal — that would ask the "
                          "board to apply nothing and report it as a restore")


class TheOtherStoresHaveADoorAndACaller(unittest.TestCase):
    """⚠⚠ `BACKED_UP_ONLY` NAMED THREE UNBUILT PATHS FOR 480 VERSIONS, THEN TWO WERE BUILT AND
    NOTHING CALLED THEM.

    `plan()['why']` has ended "...are backed up but cannot be restored through the chronicle door
    and need their own path" since v2735. v3213 built `rw_restore`, v3214 built `owned_restore` —
    each with a route, a confirm guard, a world check and a red-proved hop — and a cross-family
    review then found they had NO CALLER anywhere in the tree. Two complete doors nobody could
    open. control_ui.html already records CI reddening v2735 for the identical shape: *"a route
    with no caller is plumbing with no tap"*.

    MEASURED before the join: the chronicle restore moved foundLog 363->445 and setPieces 83->133
    while `owned` sat at 52 against a snapshot's 172 and `rwMade` at 0 against 99 — a restore
    reporting success having covered two stores of four. [[the-unjoined-end]] [[plumbing-with-no-tap]]
    """

    def setUp(self):
        self.src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = self.src.find("def ledger_restore_apply(")
        self.assertGreater(i, 0, "ledger_restore_apply is gone")
        j = self.src.find("\ndef ", i + 10)
        self.body = self.src[i:j if j > 0 else len(self.src)]
        self.assertLess(len(self.body), 9000,
                        "the extracted body is %d chars — that is not one function, so this is "
                        "reading past it" % len(self.body))

    def test_the_chronicle_restore_does_NOT_drive_the_owned_door(self):
        """#246 W0d — REVERSED, AND ledger_restore.py's OWN CONTRACT IS WHY. `owned` is "BACKED UP but NOT
        restorable here", and v3215 called owned_restore(confirm=True) from inside a restore he confirmed
        for the CHRONICLE — on 2026-09-16 that turned a backup's 171-name owned list into 152 mule filings
        with no witness behind any of them. owned_restore stays its own door, confirm required."""
        code = "\n".join(l.split("#", 1)[0] for l in self.body.split("\n"))
        self.assertNotIn("owned_restore(", code,
                         "ledger_restore_apply calls owned_restore again — a chronicle restore puts a "
                         "found-ever owned list back as possession, and the sorter files it")

    def test_the_apply_drives_the_runeword_door(self):
        self.assertIn("rw_restore(", self.body,
                      "ledger_restore_apply no longer calls rw_restore, so the runewords stay at "
                      "0 while the call reports success")

    def test_each_door_answers_for_itself(self):
        """'the uniques came back and the runewords did not' must be sayable."""
        self.assertIn("alsoRestored", self.body,
                      "the other doors' results are not reported separately, so a partial restore "
                      "cannot be told from a complete one")

    def test_a_store_with_no_door_is_named_not_dropped(self):
        import ledger_restore as _LR
        self.assertIn("gameFound", _LR.BACKED_UP_ONLY,
                      "gameFound left BACKED_UP_ONLY — it still has no door, and dropping it from "
                      "the list would make an unrestorable store look restored")
        src = io.open(os.path.join(HERE, "ledger_restore.py"), encoding="utf-8").read()
        self.assertIn("gameFound", src.split("def backed_up_only_from")[1][:2200],
                      "the backup reader says nothing about gameFound, so the one store still "
                      "without a path would vanish from the report instead of being declared")


class AConfirmMustBeAnActualYes(unittest.TestCase):
    """⚠⚠ `bool("false")` IS True, AND EVERY LEDGER-WRITING DOOR USED IT.

    Found by a cross-family (OpenAI) review of v3214, ranked first of four. JSON bodies routinely
    carry booleans as text, so `{"confirm": "false", "names": [...]}` coerced to True and performed
    the restore the body was explicitly declining. `owned_restore`, `rw_restore` and
    `ledger_restore_apply` all read `bool(body.get("confirm"))`, and all three guard a write to his
    ledger — the one class of action this repo makes him ask for twice on purpose.

    ⚠ A WHITELIST, because the dangerous direction is acting UNASKED. Anything not recognised as an
    explicit yes is a no, including shapes nobody anticipated. [[unknown-stays-unknown]]
    """

    def setUp(self):
        sys.path.insert(0, HERE)
        os.environ.setdefault("TV_STUB", "1")
        import control_app as ca
        self.ca = ca

    def test_the_string_false_does_not_confirm(self):
        for v in ("false", "False", "FALSE", "0", "no", "off", ""):
            self.assertFalse(self.ca._confirmed(v),
                             "%r was taken as a yes — a body that says no would write his ledger" % v)

    def test_a_real_yes_still_confirms(self):
        for v in (True, "true", "True", "yes", "1", 1, "on"):
            self.assertTrue(self.ca._confirmed(v),
                            "%r no longer confirms, so the door he deliberately asked for refuses "
                            "him" % v)

    def test_an_unanticipated_shape_is_a_no(self):
        for v in (None, [], {}, {"a": 1}, 2, object()):
            self.assertFalse(self.ca._confirmed(v),
                             "%r was taken as a yes — an unrecognised shape must never authorise "
                             "a write" % (v,))

    def test_every_confirm_gated_door_uses_it(self):
        """A helper two of three doors use is the next silent regression."""
        # ⚠ THE CALL FORM, NOT THE PHRASE. The first cut counted 'bool(body.get("confirm"))'
        # anywhere in the file and failed on the DOCSTRING that explains the defect — a guard that
        # forbids describing the bug it guards against. Judging code means ignoring prose.
        # [[measured-true-read-wrong]] [[source-reading-guard]]
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        stale = src.count('confirm=bool(body.get("confirm"))')
        self.assertEqual(stale, 0,
                         "%d door(s) still coerce confirm with bool(), so the string 'false' "
                         "authorises a write there" % stale)
        self.assertGreaterEqual(src.count('_confirmed(body.get("confirm"))'), 3,
                                "fewer than three doors route through _confirmed — one of them is "
                                "reading the raw body again")


class ARestoredItemIsFiledNotDumped(unittest.TestCase):
    """⚠⚠⚠ THE RESTORE PUT HIS POSSESSIONS BACK AND LEFT EVERY ONE OF THEM IN THE DOCK.

    His words, looking at the vault: *"its not even sorting them.. only some"*. MEASURED: dock 198,
    assigned 21, and a read-only route probe showed **all 198 already had a valid destination** —
    uni-armor 67, uni-weap 63, __throwout 46, uni-small 9, shared 7, runewords 5, __keep 1, with
    laneLocked 0. Nothing was mis-routed. Nothing had run.

    The cause was v3214's own `owned_restore`. Every automatic call to `vaultAutoAssign` is gated
    on a chronicleApply having landed something —
    `if (_landedAny && typeof window.vaultAutoAssign === 'function')` — and `owned_restore` writes
    `d2r_owned` directly through LSR, which is correct for restoring possession and means the
    sorter never fires. The arithmetic matched exactly: 52 owned with 21 assigned (dock ~31) plus
    171 restored = 198.

    ⚠ AND THE FIX FOR REG-1010 MADE IT WORSE BEFORE IT MADE IT BETTER: v3215 reloaded the whole
    board after each write, which kept the data safe and still left it unfiled. Re-reading the Set
    (`_vaultReloadOwned`) and then filing is what closes both. [[the-unjoined-end]]
    """

    def setUp(self):
        self.src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()

    def _door(self, name):
        tree = ast.parse(self.src)
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef) and fn.name == name:
                for n in ast.walk(fn):
                    # ⚠ match the FAMILY, not one member: v3224 gave rw_restore its own
                    # re-reader (_vaultReloadRwMade), and a helper pinned to the owned one simply
                    # stopped finding that door and returned "" — which every assertion below
                    # would then read as "absent". [[source-reading-guard]]
                    if isinstance(n, ast.Constant) and isinstance(n.value, str) \
                       and "_vaultReload" in n.value:
                        return n.value
        return ""

    def test_a_possession_write_re_reads_the_live_set(self):
        for door in ("owned_restore", "rw_restore"):
            js = self._door(door)
            self.assertTrue(js,
                            "%s no longer re-reads the board's in-memory set after writing, so "
                            "the next persist() overwrites the restore from the boot-time copy "
                            "(REG-1010)" % door)

    def test_a_possession_write_never_presses_the_sorter(self):
        """#246 W0d — REVERSED BY HIS RULING. v3222 made a restore FILE what it wrote: `owned` is
        ticked-or-found-ever, not a sighting in his stash, and this exact post-hook is how a backup
        became 152 mule filings on 2026-09-16 (20:12:49). A restore puts possession RECORDS back; the
        names wait in the dock for a witness or his hand. Both possession doors, both halves."""
        for door in ("owned_restore", "rw_restore"):
            js = self._door(door)
            self.assertTrue(js, "%s's board script could not be found — this law would grade nothing" % door)
            self.assertNotIn("vaultAutoAssign", js,
                             "%s presses the sorter again — a restored possession record becomes a "
                             "mule filing with no witness behind it" % door)

    def test_the_reload_survives_as_the_fallback(self):
        """The blunt fix must stay for a build without the re-read door — stale memory DESTROYS."""
        js = self._door("owned_restore")
        self.assertIn("location.reload", js,
                      "the reload fallback is gone, so on a board without _vaultReloadOwned the "
                      "write is left behind stale memory and the next persist() erases it")

    def test_each_door_re_reads_ITS_OWN_store(self):
        """⚠⚠ v3222 POINTED BOTH DOORS AT THE SAME RE-READER AND ONE OF THEM TOUCHES A DIFFERENT
        STORE. `_vaultReloadOwned` re-reads `d2r_owned` and nothing else, so `rw_restore` wrote
        `d2r_rwMade`, got a number back (because d2r_owned was readable), SKIPPED the reload, and
        left `rwMade` stale — REG-1010 reintroduced for the runewords, where `rwToggleMade` writes
        the in-memory object back over them. Named by a cross-family look at v3222:
        *"do not skip reload on rw_restore unless something actually re-binds rwMade"*.
        [[copy-drift]] [[the-unjoined-end]]"""
        owned_js = self._door("owned_restore")
        rw_js = self._door("rw_restore")
        self.assertIn("_vaultReloadOwned", owned_js,
                      "owned_restore no longer re-reads d2r_owned")
        self.assertIn("_vaultReloadRwMade", rw_js,
                      "rw_restore re-reads the wrong store, so it skips its reload while rwMade "
                      "stays stale and the next tick erases the restored runewords")
        self.assertNotIn("_vaultReloadOwned", rw_js,
                         "rw_restore is still pointed at the owned re-reader — a door that asks "
                         "about a store it did not write")

    def test_the_board_exposes_both_re_read_doors(self):
        bible = io.open(os.path.join(os.path.dirname(HERE), "bible.html"),
                        encoding="utf-8", errors="replace").read()
        for fn_name, store in (("_vaultReloadOwned", "d2r_owned"),
                               ("_vaultReloadRwMade", "d2r_rwMade")):
            self.assertIn("window." + fn_name, bible,
                          "bible.html no longer exposes %s, so its door falls back to rebooting "
                          "his page" % fn_name)
            # ⚠ BOTH ENDS. `bible[i:i + 500]` is a guess about how long the function is, and
            # a function grows every time somebody documents it — which is exactly how the
            # /api/river guard came to examine nothing. The re-reader is a one-liner that ends at
            # its own closing brace; find that instead. [[source-window-shortcut]]
            i = bible.find("window." + fn_name)
            _end = bible.find("};", i)
            self.assertGreater(_end, i, "could not find the end of %s — re-anchor" % fn_name)
            self.assertIn(store, bible[i:_end],
                          "%s does not read %s — a re-reader pointed at the wrong store is worse "
                          "than none, because it answers and the caller believes it"
                          % (fn_name, store))

    def test_the_board_exposes_the_re_read_door(self):
        bible = io.open(os.path.join(os.path.dirname(HERE), "bible.html"),
                        encoding="utf-8", errors="replace").read()
        self.assertIn("window._vaultReloadOwned", bible,
                      "bible.html no longer exposes _vaultReloadOwned, so every restore falls back "
                      "to rebooting his page")
        i = bible.find("window._vaultReloadOwned")
        _end = bible.find("};", i)
        self.assertGreater(_end, i, "could not find the end of _vaultReloadOwned — re-anchor")
        self.assertIn("Array.isArray(fresh)", bible[i:_end],
                      "the re-read no longer refuses an unreadable store — an unparseable "
                      "d2r_owned would blank the live Set, which is a wipe, not a refresh")

RED_PROOF = [
    {"why": "v3213 - a restore proposal is a dict keyed by name again: the board's forEach throws and writes nothing",
     "file": "tv/ledger_restore.py",
     "find": "            add[half].append({\"name\": name})\n",
     "replace": "            add[half] = add[half] if isinstance(add[half], dict) else {}\n            add[half][name] = []\n",
     "matches": 1},
    {"why": "v3216 - a confirm reads bool() again: the string \"false\" says yes and a ledger write the body declined is performed",
     "file": "tv/control_app.py",
     "find": "    if v is True:\n        return True\n    if isinstance(v, str):\n        return v.strip().lower() in (\"true\", \"yes\", \"y\", \"1\", \"on\")\n",
     "replace": "    if v is True:\n        return True\n    if isinstance(v, str):\n        return bool(v)\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
