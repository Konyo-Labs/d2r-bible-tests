# -*- coding: utf-8 -*-
"""v3893 (#193, REG-3553) - THE GUEST BOARD BUILD BADGE READS THE LIVE API VERSION.

The badge was painted from bible.html's D2R_BUILD, which is baked into a cached page and can lag
the running console (guest showed v3888 while /api/status and the Fleet said v3889). His ruling:
the badge must read the exact version from the live API (st.ver). A failed fetch, a public page
with no console, or a payload without ver never claims a live version — the baked stamp stays.

Law: applying a status object whose ver is v3889 paints that id; a missing or junk ver leaves the
baked text alone; /api/status's success path calls the painter and its failure path does not.
RED_PROOF below.
"""
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()


def _bible():
    with open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _apply_src(html):
    i = html.index("window._badgeApplyLiveVer = function(el, st, baked){")
    j = html.index("  };\n  window._badgePaintLive", i)
    return html[i:j + 4]


class TheBadgeTakesTheLiveVersion(unittest.TestCase):

    def test_a_live_ver_replaces_the_baked_stamp_and_a_failed_payload_does_not(self):
        html = _bible()
        fn = _apply_src(html)
        js = (
            "const apply = (function(){ var window = {}; " + fn + "; return window._badgeApplyLiveVer; })();\n"
            "function el(text){ return { textContent: text, attrs: {},\n"
            "  setAttribute: function(k,v){ this.attrs[k]=v; },\n"
            "  getAttribute: function(k){ return this.attrs[k]; } }; }\n"
            "const baked = { id: 'v3888', name: 'v3888 - Game Door', date: '2026-11-09', note: 'baked' };\n"
            "const a = el(baked.id + ' · ' + baked.date + ' · Game Door');\n"
            "const ok = apply(a, { ver: 'v3889' }, baked);\n"
            "const b = el(a.textContent);\n"
            "const no = apply(b, { ver: '' }, baked);\n"
            "const c = el(a.textContent);\n"
            "const junk = apply(c, { ver: 'not-a-build' }, baked);\n"
            "process.stdout.write(JSON.stringify({ ok: ok, text: a.textContent, live: a.attrs['data-live-ver'],\n"
            "  no: no, junk: junk, kept: b.textContent, junkKept: c.textContent }));\n"
        )
        r = subprocess.run(["node", "-"], input=js, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        import json
        got = json.loads(r.stdout)
        self.assertTrue(got["ok"])
        self.assertTrue(got["text"].startswith("v3889"), got)
        self.assertIn("2026-11-09", got["text"])
        self.assertEqual(got["live"], "v3889")
        self.assertFalse(got["no"])
        self.assertFalse(got["junk"])
        self.assertEqual(got["kept"], got["text"])
        self.assertEqual(got["junkKept"], got["text"])

    def test_the_status_success_path_paints_and_a_failed_fetch_does_not(self):
        html = _bible()
        i = html.index("function _eagleNYFetch(){")
        block = html[i:html.index("window.renderInbox = function(){", i)]
        self.assertIn("window._badgePaintLive(d)", block)
        self.assertIn("base + '/api/status'", block)
        catch = block[block.index(".catch(function(err){"):]
        self.assertNotIn("_badgePaintLive", catch)
        self.assertIn("if (base === null){ _eagleNYPaint(); return; }", block)


RED_PROOF = [
    {"why": "v3893 (#193, REG-3553) - a live st.ver is ignored and the baked D2R_BUILD stays",
     "file": "bible.html",
     "find": "    if (!/^v\\d/.test(v)) return false;\n",
     "replace": "    return false;\n",
     "matches": 1},
    {"why": "v3893 (#193, REG-3553) - a failed /api/status fetch still claims a live version, or a success never paints one",
     "file": "bible.html",
     "find": "          try { if (window._badgePaintLive) window._badgePaintLive(d); } catch (e) {}\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
