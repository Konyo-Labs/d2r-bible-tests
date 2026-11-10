#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3388 - THE SECOND EYE ASKS GIT FOR EVERY CODE EXTENSION, NOT MOST OF THEM.

THE EYE FOUND THIS ONE ITSELF, reviewing v3387. Its answer named the gap before I did:

    "Also absent: any Cloudflare worker / functions code that actually performs the
     lastseen/webseen lookup, key matching, throttling, null-handling... All claims about
     matching behaviour, throttling, webAt presence, or UI output are therefore UNVERIFIED."

I did not take it at face value - the run had reported only TWO omitted files, which contradicts
the eye. MEASURED on that payload, and the eye was right:

    webSeenSlug     0        recordWebSeen   0
    _fleetSeen      0        webOnly         0
    functions/_middleware.js  - 0 occurrences, and NOT in the omitted list either

CAUSE: both git pathspecs listed `*.py`, `*.mjs`, `*.sh` (and `*.html` for the roster). `*.js`
was never there. Someone added the module extension and not the plain one. v3387's entire
subject is two Cloudflare function files and the eye saw NEITHER.

⚠⚠ WORSE THAN A DROPPED FILE, AND THIS IS THE PART WORTH KEEPING. A file excluded by the
pathspec is never a CANDIDATE, so v3341's "the payload names the files it left out" and v3354's
"the partial counter NAMES the file nobody saw" both reported 0 - truthfully, about a question
they were never asked. A false NEGATIVE in the instrument built to catch exactly this.
[[the-unjoined-end]] [[zero-needs-a-denominator]]

