#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TWELVE OF SIXTEEN LOCKS COULD NOT SAY HOW MANY DISTINCT ATTACKS BACKED THEM.

⚠⚠ WHY THAT FIELD IS THE WHOLE POINT. REG-598: Wilson tightens as `n` grows and **cannot tell 83
independent looks from ONE attack applied 83 times**, so running more of the same buys a higher
number and proves nothing. `attacks` is the field that stops it, and `wilsonByAttack` is the score
recomputed over distinct attacks rather than repetitions.

⚠⚠ MEASURED 2026-09-05, and the count was the tell. Twelve locks with `n > 0` read
`attacks: UNSTATED` — including **`prune.arm`, the one door with no undo**, and
**`vault.sweep_start`, which spends his money**. `attacks: null` is documented as *"the harness has
not re-run since the field existed"*, which is NOT the same as "no repetition" — but nothing
distinguished the two on the badge, so a lock resting on one attack looped many times rendered
exactly like one that earned it.

**IT WAS NOT A WIRING GAP.** Walked by AST: every harness that banks — all ten of them — already
passes `attacks=`. v2623 wired them; the STORED ROWS simply predated the re-run. So the fix was to
re-run the harnesses, not to change them, and this guard is what stops the state coming back.

AFTER RE-RUNNING, and this is the picture the field exists to show:

    lock                 wilson   byAttack   bar
    prune.arm            0.9259     0.5655   0.839     <- the deleter
    vault.apply          0.9259     0.4385   0.722     <- the only HARDENED lock
    vault.sweep_start    0.8064     0.3424   0.510     <- his money
    miniauto.run         0.9347     0.5101   0.510
    printer.stream       0.9558     0.5655   0.510

⚠⚠⚠ WHAT THIS GUARD DOES NOT DECIDE, DELIBERATELY. Whether the bars are read against `wilson` or
against `wilsonByAttack` is **HIS RULING**, still open on the board. Every one of those locks
CLEARS on `wilson` and several do NOT clear on `wilsonByAttack`. This file makes both numbers
available on every lock so the decision can be made on evidence; it does not make the decision, and
it must never be edited into making it. [[unknown-stays-unknown]]

