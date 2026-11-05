# -*- coding: utf-8 -*-
"""#229 — EACH CONSOLE SAYS ITS OWN SYSTEM TO THE FLEET: its tree, its shelf. Counts only.

The roadmap's last build item: from the fleet, see that every console stands on its own - whether its own tree
is established and how many reels sit on its own shelf - instead of assuming it. Three ends, one field, each
driven for real: the beacon builds it, the relay shapes it, the row's hover says it (his v2875 ruling: one word
on the row, the rest behind it).

  · DRIVEN (python): _system_for_wire reads the doctor's OWN tree verdict and counts reel_ folders; no eagle
    verdict -> tree None; an unreadable shelf -> reels None, never 0.
  · DRIVEN (node, the REAL shaper from console.js): known states and small integers cross; anything else -> null.
  · DRIVEN (node, the REAL _sysTxt from control_ui.html): the hover says established / NOT established /
    unmeasured and N reels or 'shelf UNKNOWN'; a console older than the field says nothing.
  · JOINED: the beacon sends it and both row branches carry it.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import control_app as ca  # noqa: E402
import worker_source as _ws  # noqa: E402  REG-1839 - the worker's top-level helpers, lifted with the shaper

NODE = shutil.which("node")


def _between(src, start, end):
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i:j + len(end)]


def _node(js):
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node could not run the shipped code - UNKNOWN, not passing: %s" % r.stderr[:400])
    return json.loads(r.stdout.strip().splitlines()[-1])


class TheBeaconBuildsIt(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sys-wire-")
        self._hist, self._rows = ca.HIST_DIR, list(ca._EAGLE.get("rows") or [])
        ca.HIST_DIR = self.d
        # 2026-09-28 — the system block now carries the triage lane, whose last walk is seeded from
        # the survey store: point that store at the fixture too, never at his tv/retro_triage.json
        self._env_hist, self._seed = os.environ.get("TV_HIST"), ca._TRIAGE_STORE_SEED
        os.environ["TV_HIST"] = self.d
        ca._TRIAGE_STORE_SEED = {"read": False, "ts": None, "why": ""}

    def tearDown(self):
        ca.HIST_DIR = self._hist
        ca._EAGLE["rows"] = self._rows
        ca._TRIAGE_STORE_SEED = self._seed
        if self._env_hist is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._env_hist
        shutil.rmtree(self.d, ignore_errors=True)

    @staticmethod
    def _counts(got):
        """The #229 half of the block. capture/river ride beside it since 2026-09-28 and have their
        own law (test_the_beacon_says_how_each_pc_films_and_drains)."""
        return {k: got[k] for k in ("tree", "reels")}

    def test_it_reads_the_doctor_and_counts_reels(self):
        for n in ("reel_a", "reel_b", "not_a_reel"):
            os.mkdir(os.path.join(self.d, n))
        open(os.path.join(self.d, "reel_file_not_dir"), "w").close()
        ca._EAGLE["rows"] = [{"check": "this console tree is established", "state": "ok"}]
        self.assertEqual(self._counts(ca._system_for_wire()), {"tree": "ok", "reels": 2})

    def test_no_verdict_and_no_shelf_are_unknown_not_zero(self):
        ca._EAGLE["rows"] = []
        ca.HIST_DIR = os.path.join(self.d, "no-such-shelf")
        self.assertEqual(self._counts(ca._system_for_wire()), {"tree": None, "reels": None})

    def test_the_beacon_sends_it(self):
        self.assertIn("_system_for_wire", ca._console_beacon.__code__.co_names,
                      "the beacon never sends the system block - the fleet cannot see it")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheRelayShapesIt(unittest.TestCase):

    def _shape(self, v):
        with io.open(os.path.join(ROOT, "functions", "api", "console.js"), encoding="utf-8") as f:
            src = f.read()
        fn = _between(src, "    system: (function (s) {", "    })(body.system),")
        fn = "(" + fn[len("    system: "):-len("(body.system),")] + ")"
        return _node(_ws.prelude(src) + "var shape = %s; console.log(JSON.stringify(shape(%s)));" % (fn, json.dumps(v)))

    def test_known_values_cross(self):
        self.assertEqual(self._shape({"tree": "ok", "reels": 25}), {"tree": "ok", "reels": 25})

    def test_anything_else_is_null(self):
        self.assertEqual(self._shape({"tree": "yes", "reels": -3}), {"tree": None, "reels": None})
        self.assertEqual(self._shape({"tree": None, "reels": "25"}), {"tree": None, "reels": None})
        self.assertIsNone(self._shape(None))


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheHoverSaysIt(unittest.TestCase):

    def setUp(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as f:
            self.ui = f.read()
        self.fn = _between(self.ui, "      var _sysTxt = function (m) {", "\n      };")

    def _say(self, m):
        return _node("%s; console.log(JSON.stringify(_sysTxt(%s)));" % (self.fn, json.dumps(m)))

    def test_the_three_tree_states_and_the_shelf(self):
        self.assertIn("own tree established", self._say({"system": {"tree": "ok", "reels": 25}}))
        self.assertIn("25 reels on its shelf", self._say({"system": {"tree": "ok", "reels": 25}}))
        self.assertIn("own tree NOT established", self._say({"system": {"tree": "missing", "reels": 0}}))
        self.assertIn("0 reels on its shelf", self._say({"system": {"tree": "missing", "reels": 0}}))
        self.assertIn("own tree unmeasured", self._say({"system": {"tree": None, "reels": None}}))
        self.assertIn("shelf UNKNOWN", self._say({"system": {"tree": None, "reels": None}}))

    def test_an_older_console_says_nothing(self):
        self.assertEqual(self._say({"ver": "v3400"}), "")

    def test_both_row_branches_carry_it(self):
        code = "\n".join(l.split("/*", 1)[0] for l in self.ui.split("\n"))
        self.assertEqual(code.count("escC(_sysTxt(m))"), 2, "an online or an offline row does not carry its system")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "#229 - the beacon stops sending the machine's own system: the fleet assumes every console stands alone",
        "file": "control_app.py",
        "find": "            \"system\": _system_for_wire(),\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#229 - an unreadable shelf reaches the fleet as 0 reels - an empty machine instead of an unread one",
        "file": "control_app.py",
        "find": "    except Exception:\n        out[\"reels\"] = None\n    out[\"repair\"] = _repair_for_wire()\n",
        "replace": "    except Exception:\n        out[\"reels\"] = 0\n    out[\"repair\"] = _repair_for_wire()\n",
        "matches": 1,
    },
    {
        "why": "#229 - the relay forwards a guessed state instead of null",
        "file": "functions/api/console.js",
        "find": "        tree: ['ok', 'missing', 'unmeasured', 'unknown'].indexOf(t) >= 0 ? t : null,\n",
        "replace": "        tree: t || 'ok',\n",
        "matches": 1,
    },
]
