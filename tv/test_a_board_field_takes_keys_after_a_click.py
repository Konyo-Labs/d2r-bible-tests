"""v3845 - A BOARD FIELD TAKES KEYS AFTER A CLICK (Elad, 2026-10-30 09:32/09:50): in his pywebview/WebKit
window PRICE SEARCH and "Find a filed item" on the D2JSP board took no keystrokes. Measured in a real
WKWebView on his Mac: once the field has focus, native keys type into it - the lost step is the click
giving focus. Here a capture listener cancels mousedown's default (the focus a click normally gives), the
way his window behaves, then a REAL CDP click and REAL key events must still land text in both fields.
NO CHROME = a declared skip, never a pass. RED_PROOF below. [[regression-guard]]

v3879 fix (v3878's proof round 42376032118, shard 17): RED UNTAMPERED in the proof sandbox ("Ran 1 test in 2.766s |
FAILED") while the same commit's agent suite passed it. The board sets html{scroll-behavior:smooth}, so scrollIntoView
ANIMATED and the field's rect was read mid-scroll - the click could land beside the field on a busy runner. The scroll is
now instant, so the point read is the point clicked (the same in the two sibling laws that click by coordinates)."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

from test_a_sweep_never_reticks_what_he_unticked import Board  # noqa: E402
import test_found_ever_never_files_to_a_mule as _H  # noqa: E402


@unittest.skipUnless(os.path.exists(_H.RC.CHROME), "no Chrome on this machine (declared skip)")
class ABoardFieldTakesKeysAfterAClick(unittest.TestCase):
    def test_click_then_type_lands_in_both_d2jsp_fields(self):
        b = Board()
        b.open()
        t = b.t
        b.run("window.fetch = (function(f){ return function(u, o){ if (String(u).indexOf('/api/ui_fault') >= 0) return Promise.resolve(new Response('{}')); return f.apply(this, arguments); }; })(window.fetch);"
              "switchTab('d2jsp'); document.addEventListener('mousedown', function(e){ if (e.target.closest && e.target.closest('input')) e.preventDefault(); }, true);")
        for sel in ("#d2jsp-price-q", "#d2jsp-find"):
            r = b.run("var el = document.querySelector('%s'); el.value = ''; el.scrollIntoView({block:'center', behavior:'instant'}); document.body.focus();"
                      "var q = el.getBoundingClientRect(); OUT.x = q.left + q.width / 2; OUT.y = q.top + q.height / 2;" % sel)
            for ty in ("mousePressed", "mouseReleased"):
                t.send("Input.dispatchMouseEvent", type=ty, x=r["x"], y=r["y"], button="left", clickCount=1)
            for ch in "ann":
                t.send("Input.dispatchKeyEvent", type="keyDown", text=ch, key=ch)
                t.send("Input.dispatchKeyEvent", type="keyUp", key=ch)
            got = json.loads(t.ev("JSON.stringify([document.querySelector('%s').value, document.activeElement && document.activeElement.id])" % sel))
            self.assertEqual(got[0], "ann", "%s took no keys after a click that gave no focus: %r" % (sel, got))


RED_PROOF = [
    {"why": "a click that gave no focus is left that way",
     "file": "bible.html", "find": "    if (isField(el)) rescue(el, ev);",
     "replace": "    void el;", "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
