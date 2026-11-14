# -*- coding: utf-8 -*-
"""v3906 (REG-3852, #223) - A MADE x LEAVES WHEN THE OVERLAY'S OWN CLOSE COMES BACK.

GrokBot #230 6866422963 (v3905, his console, 1512 / 1440 / 901): opening the Theatre straight in shows "✕ CLOSE" whole.
Opening the Shelf inside the Theatre and then a reel from it leaves a separate 28 px x (class "ovx-made ovx") pinned inside
CLOSE's right end, exactly over its last letter - "✕ CLOS ×" - and it survives closing and reopening the Theatre on the same
page. Cause (Claude's ASK 6865422998, not refuted): the Shelf hides CLOSE, the overlay contract's tick makes its own x for the
Theatre, and when CLOSE comes back the tick finds and pins CLOSE but never removes the x it made.

Driven in a real headless Chrome on the SHIPPED overlay-contract block (cut from control_ui.html byte for byte; the board
carries the identical copy, test_every_overlay_closes_the_same_way): a fixed Theatre stand-in with the real #th-close, the
tick run by hand - CLOSE shown, CLOSE hidden (the Shelf's route: a made x appears, as designed), CLOSE back (the made x must
be gone and CLOSE the only x). At 1512, 1440 and 901. No Chrome here is UNMEASURED, never a pass.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402 - a cp1255 console must survive its own report
_console_safe_enable()

UI = os.path.join(HERE, "control_ui.html")
BLOCK = re.compile(r"/\* OVERLAY-CONTRACT v3847.*?/\* /OVERLAY-CONTRACT \*/", re.S)
WIDTHS = (1512, 1440, 901)


import render_check as RC  # noqa: E402 - the one Chrome finder and CDP tab every render law uses

_CACHE = {}

_PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:#000;color:#ddd;font:14px system-ui,sans-serif}
.theatre{position:fixed;inset:64px 24px 24px 24px;background:#0b0906}  /* the console's Theatre sits in its stage (absolute, not the whole window) */
.theatre[hidden]{display:none}
.th-topline{position:relative;display:flex;justify-content:flex-end;padding:8px 12px;z-index:4}
.th-x{height:28px}
</style></head><body>
<div class="theatre" id="theatre">
  <div class="th-topline"><span class="th-rib">THEATRE · SESSION 4 · PAST REPLAY · NOT LIVE</span>
    <button class="th-x" id="th-close" type="button" style="width:auto;padding:0 12px">\u2715 CLOSE</button></div>
  <div style="height:600px"></div>
</div>
<pre id="out">pending</pre>
<script>%(block)s</script>
<script>
(function () {
  var th = document.getElementById('theatre'), close = document.getElementById('th-close'), res = {};
  function made() { return th.querySelectorAll('.ovx-made').length; }
  function cover() {
    var r = close.getBoundingClientRect(), hit = document.elementFromPoint(r.right - 6, r.top + r.height / 2);
    return hit && hit !== close && !close.contains(hit) ? (hit.className || hit.tagName) : '';
  }
  window.__tvOvxTick();
  res.straight = made();
  close.style.display = 'none';              /* the Shelf's route hides CLOSE */
  window.__tvOvxTick();
  res.hidden = made();
  close.style.display = '';                  /* a reel from the Shelf: CLOSE is back */
  window.__tvOvxTick(); window.__tvOvxTick();
  res.back = made();
  res.coveredBy = cover();
  th.hidden = true; window.__tvOvxTick();    /* close the Theatre and open it straight again on the same page */
  th.hidden = false; window.__tvOvxTick();
  res.reopened = made();
  document.getElementById('out').textContent = 'RESULT ' + JSON.stringify(res);
})();
</script></body></html>"""


def _results():
    """one scratch Chrome (render_check's), the stand-in page served from a temp dir, the tick driven at each width"""
    if "r" in _CACHE:
        return _CACHE["r"]
    with io.open(UI, encoding="utf-8") as fh:
        block = BLOCK.findall(fh.read())[0]
    res = {}
    with tempfile.TemporaryDirectory(prefix="tvd_ovx_made_") as d:
        page = os.path.join(d, "p.html")
        with io.open(page, "w", encoding="utf-8") as fh:
            fh.write(_PAGE % {"block": block})
        url = "file://" + page.replace(os.sep, "/") if os.name != "nt" else "file:///" + page.replace(os.sep, "/")
        RC.require_chrome()   # REG-3061 - a browser that will not start is UNKNOWN for this law (a VenueFault), never a red
        try:
            t = RC._Tab("about:blank")
            t.send("Page.enable")
            t.send("Runtime.enable")
            for w in WIDTHS:
                t.send("Emulation.setDeviceMetricsOverride", width=w, height=900, deviceScaleFactor=1, mobile=False)
                t.send("Page.navigate", url=url)
                got = None
                for _ in range(120):
                    time.sleep(0.25)
                    try:
                        got = t.ev("(document.getElementById('out')||{}).textContent||''")
                    except Exception:
                        got = None
                    if got and str(got).startswith("RESULT "):
                        break
                m = re.match(r"RESULT (\{.*\})$", str(got or ""))
                if not m:
                    raise AssertionError("the stand-in page gave no result at %d (%r) - UNKNOWN, not passing" % (w, got))
                res[w] = json.loads(m.group(1))
            try:
                t.close()
            except Exception:
                pass
        finally:
            RC._chrome_down()
    _CACHE["r"] = res
    return res


@unittest.skipUnless(os.path.exists(RC.CHROME or ""), "no Chrome on this machine - UNMEASURED, never a pass")
class AMadeXLeavesWhenCloseComesBack(unittest.TestCase):

    def test_close_is_the_only_x_after_the_shelf_route(self):
        for w in WIDTHS:
            res = _results()[w]
            with self.subTest(width=w):
                self.assertEqual(res["straight"], 0, "the Theatre opened straight got a made x beside CLOSE: %r" % res)
                self.assertEqual(res["hidden"], 1, "with CLOSE hidden the contract made no x (the design changed?): %r" % res)
                self.assertEqual(res["back"], 0, "CLOSE came back and the made x stayed - '\u2715 CLOS \u00d7': %r" % res)
                self.assertEqual(res["coveredBy"], "", "something sits over CLOSE's last letter: %r" % res)
                self.assertEqual(res["reopened"], 0, "the made x survived closing and reopening the Theatre: %r" % res)


RED_PROOF = [
    {"why": "REG-3852 - the overlay's own x is pinned and the made x is left in place (the v3905 contract)",
     "file": "tv/control_ui.html",
     "find": "    if (x && !x.classList.contains('ovx-made')) { ovxDropMade(card); if (ov !== card) ovxDropMade(ov); return x; }",
     "replace": "    if (x && !x.classList.contains('ovx-made')) return x;",
     "matches": 1},
    {"why": "REG-3852 - the drop finds nothing, so every made x survives",
     "file": "tv/control_ui.html",
     "find": "    var ms = el.querySelectorAll(':scope > .ovx-made');",
     "replace": "    var ms = [];",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
