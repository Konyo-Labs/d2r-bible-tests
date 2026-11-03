# -*- coding: utf-8 -*-
"""v3859 B3 (#230, Claude slice 1) - A SHADOW FETCHES ITS OWNER'S WITNESS FRAMES THROUGH ITS OWN READ-ONLY SHIM.

_tvdFrameBoot asks GET /api/roster-cache?frames=<owner>, but by then the SHADOW MODE BOOT shim had replaced window.fetch
and refused every same-origin /api/ path but picture_status: {ok:false, why:'shadow: read only'}, so a witness in Dean's
shadow still showed words only. test_a_shadow_witness_frame_is_the_owners stubs window.fetch and never met the shim.
This law runs the page's own boot block in node and calls the boot THROUGH the real shim: the owner's frames read passes
and fills the witness map; any other owner, an extra parameter, or a POST is still refused. RED_PROOF below."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()
import test_shadow_mode_reads_their_console as T  # noqa: E402

JS = r"""
const fs = require('fs');
const CFG = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const html = fs.readFileSync(CFG.bible, 'utf8');
const at = html.indexOf('/* SHADOW MODE BOOT');
const code = html.slice(html.lastIndexOf('<script>', at) + 8, html.indexOf('</script>', at));
const realLS = { setItem() { throw new Error('real localStorage touched'); }, getItem() { throw new Error('real localStorage read'); } };
const sent = [];
class Resp { constructor(b, o) { this.body = b; this.status = (o && o.status) || 200; } async json() { return JSON.parse(this.body); } async text() { return this.body; } }
const doc = { readyState: 'loading', documentElement: { classList: { list: [], add(c) { this.list.push(c); } } }, head: { appendChild() {} },
  createElement() { return { textContent: '' }; }, write() {}, addEventListener() {} };
const win = { location: { search: '?app=1&tvd-shadow=1', href: 'http://127.0.0.1/board?app=1&tvd-shadow=1', origin: 'http://127.0.0.1', protocol: 'http:' },
  parent: null, stop() {}, open() {},
  fetch: (u, i) => { sent.push([String(u), (i && i.method) || 'GET']);
    return Promise.resolve(new Resp(JSON.stringify({ ok: true, frames: { f_1: 'data:image/jpeg;base64,AA' } }))); } };
const host = { _tvdShadowSnap: CFG.snap, postMessage() {} }; win.parent = host;
Object.defineProperty(win, 'localStorage', { configurable: true, get: () => realLS });
Object.defineProperty(win, 'sessionStorage', { configurable: true, get: () => realLS });
const XHR = function () {}; XHR.prototype.open = function () {}; XHR.prototype.send = function () {};
const f = new Function('window', 'document', 'localStorage', 'XMLHttpRequest', 'navigator', 'Response', 'URL', 'location',
                       'with (window) {' + code + '}');
const res = { threw: null };
try { f(win, doc, undefined, XHR, { sendBeacon() { return true; } }, Resp, URL, win.location); } catch (e) { res.threw = String(e.message || e); }
(async () => {
  const w = win, own = w._tvdShadow && w._tvdShadow.owner;
  res.owner = own || null;
  res.took = null;
  w._tvdShadowWitnessTake = function (d) { res.took = d; };
  w._tvdFrameBoot();
  await new Promise((r) => setTimeout(r, 50));
  const ask = async (u, m) => (await (await w.fetch(u, { method: m || 'GET' })).text());
  const n0 = sent.length;
  res.other = await ask('/api/roster-cache?frames=' + encodeURIComponent('Somebody Else'));
  res.extra = await ask('/api/roster-cache?frames=' + encodeURIComponent(own) + '&x=1');
  res.post = await ask('/api/roster-cache?frames=' + encodeURIComponent(own), 'POST');
  res.plain = await ask('/api/roster-cache');
  res.leaked = sent.slice(n0);
  res.sent = sent;
  process.stdout.write(JSON.stringify(res));
})();
"""


@unittest.skipUnless(T.NODE, "node is absent - the boot block cannot be run here, so it is UNMEASURED")
class AShadowFetchesItsOwnersWitnessFrames(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        snap = {"owner": T.OWNER, "t": T.T0, "stores": dict(T._wstores())}
        with tempfile.TemporaryDirectory(prefix="tvd_shadow_frames_") as d:
            c = os.path.join(d, "cfg.json")
            with io.open(c, "w", encoding="utf-8") as fh:
                json.dump({"bible": os.path.join(HERE, "..", "bible.html"), "snap": snap}, fh)
            out = subprocess.run([T.NODE, "-", c], input=JS, capture_output=True, text=True, encoding="utf-8",
                                 errors="replace", timeout=120)
        if out.returncode != 0 or not out.stdout.strip():
            raise AssertionError("the boot block did not run: %s" % out.stderr[-2000:])
        cls.r = json.loads(out.stdout)

    def test_the_owners_frames_reach_the_witness_map(self):
        r = self.r
        self.assertIsNone(r["threw"], r)
        self.assertTrue(r["owner"], "PREMISE: the boot set no shadow owner: %r" % r)
        self.assertTrue(any(u.startswith("/api/roster-cache?frames=") for u, _m in r["sent"]),
                        "the shim refused the owner's own witness-frame read: %r" % r["sent"])
        self.assertEqual((r["took"] or {}).get("frames"), {"f_1": "data:image/jpeg;base64,AA"},
                         "the witness map was never filled: %r" % r["took"])

    def test_anything_else_is_still_read_only(self):
        r = self.r
        self.assertEqual(r["leaked"], [], "the allowance let another read or a write through: %r" % r["leaked"])
        for k in ("other", "extra", "post", "plain"):
            self.assertIn("shadow: read only", r[k], "%s was not refused: %r" % (k, r[k]))


RED_PROOF = [
    {"why": "v3859 B3 - the shim refuses the shadow's own witness-frame read",
     "file": "bible.html",
     "find": "          && u.searchParams.get('frames') === String(window._tvdShadow.owner)) return false;\n",
     "replace": "          && u.searchParams.get('frames') === String(window._tvdShadow.owner)) return true;\n",
     "matches": 1, "needs": "node"},
    {"why": "v3859 B3 - the allowance lets any owner's frames through",
     "file": "bible.html",
     "find": "          && u.searchParams.get('frames') === String(window._tvdShadow.owner)) return false;\n",
     "replace": "          ) return false;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
