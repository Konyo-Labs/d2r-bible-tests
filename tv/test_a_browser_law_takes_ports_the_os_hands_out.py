# -*- coding: utf-8 -*-
"""v3855 (REG-3128) - A BROWSER LAW TAKES THE PORTS THE OS HANDS OUT, NEVER FIXED ONES.

ROOT CAUSE OF A GATE COLLISION. test_shadow_mode_draws_their_console served its page on a fixed 17975 and drove Chrome on a fixed
17976. When a second tree (a parallel shard, another seat's pre-check, or the hook) ran the same law at the same moment, one
of them found the port taken and setUpClass died - v3853 push 8 went red there, green alone. Its user-data-dir was already a
fresh mkdtemp; only the ports were shared. It now takes _free_ports(2), as test_v3769 and test_v3771 already did.

This law reads every tv/test_*.py that launches Chrome with --remote-debugging-port and refuses a module-level
HTTP_PORT / CDP_PORT bound to a literal number.
"""
import glob
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

_FIXED = re.compile(r"^(?:HTTP_PORT|CDP_PORT)\s*=\s*\d+\s*(?:#.*)?$", re.M)


def fixed_port_laws(folder=HERE):
    """[file name] of browser laws that pin a literal port at module level."""
    out = []
    for path in sorted(glob.glob(os.path.join(folder, "test_*.py"))):
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        if "remote-debugging-port" in src and _FIXED.search(src):
            out.append(os.path.basename(path))
    return out


class ABrowserLawTakesFreePorts(unittest.TestCase):
    def test_no_browser_law_pins_a_port(self):
        self.assertEqual(fixed_port_laws(), [], "a browser law pins a literal port; take _free_ports(2)")

    def test_the_shadow_law_takes_free_ports(self):
        with io.open(os.path.join(HERE, "test_shadow_mode_draws_their_console.py"), encoding="utf-8") as fh:
            self.assertIn("HTTP_PORT, CDP_PORT = _free_ports(2)  # SHADOW-FREE-PORTS", fh.read())

    def test_the_reader_sees_a_pinned_port(self):
        import tempfile, shutil
        d = tempfile.mkdtemp(prefix="ports.")
        self.addCleanup(shutil.rmtree, d, True)
        with io.open(os.path.join(d, "test_x.py"), "w", encoding="utf-8") as fh:
            fh.write('CDP_PORT = 17976\nARGS = ["--remote-debugging-port=%d" % CDP_PORT]\n')
        self.assertEqual(fixed_port_laws(d), ["test_x.py"])


_F = "test_shadow_mode_draws_their_console.py"
RED_PROOF = [{'why': 'the shadow law pins 17975/17976 again',
  'file': 'test_shadow_mode_draws_their_console.py',
  'find': 'HTTP_PORT, CDP_PORT = _free_ports(2)  # SHADOW-FREE-PORTS\n',
  'replace': 'HTTP_PORT = 17975\nCDP_PORT = 17976\n',
  'matches': 1},
 {'why': 'the reader never matches a pinned port',
  'file': 'test_a_browser_law_takes_ports_the_os_hands_out.py',
  'find': '        if "remote-debugging-port" in src and _FIXED.search(src):\n',
  'replace': '        if False:\n',
  'matches': 1}]

if __name__ == "__main__":
    unittest.main(verbosity=1)
