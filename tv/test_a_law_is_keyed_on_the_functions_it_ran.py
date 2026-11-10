# -*- coding: utf-8 -*-
"""#92 (REG-3625) - A LAW IS KEYED ON THE FUNCTIONS IT RAN, NEVER ON ONES IT NEVER CALLED.

His 11-06 ask: a one-law fix must not re-prove half of 9,446 proofs. REG-3393 traced past children
that cannot read the tree, so a complete trace can drop files the run never opened. A file the run
DID open (heart2, the law itself) still put every byte in the key, so a wording change in an
uncalled helper discarded every proof (v3875 round 3 reused 0 of 9,446).

This keys a traced .py on the functions that actually started (sys.monitoring PY_START) plus the
module-level lines that always run on import. An uncalled function is not in the key. A function
that ran is. Module-level code is. A file the law opened as data (not as an import) keeps every
byte, so a narrow key cannot serve a stale proof over source it read. RED_PROOF below.
"""
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


SAMPLE = (
    "X = 1\n"
    "def used():\n"
    "    return X + 2\n"
    "\n"
    "def unused():\n"
    "    return 99\n"
    "\n"
    "class C:\n"
    "    def meth(self):\n"
    "        return used()\n"
)


def _ran_used():
    # firstlineno values from SAMPLE: used at 2, C.meth at 9
    return [("used", 2), ("C.meth", 9)]


class ALawIsKeyedOnTheFunctionsItRan(unittest.TestCase):

    def test_an_uncalled_function_is_not_in_the_key(self):
        """* THE POINT: a wording change in unused() must not discard a proof that never called it"""
        a = H._fn_digest(SAMPLE, _ran_used())
        b = H._fn_digest(SAMPLE.replace("return 99", "return 100"), _ran_used())
        self.assertEqual(a, b, "an uncalled function's body is still in the key")
        self.assertIsNotNone(a)

    def test_a_function_that_ran_is_in_the_key(self):
        a = H._fn_digest(SAMPLE, _ran_used())
        b = H._fn_digest(SAMPLE.replace("return X + 2", "return X + 3"), _ran_used())
        self.assertNotEqual(a, b, "a function that ran can change without the key seeing it")

    def test_module_level_code_is_in_the_key(self):
        a = H._fn_digest(SAMPLE, _ran_used())
        b = H._fn_digest(SAMPLE.replace("X = 1", "X = 7"), _ran_used())
        self.assertNotEqual(a, b, "module-level code can change without the key seeing it")

    def test_a_missing_function_is_not_silent(self):
        a = H._fn_digest(SAMPLE, _ran_used())
        b = H._fn_digest(SAMPLE, _ran_used() + [("gone", 99)])
        self.assertNotEqual(a, b, "a function the run named that is no longer in the file left the key unchanged")

    def test_a_source_read_is_not_narrowed(self):
        """opening a .py as data (not as an import) keeps every byte, including uncalled functions"""
        self.assertFalse(H._fn_narrows("tv/heart2.py", quoted={"heart2.py"}),
                         "a file the law opened as data was still function-narrowed")
        self.assertTrue(H._fn_narrows("tv/heart2.py", quoted=set()),
                        "an imported .py with no source-read was not offered for narrowing")
        self.assertFalse(H._fn_narrows("tv/control_ui.html", quoted=set()),
                         "a non-Python file was offered for function narrowing")

    def test_the_trace_site_records_the_functions_that_ran(self):
        """the real sitecustomize writes an F line for a function that started, and not for one that did not"""
        site = H._trace_site()
        self.assertIsNotNone(site, "no trace site could be written")
        root = tempfile.mkdtemp(prefix="h2fn.")
        try:
            dest = os.path.join(root, "mod.py")
            with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(SAMPLE)
            log = os.path.join(root, "trace.log")
            env = dict(os.environ, PYTHONPATH=site, HEART2_TRACE_LOG=log, HEART2_TRACE_SITE=site,
                       HEART2_TRACE_ROOT=root, MOD=dest)
            for k in [k for k in env if k.startswith("GIT_")]:
                env.pop(k)
            body = ("import importlib.util, os\n"
                    "p = os.environ['MOD']\n"
                    "s = importlib.util.spec_from_file_location('mod', p)\n"
                    "m = importlib.util.module_from_spec(s)\n"
                    "s.loader.exec_module(m)\n"
                    "m.used()\n")
            r = subprocess.run([sys.executable, "-c", body], env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, "the traced child failed: " + (r.stdout + r.stderr)[-800:])
            funcs, quoted, fn_on = set(), set(), set()
            why = set()
            seen, ok = H._trace_read(log, os.getpid(), why=why, sandbox=root,
                                     funcs=funcs, quoted=quoted, fn=fn_on)
            self.assertIn("on", fn_on, "the site did not say function monitoring was on: %r %r" % (why, fn_on))
            quals = {q for _path, _ln, q in funcs}
            self.assertIn("used", quals, "used() ran but was not recorded: %r" % funcs)
            self.assertNotIn("unused", quals, "unused() was recorded though it never ran: %r" % funcs)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_line_endings_do_not_change_the_function_key(self):
        """the same source with CRLF or LF is one key, so a Windows checkout does not re-prove a POSIX proof"""
        crlf = SAMPLE.replace("\n", "\r\n")
        self.assertEqual(H._fn_digest(SAMPLE, _ran_used()), H._fn_digest(crlf, _ran_used()),
                         "CRLF vs LF in an otherwise identical file produced two function keys")


RED_PROOF = [
    {"why": "REG-3625 - an uncalled function is hashed as if it ran, so a wording change discards every proof again",
     "file": "tv/heart2.py",
     "find": "    # REG-3625 - only the functions in `ran` (and module-level lines) enter the digest\n",
     "replace": "    ran = list(funcs)  # REG-3625 saboteur: every function is treated as if it ran\n    # REG-3625 - only the functions in `ran` (and module-level lines) enter the digest\n",
     "matches": 1},
    {"why": "REG-3625 - module-level lines are dropped from the digest, so an import-time change is not seen",
     "file": "tv/heart2.py",
     "find": "    for i in sorted(mod):\n",
     "replace": "    for i in ():\n",
     "matches": 1},
    {"why": "REG-3625 - a .py the law opened as data is still function-narrowed, so a stale proof can cover bytes it read",
     "file": "tv/heart2.py",
     "find": "    return bool(rel.endswith(\".py\") and os.path.basename(rel) not in (quoted or ()))\n",
     "replace": "    return bool(rel.endswith(\".py\"))\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
