# -*- coding: utf-8 -*-
"""#2 (REG-3081) - CI RE-BLESSES THE COVERAGE FLOORS ON A FULL COLD RUN, HANDS THEM BACK, AND NEVER COMMITS THEM.

`render_check.py --bless` needs a browser and his Mac does not run one for a suite, so ~30 stale floors (task #2) could
not be raised anywhere. .github/workflows/render-bless.yml runs it on CI, and this law holds the job to the bless's own
refusal rules and to what it hands back:
  * it starts by hand (workflow_dispatch) or from a ci/bless/** push - never on main's own pushes;
  * its token reads only: no commit, no push, no write permission - a bless is a measurement handed to a person;
  * it blesses the FULL set: `render_check.py --bless` with no target, once (a subset bless refuses, and must);
  * a fresh checkout every run (a cold tree, v3215) and TV_RENDER_SCALE at render_bound.CAP, the most budget the
    render's own clock grants, since no push hook kills a slow run here;
  * the floor, its diff, the log and the record (tv/.render_bless.json, where render_check writes it) are uploaded
    even when the bless refuses, hidden files included;
  * the job's verdict is render_check's exit code, read through PIPESTATUS (not tee's), never swallowed.
Reads the workflow text with its comment lines dropped (prose is never the subject). RED_PROOF below.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import render_bound  # noqa: E402

WF = os.path.join(ROOT, ".github", "workflows", "render-bless.yml")


def _code():
    with io.open(WF, encoding="utf-8") as fh:
        return "\n".join(l for l in fh.read().split("\n") if not l.lstrip().startswith("#"))


def _step(code, name):
    """the text of one step, from its `- name:` line to the next step"""
    m = re.search(r"\n      - name: %s\n(.*?)(?=\n      - |\Z)" % re.escape(name), code, re.S)
    return m.group(1) if m else None


class CiBlessesCoverageOnAFullColdRun(unittest.TestCase):

    def test_it_starts_by_hand_or_from_a_bless_branch_never_from_main(self):
        on = re.search(r"^on:\n((?:[ \t]+[^\n]*\n)+)", _code() + "\n", re.M).group(1)
        self.assertRegex(on, r"(?m)^  workflow_dispatch:")
        self.assertEqual(re.findall(r"(?m)^      - '([^']+)'", on), ["ci/bless/**"],
                         "the bless job runs on a branch other than ci/bless/**")
        self.assertNotIn("schedule", on)

    def test_its_token_reads_only_and_it_never_commits(self):
        code = _code()
        self.assertRegex(code, r"(?m)^permissions:\n  contents: read\n")
        for bad in ("git push", "git commit", "contents: write", "git add"):
            self.assertNotIn(bad, code, "the bless job writes to the repo (%s)" % bad)

    def test_it_blesses_the_full_set_once(self):
        calls = re.findall(r"python3 tv/render_check\.py([^\n|]*)", _code())
        self.assertEqual([re.sub(r"\s*2>&1\s*$", "", c).strip() for c in calls], ["--bless"],
                         "render_check is called with a target or more than once: %r" % calls)

    def test_a_cold_checkout_and_the_most_render_budget_the_clock_grants(self):
        code = _code()
        self.assertIn("      - uses: actions/checkout@v5\n", code)
        self.assertNotRegex(code, r"actions/cache@v\d+\n(?:.*\n){0,3}.*path:.*render", "a render sandbox is restored")
        scale = re.search(r'(?m)^      TV_RENDER_SCALE: "([0-9.]+)"', code)
        self.assertIsNotNone(scale, "TV_RENDER_SCALE is not set, so a slow runner reads under his Mac's push budget")
        self.assertEqual(float(scale.group(1)), render_bound.CAP)

    def test_everything_it_measured_is_uploaded_even_on_a_refusal(self):
        up = _step(_code(), "Upload the floor, its diff, the log and the measurement")
        self.assertIsNotNone(up, "PREMISE: the upload step moved")
        self.assertIn("        if: always()\n", up)
        self.assertIn("include-hidden-files: true", up, "the record is a dotfile and would be left out")
        for f in ("tv/render_coverage.json", "tv/.render_bless.json", "render_coverage.diff", "render-bless.log"):
            self.assertIn(f, up)
        import render_check as R
        self.assertEqual(os.path.relpath(R._bless_record_path(), ROOT).replace(os.sep, "/"), "tv/.render_bless.json",
                         "the job uploads a record from a path render_check does not write")

    def test_the_jobs_verdict_is_render_checks(self):
        code = _code()
        bless = _step(code, "Bless on a full cold run")
        self.assertIsNotNone(bless, "PREMISE: the bless step moved")
        self.assertIn("rc=${PIPESTATUS[0]}", bless, "the bless step reads tee's exit, not render_check's")
        self.assertIn('echo "rc=$rc" >> "$GITHUB_OUTPUT"', bless)
        last = _step(code, "The verdict is render_check's")
        self.assertIsNotNone(last, "PREMISE: the verdict step moved")
        self.assertIn('rc="${{ steps.bless.outputs.rc }}"', last)
        self.assertIn('exit "${rc:-2}"', last, "the job's verdict is not render_check's exit code")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "#2 (REG-3081) - CI blesses a subset, which render_check refuses - or would bless what it never measured",
     "file": ".github/workflows/render-bless.yml",
     "find": "          python3 tv/render_check.py --bless 2>&1 | tee render-bless.log\n",
     "replace": "          python3 tv/render_check.py --bless vault 2>&1 | tee render-bless.log\n",
     "matches": 1},
    {"why": "#2 (REG-3081) - a refused bless uploads nothing, so the run that refused leaves no measurement",
     "file": ".github/workflows/render-bless.yml",
     "find": "        if: always()\n",
     "replace": "",
     "matches": 1},
    {"why": "#2 (REG-3081) - the bless job may write to the repo",
     "file": ".github/workflows/render-bless.yml",
     "find": "  contents: read\n",
     "replace": "  contents: write\n",
     "matches": 1},
    {"why": "#2 (REG-3081) - the job reads tee's exit, so a refused bless reads green",
     "file": ".github/workflows/render-bless.yml",
     "find": "          rc=${PIPESTATUS[0]}\n",
     "replace": "          rc=$?\n",
     "matches": 1},
    {"why": "#2 (REG-3081) - the job ends green whatever render_check said",
     "file": ".github/workflows/render-bless.yml",
     "find": "          exit \"${rc:-2}\"\n",
     "replace": "          exit 0\n",
     "matches": 1},
    {"why": "#2 (REG-3081) - the bless job runs on main's pushes",
     "file": ".github/workflows/render-bless.yml",
     "find": "      - 'ci/bless/**'\n",
     "replace": "      - 'main'\n",
     "matches": 1},
    {"why": "#2 (REG-3081) - a slow runner's reads are clamped to his Mac's push budget",
     "file": ".github/workflows/render-bless.yml",
     "find": "      TV_RENDER_SCALE: \"2.5\"\n",
     "replace": "      TV_RENDER_SCALE: \"1\"\n",
     "matches": 1},
    {"why": "#2 (REG-3081) - the record is a dotfile the upload leaves out",
     "file": ".github/workflows/render-bless.yml",
     "find": "          include-hidden-files: true\n",
     "replace": "",
     "matches": 1},
]
