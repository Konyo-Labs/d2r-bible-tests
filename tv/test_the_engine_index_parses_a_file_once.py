# -*- coding: utf-8 -*-
"""v3859 (e): `run_gates.py --full` is faster with no law dropped. blueprint.engine_index() parses each tv/*.py once
per process.

MEASURED: test_the_blueprint_names_the_engine took 147 s. 117 s of that was engine_index(), which its six tests and
render() ask 8 times, and each ask ast-parsed and walked every tv/*.py again. Now each file's import list is kept by
its stat (mtime_ns and size). A moved file is parsed again, and the answer equals a parse from scratch. The law took
22-31 s after the change.

RED_PROOF below: each one, applied, turns this law red."""
import ast
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()


class OneParse(unittest.TestCase):

    def test_a_second_ask_parses_nothing(self):
        import blueprint as B
        B._IMPORTS_SEEN.clear()
        calls = []
        real = ast.parse

        def counting(*a, **k):
            calls.append(1)
            return real(*a, **k)
        ast.parse = counting
        try:
            r1 = B.engine_index()
            n1 = len(calls)
            r2 = B.engine_index()
        finally:
            ast.parse = real
        self.assertGreater(n1, 100)
        self.assertEqual(n1, len(calls), "the second engine_index() parsed %d files again" % (len(calls) - n1))
        self.assertEqual(r1, r2)

    def test_a_moved_file_is_parsed_again(self):
        import blueprint as B
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "m.py")
            open(p, "w").write("import alpha\n")
            self.assertEqual(("alpha",), B._imports_of(p, ast))
            time.sleep(0.01)
            open(p, "w").write("import beta, gamma\n")
            os.utime(p, ns=(time.time_ns(), time.time_ns() + 5_000_000))
            self.assertEqual(("beta", "gamma"), B._imports_of(p, ast))
            open(p, "w").write("from delta.x import y\n")
            os.utime(p, ns=(time.time_ns(), time.time_ns() + 9_000_000))
            self.assertEqual(("delta",), B._imports_of(p, ast))
        finally:
            shutil.rmtree(d, True)

    def test_the_kept_answer_equals_a_fresh_one(self):
        import blueprint as B
        B.engine_index()
        rows, drift = B.engine_index()
        B._IMPORTS_SEEN.clear()
        self.assertEqual((rows, drift), B.engine_index())


RED_PROOF = [
    {"why": "every ask parses every file again",
     "file": "tv/blueprint.py",
     "find": "    if hit and hit[0] == key:\n        return hit[1]\n",
     "replace": "", "matches": 1},
    {"why": "a moved file keeps its old import list",
     "file": "tv/blueprint.py",
     "find": "    if hit and hit[0] == key:\n",
     "replace": "    if hit:\n", "matches": 1},
    {"why": "a from-import is no longer read",
     "file": "tv/blueprint.py",
     "find": "            names.append(node.module.split(\".\")[0])\n",
     "replace": "            pass\n", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
