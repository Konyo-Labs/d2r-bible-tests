# -*- coding: utf-8 -*-
"""ALT inject run 2026-10-24 (bug 4) - AN ITEM NAME WITH ODD CHARACTERS STAYS INSIDE ITS onclick ATTRIBUTE.

GrokBot's ALT edge batch filed `GBL-TEST-Odd <b>&"'é🧪ש</b>` to a mule and the mule window printed raw `')">` as
text: jsArg escaped only the backslash and the apostrophe, so the name's double quote closed the onclick="..."
attribute early and the rest of the call spilled into the page (and the click handed the wrong name, or none).
jsArg now also escapes " < > & as JS hex escapes - legal in a JS string literal and inert in an HTML attribute.

The mule window is drawn on the WHOLE page in node (tv/vault_page_node.py); every onclick that carries the name is
entity-decoded as the browser would, run against stub doors, and must hand back the exact name.
RED_PROOF: put jsArg back to the backslash + apostrophe escape only and the test fails.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import vault_page_node as VPN  # noqa: E402

ODD = "GBL-TEST-Odd <b>&\"'é🧪ש</b>"
PRELUDE = r"""
Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });
location.protocol = 'file:'; location.href = 'file:///spec/bible.html'; location.origin = 'null'; location.host = ''; location.hostname = '';
localStorage.setItem('d2r_ownerClaim', '*');
localStorage.setItem('d2r_muleRoster', JSON.stringify([{ id: 'm1', name: 'MULE1' }]));
(function(n){
  var tx = {}, ma = {};
  tx[n] = { rarity: 'basic', base: n, cat: 'x', val: 'tv', desc: 'law' }; ma[n] = 'm1';
  localStorage.setItem('d2r_tvExtraItems', JSON.stringify(tx));
  localStorage.setItem('d2r_muleAssign', JSON.stringify(ma));
  localStorage.setItem('d2r_owned', JSON.stringify([n]));
})(__ODD__);
"""
BODY = r"""
H.flush(60, 3);
window.openMuleCard('m1'); H.flush(60, 3);
var html = (document.getElementById('vault-detail') || {}).innerHTML || '';
function dec(s){ return s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); }
OUT.calls = []; OUT.drawn = html.indexOf('GBL-TEST-Odd') >= 0;
var re = /onclick="([^"]*)"/g, m;
while ((m = re.exec(html))){
  var code = dec(m[1]);
  if (code.indexOf('GBL-TEST-Odd') < 0) continue;
  var got = [];
  var stub = new Proxy({}, { get: function(){ return function(){ got.push(arguments[0]); }; } });
  var ev = { stopPropagation: function(){}, shiftKey: false };
  try { new Function('window', 'event', code)(stub, ev); OUT.calls.push({ code: code.slice(0, 200), got: got }); }
  catch (e) { OUT.calls.push({ code: code.slice(0, 200), threw: String(e) }); }
}
"""


class AnOddItemNameNeverLeaksOutOfItsAttribute(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = VPN.run(BODY, prelude=PRELUDE.replace("__ODD__", json.dumps(ODD)), timeout=300)

    def test_the_mule_window_draws_the_name(self):
        self.assertTrue(self.out.get("drawn"), "the odd name never reached the mule window: %r" % self.out.get("__boot"))

    def test_every_click_hands_back_the_exact_name(self):
        calls = self.out["calls"]
        self.assertTrue(calls, "no onclick carried the odd name - its attribute was cut short (bug 4)")
        for c in calls:
            self.assertNotIn("threw", c, "bug 4: an onclick carrying the odd name does not parse: %r" % c)
            self.assertEqual(c["got"][:1], [ODD], "bug 4: the click handed %r, not the name" % (c["got"],))

    def test_no_call_is_cut_short_by_the_name(self):
        for c in self.out["calls"]:
            self.assertTrue(c["code"].rstrip().endswith(")"),
                            "bug 4: the attribute ended inside the call, so its tail ')\"> prints as text: %r" % c["code"])

RED_PROOF = [
    {"why": "ALT bug 4 - jsArg escapes only the backslash and the apostrophe, so a double quote in a name closes the onclick early",
     "file": "bible.html",
     "find": "  function jsArg(t){ return String(t).replace(/\\\\/g,'\\\\\\\\').replace(/'/g,\"\\\\'\").replace(/\"/g,'\\\\x22').replace(/</g,'\\\\x3C').replace(/>/g,'\\\\x3E').replace(/&/g,'\\\\x26'); }   /* ALT inject run bug 4: a \" in a name closed the onclick attribute */\n",
     "replace": "  function jsArg(t){ return String(t).replace(/\\\\/g,'\\\\\\\\').replace(/'/g,\"\\\\'\"); }   /* ALT inject run bug 4: a \" in a name closed the onclick attribute */\n",
     "matches": 1, "needs": "node"},
    {"why": "jsArg stops escaping the double quote alone, so an odd name's \" cuts the mule window's onclick short",
     "file": "bible.html",
     "find": "  function jsArg(t){ return String(t).replace(/\\\\/g,'\\\\\\\\').replace(/'/g,\"\\\\'\").replace(/\"/g,'\\\\x22').replace(/</g,'\\\\x3C').replace(/>/g,'\\\\x3E').replace(/&/g,'\\\\x26'); }   /* ALT inject run bug 4: a \" in a name closed the onclick attribute */\n",
     "replace": "  function jsArg(t){ return String(t).replace(/\\\\/g,'\\\\\\\\').replace(/'/g,\"\\\\'\").replace(/</g,'\\\\x3C').replace(/>/g,'\\\\x3E').replace(/&/g,'\\\\x26'); }   /* ALT inject run bug 4: a \" in a name closed the onclick attribute */\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
