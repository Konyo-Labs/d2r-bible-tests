# -*- coding: utf-8 -*-
"""#154 (REG-2833, GrokBot's #13 drive, #230 6462208498) - THE SOCKETS SPINNER NEVER MOVES UNDER HIS CURSOR.

"The editor header shifts about 17 px sideways on re-render, which moves the Sockets spinner under the cursor." Two causes,
both in the vault planner's repaint: vaultPlannerPaint rewrites the whole host on every change, so the field he was in was
destroyed (focus gone, the edit pane's scroll back at the top); and the edit pane (.cb-ed, overflow:auto) reserved no room
for a scrollbar, so a classic scrollbar (17 px on Windows Chrome) arriving as the socket rows grew narrowed the pane and
reflowed it sideways. Now the repaint carries the focused field and the pane's scroll across, and .cb-ed reserves its
gutter (scrollbar-gutter: stable).

Driven in Chrome on the SHIPPED page (layout, focus and trusted keys exist only there; the node law
test_a_planner_edit_is_one_edit holds the data half): a Superior Monarch opened in the planner, real ArrowUp key presses on
the Sockets field, and the pane measured with a styled (classic, 17 px) scrollbar at a tall and a short modal height.
NO CHROME = a declared skip; CI proves it. RED_PROOF below (run by CI's census, never on his Mac).
"""
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_a_sweep_never_reticks_what_he_unticked as H  # noqa: E402

_B = {}

#: a classic scrollbar that takes room on every platform (a styled ::-webkit-scrollbar is never an overlay), and the
#: modal's height set on the HOST, which every repaint keeps (the modal element itself is rewritten)
STYLE = ("var st = document.getElementById('law-sb') || document.createElement('style'); st.id = 'law-sb';"
         "st.textContent = '#vault-planner-host .cb-ed::-webkit-scrollbar{width:17px;background:#222}"
         "#vault-planner-host .cb-ed::-webkit-scrollbar-thumb{background:#777}"
         "#vault-planner-host .cb-modal{height:var(--law-h,min(88vh,940px)) !important;max-height:var(--law-h,88vh) !important}';"
         "document.head.appendChild(st);")
OPEN = ("window.switchTab('vault'); try { window.vaultPlannerClose(); } catch (e) {}"
        "window.vaultPlannerOpen('');"
        "var db = window._cbDb(), code = Object.keys(db.b).find(function(c){ return db.b[c][0] === 'Monarch'; });"
        "window._cbChoose('b:' + code); window._cbQuality('sup');"
        "await new Promise(function(r){ setTimeout(r, 200); });")
MEASURE = ("function m(){ var i = document.getElementById('cb-sockets'), ed = document.querySelector('#vault-planner-host .cb-ed');"
           "  var r = i ? i.getBoundingClientRect() : null, c = window._cbState().host.cur();"
           "  return { focus: document.activeElement ? document.activeElement.id : null, x: r ? r.left : null, y: r ? r.top : null,"
           "           value: i ? i.value : null, draft: c ? (c.sockets | 0) : null, top: ed ? ed.scrollTop : null,"
           "           gutter: ed ? (ed.offsetWidth - ed.clientWidth) : null }; }")
# Request every face the page lists (Inter / Cinzel / Playfair, every weight, including italics)
# after the delayed #gfont-css sheet has landed. fonts.load on an unregistered family is a no-op,
# so the sheet wait comes first. A missing or blocked sheet leaves facesLoaded false; the settle
# loop and the fonts-status premise still have to hold on whatever did load.
PRELOAD = (
    "var _faces = ['400 16px Inter','500 16px Inter','600 16px Inter','700 16px Inter',"
    "'500 16px Cinzel','600 16px Cinzel','700 16px Cinzel',"
    "'400 16px \"Playfair Display\"','500 16px \"Playfair Display\"',"
    "'600 16px \"Playfair Display\"','700 16px \"Playfair Display\"',"
    "'italic 400 16px \"Playfair Display\"','italic 500 16px \"Playfair Display\"'];"
    "var _sheetOk = false, _facesOk = 0;"
    "await (function waitSheet(){ return new Promise(function(res){"
    "  var n = 0; (function tick(){ var l = document.getElementById('gfont-css');"
    "    if (l && l.sheet){ _sheetOk = true; return res(); }"
    "    if (l && !l._lawWait){ l._lawWait = 1; l.addEventListener('load', function(){ _sheetOk = true; res(); });"
    "      l.addEventListener('error', function(){ res(); }); }"
    "    if (++n >= 60) return res(); setTimeout(tick, 50); })(); }); })();"
    "if (_sheetOk){ var _got = await Promise.all(_faces.map(function(f){ return document.fonts.load(f); }));"
    "  _facesOk = _got.filter(function(x){ return x && x.length; }).length; }"
    "await document.fonts.ready;"
)


def board():
    if "b" not in _B:
        _B["b"] = H.Board().open()
    return _B["b"]


def tearDownModule():
    b = _B.pop("b", None)
    if b is not None:
        b.close()


