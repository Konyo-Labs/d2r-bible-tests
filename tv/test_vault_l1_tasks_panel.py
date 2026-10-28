# -*- coding: utf-8 -*-
"""Vault L1 - MOVE TASKS is a clean numbered checklist, one line per task (Vault v2: an overlay opened from its FAB).

Elad, 2026-10-20: "MOVE TASKS becomes a right-side panel. A clean numbered checklist, one line per task
(Arcanna's Sign · MANUAL → SETS-REST (3,1)), Moves then Throw-outs, the done ones collapsed at the bottom. Each line
has a tick box (his hand, or the reels: gone k/5), and clicking a line opens BEFORE | AFTER. The left keeps add, find,
the mules and the locked line, each with one plain line. Cut the wordy text."
Vault v2 (Elad, 2026-10-23, approved design): the right-side panel became an OVERLAY opened from a FAB above the inbox
FAB - the vault keeps its full width and the list floats over it. Everything else here holds unchanged.
Driven on the SHIPPED page in Chrome. NO CHROME = a declared skip. RED_PROOF below.
[[regression-guard]]
"""
import json
import os
import re
import sys
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
HEAD = "Arcanna's Head (helm)"     # screenshot-seen, the rules default it to junk -> a THROW OUT task
SHAKO = "Harlequin Crest (Shako)"  # screenshot-seen, routed -> a move task
SOJ = "The Stone of Jordan"        # worn -> the locked line, never a task
SIGN = "Arcanna's Sign"            # hand-added -> MANUAL -> SETS-REST


def _prov(holder, loc, cell, n=2):
    return {"kind": "owned", "source": "tv", "seen": n,
            "looks": [{"session": "w%d" % i, "frame": "f%d" % i, "holder": holder, "loc": loc, "cell": cell} for i in range(n)]}


def board():
    if "b" not in _B:
        _B["b"] = H.Board().open()
    return _B["b"]


def tearDownModule():
    b = _B.pop("b", None)
    if b is not None:
        b.close()


def world():
    board().seed({"d2r_owned": [HEAD, SHAKO, SOJ], "d2r_muleAssign": {}, "d2r_vaultRecords": None,
                  "d2r_vaultProv": {HEAD: _prov("MAIN", "stash", "c0r0"), SHAKO: _prov("MAIN", "stash", "c4r0"),
                                    SOJ: _prov("MAIN", "equipment", "c0r0")}})
    return board().run("window._vaultAutoIntakeSet(false); window.vaultHandAdd(%s); window.switchTab('vault');"
                       "window._vaultMovePaint(); OUT.ok = 1;" % json.dumps(SIGN))


