# -*- coding: utf-8 -*-
"""REG-2365 — A SANDBOX NEVER CARRIES A LIVE RUN RECORD, AND THE SUITE THE HOOK RUNS FIRST NO LONGER WRITES ONE.

⚠ WHAT IT COST. REG-2361 moved the hook's tv suites ahead of the proving stage, so they now run in the tree heart2
copies a minute later. One of them, test_control's TestV2414 (the render gate's transport handler), drives
render_check.main() - and main() writes .render_verdict.json beside render_check.HERE, which that class never moved.
MEASURED in this branch's own worktree at 04:02: tv/.render_verdict.json held the class's FIXTURE verdict (abortedAt
"state-panel", renderFailures 1, chromeUpSeconds 0.0) in place of the last real render's, and every heart2 sandbox
built after it carried that file. The records a run writes into the tree it grades - the census, the render verdict,
the proposals, the red memory, the proof ledger - are not bytes a law is proved on: heart2's key leaves their names out
(_SELF_RECORDS), so a law that read one in a sandbox was proved on a live value no key held. CI checks out none of the
untracked ones and HEAD's blob of the tracked one.

THE FIX, both ends. (1) TestV2414 points render_check.HERE at a temp dir of its own. (2) heart2.make_sandbox drops
every live run record from the copy: one HEAD does not track is removed, one it tracks becomes HEAD's blob - restored
by the sandbox's own private history, so nothing reaches the real repo - and a record a gate declares in PROOF_NEEDS
stays, because that law asked for it and its key holds it. The list is heart2's _SELF_RECORDS plus
suite_verdict.RUN_RECORDS: one definition each, no third list.

These cases build a FIXTURE repo holding every record live (the tracked ledger edited past HEAD), drive the real
make_sandbox with heart2.REPO pointed at it, and read the sandbox and the fixture by name - never by listing a folder.
The TestV2414 case runs that class in a child whose render_check.HERE points at a trap: a run that forgets to move HERE
writes its verdict into the trap, never into a real tree. [[feedback-fixtures-never-touch-live-data]]
[[the-unjoined-end]] RED_PROOF below.
"""
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()       # these print non-ASCII; a cp1255 console must not crash while REPORTING
except Exception:
    pass
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import heart2           # noqa: E402
import suite_verdict    # noqa: E402

#: the history every sandbox is handed, as the gates declare it (relative to tv/)
HISTORY_NEED = "../.git"
#: the one record git tracks, and the records it does not - all live in the fixture
TRACKED = "tv/.self_arming.jsonl"
UNTRACKED = ("tv/.render_verdict.json", "tv/.heart2.json", "tv/.heart2_proposals.md", "tv/.heart2_red.json")
COMMITTED = u'{"row": "committed with the fixture"}\n'
LIVE = u'{"row": "banked by a run after the commit"}\n'
_IDENT = ["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
          "-c", "init.defaultBranch=main"]


def _clean_env():
    """os.environ without one GIT_* variable, and never his global or system git config. -> dict"""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    return env


def _git(*args):
    r = subprocess.run(["git"] + _IDENT + list(args), capture_output=True, text=True, timeout=120, encoding="utf-8",
                       errors="replace", env=_clean_env())
    if r.returncode != 0:
        raise AssertionError("fixture git %s failed: %s" % (" ".join(args), (r.stderr or "").strip()[-300:]))
    return (r.stdout or "").strip()


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _read(path):
    try:
        with io.open(path, encoding="utf-8", newline="") as fh:
            return fh.read()
    except OSError:
        return None


