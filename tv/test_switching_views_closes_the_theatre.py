# -*- coding: utf-8 -*-
"""#172 — HIS RULING 2026-09-25: SWITCHING VIEWS CLOSES THE THEATRE.

The theatre deliberately covers every non-Sessions view while it is open. The seat's "freeze" on #230 was never a
paint freeze: its driver reopened the theatre, went to the Vault, and what covered the vault was the theatre's own
film stage (THEATRE_FILM_STAGE; a «-back close returned the shelf at ~184k). Asked, he ruled: switching views
should close it. Measured on a scratch console with fixture film: open -> click Vault -> TH.open false, #theatre
hidden, body.theatre-open gone; clicking the tab already showing leaves it open.

  · DRIVEN (node, the SHIPPED guard cut from the header-tab handler, with a stub TH/thClose): a different tab
    closes an open theatre; the same tab, or a closed theatre, calls nothing.
  · JOINED: thClose is exported on window beside thOpen, which is how the handler reaches it.
  · The browser half runs on CI in tests/v877_rinse.spec.ts against a real console with film.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

NODE = shutil.which("node")
START = "    try {\n      /* #172 / v3893 - SWITCHING views closes the theatre."
END = "    } catch (_tc) {}\n"


def _ui():
    with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as f:
        return f.read()


def _guard(src):
    assert src.count(START) == 1, "the #172 guard is not where this law looks (%d)" % src.count(START)
    i = src.index(START)
    return src[i:src.index(END, i) + len(END)]


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class SwitchingViewsClosesTheTheatre(unittest.TestCase):

    def _run(self, open_, tab, current):
        js = ("var closed = 0; var window = {TH: {open: %s}, thClose: function(){ closed++; }};\n"
              "var b = {dataset: {tab: %s}}; var _shellTab = %s;\n%s\nconsole.log(JSON.stringify(closed));"
              % (json.dumps(open_), json.dumps(tab), json.dumps(current), _guard(_ui())))
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("the shipped guard would not run - UNKNOWN, not passing: %s" % r.stderr[:300])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_a_different_view_closes_an_open_theatre(self):
        self.assertEqual(self._run(True, "vault", "tvd"), 1, "going to the Vault left the theatre over it")

    def test_the_view_already_showing_leaves_it_open(self):
        self.assertEqual(self._run(True, "tvd", "tvd"), 0)

    def test_a_click_on_tvd_stays_on_the_theatres_home(self):
        # v3893 - the theatre belongs to TV·D; _shellTab can lag after the Sessions homepage boot
        self.assertEqual(self._run(True, "tvd", "session"), 0, "clicking TV·D closed its own theatre")

    def test_a_closed_theatre_is_not_closed_again(self):
        self.assertEqual(self._run(False, "vault", "tvd"), 0)

    def test_thClose_is_reachable_from_the_handler(self):
        self.assertEqual(_ui().count("  window.thClose = thClose;"), 1, "thClose is not exported on window")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "#172 - switching views leaves the theatre open over the new view again (his 'dark glass')",
        "file": "control_ui.html",
        "find": "          && typeof window.thClose === 'function') window.thClose();\n",
        "replace": "          && false) window.thClose();\n",
        "matches": 1,
    },
    {
        "why": "#172 - thClose is not exported: the handler's guard can never reach it",
        "file": "control_ui.html",
        "find": "  window.thClose = thClose;   // #172",
        "replace": "  window._thCloseGone = thClose;   // #172",
        "matches": 1,
    },
]