⚠ NOTHING HERE ARMS ANYTHING. `may()` is still never called; the prune stays OFF.
"""
import ast
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import self_arming as SA  # noqa: E402


def _locks():
    rep = SA.report()
    return [r for r in (rep.get("locks") or []) if isinstance(r, dict)]


class EveryLockWithEvidenceDeclaresItsAttacks(unittest.TestCase):

    def test_the_report_has_locks_at_all(self):
        """⚠ A guard over an empty list is measuring nothing."""
        self.assertGreaterEqual(len(_locks()), 8,
                                "the lock table is too small to be the real one")

    def test_no_lock_with_n_over_zero_reads_UNSTATED(self):
        """★★ THE LAW. A score with an unstated attack count cannot be told apart from one bought
        by repetition — which is the defect REG-598 exists for."""
        bad = [r["lock"] for r in _locks()
               if int(r.get("n") or 0) > 0 and r.get("attacks") is None]
        self.assertEqual(bad, [],
                         "%d lock(s) carry evidence but cannot say how many DISTINCT attacks are "
                         "behind it, so a score looped from one sabotage renders exactly like one "
                         "that earned it: %s" % (len(bad), bad))

    def test_a_lock_with_NO_evidence_may_be_unstated(self):
        """⚠ THE CARVE-OUT, and it must stay. A lock with NO evidence has no attack count to state - demanding one
        would be demanding a number about an event that has not happened.

        REG-3819 - this used to pin vault.forget as its live subject (it had no refusal path, so it was n=0 on every
        machine). It banks evidence now, so the carve-out is asked of EVERY lock with no rows handed in: never an
        empty list that would pass the carve-out over nothing (REG-1893)."""
        zero = [SA.score(lk, rows=[]) for lk in sorted(SA.LOCKS)]
        self.assertGreaterEqual(len(zero), 8, "the lock table is too small to be the real one")
        for r in zero:
            self.assertIsNone(r.get("attacks"), "%s states an attack count with no rows behind it" % r.get("lock"))
            self.assertIn(r.get("state"), ("UNPROVEN", "UNKNOWN", "INCOMPLETE"),
                          "%s has no evidence but does not say so" % r.get("lock"))

    def test_wilsonByAttack_is_published_wherever_attacks_is(self):
        """⚠ The count alone is not the point — the SCORE over distinct attacks is. A lock that
        states `attacks` and hides the recomputed figure has published the input and withheld the
        answer. [[the-unjoined-end]]"""
        locks = _locks()
        # REG-1893 - `rep.get("locks") or []` turns a renamed report key into an empty table, and
        # the loop below would then pass over locks it never saw.
        self.assertGreaterEqual(len(locks), 8, "the lock table is too small to be the real one")
        for r in locks:
            if r.get("attacks"):
                self.assertIsNotNone(r.get("wilsonByAttack"),
                                     "%s declares %s attacks and publishes no wilsonByAttack"
                                     % (r.get("lock"), r.get("attacks")))

    def test_byAttack_is_never_HIGHER_than_the_raw_score(self):
        """⚠⚠ AN ARITHMETIC SANITY CHECK, because a byAttack figure ABOVE the raw one would mean
        the correction is inflating rather than deflating — and a correction that can only help is
        not a correction. Wilson rises with n, and attacks <= n, so it can only fall or tie."""
        locks = _locks()
        # REG-1893 - `rep.get("locks") or []` turns a renamed report key into an empty table, and
        # the loop below would then pass over locks it never saw.
        self.assertGreaterEqual(len(locks), 8, "the lock table is too small to be the real one")
        for r in locks:
            w, wba = r.get("wilson"), r.get("wilsonByAttack")
            if w is None or wba is None:
                continue
            self.assertLessEqual(round(wba, 6), round(w, 6) + 1e-9,
                                 "%s: wilsonByAttack %.4f exceeds wilson %.4f — the repetition "
                                 "correction is adding confidence instead of removing it"
                                 % (r.get("lock"), wba, w))


    def test_a_lock_WITH_FAILURES_is_never_credited_more_by_attack_than_raw(self):
        """⚠⚠ #123 — DRIVEN, so it does not depend on whose evidence store this machine holds. The live
        case above only fires where a lock happens to carry failures; this is prune.reports' own
        shape (117 of 125 attempts over 35 attacks), which scored byAttack 0.9011 over a raw 0.8788
        under `min(k, attacks)` — and `deciding` is wilsonByAttack, so the lock read HARDENED on
        confidence the evidence never gave."""
        rows = [{"lock": "prune.reports", "n": 125, "k": 117, "kind": "sabotage",
                 "attacks": 35, "ref": "fixture"}]
        o = SA.score("prune.reports", rows=rows)
        self.assertEqual((o.get("k"), o.get("n"), o.get("attacks")), (117, 125, 35),
                         "premise: the fixture row did not fold to the counts it declares: %r" % (o,))
        self.assertLessEqual(o["wilsonByAttack"], o["wilson"],
                             "byAttack %.4f exceeds the raw %.4f on a lock WITH failures — the "
                             "correction is adding confidence" % (o["wilsonByAttack"], o["wilson"]))
        self.assertEqual(o["wilsonByAttack"], round(SA.wilson_lower(27, 35), 4),
                         "8 failures over 35 distinct attacks must credit 27, the conservative reading")

class MoreAttacksThanAttemptsIsNeverCredit(unittest.TestCase):
    """The second eye on v3487 (grok-4.7), reproduced before fixing: `_attacks_passed` credited
    attacks - (n - k) and never capped it, so 10 of 10 over 20 attacks read 20 of 20 (0.8389 against a
    raw 0.7225) and 9 of 10 over 20 read 19 of 20. And 21 live hover_wilson rows bank n=0 with
    attacks=1, which padded miniauto.run's attack count (4 -> 3 once clamped). DRIVEN."""

    def test_the_credit_never_exceeds_k_or_the_attempts(self):
        for k, n, a in ((10, 10, 20), (9, 10, 20), (0, 3, 9), (117, 125, 35)):
            got = SA._attacks_passed(k, n, a)
            self.assertLessEqual(got, k, "%d of %d over %d attacks credited %d > k" % (k, n, a, got))
            self.assertLessEqual(SA.wilson_lower(got, min(a, n)) if min(a, n) else 0,
                                 SA.wilson_lower(k, n) + 1e-9,
                                 "%d of %d over %d attacks scores above its raw bound" % (k, n, a))

    def test_a_zero_trial_axis_adds_no_attack(self):
        rows = [{"lock": "miniauto.run", "n": 10, "k": 10, "kind": "sabotage", "attacks": 3, "ref": "a"},
                {"lock": "miniauto.run", "n": 0, "k": 0, "kind": "sabotage", "attacks": 1, "ref": "b"}]
        o = SA.score("miniauto.run", rows=rows)
        self.assertEqual(o.get("attacks"), 3, "an axis that ran zero trials added to the attack count: "
                                              "%r" % (o.get("attacks"),))
        self.assertLessEqual(o["wilsonByAttack"], o["wilson"])

    def test_bank_refuses_more_attacks_than_attempts_but_keeps_the_zero_trial_shape(self):
        lock, kind, src = self._a_declared_pair()
        with self.assertRaises(ValueError):
            self._bank_into_a_temp_ledger(lock, kind, src, 10, 10, 20)
        row = self._bank_into_a_temp_ledger(lock, kind, src, 0, 0, 1)   # declared, unable to run
        self.assertEqual((row.get("n"), row.get("attacks")), (0, 1))

    def _a_declared_pair(self):
        for src, locks in getattr(SA, "PROVES", {}).items():
            for l in (locks if isinstance(locks, (list, tuple, set)) else [locks]):
                if l in SA.LOCKS:
                    return l, sorted(SA.KINDS)[0], src
        self.skipTest("premise: no declared (source, lock) pair to bank against")

    def _bank_into_a_temp_ledger(self, lock, kind, src, n, k, attacks):
        """bank() writes to _ledger_path(); pointed at a temp file so his proof queue is never touched."""
        import shutil
        import tempfile
        d = tempfile.mkdtemp(prefix="attack-bank-")
        real = SA._ledger_path
        SA._ledger_path = lambda *a, **kw: os.path.join(d, "proof.jsonl")
        try:
            return SA.bank(lock, kind, src, n=n, k=k, attacks=attacks, note="fixture")
        finally:
            SA._ledger_path = real
            shutil.rmtree(d, ignore_errors=True)


