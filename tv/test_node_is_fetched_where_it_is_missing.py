# -*- coding: utf-8 -*-
"""#167 (REG-2484) - NODE IS FETCHED WHERE IT IS MISSING: VERIFIED BEFORE IT IS UNPACKED, AND NOTHING OF HIS CHANGES.

His ruling, 2026-10-21: node on every PC - the installer and the console fetch it where it is absent, so the next new
PC never needs an SSH session. tv/node_runtime.py is that one door. This law drives it with a FIXTURE zip in its own
scratch (no network, never his %LOCALAPPDATA%) and pins:
  * absent on Windows -> the pinned zip is fetched, its SHA-256 checked BEFORE anything is extracted, extracted, renamed
    into <LOCALAPPDATA>/Programs/nodejs, and that folder put first on THIS process's PATH - no process is spawned, so
    no setx, and nothing is written outside that folder;
  * a hash mismatch -> nothing is extracted, nothing is placed, PATH is untouched, and the answer says why;
  * a node.exe that is not the pinned build is never placed;
  * node already here -> no fetch;  off Windows -> never a fetch;
  * blocking=False fetches on ONE background thread per process and answers ok None while it runs;
  * the installer calls the door exactly once, after the clone (comments stripped);
  * the pin is the one nodejs.org published and Dean's PC verified three times.
[[heart-first]] [[feedback-fixtures-never-touch-live-data]]
"""
import ast
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import node_runtime as NR  # noqa: E402

FAKE_EXE = b"MZ this stands in for node.exe in a fixture zip"
TOP = "node-vFIX-win-x64"
DEAN_VERIFIED_X64 = "d2046d28c2c3dcd211ac5145c0bf30e2047ef9dfb306693c8c6e2eccd8b95fa5"


def _sha(b):
    return hashlib.sha256(b).hexdigest()


class _Fixture(unittest.TestCase):

    def setUp(self):
        self.scratch = tempfile.mkdtemp(prefix="node_runtime_law_")
        self.addCleanup(shutil.rmtree, self.scratch, True)
        self.zip = os.path.join(self.scratch, "fixture.zip")
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr(TOP + "/node.exe", FAKE_EXE)
            z.writestr(TOP + "/README.md", "fixture")
        with io.open(self.zip, "rb") as fh:
            self.zip_sha = _sha(fh.read())
        self.local = os.path.join(self.scratch, "LocalAppData")
        self.target = os.path.join(self.local, "Programs", "nodejs")
        self.env = {"LOCALAPPDATA": self.local, "PATH": r"C:\Windows\system32;C:\Windows",
                    "PROCESSOR_ARCHITECTURE": "AMD64"}
        self.pin = {"version": "vFIX", "base": "https://nodejs.invalid/dist/vFIX/",
                    "files": {"x64": {"file": TOP + ".zip", "sha256": self.zip_sha, "top": TOP,
                                      "exeSha256": _sha(FAKE_EXE)}}}
        self.fetched, self.order, self.refreshed, self.spawned, self.workdirs = [], [], [], [], []
        real_sha, real_extract, real_mkdtemp = NR._sha256_of, NR._extract, NR.tempfile.mkdtemp

        def _sha_rec(path):
            self.order.append(("sha256", os.path.basename(path)))
            return real_sha(path)

        def _extract_rec(zip_path, into):
            self.order.append(("extract", os.path.basename(zip_path)))
            return real_extract(zip_path, into)

        def _mkdtemp_rec(*a, **k):
            d = real_mkdtemp(*a, **k)
            self.workdirs.append(d)
            return d

        def _popen_rec(*a, **k):
            self.spawned.append(a[0] if a else k.get("args"))
            raise OSError("a node fetch must not start any process")

        for target, name, val in ((NR, "_sha256_of", _sha_rec), (NR, "_extract", _extract_rec),
                                  (NR.tempfile, "mkdtemp", _mkdtemp_rec), (subprocess, "Popen", _popen_rec)):
            p = mock.patch.object(target, name, val)
            p.start()
            self.addCleanup(p.stop)
        with NR._BG_LOCK:
            NR._BG.update(thread=None, result=None)
        self.addCleanup(self._join_background)

    def _join_background(self):
        t = NR._BG.get("thread")
        if t is not None:
            t.join(20)
        with NR._BG_LOCK:
            NR._BG.update(thread=None, result=None)

    def _fetch(self, url, dest):
        self.fetched.append(url)
        shutil.copyfile(self.zip, dest)

    def _ensure(self, platform="win32", resolve=None, pin=None, blocking=True, fetch=None):
        return NR._ensure(blocking=blocking, why="a law", platform=platform, env=self.env,
                          resolve=resolve or (lambda env: None), fetch=fetch or self._fetch,
                          pin=pin or self.pin, refresh=lambda: self.refreshed.append(1))


