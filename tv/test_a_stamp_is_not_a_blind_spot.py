# -*- coding: utf-8 -*-
"""v3354 (#106) — A VERSION STAMP IS NOT A BLIND SPOT.

v3349 gave the ledger a `partial` counter: how many looks never saw part of the change. It was the
right question and it fired on EVERYTHING. MEASURED 2026-09-19 over the 7 rows that carry `absent`:

    rows flagged partial by the shipped counter      7 of 7
    rows that missed anything but a version stamp    2 of 7     <- the honest number
    absent-file entries that were STAMP-ONLY        12 of 16

A warning that fires on every row carries no information, which is the same defect as a gate that
is always green. [[regression-guard]] [[zero-needs-a-denominator]]

=== THE TWO THAT MATTER, AND THEY ARE REAL ===
    v3349  clean     absent: tv/second_eye_run.py (21 lines), tv/test_a_partial_look_is_not_
                     agreement.py (218 lines), tv/test_a_payload_names_what_it_left_out.py (4)
    v3351  findings  absent: tv/test_the_session_gets_a_vote_on_where.py (33 lines)

v3349 was filed `clean` over a payload that never contained its own 218-line subject. That is the
exact shape v3349 itself was written about, and the counter it shipped could not point at it
because it was pointing at everything.

=== ⚠⚠ WHY A FILENAME ALLOW-LIST IS THE WRONG FIX, AND IT WAS MEASURED BEFORE BUILDING ===
Across the last 120 version commits, six files change in >=99% of them:

    100.0% tv/WINDOWS_SHIP.json   100.0% TASKS.md    100.0% tv/tv_diablo.py
    100.0% bible.html             100.0% tv/control_app.py     99.2% BLUEPRINT.md

Excusing those by NAME is obvious and wrong in both directions — bible.html and control_app.py are
the two files most often the real subject of a version. One filename, opposite verdicts:

    bible.html        @ e850b847 (v3345)  SUBSTANTIVE  37 changed lines — the apostrophe fold
    bible.html        @ c08875ad (v3352)  STAMP         2 changed lines, both version tokens
    tv/control_app.py @ d2b3f3cf (v3343)  SUBSTANTIVE   8 changed lines — the rider route
    tv/control_app.py @ c08875ad (v3352)  STAMP         2 changed lines, both version tokens

So the test asks about the CHANGE, never the name. [[the-unjoined-end]] §6.

=== THE FALSE-NEGATIVE DIRECTION WAS HUNTED BEFORE SHIPPING, NOT ASSUMED AWAY ===
A substantive change whose every line happens to carry a version token would be waved through. So
the whole population was swept — 80 version commits, every changed file. Among the file types the
classifier can actually be handed, a stamp-classified change is ALWAYS exactly two lines:

    bible.html  2/2/2 (n=71)   tv/tv_diablo.py  2/2/2 (n=80)   tv/control_app.py  2/2/2 (n=52)

The only large all-version-token diffs are TASKS.md (up to 9 lines) and tv/WINDOWS_SHIP.json (4) —
the ship-note rows, where every line names the version. Neither can ever reach this classifier:
`absent_from` asks git for *.py, *.mjs, *.sh and *.html only, so a .md or .json is outside the
question by construction. That bound is pinned below rather than trusted.

⚠ UNKNOWN IS NEVER AN EXCUSE. The classifier only ever REMOVES a warning, and may do so only where
the change was MEASURED to be a stamp. An unreadable diff stays outside the excuse.
[[unknown-stays-unknown]]

⚠ HIS 867 EXISTING ROWS ARE NOT REWRITTEN. They carry no classification, so the reader takes it
from their own sha — the same measurement from the same source, later. Testimony stands.
[[manual-tally-is-witness]]
"""
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import second_eye_ledger as L  # noqa: E402

