"""v3845 - A SHOW TOGGLE READS HIDE WHILE OPEN (Elad, 2026-10-30 09:36): the d2jsp evidence drawer kept saying
"show the 12 posts" after it opened. Every <details> whose summary says show/hide now reads "hide ..." while open and
"show ..." when closed, and slides both ways (reduced motion: no slide). Real clicks on the board, in Chrome.
NO CHROME = a declared skip, never a pass. RED_PROOF below. [[regression-guard]]"""
import json
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

from test_a_sweep_never_reticks_what_he_unticked import Board  # noqa: E402
import test_found_ever_never_files_to_a_mule as _H  # noqa: E402

SIM = {"posts": [{"fg": 140, "day": "2026-10-07", "link": "", "roll": [], "cols": [8, -9, 4, 40, 28], "w": 0.38, "out": ""}] * 12}


@unittest.skipUnless(os.path.exists(_H.RC.CHROME), "no Chrome on this machine (declared skip)")
class AShowToggleReadsHideWhileOpen(unittest.TestCase):
    def test_click_open_reads_hide_click_shut_reads_show(self):
        b = Board()
        b.open()
        t = b.t
        r = b.run("var h = document.createElement('div'); h.id = 'sh-probe'; h.style.cssText = 'position:fixed;left:20px;top:20px;z-index:2147483647;background:#000';"
                  "h.innerHTML = d2jspEvidenceHtml(%s); document.body.appendChild(h);"
                  "var s = h.querySelector('summary'), q = s.getBoundingClientRect(); OUT.x = q.left + 20; OUT.y = q.top + q.height / 2;"
                  "OUT.t0 = s.textContent;" % json.dumps(SIM))
        self.assertIn("show the 12 posts", r["t0"])
        # The slide is 220ms and ease-out, so offsetHeight can already equal the finished
        # pixel while the animation is still running. A later CDP read then sees 310 and 310
        # and cannot tell a finished slide from no slide. Hold the animation at its first
        # frame, inside animate(), before this process gets back to read it. A click that
        # never calls animate() leaves no paused height animation, which is the no-slide case.
        b.run("Element.prototype.animate = (function(orig){ return function(){"
              " var a = orig.apply(this, arguments);"
              " try { a.pause(); } catch (e) {}"
              " this._shHeld = a; return a; }; })(Element.prototype.animate);")
        seen = []
        for k in range(2):
            for ty in ("mousePressed", "mouseReleased"):
                t.send("Input.dispatchMouseEvent", type=ty, x=r["x"], y=r["y"], button="left", clickCount=1)
            mid = t.ev("(function(){var d=document.querySelector('#sh-probe details');"
                       "var a=d._shAnim; var frames=[];"
                       "try { frames = a && a.effect ? a.effect.getKeyframes().map(function(f){ return f.height || ''; }) : []; } catch (e) {}"
                       "return JSON.stringify([d.open,d.querySelector('summary').textContent,d.offsetHeight,"
                       "a ? a.playState : '', a ? a.currentTime : -1, frames]);})()")
            t.ev("(function(){var d=document.querySelector('#sh-probe details'); if (d && d._shAnim) d._shAnim.play(); return true;})()")
            # v3883 fix - WAIT FOR THE END STATE, NEVER A FIXED SLEEP (GitHub's proof shard 10/22 on 8045523eb: this law went
            # RED untampered in a 2-lane sandbox, deadlines x2, after a fixed 0.6 s - green alone on the Mac in 3 s). The slide is
            # 220 ms; under load its finish lands late. Poll up to 8 s for the state the click must reach: a drawer that never
            # opens or never closes still fails, on the same assertions below.
            want_open, end = (k == 0), None
            deadline = time.time() + 8.0
            while True:
                end = json.loads(t.ev("(function(){var d=document.querySelector('#sh-probe details');return JSON.stringify([d.open,d.querySelector('summary').textContent,d.offsetHeight]);})()"))
                if (end[0] is want_open and ("hide" if want_open else "show") in end[1]) or time.time() > deadline:
                    break
                time.sleep(0.1)
            seen.append((json.loads(mid), end))
        (m1, e1), (m2, e2) = seen
        self.assertTrue(e1[0], "the first click did not open the drawer: %r" % seen)
        self.assertIn("hide the 12 posts", e1[1], "open, the toggle still says show: %r" % seen)
        self.assertFalse(e2[0], "the second click did not close it: %r" % seen)
        self.assertIn("show the 12 posts", e2[1], "closed, the toggle does not say show again: %r" % seen)
        self.assertTrue(m2[0], "the drawer snapped shut with no slide: %r" % seen)
        self.assertEqual(m1[3], "paused", "the drawer jumped open with no slide: %r" % seen)
        self.assertTrue(m1[4] == 0 or m1[4] is None, "the open slide was not held at its first frame: %r" % seen)
        self.assertEqual(len(m1[5]), 2, "the open slide has no height pair: %r" % seen)
        self.assertNotEqual(m1[5][0], m1[5][1], "the open slide does not move: %r" % seen)


RED_PROOF = [
    {"why": "the summary word is never swapped",
     "file": "bible.html", "find": "    if (s) { word(s, d.open); d.setAttribute('data-sh', d.open ? 'open' : 'shut'); }",
     "replace": "    if (s) { d.setAttribute('data-sh', d.open ? 'open' : 'shut'); }", "matches": 1},
    {"why": "no slide: the click is left to the browser's instant toggle",
     "file": "bible.html", "find": "    ev.preventDefault();\n    if (d._shAnim)",
     "replace": "    return;\n    if (d._shAnim)", "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
