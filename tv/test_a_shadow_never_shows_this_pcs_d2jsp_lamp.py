# -*- coding: utf-8 -*-
"""#56 (GrokBot 6700580776, 11-07: in Dean's shadow the D2JSP lamp read "Signed into d2jsp in the console's own d2jsp
window on this Mac" - the viewer's sign-in drawn as the owner's) - A SHADOW NEVER SHOWS THIS PC'S D2JSP LAMP.

A shadow is the owner's board; their d2jsp sign-in lives on their PC and nothing uploads it. In a shadow the lamp is
UNKNOWN and says whose it is, asks this console nothing (no GET /api/d2jsp_login), and a click opens no login here (no
POST - a shadow writes nothing, REG-2186). Outside a shadow the lamp asks this console as before. Driven on the whole page
in node (tv/vault_page_node), with a fetch that records every ask. RED_PROOF below.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import vault_page_node as VPN  # noqa: E402

BODY = r"""
var ASKED = [];
window.fetch = function(url, opt){ ASKED.push((opt && opt.method || 'GET') + ' ' + String(url));
  return { then: function(f){ try { f({ json: function(){ return { then: function(g){ g({ state: 'on', why: 'Signed into d2jsp on this Mac' }); return { catch: function(){} }; } }; } }); } catch (e) {} return { then: function(){ return { catch: function(){} }; }, catch: function(){} }; },
           catch: function(){} }; };
try { Object.defineProperty(window.location, 'hostname', { value: '127.0.0.1', configurable: true }); } catch (e) { OUT.hostErr = String(e); }
var lamp = document.getElementById('d2jsp-lamp');
document.documentElement.classList.add('tvd-shadow');
window._d2jspLamp(); window._d2jspLamp(true);
OUT.shadow = { asked: ASKED.slice(), state: lamp && lamp.getAttribute('data-lamp'), title: lamp && lamp.title };
document.documentElement.classList.remove('tvd-shadow');
ASKED.length = 0;
window._d2jspLamp();
OUT.home = { asked: ASKED.slice(), host: (function(){ try { return location.hostname; } catch (e) { return null; } })() };
"""


@unittest.skipIf(VPN.NODE is None, "node is absent - this law is UNMEASURED here, not passing")
class AShadowNeverShowsThisPcsLamp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, timeout=600)

    def test_in_a_shadow_the_lamp_is_unknown_and_says_whose_it_is(self):
        s = self.o["shadow"]
        self.assertEqual(s["state"], "unknown", "a shadow drew a lamp state it never read: %r" % s)
        self.assertIn("lives on that PC", s["title"])
        self.assertNotIn("this Mac", s["title"], "the viewer's sign-in was drawn as the owner's")

    def test_a_shadow_asks_this_console_nothing_and_opens_no_login(self):
        self.assertEqual(self.o["shadow"]["asked"], [], "a shadow asked this console about its own d2jsp sign-in")

    def test_outside_a_shadow_the_lamp_asks_this_console_as_before(self):
        if self.o["home"]["host"] not in ("127.0.0.1", "localhost"):
            self.skipTest("the harness could not stand on the console's host - the home half is UNMEASURED here")
        self.assertIn("GET /api/d2jsp_login", self.o["home"]["asked"], "PREMISE: the lamp no longer asks its own console")


RED_PROOF = [
    {"why": "#56 - a shadow asks this console and draws the viewer's d2jsp sign-in as the owner's again",
     "file": "bible.html",
     "find": "    if (document.documentElement.classList.contains('tvd-shadow')) {\n      lamp.removeAttribute('data-busy');\n",
     "replace": "    if (false) {\n      lamp.removeAttribute('data-busy');\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