READ = r"""
function L(){ return document.getElementById('vault-move-list'); }
function open_(nm){ return L().querySelector('.vtk-list:not([data-sec="done"]) .vtk-line[data-name^="' + nm.replace(/"/g, '\\"') + '"]'); }
function done_(nm){ return L().querySelector('.vtk-donebox .vtk-line[data-name^="' + nm.replace(/"/g, '\\"') + '"]'); }
function gone(sid){ return window._vaultGoneObserve({ session: sid, holder: 'MAIN', location: 'stash', complete: true, items: [], ground: [] }); }  /* REG-2861 a whole read */
"""


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class TheTasksPanel(unittest.TestCase):

    def _at(self, w, h):
        b = board()
        b.t.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)
        try:
            return b.run("window.switchTab('vault'); var c = document.getElementById('mule-vault-card');"
                         "if (c && c.classList.contains('collapsed')) window.toggleCardCollapse('mule-vault-card');"
                         "window.vaultTasksTog(false); await new Promise(function(r){ setTimeout(r, 200); });"
                         "var m0 = document.querySelector('#mule-vault-card .vault-main').getBoundingClientRect();"
                         "window.vaultTasksTog(true); await new Promise(function(r){ setTimeout(r, 300); });"
                         "var a = document.getElementById('vault-tasks'), p = a.getBoundingClientRect();"
                         "var m = document.querySelector('#mule-vault-card .vault-main').getBoundingClientRect();"
                         "OUT.p = [p.left, p.width, p.top, p.right, p.bottom]; OUT.m0 = [m0.left, m0.width]; OUT.m = [m.left, m.width];"
                         "OUT.pos = getComputedStyle(a).position; OUT.vw = innerWidth; OUT.vh = innerHeight;"
                         "window.vaultTasksTog(false);")
        finally:
            b.t.send("Emulation.clearDeviceMetricsOverride")

    def test_the_list_lives_in_the_move_tasks_overlay(self):
        world()
        o = board().run(READ + "var a = L().closest('aside'); OUT.aside = a ? a.id : null;"
                        "OUT.inMain = !!L().closest('.vault-main');"
                        "OUT.leftKeeps = ['vault-find-input', 'vault-planner-q', 'vault-shelf', 'vault-equipped'].map(function(id){"
                        "  var e = document.getElementById(id); return !!(e && e.closest('.vault-main')); });")
        self.assertEqual(o["aside"], "vault-tasks", "MOVE TASKS is not in its own panel")
        self.assertFalse(o["inMain"], "MOVE TASKS sits inside the vault column again")
        self.assertTrue(all(o["leftKeeps"]), "add, find, the mules and the locked line must stay in the vault: %r" % o)
        for w, h in ((1440, 900), (1280, 720)):
            g = self._at(w, h)
            self.assertEqual(g["pos"], "fixed", "MOVE TASKS is not an overlay at %dx%d: %r" % (w, h, g))
            self.assertEqual(g["m"], g["m0"], "opening MOVE TASKS moved or narrowed the vault at %dx%d: %r" % (w, h, g))
            self.assertGreaterEqual(g["p"][1], 300, "the overlay is too narrow for one line at %dx%d: %r" % (w, h, g))
            self.assertTrue(0 <= g["p"][0] and g["p"][3] <= g["vw"] and g["p"][2] >= 0 and g["p"][4] <= g["vh"],
                            "the overlay leaves the screen at %dx%d: %r" % (w, h, g))

    def test_one_numbered_line_per_task_moves_then_throw_outs(self):
        world()
        o = board().run(READ + "var ls = [].slice.call(L().querySelectorAll('.vtk-line'));"
                        "OUT.lines = ls.map(function(e){ return { n: e.getAttribute('data-name') || ('make ' + e.getAttribute('data-mule')), kind: e.getAttribute('data-kind'),"
                        "  ticks: e.querySelectorAll('input[type=checkbox].vtk-tick').length, say: (e.querySelector('.vtk-say') || {}).textContent || '',"
                        "  num: getComputedStyle(e, '::before').content }; });"
                        "var secs = [].map.call(L().querySelectorAll('.vtk-sec'), function(e){ return e.getAttribute('data-sec'); }); OUT.secs = secs;"
                        "OUT.grids = L().querySelectorAll('.vmv-grid').length;")
        # REG-2990 - a "Create mule <X> in the game" row (REG-2895's CHARMS mule, a WAR mule) is a task line too: it carries the
        # mule's id, not an item name, so it is keyed "make <id>" (a None name raised here on v3837's CI)
        names = [l["n"] for l in o["lines"]]
        self.assertEqual(len(names), len(set(names)), "a task has more than one line: %r" % names)
        self.assertTrue(all(l["ticks"] == 1 for l in o["lines"]), "every line needs exactly one tick box: %r" % o["lines"])
        self.assertTrue(all(l["num"] and l["num"] != "none" for l in o["lines"]), "lines are not numbered: %r" % o["lines"])
        sign = [l for l in o["lines"] if l["n"].startswith(SIGN)]
        self.assertTrue(sign, o)
        self.assertRegex(sign[0]["say"], r"^Arcanna's Sign.* · MANUAL → SETS-REST \(\d+,\d+\)$", sign[0]["say"])
        self.assertIn("moves", o["secs"])
        self.assertIn("throws", o["secs"])
        self.assertLess(o["secs"].index("moves"), o["secs"].index("throws"), "Throw-outs come before Moves: %r" % o["secs"])
        self.assertEqual(o["grids"], 0, "the panel still draws the wide target grids (that is BEFORE | AFTER's job)")
        self.assertFalse(any(SOJ in l["n"] for l in o["lines"]), "worn gear became a task")

    def test_the_reels_show_progress_and_done_collapses_at_the_bottom(self):
        world()
        o = board().run(READ + "gone('p1'); OUT.k = ((open_(%s) || {}).textContent || '');"
                        "gone('p2'); gone('p3'); gone('p4'); gone('p5');"
                        "OUT.openAfter = !!open_(%s); OUT.done = !!done_(%s);"
                        "var d = L().querySelector('.vtk-donebox'); OUT.collapsed = !!(d && !d.open);"
                        "OUT.last = d ? (d === L().lastElementChild) : false;" % (json.dumps(HEAD), json.dumps(HEAD), json.dumps(HEAD)))
        self.assertIn("gone 1/5", o["k"], "a counted session does not show on the line: %r" % o["k"])
        self.assertFalse(o["openAfter"], "a drained throw-out is still an open task")
        self.assertTrue(o["done"], "a drained task vanished instead of going to Done")
        self.assertTrue(o["collapsed"], "Done is not collapsed")
        self.assertTrue(o["last"], "Done is not at the bottom")

    def test_his_tick_moves_a_task_to_done_and_a_click_opens_before_after(self):
        world()
        # The tick re-renders the row into Done, so a click that bubbles on reaches a DETACHED row whose expand never
        # paints - and the old BEFORE | AFTER popup is removed (#144.14). Count the row's expand handler instead: a tick that
        # reaches it is the bug, whether or not anything shows.
        o = board().run(READ + "var __n = 0, __o = window._vaultTaskExpand;"
                        "window._vaultTaskExpand = function(){ __n++; return __o.apply(this, arguments); };"
                        "var r = open_(%s); r.querySelector('.vtk-tick').click();"
                        "window._vaultTaskExpand = __o; OUT.expandOnTick = __n;"
                        "OUT.open = !!open_(%s); OUT.done = !!done_(%s);"
                        "var s = open_(%s); s.click(); var x = s.nextElementSibling;"
                        "OUT.cmp = !!(x && x.classList.contains('vtk-expand-li') && x.querySelector('.vtx-from') && x.querySelector('.vtx-to'));"
                        "s.click();" % (json.dumps(SHAKO), json.dumps(SHAKO), json.dumps(SHAKO), json.dumps(SIGN)))
        self.assertEqual(o["expandOnTick"], 0, "the tick box also opened BEFORE | AFTER (its click reached the row's expand)")
        self.assertFalse(o["open"], "his tick left the task open")
        self.assertTrue(o["done"], "his tick did not move the task to Done")
        self.assertTrue(o["cmp"], "clicking a line does not expand its own FROM | TO")

    def test_find_names_the_throw_out_task_not_the_dock(self):
        world()
        o = board().run("var i = document.getElementById('vault-find-input'); i.value = 'arcanna\\'s head';"
                        "i.dispatchEvent(new Event('input', { bubbles: true })); await new Promise(function(r){ setTimeout(r, 900); });"
                        "OUT.text = document.getElementById('vault-find-results').textContent;"
                        "i.value = ''; window.vaultFind('');")
        self.assertIn("THROW OUT task", o["text"], o["text"])
        self.assertNotIn("in the dock", o["text"], "FIND still sends him to the dock for a THROW OUT task: %r" % o["text"])

    def test_each_left_area_says_one_plain_line_and_the_wordy_text_is_gone(self):
        world()
        o = board().run("OUT.says = [].map.call(document.querySelectorAll('#mule-vault-card .vault-say, #vault-tasks .vault-say'), function(e){"
                        "  return [e.getAttribute('data-say'), e.textContent, !!e.closest('.vault-main')]; });"
                        "OUT.eq = (document.querySelector('#vault-equipped .vault-equipped-k') || {}).textContent || '';"
                        "window.vaultOrganizePaint([%s], []); var og = document.getElementById('vault-organize');"
                        "OUT.org = og ? og.innerHTML : ''; OUT.orgShown = !!(og && !og.hidden);"
                        "OUT.all = document.getElementById('mule-vault-card').innerText;" % json.dumps(SHAKO))
        by = {k: (t, left) for k, t, left in o["says"]}
        for k in ("find", "mules"):
            self.assertIn(k, by, "the %s area has no plain line" % k)
            self.assertTrue(by[k][1], "the %s line is not on the left" % k)
            self.assertLessEqual(len(by[k][0]), 70, "the %s line is not short: %r" % (k, by[k][0]))
        self.assertIn("tasks", by)
        self.assertEqual(o["eq"], "Equipped (locked)")
        self.assertTrue(o["orgShown"], "premise: the organizer painted")
        self.assertNotIn("the picture it was read on", o["org"], "the wordy 'where each item goes' header is back")
        self.assertNotIn("by DEFAULT", o["all"], "the wordy by-DEFAULT throw-out advice is back")