def _sha(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def _declaring():
    """The registered gates whose PROOF_NEEDS names the history (so the fixture sandbox gets one), by absolute path."""
    out = []
    with warnings.catch_warnings():         # other gate files' own escape sequences are not this law's finding
        warnings.simplefilter("ignore")
        for n, fn in heart2.gate_files(say=lambda *a, **k: None):
            fn = fn if os.path.isabs(fn) else os.path.join(HERE, fn)
            if HISTORY_NEED in (heart2.proof_needs_in(fn) or []):
                out.append((n, fn))
    return out


class _Case(unittest.TestCase):

    def setUp(self):
        # this law builds a repo: under a hook's leak its own git calls must not reach the real one (REG-2360)
        _gitenv = {_k: os.environ.pop(_k) for _k in list(os.environ) if _k.startswith("GIT_")}
        self.addCleanup(os.environ.update, _gitenv)
        self.root = tempfile.mkdtemp(prefix="run_records_")
        self.addCleanup(heart2._rmtree_hard, self.root)
        self.repo = os.path.join(self.root, "repo")
        _write(os.path.join(self.repo, "tv", "control_app.py"), u"# fixture\n")
        _write(os.path.join(self.repo, *TRACKED.split("/")), COMMITTED)
        _git("init", "-q", self.repo)
        _git("-C", self.repo, "config", "core.autocrlf", "false")   # #107 - the fixture's bytes, not the PC's git default
        _git("-C", self.repo, "add", "-A")
        _git("-C", self.repo, "commit", "-q", "-m", "the fixture's commit")
        _write(os.path.join(self.repo, *TRACKED.split("/")), COMMITTED + LIVE)       # a run banked past HEAD
        for rel in UNTRACKED:
            _write(os.path.join(self.repo, *rel.split("/")), u'{"live": "%s"}\n' % rel)

    def fixture_state(self):
        """every record's bytes in the FIXTURE, by name, plus what git says of its tree"""
        out = {rel: _sha(os.path.join(self.repo, *rel.split("/"))) for rel in (TRACKED,) + UNTRACKED}
        out["status"] = _git("-C", self.repo, "status", "--porcelain", "--untracked-files=all")
        out["HEAD"] = _git("-C", self.repo, "rev-parse", "HEAD")
        return out

    def build(self, gates):
        """heart2.make_sandbox for real, with REPO = the fixture and `gates` as the registered set. -> (sandbox repo
        dir, said lines); dropped when the test ends."""
        said = []
        real = (heart2.REPO, heart2.gate_files)
        heart2.REPO = self.repo
        heart2.gate_files = lambda say=None: list(gates)
        try:
            tv, root = heart2.make_sandbox(say=lambda *a, **k: said.append(" ".join(str(x) for x in a)))
        finally:
            heart2.REPO, heart2.gate_files = real
        self.assertIsNotNone(root, "PREMISE: the fixture sandbox was not built: %s" % said)
        self.addCleanup(heart2._drop_sandbox, root)
        return os.path.dirname(tv), said


class ASandboxNeverCarriesALiveRunRecord(_Case):

    def test_every_live_record_is_gone_or_heads_and_the_fixture_is_untouched(self):
        """★ the copy loses every live record - the untracked ones removed, the tracked ledger back to HEAD's blob - and
        the tree it was copied from keeps every byte (the drop acts on the copy only)"""
        declaring = _declaring()
        self.assertTrue(declaring, "PREMISE: no registered gate declares %r, so no sandbox has a history to restore "
                                   "a tracked record from" % HISTORY_NEED)
        before = self.fixture_state()
        sbx, said = self.build(declaring)
        self.assertTrue(os.path.isdir(os.path.join(sbx, ".git")), "PREMISE: the sandbox has no history: %s" % said)
        carried = [rel for rel in UNTRACKED if os.path.lexists(os.path.join(sbx, *rel.split("/")))]
        self.assertEqual(carried, [], "the sandbox carries live run records git never tracked - a law proved there "
                                      "reads a value no key holds: %s" % carried)
        restored = _read(os.path.join(sbx, *TRACKED.split("/")))
        self.assertEqual((restored or u"").replace(u"\r\n", u"\n"), COMMITTED,    # a Windows checkout may write CRLF
                         "the tracked ledger in the sandbox is not HEAD's blob - it carries the rows a run banked "
                         "after the commit")
        self.assertTrue(os.path.isfile(os.path.join(sbx, "tv", "control_app.py")), "the drop took a file it does not "
                                                                                   "own")
        self.assertEqual(self.fixture_state(), before, "building the sandbox changed the tree it copies - the drop "
                                                       "reached the real records")

    def test_the_records_are_the_two_lists_already_kept(self):
        """the set dropped is heart2's own records plus suite_verdict's gate-run records - read from both, restated
        nowhere"""
        sbx, _said = self.build(_declaring())
        want = {"tv/" + n for n in heart2._SELF_RECORDS} | set(suite_verdict.RUN_RECORDS)
        self.assertIn(TRACKED, suite_verdict.RUN_RECORDS, "PREMISE: the ledger is no longer a gate-run record")
        for rel in sorted(want):
            if rel == TRACKED:
                continue
            p = os.path.join(sbx, *rel.split("/"))
            _write(p, u"planted after the build\n")
            done = heart2._drop_run_records(sbx, (), lambda *a, **k: None)
            self.assertEqual(done.get(rel), "removed", "%s is not dropped from a sandbox: %r" % (rel, done.get(rel)))
            self.assertFalse(os.path.lexists(p), "%s survived the drop" % rel)

    def test_a_record_a_gate_declares_stays(self):
        """a law that NEEDS a record declares it in PROOF_NEEDS - its key then holds it - and the drop leaves it"""
        gate = os.path.join(self.root, "t_needs_the_verdict.py")
        _write(gate, u'PROOF_NEEDS = [".render_verdict.json"]\n')
        sbx, said = self.build(_declaring() + [("t_needs_the_verdict", gate)])
        self.assertEqual(_read(os.path.join(sbx, "tv", ".render_verdict.json")),
                         u'{"live": "tv/.render_verdict.json"}\n',
                         "a record a gate DECLARED was dropped from the sandbox: %s" % said)
        self.assertFalse(os.path.lexists(os.path.join(sbx, "tv", ".heart2.json")), "the census was kept with it")

    def test_with_no_history_heart2s_own_still_go_and_the_ledger_left_is_said(self):
        """no history in the sandbox: whether git tracks the ledger is UNKNOWN, so it stays as copied - SAID, never
        silent - while heart2's own records, which git never tracks, still go"""
        sbx, said = self.build([])
        self.assertFalse(os.path.isdir(os.path.join(sbx, ".git")), "PREMISE: the sandbox has a history")
        for rel in UNTRACKED:
            self.assertFalse(os.path.lexists(os.path.join(sbx, *rel.split("/"))), "%s was carried" % rel)
        self.assertEqual(_read(os.path.join(sbx, *TRACKED.split("/"))), COMMITTED + LIVE,
                         "PREMISE: with no history the ledger could not have been restored")
        self.assertTrue(any("live run record" in l and TRACKED in l for l in said),
                        "a live record stayed in the sandbox and nothing said so: %s" % said)


_TRAP_CHILD = r'''
import os, sys, unittest
tv, trap = sys.argv[1], sys.argv[2]
sys.path.insert(0, tv)
import render_check
render_check.HERE = trap            # where a run that never moves HERE writes its verdict
import test_control
suite = unittest.defaultTestLoader.loadTestsFromTestCase(
    test_control.TestV2414TheRenderGateReportsATransportLossInsteadOfDying)
res = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
print("RAN %d BAD %d" % (res.testsRun, len(res.failures) + len(res.errors)))
print("TRAP " + ("WRITTEN" if os.path.exists(os.path.join(trap, ".render_verdict.json")) else "EMPTY"))
print("HERE " + ("RESTORED" if render_check.HERE == trap else "LEFT ELSEWHERE"))
'''


class TheSuiteTheHookRunsFirstWritesNoRecord(unittest.TestCase):

    def test_testv2414_writes_its_verdict_into_a_dir_of_its_own(self):
        """★ test_control's render-transport class, run whole in a child whose render_check.HERE points at a trap: its
        verdict lands in a dir of its own, never where HERE pointed, and HERE is handed back"""
        trap = tempfile.mkdtemp(prefix="v2414_trap_")
        self.addCleanup(shutil.rmtree, trap, True)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        r = subprocess.run([sys.executable, "-B", "-c", _TRAP_CHILD, HERE, trap], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300, env=env, cwd=HERE)
        out = r.stdout or ""
        self.assertIn("RAN ", out, "PREMISE: the class did not run: %s" % (r.stderr or "")[-600:])
        ran = int(out.split("RAN ", 1)[1].split()[0])
        self.assertGreaterEqual(ran, 8, "PREMISE: only %d case(s) of TestV2414 ran" % ran)
        self.assertIn("BAD 0", out, "TestV2414 itself is red: %s" % (r.stderr or "")[-600:])
        self.assertIn("TRAP EMPTY", out, "TestV2414 wrote its fixture verdict where render_check.HERE pointed - in a "
                                         "push, the real tv/.render_verdict.json that heart2's sandbox then carries")
        self.assertIn("HERE RESTORED", out, "TestV2414 left render_check.HERE pointing at its own temp dir")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "REG-2365 - make_sandbox stops dropping run records: every sandbox carries the live census, render "
               "verdict and proof ledger, a value no key holds",
        "file": "heart2.py",
        "find": "        _drop_run_records(dest, {os.path.normpath(os.path.join(\"tv\", _n)).replace(os.sep, \"/\") "
                "for _n in _needs}, say)\n",
        "replace": "        pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2365 - a tracked record is left as copied: the sandbox's ledger carries the rows a run banked after "
               "HEAD",
        "file": "heart2.py",
        "find": "git + [\"checkout\", \"-q\", \"HEAD\", \"--\", rel]",
        "replace": "git + [\"status\", \"-s\", \"--\", rel]",
        "matches": 1,
    },
    {
        "why": "REG-2365 - suite_verdict's gate-run records are not read: the proof ledger stays live in every sandbox",
        "file": "heart2.py",
        "find": "        recs |= {str(r) for r in _SV.RUN_RECORDS}\n",
        "replace": "        pass\n",
        "matches": 1,
    },
    {
        "why": "REG-2365 - the drop acts on the tree it copies instead of the copy: his live records are deleted or "
               "rewound",
        "file": "heart2.py",
        "find": "    root = os.path.normpath(dest)\n    present = sorted(",
        "replace": "    root = os.path.normpath(REPO)\n    present = sorted(",
        "matches": 1,
    },
    {
        "why": "REG-2365 - a record a gate DECLARED in PROOF_NEEDS is dropped too: that law loses the input its key holds",
        "file": "heart2.py",
        "find": "    present = sorted(r for r in recs - set(keep or ())\n",
        "replace": "    present = sorted(r for r in recs\n",
        "matches": 1,
    },
    {
        "why": "REG-2365 - a live record left in the sandbox is not said: a law reads a live value and nothing names it",
        "file": "heart2.py",
        "find": "    if kept:\n        say(\"  ⚠ %d live run record(s) stay in the sandbox",
        "replace": "    if False:\n        say(\"  ⚠ %d live run record(s) stay in the sandbox",
        "matches": 1,
    },
    {
        "why": "REG-2365 - TestV2414 drives render_check.main() with HERE left on the real tv/: its fixture verdict "
               "overwrites the last real render's, before the proving stage copies the tree",
        "file": "test_control.py",
        "find": "        R.HERE = verdict_dir\n",
        "replace": "        pass\n",
        "matches": 1,
    },
]
