# -*- coding: utf-8 -*-
"""v3888 (REG-3478) - OUR SCRATCH IS COLLECTED ON WINDOWS TOO: A SANDBOX'S CHILD-GUARD LEDGER LEAVES WITH IT, THE OLD ONES ARE
COLLECTED ON PROOF, AND THE CHARACTER READER'S CROP DIRS DO NOT STRAND.

The doctor's row "our scratch is collected" on Dean's PC, 11-08: "219 of 296 scratch director(ies) WE made are older than 3 days -
oldest 105.0 days". MEASURED there (read-only): 189 tvd-child-guard-<hash> (153 old, the newest that same afternoon), 23 heartlane_
(none newer than 10-21), 15 tvd-nogit, 10 tvd-cs (the newest that morning), 2 tvd-par-dirty - all of them ours (his repo dates from
07-17). macOS ages its temp dir out after three days; Windows never touches %TEMP%. Three sources were still minting:
  * child_guard names its ledger dir by a hash of the tree's path, so every sandbox a proof copied the tree into made its own
    and nothing removed it -> run_gates.law_env (every gate, the pre-flight, every sandboxed proof) hands each gate a ledger dir
    under the run's own scratch, removed at exit;
  * the ones already there -> child_guard.collect_stale_ledger_dirs, from the console's rescue tick at most every 6 h: another
    tree's dir is removed only when every file is 3 days old and every parent and child it records is gone or a newer process -
    alive with an UNKNOWN birth, or a pid that cannot be asked, keeps it; this console's own dir is never touched; a sandbox's
    console (TV_CHILD_GUARD_DIR handed in) never collects;
  * char_select's crop dir was removed with rmtree(ignore_errors=True), which fails SILENTLY on Windows while a reader holds a
    crop open (g5_grok_eyes' REG-1687) -> retried and a leftover counted, and the console's own tick sweeps earlier ticks' dirs
    by their prefix past an hour (a law that hands its own hist never reaches the machine's temp dir).
tvd-nogit / tvd-par-dirty are disk_growers' law-scratch-win (declared, graduating); heartlane_ stopped minting 10-21.
Fixtures only (contained temp, fake process tables). RED_PROOF below. [[heart-first]] [[unknown-stays-unknown]]
"""
import inspect
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import child_guard as cg  # noqa: E402
import char_select as cs  # noqa: E402
import run_gates as rg  # noqa: E402

NOW = 1_800_000_000.0
OLD = NOW - 4 * 86400
YOUNG = NOW - 3600


def _ledger_dir(root, name, body, mtime):
    d = os.path.join(root, "tvd-child-guard-" + name)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "%d.json" % int(body.get("parent") or 1))
    with open(p, "w", encoding="utf-8") as fh:
        if isinstance(body, dict) and body.get("_raw") is not None:
            fh.write(body["_raw"])
        else:
            json.dump(body, fh)
    os.utime(p, (mtime, mtime))
    os.utime(d, (mtime, mtime))
    return d


class AGateKeepsItsLedgerInTheRunsScratch(unittest.TestCase):

    def test_every_gate_gets_a_ledger_dir_that_leaves_with_the_run(self):
        env = rg.law_env(False, {"PATH": os.environ.get("PATH", "")})
        d = env.get("TV_CHILD_GUARD_DIR")
        self.assertTrue(d, "a gate's child guard keeps its ledger in %TEMP% keyed by the tree again - one dir per sandbox")
        self.assertEqual(os.path.dirname(d), rg._LAW_LEDGER["dir"], "the dir is not under the run's own scratch (removed at exit)")
        self.assertNotEqual(rg.law_env(False, {})["TV_CHILD_GUARD_DIR"], d, "two gates share one ledger dir")
        self.assertEqual(rg.law_env(False, {"TV_CHILD_GUARD_DIR": "/x/mine"})["TV_CHILD_GUARD_DIR"], "/x/mine",
                         "a caller's own dir was overridden")
        # v3897 (REG-3696) - the run's dir names its owner, so a run that was killed before its atexit can be collected
        self.assertTrue(os.path.basename(rg._LAW_LEDGER["dir"]).startswith("%s%d-" % (rg.LAW_LEDGER_PREFIX, os.getpid())),
                        "the run's ledger dir does not name its owner: %s" % rg._LAW_LEDGER["dir"])


