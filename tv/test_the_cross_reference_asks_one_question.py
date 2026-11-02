# -*- coding: utf-8 -*-
"""HIS CROSS-REFERENCE READ 160/398 BESIDE A BOARD THAT SAYS 292/403 — TWO WRONG HALVES.

Konyo: *"the crossreference ... isnt really synced to the uniques"*, and later, flatly:
*"which one is it really?!!? is it 398 or 403 make a unifed logic"*.

BOTH HALVES WERE WRONG, FOR DIFFERENT REASONS.

=== THE NUMERATOR — a store that answers a different question ===
`fleet_mask.LEDGERS["uniques"]["store"]` was `d2r_owned` — the VAULT store — while
control_app.py:1997 repointed the uniques TALLY to the chronicle pair at v2717 and renamed the old
measure `vaultUniques`. Nothing updated the spec. So the panel answered "what is in his vault"
under a label meaning "what his Chronicle records". SETS was immune because both its sides read
`d2r_setPieces`, which is exactly why one tab was right and the other wrong.

⚠ AND IT IS A UNION, NOT ONE STORE. `bible.html:42994`'s `_ownedNames()` IS the definition of
"found" on his board: `d2r_owned` together with `keys(d2r_foundLog)`, commented "found = ledger +
LEGACY owned". Pointing at `d2r_foundLog` alone would be correct only IF the two happened to be
nested today — a coincidence, not a definition, and the legacy store is precisely where a
long-running grail keeps its oldest finds.

=== THE DENOMINATOR — a number the page itself says means nothing ===
The panel rendered `rosterN` = `len(roster)` = 398. bible.html:3755 had already ruled:
    403  chronTotal — HIS PINNED RULING, the game's own Chronicle count
    392  funiScan().total — the carded roster after his v2680 one-tally-per-sunder ruling
    398  "produced by neither, and NO array on the page is this size"
⚠⚠ BUT `rosterN` CANNOT SIMPLY BECOME 403. `fleet_mask.decode()` REFUSES any mask whose `n` does
not equal `len(roster)` — that equality is what proves both machines packed the same roster into
the same bit positions. Changing it would make every mask on the fleet undecodable. So 403 gets
its OWN field and `rosterN` keeps its job.

=== ⚠⚠ AND THE FIX HAD A LANDMINE AIMED AT ITSELF ===
`corroborate`'s count-and-mask invariant held a SECOND, hardcoded copy of the ledger->store map
with "uniques" simply absent — so the exclusion was accidental rather than stated. Its LEFT side is
dynamic and would start counting uniques the moment this fix shipped; its RIGHT side, frozen in a
literal, would not. The invariant would have gone RED because the code got MORE correct. It now
asks `ledger_authority.surface_pairs()` — one authority, no second copy. [[copy-drift]]

⚠ Fixing that, I referenced `la` in the right closure where it is imported only in the left, and my
own `except Exception: return None` SWALLOWED the NameError — right went 1 -> None while left went
1 -> 2. Caught by watching the numbers, not by anything failing. Same shape as the `qs` defect in
/api/river the same day.
"""
import ast
import io
import json
import os
import re
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

import fleet_mask as FM  # noqa: E402
import ledger_authority as LA  # noqa: E402

CA_SRC = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
CORR = io.open(os.path.join(HERE, "corroborate.py"), encoding="utf-8").read()


def _py_code(src):
    """Python source with comments stripped — never grade prose. [[source-reading-guard]]"""
    return re.sub(r"(?m)^\s*#[^\n]*", "", src)


def _js_code(src):
    src = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), src, flags=re.S)
    return re.sub(r"(?m)//[^\n]*", lambda m: " " * len(m.group(0)), src)


