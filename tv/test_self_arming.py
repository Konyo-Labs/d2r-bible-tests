#!/usr/bin/env python3
"""Guards for the self-arming lock. Every case asserts a REFUSAL as well as a pass.

The thing being replaced is a human flipping `_PRUNE_SAFE_TO_RUN` by hand, so the failure that
matters is not "it refused when it should have opened" — it is "IT OPENED WITHOUT EARNING IT".
Every test here is pointed at that direction.
"""
import ast
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import self_arming as SA


RED_PROOF = [
    {
        "why": 'the law requires this text in self_arming.py, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'self_arming.py',
        "find": 'too alike',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
]

_HEART_REAL = None


def setUpModule():
    """v2865 — v2861 joined may() to the heart: a surface may not arm itself while its instruments
    are blind, and an ABSENT census is UNKNOWN, which fails CLOSED. Correct — and it turned this
    file red on CI, where `.heart2.json` is gitignored so there IS no census: may() then returns the
    heart's refusal instead of the upstream/Wilson reason these laws assert. My machine had a
    census; the runner does not. [[feedback-blind-fixture-green-gate]]

    The precondition has its OWN gate — test_the_lock_derives_from_the_heart, 10 laws, 3 red-proofs.
    THIS file's subject is the ORDER and the ARITHMETIC, so it stubs the heart exactly as it already
    stubs SA.LEDGER. Stubbing what you are not testing is not weakening a law; letting a
    machine-local file decide an assertion about Wilson scores is.

    ⚠ MODULE level on purpose. My first cut added a setUp to each class that calls may() — and
    OVERRODE the inherited setUp that builds `self.p`, turning 3 failures into 6 errors. A fixture
    that breaks the fixtures is not a fixture.
    """
    global _HEART_REAL
    _HEART_REAL = SA._heart_says_watched
    # ⚠ v2867 — `**_k`, NOT a bare lambda. This repo already carries that scar (v2041,
    # `lambda sample=0:`): a stub with the wrong arity turns a future signature change into
    # ERRORS instead of failures, and an error says nothing about the law.
    SA._heart_says_watched = lambda **_k: (True, "stubbed: the heart is proved by its own gate")


def tearDownModule():
    if _HEART_REAL is not None:
        SA._heart_says_watched = _HEART_REAL


class _Ledger(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="arm-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.p = os.path.join(self.root, "proofs.jsonl")
        self._old = SA.LEDGER
        SA.LEDGER = self.p
        self.addCleanup(setattr, SA, "LEDGER", self._old)

    def put(self, lock, kind, refused, n=1):
        with io.open(self.p, "a", encoding="utf-8") as fh:
            for _ in range(n):
                fh.write(json.dumps({"lock": lock, "kind": kind,
                                     "refused": bool(refused), "ts": 0}) + "\n")


class TestUnprovenIsNotFailing(_Ledger):
    """The distinction the whole mechanism rests on. If these two collapse, a lock either opens on
    silence or paints its own newest surfaces red — and both get the mechanism ignored."""

    def test_no_proofs_is_UNPROVEN_and_carries_NO_score(self):
        s = SA.score("vault.apply")
        self.assertEqual(s["state"], SA.UNPROVEN)
        self.assertIsNone(s["wilson"],
                          "n=0 rendered as a NUMBER. 'nobody looked' would then be indistinguishable "
                          "from 'it scored zero', and a surface could be reported as failing when "
                          "it has simply never been tested. [[unknown-stays-unknown]]")
        self.assertIn("not a failure", s["why"])

    def test_UNPROVEN_still_does_not_permit_the_action(self):
        ok, why = SA.may("vault.apply")
        self.assertFalse(ok, "an untested surface was permitted to act")


class TestTheDenominatorIsSABOTAGES(_Ledger):
    """★ THE ONE THING THAT WOULD MAKE THIS A LIE. [[heart-first]] §5 — an invariant that always
    agrees may be perfect or INERT, and those are indistinguishable. A lock fed by an agreement
    rate opens BECAUSE nobody tested it, which is the exact failure it exists to prevent."""

    def test_a_wall_of_agreements_with_no_refusal_NEVER_opens(self):
        # 40 sabotages, and the guard failed to refuse every single time
        self.put("vault.sweep_start", "sabotage", False, n=40)
        s = SA.score("vault.sweep_start")
        self.assertEqual(s["state"], SA.LOCKED)
        self.assertEqual(s["k"], 0)
        self.assertEqual(s["n"], 40)
        self.assertEqual(s["wilson"], 0.0,
                         "40 attempts and 0 refusals must score 0.0 — this is the INERT guard, and "
                         "it must never be mistaken for an untested one")

    def test_a_refusal_is_what_counts_as_success(self):
        self.put("vault.sweep_start", "sabotage", True, n=10)
        s = SA.score("vault.sweep_start")
        self.assertEqual(s["k"], 10)
        self.assertGreater(s["wilson"], 0.72,
                           "10/10 refusals should reach the published 0.722 reference")


class TestWilsonAndConfluenceBOTH(_Ledger):
    """confidence.py's own words: 'The two run TOGETHER or neither means anything.' Wilson counts
    how many looks agreed, never whether they were INDEPENDENT — four re-runs of one sabotage by
    one harness is one proof wearing four hats."""

    def test_a_perfect_score_from_ONE_kind_is_still_LOCKED(self):
        self.put("vault.apply", "sabotage", True, n=30)      # wilson ~0.88, one kind = 1.0
        self.put("vault.sweep_start", "sabotage", True, n=30)
        s = SA.score("vault.apply")
        self.assertGreater(s["wilson"], s["bar"], "precondition: the score itself must clear")
        self.assertEqual(s["state"], SA.LOCKED,
                         "30 identical proofs opened the lock. Evidence that is all one kind is "
                         "one look wearing thirty hats.")
        self.assertIn("too alike", s["why"])

    def test_two_INDEPENDENT_kinds_open_it(self):
        self.put("vault.sweep_start", "sabotage", True, n=20)
        self.put("vault.apply", "sabotage", True, n=15)
        self.put("vault.apply", "cross-family", True, n=5)
        s = SA.score("vault.apply")
        self.assertEqual(s["state"], SA.OPEN, s["why"])
        ok, why = SA.may("vault.apply")
        self.assertTrue(ok, why)

    def test_an_UNWEIGHTED_kind_is_worth_zero_not_a_default(self):
        """A kind nobody has weighted is a kind nobody has thought about."""
        self.put("vault.sweep_start", "sabotage", True, n=20)
        self.put("vault.apply", "sabotage", True, n=20)
        self.put("vault.apply", "vibes", True, n=20)
        s = SA.score("vault.apply")
        self.assertEqual(s["state"], SA.LOCKED,
                         "an unrecognised proof kind paid as if someone had weighted it")


class TestHisOrderIsEnforced(_Ledger):
    """He gave a chain: printer+reels -> theatre+shelf -> routing -> the deleter. Proving a lock
    in isolation proves nothing about the lanes feeding it.

    ⚠⚠ v3347 - THE DELETER LEFT THE CHAIN, BY HIS RULING: *"leave it off and surgically remove
    it we need pruning"*. `prune.arm` was this class's subject. The MECHANISM it demonstrated is
    untouched and still live - `vault.apply` and `vault.forget` each wait on `vault.sweep_start` -
    so these cases drive the vault chain instead. The law is the ORDERING; the deleter was only
    the lock that happened to demonstrate it. [[regression-guard]] §4.
    """

    #: the live subject, DERIVED - a retirement moves this law rather than breaking it
    @property
    def subject(self):
        withafter = sorted(k for k, v in SA.LOCKS.items() if (v.get("after") or []))
        self.assertTrue(withafter, "no lock declares a prerequisite any more, so his ordering "
                                   "rule is enforced nowhere and these cases have no subject")
        return withafter[0]

    def test_a_lock_cannot_open_before_its_prerequisites(self):
        subj = self.subject
        # a flawless record for the lock itself, and NOTHING upstream
        self.put(subj, "sabotage", True, n=60)
        self.put(subj, "cross-family", True, n=20)
        self.put(subj, "live", True, n=20)
        ok, why = SA.may(subj)
        self.assertFalse(ok, "%s armed itself with no proof of the lanes that feed it" % subj)
        self.assertIn("blocked upstream", why)
        # ⚠⚠ REG-575 — THIS PINNED A NAME AND v2570 MOVED IT. It required the refusal to say
        # "vault.sweep_start"; then `printer.stream` was added ahead of it as step 1 of his river
        # ("printer+reels -> theatre+shelf -> routing") and the refusal correctly began naming
        # THAT instead. The invariant never broke — the assertion had pinned one name out of an
        # ORDERED list. So it now pins the property that is actually his ruling: the refusal names
        # a REAL, DECLARED, GENUINELY-UNPROVEN prerequisite, and it names them IN HIS ORDER.
        # A rule about the order survives an insertion; a rule naming one lock does not.
        named = [lk for lk in SA.LOCKS[subj]["after"] if lk in why]
        self.assertTrue(named, "the refusal named no prerequisite at all, so a high score reads "
                               "as 'nearly there' when the real blocker is elsewhere: %s" % why)
        for lk in named:
            self.assertNotEqual(SA.score(lk)["state"], SA.OPEN,
                                "%s was named as the blocker and is already OPEN" % lk)
        first_unproven = next(lk for lk in SA.LOCKS[subj]["after"]
                              if SA.score(lk)["state"] != SA.OPEN)
        self.assertIn(first_unproven, why,
                      "it skipped past the FIRST unmet prerequisite in his order and reported a "
                      "later one, which reads as further along the river than it is")

    def test_proving_the_prerequisite_CHANGES_the_answer(self):
        """⚠ BASELINE — or the test above passes on a chain that never advances. Satisfying the
        upstream step must change the refusal, never leave it naming a lane that is now proven.

        ⚠⚠ AND THE MULTI-STEP ARM HAS NO SUBJECT TODAY. With `prune.arm` retired the longest live
        chain is ONE step, so "the refusal moves to the NEXT unmet prerequisite" cannot be
        exercised by any lock in the table. That is ASSERTED here rather than silently skipped —
        a skip is not a pass — and the moment a two-step chain is declared this case drives it.
        [[regression-guard]] §2, §6."""
        subj = self.subject
        chain = SA.LOCKS[subj]["after"]
        self.put(subj, "sabotage", True, n=60)
        for lk in chain:
            self.put(lk, "sabotage", True, n=60)
            self.put(lk, "cross-family", True, n=20)
        ok, why = SA.may(subj)
        for lk in chain:
            self.assertNotIn("%s is UNPROVEN" % lk, why,
                             "%s was proven and is still being named as the blocker" % lk)
        self.assertNotIn("blocked upstream", why,
                         "every prerequisite of %s is proven and the refusal still says the "
                         "chain is holding it: %s" % (subj, why))
        longest = max(len(v.get("after") or []) for v in SA.LOCKS.values())
        if longest < 2:
            # Reach, stated out loud. Nothing here can prove the ADVANCE behaviour.
            self.assertEqual(
                len(chain), 1,
                "the longest declared chain is %d step(s), so this case proves only that ONE "
                "satisfied prerequisite changes the answer. The advance-to-the-next arm is "
                "UNMEASURED, not passing." % longest)


class TestItFailsCLOSED(_Ledger):
    """An unreadable proof queue is UNKNOWN, and UNKNOWN is never permission."""

    def test_an_unparseable_row_is_UNKNOWN_not_empty(self):
        self.put("vault.sweep_start", "sabotage", True, n=5)
        with io.open(self.p, "a", encoding="utf-8") as fh:
            fh.write("{not json\n")
        s = SA.score("vault.sweep_start")
        self.assertEqual(s["state"], SA.UNKNOWN,
                         "a hole in the evidence was read as a blank one — the 5 good rows would "
                         "then be the whole record, which is a smaller claim than the truth")
        ok, why = SA.may("vault.sweep_start")
        self.assertFalse(ok)
        self.assertIn("fails CLOSED", why)

    def test_an_undeclared_lock_is_never_permitted(self):
        ok, why = SA.may("something.nobody.declared")
        self.assertFalse(ok)
        self.assertIn("never permitted", why)


class TestThereIsNoHandOverride(unittest.TestCase):
    """The whole point is that Konyo stops being the arming mechanism. A `force` parameter would
    quietly restore the thing this replaces."""

    def test_may_takes_exactly_one_argument(self):
        import inspect
        sig = inspect.signature(SA.may)
        self.assertEqual(list(sig.parameters), ["lock"],
                         "may() grew a parameter. If one of them is an override, the lock is "
                         "decorative and the hand-arming is back.")

    def test_the_module_never_writes_an_unlock_flag(self):
        """⚠ THIS GUARD FAILED ON PROSE FIRST, AND THE LAW WAS NEVER WRONG.

        The first cut stripped `#` comments and asserted `_PRUNE_SAFE_TO_RUN` was absent. The
        module's own DOCSTRING says "This replaces `_PRUNE_SAFE_TO_RUN`" — so the guard went red
        on the sentence explaining the fix, which is [[source-reading-guard]] §4 exactly, and the
        third time that class has cost a wrong reading today. A `#`-stripper does not strip
        docstrings.

        Ask the COMPILER, not the text (§1): a name in a docstring is not in the AST. This also
        makes the guard STRONGER — it now catches `setattr(m, "_PRUNE_SAFE_TO_RUN", True)`-shaped
        writes that a substring search would miss entirely.
        """
        import ast, inspect
        tree = ast.parse(inspect.getsource(SA))

        FORBIDDEN_NAMES = {"_PRUNE_SAFE_TO_RUN", "SAFE_TO_RUN"}
        FORBIDDEN_CALLS = {"remove", "unlink", "rmtree", "replace", "setattr"}
        bad = []
        for node in ast.walk(tree):
            # writing a flag — assignment, augmented assignment, or an attribute set
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                tgts = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in tgts:
                    nm = getattr(t, "id", None) or getattr(t, "attr", None)
                    if nm in FORBIDDEN_NAMES:
                        bad.append("writes %s at line %d" % (nm, node.lineno))
            # destructive or reflective calls
            if isinstance(node, ast.Call):
                fn = node.func
                nm = getattr(fn, "attr", None) or getattr(fn, "id", None)
                if nm in FORBIDDEN_CALLS:
                    bad.append("calls %s() at line %d" % (nm, node.lineno))
        self.assertEqual(bad, [],
                         "the lock module ACTS instead of only deciding: %s. It DECIDES and "
                         "REPORTS; anything that flips a flag or deletes is a second arming path "
                         "and restores the hand-arming this replaces." % "; ".join(bad))

    def test_it_calls_confidence_rather_than_restating_the_maths(self):
        import inspect
        src = inspect.getsource(SA)
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        self.assertIn("from confidence import", code)
        self.assertNotIn("def wilson_lower", code,
                         "a second copy of the Wilson maths. [[copy-drift]] — two copies of one "
                         "safety routine diverge, and only one of them gets tuned.")


class TestBankingCannotOpenALockByBeingLookedAt(unittest.TestCase):
    """★ A2. THE DEFECT THIS EXISTS TO PREVENT IS THE WORST ONE AVAILABLE HERE.

    record() had ZERO callers, so every lock sat at n=0 UNPROVEN by construction however many
    sabotages actually ran. hover_wilson already scores the autopilot's four claims on real
    sabotage attempts and threw every result away.

    But score() counts ROWS (n = len(mine)), and hover_wilson hands out a rolling (n, k) AGGREGATE.
    Append that on each run and n goes 4, 8, 12, 16 — and the lock OPENS BECAUSE SOMEBODY LOOKED AT
    IT. On prune.arm, which deletes footage with no undo, that is the most expensive defect this
    repo could ship. Every case below defends one edge of that.
    """

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix="sa_ledger_")
        self.addCleanup(shutil.rmtree, self.tmp, True)     # #243 - 18 of these a day were left behind
        self.led = os.path.join(self.tmp, "ledger.jsonl")
        os.environ["TV_SELF_ARMING_LEDGER"] = self.led
        self.addCleanup(os.environ.pop, "TV_SELF_ARMING_LEDGER", None)

    def test_banking_TWICE_does_not_double_the_evidence(self):
        """The load-bearing one. Run the harness ten times; the lock must be exactly as proven as
        it was after the first run, because the same four sabotages were attempted each time."""
        for _ in range(10):
            SA.bank("miniauto.run", "sabotage", "hover_wilson", n=4, k=4, note="four claims")
        sc = SA.score("miniauto.run")
        self.assertEqual((sc["k"], sc["n"]), (4, 4),
                         "ten reads of the same evidence produced %d/%d. A lock that grows stronger "
                         "by being looked at is not a lock." % (sc["k"], sc["n"]))

    def test_a_LATER_bank_from_the_same_source_REPLACES_the_earlier_one(self):
        """A harness that gains a fifth sabotage must be able to say so — and one that loses a
        sabotage must be able to say that too, downward."""
        SA.bank("miniauto.run", "sabotage", "hover_wilson", n=4, k=4)
        SA.bank("miniauto.run", "sabotage", "hover_wilson", n=5, k=4)
        sc = SA.score("miniauto.run")
        self.assertEqual((sc["k"], sc["n"]), (4, 5))
        SA.bank("miniauto.run", "sabotage", "hover_wilson", n=2, k=1)
        sc = SA.score("miniauto.run")
        self.assertEqual((sc["k"], sc["n"]), (1, 2),
                         "evidence could not go DOWN. A harness whose sabotages started leaking "
                         "must be able to weaken its own lock, or the ledger is a ratchet")

    def test_an_UNDECLARED_source_is_refused(self):
        with self.assertRaises(ValueError) as cm:
            SA.bank("vault.apply", "sabotage", "some_new_harness", n=99, k=99)
        self.assertIn("not a declared evidence source", str(cm.exception))

    def test_a_source_may_not_bank_where_it_does_NOT_prove(self):
        """render_check proves the RENDER GATE. It says nothing about whether the vault may
        apply a change to his board, and an apply has no undo.

        ⚠ v3347 - the subject was `prune.arm` until his ruling retired it. A RETIRED lock is the
        wrong fixture here: bank() refuses it at an earlier door ("no such lock or route is
        declared"), so the test would go green without ever reaching the PROVES allow-list it
        exists to check. [[regression-guard]] §5 - a case that cannot fail for its own reason is
        measuring something else."""
        with self.assertRaises(ValueError) as cm:
            SA.bank("vault.apply", "sabotage", "render_check", n=40, k=40)
        self.assertIn("does not prove", str(cm.exception))
        self.assertEqual(SA.score("vault.apply")["n"], 0,
                         "the refusal still wrote a row — a refusal that banks anyway is not a "
                         "refusal")

    def test_more_refusals_than_attempts_is_an_INSTRUMENT_FAULT_not_a_great_score(self):
        with self.assertRaises(ValueError):
            SA.bank("miniauto.run", "sabotage", "hover_wilson", n=3, k=7)

    def test_single_attempts_still_ACCUMULATE_and_mix_with_aggregates(self):
        """record() rows are events and must keep adding up; only banked aggregates fold. If this
        broke, every row ever written by record() would silently change meaning."""
        # ⚠ v2612 — the src is REQUIRED now (REG-591): `record()` used to take none, so a single
        # call could credit ANY lock from anywhere, bypassing the PROVES allow-list that `bank()`
        # enforces. `hover_wilson` is the declared source for `miniauto.run`, so this exercises
        # exactly what it exercised before — accumulation — through the door as it is now.
        SA.record("miniauto.run", "fixture", True, src="hover_wilson")
        SA.record("miniauto.run", "fixture", True, src="hover_wilson")
        SA.record("miniauto.run", "fixture", False, src="hover_wilson")
        sc = SA.score("miniauto.run")
        self.assertEqual((sc["k"], sc["n"]), (2, 3))
        SA.bank("miniauto.run", "sabotage", "hover_wilson", n=4, k=4)
        sc = SA.score("miniauto.run")
        self.assertEqual((sc["k"], sc["n"]), (6, 7),
                         "aggregates and single attempts did not add up together")

    def test_a_kind_counts_only_where_something_was_actually_REFUSED(self):
        """confluence() weighs KINDS. A kind under which every sabotage LEAKED is not independent
        corroboration — it is a second witness saying nothing."""
        SA.bank("miniauto.run", "sabotage", "hover_wilson", n=6, k=0)
        self.assertEqual(SA.score("miniauto.run")["kinds"], [],
                         "a kind that refused nothing was counted as evidence")

    def test_an_UNDECLARED_TIER_is_refused_rather_than_silently_scoring_zero(self):
        """FOUND ON THE FIRST REAL RUN, and it is the quiet kind. `kind` is the TIER confluence
        weighs, not a free label. Banking the four hover claims under their own names gave kinds
        ['coordinate', 'read', 'slot'] scoring 0.00 against a bar of 1.00 — so the lock stayed shut
        FOREVER while its Wilson figure read 0.935 and every number on the page looked healthy.
        A lock nobody can explain is worse than a loud refusal."""
        with self.assertRaises(ValueError) as cm:
            SA.bank("miniauto.run", "coordinate", "hover_wilson", n=48, k=48)
        self.assertIn("not a declared evidence tier", str(cm.exception))
        self.assertEqual(SA.score("miniauto.run")["n"], 0, "the refusal still wrote a row")

    def test_two_claims_sharing_a_TIER_do_not_fold_into_one(self):
        """ALSO FOUND ON THE FIRST REAL RUN. All four hover claims are `sabotage` tier, so
        (lock, kind, src) is the SAME key for every one of them. Folding on that kept only the last
        row written — coordinate's 48/48 was thrown away and slot's 2/2 kept. n fell from 55 to 2
        and nothing said so. `ref` is what keeps them apart."""
        SA.bank("miniauto.run", "sabotage", "hover_wilson", n=48, k=48, ref="coordinate")
        SA.bank("miniauto.run", "sabotage", "hover_wilson", n=5, k=5, ref="read")
        SA.bank("miniauto.run", "sabotage", "hover_wilson", n=2, k=2, ref="slot")
        sc = SA.score("miniauto.run")
        self.assertEqual((sc["k"], sc["n"]), (55, 55),
                         "three distinct sabotage families collapsed to %d/%d — they share a tier "
                         "and were folded into one another" % (sc["k"], sc["n"]))
        # and re-running the same three still must not double them
        for _ in range(4):
            SA.bank("miniauto.run", "sabotage", "hover_wilson", n=48, k=48, ref="coordinate")
        self.assertEqual(SA.score("miniauto.run")["n"], 55)


class AnUnprovableLockSaysSoAndTheClaimIsCHECKED(unittest.TestCase):
    """⚠⚠ A LOCK THAT DECLARES ITSELF UNPROVABLE IS MAKING A CLAIM ABOUT ANOTHER FILE.

    `vault.forget` sits at n=0 forever because `vault_forget()` has NO refusal path — seven lines,
    one return, always ok — so there is no state in which it must say no and nothing a sabotage
    could attempt. That is deliberate (its docstring: an optimisation he cannot clear is a cage),
    and it is why the panel must not imply a harness is merely missing.

    But "this door has no refusal path" is a statement about `control_app.vault_forget`, sitting in
    a different file, and the day someone gives it one the declaration becomes a LIE that reads as
    documentation — a right sentence under a word that stopped being true. So it is CHECKED, by
    structure rather than by prose. [[label-outlived-referent]] [[source-reading-guard]]
    """

    def _fn(self, name):
        import ast
        here = os.path.dirname(os.path.abspath(__file__))
        src = io.open(os.path.join(here, "control_app.py"), encoding="utf-8").read()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        return None

    def test_every_unprovable_lock_names_a_function_that_really_cannot_refuse(self):
        import ast
        declared = [(k, v) for k, v in SA.LOCKS.items() if v.get("unprovable")]
        # REG-3819 - vault.forget, this law's only subject, gained a refusal path (the ledger drop refuses while a row
        # cites only released reels), so no lock is unprovable today. The check below still runs for the day one is;
        # what must hold NOW is the other half: the lock that stopped claiming it is named by a harness that attacks it.
        if not declared:
            self.assertIn("vault.forget", [lk for lks in SA.PROVES.values() for lk in lks],
                          "no lock is unprovable, and vault.forget names no harness either - it lost its "
                          "explanation without gaining evidence")
        for lock, spec in declared:
            fname = spec.get("unprovable_fn")
            self.assertTrue(
                fname, "%s claims it cannot be proven but names no function, so the claim cannot "
                       "be checked and will rot silently" % lock)
            fn = self._fn(fname)
            self.assertTrue(fn, "%s names %s(), which no longer exists in control_app"
                                % (lock, fname))
            returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)]
            raises = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
            self.assertEqual(
                len(returns), 1,
                "%s() now has %d return statements. %s is declared UNPROVABLE on the grounds that "
                "the door has no refusal path, so a second exit means either it CAN now refuse — "
                "in which case it is provable by sabotage and the declaration is a lie — or the "
                "function grew a shape nobody re-checked." % (fname, len(returns), lock))
            self.assertFalse(
                raises,
                "%s() can now raise, which is a refusal path by another name. %s claims it has "
                "none." % (fname, lock))
            # and it must not report failure through its payload either
            for node in ast.walk(fn):
                if isinstance(node, ast.Constant) and node.value is False:
                    parent_keys = [k for k in ast.walk(fn) if isinstance(k, ast.Dict)]
                    for d in parent_keys:
                        for key, val in zip(d.keys, d.values):
                            if (isinstance(key, ast.Constant) and key.value == "ok"
                                    and isinstance(val, ast.Constant) and val.value is False):
                                self.fail("%s() can return ok:False — that IS a refusal, so %s is "
                                          "provable and must not claim otherwise" % (fname, lock))

    def test_the_field_SURVIVES_the_status_trim(self):
        """⚠ THE TRIM IS A WHITELIST, AND A NEW FIELD IS DROPPED BY DEFAULT.

        `_self_arming_state()` rebuilds each lock row with a fixed set of keys "trimmed for a
        poll". `provable` was not in it, so the report carried the distinction and the BADGE never
        received it — measured on a freshly started console: the new `why` arrived and
        `provable` came back None. Built on both ends and joined on neither, which is this repo's
        most repeated defect. [[the-unjoined-end]]
        """
        import ast
        here = os.path.dirname(os.path.abspath(__file__))
        src = io.open(os.path.join(here, "control_app.py"), encoding="utf-8").read()
        fn = None
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.FunctionDef) and node.name == "_self_arming_state":
                fn = node
        self.assertTrue(fn, "_self_arming_state is gone — who publishes the locks now?")
        keys = set()
        for d in [n for n in ast.walk(fn) if isinstance(n, ast.Dict)]:
            for k in d.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.add(k.value)
        # ⚠⚠ `blindClaims` ADDED v2619, AND IT IS THE THIRD FIELD THIS TRIM HAS SWALLOWED.
        # score() computed it, the state read INCOMPLETE and the badge drew shut — while the
        # arithmetic beside it still printed "55/55 refused · 0.935 >= 0.510", an OPEN lock's
        # sentence, because the field died in the trim exactly as `provable` had. Three times is
        # the shape, not the instance: anything score() publishes for the panel has to be listed
        # here or the panel renders a correct verdict under a stale number.
        # [[the-unjoined-end]] [[label-outlived-referent]]
        for need in ("state", "why", "provable", "n", "blindClaims"):
            self.assertIn(need, keys,
                          "the status trim drops %r, so the console cannot render it however "
                          "correct self_arming.report() is" % need)

    def test_the_RENDERER_tells_them_apart_too(self):
        """The last joint. report() -> _self_arming_state() -> the badge; break any one and the
        distinction dies silently at that step. It died at the third: the renderer printed
        'untested' whenever n===0, so an unprovable door and an untested one read identically on
        screen however correct the two layers behind them were. [[the-unjoined-end]]"""
        here = os.path.dirname(os.path.abspath(__file__))
        ui = io.open(os.path.join(here, "control_ui.html"), encoding="utf-8").read()
        self.assertIn(
            "provable === false", ui,
            "the console's lock renderer never reads `provable`, so the field is published and "
            "unused — plumbing with no tap, and the badge still says 'untested' for a door that "
            "can never be sabotaged")

    def test_the_panel_tells_UNTESTED_apart_from_UNPROVABLE(self):
        """Both are n=0 and neither is a failure, but only one is waiting on work.

        REG-3819 - vault.forget, the live example this read, is provable now, so the distinction is pinned on a fixture
        lock declared unprovable by design: the mechanism must still speak for the day a real door needs it."""
        from unittest import mock
        spec = dict(SA.LOCKS["vault.forget"], unprovable="a fixture door with no refusal path", unprovable_fn="vault_forget")
        with mock.patch.dict(SA.LOCKS, {"zz.fixture_unprovable": spec}):
            rows = {r["lock"]: r for r in SA.report()["locks"]}
        forget = rows.get("zz.fixture_unprovable")
        self.assertTrue(forget, "a lock declared unprovable is not reported")
        self.assertEqual(forget["state"], SA.UNPROVEN)
        self.assertIs(forget.get("provable"), False,
                      "a by-design door is reported as still-provable, so the panel is telling him a "
                      "harness is owed for a door that can never be sabotaged")
        self.assertIn("cannot be proven", forget["why"])
        self.assertNotIn(
            "no sabotage has been attempted", forget["why"],
            "a by-design door still uses the nobody-has-tested-it sentence, which reads as a missing "
            "harness rather than a door with no refusal path")
        # a lock with real evidence must NOT be mislabelled
        for name, r in rows.items():
            if r.get("n"):
                self.assertNotIn("provable", [k for k in r if k == "provable" and r[k] is False],
                                 "%s has evidence and is marked unprovable" % name)



