# -*- coding: utf-8 -*-
"""v3316 — A LOOK IS RECORDED AGAINST THE COMMIT IT ACTUALLY READ.

`payload_for(sha)` resolves a commit, builds the diff from it, hands it to the eye — and the sha
was then THROWN AWAY. Measured 2026-09-18 across all 824 rows written before this: there is no
sha key at all. So the ledger could answer *"was this VERSION looked at"* and could not answer
*"was this COMMIT looked at"* — and the second question is the one that matters, because this repo
batches 3-4 versions per commit on purpose to pay the gate once.

MEASURED, and it is why this is not cosmetic: `0bf8cb6d` is titled **"v3304-v3307"** and ships
FOUR versions. Asking the eye once per version sends the SAME 10,016-byte payload four times —
four paid looks at one set of bytes, filed as four independent reviews. That is n inflated by
REPETITION, which is fake confluence, and it is the error this field exists to prevent. One look,
one sha, credited to every version that commit shipped.

⚠ AND THE HYPHEN RANGE IS INVISIBLE TO THE BACKLOG TOOL. `_VER_LEADING_RUN` accepts `+`, `,` and
`&` between versions but NOT `-`, so "v3304-v3307" registers as v3304 alone and v3305/v3306/v3307
are invisible to `versions_in_history()`. That is the v2862 scar — which added the `+` form for
exactly this reason — repeating with a new separator. Measured over 200 subjects on origin/main:
1 hyphen range, hiding 3 versions.

⚠ `looked_at_commit` RETURNS None, NEVER False, WHEN NO ROW CARRIES A SHA. Every row written
before v3316 is unstamped; answering False for them would make the entire 824-row history read as
"never looked at" and demand it all be bought again. UNKNOWN is the honest answer and it is
pinned below. [[unknown-stays-unknown]] [[heart-first]] §6 — persist what you KNEW.
"""
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Its docstrings and failure messages carry non-ASCII, and a unittest failure PRINTS them. On a
# cp1255 console that crash happens while REPORTING, so a clean tree exits non-zero for a reason
# that has nothing to do with the law. Caught by test_control's encoding-safety gate.
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import second_eye_ledger as L       # noqa: E402
import second_eye_run as R          # noqa: E402


