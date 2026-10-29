# -*- coding: utf-8 -*-
"""A NEWER PUSH TO THE SAME ci/ BRANCH CANCELS THE OLDER RUN, AND MAIN IS NEVER CANCELLED (gbl/ci-speed).

MEASURED 2026-10-23 21:00-21:25 IDT: main fb2079a3 (v3791) pushed at 20:51; its Publish smoke gate waited 25.1 min
and its python suites 16.8 min for a runner, behind ~12 ci/gbl-* branch runs - some of them already replaced by a
newer push to the same branch (ci/gbl-board-winwatch had three commits' agent tests queued at once). Publish ran
about 10 min of work in a 33.9 min wall.

Every workflow a ci/** push can start now carries one concurrency block: on refs/heads/ci/* the group is the
workflow + the branch and cancel-in-progress is true, so the newer push stops the older run; on any other ref the
group is the run's own id, so the shared block never cancels a main, schedule or pull-request run - not running,
and not pending either (GitHub keeps one pending run per group and drops the rest, see publish.yml).
Two workflows keep their OWN rule, pinned here too: Publish (one group publish-main, never cancelled) and
Routine I (v699.1 his ruling: newest commit wins per ref - on main as well).

Each case evaluates the workflow's OWN concurrency expressions for a given ref and run id. RED_PROOF below.
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

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

WF = os.path.join(ROOT, ".github", "workflows")
#: workflows that keep their own concurrency rule, with the reason. Neither may lose its block.
OWN_RULE = {
    "publish.yml": "main only; serialises deploys, never cancels a running publish",
    "routine-i-playwright.yml": "v699.1 his ruling: one Playwright verdict per ref, the newest commit's",
}


def _read(name):
    with io.open(os.path.join(WF, name), encoding="utf-8") as fh:
        return fh.read()


def _code(text):
    """the workflow with YAML comment lines dropped - prose is never the subject"""
    return "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))


def _top_block(code, key):
    """the lines of a top-level `key:` mapping (indented children), or None"""
    m = re.search(r"^%s:[ \t]*\n((?:[ \t]+[^\n]*\n|[ \t]*\n)*)" % re.escape(key), code + "\n", re.M)
    return m.group(1) if m else None


def _wf_name(name):
    """github.workflow: the file's top-level `name:`, else its path (GitHub's own fallback)"""
    m = re.search(r"^name:[ \t]*(.+?)[ \t]*$", _code(_read(name)), re.M)
    return m.group(1).strip().strip("'\"") if m else ".github/workflows/" + name


def _may_match_ci(pattern):
    """can a positive branches pattern match a ci/<x> branch? Only a plain literal outside ci/ cannot."""
    p = pattern.strip().strip("'\"")
    return p.startswith("ci/") or p.startswith("!") or any(ch in p for ch in "*?[+")


def _push_on_ci(code):
    """does a push to refs/heads/ci/<x> start this workflow? (branch filters read; paths are not a ref filter)"""
    on = _top_block(code, "on")
    if on is None:
        return False
    m = re.search(r"^  push:[ \t]*\n((?:    [^\n]*\n|[ \t]*\n)*)", on, re.M)
    if not m and not re.search(r"^  push:[ \t]*$", on, re.M):
        return False
    push = m.group(1) if m else ""
    b = re.search(r"^    branches:\s*\[([^\]]*)\]", push, re.M)
    if b:
        return any(_may_match_ci(x) for x in b.group(1).split(","))
    b = re.search(r"^    branches:[ \t]*\n((?:      - [^\n]*\n)+)", push, re.M)
    if b:
        return any(_may_match_ci(x.strip()[2:]) for x in b.group(1).strip().split("\n"))
    return True                                       # no branches filter (branches-ignore keeps other ci/ refs)


def _expr(value, ctx):
    """evaluate one GitHub `${{ }}` template over ctx - the grammar these blocks use: github.*, startsWith, &&, ||,
    single-quoted strings, literal text around the braces"""
    def one(m):
        e = m.group(1).strip()
        e = re.sub(r"startsWith\(\s*([^,]+?)\s*,\s*('[^']*')\s*\)", r"str(\1).startswith(\2)", e)
        e = e.replace("&&", " and ").replace("||", " or ")
        e = re.sub(r"\bgithub\.(\w+)", r"ctx['\1']", e)
        if re.search(r"[^\w\s'\[\]().,/:*-]", e.replace(" and ", " ").replace(" or ", " ")):
            raise AssertionError("an expression this law cannot read: %r" % m.group(1))
        return str(eval(e, {"__builtins__": {"str": str}}, {"ctx": ctx}))  # noqa: S307 (fixed grammar above)
    return re.sub(r"\$\{\{(.*?)\}\}", one, value.strip().strip("'\""))


def concurrency_for(name, ref, run_id, workflow=None):
    """-> (group, cancel: bool) | None - the workflow's top-level concurrency, evaluated"""
    code = _code(_read(name))
    blk = _top_block(code, "concurrency")
    if blk is None:
        return None
    g = re.search(r"^  group:\s*(.+)$", blk, re.M)
    c = re.search(r"^  cancel-in-progress:\s*(.+)$", blk, re.M)
    if not g:
        return None
    ctx = {"ref": ref, "run_id": str(run_id), "workflow": workflow or _wf_name(name), "head_ref": "", "sha": "sha%s" % run_id}  # per-run like GitHub, so a sha in the group cannot hide
    cancel = _expr(c.group(1), ctx).strip().lower() == "true" if c else False
    return _expr(g.group(1), ctx), cancel


