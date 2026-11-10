#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""♥🔒 A SURFACE MAY NOT ARM ITSELF WHILE ITS INSTRUMENTS ARE BLIND.

Konyo, 2026-09-09: *"the lock and everything still derives from the heart and visually seen"*.
MEASURED when he asked: `self_arming.py` and `hover_wilson.py` held ZERO references to heart2. The
Wilson lock and the heart were two systems that never spoke, so a surface could reach its bar and
ARM ITSELF while the gates that would catch its failure were dark — the lock proving the surface
works, with nothing left able to prove the PROOF works.

A Wilson score says "this refused every attack we made". It cannot say "and we would have noticed
if it had not". That second question is the heart's, and it belongs in the same precondition chain
as the upstream check `may()` already runs: proving a surface in isolation proves nothing about what
feeds it, and an instrument that cannot go red is exactly that kind of missing prerequisite.
[[the-unjoined-end]] [[join-gate-heart]]

MEASURED after the join, on the real lock:
    1 BLIND instrument   -> may(printer.stream) False
    unreadable census    -> False   ("UNKNOWN fails CLOSED")
    absent census        -> False
    restored             -> True    (so it is a gate, not furniture)
"""
import ast
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import console_safe  # noqa: E402  — this file prints ♥ 🔒 ⚠ ★
console_safe.enable()

import self_arming as SA  # noqa: E402
import heart2 as H  # noqa: E402

STATE = os.path.join(H.HERE, ".heart2.json")


class _Census(object):
    """Swap the heart's census for the duration of one law, and always put it back."""

    def __init__(self, payload):
        self.payload = payload
        self.bak = None

    def __enter__(self):
        if os.path.exists(STATE):
            self.bak = STATE + ".lawtest"
            shutil.copy(STATE, self.bak)
        if self.payload is None:
            if os.path.exists(STATE):
                os.unlink(STATE)
        else:
            with io.open(STATE, "w", encoding="utf-8") as fh:
                fh.write(self.payload)
        return self

    def __exit__(self, *a):
        if self.bak and os.path.exists(self.bak):
            shutil.move(self.bak, STATE)
        elif os.path.exists(STATE) and not self.bak:
            os.unlink(STATE)
        return False


def _real_census():
    return io.open(STATE, encoding="utf-8").read() if os.path.exists(STATE) else None


RED_PROOF = [
    {
        "why": "un-asking the heart returns the lock to what it was — a surface that can arm itself "
               "while the gates that would catch its failure are blind",
        "file": "self_arming.py",
        "find": "    _hok, _hwhy = _heart_says_watched()\n    if not _hok:",
        "replace": "    _hok, _hwhy = (True, \"\")\n    if not _hok:",
        "matches": 1,
    },
    {
        "why": "letting a BLIND instrument pass is the defect itself: the lock arming on a Wilson "
               "score while nothing can prove the proof still works",
        "file": "self_arming.py",
        "find": "    if _blind:",
        "replace": "    if False and _blind:",
        "matches": 1,
    },
    {
        "why": "removing the staleness refusal lets a census from before the gates changed read as "
               "authoritative — a proof that no longer speaks for the instruments on disk",
        "file": "self_arming.py",
        "find": "    if _have != _want:",
        "replace": "    if False and _have != _want:",
        "matches": 1,
    },
    {
        "why": "v2869's defect: reading a gate by its BARE basename, which resolves against the "
               "caller's cwd. From the repo root every gate read as UNREADABLE, the digest moved, "
               "and may() called a seconds-old census STALE and refused every lock permanently",
        "file": "heart2.py",
        "find": '        src = _read_text(f if os.path.isabs(f) else os.path.join(HERE, f))\n        if src is None:\n            # \u26a0 v2864',
        "replace": '        src = _read_text(f)\n        if src is None:\n            # \u26a0 v2864',
        "matches": 1,
    },
]


def _skip_if_stale(case):
    """Editing ANY gate file changes the fingerprint and makes the live census stale — including
    edits to THIS file, which is itself a gate. That refusal is CORRECT and has its own law below;
    it must not make every other law here fail. Measured: saving this file turned 3 laws red for no
    reason but the save. [[feedback-blind-fixture-green-gate]]"""
    ok, why = SA._heart_says_watched()
    if not ok and "STALE" in (why or ""):
        case.skipTest("live census is stale (gates changed since the last prove) — re-prove first")


