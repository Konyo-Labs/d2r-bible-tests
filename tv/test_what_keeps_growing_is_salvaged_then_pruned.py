# -*- coding: utf-8 -*-
"""REG-3208 (the growers lane) / REG-3209 (salvage before prune) - WHAT KEEPS GROWING ON THE DISK IS MEASURED, ITS
INFORMATION SAVED AND READ BACK, AND ONLY THEN PRUNED, IN A LOOP.

His words 2026-11-05: "whatever keeps growing needs to have a looped system in place that prunes and extracts and saves
any data informational that's needed". MEASURED that night: 6.9 GiB free, under his 8 GB ON AIR floor; 94 scratch dirs
in the temp root, ~3.3 GB of Grok-seat worktrees (some NOT merged, some not git trees at all), 2.2 GB of Claude's own
shipped worktrees, and a 2.7 GB clone holding ONE commit not upstream by patch-id that Claude had to salvage by hand.
Nothing in the console measured or pruned any of it. tv/disk_growers.py is the lane; the console runs it in the disk
sign's pass; console_doctor's "disk growers" row reads it. Held here, every fixture a temp dir (never his temp root):
  * a dirty / unmerged worktree is salvaged FIRST (each commit not upstream as a format-patch that `git am` restores, the
    tracked dirty diff, untracked files under the cap, the over-cap ones named) and read back, and only then removed
    through `git worktree remove` - the repo's worktree list no longer names it, its branch survives;
  * a tree a live process holds is skipped - held at measure time it is not even salvaged, held by the time of the
    prune it stays; when holders cannot be read nothing is pruned and owed is UNKNOWN;
  * a salvage that does not read back BLOCKS the prune, and so does a tree whose upstream cannot be told;
  * inside the age floor nothing is touched; the dry-run never deletes, and arms only after its clean passes span a day;
  * the console's tree, the salvage dir and the main tree of linked worktrees are never pruned; a scratch dir keeps its
    summary, verdicts and the tail of its logs; a skip glob is never looked at;
  * the console asks for the lane only from its own loop, publishes it on the disk sign, and the doctor row says which
    link broke - a salvage the lane claims that is not on disk is MISSING.
THE ADVERSARIAL REVIEW (each reproduced on a temp fixture before it was fixed, each held here):
  * lsof was asked ONCE per pass: a shell that entered tree B after tree A's prune did not stop B's. Now it is asked
    again before EACH prune, after that tree's own salvage;
  * age was mtime only: a folder made seconds ago by cp -Rp from a 10-day-old one read 240 h old and was pruned at once.
    Age is now the newer of mtime and ctime, which no copy carries over;
  * git cherry skips merge commits: a clone's conflict resolution was in no salvaged file. A tree with a merge commit
    not upstream is now salvaged as a bundle of its unmerged history too, and the bundle restores it;
  * patches and the dirty diff had no cap and nothing checked free space: a 30 MB dirty binary became a 58 MB salvage on
    a disk at 2 GB free. Every written byte now counts against SALVAGE_CAP (past it the tree waits, nothing is cut
    short), a diff whose files sum past READ_CAP is never read, and nothing is written that leaves the salvage disk
    under SALVAGE_MIN_FREE or the salvage dir past SALVAGE_DIR_CAP;
  * ONE tree that can never be salvaged (no origin/main, an untracked nested repo that raised IsADirectoryError) reset
    its whole entry's dry-run every pass, so the entry never armed. A declared wait no longer counts as a failed
    salvage, and a nested repo waits with its own reason;
  * $TMPDIR, where the laws leak (vault-law- 518, playwright-artifacts- 414 measured), was not declared: law fixture
    prefixes now are, as RECORD entries (one manifest line each, no salvage folder, never re-recorded);
  * owed read 0 while a grower's age was UNKNOWN, and a PC with no psutil was UNKNOWN even with nothing to prune: owed is
    now UNKNOWN exactly when a grower's decision rested on something unread, and holders are asked lazily;
  * a corrupt state reset every entry to dry-run and said so nowhere; a lane that only WAITED for days read OK. Both
    are said now, the second as MISSING after GROWERS_UNMEASURED_H;
  * a pass is bounded: PRUNES_PER_PASS growers, the rest deferred and counted in owed.
RED_PROOF below.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except Exception:
    pass
import disk_growers as DG  # noqa: E402

H = 3600.0
POINTERS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR")


def _entry(kind=DG.KIND_GIT, mode=DG.ARMED, name="claude-trees", globs=("claude-fx-*",), skip=(), floor=24, bound=168):
    return {"name": name, "platforms": (sys.platform,), "root": "TMP", "globs": globs, "skip": skip, "owner": "claude",
            "kind": kind, "floorH": floor, "boundH": bound, "mode": mode, "keep": DG._KEEP, "why": "a law's fixture"}


def _w(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def _r(path):
    with open(path, "rb") as fh:
        return fh.read()


class Fixture(object):
    """A repo with origin/main, a temp root for growers and a salvage dir - all under one temp dir."""

    def __init__(self, base):
        self.base = base
        self.root = os.path.join(base, "root")
        self.salv = os.path.join(base, "salvage")
        self.main = os.path.join(base, "repo")
        os.makedirs(self.root)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(HOME=base, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="law", GIT_AUTHOR_EMAIL="law@example.invalid",
                        GIT_COMMITTER_NAME="law", GIT_COMMITTER_EMAIL="law@example.invalid")
        self.repo(self.main)

    def g(self, cwd, *args):
        r = subprocess.run(["git", "-C", cwd] + list(args), env=self.env, capture_output=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("fixture git %s failed: %s" % (args, r.stderr.decode("utf-8", "replace")))
        return r.stdout.decode("utf-8", "replace").strip()

    def repo(self, path, upstream=True):
        os.makedirs(path)
        self.g(path, "init", "-q")
        self.g(path, "config", "core.autocrlf", "false")  # #107 REG-3626 - the fixture's bytes, not the PC's git default
        self.g(path, "checkout", "-q", "-b", "main")
        _w(os.path.join(path, "a.txt"), "one\n")
        self.g(path, "add", "a.txt")
        self.g(path, "commit", "-q", "-m", "base")
        if upstream:
            self.g(path, "update-ref", "refs/remotes/origin/main", "HEAD")
        return path

    def worktree(self, name, branch, main=None, where=None):
        p = os.path.join(where or self.root, name)
        self.g(main or self.main, "worktree", "add", "-q", "-b", branch, p, "main")
        return p

    def listed(self):
        return [ln[len("worktree "):] for ln in self.g(self.main, "worktree", "list", "--porcelain").splitlines()
                if ln.startswith("worktree ")]

    def run(self, entries, now_h=100.0, free_gb=5.0, held=(set(), "a law's holders: nobody"), **kw):
        kw.setdefault("salvage_dir", self.salv)
        return DG.run(entries=entries, root_map={"TMP": self.root}, free_bytes=lambda p: free_gb * 1e9,
                      now_s=time.time() + now_h * H, held=held, **kw)


def _cand(rec, name):
    return next(c for c in rec["candidates"] if c["name"] == name)


def _manifest(fx):
    p = os.path.join(fx.salv, "manifest.jsonl")
    return [json.loads(ln) for ln in _r(p).decode("utf-8").splitlines()] if os.path.exists(p) else []


class _Base(unittest.TestCase):

    def setUp(self):
        # REG-2360 - a leaked GIT_DIR would aim every git call at the hook's repo; scrubbed for this law's own scope
        p = mock.patch.dict(os.environ, {})
        p.start()
        self.addCleanup(p.stop)
        for k in POINTERS:
            os.environ.pop(k, None)
        d = tempfile.mkdtemp(prefix="growers-law-")
        self.addCleanup(shutil.rmtree, d, True)
        self.fx = Fixture(os.path.realpath(d))

    def unmerged(self, name="claude-fx-work", branch="claude/work"):
        fx = self.fx
        wt = fx.worktree(name, branch)
        _w(os.path.join(wt, "new.txt"), "unmerged work\n")
        fx.g(wt, "add", "new.txt")
        fx.g(wt, "commit", "-q", "-m", "unmerged")
        _w(os.path.join(wt, "a.txt"), "one\nedited\n")
        _w(os.path.join(wt, "note.md"), "notes worth keeping\n")
        _w(os.path.join(wt, "big.bin"), b"x" * 5000)
        return wt


class ADirtyUnmergedTreeIsSalvagedBeforeItIsRemoved(_Base):

    def test_salvaged_read_back_then_removed_through_the_worktree_list(self):
        fx = self.fx
        wt = self.unmerged()
        done = fx.worktree("claude-fx-done", "claude/done")
        seen = []
        real_prune = DG.prune

        def spy(c, facts):
            line = [m for m in _manifest(fx) if m["event"] == "salvage" and m["path"] == c["path"]]
            seen.append((c["name"], bool(line) and DG.verify(os.path.join(fx.salv, line[-1]["dir"]))[0]))
            return real_prune(c, facts)
        with mock.patch.object(DG, "FILE_CAP", 1000), mock.patch.object(DG, "prune", side_effect=spy):
            rec = fx.run([_entry()])
        self.assertIsNone(rec["error"], rec["error"])
        self.assertEqual(sorted(seen), [("claude-fx-done", True), ("claude-fx-work", True)],
                         "a tree was pruned before its salvage was on disk and read back")
        self.assertEqual(sorted(r["name"] for r in rec["removed"]), ["claude-fx-done", "claude-fx-work"], rec["say"])
        self.assertFalse(os.path.exists(wt) or os.path.exists(done))
        self.assertEqual([p for p in fx.listed() if os.path.realpath(p) != fx.main], [],
                         "the folders are gone and the repo's worktree list still names them")
        self.assertTrue(fx.g(fx.main, "rev-parse", "--verify", "claude/work"), "the branch went with the worktree")
        fin = {r["name"]: r["finished"] for r in rec["removed"]}
        self.assertEqual(fin, {"claude-fx-done": True, "claude-fx-work": False})
        sal = os.path.join(fx.salv, _cand(rec, "claude-fx-work")["salvage"]["dir"])
        meta = json.loads(_r(os.path.join(sal, "meta.json")).decode("utf-8"))
        names = sorted(meta["files"])
        self.assertTrue(any(re.match(r"patches/0001-[0-9a-f]{12}\.patch$", n) for n in names), names)
        self.assertIn("dirty.diff", names)
        self.assertEqual(_r(os.path.join(sal, "untracked", "note.md")), b"notes worth keeping\n")
        self.assertEqual([(n["path"], n["why"]) for n in meta["notSaved"]], [("big.bin", "over the size cap")])
        # the salvage RESTORES: the patch onto origin/main, then the dirty diff
        back = fx.worktree("restore", "restore", where=fx.base)
        patch = [n for n in names if n.startswith("patches/")][0]
        fx.g(back, "am", "-q", os.path.join(sal, patch))
        fx.g(back, "apply", "--binary", os.path.join(sal, "dirty.diff"))
        self.assertEqual(_r(os.path.join(back, "new.txt")), b"unmerged work\n")
        self.assertEqual(_r(os.path.join(back, "a.txt")), b"one\nedited\n")
        ev = [(m["event"], os.path.basename(m["path"])) for m in _manifest(fx)]
        self.assertLess(ev.index(("salvage", "claude-fx-work")), ev.index(("prune", "claude-fx-work")))
        self.assertEqual(rec["owed"], 0)
        self.assertGreater(rec["salvageBytes"], 0, "the salvage dir grows too, and the pass did not measure it")
        self.assertIn("the salvage dir holds", rec["say"])


class TheWorktreeListIsKeptTrue(_Base):

    def test_an_entry_whose_folder_someone_deleted_is_said(self):
        fx = self.fx
        gone = fx.worktree("claude-fx-gone", "claude/gone", where=fx.base)
        shutil.rmtree(gone)
        rec = fx.run([_entry()], repo=fx.main)
        self.assertEqual((rec["staleWorktrees"], rec["staleNames"]), (1, ["claude-fx-gone"]))
        self.assertIn("git worktree prune clears them", rec["say"])
        self.assertEqual(len(fx.listed()), 2, "the lane acted on an entry it is only meant to say")


class ATreeALiveProcessHoldsIsSkipped(_Base):

    def test_held_at_measure_time_is_not_even_salvaged(self):
        wt = self.unmerged()
        rec = self.fx.run([_entry()], held=({os.path.join(os.path.realpath(wt), "a.txt")}, "a law's holders"))
        c = _cand(rec, "claude-fx-work")
        self.assertEqual(c["state"], "held", c["why"])
        self.assertTrue(os.path.isdir(wt))
        self.assertFalse(os.path.isdir(os.path.join(self.fx.salv, "claude-trees")), "a held tree was salvaged")

    def test_held_by_the_time_of_the_prune_it_stays(self):
        wt = self.unmerged()
        asks = iter([(set(), "first ask: nobody"), ({os.path.realpath(wt)}, "second ask: a shell went in")])
        with mock.patch.object(DG, "holders", side_effect=lambda *a, **k: next(asks)):
            rec = self.fx.run([_entry()], held=None)
        self.assertTrue(os.path.isdir(wt), "a tree a process entered during the pass was pruned")
        self.assertEqual(_cand(rec, "claude-fx-work")["state"], "held")

    def test_holders_unknown_prunes_nothing_and_owes_unknown(self):
        wt = self.unmerged()
        rec = self.fx.run([_entry()], held=(None, "there is no lsof here"))
        self.assertTrue(os.path.isdir(wt))
        self.assertEqual(_cand(rec, "claude-fx-work")["state"], "unknown")
        self.assertIsNone(rec["owed"], "holders nobody could read was reported as a measured owed")

    def test_a_real_process_whose_cwd_is_inside(self):
        if sys.platform.startswith("win") or not shutil.which("lsof"):
            self.skipTest("no lsof on this machine - the seam cases above hold the rule here")
        wt = self.unmerged()
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], cwd=wt)
        self.addCleanup(child.wait)
        self.addCleanup(child.kill)
        deadline = time.time() + 10
        hs = None
        while time.time() < deadline:
            hs, _why = DG.holders()
            if hs is not None and DG._held_by(hs, os.path.realpath(wt)):
                break
            time.sleep(0.2)
        self.assertTrue(hs is not None and DG._held_by(hs, os.path.realpath(wt)), "lsof never named the child's cwd")
        rec = self.fx.run([_entry()], held=None)
        self.assertEqual(_cand(rec, "claude-fx-work")["state"], "held")
        self.assertTrue(os.path.isdir(wt))


class ASalvageThatDoesNotReadBackBlocksThePrune(_Base):

    def test_a_patch_written_short_blocks_it(self):
        wt = self.unmerged()
        real_write = DG._write

        def short(path, data):
            # #107 (REG-3809) - on Windows the salvage path comes back with forward slashes: compare it normalised
            return real_write(path, data[:-5] if "/patches/" in str(path).replace("\\", "/") else data)
        with mock.patch.object(DG, "_write", side_effect=short):
            rec = self.fx.run([_entry()])
        c = _cand(rec, "claude-fx-work")
        self.assertEqual(c["state"], "waiting", c["why"])
        self.assertIn("read back", c["why"])
        self.assertTrue(os.path.isdir(wt), "a tree whose salvage did not read back was pruned")
        self.assertEqual([w["name"] for w in rec["waiting"]], ["claude-fx-work"])
        self.assertEqual(rec["owed"], 1)
        self.assertNotIn("prune", [m["event"] for m in _manifest(self.fx)])

    def test_a_tree_whose_upstream_cannot_be_told_waits(self):
        clone = self.fx.repo(os.path.join(self.fx.root, "claude-fx-clone"), upstream=False)
        rec = self.fx.run([_entry()])
        c = _cand(rec, "claude-fx-clone")
        self.assertEqual(c["state"], "waiting", c["why"])
        self.assertIn("origin/main", c["why"])
        self.assertTrue(os.path.isdir(clone))


class InsideTheAgeFloorNothingIsTouched(_Base):

    def test_a_fresh_tree_and_a_fresh_scratch_dir_stay_unsalvaged(self):
        wt = self.unmerged()
        sc = os.path.join(self.fx.root, "claude-fx-probe")
        _w(os.path.join(sc, "verdict.json"), "{}")
        rec = self.fx.run([_entry(), _entry(kind=DG.KIND_SCRATCH, name="claude-scratch")], now_h=0.0)
        for n in ("claude-fx-work", "claude-fx-probe"):
            self.assertEqual(_cand(rec, n)["state"], "young", _cand(rec, n)["why"])
        self.assertTrue(os.path.isdir(wt) and os.path.isdir(sc))
        self.assertFalse(os.path.exists(os.path.join(self.fx.salv, "manifest.jsonl")), "a young grower was salvaged")

    def test_an_age_that_could_not_be_measured_is_unknown(self):
        wt = self.unmerged()
        with mock.patch.object(DG, "WALK_BUDGET_S", -1.0):
            rec = self.fx.run([_entry()])
        self.assertEqual(_cand(rec, "claude-fx-work")["state"], "unknown")
        self.assertTrue(os.path.isdir(wt))
        self.assertIsNone(rec["owed"], "a grower whose age nobody could read was reported as a measured owed")


class TheDryRunNeverDeletes(_Base):

    def test_it_salvages_never_deletes_and_arms_only_after_a_day_of_clean_passes(self):
        fx = self.fx
        wt = self.unmerged()
        t0 = time.time() + 100 * H
        for i, dh in enumerate((0.0, 13.0, 25.0)):
            rec = DG.run(entries=[_entry(mode=DG.DRY)], root_map={"TMP": fx.root}, salvage_dir=fx.salv,
                         free_bytes=lambda p: 5e9, now_s=t0 + dh * H, held=(set(), "nobody"))
            c = _cand(rec, "claude-fx-work")
            self.assertEqual(c["state"], "would-prune", c["why"])
            self.assertTrue(os.path.isdir(wt), "the dry-run deleted on pass %d" % (i + 1))
            self.assertTrue(c["salvage"]["ok"])
            st = json.loads(_r(os.path.join(fx.salv, "state.json")).decode("utf-8"))["entries"]["claude-trees"]
            self.assertEqual(st["cleanPasses"], i + 1)
            if i < 2:
                self.assertFalse(st.get("armedTs"), "a dry-run armed itself inside a day")
        self.assertTrue(st.get("armedTs"), "three clean passes over 25 h did not arm it")
        rec = DG.run(entries=[_entry(mode=DG.DRY)], root_map={"TMP": fx.root}, salvage_dir=fx.salv,
                     free_bytes=lambda p: 5e9, now_s=t0 + 26 * H, held=(set(), "nobody"))
        self.assertEqual(_cand(rec, "claude-fx-work")["state"], "pruned")
        self.assertFalse(os.path.exists(wt))

    def test_three_quick_passes_do_not_arm_it(self):
        fx = self.fx
        self.unmerged()
        t0 = time.time() + 100 * H
        for dh in (0.0, 0.5, 1.0, 1.5):
            DG.run(entries=[_entry(mode=DG.DRY)], root_map={"TMP": fx.root}, salvage_dir=fx.salv,
                   free_bytes=lambda p: 5e9, now_s=t0 + dh * H, held=(set(), "nobody"))
        st = json.loads(_r(os.path.join(fx.salv, "state.json")).decode("utf-8"))["entries"]["claude-trees"]
        self.assertEqual(st["cleanPasses"], 4)
        self.assertFalse(st.get("armedTs"), "four passes inside two hours armed a new grower kind")


class WhatIsNeverPruned(_Base):

    def test_the_console_tree_the_salvage_dir_and_a_main_tree(self):
        fx = self.fx
        wt = self.unmerged()
        inner = os.path.join(fx.root, "claude-fx-salvage")
        os.makedirs(inner)
        main2 = fx.repo(os.path.join(fx.root, "claude-fx-main"))
        fx.worktree("linked", "linked", main=main2, where=fx.base)
        rec = fx.run([_entry(), _entry(kind=DG.KIND_SCRATCH, name="claude-scratch")], protect=(wt,), salvage_dir=inner)
        for n in ("claude-fx-work", "claude-fx-salvage", "claude-fx-main"):
            self.assertEqual(_cand(rec, n)["state"], "protected", (n, _cand(rec, n)["why"]))
            self.assertTrue(os.path.isdir(os.path.join(fx.root, n)))
        self.assertIn("main tree of 1", _cand(rec, "claude-fx-main")["why"])

    def test_a_main_tree_whose_worktrees_cannot_be_listed_is_kept(self):
        """v3865 (GitHub's swallow ratchet) - a worktrees folder that exists and will not list was 0 linked worktrees, so a
        main tree with live worktrees read as an ordinary tree the prune may take. It is UNKNOWN now, and kept."""
        fx = self.fx
        main2 = fx.repo(os.path.join(fx.root, "claude-fx-main"))
        fx.worktree("linked", "linked", main=main2, where=fx.base)
        real = os.listdir

        def listdir(p="."):
            if os.path.basename(str(p).rstrip("/")) == "worktrees":
                raise PermissionError("the worktrees folder will not list")
            return real(p)
        with mock.patch.object(DG.os, "listdir", listdir):
            rec = fx.run([_entry()], now_h=900.0)
        c = _cand(rec, "claude-fx-main")
        self.assertEqual(c["state"], "protected", c["why"])
        self.assertIn("could not be read", c["why"])
        self.assertTrue(os.path.isdir(os.path.join(fx.root, "claude-fx-main")))

    def test_the_disk_over_its_watermark_keeps_what_is_inside_its_bound(self):
        wt = self.unmerged()
        rec = self.fx.run([_entry()], free_gb=500.0)
        self.assertEqual(_cand(rec, "claude-fx-work")["state"], "kept")
        self.assertTrue(os.path.isdir(wt))
        rec = self.fx.run([_entry()], free_gb=500.0, now_h=200.0)
        self.assertEqual(_cand(rec, "claude-fx-work")["state"], "pruned", "past its age bound it stayed")


class AScratchDirKeepsWhatIsInformational(_Base):

    def test_summary_verdicts_and_log_tails_then_pruned(self):
        fx = self.fx
        sc = os.path.join(fx.root, "grok-3843posts")
        _w(os.path.join(sc, "out", "verdict.json"), '{"ok": false}')
        log = b"".join(b"line %06d\n" % i for i in range(5000))
        _w(os.path.join(sc, "run.log"), log)
        _w(os.path.join(sc, "frame.bin"), b"\0" * 9000)
        lock = os.path.join(fx.root, "grok-file-lock-501")
        _w(os.path.join(lock, "slot-1"), "")
        nested = os.path.join(fx.root, "grok-nested")
        os.makedirs(os.path.join(nested, "sub", ".git"))
        ent = _entry(kind=DG.KIND_SCRATCH, name="grok-scratch", globs=("grok-*",), skip=("grok-file-lock-*",))
        rec = fx.run([ent])
        self.assertNotIn("grok-file-lock-501", [c["name"] for c in rec["candidates"]], "a skip glob was looked at")
        self.assertEqual(_cand(rec, "grok-nested")["state"], "unclaimed")
        self.assertTrue(os.path.isdir(nested))
        c = _cand(rec, "grok-3843posts")
        self.assertEqual(c["state"], "pruned", c["why"])
        sal = os.path.join(fx.salv, c["salvage"]["dir"])
        self.assertEqual(_r(os.path.join(sal, "kept", "out", "verdict.json")), b'{"ok": false}')
        self.assertEqual(_r(os.path.join(sal, "kept", "run.log.tail")), log[-DG.LOG_TAIL:])
        summ = json.loads(_r(os.path.join(sal, "summary.json")).decode("utf-8"))
        self.assertEqual(summ["files"], 3)
        self.assertEqual(summ["biggest"][0], {"path": "run.log", "bytes": len(log)})


class TheConsoleRunsItAndTheDoctorReadsIt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import control_app as ca
        cls.ca = ca

    def setUp(self):
        ca = self.ca
        for name in ("_GROWERS", "_DISK_SIGN", "_GROK_PRUNE"):
            saved = dict(getattr(ca, name))
            self.addCleanup(lambda n=name, s=saved: (getattr(ca, n).clear(), getattr(ca, n).update(s)))

    def test_only_the_consoles_loop_asks_and_never_beside_his_game(self):
        ca = self.ca
        calls = []
        with mock.patch.object(ca, "_growers_pass", side_effect=lambda *a, **k: calls.append(a)), \
                mock.patch.object(ca, "_grok_prune_pass"):
            ca._disk_sign_once(now_ms=1, playing=False, busy_pct=0, candidates=[])
            self.assertEqual(calls, [], "a pass nobody asked for the growers walked the temp root")
            ca._disk_sign_once(now_ms=2, playing=False, busy_pct=0, candidates=[], growers=True)
            self.assertEqual(calls, [(2,)], "the loop's pass never reached the growers lane")
            ca._disk_sign_once(now_ms=3, playing=True, busy_pct=0, candidates=[], growers=True)
            self.assertEqual(len(calls), 1, "the growers lane ran beside his game")
        self.assertEqual(ca._GROWERS["checkedTs"], 3)
        self.assertIn("playing", ca._GROWERS["say"])
        src = _r(os.path.join(HERE, "control_app.py")).decode("utf-8")
        code = "\n".join(ln.split("#")[0] for ln in src.splitlines())
        self.assertEqual(code.count("r = _disk_sign_once(growers=True)"), 1, "the console's loop never asks for it")

    def test_the_lane_record_is_published_in_the_shared_words(self):
        ca = self.ca
        got = {}

        def fake(**k):
            got.update(k)
            return {"ts": 5, "growers": [{"name": "grok-trees", "owner": "grok", "kind": DG.KIND_GIT, "n": 7,
                                          "bytes": 3.3e9, "atLeast": False, "mode": DG.DRY}],
                    "biggest": [], "waiting": [], "wouldPrune": [{"name": "grok-v3850"}], "removed": [], "owed": 1,
                    "worked": 4, "freed": 0, "freedBytes": 9, "dryRun": [], "say": "growers: grok-trees 3.30 GB (7)",
                    "lastSalvage": None, "error": None, "stateWhy": None, "free": 6.9e9}
        rec = ca._growers_pass(now_ms=5, _run=fake)
        self.assertEqual((rec["on"], rec["worked"], rec["lastTs"], rec["owed"]), (True, 4, 5, 1))
        self.assertEqual(rec["top"][0]["name"], "grok-trees")
        self.assertIn(ca.REPO, got["protect"])
        self.assertIn(ca.HIST_DIR, got["protect"])
        self.assertEqual(got["salvage_dir"], DG.salvage_root(ca.REPO))
        self.assertEqual(got["repo"], ca.REPO)
        self.assertEqual(ca.disk_sign_payload(_free=lambda: 50e9)["growers"]["say"], "growers: grok-trees 3.30 GB (7)")

        def boom(**k):
            raise RuntimeError("x")
        rec = ca._growers_pass(now_ms=6, _run=boom)
        self.assertIsNone(rec["owed"], "a pass that raised reported a measured owed")
        self.assertIn("raised", rec["say"])

    def test_the_doctor_row_says_which_link_broke(self):
        import console_doctor as cd
        d = tempfile.mkdtemp(prefix="growers-doctor-")
        self.addCleanup(shutil.rmtree, d, True)
        now = 10 ** 13
        ok = {"on": True, "lastTs": now, "checkedTs": now, "owed": 0, "say": "growers: x", "waiting": [], "dryRun": [],
              "top": [{"name": "grok-trees", "gb": 3.3, "owner": "grok", "n": 7}], "lastSalvage": None, "error": None}

        def row(g):
            st = {"diskSign": ({} if g == "absent" else {"growers": g})}
            return cd._check_the_disk_growers_are_salvaged_then_pruned(status=st, now_ms=now, salvage_dir=d)
        with mock.patch.object(cd, "_get", return_value=None):           # the console did not answer - never his
            self.assertEqual(cd._check_the_disk_growers_are_salvaged_then_pruned(now_ms=now)[0], cd.UNKNOWN)
        self.assertEqual(row("absent")[0], cd.UNKNOWN)
        self.assertEqual(row(dict(ok, lastTs=None, checkedTs=None))[0], cd.UNKNOWN)
        stale = row(dict(ok, checkedTs=now - 3 * 3600 * 1000))
        self.assertEqual(stale[0], cd.MISSING, stale)
        # REG-3208 review - a loop that only WAITED (his game, a busy CPU) moves checkedTs; its sizes are that old
        idle = row(dict(ok, lastTs=now - 30 * 3600 * 1000, say="waiting - the machine is busy (100% CPU)"))
        self.assertEqual(idle[0], cd.MISSING, idle)
        self.assertIn("not MEASURED for 30 h", idle[1])
        wait = row(dict(ok, waiting=[{"name": "grok-v3856", "why": "patch did not read back"}]))
        self.assertEqual(wait[0], cd.MISSING)
        self.assertIn("grok-v3856", wait[1])
        lie = row(dict(ok, lastSalvage="grok-trees/grok-v3856-abc"))
        self.assertEqual(lie[0], cd.MISSING, "a salvage the lane claims and the disk does not hold read OK")
        _w(os.path.join(d, "grok-trees", "grok-v3856-abc", "meta.json"), "{}")
        good = row(dict(ok, lastSalvage="grok-trees/grok-v3856-abc"))
        self.assertEqual(good[0], cd.OK, good)
        self.assertIn("grok-trees 3.30 GB", good[1])
        self.assertIn("(measured 0 min ago)", good[1], "the row shows sizes without the age of the reading")
        reset = row(dict(ok, stateWhy="the growers state did not read (ValueError) - moved aside"))
        self.assertIn("did not read", reset[1], "a state reset is said nowhere")
        self.assertEqual(row(dict(ok, owed=None))[0], cd.UNKNOWN)
        self.assertIn("disk growers", dict(cd.CHECKS))
        self.assertIn("disk growers", cd.WATCHES)


class TheRegistryIsDeclared(unittest.TestCase):

    def test_every_entry_is_whole_and_a_new_kind_starts_in_dry_run(self):
        keys = {"name", "platforms", "root", "globs", "skip", "owner", "kind", "floorH", "boundH", "mode", "salvage",
                "why"}
        names = [e["name"] for e in DG.GROWERS]
        self.assertEqual(len(names), len(set(names)))
        for e in DG.GROWERS:
            self.assertTrue(keys <= set(e), (e["name"], keys - set(e)))
            self.assertIn(e["kind"], (DG.KIND_GIT, DG.KIND_SCRATCH))
            self.assertIn(e["salvage"], (DG.COPY, DG.RECORD))
            self.assertFalse(e["kind"] == DG.KIND_GIT and e["salvage"] == DG.RECORD,
                             "%s would prune git trees with only a record line" % e["name"])
            self.assertEqual(e["mode"], DG.DRY, "%s is armed in the registry - a kind arms by evidence, not by edit"
                             % e["name"])
            self.assertLess(e["floorH"], e["boundH"])

    def test_no_glob_names_a_live_folder(self):
        import fnmatch
        live = ("claude-501", "claude-mcp-browser-bridge-someone", "grokbot-presence", "grok-file-lock-501",
                "tv-nightly", "d2r_chrome_remote_profile", "sessions",
                # the per-user temp dir's live residents (REG-3208 review): his console's child guard, the shadow
                # reader's Chrome profile, the Grok intake, Chrome's own, every program's default prefix
                "tvd-child-guard-1a2b3c4d", "tvd-shadow-chrome", "tvd-intake-abc", "com.google.Chrome.abc123",
                "scoped_dir12_34", "tmpab12cd34", "heartlane_x1", "d2r-pre-push.123")
        for e in DG.GROWERS:
            for n in live:
                hit = any(fnmatch.fnmatch(n, g) for g in e["globs"]) and not any(
                    fnmatch.fnmatch(n, s) for s in e["skip"])
                self.assertFalse(hit, "%s would look at %s" % (e["name"], n))

    def test_each_platform_names_its_own_scratch_root(self):
        self.assertEqual(DG.roots("darwin", {}), {"TMP": "/private/tmp", "TMPDIR": "/private/tmp"})
        self.assertEqual(DG.roots("darwin", {"TMPDIR": "/var/folders/xy/abc/T/"}),
                         {"TMP": "/private/tmp", "TMPDIR": "/var/folders/xy/abc/T"},
                         "the per-user temp dir, where the laws leak, is not a root")
        self.assertEqual(DG.roots("linux", {}), {"TMP": "/tmp", "TMPDIR": "/tmp"})
        self.assertEqual(DG.roots("win32", {"TEMP": r"C:\Users\x\AppData\Local\Temp"}),
                         {"TEMP": r"C:\Users\x\AppData\Local\Temp"})
        self.assertEqual(DG.roots("win32", {}), {})
        posix = {tuple(e["globs"]) + (e["kind"],) for e in DG.entries_for("darwin")}
        win = {tuple(e["globs"]) + (e["kind"],) for e in DG.entries_for("win32")}
        self.assertEqual(posix, win, "a grower declared on the Mac has no twin on a Windows PC")
        self.assertTrue(all(e["root"] == "TEMP" for e in DG.entries_for("win32")))
        law = [e for e in DG.entries_for("darwin") if e["root"] == "TMPDIR"]
        self.assertEqual([(e["name"], e["salvage"], e["kind"]) for e in law],
                         [("law-scratch", DG.RECORD, DG.KIND_SCRATCH)])


class EachPruneAsksAgainWhatHoldsIt(_Base):
    """REG-3208 review (the blocker) - the reviewer's fixture: tree A is pruned, then a shell enters tree B."""

    def test_a_process_that_entered_a_later_tree_mid_pass_stops_its_prune(self):
        fx = self.fx
        a = fx.worktree("claude-fx-a", "claude/a")
        b = fx.worktree("claude-fx-b", "claude/b")

        def lsof(*_a, **_k):
            # the moment A is gone a shell has cd'd into B - a reading taken before A's prune cannot know it
            return ({os.path.realpath(b)} if not os.path.exists(a) else set()), "a law's holders"
        with mock.patch.object(DG, "holders", side_effect=lsof):
            rec = fx.run([_entry()], held=None)
        self.assertEqual(_cand(rec, "claude-fx-a")["state"], "pruned", _cand(rec, "claude-fx-a")["why"])
        self.assertEqual(_cand(rec, "claude-fx-b")["state"], "held", _cand(rec, "claude-fx-b")["why"])
        self.assertTrue(os.path.isdir(b), "a tree a process entered after the pass's first reading was pruned")
        self.assertEqual(rec["holdersAsked"], 3, "holders: once to measure, then once before EACH prune")


class TheGrokCliOnREG3208And3209(_Base):
    """v3867 - the Grok CLI's look at v3865's post-stamp commits (#231 6674616986): four ways a prune could take
    something that was not saved, or a hold nobody read."""

    def test_a_stash_of_untracked_files_is_restored_from_the_salvage(self):
        fx = self.fx
        clone = os.path.join(fx.root, "claude-fx-stash")
        r = subprocess.run(["git", "clone", "-q", fx.main, clone], env=fx.env, capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        _w(os.path.join(clone, "only_here.txt"), "work that lives only in the stash\n")
        fx.g(clone, "stash", "-u", "-q")
        self.assertFalse(os.path.exists(os.path.join(clone, "only_here.txt")), "the fixture's stash did not take it")
        st = fx.g(clone, "stash", "list", "--format=%H").split()[0]
        self.assertEqual(fx.g(clone, "diff", st + "^1", st), "", "premise: the first-parent diff names nothing")
        rec = fx.run([_entry()])
        c = _cand(rec, "claude-fx-stash")
        self.assertEqual(c["state"], "pruned", c["why"])
        sal = os.path.join(fx.salv, c["salvage"]["dir"])
        got = [n for n in os.listdir(os.path.join(sal, "stash")) if n.endswith(".untracked.diff")]
        self.assertEqual(len(got), 1, "the stash's untracked files were not salvaged: %s" % os.listdir(os.path.join(sal, "stash")))
        back = os.path.join(fx.base, "back")
        r = subprocess.run(["git", "clone", "-q", fx.main, back], env=fx.env, capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        fx.g(back, "apply", os.path.join(sal, "stash", got[0]))
        self.assertEqual(_r(os.path.join(back, "only_here.txt")).decode("utf-8"), "work that lives only in the stash\n")

    def test_a_process_of_this_user_that_will_not_answer_is_unknown_on_windows(self):
        import getpass
        me = getpass.getuser()

        class _P(object):
            def __init__(self, owner, ok):
                self.owner, self.ok = owner, ok

            def cwd(self):
                if not self.ok:
                    raise PermissionError("denied")
                return "/x"

            def open_files(self):
                return []

            def username(self):
                if self.owner is None:
                    raise PermissionError("denied")
                return self.owner
        for procs, unknown in (([_P("NT AUTHORITY\\SYSTEM", False), _P(me, True)], False),
                               ([_P("DOMAIN\\" + me, False)], True),
                               ([_P(None, False)], True),
                               ([_P(None, False), _P("NT AUTHORITY\\SYSTEM", False)], True)):
            fake = type(sys)("psutil")
            fake.process_iter = lambda procs=procs: iter(procs)
            with mock.patch.dict(sys.modules, {"psutil": fake}):
                held, why = DG.holders(platform="win32")
            self.assertEqual(held is None, unknown, "%r -> %r (%s)" % ([(p.owner, p.ok) for p in procs], held, why))

    def test_a_partial_lsof_is_unknown(self):
        class _R(object):
            stdout = b"p123\nn/some/file\n"
            returncode = 1
        held, why = DG.holders(platform="darwin", _run=lambda *a, **k: _R())
        self.assertIsNone(held, "an lsof that exited 1 read as a complete listing: %r" % (why,))
        self.assertIn("partial", why)
        _R.returncode = 0
        held, _why = DG.holders(platform="darwin", _run=lambda *a, **k: _R())
        self.assertEqual(held, {"/some/file"})

    def test_a_process_holding_only_the_worktrees_gitdir_stops_its_prune(self):
        fx = self.fx
        wt = self.unmerged()
        gd = fx.g(wt, "rev-parse", "--absolute-git-dir")
        self.assertIn("/worktrees/", gd.replace("\\", "/"),      # #107 (REG-3809) - git writes / on Windows too
                      "premise: a linked worktree's gitdir is under the main .git")
        calls = []

        def lsof(*_a, **_k):
            calls.append(1)
            # the measuring read sees nobody; the re-ask before the prune sees a process holding the worktree's index
            return (set() if len(calls) == 1 else {os.path.join(os.path.realpath(gd), "index")}), "a law's holders"
        with mock.patch.object(DG, "holders", side_effect=lsof):
            rec = fx.run([_entry()], held=None)
        c = _cand(rec, os.path.basename(wt))
        self.assertEqual(c["state"], "held", c["why"])
        self.assertTrue(os.path.isdir(wt), "a worktree whose gitdir a process held was pruned")


class ACopyThatKeptOldTimesIsYoung(_Base):
    """REG-3208 review - age was mtime only, and cp -Rp / tar / unzip / rsync -a keep mtimes."""

    def test_a_folder_copied_a_second_ago_from_a_ten_day_old_one_is_inside_its_floor(self):
        old = os.path.join(self.fx.base, "old-probe")
        _w(os.path.join(old, "probe.py"), "print('a probe a seat is about to run')\n")
        ten_days = time.time() - 10 * 86400
        for q in (os.path.join(old, "probe.py"), old):
            os.utime(q, (ten_days, ten_days))
        new = os.path.join(self.fx.root, "grok-copy-just-made")
        shutil.copytree(old, new)                      # copy2 keeps the mtimes, as cp -p does
        self.assertGreater(time.time() - os.lstat(new).st_mtime, 9 * 86400, "the fixture's copy did not keep mtimes")
        ent = _entry(kind=DG.KIND_SCRATCH, name="grok-scratch", globs=("grok-*",), floor=48, bound=72)
        rec = self.fx.run([ent], now_h=0.0, free_gb=500.0)
        c = _cand(rec, "grok-copy-just-made")
        self.assertEqual(c["state"], "young", c["why"])
        self.assertTrue(os.path.isfile(os.path.join(new, "probe.py")), "a folder made a second ago was pruned")


class AMergeCommitIsSalvagedAsABundle(_Base):
    """REG-3209 review - git cherry skips merge commits, and a clone's branch does not survive its rmtree."""

    def test_the_work_done_inside_a_merge_is_restored_from_the_salvage(self):
        fx = self.fx
        clone = os.path.join(fx.root, "claude-fx-clone")
        r = subprocess.run(["git", "clone", "-q", fx.main, clone], env=fx.env, capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        fx.g(clone, "checkout", "-q", "-b", "side")
        _w(os.path.join(clone, "s.txt"), "side\n")
        fx.g(clone, "add", "s.txt")
        fx.g(clone, "commit", "-q", "-m", "side")
        fx.g(clone, "checkout", "-q", "main")
        _w(os.path.join(clone, "m.txt"), "mainline\n")
        fx.g(clone, "add", "m.txt")
        fx.g(clone, "commit", "-q", "-m", "m1")
        fx.g(clone, "merge", "-q", "--no-ff", "--no-commit", "side")
        _w(os.path.join(clone, "resolution.txt"), "work done only inside the merge commit\n")
        fx.g(clone, "add", "resolution.txt")
        fx.g(clone, "commit", "-q", "-m", "merge side + resolution")
        fx.g(clone, "branch", "-q", "-D", "side")
        rec = fx.run([_entry()])
        c = _cand(rec, "claude-fx-clone")
        self.assertEqual(c["state"], "pruned", c["why"])
        self.assertFalse(c["finished"], "a clone holding a merge commit not upstream read as finished")
        sal = os.path.join(fx.salv, c["salvage"]["dir"])
        self.assertTrue(os.path.isfile(os.path.join(sal, "history.bundle")), sorted(os.listdir(sal)))
        back = os.path.join(fx.base, "back")
        r = subprocess.run(["git", "clone", "-q", fx.main, back], env=fx.env, capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        fx.g(back, "fetch", "-q", os.path.join(sal, "history.bundle"), "HEAD:refs/heads/salvaged")
        self.assertEqual(fx.g(back, "show", "salvaged:resolution.txt"), "work done only inside the merge commit")


class ASalvageNeverCostsTheDiskMoreThanItRelieves(_Base):
    """REG-3208 review - a 30 MB dirty binary became a 58 MB salvage on a disk at 2 GB free."""

    def _assert_waits(self, rec, wt, words):
        c = _cand(rec, "claude-fx-work")
        self.assertEqual(c["state"], "waiting", c["why"])
        self.assertIn(words, c["why"])
        self.assertTrue(os.path.isdir(wt), "a tree whose salvage was refused was pruned")
        self.assertFalse(os.path.isdir(os.path.join(self.fx.salv, "claude-trees")), "a refused salvage was written")

    def test_unmerged_work_over_the_cap_waits_whole_and_is_never_cut_short(self):
        wt = self.unmerged()
        with mock.patch.object(DG, "SALVAGE_CAP", 200):
            rec = self.fx.run([_entry()])
        self._assert_waits(rec, wt, "salvage cap")

    def test_a_diff_whose_files_are_too_big_is_never_read(self):
        wt = self.unmerged()
        calls = []
        real_git = DG.git

        def spy(path, args, *a, **k):
            calls.append(args[0])
            return real_git(path, args, *a, **k)
        with mock.patch.object(DG, "READ_CAP", 5), mock.patch.object(DG, "git", side_effect=spy):
            rec = self.fx.run([_entry()])
        self._assert_waits(rec, wt, "more than the lane reads")
        self.assertNotIn("format-patch", calls, "a commit over the read cap was read into memory anyway")

    def test_nothing_is_written_that_leaves_the_salvage_disk_under_its_floor(self):
        wt = self.unmerged()
        rec = self.fx.run([_entry()], free_gb=DG.SALVAGE_MIN_FREE / 1e9 + 0.00001)
        self._assert_waits(rec, wt, "would leave the salvage disk under")

    def test_a_salvage_dir_at_its_cap_takes_no_more(self):
        wt = self.unmerged()
        with mock.patch.object(DG, "SALVAGE_DIR_CAP", 1000):
            rec = self.fx.run([_entry()])
        self._assert_waits(rec, wt, "at its")

    def test_a_pass_is_bounded_and_the_rest_is_owed(self):
        fx = self.fx
        for n in ("claude-fx-s1", "claude-fx-s2"):
            _w(os.path.join(fx.root, n, "x.txt"), "x")
        ent = _entry(kind=DG.KIND_SCRATCH, name="claude-scratch")
        with mock.patch.object(DG, "PRUNES_PER_PASS", 1):
            rec = fx.run([ent])
        self.assertEqual(sorted(c["state"] for c in rec["candidates"]), ["deferred", "pruned"])
        self.assertEqual(rec["owed"], 1, "a grower deferred to a later pass was not owed")


class OneTreeThatCannotBeSalvagedDoesNotHoldItsEntryBack(_Base):
    """REG-3208 review - one stray reset the whole entry's dry-run every pass, so it never armed."""

    def test_the_entry_arms_on_the_trees_it_can_salvage_and_the_strays_wait_with_their_reason(self):
        fx = self.fx
        good = fx.worktree("claude-fx-good", "claude/good")
        stray = fx.repo(os.path.join(fx.root, "claude-fx-stray"), upstream=False)
        nested = fx.worktree("claude-fx-nested", "claude/nested")
        inner = fx.repo(os.path.join(nested, "vendor", "lib"), upstream=False)
        big = self.unmerged("claude-fx-big", "claude/big")
        t0 = time.time() + 100 * H
        with mock.patch.object(DG, "SALVAGE_CAP", 200):
            for dh in (0.0, 13.0, 25.0):
                rec = DG.run(entries=[_entry(mode=DG.DRY)], root_map={"TMP": fx.root}, salvage_dir=fx.salv,
                             free_bytes=lambda p: 5e9, now_s=t0 + dh * H, held=(set(), "nobody"))
        st = json.loads(_r(os.path.join(fx.salv, "state.json")).decode("utf-8"))["entries"]["claude-trees"]
        self.assertTrue(st.get("armedTs"), "strays it cannot salvage kept the entry from arming: %s" % st)
        self.assertIn("origin/main", _cand(rec, "claude-fx-stray")["why"])
        self.assertIn("git repository inside", _cand(rec, "claude-fx-nested")["why"])
        self.assertIn("salvage cap", _cand(rec, "claude-fx-big")["why"])
        self.assertEqual(_cand(rec, "claude-fx-good")["state"], "would-prune")
        for p in (good, stray, nested, inner, big):
            self.assertTrue(os.path.isdir(p))


class LawFixturesInTheUserTempDirAreRecorded(_Base):
    """REG-3208 review - $TMPDIR was not declared; the laws' leaks live there."""

    def _law(self, mode):
        return _entry(kind=DG.KIND_SCRATCH, name="law-scratch", globs=DG._LAW, mode=mode, bound=72)

    def test_a_record_line_then_the_prune_and_no_salvage_folder(self):
        fx = self.fx
        leak = os.path.join(fx.root, "vault-law-abc123")
        _w(os.path.join(leak, "fixture.json"), "{}")
        guard = os.path.join(fx.root, "tvd-child-guard-1a2b3c4d")
        _w(os.path.join(guard, "pids"), "1")
        ent = dict(self._law(DG.ARMED), keep=(), salvage=DG.RECORD)
        rec = fx.run([ent])
        c = _cand(rec, "vault-law-abc123")
        self.assertEqual(c["state"], "pruned", c["why"])
        self.assertNotIn("tvd-child-guard-1a2b3c4d", [x["name"] for x in rec["candidates"]])
        self.assertTrue(os.path.isdir(guard))
        ev = [(m["event"], os.path.basename(m["path"]), m.get("bytes")) for m in _manifest(fx)]
        self.assertEqual(ev, [("record", "vault-law-abc123", 2), ("prune", "vault-law-abc123", 2)])
        self.assertFalse(os.path.isdir(os.path.join(fx.salv, "law-scratch")), "a law fixture got a salvage folder")

    def test_a_dry_run_records_each_folder_once(self):
        fx = self.fx
        _w(os.path.join(fx.root, "tvd-nogit-xyz", "f.txt"), "f")
        ent = dict(self._law(DG.DRY), keep=(), salvage=DG.RECORD)
        for h in (100.0, 100.5, 101.0):
            rec = fx.run([ent], now_h=h)
            self.assertEqual(_cand(rec, "tvd-nogit-xyz")["state"], "would-prune")
        self.assertEqual([m["event"] for m in _manifest(fx)], ["record"],
                         "every 30-min dry pass wrote the same record again")


class WhatCouldNotBeReadIsSaid(_Base):
    """REG-3208 review - owed vs. what was really unread; a state reset said nowhere."""

    def test_nothing_past_its_floor_needs_holders_so_owed_is_measured(self):
        self.unmerged()
        rec = self.fx.run([_entry()], now_h=0.0, held=(None, "there is no lsof on Windows and psutil is not installed"))
        self.assertEqual((rec["owed"], rec["holdersAsked"]), (0, 0), rec["say"])

    def test_a_reset_state_is_said_on_this_pass_and_the_next(self):
        os.makedirs(self.fx.salv)
        _w(os.path.join(self.fx.salv, "state.json"), "{not json")
        rec = self.fx.run([_entry()])
        self.assertIn("did not read", rec["say"])
        rec = self.fx.run([_entry()], now_h=101.0)
        self.assertIn("did not read", rec["say"], "the reset was said once and then forgotten")


RED_PROOF = [
    {"why": "v3867 - a stash's untracked files (its third parent) are not salvaged, and the prune removes the only copy",
     "file": "tv/disk_growers.py",
     "find": "        rc3, _o3, _e3 = git(path, [\"rev-parse\", \"--verify\", \"-q\", st + \"^3\"])\n        if rc3 == 0:\n",
     "replace": "        rc3, _o3, _e3 = git(path, [\"rev-parse\", \"--verify\", \"-q\", st + \"^3\"])\n        if False:\n",
     "matches": 1},
    {"why": "v3867 - a process of this user that will not answer is dropped again, and an armed prune proceeds",
     "file": "tv/disk_growers.py",
     "find": "        if mine:\n            return None, (",
     "replace": "        if False:\n            return None, (",
     "matches": 1},
    {"why": "v3867 - lsof's exit status is ignored once any process line came back",
     "file": "tv/disk_growers.py",
     "find": "    if getattr(r, \"returncode\", None) != 0:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "v3867 - the re-ask before a prune ignores the worktree's own gitdir",
     "file": "tv/disk_growers.py",
     "find": "        _gd = (c.get(\"_facts\") or {}).get(\"gitdir\") if (c.get(\"_facts\") or {}).get(\"linked\") else None\n",
     "replace": "        _gd = None\n",
     "matches": 1},
    {"why": "v3865 - a main tree whose worktrees folder will not list reads as holding none, and may be pruned",
     "file": "tv/disk_growers.py",
     "find": "            f[\"mainOf\"] = None\n",
     "replace": "            f[\"mainOf\"] = 0\n",
     "matches": 1},
    {"why": "REG-3209 - a salvage that does not read back no longer blocks the prune",
     "file": "tv/disk_growers.py",
     "find": "        if not s[\"ok\"]:\n            c.update(state=\"waiting\",",
     "replace": "        if False:\n            c.update(state=\"waiting\",",
     "matches": 1},
    {"why": "REG-3209 - the read-back compares nothing, so a short patch passes",
     "file": "tv/disk_growers.py",
     "find": "        if len(b) != rec.get(\"bytes\") or _sha(b) != rec.get(\"sha256\"):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3209 - git cherry's '+' (not upstream) is read as '-', so the unmerged commit is not saved",
     "file": "tv/disk_growers.py",
     "find": "            if ln.startswith(\"+ \"):\n",
     "replace": "            if ln.startswith(\"- \"):\n",
     "matches": 1},
    {"why": "REG-3209 - a tree whose upstream cannot be told is salvaged as if it had nothing unmerged",
     "file": "tv/disk_growers.py",
     "find": "        if c[\"_facts\"] is not None and c[\"_facts\"].get(\"why\"):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3208 - a linked worktree is removed with rmtree, so the repo's worktree list keeps naming it",
     "file": "tv/disk_growers.py",
     "find": "    if c[\"kind\"] == KIND_GIT and facts and facts.get(\"linked\"):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3208 - a tree a live process holds at measure time is salvaged (and only the late check stops it)",
     "file": "tv/disk_growers.py",
     "find": "        if _held_by(meas[0][0], real, os.path.abspath(row[\"path\"])):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3208 - a process that entered the tree during the pass is not asked about before the prune",
     "file": "tv/disk_growers.py",
     "find": "        if fresh[0] is None or _held_by(fresh[0], c[\"real\"], os.path.abspath(c[\"path\"]), _gd,\n",
     "replace": "        if False and _held_by(fresh[0], c[\"real\"], os.path.abspath(c[\"path\"]), _gd,\n",
     "matches": 1},
    {"why": "REG-3208 - holders (or an age) nobody could read is reported as a measured owed",
     "file": "tv/disk_growers.py",
     "find": "    rec[\"owed\"] = None if unknown else len(",
     "replace": "    rec[\"owed\"] = None if False else len(",
     "matches": 1},
    {"why": "REG-3208 - the age floor is gone: a tree written a minute ago is salvaged and pruned",
     "file": "tv/disk_growers.py",
     "find": "        if age_h < ent[\"floorH\"]:\n",
     "replace": "        if age_h < 0:\n",
     "matches": 1},
    {"why": "REG-3208 - an age the walk could not finish is read as old",
     "file": "tv/disk_growers.py",
     "find": "    out[\"newest\"] = newest if out[\"complete\"] else None\n",
     "replace": "    out[\"newest\"] = newest\n",
     "matches": 1},
    {"why": "REG-3208 - the dry-run deletes",
     "file": "tv/disk_growers.py",
     "find": "        if mode != ARMED:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3208 - a dry-run arms itself on its pass count alone, inside a day",
     "file": "tv/disk_growers.py",
     "find": "    if est[\"cleanPasses\"] >= ARM_AFTER_PASSES and now_s - est[\"firstCleanTs\"] >= ARM_AFTER_H * 3600:\n",
     "replace": "    if est[\"cleanPasses\"] >= ARM_AFTER_PASSES:\n",
     "matches": 1},
    {"why": "REG-3208 - the console's tree, the salvage dir and the footage are no longer protected",
     "file": "tv/disk_growers.py",
     "find": "        if any(_inside(real, g) or _inside(g, real) for g in guard):\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3208 - the main tree of linked worktrees can be pruned out from under them",
     "file": "tv/disk_growers.py",
     "find": "            if facts.get(\"mainOf\"):\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3208 - a scratch dir that holds a git repository inside is pruned as scratch",
     "file": "tv/disk_growers.py",
     "find": "        elif w[\"nestedGit\"]:\n",
     "replace": "        elif False:\n",
     "matches": 1},
    {"why": "REG-3209 - a log is salvaged whole instead of its tail",
     "file": "tv/disk_growers.py",
     "find": "                if is_log and size > LOG_TAIL:\n                    fh.seek(size - LOG_TAIL)\n",
     "replace": "                if False:\n                    fh.seek(size - LOG_TAIL)\n",
     "matches": 1},
    {"why": "REG-3208 - the salvage dir (never pruned) is no longer measured, so its own growth goes unsaid",
     "file": "tv/disk_growers.py",
     "find": "        rec[\"salvageBytes\"], rec[\"salvageAtLeast\"] = sw[\"bytes\"], not sw[\"complete\"]\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "REG-3208 - a worktree entry whose folder is gone is no longer counted, so the list's untruth goes unsaid",
     "file": "tv/disk_growers.py",
     "find": "        elif ln.startswith(\"prunable\") and cur:\n",
     "replace": "        elif False:\n",
     "matches": 1},
    {"why": "REG-3208 - the console's loop no longer asks for the growers lane",
     "file": "tv/control_app.py",
     "find": "            r = _disk_sign_once(growers=True)\n",
     "replace": "            r = _disk_sign_once()\n",
     "matches": 1},
    {"why": "REG-3208 - the sign's pass never reaches the growers lane",
     "file": "tv/control_app.py",
     "find": "    if growers:\n        _growers_pass(now)\n",
     "replace": "    if False:\n        _growers_pass(now)\n",
     "matches": 1},
    {"why": "REG-3208 - the doctor row believes a salvage the disk does not hold",
     "file": "tv/console_doctor.py",
     "find": "            if not os.path.isfile(os.path.join(root, str(last), \"meta.json\")):\n",
     "replace": "            if False:\n",
     "matches": 1},
    # ── the adversarial review's findings, each reproduced on a fixture before it was fixed ──
    {"why": "REG-3208 review (blocker) - the prune trusts the measure-time holders reading, so a shell that entered tree "
            "B after tree A's prune does not stop B's",
     "file": "tv/disk_growers.py",
     "find": "        fresh = ask()                      # REG-3208 review - asked again before EACH prune, after its own salvage\n",
     "replace": "        fresh = meas[0]\n",
     "matches": 1},
    {"why": "REG-3208 review - age is mtime only, so a folder cp -Rp made a second ago reads 240 h old and is pruned",
     "file": "tv/disk_growers.py",
     "find": "    return max(st.st_mtime, st.st_ctime)\n",
     "replace": "    return st.st_mtime\n",
     "matches": 1},
    {"why": "REG-3209 review - a merge commit (which git cherry skips) is not bundled, so the work inside it is lost",
     "file": "tv/disk_growers.py",
     "find": "    if facts.get(\"merges\"):\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3209 review - unmerged work over the salvage cap is written anyway",
     "file": "tv/disk_growers.py",
     "find": "        if total[0] + len(data) > SALVAGE_CAP:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3209 review - a diff whose files sum past the read cap is read into memory anyway",
     "file": "tv/disk_growers.py",
     "find": "        if b > READ_CAP:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3208 review - a salvage is written that leaves the salvage disk under its floor",
     "file": "tv/disk_growers.py",
     "find": "    if rm[\"free\"] - rm[\"spent\"] - n < SALVAGE_MIN_FREE:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3208 review - the salvage dir (never pruned) takes salvages past its cap",
     "file": "tv/disk_growers.py",
     "find": "    if _num(rm[\"dir\"]) and rm[\"dir\"] + rm[\"spent\"] + n > SALVAGE_DIR_CAP:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3208 review - one tree without origin/main resets its whole entry's dry-run, so the entry never arms",
     "file": "tv/disk_growers.py",
     "find": "            rec[\"waiting\"].append({\"name\": c[\"name\"], \"entry\": ent[\"name\"], \"why\": c[\"_facts\"][\"why\"]})\n",
     "replace": "            rec[\"waiting\"].append({\"name\": c[\"name\"], \"entry\": ent[\"name\"], \"why\": c[\"_facts\"][\"why\"]})\n"
                "            outcome[ent[\"name\"]] = \"failed\"\n",
     "matches": 1},
    {"why": "REG-3208 review - one tree over the salvage cap (a declared refusal) resets its entry's dry-run",
     "file": "tv/disk_growers.py",
     "find": "            if not s[\"blocked\"]:\n",
     "replace": "            if True:\n",
     "matches": 1},
    {"why": "REG-3208 review - an untracked nested repo is not seen as one, so it waits for the wrong reason",
     "file": "tv/disk_growers.py",
     "find": "    f[\"nested\"] = [n for n in names if n.endswith(\"/\")]\n",
     "replace": "    f[\"nested\"] = []\n",
     "matches": 1},
    {"why": "REG-3208 review - the per-user temp dir, where the laws leak, is not a root",
     "file": "tv/disk_growers.py",
     "find": "    return {\"TMP\": tmp, \"TMPDIR\": (env.get(\"TMPDIR\") or tmp).rstrip(\"/\") or \"/\"}\n",
     "replace": "    return {\"TMP\": tmp}\n",
     "matches": 1},
    {"why": "REG-3208 review - a RECORD entry (law fixtures) gets a salvage folder each, and the salvage dir grows by them",
     "file": "tv/disk_growers.py",
     "find": "    if entry.get(\"salvage\") == RECORD:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3208 review - every 30-minute dry pass records the same law fixture again",
     "file": "tv/disk_growers.py",
     "find": "    if recorded is not None and recorded.get(c[\"path\"]) == fp:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3208 review - a PC with nothing past its floor and no psutil reads owed UNKNOWN forever",
     "file": "tv/disk_growers.py",
     "find": "    rec[\"owed\"] = None if unknown else len(",
     "replace": "    rec[\"owed\"] = None if (unknown or meas[0] is None or meas[0][0] is None) else len(",
     "matches": 1},
    {"why": "REG-3208 review - a pass is unbounded: every due grower is handled in one pass, none deferred or owed",
     "file": "tv/disk_growers.py",
     "find": "        if handled >= PRUNES_PER_PASS or _now() - t0 > budget_s:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3208 review - a state reset (every entry back in dry-run) is said nowhere",
     "file": "tv/disk_growers.py",
     "find": "    if rec.get(\"stateWhy\"):\n        parts.append(rec[\"stateWhy\"])\n",
     "replace": "    if False:\n        parts.append(rec[\"stateWhy\"])\n",
     "matches": 1},
    {"why": "REG-3208 review - a state reset is said on its own pass and forgotten on the next",
     "file": "tv/disk_growers.py",
     "find": "        fresh.update(resetWhy=why)\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "REG-3208 review - a lane that only WAITED for a day reads OK with day-old sizes",
     "file": "tv/console_doctor.py",
     "find": "    if now - ran > GROWERS_UNMEASURED_H * 3600 * 1000:\n",
     "replace": "    if False:\n",
     "matches": 1},
    {"why": "REG-3208 review - the row shows the top growers without the age of the reading",
     "file": "tv/console_doctor.py",
     "find": "    top += \" (measured %d min ago)\" % age_m\n",
     "replace": "    pass\n",
     "matches": 1},
    {"why": "REG-3208 review - the row never says a state reset",
     "file": "tv/console_doctor.py",
     "find": "    sw = (\" - \" + str(g.get(\"stateWhy\"))[:160]) if g.get(\"stateWhy\") else \"\"\n",
     "replace": "    sw = \"\"\n",
     "matches": 1},
    {"why": "REG-3208 - the doctor row never says the lane's loop stopped",
     "file": "tv/console_doctor.py",
     "find": "    if now - seen > GROWERS_STALE_S * 1000:\n",
     "replace": "    if False:\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
