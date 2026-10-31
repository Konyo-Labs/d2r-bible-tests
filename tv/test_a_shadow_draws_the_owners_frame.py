# -*- coding: utf-8 -*-
"""v3849 (a) - a shadow draws the OWNER's frame, never the viewer's.

The snapshot carries the owner's picture map and the address their console answers on
(d2r_api_pictures, closed shapes by console_snapshot.pictures_of). In a shadow every frame
path is that address + the path; with no address there is no picture (null), never a relative
path that the viewer's own console would answer. Read only.
"""
import inspect
import json
import os
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable
enable()

import console_snapshot as cs
import control_app as ca

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
NODE = shutil.which("node")
SRC = open(BIBLE, encoding="utf-8").read()


def _between(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start[:48], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start))]


SEED = _between(SRC, "    var _pics = null;\n", "    window._tvdShadow = { owner:")
URL = _between(SRC, "  window._shadowOwnerUrl = function(path){", "  /* #36 (REG-2908")

BODY = r"""
var out = {};
var window = {};
function seedOf(seed){ %SEED%
  return { origin: _porg, pictures: (_pics && _pics.pictures && typeof _pics.pictures === 'object') ? _pics.pictures : null }; }
%URL%
out.plain = window._vaultLookSrc({ frame: 'f_1.jpg', session: 's_1' });
var sh = seedOf({ d2r_api_pictures: JSON.stringify({ ok: true, pictures: { f_1: { present: true } }, origin: 'http://owner.example:17772' }) });
out.seedOrigin = sh.origin; out.seedPics = sh.pictures;
out.badSeed = seedOf({ d2r_api_pictures: JSON.stringify({ ok: true, pictures: {}, origin: 'javascript:alert(1)' }) }).origin;
window._tvdShadow = { owner: 'him', origin: sh.origin, pictures: sh.pictures };
out.shadow = window._vaultLookSrc({ frame: 'f_1.jpg', session: 's_1' });
out.viewerAbs = window._shadowOwnerUrl('http://127.0.0.1:17772/tv/frames/hist/x.jpg');
out.dataUrl = window._shadowOwnerUrl('data:image/jpeg;base64,AA');
window._tvdShadow = { owner: 'him', origin: '' };
out.noOrigin = window._vaultLookSrc({ frame: 'f_1.jpg', session: 's_1' });
console.log(JSON.stringify(out));
"""


def run_js(seed=SEED, url=URL):
    if not NODE:
        raise unittest.SkipTest("node missing")
    body = BODY.replace("%SEED%", seed).replace("%URL%", url)
    r = subprocess.run([NODE, "-e", body], capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class TestShadowDrawsTheOwnersFrame(unittest.TestCase):
    def test_the_snapshot_carries_the_picture_map_and_a_real_address(self):
        got = cs.pictures_of({"ok": True, "pictures": {"f_1": {"present": True, "code": "ok", "why": None},
                                                       "f_2": {"present": "yes"}},
                              "origin": "http://owner.example:17772"})
        self.assertEqual(got["origin"], "http://owner.example:17772")
        self.assertEqual(got["pictures"]["f_1"]["present"], True)
        self.assertIsNone(got["pictures"]["f_2"]["present"])
        self.assertNotIn("origin", cs.pictures_of({"ok": True, "pictures": {}, "origin": "file:///etc"}))
        self.assertIsNone(cs.pictures_of({"ok": False}))
        name, body = cs.api_store("pictures", {"ok": True, "pictures": {"f_1": {"present": True}},
                                               "origin": "http://owner.example:17772"})
        self.assertEqual(name, "d2r_api_pictures")
        self.assertEqual(json.loads(body)["origin"], "http://owner.example:17772")

    def test_the_owner_asks_about_the_frames_his_vault_cites(self):
        stores = {"d2r_magicFinds": json.dumps({"Shako": {"frameId": "f_9"}}),
                  "d2r_vaultProv": json.dumps({"Shako": {"frameId": "f_9", "looks": [{"frame": "f_8"}]}})}
        self.assertEqual(ca._profile_picture_ids(stores), ["f_9", "f_8"])
        self.assertIn('("pictures", _profile_pictures)', inspect.getsource(ca._profile_api_answers))

    def test_a_shadow_frame_is_the_owners_address_or_nothing(self):
        o = run_js()
        self.assertEqual(o["plain"], "tv/frames/hist/reel_s_1/f_1.jpg")
        self.assertEqual(o["seedOrigin"], "http://owner.example:17772")
        self.assertEqual(o["seedPics"], {"f_1": {"present": True}})
        self.assertEqual(o["badSeed"], "")
        self.assertEqual(o["shadow"], "http://owner.example:17772/tv/frames/hist/reel_s_1/f_1.jpg")
        self.assertIsNone(o["viewerAbs"])
        self.assertIsNone(o["dataUrl"])
        self.assertIsNone(o["noOrigin"])

    def test_the_evidence_probe_walks_only_owner_urls_in_a_shadow(self):
        self.assertEqual(SRC.count("if (window._tvdShadow) chain = chain.map(function(u){ return window._shadowOwnerUrl(u); })"), 1)


RED_PROOF = [
    {"why": "no address check: a hostile origin rides in", "file": "bible.html",
     "find": "/^https?:\\/\\/[A-Za-z0-9][A-Za-z0-9.\\-]*(?::\\d{1,5})?$/.test(_pics.origin)) ? _pics.origin : ''",
     "replace": "_pics.origin) ? _pics.origin : ''"},
    {"why": "shadow returns the relative path the viewer's console answers", "file": "bible.html",
     "find": "    if (!window._tvdShadow) return p || null;\n", "replace": "    return p || null;\n"},
    {"why": "no owner address falls back to the viewer's path", "file": "bible.html",
     "find": "    if (!/^https?:\\/\\//.test(org)) return null;\n", "replace": "    if (!/^https?:\\/\\//.test(org)) return p;\n"},
    {"why": "the reel path skips the owner's address", "file": "bible.html",
     "find": "    return (window._tvdShadow && typeof window._shadowOwnerUrl === 'function') ? window._shadowOwnerUrl(_rel) : _rel;",
     "replace": "    return _rel;"},
    {"why": "a viewer-absolute URL is let through", "file": "bible.html",
     "find": "return p.indexOf(org + '/') === 0 ? p : null;", "replace": "return p;"},
    {"why": "the probe chain is not re-pointed in a shadow", "file": "bible.html",
     "find": "    if (window._tvdShadow) chain = chain.map(", "replace": "    if (false) chain = chain.map("},
    {"why": "snapshot drops the origin", "file": "tv/console_snapshot.py",
     "find": "        out[\"origin\"] = org\n    return out", "replace": "        pass\n    return out"},
    {"why": "look frames are not asked about", "file": "tv/control_app.py",
     "find": "                        _add(lk.get(\"frame\"))", "replace": "                        pass"},
    {"why": "the shadow never reads the owner's pictures", "file": "tv/control_app.py",
     "find": ', ("pictures", _profile_pictures))):', "replace": ')):'},
]

if __name__ == "__main__":
    unittest.main()