class TestALookRecordsTheCommitItRead(unittest.TestCase):

    def test_a_reached_look_passes_the_commit_into_the_row(self):
        """The empty-seat path passed sha. The path that prints LOOKED did not, so the v3805 row
        stored sha null. A reached look has to name the commit it read."""
        with open(R.__file__, encoding="utf-8") as fh:
            src = fh.read()
        needle = "answer_model=_model_from_transport(), sha=sha"
        self.assertEqual(src.count(needle), 1)

    def test_a_reached_look_driven_through_run_one_writes_its_sha(self):
        """v3776-v3785 (2026-10-22): six reached grok-cli looks landed in the shared ledger with sha null, because the
        ask door called record_answer without sha= (fixed 2a03d258). The source-count case above pins the spelling;
        this one DRIVES the door: a version whose commit resolves must write a row whose sha is that commit."""
        from unittest import mock
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        ship = "1234abcd5678ef90"
        prompt = "Code review.\n```python\nx = 1\n```\n"
        try:
            with mock.patch.object(L, "LEDGER_PATH", path), \
                    mock.patch.object(R, "commit_for", lambda v: (ship, "")), \
                    mock.patch.object(R, "REVIEW_BASE", None), \
                    mock.patch.object(R, "BUMP_ONLY", True), \
                    mock.patch.object(R, "payload_for", lambda sha: (prompt, "", [], None, None)), \
                    mock.patch.object(R, "uncovered_commits", lambda sha: []), \
                    mock.patch.object(R, "_model_from_transport", lambda: "grok-cli"), \
                    mock.patch.object(R, "ask", lambda prompt, sha=None: (
                        '{"verdict":"clean","findings":[],"unseen":""} no concrete defect found in this change',
                        True, "", {"verdict": "clean", "findings": [], "unseen": ""})):
                self.assertTrue(R.run_one("v9106"), "the driven look was not recorded at all")
            rows = L._rows(path)
            self.assertEqual(len(rows), 1, "the driven look wrote %d rows" % len(rows))
            self.assertEqual(rows[0].get("sha"), ship,
                             "a reached look at a version whose commit resolved wrote sha=%r - the v3776-v3785 rows "
                             "again: their absent files can never be classified, so every one reads BLIND"
                             % (rows[0].get("sha"),))
        finally:
            os.unlink(path)

    def test_a_row_carries_the_commit_the_eye_actually_read(self):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        try:
            row = L.record(version="v9101", model="grok-4-1-fast-reasoning", verdict="clean",
                           findings=[], answer_head="No defects found.", path=path,
                           sha="0bf8cb6dcafe")
            self.assertEqual(
                row.get("sha"), "0bf8cb6dcafe",
                "the row records sha=%r. Without the commit, one look at a four-version commit "
                "cannot be told from four looks, and the ledger cannot answer the question the "
                "gate needs to ask." % (row.get("sha"),))
        finally:
            os.unlink(path)

    def test_one_look_at_one_commit_answers_for_every_version_it_shipped(self):
        """THE POINT. v3304-v3307 is ONE commit; paying for it four times is fake confluence."""
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        try:
            L.record(version="v3304", model="grok-4-1-fast-reasoning", verdict="clean",
                     findings=[], answer_head="No defects found.", path=path, sha="0bf8cb6d")
            self.assertIs(
                L.looked_at_commit("0bf8cb6d", path), True,
                "the commit was looked at and looked_at_commit says otherwise.")
            # the abbreviated/full forms must not be two different commits
            self.assertIs(
                L.looked_at_commit("0bf8cb6dcafebabe", path), True,
                "a longer form of the SAME sha read as a different commit, so the join would "
                "break on whichever length the caller happens to hold.")
            self.assertIs(
                L.looked_at_commit("deadbeef", path), False,
                "a commit nobody looked at read as looked-at.")
        finally:
            os.unlink(path)

    def test_a_ledger_with_no_sha_anywhere_is_UNKNOWN_and_never_a_denial(self):
        """⚠ 824 rows predate this field. False here would demand the whole history be re-bought."""
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        try:
            L.record(version="v3304", model="m", verdict="clean", findings=[],
                     answer_head="No defects found.", path=path)   # no sha, as every old row
            self.assertIsNone(
                L.looked_at_commit("0bf8cb6d", path),
                "a ledger whose rows carry no sha answered %r about a commit. Nobody recorded "
                "which commit those looks read, so the answer is UNKNOWN — answering False would "
                "declare 824 real looks to have never happened."
                % (L.looked_at_commit("0bf8cb6d", path),))
            self.assertIsNone(
                L.looked_at_commit("", path),
                "an empty sha must be UNKNOWN, not a measured False.")
        finally:
            os.unlink(path)

    def test_an_unbound_version_resolves_to_the_commit_that_SHIPS_it_not_one_that_mentions_it(self):
        """2026-09-26 - with v3511's TASKS.md row still `(this commit)`, commit_for fell back to subjects and took the
        FIRST one naming v3511 anywhere: "ledger: the self-arming rows the v3511 gate set recorded" - the commit after
        the ship - and the eye would have read a 1-character payload. DRIVEN on a fake history, newest first, with no
        bound row: the ledger commit and a merge that mention versions come BEFORE the ship; the ship must win, a range
        still ships its last version, and a version only ever mentioned is UNKNOWN (None), never a guess"""
        log = "\n".join([
            "aaaa1111 ledger: the self-arming rows the v3511 gate set recorded (8)",
            "bbbb2222 merge: #174 v-B3 onto v3508",
            "cccc3333 v3511: the frozen-screen watch never reads an iCloud placeholder",
            "dddd4444 v3304-v3307 — four versions in one ship",
            "eeee5555 fix: two v3494 contract holes the second eye found",
        ])
        real_sh, real_bound = R._sh, R._bound_commit
        R._sh = lambda args, timeout=60: (log, "") if args[:2] == ["git", "log"] else real_sh(args, timeout)
        R._bound_commit = lambda version: None
        try:
            got = dict((v, R.commit_for(v)[0]) for v in ("v3511", "v3307", "v3508", "v3494"))
        finally:
            R._sh, R._bound_commit = real_sh, real_bound
        self.assertEqual(got["v3511"], "cccc3333", "v3511 resolved to %s, not the commit that shipped it" % got["v3511"])
        self.assertEqual(got["v3307"], "dddd4444", "a range's last version lost its ship")
        self.assertIsNone(got["v3508"], "a version only MENTIONED (a merge onto it) was given a commit: %s" % got["v3508"])
        self.assertIsNone(got["v3494"], "a version only mentioned in a fix subject was given a commit: %s" % got["v3494"])

    def test_a_this_commit_cell_binds_through_the_stamp_and_a_sha_cell_wins(self):
        """The newest row stays `(this commit)` until the next bump. That cell is the stamp commit,
        not a later subject that mentions the version. A cell that already holds a sha is left as written."""
        body = "\n".join([
            "| **v3805** | `(this commit)` | v3805 — note |",
            "| **v3804** | `741365a6` | v3804 — note |",
            "| **v3799** | `d5922061` (in the v3800 commit) | carried |",
        ])
        real = R._sha_from_version_stamp
        R._sha_from_version_stamp = lambda version: "c8855707d" if version == "v3805" else None
        try:
            self.assertEqual(R._sha_named_by_tasks("v3805", body), "c8855707d")
            self.assertEqual(R._sha_named_by_tasks("v3804", body), "741365a6")
            self.assertEqual(R._sha_named_by_tasks("v3799", body), "d5922061")
            self.assertIsNone(R._sha_named_by_tasks("v3803", body))
        finally:
            R._sha_from_version_stamp = real

    def test_a_stamp_mention_or_a_removed_line_is_not_the_ship(self):
        """`git log -S` also hits a commit that drops the line. Only an added VERSION assignment counts."""
        real = R._sh

        def fake(args, timeout=60):
            if args[:3] == ["git", "log", "--format=%H"]:
                return ("aaaa1111\nbbbb2222\n", "")
            if args[:3] == ["git", "show", "--format="] and args[4] == "aaaa1111":
                return ('-VERSION = "v3805"\n+VERSION = "v3806"\n', "")
            if args[:3] == ["git", "show", "--format="] and args[4] == "bbbb2222":
                return (' mention VERSION = "v3805" in a comment\n+VERSION = "v3805"\n', "")
            return real(args, timeout)

        R._sh = fake
        try:
            self.assertEqual(R._sha_from_version_stamp("v3805"), "bbbb2222")
            self.assertIsNone(R._sha_from_version_stamp("nope"))
        finally:
            R._sh = real

    def test_the_shipped_version_resolves_when_its_row_still_says_this_commit(self):
        """v3805's row was still `(this commit)` and its subject did not lead with the version: the commit that ADDED the
        VERSION line is the ship, and its parent does not carry it.
        REG-2788 - this read v3805 out of the REAL history, and CI clones 200 commits (tv-tests.yml): once the tree was 210
        commits past v3805, its commit was not in the clone and the case went red with nothing broken. It is built here in
        a repo of its own - the same three shapes (an earlier stamp, a ship whose subject only says "Stamp", a later commit
        that MENTIONS the version) - with every GIT_* variable scrubbed, so a pre-push hook's GIT_DIR can never point it at
        the real repo."""
        import shutil
        import subprocess
        from unittest import mock
        d = tempfile.mkdtemp(prefix="eye_stamp_repo_")
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

        def git(*a):
            return subprocess.run(["git"] + list(a), cwd=d, env=env, check=True, capture_output=True, text=True).stdout

        def commit(version, subject, rows):
            os.makedirs(os.path.join(d, "tv"), exist_ok=True)
            with open(os.path.join(d, "tv", "tv_diablo.py"), "w") as fh:
                fh.write('VERSION = "%s"\n' % version)
            with open(os.path.join(d, "TASKS.md"), "w") as fh:
                fh.write("\n".join(rows) + "\n")
            git("add", "-A")
            git("commit", "-q", "-m", subject)
            return git("rev-parse", "HEAD").strip()
        try:
            git("init", "-q")
            first = commit("v9104", "v9104 - an earlier ship", ["| **v9104** | `(this commit)` | v9104 - note |"])
            ship = commit("v9105", "Stamp the auto intake move",
                          ["| **v9105** | `(this commit)` | v9105 - note |", "| **v9104** | `%s` | v9104 - note |" % first[:8]])
            with open(os.path.join(d, "NOTE.md"), "w") as fh:
                fh.write("after\n")
            git("add", "-A")
            git("commit", "-q", "-m", "ledger: the v9105 rows")
            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(R, "REPO", d):
                sha, why = R.commit_for("v9105")
                self.assertEqual(sha, ship, "the ship of a `(this commit)` row with a stamp-only subject was not found: %r" % why)
                parent, pwhy = R._sh(["git", "rev-parse", "%s^" % sha], timeout=30)
                here, _ = R._sh(["git", "grep", "-h", 'VERSION = "', sha, "--", "tv/tv_diablo.py"], timeout=30)
                before, _ = R._sh(["git", "grep", "-h", 'VERSION = "', parent.strip(), "--", "tv/tv_diablo.py"], timeout=30)
                self.assertIn('VERSION = "v9105"', here)
                self.assertNotIn('VERSION = "v9105"', before)
                self.assertEqual(R.commit_for("v9104")[0][:8], first[:8], "a sha cell no longer binds its version")
        finally:
            shutil.rmtree(d, True)

    def test_a_hyphen_range_in_a_commit_subject_is_a_range(self):
        """v3304-v3307 ships FOUR versions; the parser saw one. [[v2862]] with a new separator."""
        got = R.versions_in_run("v3304-v3307 — attribution, the overtaken open, and red-on-purpose")
        self.assertEqual(
            got, ["v3304", "v3305", "v3306", "v3307"],
            "a hyphen range parsed as %r. v2862 added the `+` form because a subject reading "
            "'v2859+v2860' made v2860 INVISIBLE to the queue; the hyphen form does the same thing "
            "to three versions at once, and v3305/v3306 shipped unlooked-at because of it."
            % (got,))

        # the SEPARATOR must not eat the title. "v3312 — the river" is one version and an em-dash.
        self.assertEqual(
            R.versions_in_run("v3312 — the river now prints its doors"), ["v3312"],
            "the title separator was read as a range, so a single-version ship would claim "
            "versions that do not exist.")
        # and a version mentioned LATER in the subject still must not count (v2854's protection)
        self.assertEqual(
            R.versions_in_run("fix: the v2804 row narrated the catcher"), [],
            "a version named mid-subject was registered as a ship. That is the protection the "
            "leading-run anchor exists for and it must survive this widening.")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "v3776-v3785 - the reached-look door drops sha= again, so a driven look writes sha null",
     "file": "second_eye_run.py",
     "find": "answer_model=_model_from_transport(), sha=sha,",
     "replace": "answer_model=_model_from_transport(),",
     "matches": 1},
    {"why": "REG-2788 - a `(this commit)` row no longer binds through its stamp, so a stamp-only ship is never found",
     "file": "second_eye_run.py",
     "find": "        return _sha_from_version_stamp(version)\n",
     "replace": "        return None\n",
     "matches": 1},
    {
        "why": "2026-09-26 - commit_for takes any subject that MENTIONS the version again: v3511 -> the ledger commit after it",
        "file": "second_eye_run.py",
        "find": "        if version in versions_in_run(subject):\n",
        "replace": "        if re.search(r\"\\b%s\\b\" % re.escape(version), subject):\n",
        "matches": 1,
    },
    {
        "why": "dropping the sha makes one look at a four-version commit unprovable",
        "file": "tv/second_eye_ledger.py",
        "find": '        "sha": (str(sha).strip() or None) if sha else None,',
        "replace": '        "sha": None,',
        "matches": 1,
    },
    {
        "why": "answering False for an unstamped ledger declares 824 real looks never happened",
        "file": "tv/second_eye_ledger.py",
        "find": "    return False if any_stamped else None",
        "replace": "    return False",
        "matches": 1,
    },
]
