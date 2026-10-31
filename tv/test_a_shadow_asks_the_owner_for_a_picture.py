# -*- coding: utf-8 -*-
"""v3849 - a shadow asks the owner's console whether a picture exists.

picture_status used to be refused like every /api/ call, and the panel asked
the viewer's _consoleOrigin. A shadow asks the owner origin on the snapshot,
GET only, or the snapshot's own picture map. With no frame it says
"no picture was saved for this item". The viewer's picture_status stays refused.
The non-shadow ask line stays the one the owned-door law pins.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable
enable()

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
NODE = shutil.which("node")
SRC = open(BIBLE, encoding="utf-8").read()
URL_LINE = "      var url = origin + '/api/picture_status?ids=' + encodeURIComponent(id);\n"
OWNER_LINE = "        origin = (snap && (snap.origin || snap.ownerOrigin)) || window._tvdShadow.origin || '';\n"
ALLOW = "      if (m === 'GET' && u.pathname === '/api/picture_status' && _shadowPictureOwner(u.origin)) return false;\n"
SAVED = "no picture was saved for this item"


def _fn_assign(src, start):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start[:48], src.count(start)))
    i = src.index(start)
    b = src.index("{", i)
    depth = 0
    j = b
    n = len(src)
    while j < n:
        c = src[j]
        if c in ("'", '"', "`"):
            q = c
            j += 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == q:
                    j += 1
                    break
                j += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = src.index(";", j)
                return src[i:end + 1]
        j += 1
    raise AssertionError("function never closed")


def _between(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start[:48], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start))]


BLOCKED = _between(SRC, "    function foreign(url) {", "    var realFetch = window.fetch;")
PICTURE = _fn_assign(SRC, "  window._vaultEvidencePicture = function(frameId, done, src){")

HARNESS = r"""
var fetches = [], asked = 0;
function fetch(url, opt){
  fetches.push({ url: String(url), method: (opt && opt.method) || 'GET' });
  return Promise.resolve({ ok: false, json: function(){ return Promise.resolve(null); } });
}
function _consoleOrigin(){ asked++; return 'http://127.0.0.1:17999'; }
var window = { location: { href: 'http://127.0.0.1/board', origin: 'http://127.0.0.1' } };
""" + BLOCKED + "\n" + PICTURE + r"""
function ask(id, setup){
  fetches = []; asked = 0;
  window._tvdShadow = null; window._tvdShadowSnap = null;
  setup();
  return new Promise(function(resolve){
    window._vaultEvidencePicture(id, function(p){
      resolve({ pic: p, fetches: fetches.slice(), asked: asked });
    });
  });
}
(async function(){
  var none = await ask('', function(){});
  var owner = await ask('3_1784984175075', function(){
    window._tvdShadow = { owner: 'owner' };
    window._tvdShadowSnap = { origin: 'http://owner.example' };
  });
  var mapped = await ask('3_1784984175075', function(){
    window._tvdShadow = { owner: 'owner' };
    window._tvdShadowSnap = { origin: 'http://owner.example', pictures: { '3_1784984175075': { why: 'reaped under the disk floor' } } };
  });
  var noOwn = await ask('3_1784984175075', function(){
    window._tvdShadow = { owner: 'owner' };
    window._tvdShadowSnap = { owner: 'owner' };
  });
  var home = await ask('9_1', function(){});
  window._tvdShadowSnap = { origin: 'http://owner.example' };
  window._tvdShadow = { origin: 'http://owner.example' };
  var gates = {
    ownerGet: blocked('http://owner.example/api/picture_status?ids=3_1784984175075', 'GET'),
    ownerPost: blocked('http://owner.example/api/picture_status?ids=3_1784984175075', 'POST'),
    ownerHead: blocked('http://owner.example/api/picture_status?ids=1', 'HEAD'),
    viewerGet: blocked('http://127.0.0.1/api/picture_status?ids=1', 'GET'),
    status: blocked('http://127.0.0.1/api/status', 'GET'),
    evil: blocked('http://evil.example/api/x', 'GET'),
    ping: blocked('http://127.0.0.1:17771/ping', 'GET'),
    font: blocked('/fonts/a.woff2', 'GET')
  };
  process.stdout.write(JSON.stringify({ none: none, owner: owner, mapped: mapped, noOwn: noOwn, home: home, gates: gates }));
})().catch(function(e){ console.error(e && e.stack || e); process.exit(1); });
"""


class AShadowAsksTheOwnerForAPicture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        r = subprocess.run([NODE, "-"], input=HARNESS, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if r.returncode != 0:
            raise AssertionError(r.stderr[-900:] or r.stdout[-400:])
        cls.o = json.loads(r.stdout)

    def test_no_frame_says_none_was_saved(self):
        self.assertEqual(self.o["none"]["pic"], {"state": "none", "say": SAVED})
        self.assertEqual(self.o["none"]["fetches"], [])
        self.assertEqual(SRC.count(URL_LINE), 1)

    def test_a_shadow_asks_the_owner_and_not_the_viewer(self):
        o = self.o["owner"]
        self.assertEqual(o["asked"], 0, "the shadow called the viewer's _consoleOrigin")
        self.assertEqual(len(o["fetches"]), 1)
        self.assertEqual(o["fetches"][0]["method"], "GET")
        self.assertTrue(o["fetches"][0]["url"].startswith("http://owner.example/api/picture_status?ids=3_1784984175075"), o["fetches"])
        self.assertEqual(self.o["mapped"]["fetches"], [])
        self.assertIn("disk floor", self.o["mapped"]["pic"]["say"])
        self.assertEqual(self.o["mapped"]["asked"], 0)
        self.assertEqual(self.o["noOwn"]["fetches"], [])
        self.assertEqual(self.o["noOwn"]["asked"], 0)
        self.assertIn("nobody was asked", self.o["noOwn"]["pic"]["say"])
        h = self.o["home"]
        self.assertEqual(h["asked"], 1)
        self.assertTrue(h["fetches"][0]["url"].startswith("http://127.0.0.1:17999/api/picture_status?ids="), h["fetches"])

    def test_only_a_get_of_the_owners_picture_status_is_open(self):
        g = self.o["gates"]
        self.assertIs(g["ownerGet"], False)
        self.assertIs(g["ownerPost"], True)
        self.assertIs(g["ownerHead"], True)
        self.assertIs(g["viewerGet"], True)
        self.assertIs(g["status"], True)
        self.assertIs(g["evil"], True)
        self.assertIs(g["ping"], True)
        self.assertIs(g["font"], False)
        self.assertEqual(SRC.count(OWNER_LINE), 1)
        self.assertEqual(SRC.count(ALLOW), 1)


RED_PROOF = [
    {"why": "v3849 - a shadow asks the viewer's console for the picture again",
     "file": "bible.html",
     "find": "        origin = (snap && (snap.origin || snap.ownerOrigin)) || window._tvdShadow.origin || '';\n",
     "replace": "        origin = _consoleOrigin();\n",
     "matches": 1},
    {"why": "v3849 - the owner's picture_status GET is refused with every other /api/ call",
     "file": "bible.html",
     "find": "      if (m === 'GET' && u.pathname === '/api/picture_status' && _shadowPictureOwner(u.origin)) return false;\n",
     "replace": "",
     "matches": 1},
    {"why": "v3849 - an empty frame stops saying that no picture was saved",
     "file": "bible.html",
     "find": "    if (!id) return end({ state: 'none', say: 'no picture was saved for this item' });\n",
     "replace": "    if (!id) return end({ state: 'none', say: 'no picture was recorded with this read' });\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