class TheCrossReferenceAsksOneQuestion(unittest.TestCase):

    def _constructed_roster(self, n=12):
        """REG-2375 - THE UNIVERSE CASES DRIVE A ROSTER THEY BUILT, NEVER ONE THEY FIND.

        They asked surface_pairs() for the uniques roster size and SKIPPED when it answered nothing. On his census
        (2026-10-21, 2 of 18 cases SKIPPED) the roster read nothing in that proving sandbox - a lane its neighbours had
        already run in - so the one case that catches proof [4] never ran, the other 16 stayed green, and the proof
        read BLIND: a skip filed as a law that cannot go red, and one BLIND held every lock. The subject is the
        exclusion's reason, not his roster, so the roster is constructed here and fed through the one reader both
        surface_pairs() and mask_cross_check() use (fleet_mask.load_roster_for). -> its length"""
        names = ["law roster name %02d" % i for i in range(n)]
        real = FM.load_roster_for

        def _fake(ledger):
            return (list(names), "law-roster") if str(ledger or "").strip().lower() == "uniques" else real(ledger)
        patch = mock.patch.object(FM, "load_roster_for", _fake)
        patch.start()
        self.addCleanup(patch.stop)
        got = [p.get("maskRosterN") for p in (LA.surface_pairs() or []) if p.get("ledger") == "uniques"]
        self.assertEqual([n], got, "PREMISE: surface_pairs() did not read the constructed roster, so the live path "
                                   "below would not be the one this law grades: %r" % got)
        return n

    # ── ⚠⚠ THE LAW: ONE QUESTION, PROVEN BY THE REPO'S OWN DETECTOR ───────────────────────────
    def test_every_ledger_reads_the_SAME_store_on_both_sides(self):
        """`surface_pairs()` exists to detect exactly this and reported uniques
        `sameQuestion: false` for weeks with nothing acting on it. It is the proof, not a proxy."""
        pairs = {str(p.get("ledger")): p for p in (LA.surface_pairs() or [])}
        self.assertTrue(pairs, "surface_pairs answered nothing — fix this guard first")
        bad = {k: (v.get("tallyStore"), v.get("maskStore"))
               for k, v in pairs.items()
               if not (v.get("tallyStore") and v.get("maskStore")
                       and v.get("tallyStore") == v.get("maskStore"))}
        self.assertEqual({}, bad,
                         "a ledger's mask and tally still read different stores, so their numbers "
                         "are not comparable and the panel prints one label over two questions: %r"
                         % bad)

    def test_the_union_is_declared_on_EVERY_ledger(self):
        """⚠ A field present on one entry and absent on another is how a caller learns to write
        `.get("stores") or [spec["store"]]` in three places and forget it in a fourth."""
        for led, spec in FM.LEDGERS.items():
            self.assertIn("stores", spec, "%s declares no `stores`" % led)
            self.assertIsInstance(spec["stores"], list, "%s.stores is not a list" % led)
            self.assertIn(spec["store"], spec["stores"],
                          "%s's primary store is not among its stores — the string the detector "
                          "compares and the list the mask reads have diverged" % led)

    def test_uniques_reads_the_legacy_store_TOO(self):
        """The union is the whole point: `_ownedNames()` is `d2r_owned` + `keys(d2r_foundLog)`,
        and the legacy store is where the oldest finds live."""
        self.assertIn("d2r_owned", FM.LEDGERS["uniques"]["stores"],
                      "the legacy store was dropped, so a find recorded only there is invisible "
                      "to the mask while the board still counts it")
        self.assertEqual("d2r_foundLog", FM.LEDGERS["uniques"]["store"],
                         "the primary store is no longer the tally's store")

    # ── the mask must actually READ the union ────────────────────────────────────────────────
    def test_board_mask_reads_the_STORES_not_the_single_store(self):
        code = _py_code(CA_SRC)
        self.assertIn('spec.get("stores") or [spec["store"]]', code,
                      "board_mask still interpolates one store, so the union is declared and not "
                      "read — the spec would promise what the code does not do")
        self.assertIn('"var KS=%s;"', code, "the injected JS no longer takes a list of keys")

    def test_absent_and_unparseable_and_none_are_THREE_states(self):
        """A store this board never wrote is not an error (the legacy one is absent on a fresh
        install). One that exists and will not parse IS a fault. And no store at all is UNKNOWN —
        a board that wrote neither has not said he owns nothing."""
        code = _py_code(CA_SRC)
        self.assertIn("if(rawv==null||rawv===''){continue;}", code, "absent is not skipped")
        self.assertIn("bad.push(K)", code, "an unparseable store is not reported")
        self.assertIn("no store present on this board", code,
                      "a board with neither store returns a mask of zeros rather than UNKNOWN")

    # ── ⚠⚠ rosterN IS LOAD-BEARING AND MUST NOT BECOME THE DISPLAY NUMBER ────────────────────
    def test_rosterN_is_still_the_ROSTER_length(self):
        """decode() refuses a mask whose n != len(roster). If rosterN became 403 every mask on the
        fleet would be refused as a roster mismatch."""
        code = _py_code(CA_SRC)
        self.assertIn('out["rosterN"] = len(roster)', code,
                      "rosterN is no longer the roster length — masks will fail to decode")

    def test_the_denominator_he_reads_comes_from_the_BOARD_and_never_falls_back(self):
        import control_app as CA
        # ⚠⚠ v2760 — THIS LAW WAS RED ON EVERY MACHINE BUT HIS, AND GREEN HERE FOR THE WRONG
        # REASON. It asserted 403 unconditionally, but that number is read out of
        # tv/board_tally.json — which .gitignore:104 IGNORES. On CI, on the Windows console, or in
        # any fresh clone the file is absent, `_fleet_show_total` correctly answers (None, why),
        # and this failed. A gate that can only pass on the machine that happens to hold an
        # untracked fixture is a host-machine dependency wearing a law's clothes.
        # [[feedback-blind-fixture-green-gate]] [[regression-guard]]
        #
        # ⚠ THE FIX IS NOT A skipTest. Skipping would make the venue where it matters most say
        # nothing at all. BOTH BRANCHES ARE THE CONTRACT and both are asserted: with a tally, the
        # number is the chronicle pin and never the roster length; without one, the answer is None
        # WITH A REASON — never a confident fallback. The second half is the half that actually
        # protects him, because a fallback to 398 is what the whole task existed to kill.
        # A bank that still says 403 posted the old file-row count. The fleet shows the pin.
        _has_tally = os.path.exists(os.path.join(HERE, "board_tally.json"))
        n, why = CA._fleet_show_total("uniques")
        if _has_tally:
            import route_totals as RT
            pin = RT.total("unique")
            self.assertEqual(pin, 397)
            self.assertEqual(n, pin,
                             "the fleet denominator is not the chronicle pin")
            self.assertNotEqual(398, n,
                                "the shown denominator fell back to the roster length — the exact "
                                "defect this task removed")
        else:
            self.assertIsNone(n,
                              "no board tally exists on this venue, yet a confident denominator "
                              "was produced — that can only be a fallback, and the only number it "
                              "could fall back to is the 398 roster length")
            self.assertTrue(str(why or "").strip(),
                            "an unknown denominator carries no reason, so the panel would render "
                            "a bare '?' with nothing to say [[unknown-stays-unknown]]")
        n2, why2 = CA._fleet_show_total("__no_such_ledger__")
        self.assertIsNone(n2, "an unknown ledger produced a confident denominator")
        self.assertTrue(why2, "an unknown denominator carries no reason")
        code = _py_code(CA_SRC)
        i = code.find("def _fleet_show_total")
        j = code.find("\ndef ", i + 1)
        self.assertNotIn("rosterN", code[i:j],
                         "the shown denominator falls back to the roster length, which silently "
                         "reinstates the defect and looks correct doing it")

    def test_the_panel_renders_showN_not_rosterN(self):
        js = _js_code(UI)
        self.assertIn("_fxDen(j)", js, "the panel no longer calls the denominator helper")
        self.assertNotIn("j.rosterN", js,
                         "the panel still prints rosterN — the number bible.html says is "
                         "'produced by neither, and NO array on the page is this size'")
        self.assertIn("function _fxDen(j)", js, "the helper is used but not declared")

    def test_the_helper_lives_in_the_SAME_script_block_as_its_caller(self):
        """⚠ A call across this file's two script blocks is a dead render and has cost four
        versions. Both must sit inside the second block."""
        blocks = [m.start() for m in re.finditer(r"(?m)^<script>", UI)]
        self.assertGreaterEqual(len(blocks), 2, "expected two script blocks")
        decl = UI.find("function _fxDen(j)")
        use = UI.find("_fxDen(j) + ' yours")
        self.assertGreater(decl, blocks[1], "_fxDen is declared in the FIRST block")
        self.assertGreater(use, blocks[1], "its caller is in the FIRST block")

    # ── ⚠⚠ THE LANDMINE MUST STAY DISARMED ───────────────────────────────────────────────────
    def test_corroborate_does_not_re_declare_the_ledger_store_map(self):
        code = _py_code(CORR)
        self.assertNotIn('"runewords": "d2r_rwMade"}', code,
                         "corroborate holds its own hardcoded ledger->store map again. That map "
                         "had 'uniques' absent, so the day the real fix shipped its LEFT side "
                         "would count uniques and its RIGHT side would not — the invariant going "
                         "RED because the code got more correct.")
        self.assertIn("la.surface_pairs()", code,
                      "the right side no longer asks the one authority")

    def test_la_is_imported_in_the_closure_that_uses_it(self):
        """⚠ It was not, and my own `except Exception: return None` swallowed the NameError —
        right went 1 -> None while left went 1 -> 2, which reads exactly like 'nothing to
        compare'. A name bound in a sibling scope plus a try that hides the raise."""
        i = CORR.find("_same = {str(p.get(\"ledger\"))")
        self.assertGreater(i, 0, "the surface_pairs read is gone")
        j = CORR.rfind("    def right():", 0, i)
        self.assertGreater(j, 0, "could not find the enclosing closure")
        self.assertIn("import ledger_authority as la", CORR[j:i],
                      "`la` is not imported in the closure that uses it")

    def test_it_still_parses(self):
        ast.parse(CA_SRC)
        ast.parse(CORR)

    # ── ⚠⚠ v2945 — ONE DECIDABLE FLAG, BECAUSE TWO IS TWO CHANCES TO ASK THE WRONG ONE ───────
    def test_a_pair_carries_exactly_ONE_decidable_flag(self):
        """HIS RULING, 2026-09-11: "why is there two separte ones? it needs to be unified as one..
        not two filters that way you wont be able to look at the worng key?"

        He is describing a defect that had ALREADY HAPPENED. `surface_pairs()` published
        `sameQuestion` (same store?) beside a second universe test, the corroborator asked only the
        first, got True for `uniques`, and compared a tally counted out of 403 against a mask that
        can only represent 398. One label, two questions, and the reader picked the wrong one.

        So the shape is the law: ONE key a caller may branch on, and the rest facts. Parsed from
        the dict this function actually returns — never grepped. [[source-reading-guard]]"""
        src = io.open(os.path.join(HERE, "ledger_authority.py"), encoding="utf-8").read()
        fn = next((n for n in ast.walk(ast.parse(src))
                   if isinstance(n, ast.FunctionDef) and n.name == "surface_pairs"), None)
        self.assertIsNotNone(fn, "surface_pairs is gone — this law examined nothing")
        keys = set()
        for d in (n for n in ast.walk(fn) if isinstance(n, ast.Dict)):
            for k in d.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.add(k.value)
        self.assertIn("comparable", keys,
                      "surface_pairs no longer publishes `comparable`, the one flag a caller "
                      "decides on. Keys found: %r" % sorted(keys))
        for retired in ("sameQuestion", "sameUniverse"):
            self.assertNotIn(retired, keys,
                             "`%s` is back alongside `comparable` — that is the two-filter shape "
                             "he ruled out, and the second filter is the one that gets asked by "
                             "mistake" % retired)

    def test_NO_module_still_READS_a_retired_flag(self):
        """A removed key does not fail loudly by itself: `.get("sameQuestion")` on a dict that no
        longer has it returns None, and `None is not True` quietly skips every row. That is exactly
        how `mask_cross_check` came back agreeN=0 / comparableN=0 — a clean-looking zero standing
        for "I asked a question nobody answers any more". [[zero-needs-a-denominator]]

        Reads only — `.get("x")` and `["x"]`. Prose may discuss the history freely."""
        RETIRED = {"sameQuestion", "sameUniverse"}
        bad = []
        for fn in sorted(os.listdir(HERE)):
            if not fn.endswith(".py"):
                continue
            try:
                tree = ast.parse(io.open(os.path.join(HERE, fn), encoding="utf-8").read())
            except Exception:
                continue
            for n in ast.walk(tree):
                nm = None
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "get" and n.args
                        and isinstance(n.args[0], ast.Constant)):
                    nm = n.args[0].value
                elif isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant):
                    nm = n.slice.value
                if nm in RETIRED:
                    bad.append("%s:%d %s" % (fn, getattr(n, "lineno", 0), nm))
        self.assertEqual([], bad, "a module still reads a retired flag, which now returns None "
                                  "and skips silently rather than failing: %r" % bad)

    def test_a_pair_ruled_NOT_comparable_NAMES_BOTH_NUMBERS(self):
        """An exemption nobody can audit is an exemption that grows. A ledger excluded from the
        cross-check must say which two universes disagree, IN DIGITS, so the next reader can tell
        `403 vs 398` from `the instrument is broken`.

        ⚠⚠ v3026 — THIS LAW PASSED VACUOUSLY AND ITS PROOF MEASURED **BLIND**, and the two facts
        were the same fact. Measured: surface_pairs() returns 2 pairs and `comparable is False` for
        ZERO of them, so the old loop body never executed. Worse, the branch its RED_PROOF tampered
        with is DEAD — v2947 hardcoded `_tot = None` and moved the universe question per-ROW into
        mask_cross_check, so `_univ_ok is False` can never be true. A proof aimed at unreachable
        code can never go red.

        THE COST WAS NOT LOCAL. heart2 reported the whole gate BLIND, and
        self_arming._heart_says_watched() fails closed on any blind instrument — so this one law
        closed ALL TEN self-arming locks.

        ⚠ AND THE OLD ASSERTION CHECKED ONE NUMBER WHILE ITS OWN NAME SAID **BOTH**: it looped over
        `(p.get("maskRosterN"),)` — a one-tuple — so even had it run, the tally total it was written
        to protect was never asserted.

        It now DRIVES the live path with a constructed fleet rather than waiting for his data to
        produce a disagreement, and asserts both numbers.
        [[gate-blind-to-unexercised-input]] [[zero-needs-a-denominator]] [[the-unjoined-end]]"""
        roster_n = self._constructed_roster()          # REG-2375 - never a skip

        #: a machine posting a total that disagrees with the roster — the ONE state that must
        #: produce an auditable exemption. The mask is irrelevant here: the row is excluded before
        #: it is ever decoded.
        bad_total = roster_n + 5
        fleet = {"online": [{"machine": "testbox", "nickname": "testbox",
                             "tally": {"uniques": {"have": 7, "total": bad_total}},
                             #: ⚠ the mask must be a DICT — mask_cross_check skips the row before the universe
                             #: check when it is not, which is what made my first fixture silently
                             #: unreachable and the law green for the wrong reason
                             "masks": {"uniques": {"b": ""}}}],
                 "offline": []}
        out = LA.mask_cross_check(fleet=fleet) or {}
        excluded = list(out.get("excluded") or [])
        mine = [e for e in excluded if str(e.get("ledger")) == "uniques"]
        self.assertTrue(
            mine,
            "a machine posting %d against a %d-name roster was NOT excluded from the cross-check, "
            "so two incomparable universes would be compared as if they matched. excluded=%r"
            % (bad_total, roster_n, excluded))

        why = str(mine[0].get("why") or "")
        for n in (bad_total, roster_n):
            self.assertIn(str(n), why,
                          "the exemption does not name %r, so nobody can tell %d-vs-%d from a "
                          "broken instrument: %r" % (n, bad_total, roster_n, why))

    def test_a_MATCHING_total_is_not_excluded_so_the_gate_is_not_simply_off(self):
        """⚠ THE OTHER SIDE. A law that only ever sees the exclusion cannot tell a working gate
        from one that excludes everything — and excluding everything is exactly how the cross-check
        went DARK before v2947. [[feedback-blind-fixture-green-gate]]"""
        roster_n = self._constructed_roster()          # REG-2375 - never a skip
        fleet = {"online": [{"machine": "testbox", "nickname": "testbox",
                             "tally": {"uniques": {"have": 7, "total": roster_n}},
                             #: ⚠ the mask must be a DICT — mask_cross_check skips the row before the universe
                             #: check when it is not, which is what made my first fixture silently
                             #: unreachable and the law green for the wrong reason
                             "masks": {"uniques": {"b": ""}}}],
                 "offline": []}
        out = LA.mask_cross_check(fleet=fleet) or {}
        mine = [e for e in (out.get("excluded") or [])
                if str(e.get("ledger")) == "uniques"
                and "can only represent" in str(e.get("why") or "")]
        self.assertFalse(
            mine, "a machine whose posted total MATCHES the roster (%d) was excluded for a universe "
                  "mismatch, so the gate excludes regardless and measures nothing: %r"
                  % (roster_n, mine))

    def test_the_cross_check_EXCLUDES_with_a_REASON_at_both_levels(self):
        """THE GATE HAS TWO LEVELS AND THIS LAW NAMES BOTH, because v2947 moved one of them.

        STORE level (`comparable`, answerable from the table alone): two surfaces reading
        different stores are not comparable for ANY machine, so that ledger is out everywhere.

        UNIVERSE level (per ROW, inside mask_cross_check): a machine posting `have` out of a total
        the mask cannot represent is out for THAT ROW only. Two machines can post different totals
        for one ledger, so one console-wide answer cannot be right for both -- which is why
        v2945's version, deciding it once from this console's own grail_tally(), went dark on any
        venue with no local tally and took `sets` down with it.

        What must hold at both levels: excluded AND NAMED, never silently skipped."""
        pairs = {str(p["ledger"]): p for p in (LA.surface_pairs() or [])}
        d = LA.mask_cross_check() or {}
        # REG-1893 - both `or` defaults read a lost answer as "nothing to exclude": no pairs makes
        # store_bad empty, and a renamed `excluded` key makes excl empty, so every check below
        # would pass over ledgers it never saw.
        self.assertTrue(pairs, "surface_pairs() answered nothing, so no ledger's store was judged")
        self.assertIn("excluded", d, "mask_cross_check() carries no `excluded` list: %r"
                                     % sorted(d))
        excl = d.get("excluded") or []
        named = {str(e.get("ledger")) for e in excl}
        store_bad = {k for k, v in pairs.items() if v.get("comparable") is not True}
        self.assertEqual(set(), store_bad - named,
                         "a ledger whose surfaces read different stores was measured anyway: %r"
                         % sorted(store_bad - named))
        for e in excl:
            why = str(e.get("why") or "")
            self.assertTrue(why.strip(), "%r excluded with no reason" % e.get("ledger"))
            self.assertTrue(any(ch.isdigit() for ch in why),
                            "%r excluded with a reason naming no number: %r"
                            % (e.get("ledger"), why))
        rows = d.get("rows") or []
        for led in store_bad:
            self.assertEqual([], [r for r in rows if r.get("ledger") == led],
                             "%s is out at the STORE level and was measured anyway" % led)

    def test_comparable_does_NOT_depend_on_a_live_probe_of_THIS_console(self):
        """REG-952, caught by the second eye on v2945 and reproduced before being believed.

        `comparable` briefly called control_app.grail_tally() -- a live read of THIS console's
        board -- inside the per-ledger loop. On CI, a fresh clone, or the Windows box before the
        board has POSTed, that answers nothing, so every pair went None and mask_cross_check
        excluded ALL ledgers, `sets` included, whose stores and universes genuinely match.

        Parsed, not grepped."""
        src = io.open(os.path.join(HERE, "ledger_authority.py"), encoding="utf-8").read()
        fn = next((n for n in ast.walk(ast.parse(src))
                   if isinstance(n, ast.FunctionDef) and n.name == "surface_pairs"), None)
        self.assertIsNotNone(fn)
        calls = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Attribute):
                    calls.add(f.attr)
                elif isinstance(f, ast.Name):
                    calls.add(f.id)
        self.assertNotIn("grail_tally", calls,
                         "surface_pairs() probes this console's live tally again -- the one flag "
                         "every caller branches on would go None wherever no board has POSTed, "
                         "taking the honest ledgers down with it")

