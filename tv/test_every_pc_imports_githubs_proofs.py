# -*- coding: utf-8 -*-
"""v3862 - EVERY PC IMPORTS GITHUB'S PROOFS FOR ITS OWN COMMIT FROM THE PROOF BANK, AND TAKES NOTHING ELSE FROM IT.

His ruling 2026-11-05 (the normal model): GitHub proves each version once; each PC imports those proofs instead of
proving 1,500 laws again. The proof-keys workflow's proof-bank job packs a whole, fan-in-checked set of shard caches
into proofs-<sha>.tgz on one public release; the console's proof-release tick downloads its own commit's bundle and
hands it to heart2 --import-shards (all or nothing, REG-2586). The import is how a law gets marked PROVEN on a PC it
never ran on, so every way it could take the wrong thing is pinned:
  · the unpack takes ONLY proof-shard-<k>/.heart2_cache.json regular files - a link, a `..`, an absolute path, a stray
    file or an oversize member refuses the WHOLE bundle;
  · a 404 is ABSENT (asked again), a failed read is UNKNOWN (asked again), neither is ever "imported";
  · a commit already imported or refused is not asked again; another commit is;
  · the console waits for a push grading here, the local game, and a tracked-dirty tree; the self-prove tick holds
    while an import runs (and still sends its first beacon);
  · only the bank job may write to the repo, it runs only on a whole set, packs only shard caches, and never fails
    Publish's deploy.
Driven over stand-in downloads, tarballs and git - no network, no live heart2 store.
"""
import io
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import shutil
import unittest
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import proof_release as PR  # noqa: E402

SHA = "c" * 40
OTHER = "d" * 40


def _tgz(path, members):
    """members: [(name, bytes) | (name, ("link", target))]"""
    with tarfile.open(path, "w:gz") as tf:
        for name, body in members:
            ti = tarfile.TarInfo(name)
            if isinstance(body, tuple):
                ti.type, ti.linkname = tarfile.SYMTYPE, body[1]
                tf.addfile(ti)
            else:
                ti.size = len(body)
                tf.addfile(ti, io.BytesIO(body))


class _Tmp(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="test-proof-release-")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)