class AbsentOnWindowsItIsFetchedVerifiedAndPlaced(_Fixture):

    def test_the_pinned_zip_is_verified_before_extraction_and_put_on_this_process_path_only(self):
        before = dict(self.env)
        r = self._ensure()
        print("   %s" % r["why"])
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["fetched"], r)
        node = os.path.join(self.target, "node.exe")
        self.assertEqual(r["node"], node)
        with io.open(node, "rb") as fh:
            self.assertEqual(fh.read(), FAKE_EXE, "what was placed is not what the pinned zip held")
        self.assertEqual(self.fetched, ["https://nodejs.invalid/dist/vFIX/" + TOP + ".zip"],
                         "the pinned file was not the one fetched (or it was fetched twice)")
        kinds = [k for k, _n in self.order]
        self.assertIn("extract", kinds, self.order)
        self.assertEqual(self.order[0], ("sha256", TOP + ".zip"),
                         "something was extracted before the zip's SHA-256 was checked: %r" % self.order)
        self.assertLess(kinds.index("sha256"), kinds.index("extract"), self.order)
        self.assertTrue(self.env["PATH"].startswith(self.target + ";"),
                        "node's folder is not first on this process's PATH: %r" % self.env["PATH"])
        self.assertTrue(self.env["PATH"].endswith(before["PATH"]), "the PATH it found was not kept behind node")
        self.assertTrue(r["onPath"], r)
        self.assertEqual(self.spawned, [], "the fetch started a process (setx?): %r" % self.spawned)
        self.assertEqual(set(self.env) - set(before), set(), "it wrote an environment variable other than PATH")
        self.assertEqual(self.refreshed, [1], "cb_node_harness.NODE was not resolved again after the fetch")
        self.assertTrue(self.workdirs, "PREMISE: no work folder was made")
        for d in self.workdirs:
            self.assertFalse(os.path.exists(d), "the download's work folder was left behind: %s" % d)

    def test_a_hash_mismatch_extracts_nothing_places_nothing_and_says_why(self):
        bad = dict(self.pin, files={"x64": dict(self.pin["files"]["x64"], sha256="0" * 64)})
        path0 = self.env["PATH"]
        r = self._ensure(pin=bad)
        print("   %s" % r["why"])
        self.assertFalse(r["ok"], r)
        self.assertIn("SHA-256", r["why"])
        self.assertIn("nothing was extracted", r["why"])
        self.assertNotIn("extract", [k for k, _n in self.order], "a zip that failed its hash was extracted")
        self.assertFalse(os.path.exists(self.target), "a zip that failed its hash was placed")
        self.assertEqual(self.env["PATH"], path0, "PATH changed for a node that was never placed")

    def test_a_node_exe_that_is_not_the_pinned_build_is_never_placed(self):
        bad = dict(self.pin, files={"x64": dict(self.pin["files"]["x64"], exeSha256="1" * 64)})
        r = self._ensure(pin=bad)
        self.assertFalse(r["ok"], r)
        self.assertFalse(os.path.exists(self.target), "a node.exe the pin does not name was placed")