class AKilledRunsLedgerDirIsTakenByTheNextRun(unittest.TestCase):
    """* v3897 (REG-3696) THE POINT - MEASURED 11-11 on his Mac: 37 tvd-gate-ledgers-* dirs, 8 older than 3 days (the doctor's
    "our scratch is collected" MISSING). atexit never runs for a KILLED run (a law past its timeout, a prover stood aside with
    SIGTERM). The next run removes a dir only when its name carries an owner pid that is not alive."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="rg-ledger-sweep-law-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.d = {}
        for key, nm in (("dead", "%s11-a" % rg.LAW_LEDGER_PREFIX), ("live", "%s22-b" % rg.LAW_LEDGER_PREFIX),
                        ("unknown", "%s33-c" % rg.LAW_LEDGER_PREFIX), ("own", "%s44-d" % rg.LAW_LEDGER_PREFIX),
                        ("legacy", "%sx7q2" % rg.LAW_LEDGER_PREFIX), ("other", "tvd-other-11-e")):
            self.d[key] = os.path.join(self.root, nm)
            os.makedirs(os.path.join(self.d[key], "child_guard_1"))
        # 44 (own) reads NOT alive on purpose: only the own-pid rule may keep the running process's dir - had the probe
        # answered alive, the own rule would decide nothing and its red-proof would stay green (BLIND, measured 11-11)
        self.alive = lambda pid: {11: False, 22: True, 33: None, 44: False}.get(pid, True)

    def test_only_a_dead_owners_dir_is_removed(self):
        n = rg.sweep_dead_law_ledgers(root=self.root, alive=self.alive, own=44)
        gone = sorted(k for k, p in self.d.items() if not os.path.exists(p))
        self.assertEqual(gone, ["dead"], "the sweep removed %r - only a dir whose owner is provably gone may go" % gone)
        self.assertEqual(n, 1)

    def test_an_unlistable_root_is_unknown_never_zero(self):
        self.assertIsNone(rg.sweep_dead_law_ledgers(root=os.path.join(self.root, "nope"), alive=self.alive, own=44))

    def test_a_pidless_dir_older_than_a_day_is_collected(self):
        """REG-3771 (11-12) - tvd-gate-ledgers-iq0fktsv, made before v3897, named no owner and sat 3.3 days: kept forever"""
        t = os.stat(self.d["legacy"]).st_mtime
        n = rg.sweep_dead_law_ledgers(root=self.root, alive=self.alive, own=44, now=t + rg.LEGACY_LEDGER_AGE_S - 60)
        self.assertTrue(os.path.exists(self.d["legacy"]), "a pidless dir under a day old was taken - it may be a live run's")
        self.assertEqual(n, 1)
        n = rg.sweep_dead_law_ledgers(root=self.root, alive=self.alive, own=44, now=t + rg.LEGACY_LEDGER_AGE_S + 60)
        self.assertFalse(os.path.exists(self.d["legacy"]), "a pidless dir older than a day is still kept forever")
        self.assertTrue(os.path.exists(self.d["other"]), "a dir that is not a ledger dir was taken")
        self.assertEqual(n, 1)

    def test_the_visual_laws_drop_their_shots_per_run(self):
        """REG-3771 - two visual laws wrote into a FIXED tvd-artifacts/<tag> in his temp dir and never removed it"""
        for fn in ("test_v3767_copy_witness_visual.py", "test_v3771_vault_console_face_visual.py"):
            raw = io.open(os.path.join(HERE, fn), encoding="utf-8").read()
            code = "\n".join(l.split("#", 1)[0] for l in raw.split("\n"))
            self.assertEqual(code.count('d = _t.mkdtemp(prefix="tvd-artifacts-%s-" % tag)'), 1, fn)
            self.assertEqual(code.count("_ae.register(_sh.rmtree, d, True)"), 1, "%s: the drop is not removed at exit" % fn)
            self.assertNotIn('"tvd-artifacts", tag)', code, "%s writes into the fixed drop again" % fn)

    def test_a_new_run_asks_the_sweep_first(self):
        src = inspect.getsource(rg._law_ledger_path)
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        self.assertEqual(code.count("sweep_dead_law_ledgers()"), 1, "a new run no longer takes what killed runs left")
        self.assertLess(code.index("sweep_dead_law_ledgers()"), code.index("tempfile.mkdtemp("))


class OldLedgerDirsAreCollectedOnProof(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cg-collect-law-")
        self.saved = (cg.LEDGER_DIR, dict(cg.COLLECT), list(cg._COLLECT_AT))
        cg.LEDGER_DIR = os.path.join(self.root, "tvd-child-guard-OWN")
        cg.COLLECT.update(on=True, removed=0, worked=None)
        # pids: 10 gone, 20 alive born 500, 30 alive born 999 (a reuse of a pid recorded born 300), 40 alive birth UNKNOWN
        self.alive = lambda pid: pid in (20, 30, 40)
        self.birth = lambda pid: {20: 500, 30: 999, 40: None}.get(pid)
        self.d = {
            "dead": _ledger_dir(self.root, "dead", {"parent": 10, "parentBirth": 100, "children": {}}, OLD),
            "liveparent": _ledger_dir(self.root, "liveparent", {"parent": 20, "parentBirth": 500, "children": {}}, OLD),
            "livechild": _ledger_dir(self.root, "livechild", {"parent": 10, "parentBirth": 100,
                                                              "children": {"capture": {"pid": 20, "birth": 500}}}, OLD),
            "reused": _ledger_dir(self.root, "reused", {"parent": 30, "parentBirth": 300, "children": {}}, OLD),
            "unknownbirth": _ledger_dir(self.root, "unknownbirth", {"parent": 40, "parentBirth": 400, "children": {}}, OLD),
            "young": _ledger_dir(self.root, "young", {"parent": 10, "parentBirth": 100, "children": {}}, YOUNG),
            "own": _ledger_dir(self.root, "OWN", {"parent": 10, "parentBirth": 100, "children": {}}, OLD),
            "unreadable": _ledger_dir(self.root, "unreadable", {"parent": 11, "_raw": "{not json"}, OLD),
        }
        self.other = os.path.join(self.root, "tvd-cs-notmine")
        os.makedirs(self.other)
        os.utime(self.other, (OLD, OLD))

    def tearDown(self):
        cg.LEDGER_DIR, c, at = self.saved
        cg.COLLECT.clear()
        cg.COLLECT.update(c)
        cg._COLLECT_AT[:] = at
        shutil.rmtree(self.root, ignore_errors=True)

    def _run(self, **kw):
        return cg.collect_stale_ledger_dirs(now=NOW, alive=self.alive, birth=self.birth, root=self.root, **kw)

    def test_premise_every_case_is_on_disk(self):
        self.assertTrue(all(os.path.isdir(p) for p in self.d.values()))

    def test_only_provable_litter_is_removed(self):
        """* THE POINT - gone or a newer process: removed; anything that may still be theirs, young, our own or unread: kept"""
        r = self._run()
        gone = sorted(k for k, p in self.d.items() if not os.path.exists(p))
        self.assertEqual(gone, ["dead", "reused"], "the collector removed %r" % gone)
        self.assertTrue(os.path.isdir(self.other), "a dir of another prefix was touched")
        self.assertEqual((r["kept"], r["left"], r["owed"]), (4, 0, 0), r)
        self.assertTrue(r["worked"])
        self.assertIn("2 stale ledger dir(s) of other trees removed", r["say"])

    def test_a_dir_that_will_not_go_is_counted_and_owed(self):
        r = self._run(remove=lambda p: None)
        self.assertEqual((r["left"], r["owed"]), (2, 2), "a dir that would not go read as removed")
        self.assertTrue(os.path.isdir(self.d["dead"]))

    def test_an_unlistable_root_is_unknown_never_zero(self):
        r = cg.collect_stale_ledger_dirs(now=NOW, alive=self.alive, birth=self.birth, root=os.path.join(self.root, "nope"))
        self.assertEqual((r["worked"], r["owed"]), (None, None))
        self.assertIn("UNKNOWN", r["say"])

    def test_it_runs_when_due_and_never_in_a_sandbox(self):
        with mock.patch.object(cg, "collect_stale_ledger_dirs", lambda **k: {"ran": True}):
            cg._COLLECT_AT[:] = [None]
            self.assertEqual(cg.collect_if_due(now=NOW), {"ran": True})
            self.assertIsNone(cg.collect_if_due(now=NOW + 60), "it ran again a minute later - the throttle is gone")
            self.assertEqual(cg.collect_if_due(now=NOW + cg.COLLECT_EVERY_S + 1), {"ran": True})
            cg.COLLECT["on"] = False
            cg._COLLECT_AT[:] = [None]
            self.assertIsNone(cg.collect_if_due(now=NOW), "a sandbox's console collected his temp dir")


class TheConsoleAsksTheCollector(unittest.TestCase):

    def test_the_rescue_tick_runs_it_and_status_carries_its_receipt(self):
        import control_app as ca
        src = inspect.getsource(ca._child_guard_tick)
        self.assertIn("_child_guard.collect_if_due(alive=_pid_alive)", src, "nothing collects the stale ledger dirs")
        self.assertIn("collect", cg.status())
        self.assertFalse(cg.COLLECT["on"] and os.environ.get("TV_CHILD_GUARD_DIR"), "PREMISE: a law's process would collect")


class TheCharacterReadersCropsDoNotStrand(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cs-sweep-law-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _mk(self, name, mtime):
        p = os.path.join(self.root, name)
        os.makedirs(p)
        os.utime(p, (mtime, mtime))
        return p

    def test_earlier_ticks_dirs_are_swept_by_prefix_and_age(self):
        old, fresh, other = self._mk("tvd-cs-old1", OLD), self._mk("tvd-cs-fresh", NOW - 60), self._mk("tvd-child-guard-x", OLD)
        self.assertEqual(cs._sweep_stale_scratch(root=self.root, now=NOW), (1, 0))
        self.assertEqual([os.path.exists(p) for p in (old, fresh, other)], [False, True, True],
                         "a concurrent tick's fresh dir or another prefix was swept, or the old one stayed")
        self.assertIsNone(cs._sweep_stale_scratch(root=os.path.join(self.root, "nope"), now=NOW), "an unlistable dir read as 0 swept")

    def test_a_crop_dir_that_will_not_go_is_said_never_pretended(self):
        p = self._mk("tvd-cs-stuck", NOW)
        with mock.patch.object(cs.shutil, "rmtree", lambda *a, **k: None):
            self.assertFalse(cs._clean_scratch_dir(p, attempts=3, sleep=lambda s: None), "a dir that stayed read as gone")
        self.assertTrue(cs._clean_scratch_dir(p, attempts=3, sleep=lambda s: None))
        self.assertFalse(os.path.exists(p))

    def test_only_the_consoles_own_tick_sweeps(self):
        src = inspect.getsource(cs.tick)
        self.assertIn("_console_tick = root is None", src)
        self.assertIn("_cs_gone = _sweep_stale_scratch(now=now_s) if _console_tick else None", src)
        self.assertIn("if not _clean_scratch_dir(work):", src, "the tick's own crop dir is removed silently again")


class AProofImportLeavesNoScratch(unittest.TestCase):
    """REG-3798 (the doctor on the OLD PC ALT, 11-12: 43 of 83 of our temp dirs older than 3 days, 7 of them
    tvd-proof-release-) - an import's scratch went in a finally with rmtree(ignore_errors=True), silent on Windows while
    heart2's key workers hold a file, and never at all when the console died mid-import. REG-3797 - the same row told that
    Windows PC "macOS's own policy is three days"."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tvd-scratch-law-")
        self.addCleanup(shutil.rmtree, self.root, True)

    def _mk(self, name, mtime):
        p = os.path.join(self.root, name)
        os.makedirs(p)
        os.utime(p, (mtime, mtime))
        return p

    def test_an_earlier_imports_leftover_is_swept_and_a_live_one_is_not(self):
        import proof_release as PR
        stale = NOW - PR.PROOF_SCRATCH_STALE_S - 60
        old = self._mk("tvd-proof-release-old1", stale)
        live = self._mk("tvd-proof-release-live", NOW - 5400)          # an import still inside its own bound
        crop = self._mk("tvd-cs-old1", OLD)                            # another lane's prefix
        self.assertEqual(PR.sweep_old_imports(root=self.root, now=NOW), (1, 0))
        self.assertEqual([os.path.exists(x) for x in (old, live, crop)], [False, True, True],
                         "a live import's dir or another prefix was swept, or the leftover stayed")

    def test_the_import_sweeps_first_and_removes_its_own_dir_through_the_retried_remove(self):
        import proof_release as PR
        old = self._mk("tvd-proof-release-old2", NOW - PR.PROOF_SCRATCH_STALE_S - 60)
        dropped = []
        real = cs._clean_scratch_dir

        def _drop(path, *a, **k):
            dropped.append(os.path.basename(path))
            return real(path, *a, **k)
        with mock.patch.object(tempfile, "tempdir", self.root), mock.patch.object(cs, "_clean_scratch_dir", _drop), \
                mock.patch.object(PR.time, "time", lambda: NOW):
            out = PR.import_bundle("0" * 40, tv_dir=self.root, urlopen=lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
        self.assertNotEqual(out.get("state"), "imported", "PREMISE: the fake download imported something")
        self.assertFalse(os.path.exists(old), "the earlier import's leftover was not swept")
        own = [n for n in dropped if n.startswith(PR.PROOF_SCRATCH_PREFIX) and n != "tvd-proof-release-old2"]
        self.assertEqual(len(own), 1, "the import's own dir did not go through the retried remove: %r" % dropped)
        # a literal prefix (the unkeyable-laws ratchet keys a listing by its constant), pinned to the module's own
        self.assertEqual(PR.PROOF_SCRATCH_PREFIX, "tvd-proof-release-")
        self.assertEqual([n for n in os.listdir(self.root) if n.startswith("tvd-proof-release-")], [])
        self.assertIs(out.get("scratchLeft"), False)

    def test_the_row_names_this_pcs_own_os(self):
        import console_doctor as CD
        self._mk("tmpREG3797old", OLD)
        with mock.patch.object(tempfile, "tempdir", self.root), mock.patch.object(CD.time, "time", lambda: NOW):
            win = CD._check_nothing_we_made_is_still_on_his_disk_days_later(_platform="win32")
            mac = CD._check_nothing_we_made_is_still_on_his_disk_days_later(_platform="darwin")
        self.assertIn("older than 3 days", win[1], "PREMISE: the planted old dir was not counted: %r" % (win,))
        self.assertIn("Windows never clears its temp folder", win[1])
        self.assertNotIn("macOS", win[1], "a Windows PC was told about macOS's policy")
        self.assertIn("macOS's own policy is three days", mac[1])


RED_PROOF = [
    {"why": "REG-3798 - a proof import no longer sweeps earlier imports' leftovers (they pile up on Windows)",
     "file": "tv/proof_release.py",
     "find": "    out[\"swept\"] = sweep_old_imports()",
     "replace": "    out[\"swept\"] = None",
     "matches": 1},
    {"why": "REG-3798 - an import's own dir goes through a silent rmtree again",
     "file": "tv/proof_release.py",
     "find": "        out[\"scratchLeft\"] = not _drop_scratch(d)",
     "replace": "        out[\"scratchLeft\"] = shutil.rmtree(d, ignore_errors=True)",
     "matches": 1},
    {"why": "REG-3798 - the shared sweep ignores the prefix it is handed (an import's dirs are never matched)",
     "file": "tv/char_select.py",
     "find": "        names = [n for n in os.listdir(root) if n.startswith(prefix)]",
     "replace": "        names = [n for n in os.listdir(root) if n.startswith(CS_SCRATCH_PREFIX)]",
     "matches": 1},
    {"why": "REG-3797 - a Windows PC's scratch row talks about macOS's policy again",
     "file": "tv/console_doctor.py",
     "find": "        _os_word = (\"Windows never clears its temp folder on its own\" if str(_platform or sys.platform).startswith(\"win\")",
     "replace": "        _os_word = (\"Windows never clears its temp folder on its own\" if False",
     "matches": 1},
    {"why": "REG-3771 - a pidless (pre-v3897) ledger dir is kept forever again and the doctor row stays MISSING",
     "file": "tv/run_gates.py",
     "find": "                if now - os.stat(p).st_mtime <= LEGACY_LEDGER_AGE_S:\n",
     "replace": "                if True:\n",
     "matches": 1},
    {"why": "REG-3771 - the v3767 visual law's drop is not removed at exit",
     "file": "tv/test_v3767_copy_witness_visual.py",
     "find": "    _ae.register(_sh.rmtree, d, True)\n",
     "replace": "    pass\n",
     "matches": 1},
    {"why": "v3897 (REG-3696) - the sweep removes a dir whose owner is alive or cannot be asked",
     "file": "tv/run_gates.py",
     "find": "            if alive(int(m.group(1))) is not False:\n",
     "replace": "            if alive(int(m.group(1))) is True and False:\n",
     "matches": 1},
    {"why": "v3897 (REG-3696) - the sweep removes the running process's own dir",
     "file": "tv/run_gates.py",
     "find": "        if not m or int(m.group(1)) == own:\n",
     "replace": "        if not m:\n",
     "matches": 1},
    {"why": "v3897 (REG-3696) - the run's ledger dir stops naming its owner, so a killed run's dir is never collected",
     "file": "tv/run_gates.py",
     "find": "        _LAW_LEDGER[\"dir\"] = tempfile.mkdtemp(prefix=\"%s%d-\" % (LAW_LEDGER_PREFIX, os.getpid()))\n",
     "replace": "        _LAW_LEDGER[\"dir\"] = tempfile.mkdtemp(prefix=LAW_LEDGER_PREFIX)\n",
     "matches": 1},
    {"why": "v3897 (REG-3696) - a new run no longer takes what killed runs left",
     "file": "tv/run_gates.py",
     "find": "            sweep_dead_law_ledgers()                       # v3897 (REG-3696) - what killed runs left behind\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "v3888 (REG-3478) - a gate's child guard keeps its ledger in %TEMP% keyed by the tree again (one dir per sandbox)",
     "file": "tv/run_gates.py",
     "find": "        env[\"TV_CHILD_GUARD_DIR\"] = _law_ledger_path(\"child_guard\")[:-len(\".json\")]\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "v3888 (REG-3478) - the collector removes a dir whose process may still be alive",
     "file": "tv/child_guard.py",
     "find": "            if any(_still_here(pid, born, alive, birth) for pid, born in recs):\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "v3888 (REG-3478) - the collector removes a young dir",
     "file": "tv/child_guard.py",
     "find": "        if now - newest < STALE_LEDGER_DIR_S:\n            continue\n",
     "replace": "        if False:\n            continue\n",
     "matches": 1},
    {"why": "v3888 (REG-3478) - the collector removes this console's own ledger dir",
     "file": "tv/child_guard.py",
     "find": "        if os.path.normcase(os.path.abspath(p)) == own or not os.path.isdir(p):\n",
     "replace": "        if not os.path.isdir(p):\n",
     "matches": 1},
    {"why": "v3888 (REG-3478) - nothing asks the collector",
     "file": "tv/control_app.py",
     "find": "        _child_guard.collect_if_due(alive=_pid_alive)\n",
     "replace": "        pass\n",
     "matches": 1},
    {"why": "v3888 (REG-3478) - the crop sweep takes a concurrent tick's fresh dir",
     "file": "tv/char_select.py",
     "find": "            if not os.path.isdir(p) or now - os.path.getmtime(p) < stale_s:\n",
     "replace": "            if not os.path.isdir(p):\n",
     "matches": 1},
    {"why": "v3888 (REG-3478) - a crop dir that stayed reads as removed",
     "file": "tv/char_select.py",
     "find": "        if not os.path.exists(path):\n            return True\n        if k + 1 < attempts:\n            sleep(pause_s)\n    return False\n",
     "replace": "        if not os.path.exists(path):\n            return True\n        if k + 1 < attempts:\n            sleep(pause_s)\n    return True\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