#: measured shas — one filename, opposite verdicts. See the docstring.
SHA_STAMP = "c08875ad"        # v3352: bible.html changed by the stamp alone
SHA_SUBSTANTIVE = "e850b847"  # v3345: bible.html carries the apostrophe fold


def _fixture_repo():
    """-> (repo, stamp_sha, substantive_sha): a throwaway git repo holding one stamp-only commit to
    bible.html and one substantive one.

    ⚠⚠ #227 — THE REAL SHAS FELL OFF THE CI CLONE. tv-tests.yml clones fetch-depth 200 (another
    gate's window) and SHA_STAMP is now 216 commits back, so on the runner absent_kind() answered
    'unknown' and two cases went red after passing for weeks — while green on the Mac, which holds
    full history. A fixed depth only moves that cliff. The cases that assert the CLASSIFIER now
    build the history they read; the ones that measure the REAL commits still skip, loudly, where
    those commits are unreachable. [[regression-guard]] §3 [[feedback-fixtures-never-touch-live-data]]"""
    import subprocess
    d = tempfile.mkdtemp(prefix="stamp-repo-")

    def g(*a):
        return subprocess.run(["git", "-C", d, "-c", "commit.gpgsign=false", "-c", "user.email=t@t",
                               "-c", "user.name=t"] + list(a),
                              check=True, capture_output=True, text=True).stdout.strip()
    g("init", "-q")
    page = os.path.join(d, "bible.html")

    def put(txt):
        with io.open(page, "w", encoding="utf-8") as f:
            f.write(txt)
    put("<b>v1000</b>\ncontent one\n")
    g("add", "bible.html")
    g("commit", "-qm", "base")
    put("<b>v1001</b>\ncontent one\n")
    g("commit", "-qam", "stamp only")
    stamp = g("rev-parse", "HEAD")
    put("<b>v1002</b>\ncontent two\n")
    g("commit", "-qam", "substantive")
    return d, stamp, g("rev-parse", "HEAD")


class _InAFixtureRepo(object):
    """Point the classifier at the fixture repo for one test, and forget its memo both ways."""

    def _enter_fixture(self):
        self._repo_was = L._REPO
        self.repo, self.stamp, self.subst = _fixture_repo()
        L._REPO = self.repo
        L._KIND_MEMO.clear()
        self.assertEqual(L.absent_kind(self.subst, "bible.html"), "substantive",
                         "premise: the classifier must tell the substantive commit apart, or a "
                         "constant 'stamp' would pass the case below")

    def _leave_fixture(self):
        L._REPO = self._repo_was
        L._KIND_MEMO.clear()
        import shutil
        shutil.rmtree(self.repo, ignore_errors=True)


def _tmp():
    return os.path.join(tempfile.mkdtemp(), "ledger.jsonl")