class NoFetchWhereItIsNotOwed(_Fixture):

    def test_a_node_already_here_is_not_fetched_again(self):
        have = os.path.join(self.scratch, "already", "node.exe")
        os.makedirs(os.path.dirname(have))
        with io.open(have, "wb") as fh:
            fh.write(FAKE_EXE)
        r = self._ensure(resolve=lambda env: have)
        self.assertTrue(r["ok"], r)
        self.assertFalse(r["fetched"], r)
        self.assertEqual(self.fetched, [], "node was fetched although it is on this PC")
        self.assertTrue(r["onPath"], "a node off PATH on Windows was not put on this process's PATH: %r" % r)

    def test_off_windows_it_never_fetches(self):
        for plat in ("darwin", "linux"):
            r = self._ensure(platform=plat)
            self.assertFalse(r["ok"], r)
            self.assertIn("only on Windows", r["why"])
        self.assertEqual(self.fetched, [], "node was fetched on a PC that is not Windows")
        self.assertFalse(os.path.exists(self.target))


class TheBackgroundFetchRunsOncePerProcess(_Fixture):

    def test_blocking_false_answers_fetching_then_the_answer_and_fetches_once(self):
        r1 = self._ensure(blocking=False)
        self.assertIsNone(r1["ok"], r1)
        self.assertIn("fetching", r1["why"])
        self._join_now()
        r2 = self._ensure(blocking=False)
        self.assertTrue(r2["ok"], r2)
        self.assertEqual(len(self.fetched), 1, "the background fetch ran %d times" % len(self.fetched))

    def test_a_failed_background_fetch_is_said_and_not_repeated(self):
        def _boom(url, dest):
            self.fetched.append(url)
            raise IOError("the network is down")
        self._ensure(blocking=False, fetch=_boom)
        self._join_now()
        r = self._ensure(blocking=False, fetch=_boom)
        self.assertFalse(r["ok"], r)
        self.assertIn("could not be fetched", r["why"])
        self.assertEqual(len(self.fetched), 1, "a failed fetch was retried in the same process")

    def test_a_failed_fetch_is_tried_again_after_an_hour_and_a_success_never(self):
        """REG-3263 - the repair book's hourly node door got this process's cached failure forever."""
        calls = {"n": 0}

        def _flaky(url, dest):
            calls["n"] += 1
            if calls["n"] == 1:
                self.fetched.append(url)
                raise IOError("the network is down")
            return self._fetch(url, dest)
        self._ensure(blocking=False, fetch=_flaky)
        self._join_now()
        with NR._BG_LOCK:
            NR._BG["at"] = time.time() - NR.RETRY_FAILED_S - 1
        r = self._ensure(blocking=False, fetch=_flaky)
        self.assertIsNone(r["ok"], "an hour-old failure was not asked again: %r" % r)
        self._join_now()
        self.assertTrue(self._ensure(blocking=False, fetch=_flaky)["ok"])
        with NR._BG_LOCK:
            NR._BG["at"] = time.time() - NR.RETRY_FAILED_S - 1
        self._ensure(blocking=False, fetch=_flaky)
        self.assertEqual(len(self.fetched), 2, "a success was fetched again, or the failure was not retried")

    def _join_now(self):
        t = NR._BG.get("thread")
        self.assertIsNotNone(t, "no background fetch was started")
        t.join(20)


