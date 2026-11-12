#!/usr/bin/env python3
"""Board #184 — A JOB THAT CROSSES ITS CEILING GOES SILENT, NOT RED.

GitHub does not FAIL a job that exceeds `timeout-minutes`. It CANCELS it, and `gh run list` then
prints `cancelled`, which reads as "a person pressed a button" rather than "the gate set never
reached a verdict". Measured on `.github/workflows/tv-tests.yml`, gate-set STEP durations pulled
from `gh api .../actions/runs/<id>/jobs` on 2026-09-23:

    35817826235  15m46s   completed
    35820756987  17m25s   completed
    35842043863  19m35s   completed
    35834810032  23m04s   completed
    35815188806  23m13s   completed
    35823272442  23m37s   completed   <- the worst COMPLETED run
    35825866589  24m23s   CUT OFF     <- its true length is UNKNOWN, not 24m23s

Setup before the gate-set step measured 48-64s across those runs, so the worst completed run spent
**24m41s of a 25-minute ceiling — a margin of nineteen seconds**. Whether Konyo gets a verdict is
decided by runner noise, and when he does not get one, nothing anywhere says so. Board #123 spent
weeks quoting a stale gate count ("15", really 28) for exactly this reason.

WHAT THIS GATE PINS
-------------------
1. `agent-suite` carries a step conditioned on `cancelled()`, and the workflow carries a separate
   `verdict` job that `needs` it with an `always()` condition — a second runner, whose clock the
   first one's timeout cannot touch.
2. The verdict script, EXECUTED, exits non-zero for every conclusion that is not `success` — and
   exits ZERO for `success`, which is the baseline that proves the case can tell them apart.
   [[a-law-about-a-row-must-drive-the-row]] — a law about what a row REPORTS has to call the row.
3. The ceiling watchdog treats a missing `GATE_SET_SECONDS` as UNKNOWN rather than 0. An unset
   shell variable in arithmetic is zero, which would read as "the gate set took no time, the margin
   is enormous" — the most reassuring possible lie. [[unknown-stays-unknown]]
4. `CEILING_MINUTES` in the watchdog equals `timeout-minutes` on the job. Two copies of one fact,
   and a watchdog measuring against a ceiling that has since moved reports about a number nobody
   uses. [[label-outlived-referent]] [[copy-drift]]
5. The ceiling is not simply RAISED. A ceiling above every real load is an absent detector, and a
   bigger number buys months rather than closing anything. Raising it means editing `CEILING_CAP`
   here and writing down what the new number is derived from.
6. The workflow watches ITSELF in `on: push: paths:`. `TestEveryRoutineCanSeeTheInputItPolices` in
   test_control.py already makes that a law for the five routine workflows; this file was never in
   that list, so every edit to its verdict machinery changed what CI does while triggering nothing.

WHAT THIS GATE CANNOT DO, STATED RATHER THAN IMPLIED
----------------------------------------------------
It cannot cause a real CI timeout, so GitHub's own scheduling of an `always()` job behind a
timed-out `needs` is **UNVERIFIED until it happens on a runner**. Everything above is proven by
executing the shipped shell here. The one piece of real evidence for the in-job path is run
35825866589, where the gate-set step went `cancelled` and the job's post-steps still ran — so a
step conditioned on `cancelled()` has a real chance of being reached. It is treated as best effort
and nothing depends on it.

⚠ NO `import yaml`. `TestNoSuiteImportsSomethingCIDoesNotHave` bans it outright, bare or guarded,
because v1911 imported it in a test and took the publish workflow down: PyYAML is on his Mac and is
not on the runner. The reader below is a purpose-built indentation walker, and it has its own test
that runs before any verdict built on it is believed. [[source-reading-guard]] §3.5
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe
    _console_safe()
except Exception:
    pass

REPO = os.path.dirname(HERE)
WF_REL = os.path.join(".github", "workflows", "tv-tests.yml")
WF = os.path.join(REPO, WF_REL)

#: The job ceiling this workflow is ALLOWED to declare, in minutes.
#:
#: ⚠ THIS IS A RATCHET AND THE NUMBER IS DERIVED, NOT CHOSEN. 25 is what the file has carried since
#: v1810 taught it that a stalled `playwright install` reads as `cancelled`. The measured load is
#: 24m41s worst-completed against it (see the module docstring), so the ceiling is nineteen seconds
#: above the real load — which is not a margin, it is a coin flip.
#:
#: The lever that closes board #184 is SHARDING the gate set, not a bigger number: 534 registered
#: gates run serially in one step, and `tv/run_gates.py` has no shard primitive (only
#: `--only <names>`). Raising this constant buys months and closes nothing, so moving it must be a
#: deliberate edit HERE with the new derivation written beside it.
CEILING_CAP = 25

#: Every conclusion `needs.<job>.result` can carry, and whether the verdict job may exit 0 on it.
#: `""` is the case where the job never ran at all, which is also not a pass.
CONCLUSIONS = {
    "success": 0,
    "failure": 1,
    "cancelled": 1,
    "skipped": 1,
    "": 1,
    "potato": 1,          # a value GitHub does not emit today: UNKNOWN is not a pass either
}


# ⚠⚠ v3472 — EVERY `file` BELOW WAS `WF_REL`, A NAME, AND heart2 READS THIS LIST WITH
# ast.literal_eval — which throws on a name, so the prover reported this gate as declaring NO
# red-proof and not one of its proofs had ever been executed. Literals now; the reader is fixed
# to call an unreadable list UNREADABLE rather than absent (v3473).
RED_PROOF = [
    {
        "why": "board #184 itself: the verdict job stops running when agent-suite is cancelled, so "
               "a job cut off by its own ceiling goes back to being silent - no red X, no "
               "annotation, and a run that checked nothing reads as a scheduling hiccup",
        "file": ".github/workflows/tv-tests.yml",   # a LITERAL: heart2 reads RED_PROOF by ast.literal_eval
        "find": "    if: ${{ always() }}\n",
        "replace": "    if: ${{ success() }}\n",
        "matches": 1,
    },
    {
        "why": "the loudest possible version of the defect: the verdict job still runs, reads "
               "'cancelled', and exits 0 - so NO VERDICT reports as a PASS",
        "file": ".github/workflows/tv-tests.yml",   # a LITERAL: heart2 reads RED_PROOF by ast.literal_eval
        "find": "            cancelled|skipped|\"\")\n",
        "replace": "            cancelled|skipped|\"\")\n              exit 0\n",
        "matches": 1,
    },
    {
        "why": "the in-job announcement stops being conditioned on a cancel, so the one surface "
               "that can speak from inside the dying job never fires",
        "file": ".github/workflows/tv-tests.yml",   # a LITERAL: heart2 reads RED_PROOF by ast.literal_eval
        "find": "        if: cancelled()\n",
        "replace": "        if: failure()\n",
        "matches": 1,
    },
    {
        "why": "the watchdog's copy of the ceiling drifts away from the job's real one, so every "
               "margin it prints is measured against a number nobody uses",
        "file": ".github/workflows/tv-tests.yml",   # a LITERAL: heart2 reads RED_PROOF by ast.literal_eval
        "find": "      CEILING_MINUTES: 25\n",
        "replace": "      CEILING_MINUTES: 45\n",
        "matches": 1,
    },
    {
        "why": "the ceiling is simply RAISED, which is the fix board #184 forbids: a ceiling above "
               "every real load is an absent detector",
        "file": ".github/workflows/tv-tests.yml",   # a LITERAL: heart2 reads RED_PROOF by ast.literal_eval
        "find": "    timeout-minutes: 25\n",
        "replace": "    timeout-minutes: 45\n",
        "matches": 1,
    },
    {
        "why": "an absent gate-set duration is read as ZERO instead of UNKNOWN, so a run that was "
               "cut off mid-suite prints the most reassuring margin it has ever had",
        "file": ".github/workflows/tv-tests.yml",   # a LITERAL: heart2 reads RED_PROOF by ast.literal_eval
        "find": "          if [ -z \"${GATE_SET_SECONDS:-}\" ] || [ -z \"${JOB_STARTED_AT:-}\" ]; then\n",
        "replace": "          if false; then\n",
        "matches": 1,
    },
    {
        "why": "a step takes back its own copy of the ceiling, which SHADOWS the job-scope one and "
               "then drifts from it unwatched - the shape the first cut of this file shipped, "
               "where the cancelled-path step fell back to a hardcoded 25 nothing checked",
        "file": ".github/workflows/tv-tests.yml",   # a LITERAL: heart2 reads RED_PROOF by ast.literal_eval
        "find": "      - name: How much of the ceiling was left (a thin margin is the next silent run)\n"
                "        if: always()\n",
        "replace": "      - name: How much of the ceiling was left (a thin margin is the next silent run)\n"
                   "        if: always()\n        env:\n          CEILING_MINUTES: 45\n",
        "matches": 1,
    },
    {
        "why": "the workflow stops watching itself, so a change to the verdict machinery lands "
               "without ever being run - the exact shape test_control.py polices for the five "
               "routine workflows",
        "file": ".github/workflows/tv-tests.yml",   # a LITERAL: heart2 reads RED_PROOF by ast.literal_eval
        "find": "      - '.github/workflows/tv-tests.yml'\n",
        "replace": "      # - '.github/workflows/tv-tests.yml'\n",
        "matches": 1,
    },
    {
        "why": "v3472 — a shard that never reached its end (exit 2) reads as reached in the aggregator",
        "file": ".github/workflows/tv-tests.yml",   # a LITERAL: heart2 reads RED_PROOF by ast.literal_eval
        "find": "            [ \"$_r\" = \"true\" ] || _all=false\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "v3472 — the verdict job expects fewer shards than the matrix runs",
        "file": ".github/workflows/tv-tests.yml",   # a LITERAL: heart2 reads RED_PROOF by ast.literal_eval
        "find": "      GATE_SHARDS: ${{ needs.plan.outputs.spaced }}\n",
        "replace": "      GATE_SHARDS: \"1 2 3 4\"\n",
        "matches": 1,
    },
    {
        "why": "v3472 — every shard runs the WHOLE set again, so the ceiling is crossed twice over",
        "file": ".github/workflows/tv-tests.yml",   # a LITERAL: heart2 reads RED_PROOF by ast.literal_eval
        "find": "          python3 tv/run_gates.py --shard ${{ matrix.shard }}/${{ needs.plan.outputs.n }} 2>&1 | tee \"gate-log/shard-${{ matrix.shard }}.log\"\n",
        "replace": "          python3 tv/run_gates.py 2>&1 | tee \"gate-log/shard-${{ matrix.shard }}.log\"\n",
        "matches": 1,
    },
]


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# THE READER — an indentation walker for the subset of YAML this workflow is written in.
#
# ⚠ IT GRADES CODE, NEVER PROSE. Every structural decision is taken on the comment-stripped view;
# a block scalar's BODY is taken from the raw lines, because a shell script's `#` is code.
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def strip_comment(line):
    """One line with its YAML comment removed, quote-aware. -> str

    A `#` only starts a comment at the start of a line or after whitespace, and never inside a
    quoted scalar. Anything else is a character in a value (`pw-#1`, a colour, a shell `$#`).
    """
    out, quote = [], None
    prev = ""
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            out.append(ch)
        elif ch == "#" and (prev == "" or prev in " \t"):
            break
        else:
            out.append(ch)
        prev = ch
    return "".join(out).rstrip()


def read_lines(text):
    """-> [(indent, code, raw)] for every line, comments stripped in `code` only.

    Line count is preserved: a whole-line comment becomes an empty `code` rather than vanishing,
    so nothing downstream can silently read a neighbour's line.
    """
    out = []
    for raw in text.split("\n"):
        code = strip_comment(raw)
        indent = len(code) - len(code.lstrip(" ")) if code.strip() else -1
        out.append((indent, code, raw))
    return out


def block(lines, start, indent):
    """The run of lines strictly more indented than `indent`, starting at `start`. -> [(i, ...)]"""
    out = []
    for i in range(start, len(lines)):
        ind, code, raw = lines[i]
        if ind == -1:                       # blank or comment-only: belongs to whatever follows
            out.append((i, ind, code, raw))
            continue
        if ind <= indent:
            break
        out.append((i, ind, code, raw))
    return out


def mapping_keys(lines, start, indent):
    """Every `key:` at exactly `indent` inside the block beginning at `start`. -> {key: line index}"""
    out = {}
    for i, ind, code, _raw in block(lines, start, indent - 1):
        if ind != indent:
            continue
        m = re.match(r"^ {%d}([A-Za-z0-9_.\-]+):" % indent, code)
        if m:
            out.setdefault(m.group(1), i)
    return out


def scalar(lines, idx):
    """The inline value on a `key: value` line. -> str"""
    code = lines[idx][1]
    return code.split(":", 1)[1].strip() if ":" in code else ""


def block_scalar(lines, idx):
    """The body of a `key: |` block, dedented, taken from the RAW lines. -> str

    Raw on purpose: this is a shell script, and its `#` lines are code.
    """
    key_indent = lines[idx][0]
    body, seen = [], False
    for i in range(idx + 1, len(lines)):
        ind, code, raw = lines[i]
        if not raw.strip():
            if seen:
                body.append("")
            continue
        cur = len(raw) - len(raw.lstrip(" "))
        if cur <= key_indent:
            break
        seen = True
        body.append(raw)
    if not body:
        return ""
    pad = min(len(b) - len(b.lstrip(" ")) for b in body if b.strip())
    return "\n".join(b[pad:] if b.strip() else "" for b in body)


def jobs(text):
    """-> {job name: line index of its `name:` key line}"""
    lines = read_lines(text)
    top = mapping_keys(lines, 0, 0)
    if "jobs" not in top:
        return {}, lines
    return mapping_keys(lines, top["jobs"] + 1, 2), lines


def steps(lines, job_idx):
    """Every step of the job whose key line is `job_idx`. -> [{name, if, env, run}]

    A step is a `- ` item at indent 6; its sibling keys sit at indent 8.
    """
    out = []
    for i, ind, code, _raw in block(lines, job_idx + 1, lines[job_idx][0]):
        if ind != 6 or not code.strip().startswith("- "):
            continue
        cur = {"name": None, "if": None, "env": {}, "run": None, "uses": None}
        first = code.strip()[2:]
        if ":" in first:
            k = first.split(":", 1)[0].strip()
            v = first.split(":", 1)[1].strip()
            if k in cur:
                cur[k] = v
        for j, ind2, code2, _r2 in block(lines, i + 1, 6):
            if ind2 != 8:
                continue
            m = re.match(r"^ {8}([A-Za-z0-9_.\-]+):(.*)$", code2)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            if key == "run":
                cur["run"] = block_scalar(lines, j) if val in ("|", ">", "|-", ">-") else val
            elif key == "env":
                cur["env"] = {k2: scalar(lines, idx2)
                              for k2, idx2 in mapping_keys(lines, j + 1, 10).items()}
            elif key in cur:
                cur[key] = val
        out.append(cur)
    return out


def job_env(lines, job_idx):
    """The job-scope `env:` mapping of the job whose key line is `job_idx`. -> {name: value}

    Job scope on purpose: TWO steps quote the ceiling in what they print, and a step-local copy
    left the cancelled-path step falling back to a hardcoded number nothing checked.
    """
    keys = mapping_keys(lines, job_idx + 1, 4)
    if "env" not in keys:
        return {}
    return {k: scalar(lines, i) for k, i in mapping_keys(lines, keys["env"] + 1, 6).items()}


def push_paths(text):
    """The `on: push: paths:` list, block style, one quoted string per line. -> [str]

    Same block `TestEveryRoutineCanSeeTheInputItPolices` reads, and deliberately the same regex
    for finding it: two parsers that disagree about one block is a contradiction waiting to be
    argued about.

    ⚠⚠ IT STRIPS THE COMMENT LINES BEFORE EXTRACTING, AND THE FIRST CUT DID NOT — CAUGHT BY ITS OWN
    RED-PROOF. The block pattern tolerates comment lines so a documented list still parses, and the
    extraction then ran over the WHOLE captured block, so

            # - '.github/workflows/tv-tests.yml'

    read as a live path. The sabotage that comments the entry out left GitHub no longer watching
    this file and the guard returned a byte-identical list: `STAYED_GREEN`, cause (a), a guard
    reading prose as code. [[source-reading-guard]] §4
    ⚠ The same shape is live in `test_control.py:_paths`, which is where this was copied from. Not
    touched here - that file belongs to someone else this round - but it is the same blindness.
    """
    m = re.search(r"\n  push:\n(?:\s*#[^\n]*\n)*    paths:\n"
                  r"((?:\s*(?:#[^\n]*|-\s*'[^']+')\n)+)", text)
    if not m:
        return []
    code = "\n".join(l for l in m.group(1).split("\n") if not l.lstrip().startswith("#"))
    return re.findall(r"-\s*'([^']+)'", code)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# DRIVING THE SHIPPED SHELL
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def a_shell():
    """The shell this venue can drive, matching GitHub's default flags. -> ([argv prefix], name)"""
    # REG-3629 (#107 leftover): the verdict job runs on ubuntu. On Windows `bash` is the WSL
    # launcher or Git Bash with backslash paths; neither is the job's shell, so we do not drive it.
    if os.name == "nt":
        return None, None
    bash = shutil.which("bash")
    if bash:
        return [bash, "--noprofile", "--norc", "-e", "-o", "pipefail", "-c"], "bash"
    sh = shutil.which("sh")
    if sh:
        return [sh, "-c"], "sh"
    return None, None


