# -*- coding: utf-8 -*-
"""REG-2871 (#83, his ask 2, GrokBot 6476487696) - A D2JSP POST CARRIES THE ITEM'S PICTURE, LAID OUT CLEANLY.

GrokBot: "Item image inside the post: the draft is text only, and Elad wants the item's picture embedded. The picture and
the layout (one mod per line, title, price) must render correctly on d2jsp itself."

MEASURED before: d2jspDraft wrote the title, the mods and the price as text. No picture was in the post. The room showed a
screenshot beside the draft and said "The board receives the text." The site gate answered 401 to every request without
the password, so a picture on bull-4-u.com could not have rendered for a d2jsp reader.

Now a post is BBCode: the title, then one [img] line with the item's own art from the one resolver (artUrl, which asks
_keeperArt first, REG-2805) at https://bull-4-u.com/d2r/art/..., then one mod per line, copies, and the price last (the
console's _priced still reads it there). A name with no art, or an art path outside art/, carries no picture. A sold block
carries none. The gate lets anyone GET an image file directly under /d2r/art/ - the art is already public in the repo -
and nothing else. Whether d2jsp shows an [img] from that host is for GrokBot's repost (NEEDS LIVE). The room runs in node,
the whole page in node, the gate in node. Never a browser, never d2jsp. RED_PROOF below.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable
enable()

import d2jsp_chrome as desk  # noqa: E402
import vault_page_node as VPN  # noqa: E402

ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "bible.html")
NODE = shutil.which("node")
ORIGIN = "https://bull-4-u.com/d2r/"


def _between(src, start, end):
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i + len(start):j]


ROOM = r"""
var document = { documentElement: { classList: { contains: function(){ return false; } } }, getElementById: function(){ return null; },
  querySelector: function(){ return null; }, querySelectorAll: function(){ return []; }, addEventListener: function(){},
  createElement: function(){ return { setAttribute: function(){}, appendChild: function(){} }; }, body: { appendChild: function(){} } };
var localStorage = { getItem: function(){ return null; }, setItem: function(){}, removeItem: function(){} };
var location = { hostname: '127.0.0.1' };
var window = { addEventListener: function(){}, LSR: { getItem: function(){ return null; } } };
function fetch(){ return Promise.resolve({ status: 200, json: function(){ return Promise.resolve({}); } }); }
var ART = { 'Grief': 'art/mr_griefphaseblade.png', 'Shako': 'art/hd_shako.png', 'Bad': '../bible.html', 'Out': 'tv/x.png',
            'Spacey': "art/my item.png" };
function artUrl(n){ return Object.prototype.hasOwnProperty.call(ART, n) ? ART[n] : null; }
"""

SCENARIO = r"""
var out = {};
out.one = d2jspDraft('Grief', 'Phase Blade', '+340-400% Enhanced Damage\n+36-40 to Life', 2, 55);
['Bad', 'Out', 'Spacey', 'None'].forEach(function(n){ out[n] = d2jspDraft(n, '', '+1', 1, 5); });
out.shop = d2jspShopDraft([{ name: 'Grief', base: 'Phase Blade', mods: '+1', copies: 1, fg: 55, sold: false },
                           { name: 'Shako', base: 'Harlequin Crest', mods: '+2', copies: 1, fg: 30, sold: true }]);