class AStampIsNotABlindSpot(unittest.TestCase):

    def test_a_stamp_only_absence_is_not_partial(self):
        """⚠⚠ THE CASE. Before this, every row warned and the warning meant nothing."""
        p = _tmp()
        for _ in range(2):
            L.record(version="v9101", model="m", verdict="clean", answer_head="fine", path=p,
                     absent=["bible.html", "tv/tv_diablo.py"],
                     absent_kinds={"bible.html": "stamp", "tv/tv_diablo.py": "stamp"})
        a = L.agreement("v9101", path=p)
        self.assertEqual(
            a.get("partial"), 0,
            "two looks that missed nothing but the version stamp are reported as BLIND (partial=%s)"
            ". Measured on his ledger: that fires on 7 of 7 rows where the honest count is 2, and a "
            "warning that fires on everything is furniture." % a.get("partial"))
        self.assertNotIn(
            "NEVER SAW", a["say"],
            "the sentence still warns a human about a two-line version stamp: %r" % a["say"])

    def test_a_substantive_absence_is_still_partial(self):
        """⚠ THE BASELINE, or the fix above is just an off switch. [[regression-guard]] §5"""
        p = _tmp()
        for _ in range(2):
            L.record(version="v9102", model="m", verdict="clean", answer_head="fine", path=p,
                     absent=["bible.html", "tv/second_eye_run.py"],
                     absent_kinds={"bible.html": "stamp", "tv/second_eye_run.py": "substantive"})
        a = L.agreement("v9102", path=p)
        self.assertEqual(
            a.get("partial"), 2,
            "a look that never saw a SUBSTANTIVE change is no longer counted as blind. That is "
            "v3349's whole finding turned off rather than sharpened — v3349 itself was filed clean "
            "over a payload missing its own 218-line subject.")
        self.assertIn(
            "tv/second_eye_run.py", a["say"],
            "the warning does not NAME the file nobody saw, so a reader cannot tell whether it "
            "matters: %r. A count nobody can act on is the same as no count." % a["say"])
        self.assertNotIn(
            "bible.html", a["say"],
            "the stamp-only file is named alongside the real one, which puts the noise back into "
            "the sentence this version exists to clean: %r" % a["say"])

    def test_an_unclassifiable_absence_is_not_excused(self):
        """⚠ UNKNOWN is not a stamp. The excuse is granted only where a stamp was MEASURED."""
        p = _tmp()
        L.record(version="v9103", model="m", verdict="clean", answer_head="x", path=p,
                 absent=["tv/mystery.py"], absent_kinds={"tv/mystery.py": "unknown"})
        a = L.agreement("v9103", path=p)
        self.assertEqual(
            a.get("partial"), 1,
            "a file whose change could not be read is being treated as harmless. An unreadable "
            "diff is not evidence that nothing was missed. [[unknown-stays-unknown]]")


class TheRowCarriesTheClassification(unittest.TestCase):

    def test_the_three_states_stay_apart(self):
        p = _tmp()
        L.record(version="v9104", model="m", verdict="clean", answer_head="x", path=p,
                 absent=["bible.html"], absent_kinds={"bible.html": "stamp"})
        L.record(version="v9105", model="m", verdict="clean", answer_head="x", path=p, absent=[])
        L.record(version="v9106", model="m", verdict="clean", answer_head="x", path=p)
        rows = dict((r["version"], r) for r in L._rows(p))
        self.assertEqual(
            rows["v9104"].get("absentKind"), {"bible.html": "stamp"},
            "the classification is not stored, so every read pays a git call per file and a row "
            "cannot answer what kind of change it missed")
        self.assertEqual(
            rows["v9105"].get("absentKind"), {},
            "a look that omitted nothing must record {} — a MEASUREMENT, not an absence")
        self.assertIsNone(
            rows["v9106"].get("absentKind"),
            "a row whose reach was never established must record null, or 'we never checked' "
            "becomes 'we checked and it was fine'")

    def test_record_takes_the_measurement_itself(self):
        """⚠ INSTRUMENTED AT THE DOOR so no caller can forget it. [[heart-first]] §4"""
        fx = _InAFixtureRepo()
        fx.assertEqual = self.assertEqual
        fx._enter_fixture()
        self.addCleanup(fx._leave_fixture)
        p = _tmp()
        L.record(version="v9107", model="m", verdict="clean", answer_head="x", path=p,
                 sha=fx.stamp, absent=["bible.html"])
        row = L._rows(p)[-1]
        self.assertEqual(
            (row.get("absentKind") or {}).get("bible.html"), "stamp",
            "record() did not classify an absent file for a caller that passed none, so the "
            "measurement depends on every caller remembering — which is the rule that just failed")


