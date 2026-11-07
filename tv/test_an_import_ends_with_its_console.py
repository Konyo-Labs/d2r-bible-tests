# -*- coding: utf-8 -*-
"""#103 - AN IMPORT ENDS WITH THE CONSOLE THAT ASKED FOR IT.

MEASURED 11-07 ~12:45 IST on the OLD ALT (GrokBot's #230 6705733326 saw its river time out; this is why). Three
`heart2 --import-shards` ran at once. Two were orphans of consoles that had already exited (parent GONE): one started
11-06 02:59 and had keyed v3876's bundle for 32 h, one from 03:43. The live console's own import was the third. 457 MB
of 7.9 GB free, and GET /api/river timed out at 60 s. Killing the two orphans by PID freed 575 MB.

proof_release runs heart2 with subprocess.run, whose timeout lives in the console, so it dies with the console and
nothing else bounded the child. Now the console passes its pid (--import-parent), and heart2 ends the import when that
pid is gone (_watch_import_parent). That is safe between writes: each write is atomic, under an OS lock that is
released when the process exits, and REG-3352 keeps what was written. A probe that cannot answer keeps the import,
never a guessed death.

Measured with REAL processes: a parent is started and killed, and the import must exit 3 on its own.
RED_PROOF below.
"""
import os
import subprocess
import sys
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import heart2 as H  # noqa: E402
import proof_release as PR  # noqa: E402

_CHILD = ("import sys, time; sys.path.insert(0, %r); import heart2 as H; "
          "H._watch_import_parent(int(sys.argv[1]), every=0.2); time.sleep(40); sys.exit(0)")


def _env():
    e = dict(os.environ)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    return e


class AnImportEndsWithItsConsole(unittest.TestCase):

    def _pair(self):
        parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], env=_env())
        self.addCleanup(lambda: parent.poll() is None and parent.kill())
        child = subprocess.Popen([sys.executable, "-c", _CHILD % HERE, str(parent.pid)], env=_env(),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: child.poll() is None and child.kill())
        return parent, child

    def test_the_import_ends_when_its_console_is_gone(self):
        """* THE POINT: the console dies, and its import exits by itself, saying why"""
        parent, child = self._pair()
        time.sleep(1.5)
        self.assertIsNone(child.poll(), "premise: the import ended while its console was still there")
        parent.kill()
        parent.wait(timeout=10)
        try:
            rc = child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.fail("the console is gone and its import is still running 20 s later (the old ALT's orphans)")
        err = child.stderr.read().decode("utf-8", "replace")
        self.assertEqual(rc, 3, "the orphaned import did not end by its own rule: rc=%s %s" % (rc, err[-300:]))
        self.assertIn("#103 the console that asked for this import", err)

    def test_a_live_console_keeps_its_import(self):
        parent, child = self._pair()
        time.sleep(2.0)
        self.assertIsNone(child.poll(), "an import whose console is alive ended (rc=%s)" % child.poll())

    def test_a_probe_that_cannot_answer_keeps_the_import(self):
        ended = []

        def broken(pid):
            raise OSError("cannot ask")
        t = H._watch_import_parent(4242, every=0.01, alive=broken, quit=lambda: ended.append(1))
        time.sleep(0.3)
        self.assertEqual(ended, [], "a probe that could not answer ended the import - a guessed death")
        self.assertTrue(t.is_alive())


class TheConsoleTellsTheImportWhoItIs(unittest.TestCase):

    def test_proof_release_passes_its_own_pid(self):
        seen = {}

        def run(argv, **kw):
            seen["argv"] = list(argv)
            return subprocess.CompletedProcess(argv, 0, "ok", "")
        with mock.patch.object(PR, "download", return_value=("ok", "")), \
                mock.patch.object(PR, "safe_extract", return_value=(["a.json"], "")):
            PR.import_bundle("a" * 40, tv_dir=HERE, run=run)
        argv = seen.get("argv") or []
        self.assertIn("--import-parent", argv, "the import is not told which console asked for it: %s" % argv)
        self.assertEqual(argv[argv.index("--import-parent") + 1], str(os.getpid()))
        self.assertLess(argv.index("--import-parent"), argv.index("--import-shards"))

    def test_heart2_watches_the_parent_it_is_given(self):
        calls = []
        with mock.patch.object(H, "import_shards", return_value=0), \
                mock.patch.object(H, "_watch_import_parent", side_effect=lambda p: calls.append(p)):
            H.main(["--import-parent", "4321", "--import-shards", "a.json"])
            self.assertEqual(calls, [4321], "heart2 was told its console and does not watch it")
            del calls[:]
            H.main(["--import-shards", "a.json"])
            self.assertEqual(calls, [], "an import nobody claimed watches a parent (a hand-run import must never end)")


RED_PROOF = [
    {"why": "#103 - heart2 is told its console and never watches it (the old ALT's 32 h orphan)",
     "file": "heart2.py",
     "find": "            _watch_import_parent(a.import_parent)    # #103",
     "replace": "            pass    # #103",
     "matches": 1},
    {"why": "#103 - the console never tells the import who it is",
     "file": "proof_release.py",
     "find": "        argv += [\"--import-parent\", str(os.getpid())]",
     "replace": "        argv += []",
     "matches": 1},
    {"why": "#103 - the watch never sees its console die",
     "file": "heart2.py",
     "find": "                gone = not alive(ppid)",
     "replace": "                gone = False",
     "matches": 1},
    {"why": "#103 - a probe that cannot answer is read as a dead console (a guessed death)",
     "file": "heart2.py",
     "find": "                gone = False                 # a probe that cannot answer keeps the import",
     "replace": "                gone = True                 # a probe that cannot answer keeps the import",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