class TheHARNESSESAllPassIt(unittest.TestCase):
    """★ Established by AST, so a harness that stops declaring is caught even before it re-runs and
    the stored rows go stale."""

    def test_every_banking_harness_passes_attacks(self):
        gaps = []
        for src in sorted(SA.PROVES):
            p = os.path.join(HERE, src + ".py")
            if not os.path.exists(p):
                continue                      # a SOURCE LABEL banked by another harness
            try:
                tree = ast.parse(io.open(p, encoding="utf-8").read())
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call):
                    continue
                nm = getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                if nm in ("bank", "record") and not any(
                        k.arg == "attacks" for k in (n.keywords or [])):
                    gaps.append("%s:%d" % (src, n.lineno))
        self.assertEqual(gaps, [],
                         "bank/record call(s) with no attacks= : %s — the row they write cannot "
                         "say how many distinct attacks it represents" % gaps)

    def test_a_source_with_no_module_is_a_LABEL_and_that_is_legitimate(self):
        """⚠ I RAISED THIS AS AN ALARM AND IT WAS WRONG, which is worth keeping. `vault_live` is
        declared in PROVES and has no `vault_live.py`, and for a moment that looked like the only
        HARDENED lock resting on a module that does not exist. It is a source LABEL: `vault_wilson`
        banks under it when it drives the RUNNING console over HTTP. The evidence is real and
        re-derivable. Checking before believing my own alarm is the only reason this is a note and
        not a retraction."""
        # ⚠⚠ v2795 — THE OLD FORM CONFLATED TWO OPPOSITE FACTS AND FAILED ON THE HARMLESS ONE.
        # It demanded that EVERY module-less label be referenced by some harness. But PROVES is an
        # allow-list of whose evidence WOULD COUNT, and self_arming says so where the entries are
        # written: *"An allow-list entry is not evidence; it only says whose evidence would COUNT.
        # Until a harness banks under one of these the lock is UNPROVEN."* Declaring the second
        # and third family a lock needs BEFORE they exist is the mechanism working — `kinds_bar`
        # 1.8 means one family can never open `console.pixel_rescue` alone, so the other two have
        # to be nameable in advance.
        #
        # MEASURED across all six module-less labels: every one that has BANKED anything is
        # referenced by a real harness (vault_live<-vault_wilson 21 rows, rung_accounting_live 2,
        # rung_accounting_xfam 3, frame_release_live 1). The two that are not referenced —
        # pixel_witness_live, pixel_witness_crossfamily — have banked **zero rows**. The old law
        # went red on the two that carry no claim at all.
        #
        # ⛔ SO THE LAW BINDS ON EVIDENCE, NOT ON DECLARATION, and that is STRICTER where it
        # matters: the moment a label banks a single row, its source must be derivable from a
        # module in the tree. A promise costs nothing and can be checked later; a SCORE whose
        # origin nobody can find is the untraceable evidence this guard exists for.
        labels = [s for s in SA.PROVES if not os.path.exists(os.path.join(HERE, s + ".py"))]
        self.assertTrue(labels, "no module-less label exists, so this law is vacuous — re-point "
                                "it rather than leaving it green over nothing")
        # ⚠ `_rows()` RETURNS (rows, why) — a tuple, not a list. My first cut iterated the tuple
        # and counted nothing, and the baseline assertion below is the only reason that did not
        # become a law that passes because it read no evidence at all. [[zero-needs-a-denominator]]
        _rows, _why = SA._rows()
        banked = {}
        for row in (_rows or []):
            if isinstance(row, dict) and row.get("src"):
                banked[row["src"]] = banked.get(row["src"], 0) + 1
        self.assertTrue(banked,
                        "the ledger read back EMPTY (%s), so 'has banked nothing' is true of "
                        "everything and this law would pass over an unread file" % (_why or "no "
                        "reason given"))
        for lab in labels:
            found = False
            for other in SA.PROVES:
                p = os.path.join(HERE, other + ".py")
                if not os.path.exists(p):
                    continue
                if ('"%s"' % lab) in io.open(p, encoding="utf-8").read():
                    found = True
                    break
            if found:
                continue
            # ⚠⚠ v3347 — A RETIRED PAIR IS EXEMPT, AND THE EXEMPTION IS MEASURED, NEVER WAIVED.
            # His ruling retired `prune.arm` and `prune_wilson.py` went with the ceremony, leaving
            # 19 banked rows behind. They MUST stay declared — dropping them from PROVES makes
            # _rows() return None and fails all nine surviving locks CLOSED — but they must also
            # be unable to open anything. bank() already refuses a lock absent from LOCKS; the
            # clause worth PROVING rather than believing is that no LIVE lock reads them, so that
            # is asserted here against his real ledger instead of argued in a comment.
            # Measured 2026-09-19: dropping all 19 changes 0 of 9 live scores.
            _declared = SA.PROVES.get(lab) or ()
            if _declared and all(lk in getattr(SA, "RETIRED_LOCKS", {}) for lk in _declared):
                _without = [r for r in (_rows or []) if str(r.get("src")) != lab]
                for _lk in SA.LOCKS:
                    _a, _b = SA.score(_lk, _rows), SA.score(_lk, _without)
                    self.assertEqual(
                        (_a["state"], _a["n"], _a["k"]), (_b["state"], _b["n"], _b["k"]),
                        "%r is declared only for RETIRED locks, so its rows must reach no live "
                        "surface — and %s moves when they are dropped. An exemption that lets "
                        "untraceable evidence into a live lock is the exact defect this law "
                        "exists to refuse." % (lab, _lk))
                continue
            self.assertEqual(
                banked.get(lab, 0), 0,
                "%r has banked %d row(s), has no module of its own, and no harness in the tree "
                "names it — so its evidence cannot be re-derived by anyone, which is exactly the "
                "untraceable score this guard exists to refuse. A label may be declared ahead of "
                "its harness; it may not CARRY a claim nobody can trace."
                % (lab, banked.get(lab, 0)))