class TheLedgerIsCheckedONREADNotOnlyOnWrite(unittest.TestCase):
    """v2581 — bank()'s validations guarded the DOOR and not the ROOM.

    Every check bank() makes lived only in bank(). Anything else that appended a line to the
    ledger — a stray script, a hand edit, a half-finished writer — bypassed all of them, and
    score() then read it as evidence. Worse, score() DEFAULTS a missing count:
    `int(r.get("n", 1) or 0)` and `int(r.get("k", 1 if r.get("refused") else 0) or 0)`, so a
    three-key row {lock, kind, refused: true} was silently worth n=1 k=1 of whatever tier it
    named — and `kinds` is a SET, so one such row buys that tier's whole confluence weight.

    ⚠ Measured against his 51 real rows BEFORE this shipped: zero would fail. It costs nothing
    that is honest.

    ⚠ A bad row fails the WHOLE read, as an unparseable line already does. Dropping just the bad
    row would let a forgery be silently discarded while the rest scored on, and the lock would
    open on a ledger nobody could see had been edited. UNKNOWN is LOCKED, so this fails closed.
    """

    def _ledger(self, *rows):
        d = tempfile.mkdtemp(prefix="sa_read_")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "led.jsonl")
        with io.open(p, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        return p

    def _good(self, **kw):
        row = {"lock": "prune.arm", "kind": "sabotage", "src": "prune_wilson",
               "ref": "offspelling", "n": 10, "k": 10, "refused": True,
               "ts": int(time.time() * 1000)}
        row.update(kw)
        return row

    def _read(self, path):
        was = os.environ.get("TV_SELF_ARMING_LEDGER")
        try:
            os.environ["TV_SELF_ARMING_LEDGER"] = path
            return SA._rows()
        finally:
            if was is None:
                os.environ.pop("TV_SELF_ARMING_LEDGER", None)
            else:
                os.environ["TV_SELF_ARMING_LEDGER"] = was

    def test_an_honest_row_still_reads(self):
        """BASELINE — or the check bought its safety by refusing everything."""
        rows, why = self._read(self._ledger(self._good()))
        self.assertEqual(len(rows or []), 1, why)

    def test_a_RECORD_shaped_row_is_ACCEPTED_because_record_writes_it(self):
        """⚠⚠ REG-575 — THIS TEST USED TO ASSERT THE OPPOSITE, AND IT WAS WRONG. It was called
        `test_the_three_key_row_score_would_have_DEFAULTED_is_refused` and described
        `{lock, kind, refused}` as *"the forgery that costs nothing to write"*. That row is not a
        forgery: it is EXACTLY what `self_arming.record()` writes, and `score()` documents reading
        it as a single attempt worth 1. So the test pinned my own v2581 defect as the contract —
        one bad row fails the whole read, which means a single `record()` call would have turned
        all fifteen locks UNKNOWN. Two things vouching for a bug is how it becomes invisible, and
        a test whose NAME describes inverted behaviour has to be corrected, not worked around.

        What was genuinely missing is below: a row that is NEITHER shape."""
        rows, why = self._read(self._ledger(
            self._good(), {"lock": "prune.arm", "kind": "live", "refused": True,
                           "ts": int(time.time() * 1000)}))
        self.assertIsNotNone(rows, "a row in record()'s own shape was rejected as unbankable, so "
                                   "one record() call blanks the whole table: %s" % why)

    def test_a_row_that_is_NEITHER_shape_is_still_refused(self):
        """⚠ The real forgery the old test was reaching for: no `src`, so the PROVES allow-list
        cannot apply, but carrying `n`/`k` so score() counts it as an aggregate anyway. It is not
        a bank() row and not a record() row, and accepting it would let counts in by the one door
        that has no source to check them against."""
        rows, why = self._read(self._ledger(
            self._good(), {"lock": "prune.arm", "kind": "sabotage", "refused": True,
                           "n": 99, "k": 99, "ts": int(time.time() * 1000)}))
        self.assertIsNone(rows, "a source-less row carrying 99 refusals was accepted as evidence")
        # ⚠ PINS THE RULE, NOT THE PHRASE. The wording moved in v2612 when the discriminator
        # became aggregate-vs-event; what must hold is that a counted row with nothing declaring
        # what it may prove is refused, and that the reason says why.
        self.assertTrue(("neither shape" in why) or ("no src" in why),
                        "a counted row with no declared source was refused without saying why: %r"
                        % why)

    def test_a_record_row_with_a_non_boolean_outcome_is_refused(self):
        """⚠ BASELINE — accepting record()'s shape must not mean accepting anything without a
        src. The one field it carries still has to be the field it claims."""
        rows, why = self._read(self._ledger(
            self._good(), {"lock": "prune.arm", "kind": "live", "refused": "yes",
                           "ts": int(time.time() * 1000)}))
        self.assertIsNone(rows, "refused='yes' was read as an outcome")

    def test_every_forgery_class_is_refused(self):
        for label, row in (
                ("an undeclared source", self._good(src="my_own_harness")),
                ("a source proving another lock", self._good(lock="miniauto.run")),
                ("an unweighted kind", self._good(kind="vibes")),
                ("k greater than n", self._good(n=5, k=9)),
                ("a boolean count", self._good(n=True, k=True)),
                ("a timestamp in the future",
                 self._good(ts=int((time.time() + 86400) * 1000))),
        ):
            rows, why = self._read(self._ledger(self._good(), row))
            self.assertIsNone(rows, "%s was accepted: %s" % (label, why))

    def test_a_refused_read_makes_may_say_NO(self):
        """UNKNOWN must be LOCKED — a ledger that cannot be trusted opens nothing."""
        p = self._ledger(self._good(), self._good(kind="vibes"))
        was = os.environ.get("TV_SELF_ARMING_LEDGER")
        try:
            os.environ["TV_SELF_ARMING_LEDGER"] = p
            self.assertEqual(SA.score("prune.arm")["state"], SA.UNKNOWN)
            ok, why = SA.may("prune.arm")
            self.assertFalse(ok, "a forged ledger let the deleter through: %s" % why)
        finally:
            if was is None:
                os.environ.pop("TV_SELF_ARMING_LEDGER", None)
            else:
                os.environ["TV_SELF_ARMING_LEDGER"] = was


class TheHardenedTierGivesAnAccountOfItself(unittest.TestCase):
    """⚠⚠ 14 LOCKS OPEN, 0 HARDENED, AND NOT ONE SAID WHY. Measured 2026-09-04: every `why` on an
    OPEN row recited the bar it had already cleared and never mentioned the tier above it, so a
    surface could sit ONE evidence-kind short of his HARDENING stamp indefinitely with the report
    reading exactly as it would if the tier did not exist. An unreachable tier that gives no
    account of itself is indistinguishable from a broken one. [[unknown-stays-unknown]]

    `_hardening_gap` names the shortfall and the cheapest combination of kinds that would close
    it. It LOWERS NOTHING — the bars are his — and the kinds it names are earned by doing that
    work, never by relabelling evidence already banked.
    """

    def test_the_refusal_COUNT_is_real_arithmetic_and_falsifiable(self):
        """⚠ THE SHARP ONE. `moreRefusalsNeeded` is a promise about the future: run this many more
        refused sabotages and HARD_BAR clears. So apply it and check — and check that ONE FEWER
        does NOT clear, or the number would be merely sufficient rather than the answer."""
        import self_arming as SA
        for n in (5, 24, 48, 83):
            g = SA._hardening_gap(SA.wilson_lower(n, n), 1.0, ["sabotage"], n, n)
            need = g["moreRefusalsNeeded"]
            if SA.wilson_lower(n, n) >= SA.HARD_BAR:
                continue
            self.assertIsNotNone(need, "n=%d is below HARD_BAR and no count was offered" % n)
            self.assertGreaterEqual(
                SA.wilson_lower(n + need, n + need), SA.HARD_BAR,
                "n=%d: it promised %d more refusals would clear %.3f and they do not"
                % (n, need, SA.HARD_BAR))
            self.assertLess(
                SA.wilson_lower(n + need - 1, n + need - 1), SA.HARD_BAR,
                "n=%d: %d was not the ANSWER, merely a number large enough — one fewer already "
                "clears the bar" % (n, need))

    def test_it_never_proposes_a_kind_the_surface_ALREADY_has(self):
        """Proposing `sabotage` to a surface whose only evidence is sabotage would be advice to
        relabel — the one move the confluence bar exists to refuse."""
        import self_arming as SA
        g = SA._hardening_gap(0.95, 1.0, ["sabotage"], 90, 90)
        self.assertNotIn("sabotage", g["kindsWouldClose"],
                         "it proposed a kind already banked, which closes the gap on paper only")
        self.assertTrue(g["kindsWouldClose"], "it proposed nothing at all")
        got = 1.0 + sum(SA.KINDS[k] for k in g["kindsWouldClose"])
        self.assertGreaterEqual(round(got, 4), SA.HARD_KINDS_BAR,
                                "the proposed kinds do not actually reach the bar: %.2f" % got)

    def test_an_ALREADY_hardened_surface_reports_no_gap(self):
        import self_arming as SA
        g = SA._hardening_gap(0.99, 3.4, sorted(SA.KINDS), 500, 500)
        self.assertTrue(g["hardened"])
        self.assertEqual(g["why"], "already HARDENED")
        self.assertIsNone(g["wilsonShort"])
        self.assertIsNone(g["kindsShort"])

    def test_an_UNMEASURED_surface_is_not_reported_as_a_SHORT_one(self):
        """⚠ n=0 has no distance to the bar. Rendering it as "short by 0.900" would turn nobody
        having looked into a near miss."""
        import self_arming as SA
        g = SA._hardening_gap(None, 0.0, [], 0, 0)
        self.assertIsNone(g["wilsonShort"])
        self.assertIsNone(g["moreRefusalsNeeded"])
        self.assertIn("unmeasured", g["why"])

    def test_every_scored_row_carries_the_key_on_EVERY_path(self):
        """⚠ REG-547 SHAPE LAW — including the n=0 rows, or "no gap" and "never computed" render
        the same and a consumer cannot tell which it has."""
        import self_arming as SA
        rows = SA.report()["locks"]
        self.assertTrue(rows, "no locks to check")
        for r in rows:
            self.assertIn("hardeningGap", r, "%s carries no gap" % r["lock"])
            for key in ("hardened", "wilsonShort", "kindsShort", "moreRefusalsNeeded",
                        "kindsWouldClose", "why"):
                self.assertIn(key, r["hardeningGap"],
                              "%s's gap is missing %r — a shape that changes with the verdict is "
                              "not a shape" % (r["lock"], key))


class RecordHonoursTheAllowListToo(_Ledger):
    """⚠⚠ REG-591 — THE ONE RULE THAT MATTERS MOST HERE HAD A DOOR WITH NO LOCK ON IT.

    `bank()` refuses any (src, lock) pair PROVES does not declare — that is what stops one
    surface's sabotage opening a DIFFERENT surface's lock, and it matters most for `prune.arm`
    because footage has no undo. `record()` took no `src` at all, so a single call could credit
    ANY lock from anywhere.

    MEASURED when it was found: `record()` had ZERO production callers and his ledger held 51
    bank-shaped rows and 0 record-shaped. **Never a leak — a loaded gun**, and closing it is cheap
    precisely because nobody had pulled the trigger."""

    def test_no_src_is_refused(self):
        with self.assertRaises(ValueError) as e:
            SA.record("prune.arm", "sabotage", True)
        self.assertIn("credit any lock", str(e.exception))

    def test_an_UNDECLARED_src_is_refused(self):
        with self.assertRaises(ValueError):
            SA.record("prune.arm", "sabotage", True, src="my_own_harness")

    def test_a_src_that_proves_ANOTHER_lock_is_refused(self):
        """The actual danger: hover_wilson is real and declared — for miniauto.run. It must not be
        able to credit the deleter."""
        with self.assertRaises(ValueError) as e:
            SA.record("prune.arm", "sabotage", True, src="hover_wilson")
        self.assertIn("does not prove", str(e.exception))

    def test_a_DECLARED_pair_writes_a_row_that_carries_its_source(self):
        row = SA.record("miniauto.run", "sabotage", True, src="hover_wilson")
        self.assertEqual(row["src"], "hover_wilson")
        self.assertIs(row["refused"], True)
        self.assertNotIn("n", row, "a single attempt must not carry counts — it is an EVENT")

    def test_events_STILL_accumulate_now_that_they_carry_a_src(self):
        """⚠⚠ THE REGRESSION THIS FIX CAUSED AND THEN CLOSED. `_fold` keyed on `src`, so the
        moment single attempts grew one, three separate events folded into ONE and the count read
        (0, 1) instead of (2, 3). Only AGGREGATES fold — an event is not a re-report of anything."""
        for refused in (True, True, False):
            SA.record("miniauto.run", "sabotage", refused, src="hover_wilson")
        sc = SA.score("miniauto.run")
        self.assertEqual((sc["k"], sc["n"]), (2, 3),
                         "three events folded instead of accumulating: %r" % ((sc["k"], sc["n"]),))



class TestV2618AScoreMayNotBeBoughtByRepetition(unittest.TestCase):
    """★ HIS QUESTION, 2026-09-04: *"just check and make sure its really unlocked and not
    fabricated"*, then *"83 only? why not 300+ for each wilson? like why so low the score?"*

    The answer to the second is the reason for this class. Wilson tightens with n and **has no way
    to tell 83 independent looks from ONE attack applied 83 times**, so running the same sabotage
    over more inputs buys a higher score and proves nothing new.

    ⚠⚠ MEASURED ON HIS OWN LEDGER, and it is not hypothetical. `printer.stream` banked **83/83 ->
    wilson 0.9558**, the highest of the five, on ONE ledger line at ONE timestamp. Re-running the
    harness: `ownerraises` **40** and `reachraises` **40** are each ONE attack applied to all forty
    of his reels; `ownerempty`, `namelessrows` and `strangerreel` are 1 each. **Five distinct
    attacks.** On five, the identical evidence scores **0.5655** — barely over its 0.510 bar.

    **Nothing was faked.** Every refusal is real, the harness patches live functions, and it has
    been seen RED (its own docstring records 0 of 40 refused, dragging it to 43/83). What was
    wrong was the READING: the same objection already standing against `prune.arm` — *"one proof
    wearing four hats"* — at forty hats.
    """

    def setUp(self):
        self._rows = [{"lock": "printer.stream", "kind": "sabotage", "src": "printer_wilson",
                       "n": 83, "k": 83, "attacks": 5, "ts": 1}]

    def test_it_reports_the_score_the_DISTINCT_attacks_earn(self):
        r = SA.score("printer.stream", rows=self._rows)
        self.assertEqual(r["n"], 83)
        self.assertEqual(r["attacks"], 5)
        self.assertAlmostEqual(r["wilsonByAttack"], round(SA.wilson_lower(5, 5), 4), places=4)
        self.assertLess(r["wilsonByAttack"], r["wilson"],
                        "the by-attack score is not lower than the by-trial score, so repetition "
                        "is invisible exactly where it inflates")

    def test_it_says_HOW_MANY_TIMES_each_attack_was_repeated(self):
        r = SA.score("printer.stream", rows=self._rows)
        self.assertAlmostEqual(r["repetition"], 16.6, places=1)

    def test_a_harness_that_did_NOT_declare_its_attacks_reports_None_not_one(self):
        """⚠ THE TRAP. Defaulting an unstated attack count to 1 would report every older harness
        as maximally repetitious, and defaulting it to n would report every one as perfectly
        independent. Both are verdicts nobody measured. [[unknown-stays-unknown]]"""
        rows = [{"lock": "printer.stream", "kind": "sabotage", "src": "printer_wilson",
                 "n": 83, "k": 83, "ts": 1}]
        r = SA.score("printer.stream", rows=rows)
        self.assertIsNone(r["attacks"], "an unstated attack count became a number")
        self.assertIsNone(r["wilsonByAttack"])
        self.assertIsNone(r["repetition"])

    def test_the_key_is_present_on_EVERY_path_including_n_zero(self):
        """REG-547 — a row that carries `attacks` only sometimes makes 'not repetitious' and
        'never computed' render identically."""
        for rows in ([], self._rows):
            r = SA.score("vault.forget" if not rows else "printer.stream", rows=rows)
            for key in ("attacks", "wilsonByAttack", "repetition"):
                self.assertIn(key, r, "%r is missing on one path" % key)

    def test_the_LIVE_printer_harness_now_declares_its_attack_count(self):
        """⚠ The arithmetic is worthless if the one harness that provoked it does not report.
        Pins the JOIN, not the number — a sixth attack must not break this."""
        import inspect
        import printer_wilson as PW
        src = inspect.getsource(PW.bank_into_proof_queue)
        self.assertIn("attacks=", src,
                      "printer_wilson banks without saying how many distinct attacks it ran, so "
                      "its 83 still reads as 83 independent looks")




class TestV2619AnUnexercisedAxisHoldsTheLock(unittest.TestCase):
    """★★ HIS CATCH, 2026-09-04, AND IT IS THE SHARPEST OF THE WHOLE AUDIT.

    Told that `miniauto.run` read OPEN at 55/55 he answered: *"absolutely has not been proven or
    done yet… its not working at all what do you mean? it should be locked as hell!"*

    **He was right, and the harness's own words say why.** `hover_wilson.probe_anchor` banks a
    claim with **n = 0**, because `slot_identity.anchor_from_tooltip_rect` refuses: *"no
    tooltip->cell OFFSET has been calibrated, so the anchor would be the tip's own corner and
    EVERY ITEM WOULD LAND IN WHICHEVER CELL THE TEXT COVERS."* That sentence is a precise
    description of MINI AUTO not working — and it is the ONLY probe that tests whether a hover
    lands on the right cell.

    ⚠⚠ **ZERO ATTEMPTS CANNOT MOVE A WILSON BOUND.** So the axis did not fail the score, it was
    ABSENT from it: the lock scored 0.9347 on its other claims — 48 of which are floor-division
    assertions (REG-600) — and reported OPEN over a feature that does not work. **A declared claim
    that could not run is not an absent claim**, and treating the two alike is the same collapse
    as reading `None` as `0`. [[unknown-stays-unknown]]

    ⚠ IT IS A REPORT, NOT A GATE. `may()` is still never called and no button is blocked; what
    changes is that the badge stops saying proven.
    """

    def _rows(self, blind=True):
        rows = [{"lock": "miniauto.run", "kind": "sabotage", "src": "hover_wilson",
                 "ref": "coordinate", "n": 48, "k": 48, "ts": 1},
                {"lock": "miniauto.run", "kind": "sabotage", "src": "hover_wilson",
                 "ref": "read", "n": 5, "k": 5, "ts": 2},
                {"lock": "miniauto.run", "kind": "sabotage", "src": "hover_wilson",
                 "ref": "slot", "n": 2, "k": 2, "ts": 3}]
        if blind:
            rows.append({"lock": "miniauto.run", "kind": "sabotage", "src": "hover_wilson",
                         "ref": "anchor", "n": 0, "k": 0, "ts": 4})
        return rows

    def test_a_claim_banked_with_ZERO_attempts_stops_the_lock_reading_OPEN(self):
        r = SA.score("miniauto.run", rows=self._rows(blind=True))
        self.assertEqual(r["state"], SA.INCOMPLETE,
                         "a lock whose own harness never exercised one of its claims still "
                         "reported %r" % r["state"])
        self.assertEqual(r["blindClaims"], ["anchor"])

    def test_the_reason_NAMES_the_claim_that_never_ran(self):
        """A state with no name attached sends him looking through four probes for the one that
        did not fire."""
        r = SA.score("miniauto.run", rows=self._rows(blind=True))
        self.assertIn("anchor", r["why"])
        self.assertIn("never exercised", r["why"])

    def test_it_does_NOT_pretend_the_other_claims_failed(self):
        """⚠ The axis is MISSING from the score, not failing it. Reporting 55/55 as though it had
        been refuted would be a different lie in the other direction."""
        r = SA.score("miniauto.run", rows=self._rows(blind=True))
        self.assertEqual(r["n"], 55)
        self.assertEqual(r["k"], 55)
        self.assertGreater(r["wilson"], 0.9)

    def test_WITHOUT_the_blind_claim_the_same_evidence_is_OPEN(self):
        """⚠⚠ THE BASELINE, AND IT IS THE WHOLE RISK. If this marked every lock INCOMPLETE the
        state would carry no information at all."""
        r = SA.score("miniauto.run", rows=self._rows(blind=False))
        self.assertEqual(r["state"], SA.OPEN, r.get("why"))
        self.assertEqual(r["blindClaims"], [])

    def test_it_does_not_touch_the_OTHER_locks(self):
        """Measured on the live ledger: only miniauto.run banks a zero-attempt claim, so exactly
        one lock may change state. A rule that quietly re-badged five surfaces would be a much
        bigger thing than the defect it fixes."""
        changed = [r["lock"] for r in SA.report()["locks"] if r["state"] == SA.INCOMPLETE]
        self.assertEqual(changed, ["miniauto.run"],
                         "INCOMPLETE spread beyond the one lock with an unexercised claim: %s"
                         % changed)

    def test_UNPROVEN_is_untouched_because_it_banked_NOTHING(self):
        """⚠ A lock with no rows at all is a different fact from one with a row that could not run. Collapsing them
        would relabel a door nobody has attacked as one whose attack was blind. (REG-3819: vault.forget, the lock this
        read live, now banks evidence, so the no-rows case is handed in explicitly.)"""
        r = SA.score("vault.forget", rows=[])
        self.assertEqual(r["state"], SA.UNPROVEN)
        self.assertEqual(r["blindClaims"], [])




class TestV2623EveryHarnessDeclaresItsAttackCount(unittest.TestCase):
    """★ REG-598, swept. Wiring five of six harnesses and calling it done is how the sixth becomes
    the one nobody notices — and the sixth here was `hover_wilson`, which carries the WORST
    inflation of all: 48 of its 55 trials are two probes applied to 24 synthetic grid cells each.

    ⚠ IT ASKS EVERY SOURCE THE ALLOW-LIST DECLARES, not a list typed here. A harness added later
    is covered the day it is registered, without anyone remembering this file exists.
    [[sweep-dont-ask]]
    """

    #: `render_check` proves no lock — it is in PROVES with an empty list — so it banks nothing and
    #: owes nothing. Named, not silently skipped: an exemption nobody can see is a hole.
    BANKS_NOTHING = {"render_check"}

    def _module_for(self, src):
        """The harness module behind an evidence source name. -> module | None"""
        import importlib
        for guess in (src, src.replace("_live", "_wilson")):
            try:
                return importlib.import_module(guess)
            except Exception:
                continue
        return None

    def test_every_declared_evidence_source_passes_attacks(self):
        import inspect
        missing, checked = [], 0
        for src in sorted(SA.PROVES):
            if src in self.BANKS_NOTHING:
                continue
            mod = self._module_for(src)
            if mod is None:
                continue                      # its module is not importable here; not this test's claim
            try:
                text = inspect.getsource(mod)
            except Exception:
                continue
            if ".bank(" not in text:
                continue                      # this source does not bank at all
            checked += 1
            # ⚠⚠ PARSE THE CALLS, DO NOT GREP THE TEXT — and the first cut of this DID grep, for
            # `\.bank\(`. It failed on five of six harnesses, and every "extra" match was PROSE:
            # my own comment "See self_arming.bank() and REG-598", and route_wilson's docstring
            # "in the shape self_arming.bank() takes". The code was right and the guard was
            # counting sentences — the third time in one day a check graded documentation instead
            # of behaviour. An AST walk cannot be fooled by a comment.
            # [[source-reading-guard]] [[feedback-comments-vs-code]]
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                if name != "bank":
                    continue
                if not any(kw.arg == "attacks" for kw in (node.keywords or [])):
                    missing.append("%s: a bank() call at line %d does not declare attacks"
                                   % (src, getattr(node, "lineno", -1)))
        self.assertTrue(checked, "no harness was actually inspected — this test proved nothing")
        self.assertEqual(missing, [],
                         "a Wilson score can still be bought by repetition here: %s"
                         % "; ".join(missing))

    def test_the_exemption_is_NAMED_and_really_proves_nothing(self):
        """⚠ An exemption list is a hole unless each entry is checked to still deserve it."""
        for src in self.BANKS_NOTHING:
            self.assertIn(src, SA.PROVES, "%s is exempted but is not a declared source" % src)
            self.assertEqual(list(SA.PROVES[src]), [],
                             "%s is exempted from declaring attacks but DOES prove a lock" % src)




class TestV2629NoThirdSpellingForARoute(unittest.TestCase):
    """★ REG-470, closed the way the measurement supports — by stopping the drift, not by paying a
    migration that buys nothing.

    His three route sets do not agree: `chronicle.runeword` and `roster.runeword` are SINGULAR
    while `fleet.runewords`, `fleet.sets`, `fleet.uniques` are PLURAL. A3 logged it and explicitly
    did NOT fix it, only stopped it corrupting the matrix.

    ⚠⚠ MEASURED BEFORE DECIDING, AND THE MEASUREMENT ARGUED AGAINST THE OBVIOUS FIX:
      · `one_name` ALREADY resolves it — `same_thing('fleet.runewords','chronicle.runeword')` is
        True, and `form(n,'route')` canonicalises both spellings to the singular.
      · `organ_matrix` publishes every form, so nothing mis-joins today.
      · and the self-arming ledger is keyed on the RAW names — renaming `fleet.runewords` would
        **orphan its banked rows and drop that lock to UNPROVEN**. A cosmetic rename that costs a
        surface its evidence is a bad trade.

    So the inconsistency stays, NAMED, and this stops a THIRD spelling ever arriving. A new route
    must use the canonical route form; the three legacy keys are listed with their reason, and the
    list is checked to still be true rather than being a place to add things.
    """

    #: the three keys that predate `one_name` and keep their spelling because renaming them would
    #: orphan banked evidence. NOT a licence to add more — the next case asserts they are still
    #: exactly the routes that disagree.
    LEGACY = {"fleet.runewords", "fleet.sets", "fleet.uniques"}

    def _canonical(self, key):
        """The canonical route spelling for this key, or None if one_name does not know it.

        ⚠⚠ NO `or tail` FALLBACK, AND THE FIRST CUT HAD ONE. `one_name.form()` returns None for a
        concept it does not recognise, so falling back to the input made every MISSPELLING equal
        to its own canonical form and pass. Proven by sabotage: declaring `roster.runewordses`
        left this suite GREEN — the guard was measuring nothing for exactly the case it exists to
        catch. An unknown concept is now a failure, not a default.
        [[unknown-stays-unknown]] [[sabotage-is-usually-the-wrong-one]]
        """
        import one_name as ON
        tail = key.split(".", 1)[1] if "." in key else key
        return ON.form(tail, "route")

    def test_every_route_uses_the_canonical_form_or_is_named_legacy(self):
        bad = []
        for key in sorted(SA.ROUTES):
            tail = key.split(".", 1)[1] if "." in key else key
            canon = self._canonical(key)
            if canon is None:
                bad.append("%s names a concept one_name does not know (%r) — a route whose noun "
                           "is unrecognised cannot be joined to anything" % (key, tail))
                continue
            if tail != canon and key not in self.LEGACY:
                bad.append("%s (canonical route form is %r)" % (key, canon))
        self.assertEqual(bad, [],
                         "a route was declared with a spelling one_name does not consider "
                         "canonical, and it is not on the named legacy list: %s" % "; ".join(bad))

    def test_the_LEGACY_list_is_still_TRUE_and_not_a_dumping_ground(self):
        """⚠ An exemption list nobody re-checks becomes the place drift hides. Every entry must
        still actually disagree with the canonical form — if one gets fixed, it must leave."""
        for key in sorted(self.LEGACY):
            self.assertIn(key, SA.ROUTES, "%s is exempted but is no longer a declared route" % key)
            tail = key.split(".", 1)[1]
            self.assertIsNotNone(self._canonical(key),
                                 "%s is on the legacy list but one_name no longer knows its "
                                 "concept at all" % key)
            self.assertNotEqual(
                tail, self._canonical(key),
                "%s now matches the canonical form, so it is not legacy any more and must come "
                "off this list" % key)

    def test_one_name_really_does_join_the_two_spellings(self):
        """⚠ The load-bearing claim under the decision NOT to rename. If this stops being true,
        the split IS corrupting joins and the trade changes."""
        import one_name as ON
        for a, b in (("fleet.runewords", "chronicle.runeword"),
                     ("fleet.sets", "roster.set"),
                     ("fleet.uniques", "chronicle.unique")):
            self.assertTrue(ON.same_thing(a, b),
                            "one_name no longer joins %r and %r — the split is now a real "
                            "mis-join and REG-470 needs the migration after all" % (a, b))

    def test_renaming_a_legacy_route_would_orphan_its_evidence(self):
        """⚠ The cost that decided this. Pinned so a later reader does not 'tidy' the names and
        silently drop three locks to UNPROVEN."""
        rows, why = SA._rows()
        if rows is None:
            self.skipTest("the ledger could not be read here: %s" % why)
        banked = {r.get("lock") for r in rows}
        for key in sorted(self.LEGACY):
            if key in banked:
                self.assertIn(key, SA.ROUTES,
                              "%s has banked evidence under a name the table no longer declares — "
                              "that lock has lost its proof" % key)





class TheCountsNameTheSameQuantityAsTheFigure(unittest.TestCase):
    """⚠ ddd55279 made the DECISION honest and left every sentence printing the raw counts.

    A row read `56 of 56 sabotages refused * wilson 0.646`, and 56/56 is 0.936 — the number was
    right and the words beside it named another quantity. Nobody can check arithmetic that does
    not reconcile, so a reader either trusts it blindly or stops reading it.

    THE LAW, not the number: whatever pair a scored row prints, feeding that pair back through
    the module's OWN wilson_lower must reproduce the figure printed beside it.
    """

    def _scored(self):
        rep = SA.report()
        return [l for l in (rep.get("locks") or []) if l.get("wilson") is not None]

    def test_the_printed_pair_reproduces_the_printed_figure(self):
        seen = 0
        for l in self._scored():
            why = l.get("why") or ""
            m = re.match(r"\s*(\d+) of (\d+) ", why)
            if not m:
                continue                      # INCOMPLETE/blind rows word it differently, by design
            k, n = int(m.group(1)), int(m.group(2))
            shown = l.get(l.get("deciding") or "wilson")
            if shown is None:
                continue
            seen += 1
            self.assertAlmostEqual(
                SA.wilson_lower(k, n), shown, places=3,
                msg=("%s prints '%d of %d' beside wilson %.3f, but wilson_lower(%d, %d) is %.3f. "
                     "The pair and the figure name different quantities."
                     % (l.get("lock"), k, n, shown, k, n, SA.wilson_lower(k, n))))
        self.assertGreater(seen, 0, "no scored row carried a readable pair — this proved nothing")

    def test_at_least_one_row_is_actually_decided_per_attack(self):
        """Anti-vacuity: if nothing decides on wilsonByAttack, the law above never fires."""
        by = [l for l in self._scored() if l.get("deciding") == "wilsonByAttack"]
        self.assertTrue(by, "no lock decided per attack, so the reconciliation law was untested")
        for l in by:
            self.assertIn("DISTINCT ATTACKS", l.get("why") or "",
                          "%s decides per attack but its sentence does not say so" % l.get("lock"))

    def test_the_advice_counts_what_the_bar_counts(self):
        """REG-616: `moreRefusalsNeeded` must be expressed in the unit that DECIDES.

        It was computed from the raw attempt count while the bar reads the per-attack score, so it
        told reel.route "1 more refused sabotage would clear it" when a 57th attempt leaves the 7
        distinct attacks — and the figure — untouched. Advice that recommends repetition is worse
        than no advice here: repetition is the exact thing the ruling refuses to reward.

        THE LAW: adding that many to the DECIDING denominator must actually clear HARD_BAR, and
        one fewer must not (it is the smallest such number, not merely a sufficient one).
        """
        checked = 0
        for l in self._scored():
            g = l.get("hardeningGap") or {}
            m = g.get("moreRefusalsNeeded")
            if m is None:
                continue
            pair = re.match(r"\s*(\d+) of (\d+) ", l.get("why") or "")
            if not pair:
                continue
            d = int(pair.group(2))                      # the deciding denominator
            checked += 1
            self.assertGreaterEqual(
                SA.wilson_lower(d + m, d + m), SA.HARD_BAR,
                "%s: +%d on a denominator of %d does not reach HARD_BAR" % (l.get("lock"), m, d))
            self.assertLess(
                SA.wilson_lower(d + m - 1, d + m - 1), SA.HARD_BAR,
                "%s: +%d is not minimal — one fewer already clears" % (l.get("lock"), m))
        self.assertGreater(checked, 0, "no row carried advice — this proved nothing")

    def test_the_old_raw_denominator_advice_would_FAIL_this_law(self):
        """RED-PROOF, on the real historical value rather than an invented one.

        Before REG-616 the report told reel.route "1 more refused sabotage would clear it", derived
        from the raw pair n=56 -> wilson_lower(57, 57) >= 0.900. reel.route's DECIDING denominator
        is 7 distinct attacks, so the law above must reject +1 on 7.
        """
        d, old_m = 7, 1
        self.assertLess(SA.wilson_lower(d + old_m, d + old_m), SA.HARD_BAR,
                        "the old advice would have satisfied the law, so the law proves nothing")
        self.assertGreaterEqual(SA.wilson_lower(d + 28, d + 28), SA.HARD_BAR,
                                "+28 on 7 distinct attacks should be the honest answer")

    def test_a_mismatched_pair_is_caught(self):
        """RED-PROOF: the assertion must fail on a row whose pair does not match its figure."""
        bad = {"lock": "fake", "deciding": "wilson", "wilson": 0.646, "why": "56 of 56 refused"}
        self.assertNotAlmostEqual(SA.wilson_lower(56, 56), bad["wilson"], places=3)


if __name__ == "__main__":
    try:
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    unittest.main(verbosity=1)
