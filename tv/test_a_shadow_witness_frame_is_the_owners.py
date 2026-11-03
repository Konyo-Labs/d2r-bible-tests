# -*- coding: utf-8 -*-
"""v3857 item 18 (#230, Elad 10:39 on v3855): in a shadow on Dean's Vault, witness 1 of Brimstone Clasp opened 'frame
missing (agent off + no archive)' over a broken black picture: the viewer's frame chain asked THIS viewer's bridge and
console for the owner's frame. In a shadow every leg is the owner's address (or dropped, never the viewer's), and a frame
nobody serves hides the picture and says why in words, from the owner's picture map or as UNKNOWN.

v3859 (c): the shadow legs, the words and the witness upload live in SHADOW MODE BOOT, not in the board's frame viewer, so
no board screen branches on window._tvdShadow (test_no_screen_of_the_board_branches_on_the_shadow). The board calls three
hooks - _tvdFrameLegs, _tvdFrameMissingSay, _tvdFrameBoot - that are no-ops on the owner's own board. This law pins each
hook in its block, runs the boot's own hooks against the board's own defaults, and runs the board's defaults alone.

RED_PROOF below: each one, applied, turns this law red."""
import os
import re
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
  "      var _chain = window._tvdFrameLegs(window._tvdFrameChain(id, meta.src), id);\n",
  1
 ],
 [
  "bible.html",
  "        var o = window._shadowOwnerUrl(/^https?:/i.test(String(u)) ? String(u) : String(u).replace(/^\\/+/, ''));\n",
  1
 ],
 [
  "bible.html",
  "      if (a && a.end && a.end.say) return a.end.say;\n",
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
 ],
 [
  "bible.html",
  "  if (typeof window._tvdFrameLegs !== 'function') window._tvdFrameLegs = function(chain){ return chain; };\n",
  1
 ],
 [
  "bible.html",
  "  if (typeof window._tvdFrameBoot === 'function') window._tvdFrameBoot();\n",
  1
 ]
]