class ItDoesNotDecideHisRuling(unittest.TestCase):
    """⚠⚠ THE ONE WAY THIS FILE COULD DO HARM. Several locks clear on `wilson` and do NOT clear on
    `wilsonByAttack`; which figure the bars read is HIS open ruling. This guard must never quietly
    settle it."""

    def test_the_bar_is_still_compared_against_the_RAW_wilson(self):
        """If this ever fails, the ruling was made — say so out loud rather than letting a guard
        record it silently."""
        import inspect
        src = inspect.getsource(SA.score)
        self.assertIn("wilson_lower(k, n)", src,
                      "the bar is no longer compared against the raw wilson. If that was his "
                      "ruling, this guard should be rewritten to state it, not deleted")

    def test_the_locks_that_would_CHANGE_under_the_other_reading_are_visible(self):
        """★ The evidence his decision needs, published rather than argued."""
        locks = _locks()
        # REG-1893 - `rep.get("locks") or []` turns a renamed report key into an empty table, and
        # the loop below would then pass over locks it never saw.
        self.assertGreaterEqual(len(locks), 8, "the lock table is too small to be the real one")
        flip = [(r["lock"], r.get("wilson"), r.get("wilsonByAttack"), r.get("bar"))
                for r in locks
                if r.get("wilson") is not None and r.get("wilsonByAttack") is not None
                and r.get("bar") is not None
                and r["wilson"] >= r["bar"] > r["wilsonByAttack"]]
        for lock, w, wba, bar in flip:
            self.assertLess(wba, bar)          # by construction; asserted so the list is real
        self.assertIsInstance(flip, list)


