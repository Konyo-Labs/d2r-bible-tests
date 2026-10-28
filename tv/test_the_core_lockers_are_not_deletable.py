# -*- coding: utf-8 -*-
"""REG-2195 — a CORE vault locker is never deletable. GrokBot batch K on v3718: "every core locker also has a
delete button, which is easy to hit by mistake." Deleting a core locker drops part of his taxonomy and sends
its items back to the dock. Now only a mule HE added (added:true from vaultAddMule, or the mint-id shape
'm'+base36 time that vaultAddMule stamps) gets a delete button, and window.vaultDeleteMule refuses a core
locker outright (defense-in-depth). `_vmAddedMule` is pure — cut from bible.html and run in node. NO node =
a declared skip, never a pass. RED_PROOF: a core id must read not-deletable, and BOTH wiring sites (the
button render and the door) must gate on `_vmAddedMule`.
"""
import io
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import sys as _sys
_sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
BIBLE = os.path.join(HERE, "..", "bible.html")
NODE = os.environ.get("NODE") or shutil.which("node")

FN = "  function _vmAddedMule(m){ return !!(m && (m.added || /^m[0-9a-z]{6,}$/.test(String(m.id)))); }\n"
CORE = ["uni-weap", "uni-armor", "uni-small", "sets-rest", "sets-major", "runewords",
        "bases", "magic-rare", "charms", "shared", "dupes", "wip"]   # REG-2895 - CHARMS is a core locker (his 2026-10-28 ruling)


def _src():
    return io.open(BIBLE, encoding="utf-8").read()


def _added(mule):
    if not NODE:
        raise AssertionError("node is not on this machine - this law does not skip")
    s = _src()
    if s.count(FN) != 1:
        raise AssertionError("anchor matched %d times - re-point this law" % s.count(FN))
    prog = FN + "\nconsole.log(JSON.stringify(_vmAddedMule(%s)));\n" % json.dumps(mule)
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        raise AssertionError("the cut helper did not run in node: " + r.stderr[-300:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class TheCoreLockersAreNotDeletable(unittest.TestCase):

    def test_no_core_locker_is_deletable(self):
        for cid in CORE:
            self.assertFalse(_added({"id": cid}), "core locker %s must NOT be deletable (REG-2195)" % cid)

    def test_a_mule_he_added_is_deletable(self):
        self.assertTrue(_added({"id": "m1a2b3c4d"}), "a mint-id added mule is deletable")
        self.assertTrue(_added({"id": "whatever", "added": True}), "the added:true flag makes it deletable")

    def test_both_wiring_sites_gate_on_the_added_check(self):
        s = _src()
        self.assertIn("(_vmAddedMule(m) ? '<button class=\"vm-tool\" onclick=\"event.stopPropagation();window.vaultDeleteMule(", s,
                      "the delete button must render only for a mule he added (REG-2195)")
        self.assertNotIn("(m.id==='shared' ? '' : '<button class=\"vm-tool\" onclick=\"event.stopPropagation();window.vaultDeleteMule(", s,
                         "the old 'every mule but shared' button condition must be gone (REG-2195)")
        self.assertIn("if (!_vmAddedMule(m)) return;", s,
                      "vaultDeleteMule must refuse a core locker outright (REG-2195)")

RED_PROOF = [
    {"why": "REG-2195 - the delete door stops refusing a core locker",
     "file": "bible.html",
     "find": "    if (!_vmAddedMule(m)) return;   // REG-2195 - a core locker is never deletable\n",
     "replace": "    if (false) return;   // REG-2195 - a core locker is never deletable\n",
     "matches": 1},
    {"why": "REG-2195 - every locker draws a delete button again, core lockers included",
     "file": "bible.html",
     "find": "(_vmAddedMule(m) ? '<button class=\"vm-tool\" onclick=\"event.stopPropagation();window.vaultDeleteMule(",
     "replace": "(true ? '<button class=\"vm-tool\" onclick=\"event.stopPropagation();window.vaultDeleteMule(",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