def red_after(file, text):
    return any(f == file and text.count(nd) != n for f, nd, n in CHECKS)


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def _blocks(self):
        s = _read('bible.html')
        b0 = s.index('/* SHADOW MODE BOOT')
        b1 = s.index('</script>', b0)
        h0 = s.index("  /* v3859 (c) item 18 - THE FRAME VIEWER'S THREE HOOKS.")
        h1 = s.index('  window._tvdOpenFrame = function(id, meta){', h0)
        return s, (b0, b1), (h0, h1)

    def test_each_shadow_hook_lives_in_the_shadow_boot(self):
        s, (b0, b1), (h0, h1) = self._blocks()
        for name in ('_tvdFrameLegs', '_tvdFrameMissingSay', '_tvdFrameBoot', '_tvdShadowWitnessTake', '_tvdShadowWitnessUrl'):
            defs = [m.start() for m in re.finditer(r'window\.' + name + r' = function', s)]
            boot = [d for d in defs if b0 <= d < b1]
            self.assertEqual(len(boot), 1, '%s must be defined once in SHADOW MODE BOOT: %r' % (name, defs))
            # the board's own default sits only in its hook block, behind `typeof ... !== 'function'` (pinned in CHECKS)
            self.assertTrue(all(b0 <= d < b1 or h0 <= d < h1 for d in defs),
                            '%s must be defined only inside SHADOW MODE BOOT: %r' % (name, defs))
        self.assertEqual(1, s.count("fetch('/api/roster-cache?frames='"), 'the witness upload is fetched once')
        self.assertTrue(b0 < s.index("fetch('/api/roster-cache?frames='") < b1)
        self.assertNotIn('_tvdShadow', s[h0:h1], 'the board hooks branch on the shadow')
        self.assertNotIn('_tvdShadow', s[h1:s.index('  window._tvdCloseFrame = function', h1)],
                         'the board frame viewer branches on the shadow')
        self.assertIn('window._tvdFrameBoot = function', s[s.index('window._tvdShadow = {', b0):b1],
                      'the frame hooks are set after the boot declared the shadow')

    def _run(self, shadow):
        import json, subprocess, shutil
        node = shutil.which('node')
        if not node:
            self.skipTest('node absent: UNKNOWN, not passed')
        s, (b0, b1), (h0, h1) = self._blocks()
        i0 = s.find('    window._shadowOwnerUrl = function(path){')
        j0 = s.find('    /* v3849 - THE SHADOW', i0)
        k0 = s.find('    window._shadowPictureAsk = function (id) {')
        l0 = s.find('    /* v3849 D2 - a read-only board', k0)
        f0 = s.find("    /* v3857 item 18 (#230, Elad 10:39 on v3855) - A SHADOW'S WITNESS FRAME IS THE OWNER'S.", b0)
        f1 = s.find('    /* /v3859 (c) frame hooks */', f0)
        self.assertTrue(min(i0, j0, k0, l0) > 0 and b0 < f0 < f1 < b1)
        boot = (s[i0:j0] + s[k0:l0] + s[f0:f1]) if shadow else ''
        js = 'var window = {}; var location = {protocol: "http:"}; var _asked = [];\n' + \
             'window.fetch = function(u){ _asked.push(u); return {then: function(){ return {then: function(){ return {catch: function(){}}; }}; }}; };\n' + \
             'var fetch = window.fetch;\n' + \
             ('window._tvdShadow = {owner: "Dean PC", origin: "http://owner.example:17777"};\n' if shadow else '') + \
             'window._tvdShadowSnap = {pictures: {"3_1": {present: false, code: "gone", why: "released after 30 days"}}};\n' + \
             boot + '\nvar _bootAsked = _asked.length;\n' + s[h0:h1] + '''
var out = {bootAsked: _bootAsked, asked: _asked};
out.chain = window._tvdFrameLegs(['http://127.0.0.1:17771/frame?id=3_1', 'tv/frames/hist/3_1.jpg'], '3_1');
out.gone = window._tvdFrameMissingSay('3_1');
out.unk = window._tvdFrameMissingSay('9_9');
if (window._tvdShadowWitnessTake) {
  window._tvdShadowWitnessTake({witness: {'3_1792000000000': '/9j/AAAA'}});
  out.wit = window._tvdFrameLegs(['tv/frames/hist/3_1792000000000.jpg'], '3_1792000000000');
}
console.log(JSON.stringify(out));
'''
        return json.loads(subprocess.check_output([node, '-e', js], timeout=30).decode())

    def test_the_chain_and_the_words_run_in_a_shadow(self):
        r = self._run(True)
        self.assertEqual(r['bootAsked'], 0, 'the shadow boot asked for something before the board called it')
        self.assertEqual(r['asked'], ['/api/roster-cache?frames=Dean%20PC'], 'the board hook fetches the upload once')
        self.assertEqual(r['chain'], ['http://owner.example:17777/tv/frames/hist/3_1.jpg'], 'a shadow asked the viewer for the owner frame')
        self.assertIn('released after 30 days', r['gone'])
        self.assertIn('UNKNOWN', r['unk'])
        self.assertNotIn('agent off', r['unk'])
        self.assertEqual(r['wit'][0], 'data:image/jpeg;base64,/9j/AAAA', 'the uploaded witness opens first')

    def test_the_owners_own_board_keeps_its_chain(self):
        r = self._run(False)
        self.assertEqual(r['asked'], [], 'the owner board fetched a shadow upload')
        self.assertEqual(r['chain'], ['http://127.0.0.1:17771/frame?id=3_1', 'tv/frames/hist/3_1.jpg'], 'the owner board chain must not change')
        self.assertEqual(r['gone'], 'frame missing (agent off + no archive)')


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
  "find": "      var _chain = window._tvdFrameLegs(window._tvdFrameChain(id, meta.src), id);\n",
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
  "find": "      if (a && a.end && a.end.say) return a.end.say;\n",
  "replace": "",
  "matches": 1,
  "why": "the owner's own reason is dropped for a generic one"
 },
 {
  "file": "bible.html",
  "find": "  if (typeof window._tvdFrameBoot === 'function') window._tvdFrameBoot();\n",
  "replace": "",
  "matches": 1,
  "why": "the board never asks for the owner's witness upload"
 },
 {
  "file": "bible.html",
  "find": "  if (typeof window._tvdFrameLegs !== 'function') window._tvdFrameLegs = function(chain){ return chain; };\n",
  "replace": "  window._tvdFrameLegs = function(chain){ return chain; };\n",
  "matches": 1,
  "why": "the board overwrites the shadow's owner legs with its own"
 }
]

if __name__ == "__main__":
    unittest.main()