def run_script(body, env):
    """-> (returncode, stdout+stderr)"""
    argv, _ = a_shell()
    if argv is None:
        raise unittest.SkipTest("the verdict job's bash never runs on Windows - UNMEASURED, not passing")
    full = dict(os.environ)
    full.pop("GATE_SET_SECONDS", None)
    full.pop("JOB_STARTED_AT", None)
    full.pop("CEILING_MINUTES", None)
    full.pop("SUITE_RESULT", None)
    full.update({k: str(v) for k, v in env.items()})
    p = subprocess.run(argv + [body], env=full, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def _wf():
    with open(WF, encoding="utf-8") as fh:
        return fh.read()


def _step_named(fragment, job="agent-suite"):
    text = _wf()
    js, lines = jobs(text)
    if job not in js:
        return None
    for st in steps(lines, js[job]):
        if st["name"] and fragment in st["name"]:
            return st
    return None


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 0. THE READER IS PROVEN BEFORE ANY VERDICT BUILT ON IT IS BELIEVED
# ═══════════════════════════════════════════════════════════════════════════════════════════════

FIXTURE = """name: a fixture
on:
  push:
    # a comment naming - 'decoy/**' which is not a path
    paths:
      - 'tv/**'
      # - 'commented/out/**' is NOT watched, however much it looks like an entry
      - '.github/workflows/tv-tests.yml'
jobs:
  first-job:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    env:
      CEILING_MINUTES: 25
    steps:
      # this prose says `if: cancelled()` and is NOT a step condition
      - name: plain step
        run: echo hello
      - name: guarded step
        if: cancelled()
        env:
          STEP_LOCAL: 9
        run: |
          # a shell comment, which is CODE and must survive
          echo "left ${LEFT:-unknown}"
          exit 3
  second-job:
    needs: [first-job]
    if: ${{ always() }}
    steps:
      - name: only one
        run: echo bye
"""


class TestTheReaderItselfIsHonest(unittest.TestCase):
    """[[source-reading-guard]] §3.5 — a stripper or walker that nothing tests can only produce
    false NEGATIVES, and those are the quiet direction."""

    def test_it_finds_the_jobs_and_not_the_prose(self):
        js, lines = jobs(FIXTURE)
        self.assertEqual(sorted(js), ["first-job", "second-job"])
        st = steps(lines, js["first-job"])
        self.assertEqual([s["name"] for s in st], ["plain step", "guarded step"])
        self.assertEqual([s["if"] for s in st], [None, "cancelled()"],
                         "the walker read a COMMENT as a step condition - the §4b inversion, where "
                         "the better the comment the blinder the guard")
        self.assertEqual(st[1]["env"], {"STEP_LOCAL": "9"},
                         "a step-scope env and a job-scope env were not told apart")
        self.assertEqual([s["name"] for s in steps(lines, js["second-job"])], ["only one"])

    def test_a_block_scalar_keeps_its_shell_comments(self):
        js, lines = jobs(FIXTURE)
        body = steps(lines, js["first-job"])[1]["run"]
        self.assertIn("# a shell comment, which is CODE and must survive", body)
        self.assertTrue(body.startswith("# a shell"), "the body was not dedented: %r" % body[:40])
        self.assertIn("exit 3", body)
        self.assertNotIn("echo hello", body, "the block scalar ran past its own step")

    def test_the_block_scalar_it_extracts_actually_runs(self):
        argv, _name = a_shell()
        if argv is None and os.name == "nt":
            # #107 (REG-3801) - REG-3629 drives no shell on Windows (run_script skips there); this case asked first and
            # read red on GitHub windows-latest instead of UNMEASURED
            raise unittest.SkipTest("the verdict job's bash never runs on Windows - UNMEASURED, not passing")
        self.assertIsNotNone(argv, "no shell on this venue - the drive cases below are UNMEASURED")
        js, lines = jobs(FIXTURE)
        rc, out = run_script(steps(lines, js["first-job"])[1]["run"], {"LEFT": "7"})
        self.assertEqual(rc, 3, "the extracted body did not run as written: %s" % out)
        self.assertIn("left 7", out)

    def test_it_reads_a_job_scope_env(self):
        js, lines = jobs(FIXTURE)
        self.assertEqual(job_env(lines, js["first-job"]), {"CEILING_MINUTES": "25"})
        self.assertEqual(job_env(lines, js["second-job"]), {},
                         "a job with no env of its own inherited a neighbour's")

    def test_it_reads_the_push_paths_without_the_comments(self):
        """⚠ THE COMMENTED-OUT ENTRY IS THE POINT. This reader's first cut returned it, so the
        red-proof that comments out the self-watch line came back STAYED_GREEN over a real
        defect - the guard was reading prose as code. [[source-reading-guard]] §4"""
        self.assertEqual(push_paths(FIXTURE), ["tv/**", ".github/workflows/tv-tests.yml"],
                         "a commented line was read as a watched path - GitHub does not run on "
                         "it, and this guard would say it does")

    def test_the_comment_stripper_leaves_values_alone(self):
        self.assertEqual(strip_comment("  key: value   # trailing"), "  key: value")
        self.assertEqual(strip_comment("  key: 'a # b'"), "  key: 'a # b'")
        self.assertEqual(strip_comment("      # whole line"), "")
        self.assertEqual(strip_comment('  key: "x#y"'), '  key: "x#y"')


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 1. THE CANCELLED PATH EXISTS
# ═══════════════════════════════════════════════════════════════════════════════════════════════

class TestTheCancelledPathExists(unittest.TestCase):

    def test_the_workflow_still_parses_into_two_jobs(self):
        js, _lines = jobs(_wf())
        self.assertIn("agent-suite", js)
        self.assertIn("verdict", js,
                      "the job that converts a cancelled agent-suite into a red X is gone; a "
                      "timed-out gate set is back to reading as a scheduling hiccup")

    def test_the_suite_announces_its_own_cancellation(self):
        js, lines = jobs(_wf())
        conds = [s["if"] for s in steps(lines, js["agent-suite"]) if s["if"]]
        self.assertIn("cancelled()", conds,
                      "no step in agent-suite is conditioned on cancelled(), so nothing speaks "
                      "from inside a job that is being cut off. Conditions found: %r" % (conds,))

    def test_the_verdict_job_runs_whatever_the_suite_concluded(self):
        text = _wf()
        js, lines = jobs(text)
        keys = mapping_keys(lines, js["verdict"] + 1, 4)
        self.assertIn("needs", keys, "the verdict job does not depend on agent-suite at all")
        self.assertIn("agent-suite", scalar(lines, keys["needs"]))
        self.assertIn("if", keys, "the verdict job has no condition, so `needs` alone gates it - "
                                  "and `needs` defaults to 'only on success', which is silence")
        self.assertIn("always()", scalar(lines, keys["if"]),
                      "the verdict job is not conditioned on always(), so the one path it exists "
                      "for - a cancelled agent-suite - skips it: %r" % scalar(lines, keys["if"]))


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2. DRIVE THE VERDICT SCRIPT. A law about what a row REPORTS must CALL the row.
# ═══════════════════════════════════════════════════════════════════════════════════════════════

class TestACutOffSuiteCannotReadAsAPass(unittest.TestCase):
    """⚠ THE PREMISE IS ASSERTED FIRST. Without a shell these cases would pass while executing
    nothing, and "I could not run" must never read the same as "I ran and it was fine"."""

    def setUp(self):
        argv, name = a_shell()
        if argv is None:
            self.skipTest("no bash or sh on this venue, so the shipped verdict script cannot be "
                          "driven - UNMEASURED, not passing")
        self.shell = name
        st = _step_named("conclusion that is not a pass", job="verdict")
        self.assertIsNotNone(st, "the verdict job lost the step that reads the conclusion")
        self.body = st["run"]
        self.assertIn("SUITE_RESULT", self.body,
                      "the verdict script no longer reads the suite's conclusion at all")

    def test_success_is_the_only_conclusion_that_exits_zero(self):
        seen = {}
        for value, want_nonzero in sorted(CONCLUSIONS.items()):
            rc, out = run_script(self.body, {"SUITE_RESULT": value})
            seen[value] = rc
            if want_nonzero:
                self.assertNotEqual(rc, 0,
                                    "agent-suite = %r exits 0, so a run that produced NO VERDICT "
                                    "reads as a pass. Output:\n%s" % (value, out))
            else:
                self.assertEqual(rc, 0,
                                 "agent-suite = %r must stay green, or this row cries wolf on "
                                 "every healthy run. Output:\n%s" % (value, out))
        # the BASELINE: without it a script that exits 1 unconditionally would satisfy every
        # assertion above while being useless. [[regression-guard]] §5
        self.assertEqual(seen["success"], 0)
        self.assertNotEqual(seen["cancelled"], 0)

    def test_a_cancelled_suite_says_NO_VERDICT_in_words(self):
        rc, out = run_script(self.body, {"SUITE_RESULT": "cancelled"})
        self.assertNotEqual(rc, 0)
        self.assertIn("::error title=NO VERDICT::", out,
                      "a cancelled suite fails without saying WHY, so the log still reads as a "
                      "scheduling hiccup. Output:\n%s" % out)
        self.assertIn("timeout", out.lower(),
                      "the annotation never names the ceiling, which is the cause in every "
                      "measured case. Output:\n%s" % out)

    def test_a_red_gate_set_is_a_different_sentence_from_no_verdict(self):
        """[[unknown-stays-unknown]] — 'the gates refused' and 'the gates never answered' are two
        states, and collapsing them is how a missing verdict gets triaged as a known failure.

        ⚠⚠ v3447 — A `failure` CONCLUSION IS NOT ENOUGH TO SAY THE GATES WERE RED, and the first
        cut of this case asserted that it was. Found by the cross-family eye on the SHIPPED v3446
        bytes: a job is `failure` when ANY step fails, and two paths reach it with the gate set
        never having run —
          (1) `Install Chromium` (timeout-minutes: 6, no continue-on-error) fails, so THE GATE SET
              STEP IS SKIPPED, GATE_SET_SECONDS is never written, the always() watchdog reports
              NO VERDICT and exits 1, the job is `failure`, and the verdict job announced
              GATES RED about a gate set that never started;
          (2) the gate set exits 0 and the intake smoke after it fails — same false red.
        A red that is sometimes fiction trains a reader to ignore reds, which is worse than the
        silence this workflow was written to end. So the verdict now reads the FACT published by
        the gate-set step itself (`gate_set_reached`), and this case drives BOTH paths.
        """
        _rc_f, red = run_script(self.body, {"SUITE_RESULT": "failure",
                                            "GATE_SET_REACHED": "true", "GATE_SET_RED": "true"})
        _rc_c, none = run_script(self.body, {"SUITE_RESULT": "cancelled"})
        self.assertIn("::error title=GATES RED::", red)
        self.assertIn("::error title=NO VERDICT::", none)
        self.assertNotIn("GATES RED", none)

        # ⚠ THE PATH THE EYE FOUND: failure, but the gate set never reached its end.
        _rc_n, never = run_script(self.body, {"SUITE_RESULT": "failure"})
        self.assertNotEqual(_rc_n, 0,
                            "a job that failed before the gate set ran exits 0 — nothing was "
                            "checked and it reads as a pass.\n%s" % never)
        self.assertIn("::error title=NO VERDICT::", never,
                      "agent-suite = failure with NO gate-set verdict was not called UNKNOWN.\n%s"
                      % never)
        self.assertNotIn("GATES RED", never,
                         "a gate set that NEVER RAN was announced as RED. That is a false red, and "
                         "a red that is sometimes fiction is worse than silence.\n%s" % never)

        # ⚠⚠ v3452 — PATH (2), WHICH THIS DOCSTRING HAS NAMED SINCE v3447 AND NEVER DROVE.
        # The gate set runs to the end, every gate PASSES (`red=false`), and a LATER step — the
        # intake smoke — fails. `reached` is true, so the guard above lets it through, and the
        # failure arm announced GATES RED about a gate set that was GREEN. The case was written
        # down in two places (this docstring and the gate-set step's own comment) and implemented
        # in neither. A rule that lives only in prose is a rule nothing enforces.
        # [[feedback-comments-vs-code]] [[the-unjoined-end]]
        _rc_g, green = run_script(self.body, {"SUITE_RESULT": "failure",
                                              "GATE_SET_REACHED": "true", "GATE_SET_RED": "false"})
        self.assertNotIn("GATES RED", green,
                         "the gate set PASSED (red=false) and a later step failed, and this was "
                         "still announced as GATES RED. That is the false red v3447 was written "
                         "to end, surviving in the half that was published but never read.\n%s"
                         % green)
        self.assertIn("::error title=NO VERDICT::", green,
                      "a green gate set with a later step failing must say NO VERDICT about the "
                      "GATES - it is a real failure, but not a gate verdict.\n%s" % green)
        self.assertNotEqual(_rc_g, 0,
                            "a failed job exited 0 - a real failure would read as a pass.\n%s"
                            % green)

        # ⚠ AND THE THIRD STATE: the fact was never published at all. UNKNOWN is not a red.
        _rc_u, unk = run_script(self.body, {"SUITE_RESULT": "failure", "GATE_SET_REACHED": "true"})
        self.assertNotIn("GATES RED", unk,
                         "with no red/green fact published, the gates were still called RED. "
                         "[[unknown-stays-unknown]]\n%s" % unk)
        self.assertIn("::error title=NO VERDICT::", unk)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 3. DRIVE THE CEILING WATCHDOG
# ═══════════════════════════════════════════════════════════════════════════════════════════════

class TestAnAbsentDurationIsUnknownNeverZero(unittest.TestCase):

    def setUp(self):
        argv, _name = a_shell()
        if argv is None:
            self.skipTest("no bash or sh on this venue, so the shipped watchdog cannot be driven "
                          "- UNMEASURED, not passing")
        st = _step_named("How much of the ceiling was left")
        self.assertIsNotNone(st, "the ceiling watchdog step is gone")
        self.body = st["run"]
        js, lines = jobs(_wf())
        self.ceiling = int(job_env(lines, js["agent-suite"])["CEILING_MINUTES"])

    def _now(self):
        rc, out = run_script("date -u +%s", {})
        self.assertEqual(rc, 0, out)
        return int(out.strip())

    def test_a_missing_gate_set_duration_is_refused_not_zeroed(self):
        rc, out = run_script(self.body, {"CEILING_MINUTES": self.ceiling,
                                         "JOB_STARTED_AT": self._now() - 60})
        self.assertNotEqual(rc, 0,
                            "the gate set never finished and the watchdog reported anyway - an "
                            "unset shell variable is 0 in arithmetic, so this prints the largest "
                            "margin it has ever seen. Output:\n%s" % out)
        self.assertIn("UNKNOWN", out, "Output:\n%s" % out)

    def test_a_healthy_margin_is_quiet(self):
        """The baseline. Without it, a watchdog that warned unconditionally would satisfy the
        thin-margin case below while crying wolf on every run — which gets it silenced."""
        rc, out = run_script(self.body, {"CEILING_MINUTES": self.ceiling,
                                         "GATE_SET_SECONDS": 60,
                                         "JOB_STARTED_AT": self._now() - 120})
        self.assertEqual(rc, 0, "Output:\n%s" % out)
        self.assertNotIn("AT THE CEILING", out,
                         "a two-minute run of a %d-minute ceiling warned - this row would be "
                         "silenced within a week. Output:\n%s" % (self.ceiling, out))
        self.assertIn("left", out, "the watchdog never printed a margin at all:\n%s" % out)

    def test_a_thin_margin_says_so(self):
        used = self.ceiling * 60 - 22        # the 19-24s margin measured on board #184
        rc, out = run_script(self.body, {"CEILING_MINUTES": self.ceiling,
                                         "GATE_SET_SECONDS": used - 60,
                                         "JOB_STARTED_AT": self._now() - used})
        self.assertEqual(rc, 0, "a thin margin must WARN, never fail - the measured runs sit "
                               "inside it and a row that turns them all red gets silenced. "
                               "Output:\n%s" % out)
        self.assertIn("::warning title=AT THE CEILING::", out,
                      "the suite spent all but 22s of its ceiling and the watchdog said nothing. "
                      "Output:\n%s" % out)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 4. THE CEILING IS ONE FACT, AND IT IS NOT SIMPLY RAISED
# ═══════════════════════════════════════════════════════════════════════════════════════════════

class TestTheCeilingIsOneFact(unittest.TestCase):

    def test_the_job_declares_the_derived_ceiling(self):
        text = _wf()
        js, lines = jobs(text)
        keys = mapping_keys(lines, js["agent-suite"] + 1, 4)
        self.assertIn("timeout-minutes", keys, "agent-suite has no ceiling at all")
        got = int(scalar(lines, keys["timeout-minutes"]))
        self.assertEqual(got, CEILING_CAP,
                         "the job ceiling moved to %d. A ceiling above every real load is an "
                         "absent detector and a bigger number buys months rather than closing "
                         "anything - board #184. If %d is DERIVED from something, move CEILING_CAP "
                         "in this file and write the derivation beside it; the lever that closes "
                         "the defect is sharding the 534-gate set, not a bigger ceiling."
                         % (got, got))

    def test_the_watchdog_measures_against_the_real_ceiling(self):
        text = _wf()
        js, lines = jobs(text)
        job = int(scalar(lines, mapping_keys(lines, js["agent-suite"] + 1, 4)["timeout-minutes"]))
        env = job_env(lines, js["agent-suite"])
        self.assertIn("CEILING_MINUTES", env,
                      "the job no longer carries the ceiling its steps quote, so each of them is "
                      "back to a hardcoded number nothing drives")
        self.assertEqual(int(env["CEILING_MINUTES"]), job,
                         "the steps measure and report against %s minutes and the job is capped at "
                         "%d - two copies of one fact, drifted. Every margin printed is about a "
                         "number nobody uses." % (env["CEILING_MINUTES"], job))
        # and it must be the ONLY copy: a step-local env would shadow it silently
        strays = [s["name"] for s in steps(lines, js["agent-suite"])
                  if "CEILING_MINUTES" in (s["env"] or {})]
        self.assertEqual(strays, [],
                         "a step carries its own CEILING_MINUTES, which shadows the job-scope one "
                         "and drifts from it unwatched: %r" % (strays,))


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 5. THE WORKFLOW SEES ITS OWN INPUT
# ═══════════════════════════════════════════════════════════════════════════════════════════════

class TestTheWorkflowWatchesItself(unittest.TestCase):

    def test_editing_the_verdict_machinery_runs_the_workflow(self):
        paths = push_paths(_wf())
        self.assertTrue(paths, "tv-tests.yml has no push paths at all, or they are not the block "
                               "shape test_control.py's parser reads")
        self.assertIn("tv/**", paths)
        self.assertIn(".github/workflows/tv-tests.yml", paths,
                      "the workflow does not watch ITSELF, so a change to the cancelled-path "
                      "machinery lands without ever being exercised - the same defect "
                      "TestEveryRoutineCanSeeTheInputItPolices polices for the five routines")



class TestAShardedGateSetIsStillOneVerdict(unittest.TestCase):
    """v3472 (#184) — the gate set outgrew the 25-minute ceiling (25m18s on d9bdb682, CANCELLED, no
    verdict for a shipped version) and is now SHARDED. Sharding must not let one shard's silence or
    one shard's red disappear: a matrix job's `outputs:` keep only the LAST shard to finish, so the
    facts travel as artifacts and one step reads every shard. Each case DRIVES the shipped step."""

    def _matrix(self):
        js, lines = jobs(_wf())
        # read_lines gives (indent, CODE, raw); CODE is already comment-stripped by this file's own
        # stripper, so prose explaining the matrix can never satisfy a case about it
        body = "\n".join(code for _i, code, _raw in lines[js["agent-suite"]:js["verdict"]])
        # v3891 (#194) - the matrix is the PLAN job's list (the round chooses its slice count from measured gate costs);
        # what these cases count is that list's fallback, which the plan's n and spaced fallbacks must describe alike
        m = re.search(r"^\s*shard:\s*\$\{\{ fromJSON\(needs\.plan\.outputs\.list\) \}\}", body, re.M)
        self.assertIsNotNone(m, "agent-suite has no shard matrix (the plan job's list)")
        plan = "\n".join(code for _i, code, _raw in lines[js["plan"]:js["agent-suite"]])
        fb = re.search(r"list: \$\{\{ steps\.count\.outputs\.list \|\| '\[([\d,]+)\]' \}\}", plan)
        self.assertIsNotNone(fb, "the plan job's list output (or its fallback) is gone")
        return [x.strip() for x in fb.group(1).split(",") if x.strip()], body, lines, js

    def test_the_matrix_and_the_verdict_count_the_same_shards(self):
        shards, _b, lines, js = self._matrix()
        self.assertGreaterEqual(len(shards), 2, "a one-shard matrix is not a shard")
        env = job_env(lines, js["verdict"])
        # v3891 (#194) - ONE count: the verdict reads the plan job's spaced list, the matrix its list
        self.assertEqual(env.get("GATE_SHARDS", "").strip(), "${{ needs.plan.outputs.spaced }}",
                         "the verdict expects another set of shards than the plan dealt - a shard the verdict never "
                         "asks about is a shard whose silence reads as nothing")
        plan = "\n".join(code for _i, code, _raw in lines[js["plan"]:js["agent-suite"]])
        self.assertIn("spaced: ${{ steps.count.outputs.spaced || '%s' }}" % " ".join(shards), plan,
                      "the plan's spaced fallback is not its list fallback %r" % shards)
        self.assertIn("n: ${{ steps.count.outputs.n || '%d' }}" % len(shards), plan,
                      "the plan's count fallback is not its list's length")
        self.assertEqual(shards, [str(k) for k in range(1, len(shards) + 1)], "the fallback is not every slice 1..N")

    def test_every_shard_runs_its_own_slice_of_the_WHOLE_set(self):
        shards, body, _l, _j = self._matrix()
        want = "python3 tv/run_gates.py --shard ${{ matrix.shard }}/${{ needs.plan.outputs.n }}"   # v3891 (#194)
        self.assertIn(want, body, "the gate-set step does not run its slice of the plan's count: %r" % want)

    def test_no_matrix_output_carries_a_verdict(self):
        _s, body, _l, _j = self._matrix()
        head = body.split("    steps:")[0]
        self.assertNotIn("steps.gateset.outputs", head,
                         "agent-suite still publishes the gate-set fact as a JOB output — a matrix "
                         "keeps only the last shard's, so a red shard can be overwritten by a green one")

    def _aggregate(self, files):
        import tempfile
        st = _step_named("Every shard must have reached its end", job="verdict")
        self.assertIsNotNone(st, "the verdict job lost the step that reads every shard")
        d = tempfile.mkdtemp(prefix="shard-verdict-")
        out = os.path.join(d, "GITHUB_OUTPUT")
        try:
            os.mkdir(os.path.join(d, "v"))
            for k, (r, red) in files.items():
                io.open(os.path.join(d, "v", "shard-%s.txt" % k), "w").write("reached=%s\nred=%s\n" % (r, red))
            rc, log = run_script(st["run"], {"GATE_SHARDS": "1 2", "VERDICT_DIR": os.path.join(d, "v"),
                                             "GITHUB_OUTPUT": out})
            got = (dict(l.split("=", 1) for l in io.open(out).read().split() if "=" in l)
                   if os.path.exists(out) else {})
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertEqual(rc, 0, log)
        return got

    def test_the_aggregator_reads_every_shard(self):
        if a_shell()[0] is None:
            self.skipTest("no bash or sh on this venue - UNMEASURED, not passing")
        self.assertEqual(self._aggregate({1: ("true", "false"), 2: ("true", "false")}),
                         {"reached": "true", "red": "false"}, "two green shards did not read as green")
        self.assertEqual(self._aggregate({1: ("true", "false")}),
                         {"reached": "false", "red": "unknown"},
                         "a shard that published NOTHING read as reached — its silence became a pass")
        self.assertEqual(self._aggregate({1: ("true", "true"), 2: ("true", "false")}),
                         {"reached": "true", "red": "true"}, "one red shard did not make the set red")
        self.assertEqual(self._aggregate({1: ("false", "unknown"), 2: ("true", "false")}),
                         {"reached": "false", "red": "unknown"},
                         "a shard that never reached its end (exit 2) read as reached")
        self.assertEqual(self._aggregate({2: ("true", "true")}),
                         {"reached": "false", "red": "true"},
                         "a red shard beside a SILENT one lost the red")


if __name__ == "__main__":
    unittest.main(verbosity=2)