def _census_the_heart_would_call_CURRENT():
    """A census this machine accepts as current, so the only variable a law changes is its own.

    ⚠⚠ v2866 — THIS LAW SHIPPED BLIND, AND THE SKIP IS WHY. `--prove` runs each arm in a
    sandbox built by safe_copy, and `.heart2.json` is gitignored, so the copy has NO census. The law
    then called `self.skipTest("no census on this machine")` — and a skip is not a red. heart2
    recorded arm [1] (`if _blind:` → `if False and _blind:`) as BLIND, and v2865 shipped with
    `blind: 1` in its own census. An instrument that cannot go red in the sandbox is exactly the
    thing this whole file exists to refuse, sitting inside the file that refuses it.

    Building the census here removes BOTH skips at once: the fingerprint is current by
    construction, and a machine that has never run the heart no longer opts out. What is under test
    is `_heart_says_watched`'s `blind` branch, and that branch needs only these two keys.
    [[feedback-blind-fixture-green-gate]] [[the-unjoined-end]]

    ⚠ IT READS NOTHING. The first cut seeded itself from the live census and swallowed a parse
    failure into `{}` — RANK 1 on the swallow ratchet, "a failed read handed back as DATA",
    `tv/test_the_lock_derives_from_the_heart.py 0 -> 1`, caught by CI within the hour and correctly:
    an unreadable census would have produced a fixture that LOOKED built. There was never a reason
    to read. `_heart_says_watched` consults exactly these keys, and a fixture that borrows a
    machine-local file is a fixture whose subject can change without anyone editing it.
    [[feedback-fixtures-never-touch-live-data]] [[unknown-stays-unknown]]
    """
    return {
        "gatesFingerprint": H.gates_fingerprint(),
        "blind": [],
        "proved": 0,
        "total": 0,
    }


