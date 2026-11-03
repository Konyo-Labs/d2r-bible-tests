# -*- coding: utf-8 -*-
"""v3857 item 19 (#230, Elad 10:43/10:45): D2JSP read price failed on Dean's console with no word - most likely no d2jsp
session in that PC's Chrome. A D2JSP lamp now sits beside CLAUDE and GROK (same .rl lamp): red with no session, green with
one, a click opens the login and re-asks every 3 s for 2 minutes. Read price with no session says 'Sign in to d2jsp first'.
The lamp reads only the server's on/off/why answer - no cookie, password or credential reaches the page, a log or the repo.

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
  "tv/control_ui.html",
  "<button type=\"button\" class=\"rl\" id=\"rl-d2jsp\" data-lamp=\"unknown\" onclick=\"window._d2jspLampClick(this)\"",
  1
 ],
 [
  "tv/control_ui.html",
  "    return fetch('/api/d2jsp_login').then(function (r) { return r.json(); })\n",
  1
 ],
 [
  "tv/control_ui.html",
  "      _D2L.t = setTimeout(_d2jspLampLoop, fast ? 3000 : 120000);\n",
  1
 ],
 [
  "tv/control_ui.html",
  "        _D2L.fast = Date.now() + 120000;\n",
  1
 ],
 [
  "bible.html",
  "  if (q.reason === 'need-login') return 'Sign in to d2jsp first - the price read uses the Chrome login on this machine; ' + (q.opened",
  1
 ]
]


def red_after(file, text):
    return any(f == file and text.count(nd) != n for f, nd, n in CHECKS)


class TheLawHolds(unittest.TestCase):
    def test_each_line_is_where_it_should_be(self):
        for f, needle, n in CHECKS:
            self.assertEqual(_read(f).count(needle), n, "%s: %r should appear %d time(s)" % (f, needle, n))

    def test_the_lamp_is_beside_claude_and_grok(self):
        s = _read('tv/control_ui.html')
        i = s.find('<div class="reader-lamps" id="reader-lamps"')
        j = s.find('</div>', i)
        box = s[i:j]
        self.assertTrue(box.find('id="rl-claude"') < box.find('id="rl-grok"') < box.find('id="rl-d2jsp"'))

    def test_red_without_a_session_green_with_one(self):
        import json, subprocess, shutil
        node = shutil.which('node')
        if not node:
            self.skipTest('node absent: UNKNOWN, not passed')
        s = _read('tv/control_ui.html')
        i = s.find('  var _D2L = { last: null, fast: 0, t: null };')
        j = s.find('  window._d2jspLampPaint = _d2jspLampPaint;', i)
        self.assertTrue(i > 0 and j > i)
        js = '''var A={}; var el={setAttribute:function(k,v){A[k]=String(v);},removeAttribute:function(k){delete A[k];},title:''};
var document={getElementById:function(){return el;}}; var window={};
''' + s[i:j] + '''
var o={};
_d2jspLampPaint({state:'off',why:'not signed in'}); o.off=JSON.parse(JSON.stringify(A)); o.offT=el.title;
_d2jspLampPaint({state:'on',why:'signed in'}); o.on=JSON.parse(JSON.stringify(A));
_d2jspLampPaint(null); o.unk=JSON.parse(JSON.stringify(A));
console.log(JSON.stringify(o));
'''
        r = json.loads(subprocess.check_output([node, '-e', js], timeout=30).decode())
        self.assertEqual(r['off'].get('data-lamp'), 'off')
        self.assertEqual(r['off'].get('data-fault'), '1', 'no session must read red')
        self.assertIn('click to open the d2jsp login', r['offT'])
        self.assertEqual(r['on'].get('data-lamp'), 'on')
        self.assertNotIn('data-fault', r['on'])
        self.assertEqual(r['unk'].get('data-lamp'), 'unknown')

    def test_no_credential_reaches_the_page(self):
        s = _read('tv/control_ui.html')
        i = s.find('  var _D2L = { last: null, fast: 0, t: null };')
        blk = s[i:s.find('  try { setTimeout(_d2jspLampLoop, 1500); }', i)]
        for w in ('cookie', 'password', 'passwd', 'localStorage', 'console.log'):
            self.assertNotIn(w, blk.replace('the cookie is read and dropped', ''), w)


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
  "file": "tv/control_ui.html",
  "find": "<button type=\"button\" class=\"rl\" id=\"rl-d2jsp\" data-lamp=\"unknown\" onclick=\"window._d2jspLampClick(this)\"",
  "replace": "<button type=\"button\" class=\"rl\" id=\"rl-d2jsp\" data-lamp=\"unknown\" hidden",
  "matches": 1,
  "why": "the lamp no longer opens the login"
 },
 {
  "file": "tv/control_ui.html",
  "find": "      _D2L.t = setTimeout(_d2jspLampLoop, fast ? 3000 : 120000);\n",
  "replace": "      _D2L.t = setTimeout(_d2jspLampLoop, 120000);\n",
  "matches": 1,
  "why": "no fast re-check after a sign-in"
 },
 {
  "file": "bible.html",
  "find": "  if (q.reason === 'need-login') return 'Sign in to d2jsp first - the price read uses",
  "replace": "  if (q.reason === 'need-login') return 'Public price unknown - the price read uses",
  "matches": 1,
  "why": "read price with no session goes back to a silent unknown"
 }
]

if __name__ == "__main__":
    unittest.main()