class TheUnpackTakesOnlyShardCaches(_Tmp):

    def _x(self, members):
        b = os.path.join(self.d, "b.tgz")
        _tgz(b, members)
        return PR.safe_extract(b, os.path.join(self.d, "out"))

    def test_a_whole_set_is_taken(self):
        paths, why = self._x([("proof-shard-1/.heart2_cache.json", b"{}"), ("./proof-shard-2/.heart2_cache.json", b"{}")])
        self.assertIsNone(why)
        self.assertEqual([os.path.relpath(p, os.path.join(self.d, "out")) for p in paths],
                         [os.path.join("proof-shard-1", ".heart2_cache.json"),
                          os.path.join("proof-shard-2", ".heart2_cache.json")])

    def test_a_stray_file_refuses_the_whole_bundle(self):
        paths, why = self._x([("proof-shard-1/.heart2_cache.json", b"{}"), ("proof-shard-1/prove.log", b"x")])
        self.assertIsNone(paths, "a file that is not a shard cache was taken out of the bundle")
        self.assertIn("not a shard cache", why)
        self.assertFalse(os.path.exists(os.path.join(self.d, "out")), "something was written before the refusal")

    def test_a_path_out_of_the_folder_refuses(self):
        for name in ("../proof-shard-1/.heart2_cache.json", "/etc/proof-shard-1/.heart2_cache.json",
                     "proof-shard-1/../../.heart2_cache.json"):
            with self.subTest(name=name):
                paths, why = self._x([(name, b"{}")])
                self.assertIsNone(paths, "%s was unpacked" % name)

    def test_a_link_refuses_as_a_link(self):
        paths, why = self._x([("proof-shard-1/.heart2_cache.json", ("link", "/etc/passwd"))])
        self.assertIsNone(paths)
        self.assertIn("not a plain file", why, "a link was not refused for being a link")

    def test_an_oversize_member_refuses(self):
        saved = PR.MAX_FILE_BYTES
        PR.MAX_FILE_BYTES = 4
        try:
            paths, why = self._x([("proof-shard-1/.heart2_cache.json", b"0123456789")])
        finally:
            PR.MAX_FILE_BYTES = saved
        self.assertIsNone(paths)
        self.assertIn("over the cap", why)

    def test_not_a_tarball_refuses(self):
        b = os.path.join(self.d, "b.tgz")
        io.open(b, "wb").write(b"<html>not found</html>")
        paths, why = PR.safe_extract(b, os.path.join(self.d, "out"))
        self.assertIsNone(paths)


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class TheDownloadSaysWhatHappened(_Tmp):

    def test_the_url_names_this_commit_in_the_bank(self):
        self.assertEqual(PR.asset_url(SHA), "https://github.com/KonyoDigital/d2r-bible-tests/releases/download/"
                                            "proof-bank/proofs-%s.tgz" % SHA)

    def test_a_404_is_absent(self):
        def op(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
        got, why = PR.download(SHA, os.path.join(self.d, "b"), urlopen=op)
        self.assertEqual(got, "absent", why)

    def test_another_answer_or_no_network_is_unknown(self):
        def e500(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 500, "x", {}, None)

        def down(req, timeout=None):
            raise OSError("no route")
        for op in (e500, down):
            with self.subTest(op=op.__name__):
                self.assertEqual(PR.download(SHA, os.path.join(self.d, "b"), urlopen=op)[0], "unknown")

    def test_a_read_is_ok_and_a_bundle_past_the_cap_is_not(self):
        def op(req, timeout=None):
            self.assertIn(SHA, req.full_url)
            return _Resp(b"x" * 100)
        self.assertEqual(PR.download(SHA, os.path.join(self.d, "b"), urlopen=op)[0], "ok")
        self.assertEqual(PR.download(SHA, os.path.join(self.d, "b"), urlopen=op, max_bytes=10)[0], "unknown")

    def test_no_full_commit_id_is_never_asked(self):
        def op(req, timeout=None):
            raise AssertionError("asked GitHub about %r" % req.full_url)
        self.assertEqual(PR.download("abc", os.path.join(self.d, "b"), urlopen=op)[0], "unknown")


class TheImport(_Tmp):

    def _bundle_op(self, members):
        b = os.path.join(self.d, "src.tgz")
        _tgz(b, members)
        data = io.open(b, "rb").read()
        return lambda req, timeout=None: _Resp(data)

    def test_a_whole_set_is_handed_to_heart2_at_low_priority(self):
        seen = {}

        def run(argv, **kw):
            seen["argv"], seen["kw"] = list(argv), kw
            return subprocess.CompletedProcess(argv, 0, "  ✓ REG-2586 IMPORTED 1 shard(s) of HEAD cccc", "")
        r = PR.import_bundle(SHA, tv_dir=HERE, run=run,
                             urlopen=self._bundle_op([("proof-shard-1/.heart2_cache.json", b"{}")]))
        self.assertEqual(r["state"], "imported", r)
        self.assertIn("REG-2586 IMPORTED", r["why"])
        self.assertIn("--import-shards", seen["argv"])
        self.assertTrue(seen["argv"][-1].endswith(os.path.join("proof-shard-1", ".heart2_cache.json")))
        if os.name == "nt":
            self.assertEqual(seen["kw"].get("creationflags", 0) & 0x00004000, 0x00004000, "the import runs at full priority")
        else:
            self.assertIn("nice", os.path.basename(seen["argv"][0]), "the import runs at full priority")

    def test_heart2_refusing_is_refused(self):
        def run(argv, **kw):
            return subprocess.CompletedProcess(argv, 2, "  ✗ REG-2586 IMPORT REFUSED: a partial set", "")
        r = PR.import_bundle(SHA, tv_dir=HERE, run=run,
                             urlopen=self._bundle_op([("proof-shard-1/.heart2_cache.json", b"{}")]))
        self.assertEqual(r["state"], "refused")
        self.assertIn("partial set", r["why"])

    def test_an_absent_or_refused_bundle_never_reaches_heart2(self):
        def run(argv, **kw):
            raise AssertionError("heart2 was asked to import %r" % (argv,))

        def absent(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
        self.assertEqual(PR.import_bundle(SHA, tv_dir=HERE, run=run, urlopen=absent)["state"], "absent")
        r = PR.import_bundle(SHA, tv_dir=HERE, run=run, urlopen=self._bundle_op([("evil.sh", b"rm -rf /")]))
        self.assertEqual(r["state"], "refused")


class WhenACommitIsOwed(unittest.TestCase):

    def test_owed(self):
        M = "darwin"
        self.assertTrue(PR.owed({}, SHA, M))
        self.assertTrue(PR.owed({"sha": OTHER, "state": "imported"}, SHA, M), "another commit's import vouched for this one")
        self.assertFalse(PR.owed({"sha": SHA, "state": "imported"}, SHA, M))
        self.assertFalse(PR.owed({"sha": SHA, "state": "refused"}, SHA, M))
        self.assertTrue(PR.owed({"sha": SHA, "state": "absent"}, SHA, M), "an absent bundle was never asked again")
        self.assertTrue(PR.owed({"sha": SHA, "state": "unknown"}, SHA, M))
        self.assertFalse(PR.owed({}, "not-a-sha", M))

    def test_a_windows_pc_wants_the_windows_set(self):
        W = "win32"
        self.assertEqual(PR.flavors(W), ("win32", ""))
        self.assertEqual(PR.asset_name(SHA, "win32"), "proofs-%s-win32.tgz" % SHA)
        self.assertTrue(PR.owed({"sha": SHA, "state": "imported", "imported": [""]}, SHA, W),
                        "a Windows PC that took the Linux set stopped asking for the Windows one")
        self.assertFalse(PR.owed({"sha": SHA, "state": "imported", "imported": ["", "win32"]}, SHA, W))

    def test_the_best_set_first_and_the_linux_one_meanwhile(self):
        asked = []

        def imp(sha, tv_dir=None, flavor="", **kw):
            asked.append(flavor)
            return {"state": "absent" if flavor == "win32" else "imported", "sha": sha, "flavor": flavor, "why": "x"}
        saved = PR.import_bundle
        PR.import_bundle = imp
        try:
            r = PR.import_best(SHA, platform="win32")
            self.assertEqual(asked, ["win32", ""])
            self.assertEqual(r["imported"], [""])
            asked.clear()
            r2 = PR.import_best(SHA, platform="win32", state=r)
            self.assertEqual(asked, ["win32"], "the Linux set was fetched again after it was in")
        finally:
            PR.import_bundle = saved


class TheConsoleTick(_Tmp):

    @classmethod
    def setUpClass(cls):
        import control_app as CA
        cls.CA = CA

    def setUp(self):
        super().setUp()
        CA = self.CA
        self._saved = {k: getattr(CA, k) for k in ("_a_push_is_grading", "_sp_proof_playing_here", "HERE")}
        self._state = dict(CA._PROOF_RELEASE)
        CA._a_push_is_grading = lambda: False
        CA._sp_proof_playing_here = lambda: False
        CA.HERE = self.d                               # the state file is read from and written to the scratch dir
        CA._PROOF_RELEASE.update(running=False, state=None, sha=None)

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(self.CA, k, v)
        self.CA._PROOF_RELEASE.clear()
        self.CA._PROOF_RELEASE.update(self._state)
        super().tearDown()

    def _git(self, dirty=""):
        def git(argv, **kw):
            if argv[1:3] == ["rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(argv, 0, SHA + "\n", "")
            if argv[1] == "status":
                return subprocess.CompletedProcess(argv, 0, dirty, "")
            raise AssertionError(argv)
        return git

    def _tick(self, **kw):
        calls = []

        def imp(sha, tv_dir=None):
            calls.append(sha)
            return {"state": "imported", "sha": sha, "why": "imported", "seconds": 1.0, "at": 1,
                    "imported": [PR.flavors()[0]]}
        r = self.CA._proof_release_tick(_thread=lambda f: f(), _import=imp, **kw)
        return r, calls

    def test_an_owed_commit_is_imported_once_and_published(self):
        r, calls = self._tick(_git_run=self._git())
        self.assertEqual(calls, [SHA])
        self.assertEqual(self.CA._PROOF_RELEASE["state"], "imported")
        self.assertFalse(self.CA._PROOF_RELEASE["running"])
        r, calls = self._tick(_git_run=self._git())
        self.assertEqual(calls, [], "an imported commit was imported again")

    def test_a_push_grading_here_waits(self):
        self.CA._a_push_is_grading = lambda: True
        r, calls = self._tick(_git_run=self._git())
        self.assertEqual(calls, [], "the import ran during a push on this PC")
        self.assertIn("push", r["why"])

    def test_the_local_game_waits(self):
        self.CA._sp_proof_playing_here = lambda: True
        r, calls = self._tick(_git_run=self._git())
        self.assertEqual(calls, [])
        self.assertIn("game", r["why"])

    def test_a_dirty_tree_waits_and_is_not_refused_for_good(self):
        r, calls = self._tick(_git_run=self._git(dirty=" M tv/control_app.py\n"))
        self.assertEqual(calls, [], "a dirty tree was imported into (heart2 would refuse it, final for the commit)")
        self.assertEqual(r["state"], "waiting")
        r, calls = self._tick(_git_run=self._git())
        self.assertEqual(calls, [SHA], "a tree cleaned later never imported")

    def test_the_proof_tick_holds_while_an_import_runs_and_still_beacons(self):
        CA = self.CA
        ran, beacons = [], []
        saved = (CA._self_prove_tick, CA._console_beacon_async, CA._self_prove_step)
        self.addCleanup(lambda st=dict(CA._SELF_PROVE): (CA._SELF_PROVE.clear(), CA._SELF_PROVE.update(st)))
        CA._self_prove_tick = lambda: ran.append(1)
        CA._console_beacon_async = lambda e: beacons.append(e)
        CA._self_prove_step = lambda n, st: "tick"
        try:
            CA._PROOF_RELEASE["running"] = True
            CA._self_prove_dispatch(CA.SELF_PROVE_FIRST_TICK)
            self.assertEqual(ran, [], "a proof started beside the import of the same proofs")
            self.assertEqual(beacons, ["proof"])
            CA._PROOF_RELEASE["running"] = False
            CA._self_prove_dispatch(CA.SELF_PROVE_FIRST_TICK + CA.SELF_PROVE_EVERY_TICKS)
            self.assertEqual(ran, [1])
        finally:
            CA._self_prove_tick, CA._console_beacon_async, CA._self_prove_step = saved

    def test_the_rescue_loop_asks_and_status_says(self):
        import inspect
        loop = inspect.getsource(self.CA._console_rescue_loop)
        self.assertIn("_proof_release_tick()", loop)
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            self.assertIn('"proofRelease": dict(_PROOF_RELEASE)', fh.read())


def _code(text):
    return "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))


class TheBankJob(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(ROOT, ".github", "workflows", "proof-keys-shards.yml"), encoding="utf-8") as fh:
            cls.wf = _code(fh.read())
        with io.open(os.path.join(ROOT, ".github", "workflows", "publish.yml"), encoding="utf-8") as fh:
            cls.pub = _code(fh.read())
        cls.bank = cls.wf[cls.wf.index("\n  proof-bank:\n"):]

    def test_only_the_bank_may_write(self):
        self.assertEqual(self.wf.count("contents: write"), 1, "a job other than the bank may write to the repo")
        self.assertIn("contents: write", self.bank)
        self.assertIn("\npermissions:\n  contents: read\n", self.wf, "the workflow's default is no longer read-only")
        self.assertNotIn("actions/checkout", self.bank, "the job that may write now runs repo code")

    def test_it_runs_on_a_whole_set_only_and_never_holds_the_deploy(self):
        self.assertIn("if: ${{ always() && needs.fan-in.outputs.whole == 'true' }}", self.bank)
        self.assertIn("continue-on-error: true", self.bank)
        fan = self.wf[self.wf.index("\n  fan-in:\n"):self.wf.index("\n  proof-bank:\n")]
        a = fan.index("python3 tv/proof_shard.py --fan-in shards")
        b = fan.index('run: echo "whole=true" >> "$GITHUB_OUTPUT"')
        self.assertLess(a, b, "the set is called whole before the fan-in checked it")

    def test_it_packs_only_shard_caches_under_this_commit(self):
        fan = self.wf[self.wf.index("\n  fan-in:\n"):self.wf.index("\n  proof-bank:\n")]
        self.assertIn('python3 tv/proof_shard.py --bank shards --out "$RUNNER_TEMP/bank/proofs-${GITHUB_SHA}.tgz"', fan,
                      "the bundle is no longer packed by the read-only fan-in")
        self.assertIn('"bank/proofs-${GITHUB_SHA}.tgz"', self.bank)
        self.assertIn("gh release upload proof-bank", self.bank)
        self.assertIn(PR.RELEASE_TAG, self.bank)
        self.assertNotIn("python3 tv/", self.bank, "the job that may write runs repo code")

    def test_the_bank_packs_only_stores_and_the_pc_takes_exactly_that(self):
        import proof_shard as PS
        d = tempfile.mkdtemp(prefix="bank-")
        try:
            for k in (1, 2):
                os.makedirs(os.path.join(d, "shards", "proof-shard-%d" % k))
                io.open(os.path.join(d, "shards", "proof-shard-%d" % k, PS.STORE_NAME), "w").write("{}")
                io.open(os.path.join(d, "shards", "proof-shard-%d" % k, "prove.log"), "w").write("log")
            out = os.path.join(d, "bank", "b.tgz")
            self.assertEqual(PS.bank(os.path.join(d, "shards"), out, say=lambda *a: None), 0)
            paths, why = PR.safe_extract(out, os.path.join(d, "x"))
            self.assertIsNone(why, "the PC refused the bundle the bank packed")
            self.assertEqual(len(paths), 2, "the bank packed something besides the two stores")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_publish_lets_the_bank_write(self):
        job = self.pub[self.pub.index("\n  proof:\n"):self.pub.index("\n  deploy:\n")]
        self.assertIn("contents: write", job)

    def test_the_state_file_never_shows_in_git_status(self):
        with io.open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as fh:
            self.assertIn("\ntv/.proof_release.json\n", fh.read())


class TheWindowsSet(unittest.TestCase):
    """v3862 (item 3) - proof-keys-windows.yml: proves the PUBLISHED commit on windows-latest, off the ship's path."""

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(ROOT, ".github", "workflows", "proof-keys-windows.yml"), encoding="utf-8") as fh:
            cls.wf = _code(fh.read())

    def test_it_runs_after_publish_and_is_never_a_ship_gate(self):
        import ci_verdict as CV
        self.assertIn('workflows: ["Publish — gates, review, then deploy"]', self.wf)
        self.assertNotIn("ci/", self.wf.split("\njobs:")[0], "the Windows set runs on a ci/ push - it would queue the ship")
        name = self.wf.split("\n", 1)[0].split("name:", 1)[1].strip()
        self.assertNotIn(name, CV.REQUIRED, "an unmeasured Windows leg became a gate on every ship")

    def test_its_shards_never_fail_the_run_and_only_the_bank_writes(self):
        shard = self.wf[self.wf.index("\n  shard:\n"):self.wf.index("\n  fan-in:\n")]
        self.assertIn("exit 0", shard)
        self.assertEqual(self.wf.count("contents: write"), 1)
        self.assertIn("contents: write", self.wf[self.wf.index("\n  proof-bank:\n"):])
        self.assertIn('"bank/proofs-${HEAD_SHA}-win32.tgz"', self.wf)
        self.assertIn("--bank shards --out", self.wf[self.wf.index("\n  fan-in:\n"):self.wf.index("\n  proof-bank:\n")])
        self.assertIn("runs-on: windows-latest", shard)


RED_PROOF = [
    {"why": "v3862 - a stray file in the bundle is unpacked (prove.log overwrites a shard cache)",
     "file": "tv/proof_release.py",
     "find": "                if not _MEMBER.match(name):\n"
             "                    return None, \"the bundle holds %r, which is not a shard cache\" % m.name[:60]\n",
     "replace": "",
     "matches": 1},
    {"why": "v3862 - a link in the bundle is not refused as a link",
     "file": "tv/proof_release.py",
     "find": "                if not m.isreg():\n"
             "                    return None, \"the bundle holds %r, which is not a plain file\" % m.name[:60]\n",
     "replace": "",
     "matches": 1},
    {"why": "v3862 - an absent bundle reads as downloaded",
     "file": "tv/proof_release.py",
     "find": "        if e.code == 404:\n            return \"absent\",",
     "replace": "        if e.code == 404:\n            return \"ok\",",
     "matches": 1},
    {"why": "v3862 - an absent bundle is never asked again: the PC never imports its commit",
     "file": "tv/proof_release.py",
     "find": "    return [s.get(\"flavor\") or \"\"] if s.get(\"state\") == \"imported\" else []",
     "replace": "    return [s.get(\"flavor\") or \"\"] if s.get(\"state\") in (\"imported\", \"absent\") else []",
     "matches": 1},
    {"why": "v3862 - the import runs during a push grading on this PC",
     "file": "tv/control_app.py",
     "find": "            \"a push is grading on this PC\" if _a_push_is_grading() else\n",
     "replace": "",
     "matches": 1},
    {"why": "v3862 - a dirty tree is imported into (heart2 refuses it, and the refusal is final for the commit)",
     "file": "tv/control_app.py",
     "find": "        if d.returncode != 0 or (d.stdout or \"\").strip():\n            _PROOF_RELEASE.update(sha=head, state=\"waiting\",",
     "replace": "        if False:\n            _PROOF_RELEASE.update(sha=head, state=\"waiting\",",
     "matches": 1},
    {"why": "v3862 - a proof starts beside the import of the same proofs",
     "file": "tv/control_app.py",
     "find": "        if _PROOF_RELEASE.get(\"running\"):   # v3862",
     "replace": "        if False:   # v3862",
     "matches": 1},
    {"why": "v3862 - a Windows PC never asks for the set proved on Windows",
     "file": "tv/proof_release.py",
     "find": "    return (\"win32\", \"\") if (platform or sys.platform) == \"win32\" else (\"\",)",
     "replace": "    return (\"\",)",
     "matches": 1},
    {"why": "v3862 - the bank publishes a set the fan-in never called whole",
     "file": ".github/workflows/proof-keys-shards.yml",
     "find": "    if: ${{ always() && needs.fan-in.outputs.whole == 'true' }}\n",
     "replace": "    if: ${{ always() }}\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