# ══ THE EXECUTABLE RED-PROOF ═════════════════════════════════════════════════
# PROPOSED by tv/heart2_candidates.py — derived from this gate's OWN assertions and
# measured against the target file (each anchor occurs exactly once). Review it: the
# question is whether deleting this text is the defect the law exists to catch.
RED_PROOF = [
    {
        "why": 'the law requires this text in control_app.py, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'control_app.py',
        "find": 'spec.get("stores") or [spec["store"]]',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
    {
        "why": 'the law requires this text in control_app.py, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'control_app.py',
        "find": "if(rawv==null||rawv===''){continue;}",
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
    {
        "why": 'law: a pair carries exactly ONE decidable flag. `comparable` is the key every caller branches on; deleting it from the returned dict must turn the gate red',
        "file": 'ledger_authority.py',
        "find": '"comparable": _comparable, "why": _why})',
        "replace": '"_HEART2_TAMPERED_": _comparable, "why": _why})',
        "matches": 1,
    },
    {
        "why": 'law: the cross-check excludes exactly the non-comparable and NAMES them. Breaking the exclusion comprehension must turn the gate red, not silently empty the list',
        "file": 'ledger_authority.py',
        "find": 'if v.get("comparable") is not True]',
        "replace": 'if v.get("_HEART2_TAMPERED_") is not True]',
        "matches": 1,
    },
    {
        "why": 'law: a pair ruled not-comparable names BOTH numbers. Dropping the tally total from the reason leaves an exemption nobody can audit',
        "file": 'ledger_authority.py',
        #: ⚠⚠ v3026 — RE-ANCHORED FROM DEAD CODE TO THE LIVE PATH. This tampered a string inside
        #: surface_pairs()'s `_univ_ok is False` branch, which has been UNREACHABLE since v2947
        #: hardcoded `_tot = None` — so the proof could never go red and heart2 called the whole
        #: gate BLIND, which closed all ten self-arming locks. The universe question moved per-ROW
        #: into mask_cross_check; this now tampers the reason that actually gets built.
        #: ⚠ REG-2398 — AND IT WENT RED BY CRASHING. It dropped ` out of %d` and left `_rowTot` in the argument tuple, so
        #: the `%` raised TypeError (measured by the cross-family review: 0 failures, 2 ERRORS) and the assertion this
        #: proof exists for - the reason names BOTH numbers - never ran. The tamper now drops the placeholder AND its
        #: argument together, the way a real edit would: the reason is built, and the law fails on it.
        "find": '"%s posts %s out of %d while the %s mask can only represent %d roster names, "\n'
                '                    "so their counts are not comparable" % (who, t.get("have"), _rowTot, led,\n',
        "replace": '"%s posts %s while the %s mask can only represent %d roster names, "\n'
                   '                    "so their counts are not comparable" % (who, t.get("have"), led,\n',
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
