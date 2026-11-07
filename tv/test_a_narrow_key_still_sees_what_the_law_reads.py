# -*- coding: utf-8 -*-
"""v3882 (REG-3393) - NARROW PROOF KEYS: A LAW IS TRACED PAST WHAT CANNOT READ THE TREE, AND NEVER PAST WHAT CAN.

His question 2026-11-07: "didnt we say the proofs get saved and dont need to reprove themselves ... why does a full run need
to keep being done?" - then "do it sooner, build the narrow keys now". MEASURED on v3879's round on c136dc468 (only
tv/demo_console.mjs changed): 5,154 proofs served, 4,419 proved again. A proof's key is its law, the whole import closure and
every file the closure names; 381 laws import control_app, whose closure reaches console_doctor, which reads demo_console.mjs.
A law whose run is TRACED completely is keyed only by the files it opened (REG-2640/3319) - but 320 of 520 law files could not
be traced: spawn git 123 · ctypes 141 · Pillow natives 85 · lsof 47 · chrome 80 · numpy 10.

Admitted now, each only in the shape that cannot read a byte of the tree (heart2's trace site says why for each):
  * lsof / ldconfig (the process table, the linker cache);
  * Pillow's codecs PIL._imaging/_webp/_avif (bytes in from Python; an image opened by path is a builtins.open the hook sees)
    - never _imagingft (a font by path, in C) or numpy (fromfile opens a path in C);
  * ctypes: a library by bare name or from the system, and only process / clock / disk-metadata symbols;
  * git in the law's OWN temp repo: inside the temp dir, outside the sandbox, nothing redirecting it (GIT_DIR and kin - a hook
    leaks GIT_DIR into tests), no path argument leaving that directory, no --no-index / --git-dir / --work-tree.
Every case below runs a real child under the real trace site. Each admission has a twin that must still keep every byte.
RED_PROOF below. [[regression-guard]] [[unknown-stays-unknown]]
"""
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import heart2 as H  # noqa: E402

POSIX = os.name == "posix"


