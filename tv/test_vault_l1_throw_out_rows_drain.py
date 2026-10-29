# -*- coding: utf-8 -*-
"""Vault L1 - a junk route is a THROW OUT row in MOVE TASKS, and every row drains on direct proof only.

Elad, 2026-10-20, at his live Vault: throw-out suggestions leave the Unsorted Dock. They are THROW OUT rows next to
the moves, target NOWHERE, one plain reason ("set never ruled"), Keep / Junk inline. Keep turns the row into a normal
move. The dock keeps only items with no route. A hand-added unruled set piece stays kept and routed (his ruling), so
it is never a THROW OUT row.

The drain (same pipeline, closed by sighting):
  - a move seen in its TARGET cell closes at once;
  - a row whose item is missing from its first-witnessed cell closes only after 5 reel sessions in which a frame
    actually SHOWED that cell without the item; a session whose frames never show that container counts nothing;
  - a re-sighting at that cell resets the count; the row says "gone k/5";
  - a throw-out whose item already left its cell and is then read as a dropped-item label on the ground closes at once.
Driven on the SHIPPED page through window._vaultGoneObserve. NO CHROME = a declared skip. RED_PROOF below.
[[regression-guard]] [[unknown-stays-unknown]]
"""
import json
import os
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
HEAD = "Arcanna's Head (helm)"     # screenshot-seen, the rules default it to junk (set never ruled)
SHAKO = "Harlequin Crest (Shako)"  # screenshot-seen, routed to the shared stash
SOJ = "The Stone of Jordan"        # seen on the equipment
SIGN = "Arcanna's Sign"            # hand-added unruled set piece: kept and routed


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
function bag(){ var m = {}; try { (JSON.parse(LSR.getItem('d2r_vaultRecords') || '{}').records || []).forEach(function(r){ if (r.move) m[r.name] = r.move; }); } catch (e) {} return m; }
function row(nm){ var l = document.getElementById('vault-move-list'); return l ? l.querySelector('.vtk-list:not([data-sec="done"]) .vmv-row[data-name="' + nm.replace(/"/g, '\\"') + '"]') : null; } /* an open task; a drained one sits in Done */
function obs(f){ return window._vaultGoneObserve(f); }
"""


def frame(session, holder="MAIN", location="stash", items=(), ground=()):
    # REG-2861 - these frames are whole reads of their container: only such a frame may count an item gone
    return json.dumps({"session": session, "holder": holder, "location": location, "complete": True,
                       "items": [{"name": n, "cell": c} for n, c in items], "ground": list(ground)})


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class ThrowOutRows(unittest.TestCase):

    def test_a_junk_route_is_a_throw_out_row_not_a_dock_chip(self):
        world()
        o = board().run(READ + "var r = row(%s); OUT.has = !!r; OUT.kind = r && r.getAttribute('data-kind');"
                        "OUT.text = r ? r.textContent + ' ' + ((r.querySelector('[data-reason]') || {getAttribute: function(){ return ''; }}).getAttribute('data-reason') || '') : ''; OUT.keep = !!(r && r.querySelector('.vmv-keep'));"
                        "OUT.reason = r ? ((r.querySelector('[data-reason]') || {getAttribute: function(){ return null; }}).getAttribute('data-reason')) : null;"
                        "OUT.junk = !!(r && r.querySelector('.vmv-junk')); OUT.dock = window._vaultDockNames();"
                        "OUT.org = (document.getElementById('vault-organize') || {}).textContent || '';"
                        "OUT.list = document.getElementById('vault-move-list').textContent;" % json.dumps(HEAD))
        self.assertTrue(o["has"], "no THROW OUT row for the screenshot-seen junk item")
        self.assertEqual(o["kind"], "throw")
        self.assertIn("NOWHERE", o["text"])
        # the plain reason rides on the line (hover + data-reason). v3849 (6fff0ef41): an unvalued set piece is ruled
        # "low set piece" now - no set is "never ruled" - so the plain reason is that one
        self.assertIn("low set piece", o["text"])
        # REG-2962 - ONE plain reason: the why's first clause, never the whole advice ("... track for chronicle, discard: ...")
        self.assertEqual(o["reason"], "low set piece", "the row's reason is not the one plain clause: %r" % o["reason"])
        self.assertNotIn("by DEFAULT", o["list"], "the wordy throw-out advice is back in MOVE TASKS")
        self.assertTrue(o["keep"] and o["junk"], "Keep / Junk are not inline on the row")
        self.assertNotIn(HEAD, o["dock"] or [], "the junk item still sits in the Unsorted Dock")
        self.assertNotIn("throw-out advice", o["org"], "the organizer still prints throw-out advice")

    def test_his_hand_added_unruled_set_piece_is_never_a_throw_out_row(self):
        world()
        o = board().run(READ + "var r = row(\"Arcanna's Sign (amulet)\"); OUT.kind = r && r.getAttribute('data-kind');"
                        "OUT.to = (bag()[\"Arcanna's Sign (amulet)\"] || {}).to;")
        self.assertIsNone(o["kind"], "his hand add became a THROW OUT row")
        self.assertEqual((o["to"] or {}).get("holder"), "SETS-REST")

    def test_keep_turns_the_row_into_a_normal_move(self):
        world()
        o = board().run(READ + "window._vaultThrowKeep(%s, 0); var m = bag()[%s]; OUT.m = m; var r = row(%s);"
                        "OUT.kind = r && r.getAttribute('data-kind'); OUT.status = r && r.getAttribute('data-status');"
                        % (json.dumps(HEAD), json.dumps(HEAD), json.dumps(HEAD)))
        self.assertNotEqual(o["m"].get("kind"), "throw", o["m"])
        self.assertTrue(o["m"].get("kept"), o["m"])
        self.assertTrue(o["m"]["to"]["cell"], "Keep left no target cell: %r" % o["m"])
        self.assertIsNone(o["kind"])
        self.assertEqual(o["status"], "to-move")

    def test_junk_confirms_and_the_row_stays_until_drained(self):
        world()
        o = board().run(READ + "window._vaultThrowJunk(%s, 0); OUT.m = bag()[%s]; var r = row(%s); OUT.j = r && r.getAttribute('data-junk');"
                        % (json.dumps(HEAD), json.dumps(HEAD), json.dumps(HEAD)))
        self.assertTrue(o["m"].get("junk"))
        self.assertEqual(o["j"], "1")


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class TheDrain(unittest.TestCase):

    def test_five_sessions_of_direct_proof_close_a_throw_out_with_progress(self):
        world()
        js = READ
        for i in range(1, 5):
            js += "obs(%s);" % frame("s%d" % i)
        js += "var r = row(%s); OUT.say4 = r ? r.textContent : null; OUT.m4 = bag()[%s];" % (json.dumps(HEAD), json.dumps(HEAD))
        js += "obs(%s); OUT.m4b = bag()[%s];" % (frame("s4"), json.dumps(HEAD))  # same session again: still 4
        js += "obs(%s); OUT.m5 = bag()[%s]; OUT.row5 = !!row(%s);" % (frame("s5"), json.dumps(HEAD), json.dumps(HEAD))
        o = board().run(js)
        self.assertIn("gone 4/5", o["say4"] or "", "the row does not show its drain progress")
        self.assertEqual(o["m4"]["status"], "to-move")
        self.assertEqual(len(o["m4b"]["gone"]), 4, "one session counted twice")
        self.assertEqual(o["m5"]["status"], "closed", o["m5"])
        self.assertFalse(o["row5"], "a drained row is still an open task")

    def test_container_not_shown_so_no_count(self):
        world()
        js = READ
        for i in range(1, 9):
            js += "obs(%s);" % frame("x%d" % i, holder="SOME-MULE")       # another container entirely
            js += "obs(%s);" % frame("y%d" % i, location="inventory")    # same holder, other container
        js += "OUT.m = bag()[%s];" % json.dumps(HEAD)
        o = board().run(js)
        self.assertEqual(o["m"].get("gone"), None, "a session that never showed the cell was counted: %r" % o["m"])
        self.assertEqual(o["m"]["status"], "to-move")

    def test_a_re_sighting_resets_the_count(self):
        world()
        js = READ
        for i in range(1, 5):
            js += "obs(%s);" % frame("s%d" % i)
        js += "obs(%s);" % frame("s5", items=[(HEAD, "c0r0")])
        js += "OUT.m = bag()[%s];" % json.dumps(HEAD)
        o = board().run(js)
        self.assertEqual(o["m"].get("gone"), None, o["m"])
        self.assertEqual(o["m"]["status"], "to-move")

    def test_seen_on_the_ground_after_leaving_closes_a_throw_out_at_once(self):
        world()
        js = READ
        js += "obs(%s); OUT.before = bag()[%s].status;" % (frame("g0", holder="ELSEWHERE", ground=[HEAD]), json.dumps(HEAD))
        js += "obs(%s); obs(%s); OUT.m = bag()[%s];" % (frame("g1"), frame("g2", holder="ELSEWHERE", location="ground", ground=[HEAD]), json.dumps(HEAD))
        o = board().run(js)
        self.assertEqual(o["before"], "to-move", "a ground label before the item left its cell closed the row")
        self.assertEqual(o["m"]["status"], "closed")
        self.assertEqual(o["m"].get("closedBy"), "seen on the ground")

    def test_one_dropped_copy_closes_only_one_copys_row(self):
        """review #247: two copies of the same junk both left their cells; ONE ground label closes ONE row, a 2nd closes the other"""
        world()
        js = READ + r"""
var st = JSON.parse(LSR.getItem('d2r_vaultRecords')); var r0 = st.records.filter(function(r){ return r.name === %s; })[0];
var r1 = JSON.parse(JSON.stringify(r0)); r1.copyIx = 1; if (r1.recId) r1.recId = r1.recId + '#1'; r1.move.from.cell = 'c1r0'; if (r1.sight) r1.sight.cell = 'c1r0';
st.records.push(r1); LSR.setItem('d2r_vaultRecords', JSON.stringify(st));
function both(){ return (JSON.parse(LSR.getItem('d2r_vaultRecords')).records || []).filter(function(r){ return r.name === %s && r.move; })
  .map(function(r){ return [r.copyIx || 0, r.move.status]; }).sort(); }
OUT.b0 = both();
""" % (json.dumps(HEAD), json.dumps(HEAD))
        js += "obs(%s); OUT.left = both();" % frame("d1")  # both copies' cells shown empty
        js += "obs(%s); OUT.one = both();" % frame("d2", holder="ELSEWHERE", location="ground", ground=[HEAD])
        js += "obs(%s); OUT.two = both();" % frame("d3", holder="ELSEWHERE", location="ground", ground=[HEAD])
        o = board().run(js)
        self.assertEqual(o["b0"], [[0, "to-move"], [1, "to-move"]], "PREMISE: two open copy rows: %r" % o["b0"])
        self.assertEqual(o["left"], [[0, "to-move"], [1, "to-move"]])
        self.assertEqual(sorted(x[1] for x in o["one"]), ["closed", "to-move"],
                         "one dropped copy must close exactly one copy's row: %r" % o["one"])
        self.assertEqual(o["two"], [[0, "closed"], [1, "closed"]], "the 2nd drop did not close the other copy: %r" % o["two"])

    def test_a_move_seen_at_its_target_in_two_sessions_closes(self):
        """REG-2843 - his done rule: one full look of the target is half-way; a second session read after it opened closes it"""
        world()
        o = board().run(READ + "var t = bag()[%s].to, T0 = Date.now(); OUT.to = t;"
                        " function look(n){ var ms = T0 + n * 60000; return { session: 's_' + ms + '_' + n, at: new Date(ms).toISOString(),"
                        " holder: t.holder, location: t.location, items: [{ name: %s, cell: t.cell }] }; }"
                        " obs(look(1)); OUT.h = bag()[%s]; obs(look(2)); OUT.m = bag()[%s];"
                        % (json.dumps(SHAKO), json.dumps(SHAKO), json.dumps(SHAKO), json.dumps(SHAKO)))
        self.assertEqual(o["h"]["status"], "to-move", "one full look closed the task: %r" % o)
        self.assertEqual(len(o["h"].get("seen") or []), 1, o)
        self.assertEqual(o["m"]["status"], "verified", o)

    def test_a_vanished_move_drains_after_five_sessions(self):
        world()
        js = READ
        for i in range(1, 6):
            js += "obs(%s);" % frame("v%d" % i, items=[(HEAD, "c0r0")])  # HEAD still there, SHAKO gone from c4r0
            if i == 2:
                js += "var r = row(%s); OUT.say2 = r ? r.textContent : null;" % json.dumps(SHAKO)
        js += "OUT.m = bag()[%s]; OUT.h = bag()[%s];" % (json.dumps(SHAKO), json.dumps(HEAD))
        o = board().run(js)
        self.assertIn("gone 2/5", o["say2"] or "")
        self.assertEqual(o["m"]["status"], "closed", o["m"])
        self.assertEqual(o["h"].get("gone"), None, "the item still in its cell was counted gone")

    def test_distinct_attacks_clear_the_vault_apply_wilson_bar(self):
        from confidence import confluence, wilson_lower
        import self_arming as SA
        bar = SA.LOCKS["vault.apply"]["bar"]
        kinds_bar = SA.LOCKS["vault.apply"]["kinds_bar"]
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        conf = confluence(["sabotage"], SA.KINDS)
        msg = ("vault L1 throw-out + drain: %d distinct attacks, wilson %.4f vs bar %.3f; kinds %.2f vs %.2f"
               % (n, w, bar, conf, kinds_bar))
        print(msg)
        self.assertGreaterEqual(w, bar, msg)
        self.assertLess(conf, kinds_bar, msg)


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class OneItemOnePlace(unittest.TestCase):
    """Elad 2026-10-20: remove the duplicate item chips around MOVE TASKS - an item with a row is drawn once."""

    def test_an_item_with_a_row_is_not_drawn_again(self):
        world()
        o = board().run("window.renderVault && window.renderVault(); var rows = {};"
                        "document.querySelectorAll('#vault-move-list .vmv-row').forEach(function(r){ rows[r.getAttribute('data-name')] = 1; });"
                        "OUT.rows = Object.keys(rows); OUT.chips = Array.from(document.querySelectorAll('#vault-dock [data-vault-item]')).map(function(c){ return c.getAttribute('data-vault-item'); });"
                        "OUT.org = Array.from(document.querySelectorAll('#vault-organize .vault-org-row[data-name]')).map(function(c){ return c.getAttribute('data-name'); });")
        self.assertIn(SHAKO, o["rows"], "premise: the routed Shako has a move row")
        self.assertIn("Arcanna's Sign (amulet)", o["rows"])
        dup = [n for n in o["chips"] + o["org"] if n in o["rows"]]
        self.assertEqual(dup, [], "drawn twice - a MOVE TASKS row and a chip/organizer line: %r" % dup)


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class EquippedLine(unittest.TestCase):
    """Elad 2026-10-20: locked equipped gear reads on a quiet 'Equipped (locked)' line, not in MOVE TASKS."""

    def test_worn_gear_is_a_quiet_line_outside_move_tasks(self):
        world()
        o = board().run("var e = document.getElementById('vault-equipped'); OUT.hidden = e.hidden; OUT.text = e.textContent;"
                        "var l = document.getElementById('vault-move-list'); OUT.inList = l.contains(e); OUT.list = l.textContent;")
        self.assertFalse(o["hidden"], "no Equipped (locked) line")
        self.assertIn("Equipped (locked)", o["text"])
        self.assertIn(SOJ, o["text"])
        self.assertFalse(o["inList"], "the equipped line sits inside MOVE TASKS")
        self.assertNotIn(SOJ, o["list"], "worn gear still shows in MOVE TASKS")

    def test_a_locked_record_leaves_the_move_tasks_head(self):
        world()
        o = board().run("OUT.h = window._vaultMoveHtml({ tasks: [], groups: [], locks: [{ name: 'Griffon\\'s Eye', say: 'LOCKED' }, { name: 'Tyrael\\'s Might', say: 'WATCHING' }] });")
        self.assertNotIn("LOCKED", o["h"], "LOCKED chips still ride in the MOVE TASKS head")
        self.assertIn("WATCHING", o["h"], "the control: WATCHING stays")


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class AnUnseenThrowOutTakesItsFirstSighting(unittest.TestCase):
    """Found on his real store (2026-10-20 click-through): all 9 THROW OUT rows were made before any frame saw the item,
    so they read 'not seen yet' forever and the drain had no cell to watch."""

    def test_the_first_sighting_fills_from_on_the_same_row_and_the_drain_counts(self):
        board().seed({"d2r_owned": [HEAD], "d2r_muleAssign": {}, "d2r_vaultRecords": None,
                      "d2r_vaultProv": {HEAD: {"kind": "owned", "source": "tv", "seen": 0, "looks": []}}})
        o = board().run(READ + "window._vaultAutoIntakeSet(false); window.switchTab('vault'); window._vaultMovePaint();"
                        "OUT.f0 = (row(%s) || {getAttribute: function(){ return 'missing'; }}).getAttribute('data-from');"
                        "window._ownedProvWrite(%s, { source: 'intake-read', by: 'reel', holder: 'MAIN', loc: 'stash', cell: 'stash:c3r2',"
                        "  sessionId: 'z1', frameId: 'z-a', ts: Date.now() });"
                        "window._vaultMovePaint(); OUT.f1 = (row(%s) || {getAttribute: function(){ return 'missing'; }}).getAttribute('data-from');"
                        "OUT.rows = document.querySelectorAll('#vault-move-list .vmv-row[data-name=\"' + %s + '\"]').length;"
                        # REG-3014 - a whole read of the stash (REG-2861: only such a frame counts an item gone), as frame() says
                        "obs({ session: 'z2', holder: 'MAIN', location: 'stash', complete: true, items: [], ground: [] }); window._vaultMovePaint();"
                        "OUT.k = (row(%s) || {}).textContent || '';"
                        % (json.dumps(HEAD), json.dumps(HEAD), json.dumps(HEAD), json.dumps(HEAD), json.dumps(HEAD)))
        self.assertEqual(o["f0"], "", "premise: the row starts unseen: %r" % o)
        self.assertTrue(o["f1"] and "c3r2" in o["f1"], "the first sighting did not fill FROM: %r" % o)
        self.assertEqual(o["rows"], 1, "a second row appeared: %r" % o)
        self.assertIn("gone 1/5", o["k"], "the drain cannot count a row that never got its cell: %r" % o)


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class CompactSearchRow(unittest.TestCase):
    """Elad 2026-10-20: ADD AN ITEM and FIND ON A MULE sit in one compact row."""

    def test_both_bars_share_one_compact_row_at_desktop_width(self):
        world()
        b = board()
        b.t.send("Emulation.setDeviceMetricsOverride", width=1440, height=900, deviceScaleFactor=1, mobile=False)
        try:
            o = b.run("window.switchTab('vault'); await new Promise(function(r){ setTimeout(r, 300); });"
                      "var a = document.querySelector('.vault-planner-find').getBoundingClientRect();"
                      "var f = document.querySelector('.vault-find-mule').getBoundingClientRect();"
                      "OUT.a = [a.top, a.height, a.width]; OUT.f = [f.top, f.height, f.width];"
                      "OUT.same = document.querySelector('.vault-planner-find').closest('.vault-find-row') === document.querySelector('.vault-find-mule').closest('.vault-find-row');")
        finally:
            b.t.send("Emulation.clearDeviceMetricsOverride")
        self.assertTrue(o["same"])
        self.assertLess(abs(o["a"][0] - o["f"][0]), 3, "the two bars are stacked, not one row: %r" % o)
        self.assertLessEqual(max(o["a"][1], o["f"][1]), 44, "the row is not compact: %r" % o)
        self.assertGreater(min(o["a"][2], o["f"][2]), 280, "a bar collapsed: %r" % o)


RED_PROOF = [
    {"why": "An unseen THROW OUT row never takes its first sighting, so it can never drain.",
     "file": "bible.html",
     "find": "        up.from = _vaultMovePlace(r.sight.holder, r.sight.location, r.sight.cell); /* L1 throw row takes its first sighting */\n",
     "replace": "",
     "matches": 1},
    {"why": "A junk route goes back to the dock instead of a THROW OUT row.",
     "file": "bible.html",
     "find": "? _vaultThrowTask(r, stored) : null;\n",
     "replace": "? null : null;\n",
     "matches": 1},
    {"why": "The row loses its plain reason and prints the wordy DEFAULT advice.",
     "file": "bible.html",
     # REG-2962 (v3854 fan-in BLIND, measured 2026-11-03): since v3849 no set is "never ruled", so the reason this row
     # carries ("low set piece") comes through the DEFAULT-strip line - that is the door, not the never-ruled one
     "find": "    var first = w.replace(/^by DEFAULT( only)?\\s*[—-]\\s*/i, '').split(' — ')[0].trim();\n",
     "replace": "    var first = w.trim();\n",
     "matches": 1},
    {"why": "The dock keeps a junk-routed item as a chip.",
     "file": "bible.html",
     "find": "if (_sgD && _sgD.id === '__throwout') return false; } catch (eSgD) {}",
     "replace": "if (false) return false; } catch (eSgD) {}",
     "matches": 1},
    {"why": "Keep stays a THROW OUT row.",
     "file": "bible.html",
     "find": "if (sg.id === '__throwout' && typeof window._vaultKeptByHim === 'function' && window._vaultKeptByHim(name)) {",
     "replace": "if (sg.id === '__throwout' && typeof window._vaultKeptByHim === 'function' && false) {",
     "matches": 1},
    {"why": "A hand-added unruled set piece is not routed to SETS-REST (his ruling: kept and routed). Breaks the L1 RETURN: breaking only its condition is caught by v3778's every-hand-add-is-filed fallback, which left the old proof BLIND.",
     "file": "bible.html",
     "find": "        return { loc: 'filed', mule: 'sets-rest' }; /* L1 he typed a set piece: kept, not thrown out */",
     "replace": "        return { loc: 'loose', mule: null }; /* L1 he typed a set piece: kept, not thrown out */",
     "matches": 1},
    {"why": "A frame that never showed the container counts a session.",
     "file": "bible.html",
     "find": "      } else if (shows(t.from)) {\n",
     "replace": "      } else if (t.from && t.from.cell != null) {\n",
     "matches": 1},
    {"why": "A re-sighting no longer resets the count.",
     "file": "bible.html",
     "find": "        if (here(name, t.from.cell)) { if (t.gone || t.left) { next = _vaultMoveTask(t); delete next.gone; delete next.left; } }\n",
     "replace": "        if (here(name, t.from.cell)) { }\n",
     "matches": 1},
    {"why": "The row closes after one missing frame instead of five sessions.",
     "file": "bible.html",
     "find": "  var VAULT_GONE_SESSIONS = 5;\n",
     "replace": "  var VAULT_GONE_SESSIONS = 1;\n",
     "matches": 1},
    {"why": "The same session counts twice.",
     "file": "bible.html",
     "find": "var g = (next.gone || []).slice(); if (g.indexOf(sid) < 0) g.push(sid); next.gone = g;",
     "replace": "var g = (next.gone || []).slice(); g.push(sid + g.length); next.gone = g;",
     "matches": 1},
    {"why": "A ground label closes a throw-out before the item left its cell.",
     "file": "bible.html",
     "find": "if (cur.kind === 'throw' && cur.status !== 'closed' && cur.left && groundLeft[name] > 0) {",
     "replace": "if (cur.kind === 'throw' && cur.status !== 'closed' && groundLeft[name] > 0) {",
     "matches": 1},
    {"why": "The ground close matches by name only: one dropped copy closes every copy's THROW OUT row.",
     "file": "bible.html",
     "find": "        groundLeft[name] -= 1; /* L1 one ground label closes one copy */\n",
     "replace": "",
     "matches": 1},
    {"why": "A move seen at its target no longer closes at once.",
     "file": "bible.html",
     "find": "      if (t.kind !== 'throw' && shows(t.to) && here(name, t.to.cell)) {\n",
     "replace": "      if (false) {\n",
     "matches": 1},
    {"why": "The row hides its drain progress.",
     "file": "bible.html",
     "find": "    return n ? ('gone ' + n + '/' + VAULT_GONE_SESSIONS) : '';\n",
     "replace": "    return '';\n",
     "matches": 1},
    {"why": "An item with a MOVE TASKS row is drawn again as a dock chip.",
     "file": "bible.html",
     "find": "    unsorted = _dockShown.filter(_noRow); /* L1 no duplicate chips */\n",
     "replace": "    unsorted = _dockShown.concat(Object.keys(_rowNm)); /* L1 no duplicate chips */\n",
     "matches": 1},
    {"why": "The organizer repeats every item that already has a move row.",
     "file": "bible.html",
     "find": "            window.vaultOrganizePaint(unsorted.filter(_noRow),",
     "replace": "            window.vaultOrganizePaint(unsorted,",
     "matches": 1},
    {"why": "Worn gear loses its Equipped (locked) line.",
     "file": "bible.html",
     "find": "      if (r.locked === true || (r.sight && _vaultMoveWorn(r.sight))) { seen[r.name] = 1; out.push(r.name); }\n",
     "replace": "",
     "matches": 1},
    {"why": "LOCKED chips go back into the MOVE TASKS head.",
     "file": "bible.html",
     "find": "    var locks = (built.locks || []).filter(function(l){ return l.say !== 'LOCKED'; }).map(function(l){",
     "replace": "    var locks = (built.locks || []).map(function(l){",
     "matches": 1},
    {"why": "ADD AN ITEM and FIND ON A MULE stack again on two rows.",
     "file": "bible.html",
     "find": "#mule-vault-card .vault-deck{display:grid;grid-template-columns:1fr 1fr;gap:var(--vsp-4);align-items:stretch;margin:0 0 var(--vsp-4)}",
     "replace": "#mule-vault-card .vault-deck{display:block;grid-template-columns:1fr;gap:var(--vsp-4);align-items:stretch;margin:0 0 var(--vsp-4)}",
     "matches": 1},
    {"why": "The search row goes back to the tall bars.",
     "file": "bible.html",
     "find": "#mule-vault-card .vault-tool > .vault-find{margin:0;width:100%;max-width:none}",
     "replace": "#mule-vault-card .vault-tool > .vault-find{margin:0;width:100%;max-width:none;min-height:80px;padding:28px 12px}",
     "matches": 1},
    {"why": "Keep/Junk buttons leave the THROW OUT row.",
     "file": "bible.html",
     "find": "        + ((thr && !fin && !t.junk) ? '<button type=\"button\" class=\"vault-btn vmv-keep\"",
     "replace": "        + ((false) ? '<button type=\"button\" class=\"vault-btn vmv-keep\"",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