class TheInstallerAndThePin(unittest.TestCase):

    def _ps1_code(self):
        with io.open(os.path.join(HERE, "install-tvd.ps1"), encoding="utf-8-sig") as fh:
            raw = fh.read()
        out, in_block = [], False
        for ln in raw.splitlines():
            s = ln.strip()
            if in_block:
                if "#>" in s:
                    in_block = False
                continue
            if s.startswith("<#"):
                in_block = "#>" not in s
                continue
            if s.startswith("#"):
                continue
            out.append(ln)
        return "\n".join(out)

    def test_the_installer_calls_the_door_exactly_once_after_the_clone(self):
        code = self._ps1_code()
        call = '& $py "$repoDir\\tv\\node_runtime.py" --ensure'
        n = code.count(call)
        print("   installer calls of the node door: %d" % n)
        self.assertEqual(n, 1, "the installer must call tv/node_runtime.py --ensure exactly once (found %d)" % n)
        clone = code.find('Ok "repo at $repoDir (control app present)"')
        self.assertGreater(clone, 0, "PREMISE: the clone block's last line moved")
        self.assertGreater(code.find(call), clone, "the node step runs before the repo is on disk")

    def test_the_pin_is_the_build_nodejs_published_and_dean_verified(self):
        pin, why = NR.load_pin()
        self.assertIsNotNone(pin, why)
        self.assertEqual(pin["version"], "v24.22.1")
        x64 = pin["files"]["x64"]
        self.assertEqual(x64["sha256"], DEAN_VERIFIED_X64, "the x64 pin is not the hash verified three times")
        for a, ent in pin["files"].items():
            self.assertTrue(ent["file"].startswith("node-%s-win-" % pin["version"]), ent)
            self.assertEqual(ent["top"] + ".zip", ent["file"], ent)
            for k in ("sha256", "exeSha256"):
                self.assertRegex(ent[k], r"^[0-9a-f]{64}$", "%s %s is not a SHA-256" % (a, k))

    def test_the_door_names_no_persistent_write(self):
        """No registry module, no setx, no SetEnvironmentVariable - read from the compiler, never from prose."""
        with io.open(os.path.join(HERE, "node_runtime.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        docs = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body \
                    and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0], "value", None), ast.Constant):
                docs.add(id(n.body[0].value))
        bad = []
        for n in ast.walk(tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in n.names] + ([n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
                bad += [x for x in names if x and x.split(".")[0] in ("winreg", "_winreg", "subprocess")]
            if isinstance(n, ast.Attribute) and n.attr.startswith("SetEnvironmentVariable"):
                bad.append(n.attr)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs \
                    and n.value.strip().lower() in ("setx", "setx.exe"):
                bad.append(n.value)
        self.assertEqual(bad, [], "the node door reaches for a persistent write: %r" % bad)


RED_PROOF = [
    {"why": "REG-3263 - a failed node fetch is this process's answer forever, so the book's hourly retry never fetches",
     "file": "tv/node_runtime.py",
     "find": "            if not (failed and time.time() - float(_BG.get(\"at\") or 0) >= RETRY_FAILED_S):\n",
     "replace": "            if True:\n",
     "matches": 1},
    {
        "why": "REG-2484 - the download is no longer checked against the pin: any zip is unpacked and placed",
        "file": "node_runtime.py",
        "find": "        if got != str(ent[\"sha256\"]).lower():\n",
        "replace": "        if False:\n",
        "matches": 1,
    },
    {
        "why": "REG-2484 - the zip is unpacked BEFORE its hash is checked: a tampered archive's files land on disk",
        "file": "node_runtime.py",
        "find": "        got = _sha256_of(zpath)\n",
        "replace": "        _extract(zpath, os.path.join(work, \"early\"))\n        got = _sha256_of(zpath)\n",
        "matches": 1,
    },
    {
        "why": "REG-2484 - PATH is written for good (setx): the fetch changes his account's PATH, not this process's",
        "file": "node_runtime.py",
        "find": "    env[\"PATH\"] = folder + (sep + cur if cur else \"\")\n",
        "replace": "    env[\"PATH\"] = folder + (sep + cur if cur else \"\")\n"
                   "    __import__(\"subprocess\").Popen([\"setx\", \"PATH\", env[\"PATH\"]])\n",
        "matches": 1,
    },
    {
        "why": "REG-2484 - a Mac or Linux box fetches the Windows zip it can never run",
        "file": "node_runtime.py",
        "find": "    if plat != \"win32\":\n        return _res(False, None, False, False, \"node is not on this PC, and it is "
                "fetched only on Windows - \"\n",
        "replace": "    if False:\n        return _res(False, None, False, False, \"node is not on this PC, and it is "
                   "fetched only on Windows - \"\n",
        "matches": 1,
    },
    {
        "why": "REG-2484 - the installer stops calling the node door: the next new PC has no node again",
        "file": "install-tvd.ps1",
        "find": "    $nodeOut = & $py \"$repoDir\\tv\\node_runtime.py\" --ensure 2>&1\n",
        "replace": "    $nodeOut = 'skipped'\n",
        "matches": 1,
    },
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