#: every workflow file, NAMED - never listed: a law that lists a directory is unkeyable and re-proves on every push
#: (test_the_unkeyable_laws_only_get_fewer, REG-2363). Each name is a string constant heart2 keys by its bytes.
#: A NEW workflow file must be added here; the census below then decides whether a ci push can start it.
WORKFLOW_FILES = (
    ".github/workflows/publish.yml",
    ".github/workflows/render-bless.yml",
    ".github/workflows/routine-g-audit.yml",
    ".github/workflows/routine-h-item-sweep.yml",
    ".github/workflows/routine-i-playwright.yml",
    ".github/workflows/routine-j-screens.yml",
    ".github/workflows/routine-k-perf.yml",
    ".github/workflows/routine-l-integrity.yml",
    ".github/workflows/routine-m-swallows.yml",
    ".github/workflows/tv-soak.yml",
    ".github/workflows/tv-tests.yml",
    ".github/workflows/tv-windows-boot.yml",
)


def ci_workflows():
    return sorted(n for n in (os.path.basename(f) for f in WORKFLOW_FILES) if _push_on_ci(_code(_read(n))))


class TheBranchRule(unittest.TestCase):

    def test_the_census_of_workflows_is_measured(self):
        names = ci_workflows()
        self.assertIn("tv-tests.yml", names)
        self.assertIn("tv-windows-boot.yml", names)
        self.assertNotIn("publish.yml", names, "publish runs on main only")
        self.assertGreaterEqual(len(names), 8, "a zero needs a denominator: %r" % names)

    def test_every_ci_workflow_has_the_block(self):
        for n in ci_workflows():
            self.assertIsNotNone(concurrency_for(n, "refs/heads/ci/x", 1),
                                 "%s runs on ci/** pushes with no concurrency: a replaced push keeps its runners" % n)

    def test_a_newer_push_to_the_same_ci_branch_cancels_the_older(self):
        for n in ci_workflows():
            a = concurrency_for(n, "refs/heads/ci/gbl-m4-5", 101)
            b = concurrency_for(n, "refs/heads/ci/gbl-m4-5", 202)
            self.assertEqual(a[0], b[0], "%s: two pushes to one ci branch are in different groups" % n)
            self.assertTrue(b[1], "%s: the newer ci push does not cancel the older run" % n)

    def test_two_ci_branches_never_cancel_each_other(self):
        for n in ci_workflows():
            self.assertNotEqual(concurrency_for(n, "refs/heads/ci/gbl-m4-5", 1)[0],
                                concurrency_for(n, "refs/heads/ci/gbl-m2-5", 2)[0], n)

    def test_two_workflows_on_one_ci_branch_never_cancel_each_other(self):
        groups = {}
        for n in ci_workflows():
            g = concurrency_for(n, "refs/heads/ci/x", 7)[0]          # github.workflow = the file's real name
            self.assertNotIn(g, groups, "%s and %s share a group on one push" % (n, groups.get(g)))
            groups[g] = n
            if n not in OWN_RULE:   # a group without the workflow collides the day a second workflow copies it
                self.assertIn(_wf_name(n), g, "%s: the group does not name its workflow" % n)

    def test_workflow_names_are_unique(self):
        names = [_wf_name(n) for n in ci_workflows()]
        self.assertEqual(len(names), len(set(names)), "two ci workflows share a name, so a group: %r" % names)

    def test_a_branch_filter_is_read_as_github_reads_it(self):
        for pat, hit in (("main", False), ("'release'", False), ("ci/**", True), ("'!main'", True), ("**", True),
                         ("feature/*", True), ("gbl/x", False)):
            self.assertEqual(_may_match_ci(pat), hit, pat)
        self.assertTrue(_push_on_ci("on:\n  push:\n    branches: ['!main']\njobs:\n"))
        self.assertFalse(_push_on_ci("on:\n  push:\n    branches: [main]\njobs:\n"))
        self.assertTrue(_push_on_ci("on:\n  push:\n    paths:\n      - 'tv/**'\njobs:\n"))

    def test_main_is_never_cancelled(self):
        for n in ci_workflows():
            if n in OWN_RULE:
                continue
            for ref in ("refs/heads/main", "refs/pull/12/merge", "refs/heads/gbl/ci-speed", "refs/heads/cix"):
                a, b = concurrency_for(n, ref, 101), concurrency_for(n, ref, 202)
                self.assertFalse(b[1], "%s: cancel-in-progress is true on %s" % (n, ref))
                self.assertNotEqual(a[0], b[0], "%s: two %s runs share a group, so GitHub drops a pending one" % (n, ref))

    def test_the_own_rule_workflows_keep_their_block(self):
        p1, p2 = concurrency_for("publish.yml", "refs/heads/main", 1), concurrency_for("publish.yml", "refs/heads/main", 2)
        self.assertEqual((p1, p2), (("publish-main", False), ("publish-main", False)),
                         "Publish must serialise every main publish in one group and never cancel one")
        m1 = concurrency_for("routine-i-playwright.yml", "refs/heads/main", 1)
        m2 = concurrency_for("routine-i-playwright.yml", "refs/heads/main", 2)
        self.assertTrue(m1[1] and m1[0] == m2[0] == "routine-i-refs/heads/main",
                        "Routine I lost his v699.1 rule on main (one group, newest wins): %r %r" % (m1, m2))
        ri = concurrency_for("routine-i-playwright.yml", "refs/heads/ci/x", 1)
        self.assertTrue(ri[1] and ri[0] == concurrency_for("routine-i-playwright.yml", "refs/heads/ci/x", 2)[0],
                        "Routine I lost its newest-commit-wins rule on ci branches")