class ItReadsTheChangeNotTheName(unittest.TestCase):
    """⚠⚠ THE PAIR THAT REFUTES AN ALLOW-LIST. Same file, opposite verdicts, against real git."""

    def test_one_filename_two_verdicts(self):
        stamp = L.absent_kind(SHA_STAMP, "bible.html")
        subst = L.absent_kind(SHA_SUBSTANTIVE, "bible.html")
        if "unknown" in (stamp, subst):
            self.skipTest("neither sha is reachable in this clone (%s / %s)" % (stamp, subst))
        self.assertEqual(
            stamp, "stamp",
            "bible.html at %s changed by two lines, both carrying a version token, and reads %r"
            % (SHA_STAMP, stamp))
        self.assertEqual(
            subst, "substantive",
            "bible.html at %s carries the 37-line apostrophe fold and reads %r. If the classifier "
            "answers by FILENAME it will excuse a genuinely blind look on the day bible.html is "
            "the subject — and it is the subject often." % (SHA_SUBSTANTIVE, subst))

    def test_only_code_files_can_ever_reach_the_classifier(self):
        """⚠ THE STATED BOUND. The false-negative risk — a substantive change whose every line
        carries a version token — is concentrated in TASKS.md and tv/WINDOWS_SHIP.json, whose ship
        notes name the version on every line. They can never be handed here, because the roster
        payload_for builds asks git for code only. Pin that, or the bound is a belief."""
        import second_eye_run as R
        absent, why = R.absent_from(SHA_STAMP, "")
        if absent is None:
            self.skipTest("the roster could not be read here: %s" % why)
        bad = [f for f in absent
               if not f.endswith((".py", ".mjs", ".sh", ".html"))]
        self.assertEqual(
            bad, [],
            "the absent roster now carries %s. A .md or .json ship note is all version tokens by "
            "nature, so the stamp test would read a real 9-line change as a stamp — the one "
            "false-negative this classifier has, arriving through a widened roster." % bad)

    def test_a_missing_sha_is_unknown_never_stamp(self):
        self.assertEqual(L.absent_kind(None, "bible.html"), "unknown")
        self.assertEqual(L.absent_kind(SHA_STAMP, ""), "unknown")

    def test_a_diff_that_cannot_be_READ_is_unknown_never_stamp(self):
        """⚠⚠ THE ARM THE FIRST SABOTAGE FOUND BLIND, and the sabotage was right.

        The two cases above only reach the guard for an EMPTY argument, which returns a literal.
        Nothing drove a sha git cannot resolve, so the fall-through value — the one that decides
        what an unreadable diff means — was never asserted at all: flipping it from "unknown" to
        "stamp" left this file entirely green. That is `regression-guard` §5a cause 2, the test
        being too weak to see the change rather than the guard being blind, and it matters because
        "stamp" is the value that SILENCES the warning. An unreadable diff silently excusing a
        blind look is the exact collapse this version exists to prevent, arriving through the
        error path instead of the happy one.
        """
        self.assertEqual(
            L.absent_kind("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef", "bible.html"), "unknown",
            "a sha git cannot resolve is being classified as a version stamp. That grants the "
            "excuse where nothing was measured, and it does so on the ERROR path, which is the "
            "one nobody watches. [[unknown-stays-unknown]]")

    def test_a_legacy_row_is_classified_from_its_own_sha(self):
        """The 867 rows before this version carry no kinds. They are MEASURED, not assumed."""
        p = _tmp()
        row = L.record(version="v9108", model="m", verdict="clean", answer_head="x", path=p,
                       sha=SHA_STAMP, absent=["bible.html"])
        if (row.get("absentKind") or {}).get("bible.html") == "unknown":
            self.skipTest("this clone cannot reach %s" % SHA_STAMP)
        # strip the stored classification, exactly as a pre-v3354 row has none
        row.pop("absentKind", None)
        self.assertEqual(
            L.blind_to(row), [],
            "a legacy row is not classified from its own sha, so every historical look keeps the "
            "warning whatever it actually missed — the defect, preserved for history")


