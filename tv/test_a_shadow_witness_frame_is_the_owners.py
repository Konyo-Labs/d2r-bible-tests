# -*- coding: utf-8 -*-
"""v3857 item 18 (#230, Elad 10:39 on v3855): in a shadow on Dean's Vault, witness 1 of Brimstone Clasp opened 'frame
missing (agent off + no archive)' over a broken black picture: the viewer's frame chain asked THIS viewer's bridge and
console for the owner's frame. In a shadow every leg is the owner's address (or dropped, never the viewer's), and a frame
nobody serves hides the picture and says why in words, from the owner's picture map or as UNKNOWN. Not yet in this fix:
the frame bytes riding the shadow upload itself (left for a later item, said in the report).

RED_PROOF below: each one, applied, turns this law red."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
ROOT = os.path.join(HERE, "..")


def _read(p):
    return open(os.path.join(ROOT, p), encoding="utf-8").read()


# [file, needle, how many times it must appear]
CHECKS = [
 [
  "bible.html",
  "      var _chain = window._tvdShadowFrameChain(window._tvdFrameChain(id, meta.src));\n",
  1
 ],
 [
  "bible.html",
  "      var o = window._shadowOwnerUrl(/^https?:/i.test(String(u)) ? String(u) : String(u).replace(/^\\/+/, ''));\n",
  1
 ],
 [
  "bible.html",
  "    if (a && a.end && a.end.say) return a.end.say;\n",
  1
 ],
 [
  "bible.html",
  "        img.style.visibility = 'hidden';\n",
  1
 ],
 [
  "bible.html",
  "      if (!_chain.length) _missing(); else img.src = _chain[0];\n",
  1
 ]
]


def red_after(file, text):
    return any(f == file and text.count(nd) != n for f, nd, n in CHECKS)


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_the_chain_and_the_words_run(self):
        import json, subprocess, shutil
        node = shutil.which('node')
        if not node:
            self.skipTest('node absent: UNKNOWN, not passed')
        s = _read('bible.html')
        i = s.find('  window._tvdShadowFrameChain = function(chain){')
        j = s.find('  window._tvdOpenFrame = function(id, meta){', i)
        i0 = s.find('    window._shadowOwnerUrl = function(path){')
        j0 = s.find('    /* v3849 - THE SHADOW', i0)
        k0 = s.find('    window._shadowPictureAsk = function (id) {')
        l0 = s.find('    /* v3849 D2 - a read-only board', k0)
        self.assertTrue(min(i, j, i0, j0, k0, l0) > 0)
        js = 'var window = {};\n' + s[i0:j0] + s[k0:l0] + s[i:j] + '''
var out = {};
window._tvdShadow = {origin: 'http://owner.example:17777'};
window._tvdShadowSnap = {pictures: {'3_1': {present: false, code: 'gone', why: 'released after 30 days'}}};
out.chain = window._tvdShadowFrameChain(['http://127.0.0.1:17771/frame?id=3_1', 'tv/frames/hist/3_1.jpg']);
out.gone = window._tvdFrameMissingSay('3_1');
out.unk = window._tvdFrameMissingSay('9_9');
window._tvdShadow = null;
out.own = window._tvdShadowFrameChain(['tv/frames/hist/3_1.jpg']);
console.log(JSON.stringify(out));
'''
        r = json.loads(subprocess.check_output([node, '-e', js], timeout=30).decode())
        self.assertEqual(r['chain'], ['http://owner.example:17777/tv/frames/hist/3_1.jpg'], 'a shadow asked the viewer for the owner frame')
        self.assertIn('released after 30 days', r['gone'])
        self.assertIn('UNKNOWN', r['unk'])
        self.assertNotIn('agent off', r['unk'])
        self.assertEqual(r['own'], ['tv/frames/hist/3_1.jpg'], 'the owner board chain must not change')


class TheProofsNameOnePlace(unittest.TestCase):
    def test_each_find_matches_once(self):
        for p in RED_PROOF:
            self.assertEqual(_read(p["file"]).count(p["find"]), p["matches"], p["why"])

    def test_each_proof_turns_a_check_red(self):
        for p in RED_PROOF:
            after = _read(p["file"]).replace(p["find"], p["replace"])
            self.assertTrue(red_after(p["file"], after), "this proof would not turn the law red: " + p["why"])


RED_PROOF = [
 {
  "file": "bible.html",
  "find": "      var _chain = window._tvdShadowFrameChain(window._tvdFrameChain(id, meta.src));\n",
  "replace": "      var _chain = window._tvdFrameChain(id, meta.src);\n",
  "matches": 1,
  "why": "a shadow asks the viewer's own bridge for the owner's frame again"
 },
 {
  "file": "bible.html",
  "find": "        img.style.visibility = 'hidden';\n",
  "replace": "",
  "matches": 1,
  "why": "the broken black picture is back"
 },
 {
  "file": "bible.html",
  "find": "    if (a && a.end && a.end.say) return a.end.say;\n",
  "replace": "",
  "matches": 1,
  "why": "the owner's own reason is dropped for a generic one"
 }
]

if __name__ == "__main__":
    unittest.main()