def key_up():
    t = board().t
    for kind in ("keyDown", "keyUp"):
        t.send("Input.dispatchKeyEvent", type=kind, key="ArrowUp", code="ArrowUp", windowsVirtualKeyCode=38,
               nativeVirtualKeyCode=38)
    time.sleep(0.25)


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class ThePlannerSpinnerStaysUnderTheCursor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        board().seed({"d2r_owned": [], "d2r_muleAssign": {}, "d2r_vaultRecords": None, "d2r_vaultProv": {}})

    def test_the_edit_pane_reserves_its_scrollbar_whether_it_scrolls_or_not(self):
        o = board().run(STYLE + OPEN + MEASURE +
                        "var md = document.getElementById('vault-planner-host');"
                        "md.style.setProperty('--law-h', '1400px'); await new Promise(function(r){ setTimeout(r, 120); }); OUT.tall = m();"
                        "md.style.setProperty('--law-h', '260px'); await new Promise(function(r){ setTimeout(r, 120); }); OUT.short = m();"
                        "var ed = document.querySelector('#vault-planner-host .cb-ed');"
                        "OUT.overflows = ed ? ed.scrollHeight > ed.clientHeight : null;"
                        "OUT.css = ed ? getComputedStyle(ed).scrollbarGutter : null;")
        self.assertTrue(o["overflows"], "PREMISE: the short modal does not make the edit pane scroll: %r" % o)
        self.assertEqual(o["css"], "stable", "the edit pane reserves no gutter: %r" % o)
        self.assertEqual(o["tall"]["gutter"], o["short"]["gutter"],
                         "the pane narrows when its scrollbar arrives, so the editor shifts sideways: %r" % o)
        # REG-2792 (CI on ci/claude-v3833) - the page's own scrollbar style wins on CI's Chrome (10 px measured), so the
        # premise is that the scrollbar takes SOME room, never a width guessed from one platform (17 px is Windows')
        self.assertGreater(o["tall"]["gutter"] or 0, 0, "PREMISE: the styled scrollbar takes no room: %r" % o)

    def test_arrow_keys_on_the_sockets_field_keep_it_focused_and_still(self):
        board().run(STYLE + OPEN +
                    "document.getElementById('vault-planner-host').style.setProperty('--law-h', '260px');"
                    "var i = document.getElementById('cb-sockets'); i.scrollIntoView({ block: 'center' }); i.focus();"
                    # REG-2937 - and the pane is left SCROLLED (a nudge when centring the field did not scroll it), so a
                    # repaint that sends it back to the top is a change this case can see
                    "var ed = document.querySelector('#vault-planner-host .cb-ed');"
                    # #107 (REG-3812, windows-latest: 'top': 0 - narrower fonts fit the pane at 260 px, so nothing could
                    # scroll) - the modal is shortened 20 px at a time until the pane overflows, never by a font's luck
                    "var _lh = 260; while (ed && ed.scrollHeight - ed.clientHeight < 13 && _lh > 140) { _lh -= 20;"
                    " document.getElementById('vault-planner-host').style.setProperty('--law-h', _lh + 'px');"
                    " ed = document.querySelector('#vault-planner-host .cb-ed'); i.scrollIntoView({ block: 'center' }); }"
                    "if (ed && ed.scrollTop < 1) ed.scrollTop = Math.min(ed.scrollHeight - ed.clientHeight, 12);"
                    # #107 (REG-3812) - what the staging reached, said beside the premise if the pane still reads unscrolled
                    "window._lawStage = { lawH: _lh, overflow: ed ? ed.scrollHeight - ed.clientHeight : null,"
                    " topAfterStage: ed ? ed.scrollTop : null };"
                    "OUT.ok = 1;")
        # REG-2936 (CI on ci/claude-v3835: one 22 px "moved sideways" at step 1 on bytes a re-run passed) - the BASELINE is
        # read once the field has stopped moving before any key is pressed (two readings 150 ms apart agree), and how
        # long that took rides in the reading. The steps are NOT settled: a jump on repaint that later returns is the
        # defect he reported, so each step is still read 250 ms after its key.
        # REG-2936 again (CI on ci/claude-v3847j: the same 22 px at step 1, x only, y still) - the page's web fonts
        # (Inter via Google Fonts, display=swap) can land AFTER two equal readings, and a swapped font re-measures every
        # control left of Sockets in its flex row. The baseline is read once document.fonts has nothing left loading, so
        # what a step measures is the repaint, never a font arriving.
        # v3848 CI (twice on ci/claude-v3848, 'loading' != 'loaded'): a second face (another weight) can START loading
        # while the row settles, after fonts.ready resolved. So wait-and-settle repeats until a settled reading finds
        # nothing loading (at most 5 rounds); the PREMISE below still refuses a baseline read mid-font.
        # REG-2936 again (attempt 9, ci/claude-v3893 on 8a2f21fe9: the same 22.0625 px at step 1; the same SHA was
        # already green on grok/bundle-3891-3893 minutes earlier). fonts.status can be 'loaded' while a listed
        # weight has never been requested; the first sockets repaint then starts that face (display=swap) and
        # re-measures every control left of Sockets. The baseline now waits for the sheet and preloads every
        # listed Inter / Cinzel / Playfair face, so a step cannot start a new download.
        o0 = board().run(MEASURE + PRELOAD + "var a, b, k = 0, round = 0;"
                         "for (round = 0; round < 5; round++){ await document.fonts.ready; a = m(); b = a;"
                         "for (k = 0; k < 20; k++){ await new Promise(function(r){ setTimeout(r, 150); }); b = m();"
                         "  if (b.x === a.x && b.y === a.y && b.top === a.top) break; a = b; }"
                         "if (document.fonts.status === 'loaded') break; }"
                         "b.settledAfterMs = (k + 1) * 150; b.fontRounds = round + 1; b.fonts = document.fonts.status;"
                         "b.facesLoaded = _facesOk; b.sheetReady = _sheetOk; OUT.m = b;")["m"]
        self.assertEqual(o0["focus"], "cb-sockets", "PREMISE: the Sockets field did not take focus: %r" % o0)
        # REG-2937 (the v3832/v3833 push gate: RED_PROOF[2] BLIND) - at 420 px the hook's Chrome did not scroll the edit pane,
        # so its scrollTop was 0 before any key and putting it back after a repaint changed nothing this case can see.
        # The case now opens the modal at the 260 px its sibling proves makes the pane scroll, and says so first.
        _stage = board().run("OUT.s = window._lawStage || null;").get("s")
        if os.name == "nt" and isinstance(_stage, dict) and _stage.get("overflow") == 0:
            # #107 (REG-3812, windows-latest run 43308030093: lawH 140, overflow 0) - MEASURED: on Windows the edit pane never
            # overflows even at a 140 px modal, so the reset this law guards cannot happen there or be seen - UNMEASURED here.
            # Its two proofs declare posix; anywhere else a pane that will not scroll stays the PREMISE red below.
            self.skipTest("the edit pane never overflows on this venue (measured down to a 140 px modal) - UNMEASURED here")
        self.assertGreater(o0["top"] or 0, 0, "PREMISE: the edit pane is not scrolled, so a repaint that sends it back to "
                                             "the top would change nothing this case can see: %r (staging: %r - topAfterStage > 0 "
                                             "and top 0 here means the baseline's repaint reset it)" % (o0, _stage))
        self.assertEqual(o0["fonts"], "loaded", "PREMISE: a web font was still loading when the baseline was read: %r" % o0)
        self.assertLess(o0["settledAfterMs"], 3000, "PREMISE: the planner never stopped moving before a key was pressed: %r" % o0)
        steps = []
        for _ in range(3):
            key_up()
            steps.append(board().run(MEASURE + "OUT.m = m();")["m"])
        for k, st in enumerate(steps):
            self.assertEqual(st["focus"], "cb-sockets", "step %d: the repaint took focus off the Sockets field: %r" % (k + 1, st))
            self.assertEqual(st["draft"], o0["draft"] + k + 1, "step %d: the arrow key did not move the draft live: %r" % (k + 1, st))
            self.assertLess(abs(st["x"] - o0["x"]), 1, "step %d: the Sockets field moved sideways: %r -> %r" % (k + 1, o0, st))
            self.assertLess(abs(st["y"] - o0["y"]), 1, "step %d: the Sockets field moved up or down: %r -> %r" % (k + 1, o0, st))
            self.assertLess(abs(st["top"] - o0["top"]), 1, "step %d: the pane's scroll jumped: %r -> %r" % (k + 1, o0, st))
        o = board().run("var a = JSON.parse(window.LSR.getItem('d2r_muleAssign') || '{}');"
                        "OUT.mid = Object.keys(a).filter(function(k){ return /Monarch/.test(k); });"
                        "window.vaultPlannerClose(); await new Promise(function(r){ setTimeout(r, 200); });"
                        "var b = JSON.parse(window.LSR.getItem('d2r_muleAssign') || '{}');"
                        "OUT.done = Object.keys(b).filter(function(k){ return /Monarch/.test(k); });")
        self.assertEqual(o["mid"], [], "the edit was filed before Done: %r" % o)
        self.assertEqual(len(o["done"]), 1, "Done did not file the one edit: %r" % o)


RED_PROOF = [
    {"why": "REG-2833 - the edit pane reserves no gutter, so the editor shifts when its scrollbar arrives",
     "file": "bible.html",
     "find": ".cb-ed{scrollbar-gutter:stable}",
     "replace": ".cb-ed{scrollbar-gutter:auto}",
     "matches": 1},
    {"why": "REG-2833 - the repaint drops the field he is in",
     "file": "bible.html",
     "find": "    if (_fid){ var _f1 = document.getElementById(_fid); if (_f1 && typeof _f1.focus === 'function'){ try { _f1.focus({ preventScroll: true }); } catch (eFc) {} } }\n",
     "replace": "",
     "matches": 1, "needs": "posix"},
    {"why": "REG-2833 - the repaint sends the edit pane back to the top",
     "file": "bible.html",
     "find": "    if (_ed1 && _edTop) _ed1.scrollTop = _edTop;\n",
     "replace": "",
     "matches": 1, "needs": "posix"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