#: v3856 - a CHECKED-IN sample ledger, not the box's shared one. The shared ledger is whatever this machine's eyes
#: happened to write: on 2026-10-22 six reached looks landed there with sha null (the ask door dropped sha=, fixed
#: 2a03d258), so every absent row it held read UNKNOWN -> BLIND and this case went red with the classifier sound.
#: The sample keeps the shapes that matter: two stamp rows and two substantive rows at the measured shas in the module
#: docstring, one sha-null row with a stored 'unknown' kind and one legacy sha-null row with none (both MUST stay BLIND),
#: and one fully-reached row with an empty absent list (outside the population). [[feedback-fixtures-never-touch-live-data]]
SAMPLE_LEDGER = os.path.join(HERE, "fixtures", "second_eye_sample_ledger.jsonl")
SAMPLE_BLIND = {"v3345", "v3343", "v3785", "v3776"}
SAMPLE_EXCUSED = {"v3352"}


class HisRealLedgerStopsWarningOnEverything(unittest.TestCase):
    """BEHAVIOURAL, against a sample ledger that is checked in, so the verdict is about the classifier, not this box."""

    def test_the_counter_discriminates(self):
        rows = [r for r in L._rows(SAMPLE_LEDGER) if r.get("absent")]
        self.assertEqual(len(rows), 6, "the sample ledger lost rows (%d with an absent list) - its denominator is gone"
                         % len(rows))
        blind = [r for r in rows if L.blind_to(r)]
        self.assertLess(
            len(blind), len(rows),
            "%d of %d rows with an absent list are still reported BLIND. Measured 2026-09-19 the "
            "figure was 7 of 7 and the honest one was 2 — if it is back to firing on everything "
            "the classifier has stopped discriminating and the warning is furniture again."
            % (len(blind), len(rows)))
        self.assertTrue(
            blind,
            "NO row is reported blind any more. v3349's finding was real — v3349's own look never "
            "saw its 218-line subject and was filed clean — so a counter that can no longer reach "
            "it has been turned off rather than sharpened. [[regression-guard]] §5")
        self.assertEqual(
            set(r["version"] for r in blind), SAMPLE_BLIND,
            "the counter split the sample wrong. Substantive rows and BOTH sha-null rows must read BLIND (UNKNOWN is never "
            "a stamp), and only the stamp rows may be excused.")
        self.assertFalse(
            set(r["version"] for r in rows if not L.blind_to(r)) - SAMPLE_EXCUSED,
            "a row that is not a measured stamp was excused")

    def test_the_sample_kinds_are_what_git_measures_where_the_commit_is_here(self):
        """The stored kinds are not invented: where this clone holds the commit, the classifier agrees with them. On a
        shallow clone (CI, fetch-depth 200) the commit is gone and that row is SKIPPED by name, never passed."""
        import subprocess
        checked = 0
        for r in L._rows(SAMPLE_LEDGER):
            sha = r.get("sha")
            if not sha or not r.get("absentKind"):
                continue
            have = subprocess.run(["git", "-C", L._REPO, "cat-file", "-e", "%s^{commit}" % sha],
                                  capture_output=True).returncode == 0
            if not have:
                continue
            for f, k in r["absentKind"].items():
                with self.subTest(sha=sha, path=f):
                    self.assertEqual(L.absent_kind(sha, f), k)
                    checked += 1
        if not checked:
            self.skipTest("none of the sample's commits are in this clone - the stored kinds were NOT re-measured here")