process.stdout.write(JSON.stringify(out));
"""

GATE = r"""
const m = await import(process.argv[1]);
const out = {};
async function ask(method, path, auth){
  const headers = new Map(); if (auth) headers.set('authorization', auth);
  const request = { method, url: 'https://bull-4-u.com' + path, headers: { get: (k) => headers.get(String(k).toLowerCase()) || null }, cf: {} };
  let passed = false;
  const res = await m.onRequest({ request, env: { SITE_PASS: 'law-pass' }, next: () => { passed = true; return { status: 200 }; },
                                  waitUntil: () => {} });
  return passed ? 200 : (res && res.status);
}
out.art = await ask('GET', '/d2r/art/mr_griefphaseblade.png');
out.artJpg = await ask('GET', '/d2r/art/x.jpg');
out.page = await ask('GET', '/d2r/');
out.html = await ask('GET', '/d2r/art/x.html');
out.deep = await ask('GET', '/d2r/art/sub/x.png');
out.post = await ask('POST', '/d2r/art/x.png');
out.dots = await ask('GET', '/d2r/art/..%2Fbible.png');
out.pass = await ask('GET', '/d2r/', 'Basic ' + Buffer.from('x:law-pass').toString('base64'));
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, "node is required to run the room's own code")
class AD2jspPostCarriesTheItemPicture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        desk_block = _between(src, "/* ⟦D2JSP DESK BEGIN⟧ */", "/* ⟦D2JSP DESK END⟧ */")
        r = subprocess.run([NODE, "-"], input=ROOM + desk_block + "\n" + SCENARIO, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
        cls.o = json.loads(r.stdout.strip().splitlines()[-1])
        g = subprocess.run([NODE, "--input-type=module", "-e", GATE, os.path.join(ROOT, "functions", "_middleware.js")],
                           capture_output=True, text=True, timeout=60)
        if g.returncode != 0:
            raise AssertionError("node failed on the gate: " + (g.stderr or g.stdout)[-2500:])
        cls.g = json.loads(g.stdout.strip().splitlines()[-1])
        # the item of GrokBot's real post
        cls.page = VPN.run("var N = \"Andariel's Visage\"; OUT.art = artUrl(N); OUT.pic = d2jspPictureOf(N);"
                           "OUT.keeper = (window._keeperArt(N) || {}).url || null;", timeout=300)

    def test_the_post_is_title_picture_mods_price(self):
        one = self.o["one"]
        self.assertEqual(one["body"].split("\n"), [
            "WTS Grief Phase Blade",
            "[img]" + ORIGIN + "art/mr_griefphaseblade.png[/img]",
            "+340-400% Enhanced Damage",
            "+36-40 to Life",
            "copies: 2",
            "55 fg",
        ], one["body"])
        self.assertEqual(one["picture"], ORIGIN + "art/mr_griefphaseblade.png")
        self.assertTrue(desk._priced(one["subject"], one["body"]), "the console refuses the post the room builds")

    def test_no_art_or_an_art_path_outside_art_carries_no_picture(self):
        for n in ("Bad", "Out", "Spacey", "None"):
            self.assertNotIn("[img]", self.o[n]["body"], "%s carries a picture: %r" % (n, self.o[n]["body"]))
            self.assertEqual(self.o[n]["picture"], "", n)

    def test_the_list_gives_each_item_its_picture_and_a_sold_block_none(self):
        blocks = self.o["shop"]["body"].split("\n\n")
        self.assertEqual(blocks[0].split("\n")[1], "[img]" + ORIGIN + "art/mr_griefphaseblade.png[/img]", blocks)
        self.assertTrue(blocks[1].startswith("SOLD Shako"), blocks)
        self.assertNotIn("[img]", blocks[1], "a sold block carries a picture")
        self.assertTrue(desk._priced(self.o["shop"]["subject"], self.o["shop"]["body"]))

    def test_the_real_page_takes_the_one_resolvers_picture_and_it_is_on_disk(self):
        p = self.page
        self.assertEqual(p["__boot"]["errors"], [], p["__boot"])
        self.assertTrue(p["keeper"], "PREMISE: the keeper resolver has no art for Andariel's Visage")
        self.assertEqual(p["art"], p["keeper"], "artUrl does not answer the keeper resolver first")
        self.assertEqual(p["pic"], ORIGIN + p["art"], p)
        self.assertTrue(os.path.isfile(os.path.join(ROOT, p["art"])), "the picture the post links is not in the repo's art/: %r" % p["art"])

    def test_the_gate_opens_art_images_and_nothing_else(self):
        g = self.g
        self.assertEqual((g["art"], g["artJpg"]), (200, 200), "a d2jsp reader cannot load the item's picture: %r" % g)
        self.assertEqual(g["pass"], 200, "PREMISE: the gate refuses the right password: %r" % g)
        for k in ("page", "html", "deep", "post", "dots"):
            self.assertEqual(g[k], 401, "the gate opened %s without the password: %r" % (k, g))


RED_PROOF = [
    {"why": "REG-2871 - the post is text only again",
     "file": "bible.html",
     "find": "  if (pic) lines.push('[img]' + pic + '[/img]');   /* REG-2871 */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2871 - an art path outside art/ becomes a picture",
     "file": "bible.html",
     "find": "  if (r.indexOf('..') >= 0 || !/^art\\/[A-Za-z0-9_.\\-]+\\.(?:png|jpe?g|gif|webp)$/i.test(r)) return '';\n",
     "replace": "  if (!r) return '';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2871 - the picture is not the one resolver's (another lookup)",
     "file": "bible.html",
     "find": "  try { return (typeof artUrl === 'function') ? d2jspPictureUrl(artUrl(name)) : ''; } catch (ePic) { return ''; }\n",
     "replace": "  try { return (typeof D2IO_ART === 'object') ? d2jspPictureUrl(D2IO_ART[name]) : ''; } catch (ePic) { return ''; }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2871 - the gate keeps the art behind the password, so the picture cannot render on d2jsp",
     "file": "functions/_middleware.js",
     "find": "      && url.pathname.indexOf('..') < 0) return next();\n",
     "replace": "      && false) return next();\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2871 - the gate opens any path under /d2r/art/ (a page, a POST, a subfolder)",
     "file": "functions/_middleware.js",
     "find": "  if (request.method === 'GET' && /^\\/d2r\\/art\\/[A-Za-z0-9_.\\-]+\\.(?:png|jpe?g|gif|webp)$/i.test(url.pathname)\n",
     "replace": "  if (url.pathname.indexOf('/d2r/art/') === 0\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
