# -*- coding: utf-8 -*-
"""v3341 (#97) — A PAYLOAD NAMES THE FILES IT LEFT OUT, NOT JUST HOW MANY CHARACTERS IT CUT.

`payload_for(sha)` declared its truncation as a CHARACTER COUNT — "truncated to 8142 of 16736 diff
chars at a line boundary". True, and unusable. A char count cannot tell the eye WHICH FILES are
missing, so the eye answers "the diff is correct as shown" in perfect good faith about a payload
that contains none of the change under review.

MEASURED 2026-09-19 by rebuilding this function for every version v3300-v3340 and diffing what it
would send against what the commit actually changed (version stamps excluded — they carry no logic):

    versions examined with code changes                36
    versions where a code file NEVER reached the eye   22   (61%)

AND IN SEVERAL, THE DROPPED FILE IS THE VERSION'S ENTIRE SUBJECT:

    v3330  dropped tv/tree_busy.py          the module that version exists to create
    v3315  dropped tv/second_eye_run.py     the file that version exists to change
    v3333  dropped tv/control_ui.html AND tv/test_a_session_card_always_has_a_clock.py
    v3339  dropped its own law

⚠ THE ROSTER MUST COME FROM GIT, NEVER FROM WHAT WAS FETCHED. payload_for asks for *.py first and
appends *.html only if the budget is not already spent, so when the python diff alone exceeds the
cap the html show is NEVER RUN. A dropped .html is therefore not missing from any buffer that could
be compared — it is missing from the QUESTION. Deriving the absent set from the fetched text would
report a confident 0 for exactly the v3333 case that prompted this law. That is why
`absent_from()` shells to `git show --name-only` instead of parsing what it already has.

THREE STATES, AND COLLAPSING ANY TWO IS THE DEFECT:
    a LIST  -> these changed files never reached the eye at all
    []      -> MEASURED AND NONE — every changed code file is in the payload
    None    -> the roster could not be read: UNKNOWN, and NEVER "nothing was missed"

⚠ THIS DOES NOT WIDEN THE PAYLOAD, AND DELIBERATELY SO. v3299 ruled that closing the coverage gap
means a bigger payload, which costs money and is HIS call. That law pinned instead that the runner
STATES ITS OWN REACH. This is the same move one level down: the payload now states which files it
could not carry. [[unknown-stays-unknown]] [[the-unjoined-end]] [[zero-needs-a-denominator]]
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import second_eye_run as R  # noqa: E402


#: the code files the fixture's HEAD commit changes — the roster every case below is judged against
_FIXTURE_CHANGED = ("tv/alpha.py", "tv/beta.sh", "tv/ui.html")


def _fixture_repo():
    """A throwaway repo whose HEAD changes exactly _FIXTURE_CHANGED plus one doc. -> path | None

    ⚠⚠ #123 — THIS LAW USED TO TAKE ITS FIXTURE FROM WHATEVER THE REAL HEAD CHANGED. On CI run
    35939383947 HEAD was a docs-only `fix:` commit touching 0 code files, so "HEAD changed code"
    was false, the premise failed, and the gate went red while the code under test was fine. A
    law whose verdict depends on what the last commit happened to be is a law about the commit
    log. It builds its own history now, so the roster is known before anything is asked.
    [[feedback-blind-fixture-green-gate]] [[a-gate-can-perturb-what-it-measures]]
    """
    import shutil
    import subprocess
    import tempfile
    root = tempfile.mkdtemp(prefix="payload_law.")
    git = ["git", "-c", "user.name=law", "-c", "user.email=law@example.invalid",
           "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main",
           "-c", "core.hooksPath=/dev/null"]      # no machine's hooks run inside the fixture

    def _w(rel, text):
        p = os.path.join(root, rel)
        if not os.path.isdir(os.path.dirname(p)):
            os.makedirs(os.path.dirname(p))
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(text)

    try:
        subprocess.check_call(git + ["init", "-q", root], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        subprocess.check_call(git + ["-C", root, "config", "core.autocrlf", "false"])  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        for rel in _FIXTURE_CHANGED + ("README.md",):
            _w(rel, "one = 1\n")
        subprocess.check_call(git + ["-C", root, "add", "-A"])
        subprocess.check_call(git + ["-C", root, "commit", "-q", "-m", "base"])
        for rel in _FIXTURE_CHANGED + ("README.md",):
            _w(rel, "one = 1\ntwo = 2\n")
        subprocess.check_call(git + ["-C", root, "add", "-A"])
        subprocess.check_call(git + ["-C", root, "commit", "-q", "-m", "the change under review"])
    except (OSError, subprocess.CalledProcessError):
        shutil.rmtree(root, ignore_errors=True)
        return None
    return root


def _merge_repo():
    """A scratch history whose HEAD is a CLEAN MERGE bringing two files onto main. -> path | None"""
    import shutil
    import subprocess
    import tempfile
    root = tempfile.mkdtemp(prefix="payload_merge.")
    git = ["git", "-c", "user.name=law", "-c", "user.email=law@example.invalid",
           "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main", "-c", "core.hooksPath=/dev/null"]

    def _w(rel, text):
        with io.open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
    try:
        subprocess.check_call(git + ["init", "-q", root], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call(git + ["-C", root, "config", "core.autocrlf", "false"])  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        _w("a.py", "one = 1\n")
        subprocess.check_call(git + ["-C", root, "add", "-A"])
        subprocess.check_call(git + ["-C", root, "commit", "-q", "-m", "base"])
        subprocess.check_call(git + ["-C", root, "checkout", "-q", "-b", "side"])
        _w("b.py", "two = 2\n")
        _w("c.html", "<p>three</p>\n")
        subprocess.check_call(git + ["-C", root, "add", "-A"])
        subprocess.check_call(git + ["-C", root, "commit", "-q", "-m", "side work"])
        subprocess.check_call(git + ["-C", root, "checkout", "-q", "main"])
        _w("a.py", "one = 1\nfour = 4\n")
        subprocess.check_call(git + ["-C", root, "commit", "-q", "-am", "main moves on"])
        subprocess.check_call(git + ["-C", root, "merge", "-q", "--no-ff", "--no-edit", "side"])
    except (OSError, subprocess.CalledProcessError):
        shutil.rmtree(root, ignore_errors=True)
        return None
    return root


class TestAMergeIsLookedAtByWhatItBrought(unittest.TestCase):
    """2026-09-28 - two #231 rows on merge commits (e81dde8f, 44f6b389) read "cannot-tell, chars 0, git show combined
    diff is empty": a clean merge's COMBINED diff is empty, so the eye was handed nothing while the merge carried
    bible.html and eight more files onto main. Driven on a scratch history whose HEAD is a clean merge."""

    @classmethod
    def setUpClass(cls):
        cls.repo = _merge_repo()

    @classmethod
    def tearDownClass(cls):
        import shutil
        if cls.repo:
            shutil.rmtree(cls.repo, ignore_errors=True)

    def setUp(self):
        if not self.repo:
            self.skipTest("git could not build the merge fixture here - UNMEASURED, not clean")
        _real, _base = R.REPO, R.REVIEW_BASE
        R.REPO, R.REVIEW_BASE = self.repo, None
        self.addCleanup(setattr, R, "REPO", _real)
        self.addCleanup(setattr, R, "REVIEW_BASE", _base)

    def test_the_premise_git_show_of_a_clean_merge_is_empty(self):
        out, why = R._sh(["git", "show", "--format=", "--name-only", "HEAD"])
        self.assertIsNotNone(out, why)
        self.assertEqual(out.split(), [], "PREMISE: git show printed files for this merge, so the fixture tests nothing")

    def test_a_merge_is_looked_at_by_the_files_it_brought(self):
        out, why = R._sh(R._changes("HEAD", "--name-only"))
        self.assertIsNotNone(out, why)
        self.assertEqual(sorted(out.split()), ["b.py", "c.html"],
                         "a clean merge's look named %r - the eye would be handed nothing again" % out.split())

    def test_an_ordinary_commit_is_still_its_own_diff(self):
        out, _ = R._sh(R._changes("HEAD^1", "--name-only"))
        self.assertEqual(out.split(), ["a.py"], "a non-merge commit's look changed shape")


class TestAPayloadNamesWhatItLeftOut(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo = _fixture_repo()

    @classmethod
    def tearDownClass(cls):
        import shutil
        if cls.repo:
            shutil.rmtree(cls.repo, ignore_errors=True)

    def setUp(self):
        if not self.repo:
            self.skipTest("git could not build the fixture history here — the changed-file "
                          "roster cannot be asked for, which is UNMEASURED, not clean")
        _real = R.REPO
        R.REPO = self.repo
        self.addCleanup(setattr, R, "REPO", _real)

    def test_the_fixture_head_changes_the_code_it_claims(self):
        """⚠ THE PREMISE, measured — or every case below is judged against a roster nobody read."""
        names, why = R._sh(["git", "show", "--format=", "--name-only", "HEAD"])
        self.assertIsNotNone(names, "the fixture's HEAD could not be read (%s)" % why)
        self.assertEqual(sorted(names.split()), sorted(_FIXTURE_CHANGED + ("README.md",)),
                         "the fixture's HEAD does not change what this law assumes it does")

    # ── the helper ────────────────────────────────────────────────────────────────────────────
    def test_a_file_that_never_reached_the_payload_is_named(self):
        """BEHAVIOURAL. An empty body means nothing arrived, so every changed file is absent."""
        absent, why = R.absent_from("HEAD", "")
        self.assertIsNotNone(
            absent, "absent_from returned UNKNOWN for HEAD in a real checkout (%s); the roster IS "
                    "readable here, so the caller is told UNKNOWN when the answer was available."
                    % (why or "no reason given"))
        # the WHOLE roster, not "at least one" — and the doc HEAD also changed is not a code file
        self.assertEqual(
            sorted(absent), sorted(_FIXTURE_CHANGED),
            "HEAD changed %d code file(s) and an EMPTY payload reported %r absent. A payload "
            "containing nothing cannot have carried anything, and README.md is not code."
            % (len(_FIXTURE_CHANGED), absent))

    def test_a_complete_payload_reports_MEASURED_AND_NONE(self):
        """⚠ THE BASELINE. A law that only ever sees files named proves nothing about the [] case —
        it would pass over a helper that returns every file every time. [[regression-guard]] §5"""
        names, _ = R._sh(["git", "show", "--format=", "--name-only", "HEAD",
                          "--", "*.py", "*.mjs", "*.sh", "*.html"])
        self.assertIsNotNone(names, "could not read HEAD's changed files; refusing to judge")
        body = "\n".join("diff --git a/%s b/%s" % (f, f) for f in names.split())
        absent, _why = R.absent_from("HEAD", body)
        self.assertEqual(
            absent, [],
            "a payload carrying every changed file still reported %r absent. A warning that fires "
            "when nothing is wrong is an off switch — it teaches the reader to skip the line that "
            "matters. [[strictness-that-closes-the-lane]]" % (absent,))

    def test_an_unreadable_roster_is_UNKNOWN_and_never_an_empty_list(self):
        """⚠⚠ THE ONE THAT MATTERS. [] is read by the caller as MEASURED-AND-NONE, so a failed git
        call would print nothing and the operator would conclude the payload was complete."""
        absent, why = R.absent_from("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef", "")
        self.assertIsNone(
            absent,
            "an unresolvable sha returned %r instead of None. An empty list means 'every changed "
            "file reached the eye' — that would be a confident zero manufactured from an error, "
            "which is the exact defect this whole law exists to remove." % (absent,))
        self.assertTrue(
            (why or "").strip(),
            "UNKNOWN was returned with no reason, so nothing can say WHY the roster is unreadable.")

    def test_the_roster_comes_from_git_not_from_the_fetched_text(self):
        """⚠ LOAD-BEARING. Deriving the absent set from the payload text cannot see a file the
        payload never asked for — and *.html is exactly that file whenever the cap is already
        spent. This is the difference between catching v3333 and reporting 0 for it."""
        src = _code(os.path.join(HERE, "second_eye_run.py"))
        i = src.find("def absent_from(")
        self.assertGreater(i, -1, "absent_from() is gone; the roster has no single definition")
        j = src.find("\ndef ", i + 1)
        self.assertGreater(j, i, "could not bound absent_from — refusing to judge a slice whose "
                                 "far end is a guess. [[source-reading-guard]]")
        fn = src[i:j]
        self.assertIn(
            "--name-only", fn,
            "absent_from no longer asks git for the changed-file roster. Any roster derived from "
            "the fetched diff is blind to a file that was never fetched, which is the majority of "
            "this defect's population.")
        for pat in ('"*.py"', '"*.html"'):
            self.assertIn(
                pat, fn,
                "absent_from no longer asks git about %s, so a dropped %s file cannot be named."
                % (pat, pat))

    # ── the join: a correct helper nobody reads fixes nothing ─────────────────────────────────
    def test_the_payload_prints_the_names_it_was_given(self):
        """[[the-unjoined-end]] — the helper being right is worthless if payload_for drops it."""
        real = R.absent_from
        R.absent_from = lambda sha, body: (["tv/PLANTED_ABSENT_FILE.py"], "")
        try:
            prompt, dropped, _absent, _reach, _strip = R.payload_for("HEAD")
        finally:
            R.absent_from = real
        self.assertIsNotNone(prompt, "payload_for returned nothing for HEAD")
        self.assertIn(
            "tv/PLANTED_ABSENT_FILE.py", prompt,
            "the payload did not NAME the absent file in the prompt, so the eye is told a count and "
            "left to assume the rest of the commit was unchanged.")
        self.assertIn(
            "tv/PLANTED_ABSENT_FILE.py", dropped or "",
            "the absent file is missing from the `dropped` note, so the LEDGER ROW will not carry "
            "it either — and a later reader sees a clean verdict with no way to know its reach "
            "without rebuilding the payload by hand. That is how this went unnoticed for 22 ships.")

    def test_an_unknown_roster_reaches_the_prompt_as_UNKNOWN(self):
        """None and [] must not print the same thing, or a failed roster reads as full coverage."""
        real = R.absent_from
        R.absent_from = lambda sha, body: (None, "planted: the roster could not be read")
        try:
            prompt, dropped, _absent, _reach, _strip = R.payload_for("HEAD")
        finally:
            R.absent_from = real
        self.assertIn(
            "UNKNOWN", prompt,
            "an unreadable roster did not reach the prompt as UNKNOWN, so the eye cannot tell a "
            "complete payload from one whose coverage nobody could establish.")
        self.assertIn(
            "UNKNOWN", dropped or "",
            "the row will not record that the payload's reach was UNKNOWN.")

    def test_the_caller_branches_on_None_rather_than_collapsing_it(self):
        """A caller writing `if absent:` alone folds UNKNOWN into MEASURED-AND-NONE silently."""
        src = _code(os.path.join(HERE, "second_eye_run.py"))
        i = src.find("def payload_for(")
        self.assertGreater(i, -1, "payload_for is gone")
        j = src.find("\ndef ", i + 1)
        blk = src[i:j] if j > i else src[i:]
        self.assertIn(
            "absent is None", blk,
            "payload_for does not branch on `absent is None`. Comments are stripped before this "
            "check, because the prose above it explains exactly this distinction. [[REG-1070]]")


    # ── v3375: the two STRIPS are a reach reduction, and reach must be declared ───────────────
    #
    # v3360 built the ship-note strip. v3341/v3349 built "the payload names what it left out".
    # Neither knew about the other for 15 versions, so the eye was handed a diff with the
    # author's own account of the change removed and was never told. [[the-unjoined-end]]
    #
    # MEASURED on v3374's own look: ship-note strip 7,885 chars (22% of the raw diff), comment
    # strip 2,049. The cross-family answer came back reporting that "the test file claims
    # panel-sourced names auto-bank; the banking step is not present" — a claim-versus-delivery
    # finding invented out of a docstring, because the author's real note said the OPPOSITE and
    # had been replaced by a stub. Over 39 version commits: comments 39/39, notes 22/39.

    _CLEAN = (
        "diff --git a/tv/t.py b/tv/t.py\nindex 1..2 100644\n--- a/tv/t.py\n+++ b/tv/t.py\n"
        "@@ -1,2 +1,3 @@\n def f():\n+    x = 1\n     return 1\n")
    _NOTE = (
        "diff --git a/tv/run_gates.py b/tv/run_gates.py\nindex 1..2 100644\n"
        "--- a/tv/run_gates.py\n+++ b/tv/run_gates.py\n@@ -1,3 +1,6 @@\n GATES = [\n"
        '+    Gate("planted-law", ["python3", "-m", "unittest", "x"], 60,\n'
        '+         why="PLANTED SHIP NOTE, long enough that the strip has real work to do."),\n ]\n')
    _CMT = (
        "diff --git a/tv/t.py b/tv/t.py\nindex 1..2 100644\n--- a/tv/t.py\n+++ b/tv/t.py\n"
        "@@ -1,2 +1,5 @@\n def f():\n"
        "+    # PLANTED COMMENT ONE, long enough to matter to a character count.\n"
        "+    # PLANTED COMMENT TWO, long enough to matter to a character count.\n"
        "     return 1\n")

    def _header_for(self, diff):
        """Build a payload from a planted diff and hand back only the prose above the fence.

        ⚠ The fixtures are VALIDATED, not assumed: `test_the_fixtures_actually_exercise_each_strip`
        below asserts each one drives the strip it is named for and the CLEAN one drives neither.
        A case built on a fixture that does not reach the subject measures the fixture.
        """
        real_sh, real_absent = R._sh, R.absent_from
        calls = {"n": 0}

        def _fake_sh(argv, timeout=None):
            # answer by WHAT is asked, not by call order: 2026-09-28 a merge check (git rev-list) now runs
            # before the diff call, and an order-keyed stub handed it the diff and the diff call nothing
            calls["n"] += 1
            if any(str(a).startswith("--unified") for a in argv) and not calls.get("served"):
                calls["served"] = True
                return diff, ""
            return "", ""

        R._sh = _fake_sh
        R.absent_from = lambda sha, body: ([], "")
        try:
            out = R.payload_for("PLANTED")
        finally:
            R._sh, R.absent_from = real_sh, real_absent
        self.assertIsNotNone(out and out[0], "payload_for returned nothing for the planted diff")
        return out[0].split("```diff")[0]

    def test_the_fixtures_actually_exercise_each_strip(self):
        """Prove the planted diffs reach the subject BEFORE any case is believed. [[regression-guard]]"""
        for label, diff, want_c, want_n in (
                ("CLEAN", self._CLEAN, False, False),
                ("NOTE", self._NOTE, False, True),
                ("CMT", self._CMT, True, False)):
            c = R._strip_comments(diff)
            n = R._strip_ship_notes(c)
            dc = len(diff.rstrip("\n")) - len(c.rstrip("\n"))
            dn = len(c.rstrip("\n")) - len(n.rstrip("\n"))
            self.assertEqual(
                bool(dc), want_c,
                "%s fixture: comment strip removed %d chars, expected %s. A fixture that does not "
                "drive the strip it is named for measures nothing." % (label, dc, want_c))
            self.assertEqual(
                bool(dn), want_n,
                "%s fixture: ship-note strip removed %d chars, expected %s." % (label, dn, want_n))

    def test_a_stripped_ship_note_is_declared_with_its_size(self):
        head = self._header_for(self._NOTE)
        self.assertIn(
            "AND THE AUTHOR'S OWN SHIP NOTE IS NOT IN THIS PAYLOAD", head,
            "the ship note was removed from the payload and the eye was not told. It then has no "
            "way to tell 'the author claimed nothing' from 'the author's claim was deleted in "
            "transit', and answers about intent from whatever prose survived the cut.")
        self.assertRegex(
            head, r"SHIP NOTE IS NOT IN THIS PAYLOAD - \d+ characters",
            "the declaration carries no measured size, so it reads as a standing disclaimer rather "
            "than a fact about THIS payload. [[zero-needs-a-denominator]]")

    def test_a_stripped_comment_block_is_declared_with_its_size(self):
        head = self._header_for(self._CMT)
        self.assertIn(
            "COMMENT-ONLY ADDED LINES WERE REMOVED", head,
            "comment-only added lines were removed and the eye was not told, so it can report a "
            "change as undocumented on the strength of a payload the documentation was cut from.")
        self.assertRegex(
            head, r"COMMENT-ONLY ADDED LINES WERE REMOVED \(\d+ characters\)",
            "the comment-strip declaration carries no measured size.")

    def test_a_strip_that_removed_nothing_is_not_declared(self):
        """⚠ THE OTHER DIRECTION, AND MY FIRST CUT FAILED IT.

        `_strip_comments` ends `return "\n".join(keep)`, so splitlines() drops the trailing newline
        and EVERY diff came back one character shorter. A bare truthiness test on the delta would
        have declared a comment strip on every payload ever built — a confident, false statement
        about a payload where nothing was stripped. Declaring a strip that did not happen is the
        same class of lie as hiding one that did. [[unknown-stays-unknown]]
        """
        head = self._header_for(self._CLEAN)
        self.assertNotIn(
            "AND THE AUTHOR'S OWN SHIP NOTE IS NOT IN THIS PAYLOAD", head,
            "a payload with no ship note in it still told the eye one had been stripped.")
        self.assertNotIn(
            "COMMENT-ONLY ADDED LINES WERE REMOVED", head,
            "a payload with no comments in it still told the eye comments had been removed.")

    def test_every_strip_the_builder_applies_is_on_the_roster(self):
        """A third stripper added without a roster entry is an UNDECLARED reach cut."""
        blk = _payload_for_block()
        called = set(re.findall(r"_strip_(\w+)\(", blk))
        self.assertTrue(called, "payload_for calls no _strip_* helper at all — the anchor moved.")
        self.assertEqual(
            len(called), len(R._STRIPS_APPLIED),
            "payload_for applies %d distinct strips (%s) but _STRIPS_APPLIED names %d (%s). Every "
            "transformation applied to the body is a reduction in what the eye can see, and one "
            "that is not on the roster is never counted and never declared."
            % (len(called), ", ".join(sorted(called)),
               len(R._STRIPS_APPLIED), ", ".join(R._STRIPS_APPLIED)))

    def test_every_name_on_the_roster_is_counted_and_declared(self):
        """[[the-unjoined-end]] — counting it and never printing it is the half-built form."""
        blk = _payload_for_block()
        for key in R._STRIPS_APPLIED:
            self.assertIn(
                '_stripped["%s"]' % key, blk,
                "the roster names %r but payload_for never adds to _stripped[%r], so its size is "
                "always 0 and it can never be declared." % (key, key))
            guard = '_stripped.get("%s")' % key
            i = blk.find(guard)
            self.assertGreater(
                i, -1,
                "the roster names %r but no `if _stripped.get(%r):` guards a declaration for it. "
                "Either it is declared unconditionally — a false statement whenever it removed "
                "nothing — or it is not declared at all." % (key, key))
            j = blk.find("\n    if ", i + 1)
            self.assertIn(
                "note +=", blk[i:j] if j > i else blk[i:],
                "the guard for %r adds nothing to the header, so the strip is measured and then "
                "dropped before it reaches the eye." % key)


def _payload_for_block():
    """payload_for's own source, COMMENTS STRIPPED — this law's subject documents its own shapes.

    ⚠ Anchored on the CALL and the SUBSCRIPT, never on the bare name: `_stripped` and
    `_STRIPS_APPLIED` both appear in the prose above the code, so a comment would satisfy a
    name-only assertion and the guard would read green over a deleted declaration.
    [[source-reading-guard]] §4b
    """
    src = _code(os.path.join(HERE, "second_eye_run.py"))
    i = src.find("def payload_for(")
    assert i > -1, "payload_for is gone"
    j = src.find("\ndef ", i + 1)
    return src[i:j] if j > i else src[i:]


def _code(path):
    """Source with comments removed — this law's subject documents the very shapes it bans."""
    with io.open(path, encoding="utf-8") as fh:
        raw = fh.read()
    return "\n".join(re.sub(r"#.*$", "", l) for l in raw.split("\n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "2026-09-28 - a clean merge is looked at through git show's combined diff again: the eye is handed nothing",
        "file": "tv/second_eye_run.py",
        "find": "    _fp = _first_parent_of_merge(sha)\n",
        "replace": "    _fp = None\n",
        "matches": 1,
    },
    {
        "why": "hardcoding an empty absent set puts every dropped file back out of sight",
        "file": "tv/second_eye_run.py",
        "find": "    absent, _nwhy = absent_from(sha, body)",
        "replace": "    absent, _nwhy = [], \"\"",
        "matches": 1,
    },
    {
        "why": "returning [] for an unreadable roster turns a failed git call into full coverage",
        "file": "tv/second_eye_run.py",
        "find": '        return None, (why or "the changed-file roster could not be read")',
        "replace": '        return [], (why or "the changed-file roster could not be read")',
        "matches": 1,
    },
    {
        "why": "dropping *.html from the roster makes control_ui.html invisible again - the v3333 case",
        "file": "tv/second_eye_run.py",
        # re-anchored 2026-09-27: the roster's git call goes through _changes() now (--base), same pathspec
        # v3897 re-anchored: REG-3699 wraps the pathspec in _pathspec([...]) (a follow-up look's named files)
        "find": '                     _pathspec(["--", "*.py", "*.js", "*.mjs", "*.sh", "*.html",',
        "replace": '                     _pathspec(["--", "*.py", "*.js", "*.mjs", "*.sh",',
        "matches": 1,
    },
    {
        "why": "not naming the files in the prompt leaves the eye with a char count it cannot use",
        "file": "tv/second_eye_run.py",
        "find": '                 % ", ".join(absent))',
        "replace": '                 % len(absent))',
        "matches": 1,
    },
    {
        "why": "the eye is never told the author's ship note was removed - the v3374 case, where it then invented a claim-versus-delivery finding out of a docstring",
        "file": "tv/second_eye_run.py",
        "find": '    if _stripped.get("notes"):\n        note += ("\\nAND THE AUTHOR\'S OWN SHIP NOTE IS NOT IN THIS PAYLOAD - %d characters of it "\n                 "were replaced with the stub why=\\"<ship note stripped for the eye>\\" before you "\n                 "were sent this. You cannot see what the author CLAIMED this change does, so do "\n                 "not report a claim as undelivered, and do not infer the author\'s intent from "\n                 "whatever prose happens to remain. Judge the code.\\n" % _stripped["notes"])\n',
        "replace": '    if False:\n        pass\n\n',
        "matches": 1,
    },
    {
        "why": 'the eye is never told comment-only lines were removed, so it can report a change as undocumented on a payload the documentation was cut from',
        "file": "tv/second_eye_run.py",
        "find": '    if _stripped.get("comments"):\n        note += ("\\nAND COMMENT-ONLY ADDED LINES WERE REMOVED (%d characters). You are reading the "\n                 "code, not the author\'s account of it. Do not report a change as undocumented or "\n                 "unexplained on the strength of this payload.\\n" % _stripped["comments"])\n',
        "replace": '    if False:\n        pass\n\n',
        "matches": 1,
    },
    {
        "why": 'declaring the ship-note strip UNCONDITIONALLY states it as a fact about payloads where nothing was stripped',
        "file": "tv/second_eye_run.py",
        "find": '    if _stripped.get("notes"):',
        "replace": '    if True:',
        "matches": 1,
    },
    {
        "why": 'counting the raw length delta re-lands the trailing-newline artifact: _strip_comments ends in "\\n".join(keep), so every payload loses 1 char and declares a strip that never happened',
        "file": "tv/second_eye_run.py",
        "find": '        _stripped["comments"] += len(_raw.rstrip("\\n")) - len(_c.rstrip("\\n"))',
        "replace": '        _stripped["comments"] += len(_raw) - len(_c)',
        "matches": 1,
    },
    {
        "why": 'a strip missing from _STRIPS_APPLIED is never counted and never declared - the exact shape the ship-note strip had for 15 versions',
        "file": "tv/second_eye_run.py",
        "find": '_STRIPS_APPLIED = ("comments", "notes")',
        "replace": '_STRIPS_APPLIED = ("comments",)',
        "matches": 1,
    },
    {
        "why": 'dropping the measured size turns the declaration into a standing disclaimer rather than a fact about THIS payload. First cut of this proof came back BLIND at a correct match count of 1: it edited the SECOND line of the string while the %d it claims to remove sits on the FIRST, so it broke something adjacent to the property, never the property',
        "file": "tv/second_eye_run.py",
        "find": ' - %d characters of it "\n                 "were replaced with the stub why=\\"<ship note stripped for the eye>\\" before you "\n                 "were sent this. You cannot see what the author CLAIMED this change does, so do "\n                 "not report a claim as undelivered, and do not infer the author\'s intent from "\n                 "whatever prose happens to remain. Judge the code.\\n" % _stripped["notes"])',
        "replace": ' - some of it "\n                 "was replaced with a stub before you were sent this. Judge the code.\\n")',
        "matches": 1,
    },
]