RED_PROOF = [
    {
        "why": "#123 - the per-attack credit back on min(k, attacks): with failures present every distinct attack is credited as refused, and prune.reports' shape scores 0.9011 over a raw 0.8788",
        "file": "self_arming.py",
        # re-anchored for v3487's second eye (the line now clamps attacks to n and the credit to k)
        "find": "    return max(0, min(int(k), a - (int(n) - int(k))))",
        "replace": "    return min(int(k), int(attacks))",
        "matches": 1
    },
    {
        "why": "v3487 second eye - the credit is no longer capped: 10 of 10 over 20 attacks credits 20, above k and above the raw bound",
        "file": "self_arming.py",
        "find": "    a = min(int(attacks), int(n))\n    return max(0, min(int(k), a - (int(n) - int(k))))",
        "replace": "    a = int(attacks)\n    return max(0, a - (int(n) - int(k)))",
        "matches": 1
    },
    {
        "why": "v3487 second eye - a zero-trial axis adds to the attack count again (hover_wilson's n=0 attacks=1 rows padded miniauto.run 3 -> 4)",
        "file": "self_arming.py",
        "find": "    _atk = [min(r.get(\"attacks\"), int(r.get(\"n\") or 0))\n",
        "replace": "    _atk = [r.get(\"attacks\")\n",
        "matches": 1
    },
    {
        "why": "v3487 second eye - bank() accepts more distinct attacks than attempts again",
        "file": "self_arming.py",
        "find": "    if attacks is not None and n > 0 and int(attacks) > n:\n",
        "replace": "    if False:\n",
        "matches": 1
    },
    {
        'why': "a bank() call with no attacks= writes a row that cannot say how many DISTINCT attacks back it — REG-598's defect exactly, where Wilson could not tell 83 independent looks from one attack applied 83 times (83/83 was 2 attacks x 40 reels, really 0.5655). Verified by hand: untampered OK, tampered FAILED (failures=1), and the law that went red is test_every_banking_harness_passes_attacks itself, not a sibling failing for its own reason.",
        'file': 'frame_release_wilson.py',
        'find': 'attacks=n,',
        'replace': '',
        'matches': 1,
    },
]


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    unittest.main(verbosity=2)