⚠ THE BLAST RADIUS IS SMALL AND STATED. My first pass said "60 of 60 versions had an unseen .js
change" - implausible agreement, which is the instrument-fault tell. Filtering _archive/ and
re-running: 1 of the last 60, and it is v3387. functions/*.js rarely changes. The honest claim
is the smaller one. [[feedback-suspect-the-instrument]]

⚠ _archive/ IS EXCLUDED ALONGSIDE. 67 tracked .js, the bulk archived build chunks under
_archive/phase_z_20260715/assets/. 0 of the last 60 versions touch that tree, so the exclusion
is a measured no-op today and a guard against one archived rebuild flooding the payload and
starving the real files - the failure v3370 fixed for the allocator.

HOW THIS FILE TESTS IT, and why not by reading the source: it CAPTURES the argv the shipped code
hands to git, then REPLAYS that exact argv against a purpose-built temp repo. So the law
exercises the pathspec that actually ships rather than a retyped copy of it, and it asks GIT
what the pathspec means rather than asking me. [[source-reading-guard]] section 1
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    import console_safe
    console_safe.enable()
except Exception:
    pass

import second_eye_run as R


def _git(cwd, *args):
    return subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True,
                          text=True, timeout=60)


def _capture_argvs():
    """The argv of every `git show` the shipped code issues for one sha. -> list[list[str]]

    ⚠ The real _sh is replaced only for the duration of the call and restored in `finally`;
    a harness that leaks a stub into the rest of the suite is a defect of its own.
    """
    seen = []
    real = R._sh

    def _fake(argv, timeout=None):
        seen.append(list(argv))
        return "", ""                      # empty, so nothing downstream does real work

    R._sh = _fake
    try:
        try:
            R.payload_for("HEAD")
        except Exception:
            pass
        try:
            R.absent_from("HEAD", "")
        except Exception:
            pass
    finally:
        R._sh = real
    return [a for a in seen if len(a) > 1 and a[0] == "git" and a[1] == "show"]


class TheEyeSeesEveryCodeExtension(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.argvs = _capture_argvs()
        cls.tmp = tempfile.mkdtemp(prefix="tvd_eye_ext_")
        d = cls.tmp
        _git(d, "init", "-q")
        _git(d, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        _git(d, "config", "user.email", "gate@example.invalid")
        _git(d, "config", "user.name", "gate")
        os.makedirs(os.path.join(d, "functions", "api"))
        os.makedirs(os.path.join(d, "_archive", "assets"))
        for rel, body in (
            ("keep.py", "def a():\n    return 1\n"),
            ("functions/api/keep.js", "export function a(){ return 1; }\n"),
            ("_archive/assets/chunk.js", "var flood = 1;\n"),
            ("keep.html", "<p>x</p>\n"),
            ("keep.mjs", "export const a = 1;\n"),
            ("keep.sh", "echo hi\n"),
        ):
            p = os.path.join(d, rel.replace("/", os.sep))
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(body)
        _git(d, "add", "-A")
        _git(d, "commit", "-q", "-m", "v9999 - every extension in one commit")
        cls.sha = _git(d, "rev-parse", "HEAD").stdout.strip()

    @classmethod
    def tearDownClass(cls):
        import shutil
        try:
            shutil.rmtree(cls.tmp)
        except Exception:
            pass

    def _replay(self, argv):
        """Run the SHIPPED argv against the temp repo, with the sha swapped for ours."""
        args = ["git"] + [self.sha if a == "HEAD" else a for a in argv[1:]]
        r = subprocess.run(args, cwd=self.tmp, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0,
                         "the shipped pathspec is not valid git: %s" % (r.stderr or "")[:300])
        return r.stdout

    def test_the_code_fetch_asks_git_for_js(self):
        """THE WHOLE POINT. Without .js here, a Cloudflare change is reviewed by nobody."""
        self.assertTrue(self.argvs, "the shipped code issued no `git show` at all")
        outs = [self._replay(a) for a in self.argvs]
        self.assertTrue(any("functions/api/keep.js" in o for o in outs),
                        "NO shipped pathspec reaches a .js file - v3387's own subject would "
                        "again be invisible to the eye")

    def test_the_roster_AND_the_code_fetch_both_reach_js(self):
        """A roster that knows about a file the fetch cannot send is how a gap goes unreported;
        a fetch that sends a file the roster does not know is how it is never counted. BOTH.

        ⚠ THE HTML TOP-UP IS A NAMED EXEMPTION, NOT A WEAKENING. payload_for asks for code
        first and then appends `git show ... -- "*.html"` only if budget remains, because a
        control_ui.html diff is tens of thousands of characters of prose that would otherwise
        spend the whole cap before the eye reaches any logic. That call is SUPPOSED to see only
        html. My first cut of this case asserted every shipped git call must reach .js and went
        red on it - the TEST was wrong, not the code. Exempt it by name, with its reason, so the
        exemption cannot quietly grow. [[heart-first]] rule 4
        """
        roster = [a for a in self.argvs if "--name-only" in a]
        html_only = [a for a in self.argvs
                     if "*.html" in a and "*.py" not in a]        # the named exemption
        code = [a for a in self.argvs
                if "--name-only" not in a and a not in html_only]
        self.assertEqual(len(html_only), 1,
                         "expected exactly ONE html-only top-up; found %d - the exemption has "
                         "grown and each new one needs its own reason" % len(html_only))
        self.assertTrue(roster, "no --name-only roster call was issued at all")
        self.assertTrue(code, "no code fetch was issued at all")
        for label, group in (("roster", roster), ("code fetch", code)):
            for a in group:
                self.assertIn("functions/api/keep.js", self._replay(a),
                              "the %s still cannot see a .js file" % label)

    def test_python_still_reaches_the_eye(self):
        """BASELINE. Without it, a pathspec that had lost .py entirely would satisfy the cases
        above and this law would be measuring only the extension I happened to add.
        [[regression-guard]] section 5"""
        outs = [self._replay(a) for a in self.argvs]
        self.assertTrue(any("keep.py" in o for o in outs),
                        "the eye no longer reaches python, which is most of this repo")

    def test_an_archived_build_chunk_is_not_sent(self):
        """67 tracked .js, the bulk archived chunks. One archived rebuild must not flood the
        payload and starve the files the version is actually about."""
        # REG-1893 - the spy swallows payload_for's exceptions, so a renamed or crashing fetch
        # leaves argvs EMPTY, and "no archive chunk was sent" would pass over calls never made.
        self.assertTrue(self.argvs, "the shipped code issued no `git show` at all, so nothing "
                                    "was sent and nothing was judged")
        outs = [self._replay(a) for a in self.argvs]
        self.assertFalse(any("_archive/assets/chunk.js" in o for o in outs),
                         "an _archive/ file reached the payload - one rebuild there would spend "
                         "the whole budget on files nobody is reviewing")

    def test_the_archive_exclusion_does_not_eat_live_files(self):
        """The mirror of the case above, and the reason it is not just 'exclude more'."""
        outs = [self._replay(a) for a in self.argvs]
        joined = "\n".join(outs)
        for live in ("keep.py", "functions/api/keep.js"):
            self.assertIn(live, joined,
                          "%s was swallowed by the archive exclusion" % live)

    def test_the_html_roster_is_unchanged(self):
        """.html reaches the eye through the roster and a separate top-up; widening must not
        have cost it. A fix that trades one extension for another is not a fix."""
        outs = [self._replay(a) for a in self.argvs]
        self.assertTrue(any("keep.html" in o for o in outs),
                        "html no longer appears in any shipped git call")


RED_PROOF = [
    {
        "why": "removing .js from the code fetch restores the exact blindness that let v3387 be "
               "reviewed without either of the two files it exists to change",
        "file": "tv/second_eye_run.py",
        # re-anchored 2026-09-27: the fetch goes through _changes() now (--base), same pathspec
        "find": '                   ["--", "*.py", "*.js", "*.mjs", "*.sh",\n'
                '                    ":(exclude)_archive/*"], timeout=90)',
        "replace": '                   ["--", "*.py", "*.mjs", "*.sh"], timeout=90)',
        "matches": 1,
    },
    {
        "why": "removing .js from the ROSTER is the subtler half: the file stops being a "
               "candidate, so the omitted-file report says 0 truthfully and nobody is told",
        "file": "tv/second_eye_run.py",
        "find": '                     ["--", "*.py", "*.js", "*.mjs", "*.sh", "*.html",\n'
                '                      ":(exclude)_archive/*"], timeout=90)',
        "replace": '                     ["--", "*.py", "*.mjs", "*.sh", "*.html"], timeout=90)',
        "matches": 1,
    },
    {
        "why": "without the archive exclusion an archived rebuild is eligible, and one of those "
               "trees would spend the whole cap on files nobody reviews",
        "file": "tv/second_eye_run.py",
        # ⚠ MY FIRST CUT OF THIS SABOTAGE MATCHED 0 TIMES and heart2 called it INVALID - the
        # anchor began at `"*.py"` with 20 spaces before it, but in the file that token is
        # preceded by `"--", ` on the same line. The SABOTAGE was wrong, not the law. Anchored on
        # the exclusion's own line instead, which removes ONLY the exclusion and leaves *.js in
        # place - so this proof tests the archive case and nothing else. [[regression-guard]] 5a
        "find": '"*.sh",\n                    ":(exclude)_archive/*"], timeout=90)',
        "replace": '"*.sh"], timeout=90)',
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
