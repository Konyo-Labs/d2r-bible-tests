# -*- coding: utf-8 -*-
"""REG-3818 (his 11-13: "also for the lock on VAULT is it unlocked already? or not yet?") - A DOOR UNPROVABLE BY DESIGN NEVER
SHUTS ITS GROUP'S PADLOCK. MEASURED on his Mac (v3903): vault.apply OPEN (proven 0.90), vault.sweep_start OPEN (0.90),
vault.forget shut "by design, nothing to sabotage" (provable: false). The Vault chip's _lockFor ranks its group worst-first,
so vault.forget painted the Vault padlock LOCKED over two open, proven doors. A member with provable === false is left out
of the vote unless it is the only member; a lock that is unproven (never sabotaged YET) still shuts the group.

DRIVEN: the shipped _lockFor cut from tv/control_ui.html and run in node over his Mac's rows. RED_PROOF below."""
import io
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402

ROWS = [{"lock": "vault.apply", "state": "OPEN", "permitted": True, "provable": None},
        {"lock": "vault.forget", "state": "UNPROVEN", "permitted": False, "provable": False},
        {"lock": "vault.sweep_start", "state": "OPEN", "permitted": True, "provable": None}]


def _run(rows, prefix):
    if NODE is None:
        raise AssertionError("node is not installed on this PC - this law runs the shipped chip rule in node and does not skip")
    with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
        src = fh.read()
    head = "      var _lockFor = function(prefix){"
    assert src.count(head) == 1, "PREMISE: _lockFor is declared %d times" % src.count(head)
    i = src.index(head)
    j = src.index("\n      };\n", i) + len("\n      };\n")
    js = ("var _sa = {}; var _saRows = %s;\n" % json.dumps(rows) + src[i:j]
          + "\nvar l = _lockFor(%s); process.stdout.write(JSON.stringify(l ? l.lock : null));" % json.dumps(prefix))
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr[-600:]
    return json.loads(r.stdout)


class ADoorUnprovableByDesignNeverShutsItsGroup(unittest.TestCase):

    def test_his_vault_reads_its_open_doors(self):
        """* THE POINT - his Mac's three vault rows: the chip speaks for an open, proven door, not vault.forget"""
        self.assertIn(_run(ROWS, "vault."), ("vault.apply", "vault.sweep_start"), "the by-design door shut the Vault padlock")

    def test_an_unproven_door_still_shuts_the_group(self):
        rows = ROWS + [{"lock": "vault.new", "state": "UNPROVEN", "permitted": False, "provable": None}]
        self.assertEqual(_run(rows, "vault."), "vault.new", "BASELINE: a door never sabotaged YET no longer shuts its group")

    def test_a_group_of_only_the_by_design_door_still_reads_it(self):
        self.assertEqual(_run([ROWS[1]], "vault."), "vault.forget", "a group with only a by-design door read as nothing")


RED_PROOF = [
    {"why": "REG-3818 - a door unprovable by design shuts the Vault padlock over two open, proven doors again",
     "file": "tv/control_ui.html",
     "find": "        if (_gated.length) mine = _gated;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