if __name__ == "__main__":
    unittest.main()


RED_PROOF = [
    {
        "why": "gbl/ci-speed - tv-tests has no concurrency again: a replaced ci push keeps 5 shards of runners",
        "file": "../.github/workflows/tv-tests.yml",
        "find": "concurrency:\n  group: ${{ github.workflow }}-${{ startsWith(github.ref, 'refs/heads/ci/') && github.ref || github.run_id }}\n  cancel-in-progress: ${{ startsWith(github.ref, 'refs/heads/ci/') }}\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "gbl/ci-speed - cancel-in-progress true everywhere: a newer main push cancels the older main run",
        "file": "../.github/workflows/tv-windows-boot.yml",
        "find": "  cancel-in-progress: ${{ startsWith(github.ref, 'refs/heads/ci/') }}\n",
        "replace": "  cancel-in-progress: true\n",
        "matches": 1,
    },
    {
        "why": "gbl/ci-speed - the group is the ref on main too: GitHub keeps one pending main run and drops the rest",
        "file": "../.github/workflows/routine-m-swallows.yml",
        "find": "&& github.ref || github.run_id }}",
        "replace": "&& github.ref || github.ref }}",
        "matches": 1,
    },
    {
        "why": "gbl/ci-speed - the ci test is the wrong prefix: every branch, main included, is cancelled",
        "file": "../.github/workflows/routine-l-integrity.yml",
        "find": "  cancel-in-progress: ${{ startsWith(github.ref, 'refs/heads/ci/') }}\n",
        "replace": "  cancel-in-progress: ${{ startsWith(github.ref, 'refs/heads/') }}\n",
        "matches": 1,
    },
    {
        "why": "gbl/ci-speed - the workflow left the group: one push's workflows cancel each other",
        "file": "../.github/workflows/routine-g-audit.yml",
        "find": "  group: ${{ github.workflow }}-${{",
        "replace": "  group: ci-${{",
        "matches": 1,
    },
    {
        "why": "gbl/ci-speed - the group is the run id on ci too: a replaced ci run is never cancelled",
        "file": "../.github/workflows/routine-k-perf.yml",
        "find": "&& github.ref || github.run_id }}",
        "replace": "&& github.run_id || github.run_id }}",
        "matches": 1,
    },
    {
        "why": "review r1 - Routine I stops grouping main by ref: his v699.1 newest-wins rule is gone on main",
        "file": "../.github/workflows/routine-i-playwright.yml",
        "find": "  group: routine-i-${{ github.ref }}\n",
        "replace": "  group: routine-i-${{ startsWith(github.ref, 'refs/heads/ci/') && github.ref || github.run_id }}\n",
        "matches": 1,
    },
    {
        "why": "review r1 - Publish leaves its one group: two main publishes stop serialising",
        "file": "../.github/workflows/publish.yml",
        "find": "  group: publish-main\n",
        "replace": "  group: publish-${{ github.run_id }}\n",
        "matches": 1,
    },
]
