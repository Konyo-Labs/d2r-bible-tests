# -*- coding: utf-8 -*-
"""#224 — AN IN-PLACE RELAUNCH LEAVES NO <defunct> CHILD, AND THE NEXT IMAGE COLLECTS ANY IT INHERITS.

⚠⚠ MEASURED 2026-09-24 (read-only audit of his console): 35 <defunct> `ocr_mac` children under one pid,
exactly one per os.execv relaunch — the warm tv_diablo OCR worker was alive at every exec and the new
image had no handle to wait() it. DRIVEN on REAL processes in a temp dir, never on his console:
a worker quiesced before exec leaves nothing; a child that dies AFTER exec is reaped by the new image
BY PID; and the baseline proves the end-to-end case can tell the two apart. RED_PROOF below.
"""
import ast
import io
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import exec_hygiene as EH  # noqa: E402

_POSIX = os.name == "posix"


def _zombie_children(pid):
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,stat="], capture_output=True, text=True).stdout
    return [ln.split()[0] for ln in out.splitlines()
            if len(ln.split()) >= 3 and ln.split()[1] == str(pid) and ln.split()[2].startswith("Z")]


class _Worker(object):
    """The shape tv_diablo's OcrWorker has: a live Popen in `.p` and a stop() that kills and waits."""
    def __init__(self):
        self.p = subprocess.Popen(["sleep", "60"])

    def stop(self):
        p, self.p = self.p, None
        p.kill()
        p.wait(timeout=5)


@unittest.skipUnless(_POSIX, "UNMEASURED: os.execv replaces the image only on POSIX")
class AnExecLeavesNoCorpse(unittest.TestCase):

    def test_quiesce_stops_every_warm_worker_it_can_see(self):
        mod = types.ModuleType("_fake_warm_mod")
        w = _Worker()
        mod._OCR = w
        mod.not_a_worker = object()
        sys.modules["_fake_warm_mod"] = mod
        pid = w.p.pid
        try:
            self.assertEqual([n for _m, n, _o in EH.warm_workers(("_fake_warm_mod",))], ["_OCR"])
            done = EH.quiesce_before_exec(("_fake_warm_mod",))
            self.assertEqual(done, ["_fake_warm_mod._OCR stopped"])
            self.assertEqual(_zombie_children(os.getpid()), [], "the stopped worker was left <defunct>")
            with self.assertRaises(ChildProcessError):
                os.waitpid(pid, os.WNOHANG)                     # already collected by stop()
        finally:
            sys.modules.pop("_fake_warm_mod", None)

    def test_a_LIST_of_warm_workers_is_seen_too(self):
        mod = types.ModuleType("_fake_pool_mod")
        mod._WORKERS = [_Worker(), _Worker()]
        sys.modules["_fake_pool_mod"] = mod
        try:
            self.assertEqual(sorted(n for _m, n, _o in EH.warm_workers(("_fake_pool_mod",))),
                             ["_WORKERS[0]", "_WORKERS[1]"])
            EH.quiesce_before_exec(("_fake_pool_mod",))
            self.assertEqual(_zombie_children(os.getpid()), [])
        finally:
            for w in mod._WORKERS:
                if w.p is not None:
                    w.stop()
            sys.modules.pop("_fake_pool_mod", None)

    def _exec_pair(self, reap, dead_before_exec=False):
        """Image A spawns a child, then execs into image B; B reports how many zombie children it holds
        once the child has died. `dead_before_exec`: the child is already a zombie AT the exec, so B's
        IMMEDIATE reap is what must collect it; otherwise it is alive at the exec and dies later, which
        is the reaper THREAD's job — two paths, two cases (the first cut drove only one, and heart2
        caught the other's sabotage staying green)."""
        d = tempfile.mkdtemp(prefix="exec-corpse-")
        b = os.path.join(d, "b.py")
        a = os.path.join(d, "a.py")
        io.open(b, "w").write(textwrap.dedent("""
            import os, subprocess, sys, time
            sys.path.insert(0, %r)
            import exec_hygiene as EH
            kids = EH.children_of()
            rp = {"reaped": -1, "waiting": -1}
            if %r:
                rp = EH.reap_inherited(kids or [], retry_s=0.2, give_up_s=10)
            print("REAPED=%%d WAITING=%%d" %% (rp["reaped"], rp["waiting"]))
            time.sleep(2.5)                      # the inherited child exits at 1.2 s
            out = subprocess.run(["ps", "-axo", "pid=,ppid=,stat="], capture_output=True, text=True).stdout
            z = [l for l in out.splitlines() if len(l.split()) >= 3 and l.split()[1] == str(os.getpid())
                 and l.split()[2].startswith("Z")]
            print("INHERITED=%%d ZOMBIES=%%d" %% (len(kids or []), len(z)))
        """ % (HERE, reap)))
        io.open(a, "w").write(textwrap.dedent("""
            import os, subprocess, sys
            import time
            if %r:
                _child = subprocess.Popen(["true"]); time.sleep(0.5)   # already <defunct> at the exec
            else:
                _child = subprocess.Popen(["sleep", "1.2"])      # alive at exec, like the warm worker
            os.execv(sys.executable, [sys.executable, %r])
        """ % (dead_before_exec, b)))
        try:
            return subprocess.run([sys.executable, a], capture_output=True, text=True, timeout=30).stdout
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    def test_the_new_image_reaps_what_it_inherited(self):
        got = self._exec_pair(reap=True)
        self.assertIn("INHERITED=1", got, "premise: the child did not survive the exec: %r" % got)
        self.assertIn("ZOMBIES=0", got, "the inherited child died and was left <defunct>: %r" % got)

    def test_a_child_already_dead_at_the_exec_is_reaped_at_once(self):
        got = self._exec_pair(reap=True, dead_before_exec=True)
        self.assertIn("INHERITED=1", got, "premise: the dead child was not inherited: %r" % got)
        self.assertIn("ZOMBIES=0", got, "an inherited corpse was not collected at boot: %r" % got)
        # "AT ONCE" is the property: the reaper thread would also collect it within its retry, so only
        # the immediate return can tell the boot reap from the backstop (heart2 caught that BLIND).
        self.assertIn("REAPED=1 WAITING=0", got, "a child already dead at the exec was left to the "
                                                 "thread instead of collected at boot: %r" % got)

    def test_baseline_without_the_reap_a_corpse_is_left(self):
        """Proves the case above can FAIL: the same exec, no reap, leaves exactly the measured corpse."""
        got = self._exec_pair(reap=False)
        self.assertIn("INHERITED=1 ZOMBIES=1", got, "the baseline did not reproduce the leak: %r" % got)