class TheCorroboratorReadsONESnapshot(unittest.TestCase):
    """⚠⚠ THE CROSS-FAMILY EYE FOUND THIS ON THE DAY v3354 SHIPPED, and it reproduces.

    `_inv_a_stored_reach_still_matches_git` had each side call `_rows_with_reach()` for itself.
    The ledger is APPEND-ONLY and `second_eye_run --answer-in` writes to it, so one row landing
    between the two calls makes a perfectly healthy store report DISAGREE. REPRODUCED by handing
    the sides populations of 1 and 2 rows: left 0, right 1, relation "==" false, no defect
    anywhere. The asymmetric case is worse — one side None and the other a number reads as
    UNKNOWN, which is the agreement-about-nothing this invariant exists to refuse.

    ⚠ Sharing the SUBJECT is not self-corroboration. The METHOD must differ — the stored dict on
    one side, git on the other; two sides judging different rows corroborate nothing at all.
    """

    def test_both_sides_judge_the_same_rows(self):
        import corroborate as C
        import second_eye_ledger as SEL
        fx = _InAFixtureRepo()
        fx.assertEqual = self.assertEqual
        fx._enter_fixture()
        self.addCleanup(fx._leave_fixture)
        A = {"version": "vX", "sha": fx.stamp, "absent": ["bible.html"],
             "absentKind": {"bible.html": "stamp"}}
        B = {"version": "vY", "sha": fx.subst, "absent": ["bible.html"],
             "absentKind": {"bible.html": "substantive"}}
        calls = {"n": 0}
        real = SEL._rows

        def growing(path=None):
            calls["n"] += 1
            return [A] if calls["n"] == 1 else [A, B]
        SEL._rows = growing
        try:
            _n, _d, _s, _ln, left, _rn, right, rel = C._inv_a_stored_reach_still_matches_git()
            l, r = left(), right()
        finally:
            SEL._rows = real
        self.assertEqual(
            calls["n"], 1,
            "the ledger was read %d times while building one reading. The store is append-only "
            "and a look can land between the two calls, so the two sides would be judging "
            "different populations." % calls["n"])
        self.assertEqual(
            l, r,
            "a row appended between the two sides made a healthy store report %r vs %r. A "
            "supervisor that cries wolf on its own timing is worse than no supervisor."
            % (l, r))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "v3856 - excusing UNKNOWN as if it were a stamp lets the sample's two sha-null rows (the 2026-10-22 shape) "
               "read as clean looks",
        "file": "tv/second_eye_ledger.py",
        "find": "        if k != \"stamp\":\n            out.append(f)",
        "replace": "        if k not in (\"stamp\", \"unknown\"):\n            out.append(f)",
        "matches": 1,
    },
    {
        "why": "counting every absent file as blind puts the warning back on 7 of 7 rows, where "
               "the measured figure is 2 — a warning that fires on everything is furniture",
        "file": "tv/second_eye_ledger.py",
        "find": "        if k != \"stamp\":\n            out.append(f)",
        "replace": "        out.append(f)",
        "matches": 1,
    },
    {
        "why": "a classifier that answers stamp for everything stops the counter reaching v3349's "
               "real case, where a look was filed clean over its own 218-line subject",
        "file": "tv/second_eye_ledger.py",
        "find": "            out = \"stamp\" if len(stampy) == len(body) else \"substantive\"",
        "replace": "            out = \"stamp\"",
        "matches": 1,
    },
    {
        "why": "treating an unreadable diff as a stamp grants the excuse where nothing was measured",
        "file": "tv/second_eye_ledger.py",
        "find": "    out = \"unknown\"\n    try:\n        p = subprocess.Popen",
        "replace": "    out = \"stamp\"\n    try:\n        p = subprocess.Popen",
        "matches": 1,
    },
    {
        "why": "giving each side of the corroborator its own ledger read lets one appended look "
               "make a healthy store report DISAGREE — reproduced at 0 vs 1 with no defect present",
        "file": "tv/corroborate.py",
        "find": "    def left():\n        rows = _snapshot",
        "replace": "    def left():\n        rows = _rows_with_reach()",
        "matches": 1,
    },
    {
        "why": "dropping the classification from the row makes every read re-derive it by git and "
               "leaves the row unable to say what kind of change it missed",
        "file": "tv/second_eye_ledger.py",
        "find": "        \"absentKind\": _kinds_for(absent, absent_kinds, sha),",
        "replace": "        \"absentKind\": None,",
        "matches": 1,
    },
]