RED_PROOF = [
    {"why": "FIND sends him to the dock for a THROW OUT task.",
     "file": "bible.html",
     "find": "        : (w.kind === 'dock' && typeof window._vaultThrowRoute === 'function' && window._vaultThrowRoute(n)) ?",
     "replace": "        : (false) ?",
     "matches": 1},
    {"why": "MOVE TASKS goes back into the vault column (the boot hangs the overlay inside .vault-main, not on <body>).",
     "file": "bible.html",
     "find": "if (el && document.body && el.parentNode !== document.body) document.body.appendChild(el);",
     "replace": "if (el && document.body && el.parentNode !== document.body) document.querySelector('#mule-vault-card .vault-main').appendChild(el);",
     "matches": 1},
    {"why": "MOVE TASKS stops being an overlay and takes layout room again (in-flow, pushing the vault).",
     "file": "bible.html",
     "find": ".vault-tasks-pop{position:fixed;",
     "replace": ".vault-tasks-pop{position:static;",
     "matches": 1},
    {"why": "A line loses its tick box.",
     "file": "bible.html",
     "find": "            : '<input type=\"checkbox\" class=\"vtk-tick vmv-mark\" aria-label=\"mark moved\"",
     "replace": "            : '<input type=\"hidden\" class=\"vtk-tick vmv-mark\" aria-label=\"mark moved\"",
     "matches": 1},
    {"why": "Lines lose their numbers.",
     "file": "bible.html",
     "find": ".vtk-line::before{content:counter(vtk) \".\";",
     "replace": ".vtk-line::before{content:none;",
     "matches": 1},
    {"why": "The line goes back to the wordy holder · stash · cell · col · row say.",
     "file": "bible.html",
     "find": " + ' → ' + (thr ? '<b class=\"vmv-nowhere\">NOWHERE</b>' : '<span class=\"vtk-to\">' + esc(_vtkPlace(t.to, false)) + '</span>') + '</span>'",
     "replace": " + ' → ' + (thr ? '<b class=\"vmv-nowhere\">NOWHERE</b>' : '<span class=\"vtk-to\">' + esc(_vaultMovePlaceSay(t.to)) + '</span>') + '</span>'",
     "matches": 1},
    {"why": "Throw-outs are listed before Moves.",
     "file": "bible.html",
     "find": "    var html = head;\n",
     "replace": "    var html = head + (throws.length ? '<p class=\"vtk-sec\" data-sec=\"throws\">Throw-outs</p>' : '');\n",
     "matches": 1},
    {"why": "The wide target grids come back into the panel.",
     "file": "bible.html",
     "find": "    html += unrHtml;\n",
     "replace": "    html += unrHtml + _vaultMoveGridHtml(moves);\n",
     "matches": 1},
    {"why": "The line hides the reels' gone k/5 progress.",
     "file": "bible.html",
     "find": "      var gs = (typeof _vaultGoneSay === 'function') ? _vaultGoneSay(t) : ((t.gone && t.gone.length) ? 'gone ' + t.gone.length + '/' + (window.VAULT_GONE_SESSIONS || 5) : '');\n",
     "replace": "      var gs = '';\n",
     "matches": 1},
    {"why": "A drained task vanishes instead of going to Done.",
     "file": "bible.html",
     "find": "        else if (thr.task.status === 'closed') done.push(",
     "replace": "        else if (false) done.push(",
     "matches": 1},
    {"why": "Done is open, not collapsed.",
     "file": "bible.html",
     "find": "html += '<details class=\"vtk-donebox\">",
     "replace": "html += '<details open class=\"vtk-donebox\">",
     "matches": 1},
    {"why": "His tick does nothing.",
     "file": "bible.html",
     "find": "    } else res = _vaultMoveMark(name, copyIx);\n",
     "replace": "    } else res = null;\n",
     "matches": 1},
    {"why": "The tick box click also opens BEFORE | AFTER.",
     "file": "bible.html",
     "find": "              + ' onclick=\"event.stopPropagation();window._vaultTaskTick(",
     "replace": "              + ' onclick=\"window._vaultTaskTick(",
     "matches": 1},
    {"why": "The mules lose their plain line.",
     "file": "bible.html",
     "find": "      <h3 class=\"vault-say vault-sec-h\" data-say=\"mules\">Your mules <span class=\"vault-sec-sub\">Click one to open its stash.</span></h3>\n",
     "replace": "",
     "matches": 1},
    {"why": "The wordy organizer header comes back.",
     "file": "bible.html",
     "find": "var h = '<p class=\"vault-org-h\">Where it goes · nothing moves until you move it'",
     "replace": "var h = '<p class=\"vault-org-h\">Where each item goes — the mule, the stash cell, and the picture it was read on · nothing moves until you move it'",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
