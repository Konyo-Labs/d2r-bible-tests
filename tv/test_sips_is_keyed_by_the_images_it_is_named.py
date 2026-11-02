# -*- coding: utf-8 -*-
"""v3855 (REG-3125) - SIPS IS KEYED BY THE IMAGES IT IS NAMED, NOT CALLED A CHILD NOBODY CAN FOLLOW.

GATE SPEED. On the v3853 hook 5 gates were "not stored - the gate started sips" and so ran on every push
(gate_costs.json: test_simulator_says_what_it_could_not_load 25.2 s, test_an_unread_test_is_not_a_clean_verdict
7.0 s, test_agent 9.9 s, ...; about 43 s idle). sips opens only the image paths on its command line, so the trace
now records each one inside this checkout as a READ (and the one after -o/--out as a WRITE). A sips that converts a
fixture in a temp folder reads nothing here. The gate is carried only while those images are unchanged - an image
it was named that moves still re-runs the gate, which is the point of the R line.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import gate_ledger as GL  # noqa: E402

_CHILD = ("import subprocess, sys\n"
          "try:\n"
          "    subprocess.run(sys.argv[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)\n"
          "except (OSError, subprocess.TimeoutExpired):\n"
          "    pass\n")


class SipsIsKeyedByItsImages(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="sips.")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.away = tempfile.mkdtemp(prefix="sips-away.")
        self.addCleanup(shutil.rmtree, self.away, True)
        os.makedirs(os.path.join(self.root, "tv", "art"))
        self.law = os.path.join(self.root, "tv", "t_child.py")
        with io.open(self.law, "w", encoding="utf-8") as fh:
            fh.write(_CHILD)

    def _trace(self, *argv):
        trace = GL.trace_path()
        self.addCleanup(lambda: os.path.exists(trace) and os.remove(trace))
        env = GL.trace_env(dict(os.environ), self.root, trace)
        subprocess.run([sys.executable, self.law] + list(argv), cwd=self.root, env=env,
                       capture_output=True, text=True, timeout=60)
        return GL.read_trace(trace)

    def test_an_image_here_is_a_read_and_the_gate_stays_traced(self):
        facts, why = self._trace("sips", "-s", "format", "jpeg", os.path.join(self.root, "tv", "art", "a.png"))
        self.assertIsNone(why)
        self.assertIn("tv/art/a.png", facts["R"])

    def test_a_relative_image_is_read_from_the_childs_folder(self):
        facts, why = self._trace("sips", "-g", "pixelWidth", "tv/art/b.png")
        self.assertIsNone(why)
        self.assertIn("tv/art/b.png", facts["R"])

    def test_the_out_path_here_is_a_write(self):
        facts, why = self._trace("sips", "-s", "format", "jpeg", os.path.join(self.away, "in.png"),
                                 "--out", os.path.join(self.root, "tv", "art", "c.jpg"))
        self.assertIsNone(why)
        self.assertIn("tv/art/c.jpg", facts["W"])
        self.assertNotIn("tv/art/c.jpg", facts["R"])

    def test_a_fixture_elsewhere_reads_nothing_here(self):
        facts, why = self._trace("sips", "-s", "format", "jpeg", os.path.join(self.away, "in.png"),
                                 "-o", os.path.join(self.away, "out.jpg"))
        self.assertIsNone(why)
        self.assertEqual(set(), set(p for p in facts["R"] if p.startswith("tv/art")))

    def test_another_image_tool_still_untraces(self):
        _facts, why = self._trace("convert", os.path.join(self.root, "tv", "art", "a.png"), "x.jpg")
        self.assertIn("started convert", why or "")

    def test_wilson_of_these_attacks_meets_the_bar(self):
        import confidence
        self.assertGreaterEqual(len(RED_PROOF), 6)
        self.assertGreaterEqual(confidence.wilson_lower(len(RED_PROOF), len(RED_PROOF)), 0.5)


_F = "gate_trace/sitecustomize.py"
RED_PROOF = [
    {"why": "sips still untraces the gate", "file": _F,
     "find": "        if head == \"sips\":\n", "replace": "        if head == \"no-sips\":\n", "matches": 1},
    {"why": "an image here is not recorded as read", "file": _F,
     "find": "                    emit(\"W\" if out_next else \"R\", r)",
     "replace": "                    out_next and emit(\"W\", r)", "matches": 1},
    {"why": "the out path is recorded as a read", "file": _F,
     "find": "                    emit(\"W\" if out_next else \"R\", r)",
     "replace": "                    emit(\"R\", r)", "matches": 1},
    {"why": "a relative image is read from the wrong folder", "file": _F,
     "find": "                r = rel(a if isabs(a) else join(base, a))\n",
     "replace": "                r = rel(a) if isabs(a) else None\n", "matches": 1},
    {"why": "--out is not seen as the out flag", "file": _F,
     "find": "                    out_next = a in (\"-o\", \"--out\")\n",
     "replace": "                    out_next = a in (\"-o\",)\n", "matches": 1},
    {"why": "every child is treated as sips", "file": _F,
     "find": "        if head == \"sips\":\n", "replace": "        if head in (\"sips\", \"convert\"):\n", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=1)