class TheLockDerivesFromTheHeart(unittest.TestCase):

    # ── ⚠⚠ THE LAW ──────────────────────────────────────────────────────────────────────────
    def test_a_BLIND_instrument_closes_the_lock(self):
        """★★ The whole join. A dark gate is a missing prerequisite, not a detail.

        ⚠ NO SKIP HERE, DELIBERATELY. See _census_the_heart_would_call_CURRENT: the two skips
        this law used to carry are what made it BLIND in its own prover."""
        st = _census_the_heart_would_call_CURRENT()
        st["blind"] = ["test_an_instrument_that_cannot_go_red"]
        with _Census(json.dumps(st)):
            ok, why = SA.may("printer.stream")
        self.assertFalse(ok, "a lock armed itself while an instrument was BLIND — the Wilson score "
                             "proved the surface and nothing was left to prove the proof")
        self.assertIn("BLIND", why)

    def test_the_fingerprint_does_not_depend_on_the_CALLERS_DIRECTORY(self):
        """★★ v2869 — THE LOCK WAS DEAD-CLOSED FOR EVERY CALLER NOT STANDING IN tv/.

        `gate_files()` returns BARE BASENAMES; `gates_fingerprint()` handed one to `_read_text`,
        which opens relative to the process's cwd. MEASURED from the repo root: 273 of 273 gates
        UNREADABLE, digest 4d640d7d instead of 55330cec, so a census written seconds earlier read
        as STALE and `may()` refused every surface. Not a staleness annoyance — a permanent,
        silent, total refusal decided by where the caller happened to stand.

        Same family as v2862's mtime and v1867's port: a rule that only holds in the tree — or the
        directory — it was run from. [[stale-reading]] [[copy-drift]]"""
        here = os.getcwd()
        tmp = tempfile.mkdtemp(prefix="cwd-")
        try:
            mine = H.gates_fingerprint()
            unk_a = []
            px_a = H.pixel_gates(None, unk_a)
            os.chdir(tmp)
            theirs = H.gates_fingerprint()
            unk_b = []
            px_b = H.pixel_gates(None, unk_b)
        finally:
            os.chdir(here)
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(
            mine, theirs,
            "the gate fingerprint changed with the working directory (%s here, %s from %r). Every "
            "caller outside tv/ would read a fresh census as STALE and the lock would refuse every "
            "surface for ever." % (mine[:12], theirs[:12], tmp))
        self.assertEqual(
            (len(px_a), len(unk_a)), (len(px_b), len(unk_b)),
            "the pixel/backend split changed with the working directory: %d pixel / %d unclassified "
            "here vs %d / %d elsewhere. That number answers 'is 100%% also a visual pass', and it "
            "must not be produced by the reader's cwd."
            % (len(px_a), len(unk_a), len(px_b), len(unk_b)))
        self.assertEqual([], unk_a,
                         "%d gate(s) are unclassifiable even from tv/: %s" % (len(unk_a), unk_a[:4]))

    def test_an_UNREADABLE_census_fails_CLOSED(self):
        """★★ Matching _rows(): UNKNOWN never arms anything.

        ⚠ NO SKIP. `_Census` writes the garbage whether or not a real census was there to back
        up, so requiring one only meant this law stopped running exactly where it matters."""
        with _Census("{ this is not json"):
            ok, why = SA.may("printer.stream")
        self.assertFalse(ok, "an unreadable heart census permitted a lock to act")
        self.assertIn("CLOSED", why)

    def test_an_ABSENT_census_fails_CLOSED(self):
        """★ Never run here is not the same as nothing wrong here.

        ⚠⚠ v2867 — THIS SKIPPED ON THE ONE CONDITION IT EXISTS TO TEST. A cross-family review of
        v2865: on a runner with no `.heart2.json` — CI, and every heart2 sandbox, because the file
        is gitignored — this law skipped, `test_an_UNREADABLE_census_fails_CLOSED` skipped, and
        v2865's `setUpModule` in test_self_arming stubbed `_heart_says_watched` to (True, …). So
        NOTHING on that runner asserted that `may()` fails closed when the heart has never run. A
        fail-open edit — dropping `if not _hok: return False, _hwhy` — was invisible in one suite
        and skipped in the suite whose comment names it as the owner.
        REPRODUCED before fixing: with `.heart2.json` moved aside, `OK (skipped=7)` and both
        fail-closed laws among them. `_Census(None)` removes the file whether or not one was there,
        so the guard bought nothing. [[the-unjoined-end]] [[feedback-blind-fixture-green-gate]]"""
        with _Census(None):
            ok, why = SA.may("printer.stream")
        self.assertFalse(ok, "a missing heart census permitted a lock to act")
        self.assertIn("CLOSED", why)

    def test_it_is_a_GATE_not_furniture(self):
        """★★ A check that can only say no would be switched off within a week.
        With the real census — 0 blind today — at least one declared lock must still be able to
        act, or this law has proved nothing except that it can refuse. [[feedback-blind-fixture-green-gate]]"""
        if _real_census() is None:
            self.skipTest("no census on this machine")
        # ⚠ STALENESS IS A DIFFERENT, CORRECT REFUSAL. Editing ANY gate file makes the census stale
        # and closes every lock until a re-prove — including edits to THIS file, which is itself a
        # gate. That is the rule working, not furniture, so skip rather than fail: measured when
        # this law first ran and reported 3 failures purely because I had just saved it.
        _skip_if_stale(self)
        opened = [k for k in list(SA.LOCKS) + list(SA.ROUTES) if SA.may(k)[0]]
        self.assertTrue(
            opened,
            "with a healthy heart NOT ONE surface may act. Either every lock is genuinely shut, or "
            "this join refuses unconditionally — and a gate that can only say no is furniture.")

    def test_the_heart_check_runs_BEFORE_the_score(self):
        """★ Order matters: a blind instrument must be reported as the reason, not a Wilson number."""
        _skip_if_stale(self)
        real = _real_census()
        if real is None:
            self.skipTest("no census on this machine")
        st = json.loads(real)
        st["blind"] = ["test_dark"]
        with _Census(json.dumps(st)):
            _, why = SA.may("vault.apply")          # a lock that is ALSO blocked upstream
        self.assertIn("BLIND", why,
                      "a blind heart was masked by another refusal — he would read the downstream "
                      "reason and never learn the instruments were dark: %r" % why)


    def test_a_STALE_census_closes_the_lock(self):
        """★★ v2862 — a cross-family review: "the file still exists with blind=[], so may() returns
        true and a surface can arm itself even though no live supervision has run since".

        ⚠⚠ AND THE FIRST CUT OF THIS RULE USED MTIME, WHICH THE SANDBOX REFUTED. safe_copy, a git
        checkout, CI and the Windows machine all stamp fresh mtimes, so every gate read as newer
        than the census, every lock closed, and --prove reported this very gate UNPROVABLE because
        it was already red in its own copy. A rule that only holds in the tree that wrote it is not
        a rule. The bar is a CONTENT fingerprint, which survives copying. [[stale-reading]]

        ⚠⚠ REG-2365 — BUILT HERE, NEVER READ FROM HIS CENSUS, FOR v2866's REASON. This case read the live census and
        skipped without one, and it is the ONE catcher of red-proof [2]. A heart2 sandbox carried his census only by
        accident (safe_copy copies gitignored files); once make_sandbox stopped carrying live run records, the case
        skipped in both runs and [2] read BLIND (MEASURED on the REG-2365 branch). The census below is current by
        construction and then made stale - the only variable this law changes is its own."""
        st = _census_the_heart_would_call_CURRENT()
        st["gatesFingerprint"] = "0" * 32          # a census proved against DIFFERENT instruments
        with _Census(json.dumps(st)):
            ok, why = SA._heart_says_watched()
            # v3049 — STALE softens for NON-destructive surfaces (the river-strip live-bug fix:
            # a display must not go blank because the prover has not caught up). The guarantee
            # this law protects survives where it matters: an IRREVERSIBLE act still fails
            # closed on a stale census, so assert it on a destructive lock.
            locked, lwhy = SA.may("vault.apply")
        self.assertFalse(ok, "a census whose fingerprint does not match the gates on disk still "
                             "read as authoritative")
        self.assertIn("STALE", why)
        self.assertFalse(locked, "a DESTRUCTIVE lock armed on a stale census")
        self.assertIn("STALE", lwhy)

    def test_the_staleness_bar_is_CONTENT_not_mtime(self):
        """★★ The portability law. Touching a gate file must NOT make the census stale; changing
        one MUST. Copying a repo resets mtimes, so an mtime rule closes every lock on every fresh
        checkout — which is how the sandbox caught it."""
        _skip_if_stale(self)
        import time
        gates = H.gate_files()
        if not gates or _real_census() is None:
            self.skipTest("no gates or no census on this machine")
        name, path = gates[0]
        # ⚠ gate_files() names files RELATIVE to tv/; stat them there, never against whatever the
        # process started in — from the repo root this raised FileNotFoundError and the portability
        # law errored instead of judging. A path is a claim about a directory. [[ship-skill]]
        path = path if os.path.isabs(path) else os.path.join(H.HERE, path)
        st = os.stat(path)
        os.utime(path, (st.st_atime, time.time() + 5))     # mtime only, content untouched
        try:
            ok, why = SA._heart_says_watched()
        finally:
            os.utime(path, (st.st_atime, st.st_mtime))
        self.assertTrue(
            ok, "a TOUCHED gate file (mtime moved, content identical) made the census read as "
                "stale: %r. That rule closes every lock on any copied tree — safe_copy, CI, a "
                "fresh checkout — and it is why the sandbox reported this gate UNPROVABLE." % why)

    def test_the_permit_reason_carries_the_COVERAGE(self):
        """★ blind=[] with 12 of 47 proved means almost nothing was exercised. That is not gated —
        picking a ratio bar would be inventing a law — but it must never be INVISIBLE."""
        _skip_if_stale(self)
        ok, why = SA._heart_says_watched()
        if not ok:
            self.skipTest("the heart is not currently permitting — nothing to read")
        # ⚠ v3318 — THIS ASSERTED THE LOWERCASE WORD, AND THE WORD IS NOT THE POINT. The
        # docstring above says the coverage "must never be INVISIBLE"; a sentence containing the
        # string "proved" and no figures satisfies the old check while showing nothing. v3318
        # rewrote the permit to say "395 of 418 gate(s) that declare a proof are PROVEN" — more
        # coverage than before, in this repo's own PROVEN vocabulary — and the lowercase literal
        # went red for a wording change that improved what it was guarding.
        # STRENGTHENED, NOT RELAXED: the numbers are now REQUIRED. A permit that says "proved"
        # with no ratio used to pass and now fails, which is the case this law exists for.
        self.assertRegex(
            why, r"(?i)\bprov(?:ed|en)\b",
            "the permit never mentions proof at all: %r" % why)
        self.assertRegex(
            why, r"\d+\s+of\s+\d+",
            "the permit says the instruments are watched and does not say HOW MUCH was actually "
            "proved — no count over a denominator appears anywhere in it, so blind=[] with almost "
            "nothing exercised would read exactly like full coverage: %r" % why)

    def test_an_UNREADABLE_gate_does_not_hash_like_an_EMPTY_one(self):
        """★★ v2864 — a cross-family review found the collapse: _read_text returns None for an
        unreadable file and the digest folded that in as "", so EVERY unreadable file hashed
        identically to every empty one. The set of readable gates could change while the
        fingerprint held still, and the lock would call a stale proof current.
        [[unknown-stays-unknown]]"""
        import tempfile, shutil
        d = tempfile.mkdtemp(prefix="fp.")
        a = os.path.join(d, "a.py"); b = os.path.join(d, "b.py")
        io.open(a, "w").write(""); io.open(b, "w").write("")
        held = {}
        try:
            empty = H.gates_fingerprint([("g", a), ("h", b)])
            # ⚠⚠ chmod 0 DOES NOT MAKE A FILE UNREADABLE FOR ROOT, for a uid with
            # CAP_DAC_OVERRIDE, or on a filesystem that ignores mode bits — a cross-family review
            # raised it and it is right: the UNREADABLE branch would never be taken, src would be
            # "" not None, and this law would FAIL on such a machine while proving nothing on any
            # other. Measure whether the premise actually holds before asserting on it.
            # [[zero-needs-a-denominator]]
            # REG-3629 (#107 leftover): on Windows chmod only toggles read-only, so the same
            # premise is staged by holding each file open with no sharing (REG-1452's shape).
            if os.name == "nt":
                import ctypes
                k32 = ctypes.windll.kernel32
                k32.CreateFileW.restype = ctypes.c_void_p
                invalid = ctypes.c_void_p(-1).value
                for p in (a, b):
                    h = k32.CreateFileW(p, 0x80000000, 0, None, 3, 0x80, None)
                    if h in (None, invalid):
                        self.skipTest("could not hold %s open without sharing — UNMEASURED, not passing" % p)
                    held[p] = h
            else:
                os.chmod(a, 0); os.chmod(b, 0)
            if H._read_text(a) is not None:
                self.skipTest("the file stayed readable here (root, or a filesystem that ignores "
                              "mode bits) — the case this law is about cannot be produced on this "
                              "machine. UNMEASURED, not passing.")
            unread = H.gates_fingerprint([("g", a), ("h", b)])
            swapped = H.gates_fingerprint([("g", b), ("h", a)])
        finally:
            if held:
                import ctypes
                for h in held.values():
                    ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(h))
            else:
                os.chmod(a, 0o644); os.chmod(b, 0o644)
            shutil.rmtree(d, ignore_errors=True)
        self.assertNotEqual(empty, unread,
                            "two UNREADABLE gate files hash the same as two EMPTY ones — the "
                            "fingerprint cannot tell 'I could not read it' from 'there was nothing "
                            "in it'")
        self.assertNotEqual(unread, swapped,
                            "two DIFFERENT unreadable files hash identically — the path is not in "
                            "the sentinel, so which instrument went dark is invisible")

    def test_the_fingerprint_covers_the_PROVER_too(self):
        """★★ Same review: the digest covered gate FILES only, so a change to gate_files(), to how
        the sabotage is injected, or to any decision heart2 makes about RED left it identical — and
        the lock would still call that proof current. A proof is only as true as the thing that
        produced it. [[the-unjoined-end]]

        ⚠⚠ THIS ASSERTED THE STRING "heart2.py" APPEARED IN THE FUNCTION SOURCE, and the same
        reviewer called it: that passes even if the fold is deleted, commented out, or put behind a
        flag nobody sets. The FIFTH time this session I wrote a law that checks a name instead of an
        act. It now changes what the prover READS and requires the digest to move.
        [[sabotage-is-usually-the-wrong-one]]"""
        import tempfile, shutil
        d = tempfile.mkdtemp(prefix="pv.")
        g = os.path.join(d, "g.py")
        io.open(g, "w", encoding="utf-8").write("# a gate\n")
        gates = [("g", g)]
        real = H._read_text
        try:
            before = H.gates_fingerprint(gates)
            # make ONLY the prover's own source read differently; the gate list is untouched
            def _fake(path):
                if os.path.basename(path) == "heart2.py":
                    return (real(path) or "") + "\n# the prover changed\n"
                return real(path)
            H._read_text = _fake
            after = H.gates_fingerprint(gates)
        finally:
            H._read_text = real
            shutil.rmtree(d, ignore_errors=True)
        self.assertNotEqual(
            before, after,
            "changing heart2.py's OWN source left the fingerprint identical (%s), so a change to "
            "the prover — how gates are found, how the tamper is applied, what counts as RED — "
            "does not invalidate the census and a stale proof reads as current" % before[:12])

if __name__ == "__main__":
    unittest.main(verbosity=2)