@unittest.skipUnless(POSIX, "the trace is POSIX-only (heart2._trace_wanted) - UNMEASURED here, not a pass")
class ANarrowKeySeesWhatTheLawReads(unittest.TestCase):

    def setUp(self):
        self.sandbox = tempfile.mkdtemp(prefix="h2sb.")          # like the real one: a tree inside the temp dir
        os.makedirs(os.path.join(self.sandbox, "tv"))
        self.subject = os.path.join(self.sandbox, "tv", "subject.txt")
        with io.open(self.subject, "w", encoding="utf-8") as fh:
            fh.write("tree bytes\n")
        self.fx = tempfile.mkdtemp(prefix="h2fx.")               # the law's own scratch: temp dir, outside the sandbox

    def tearDown(self):
        shutil.rmtree(self.sandbox, ignore_errors=True)
        shutil.rmtree(self.fx, ignore_errors=True)

    def _run(self, body, sandbox="default", env_extra=None):
        site = H._trace_site()
        self.assertIsNotNone(site, "no trace site could be written")
        log = os.path.join(self.fx, "trace.log")
        if os.path.exists(log):
            os.unlink(log)
        env = dict(os.environ, PYTHONPATH=site, HEART2_TRACE_LOG=log, HEART2_TRACE_SITE=site,
                   FX=self.fx, SB=self.sandbox, SUBJ=self.subject)
        for k in [k for k in env if k.startswith("GIT_")]:
            env.pop(k)
        env.update(env_extra or {})
        script = "import os, subprocess, sys\nFX, SB, SUBJ = os.environ['FX'], os.environ['SB'], os.environ['SUBJ']\n" + body
        r = subprocess.run([sys.executable, "-c", script], cwd=os.path.join(self.sandbox, "tv"), env=env,
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, "the traced child failed: " + (r.stdout + r.stderr)[-800:])
        why = set()
        seen, ok = H._trace_read(log, os.getpid(), why=why, sandbox=self.sandbox if sandbox == "default" else sandbox)
        return seen, ok, why

    # ── git ──────────────────────────────────────────────────────────────────────────────────────────────────────────
    GIT_OWN = ("def g(*a, **k):\n"
               "    try: subprocess.run(['git'] + list(a), capture_output=True, **k)\n"
               "    except FileNotFoundError: pass\n")

    def test_git_in_the_laws_own_temp_repo_is_traced_past(self):
        """* THE POINT: the commonest cause (123) - a law's fixture repo - no longer widens its key"""
        seen, ok, why = self._run(self.GIT_OWN + "g('init', '-q', cwd=FX)\ng('-C', FX, 'status')\n")
        self.assertTrue(ok, "git in the law's own temp repo still kept every byte: %r" % why)

    def test_git_in_the_tree_keeps_every_byte(self):
        seen, ok, why = self._run(self.GIT_OWN + "g('status')\n")          # cwd is the sandbox's tv/
        self.assertFalse(ok)
        self.assertTrue(any("in the tree" in w for w in why), why)

    def test_git_with_a_leaked_git_dir_keeps_every_byte(self):
        """a hook leaks GIT_DIR into a test: the child then works on HIS repo, whatever its cwd"""
        seen, ok, why = self._run(self.GIT_OWN + "g('status', cwd=FX)\n", env_extra={"GIT_DIR": "/elsewhere/.git"})
        self.assertFalse(ok, "a GIT_DIR-redirected git was traced past")

    def test_git_reading_a_path_outside_its_repo_keeps_every_byte(self):
        seen, ok, why = self._run(self.GIT_OWN + "g('-C', FX, 'hash-object', SUBJ)\n")
        self.assertFalse(ok, "git hash-object of a tree file was traced past")
        seen, ok, why = self._run(self.GIT_OWN + "g('-C', FX, 'diff', '--no-index', SUBJ, SUBJ)\n")
        self.assertFalse(ok, "git diff --no-index was traced past")

    def test_git_with_no_sandbox_to_judge_by_keeps_every_byte(self):
        seen, ok, why = self._run(self.GIT_OWN + "g('-C', FX, 'status')\n", sandbox=None)
        self.assertFalse(ok)

    # ── lsof ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_lsof_is_traced_past(self):
        seen, ok, why = self._run("try: subprocess.run(['lsof', '-v'], capture_output=True)\nexcept FileNotFoundError: pass\n")
        self.assertTrue(ok, why)

    # ── ctypes ───────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_a_process_call_through_ctypes_is_traced_past(self):
        seen, ok, why = self._run("import ctypes\nctypes.CDLL(None).getpid()\n")
        self.assertTrue(ok, why)

    def test_a_corefoundation_constant_is_traced_past(self):
        """a kCF... symbol is a constant (data): disk_room asks a volume's free space through it, never a file's bytes"""
        seen, ok, why = self._run("import ctypes\ntry: ctypes.CDLL(None).kCFURLVolumeAvailableCapacityKey\n"
                                  "except AttributeError: pass\n")
        self.assertTrue(ok, why)

    def test_a_file_call_through_ctypes_keeps_every_byte(self):
        seen, ok, why = self._run("import ctypes\nctypes.CDLL(None).fopen\n")
        self.assertFalse(ok, "a ctypes fopen was traced past")
        self.assertTrue(any("fopen" in w for w in why), why)

    # ── Pillow / numpy ───────────────────────────────────────────────────────────────────────────────────────────────
    @unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is not installed here - UNMEASURED, not a pass")
    def test_pillow_reading_an_image_is_traced_and_the_image_stays_in_the_key(self):
        from PIL import Image
        png = os.path.join(self.sandbox, "tv", "pic.png")
        Image.new("RGB", (4, 4), (9, 9, 9)).save(png)
        seen, ok, why = self._run("from PIL import Image\nImage.open(os.path.join(SB, 'tv', 'pic.png')).load()\n")
        self.assertTrue(ok, "Pillow's codec still widened the key: %r" % why)
        self.assertIn("pic.png", seen, "the image the law opened was not recorded - it would be dropped from the key")

    @unittest.skipUnless(importlib.util.find_spec("PIL") and importlib.util.find_spec("PIL._imagingft"),
                         "Pillow's font module is not here - UNMEASURED, not a pass")
    def test_pillow_fonts_keep_every_byte(self):
        seen, ok, why = self._run("from PIL import ImageFont\n")
        self.assertFalse(ok, "_imagingft (a font by path, in C) was traced past")

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "numpy is not installed here - UNMEASURED, not a pass")
    def test_numpy_keeps_every_byte(self):
        seen, ok, why = self._run("import numpy\n")
        self.assertFalse(ok, "numpy (fromfile opens a path in C) was traced past")

    def test_baseline_a_plain_run_is_traced_and_its_read_is_seen(self):
        seen, ok, why = self._run("open(SUBJ).read()\n")
        self.assertTrue(ok, why)
        self.assertIn("subject.txt", seen)


RED_PROOF = [
    {"why": "REG-3393 - git in the tree (the sandbox) is traced past - a stale PROVEN over the tree's own bytes",
     "file": "tv/heart2.py", "find": "    if under(g, sb) or under(sb, g):\n        return \"spawn git in the tree\"\n",
     "replace": "    if False:\n        return \"spawn git in the tree\"\n", "matches": 1},
    {"why": "REG-3393 - a GIT_DIR-redirected git (a hook's leak) is traced past",
     "file": "tv/heart2.py", "find": "        if any(_eget(src, k) for k in _GIT_ENV):\n            return None\n",
     "replace": "        if False:\n            return None\n", "matches": 1},
    {"why": "REG-3393 - a git path argument that leaves its repo is traced past",
     "file": "tv/heart2.py",
     "find": "                if not (full == d or full.startswith(d.rstrip(_o.sep) + _o.sep)):\n                    return None\n",
     "replace": "                if False:\n                    return None\n", "matches": 1},
    {"why": "REG-3393 - every ctypes symbol is traced past (a C fopen of a tree file)",
     "file": "tv/heart2.py",
     "find": "            emit(\"A\" if (sym in _SYM_OK or sym.startswith(\"kCF\")) else \"U\", ev + \" \" + sym)",
     "replace": "            emit(\"A\", ev + \" \" + sym)", "matches": 1},
    {"why": "REG-3393 - every native module is traced past (numpy fromfile, Pillow fonts read paths in C)",
     "file": "tv/heart2.py", "find": "        return (_o.sep + \"PIL\" + _o.sep) in f and b.startswith(_NATIVE_OK)\n",
     "replace": "        return True\n", "matches": 1},
    {"why": "REG-3393 - git with no sandbox to judge it by is traced past",
     "file": "tv/heart2.py", "find": "    if not sandbox:\n        return \"spawn git (no sandbox to judge it by)\"\n",
     "replace": "    if False:\n        return \"spawn git (no sandbox to judge it by)\"\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
