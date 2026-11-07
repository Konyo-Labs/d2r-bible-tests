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
            # v3881 (REG-3391) - THE FIELD MUST HOLD STILL, AND BE WHAT IS UNDER THE POINT, BEFORE THE CLICK. Red untampered on
            # v3878 shard 17 and again on v3879's second round (run 42394365352, shard 21), green on the same bytes between: the
            # D2JSP tab paints parts of itself after switchTab (the quote refresh, the lamp, the read line between the two
            # fields), so under a loaded runner the rect read here could move before the click and the click landed beside the
            # field. Now the point is read only once the rect is the same on two reads 50 ms apart AND elementFromPoint at its
            # centre is the field; a field that never settles is said, never clicked blind, and a miss names what was hit.
            r = b.run("var el = document.querySelector('%s'); el.value = ''; el.scrollIntoView({block:'center', behavior:'instant'}); document.body.focus();"
                      "var prev = null, q = null, hit = null, tries = 0;"
                      "for (; tries < 60; tries++) {"
                      "  await new Promise(function(res){ setTimeout(res, 50); });"
                      "  q = el.getBoundingClientRect();"
                      "  var key = [q.left, q.top, q.width, q.height].map(Math.round).join(',');"
                      "  hit = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2);"
                      "  if (key === prev && hit && (hit === el || el.contains(hit))) break;"
                      "  prev = key;"
                      "}"
                      "OUT.x = q.left + q.width / 2; OUT.y = q.top + q.height / 2; OUT.tries = tries;"
                      "OUT.hit = hit ? (hit.id ? '#' + hit.id : hit.tagName + '.' + String(hit.className || '')) : 'nothing';"
                      "OUT.settled = tries < 60;" % sel)
            self.assertTrue(r["settled"], "%s never held still under its own point (last hit %s after %d reads) - nothing was "
                                          "clicked blind" % (sel, r["hit"], r["tries"]))
            for ty in ("mousePressed", "mouseReleased"):
                t.send("Input.dispatchMouseEvent", type=ty, x=r["x"], y=r["y"], button="left", clickCount=1)
            for ch in "ann":
                t.send("Input.dispatchKeyEvent", type="keyDown", text=ch, key=ch)
                t.send("Input.dispatchKeyEvent", type="keyUp", key=ch)
            # REG-3391 - a miss says what the page knew: does it have focus at all, is it visible, who holds focus
            got = json.loads(t.ev("JSON.stringify([document.querySelector('%s').value, document.activeElement && document.activeElement.id,"
                                  " document.hasFocus(), document.visibilityState])" % sel))
            self.assertEqual(got[0], "ann", "%s took no keys after a click that gave no focus: %r (the point was %s after %d "
                                            "read(s))" % (sel, got, r["hit"], r["tries"]))


RED_PROOF = [
    {"why": "a click that gave no focus is left that way",
     "file": "bible.html", "find": "    if (isField(el)) rescue(el, ev);",
     "replace": "    void el;", "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