class EveryExecSiteIsQuiescedFirst(unittest.TestCase):

    def setUp(self):
        self.src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        self.tree = ast.parse(self.src)

    def test_every_os_execv_is_preceded_by_before_exec_in_its_function(self):
        funcs = [n for n in ast.walk(self.tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        execs, bad = 0, []
        for f in funcs:
            own = [n for n in ast.walk(f) if isinstance(n, ast.Call)]
            nested = {id(x) for g in ast.walk(f) if g is not f and isinstance(g, (ast.FunctionDef, ast.AsyncFunctionDef))
                      for x in ast.walk(g)}
            own = [c for c in own if id(c) not in nested]
            ex = [c for c in own if isinstance(c.func, ast.Attribute) and c.func.attr == "execv"
                  and getattr(c.func.value, "id", "") == "os"]
            before = [c.lineno for c in own if getattr(c.func, "id", "") == "_before_exec"]
            for c in ex:
                execs += 1
                if not any(b < c.lineno for b in before):
                    bad.append("%s:%d" % (f.name, c.lineno))
        self.assertGreaterEqual(execs, 4, "premise: fewer os.execv sites than measured (4) — re-anchor")
        self.assertEqual(bad, [], "an os.execv with no _before_exec ahead of it in its function: %s" % bad)

    def test_main_reaps_inherited_children_before_it_spawns_anything(self):
        main = [n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"]
        self.assertEqual(len(main), 1)
        calls = [n for n in ast.walk(main[0]) if isinstance(n, ast.Call)]
        # the reap may live in main() or in the one helper main() calls for it (#224, the UNKNOWN line)
        reap = [c.lineno for c in calls
                if (isinstance(c.func, ast.Attribute) and c.func.attr == "reap_inherited")
                or getattr(c.func, "id", "") == "_reap_inherited_at_boot"]
        first_payload = [c.lineno for c in calls if getattr(c.func, "id", "") == "status_payload"]
        helper = [n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == "_reap_inherited_at_boot"]
        if helper:
            self.assertTrue([c for c in ast.walk(helper[0]) if isinstance(c, ast.Call)
                             and isinstance(c.func, ast.Attribute) and c.func.attr == "reap_inherited"],
                            "_reap_inherited_at_boot no longer calls reap_inherited")
        self.assertTrue(reap, "main() no longer reaps inherited children")
        self.assertTrue(first_payload and min(reap) < min(first_payload),
                        "the reap runs after status_payload(), which spawns git — it must run first")


class TheBootReapSaysWhatHappened(unittest.TestCase):
    """#224 — the second eye on 955858d4 (grok-4.7): an unreadable process table reaped nothing and
    said nothing, the same silence as 'no children'. DRIVEN with a stub exec_hygiene."""

    def setUp(self):
        import control_app as ca
        self.ca = ca
        self._eh = sys.modules.get("exec_hygiene")
        self.fake = types.ModuleType("exec_hygiene")
        self.fake.reap_inherited = lambda pids, **k: {"reaped": len(pids), "waiting": 0}
        sys.modules["exec_hygiene"] = self.fake

    def tearDown(self):
        sys.modules["exec_hygiene"] = self._eh

    def test_an_unreadable_process_table_is_said_out_loud(self):
        self.fake.children_of = lambda pid=None: None
        # #107 - the POSIX path, asked as POSIX on every platform (a Windows boot is not asked: the case below)
        self.assertIn("UNKNOWN", self.ca._reap_inherited_at_boot(posix=True),
                      "an unreadable ps reaped nothing and said nothing - UNKNOWN read as 'no children'")

    def test_no_children_is_quiet(self):
        self.fake.children_of = lambda pid=None: []
        self.assertEqual(self.ca._reap_inherited_at_boot(), "")

    def test_inherited_children_are_counted(self):
        self.fake.children_of = lambda pid=None: [4242, 4243]
        self.assertIn("inherited 2 child process(es)", self.ca._reap_inherited_at_boot(posix=True))

    def test_windows_is_not_asked_and_says_no_false_unknown(self):
        # REG-1265 — the second eye on 229e2397: every Windows boot printed a false UNKNOWN
        asked = []
        self.fake.children_of = lambda pid=None: asked.append(1)
        self.assertEqual(self.ca._reap_inherited_at_boot(posix=False), "",
                         "a Windows boot printed the unreadable-ps UNKNOWN for a question that does not exist there")
        self.assertEqual(asked, [], "the boot asked a POSIX question on Windows")

    def test_premise_posix_still_says_unknown(self):
        self.fake.children_of = lambda pid=None: None
        self.assertIn("UNKNOWN", self.ca._reap_inherited_at_boot(posix=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "REG-1265 - every Windows boot prints the unreadable-process-table UNKNOWN again",
        "file": "control_app.py",
        "find": "    if not posix:\n        return \"\"\n    try:\n        import exec_hygiene as _eh\n",
        "replace": "    try:\n        import exec_hygiene as _eh\n",
        "matches": 1,
    },
    {
        "why": "#224 - an unreadable process table at boot reaps nothing and says nothing again (second eye on 955858d4)",
        "file": "control_app.py",
        "find": "        if _inh is None:\n            line = (\"   inherited-children reap UNKNOWN",
        "replace": "        if False:\n            line = (\"   inherited-children reap UNKNOWN",
        "matches": 1,
    },
    {
        "why": "#224 - quiesce stops nothing: the warm worker is still alive at exec and becomes a <defunct> child of the next image",
        "file": "exec_hygiene.py",
        "find": "            obj.stop()\n            done.append(\"%s.%s stopped\" % (modname, name))\n",
        "replace": "            done.append(\"%s.%s stopped\" % (modname, name))\n",
        "matches": 1,
        # REG-2357 - its only catching cases are AnExecLeavesNoCorpse's, which skip off POSIX (os.execv replaces the
        # image only there): on Windows this proof files BLIND. Judged where POSIX is.
        "needs": "posix",
    },
    {
        "why": "#224 - the new image never collects what it inherited: a child that dies after exec stays <defunct> for the life of the console",
        "file": "exec_hygiene.py",
        "find": "            got, _st = os.waitpid(int(p), os.WNOHANG)\n",
        "replace": "            got, _st = 0, 0\n",
        "matches": 1,
        # REG-2357 - its only catching cases are AnExecLeavesNoCorpse's, which skip off POSIX (os.execv replaces the
        # image only there): on Windows this proof files BLIND. Judged where POSIX is.
        "needs": "posix",
    },
    {
        "why": "#224 - the reaper thread never collects a child that was still alive at the exec and died later (the warm worker's own shape)",
        "file": "exec_hygiene.py",
        "find": "                        got, _st = os.waitpid(p, os.WNOHANG)\n",
        "replace": "                        got, _st = 0, 0\n",
        "matches": 1,
        # REG-2357 - its only catching cases are AnExecLeavesNoCorpse's, which skip off POSIX (os.execv replaces the
        # image only there): on Windows this proof files BLIND. Judged where POSIX is.
        "needs": "posix",
    },
    {
        "why": "#224 - the drift watcher's auto-relaunch execs without quiescing (the path that fired all 35 times)",
        "file": "control_app.py",
        "find": "                _before_exec('_drift_loop')\n",
        "replace": "",
        "matches": 1,
    },
]
