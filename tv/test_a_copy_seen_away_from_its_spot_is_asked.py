# -*- coding: utf-8 -*-
"""REG-3066, REG-3067 (his model 2026-10-28 18:56 / 19:08, #202) - A COPY SEEN AWAY FROM ITS SPOT IS ASKED ABOUT, AND ONE
SESSION IN TWO PLACES IS A QUESTION.

His model: the console tells him where each copy goes and locks it there; "a copy seen off its locked spot is a deviation
(doubt -> task) unless a move task explains it", and his done rule says a same-session conflict is a question. Measured on
the whole page in node before:
  * REG-3066 - a read somewhere other than a copy's FROM or TO set its task 'moved-elsewhere' and dropped WHERE it was seen:
    the row said moved-elsewhere and nothing could ask "did you move it there?", nor take an answer;
  * REG-3067 - a read at the target and a read somewhere else from the SAME session: the newer read won (a guess inside one
    session) - it reopened a half-way task or a verified one.
Now the task keeps the sighting away (elsewhere) and every sighting he sets aside; its row says "moved?" and the opened row
asks "Seen at <place> on <date> - did you move it there?". Yes: his hand moves the spot there through REG-2787's one door
(_vaultMoveRetargetCell) and the task is his tick at that spot (Untick takes it back); a place that is no locker is refused.
No: the task stays open and that sighting is set aside, recorded, never deleted. One session in two places keeps both
sightings as a question ("which place?") that verifies, reopens and moves nothing until he answers or a read from another
session settles it. A shadow is read only: both doors refuse there and write nothing. Driven on the whole page in node.
RED_PROOF below.
"""
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

PRELUDE = ("Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });\n"
           "localStorage.setItem('d2r_ownerClaim', '*');\n")
BODY = r"""
(function(){
var W = window, OPEN = Date.parse('2026-10-28T10:00:00.000Z'), H1 = 3600e3;
var FROM = { holder: 'MAIN', location: 'stash', cell: 'stash:c3r1' }, TO = { holder: 'UNI-SMALL', location: 'stash', cell: 'stash:c0r0' };
var AWAY = { holder: 'UNI-ARMOR', location: 'stash', cell: 'stash:c5r5' };
function read(p, s, h){ return { holder: p.holder, location: p.location, cell: p.cell, frame: 'f' + s + h, at: new Date(OPEN + h * H1).toISOString(),
                                 sessions: [{ id: s, frame: 'f' + s + h }] }; }
function task(extra){ var t = { name: 'Nagelring', status: 'to-move', manual: false, from: FROM, to: TO, evidence: [], opened: OPEN };
  for (var k in (extra || {})) t[k] = extra[k]; return W._vaultMoveTask(t); }
function st(t){ return { status: t.status, seen: (t.seen || []).map(function(x){ return x.s; }),
                         away: t.elsewhere ? [t.elsewhere.place.cell, t.elsewhere.s] : null,
                         conflict: t.conflict ? [t.conflict.target.s, t.conflict.elsewhere.place.cell] : null }; }
var w = W._vaultMoveWitness;
/* A - REG-3066: a read away keeps where; a read back at FROM clears it */
var a1 = w(task(), read(AWAY, 'S1', 1));
OUT.away = st(a1);
OUT.back = st(w(a1, read(FROM, 'S2', 2)));
OUT.roundTrip = st(W._vaultMoveTask(JSON.parse(JSON.stringify(a1))));
/* B - REG-3067: one session at the target, then the same session away */
var b1 = w(task(), read(TO, 'S1', 1));
OUT.half = st(b1);
var b2 = w(b1, read(AWAY, 'S1', 2));
OUT.conflict = st(b2);
OUT.settled = st(w(b2, read(TO, 'S3', 3)));                 /* another session settles it, and closes it */
var c1 = w(task(), read(AWAY, 'S4', 1));
OUT.reverse = st(w(c1, read(TO, 'S4', 2)));                 /* away first, then the same session at the target */
OUT.otherSession = st(w(b1, read(AWAY, 'S5', 2)));          /* another session away: the rule as before (reopens) */
/* UNKNOWN until he answers: a verified copy one of whose sessions also saw it away is neither in place nor moved */
var v2 = w(w(task(), read(TO, 'S1', 1)), read(TO, 'S2', 2));
var vc = w(v2, read(AWAY, 'S2', 3));
OUT.verifiedConflict = st(vc);
OUT.ipAsked = W._vaultInPlace({ tasks: [{ name: 'Nagelring', copyIx: 0, task: vc }, { name: 'Nagelring', copyIx: 1, task: v2 }] });
/* C - the doors, on a saved task of a real record */
W.vaultHandAdd('Nagelring', new Date().toISOString(), {}); H.flush(60, 3);
try { W.renderVault(); } catch (e) {} H.flush(60, 3);
function saved(){ var raw = null; try { raw = JSON.parse(W.LSR.getItem('d2r_vaultRecords') || 'null'); } catch (e) {}
  var r = ((raw && raw.records) || []).filter(function(x){ return x.name === 'Nagelring' && (x.copyIx | 0) === 0; })[0];
  return (r && r.move) ? W._vaultMoveTask(r.move) : null; }
var base = saved();
OUT.havePremise = !!(base && base.to && base.to.cell);
function seed(t){ W._vaultMoveCommit([{ name: 'Nagelring', copyIx: 0, task: t }]); H.flush(60, 3); }
var to0 = base ? base.to : TO;
function savedTask(extra){ var t = { name: 'Nagelring', status: 'to-move', manual: false, from: FROM, to: to0, evidence: [], opened: OPEN };
  for (var k in (extra || {})) t[k] = extra[k]; return W._vaultMoveTask(t); }
/* yes */
seed(w(savedTask(), read(AWAY, 'S1', 1)));
var html = W._vaultTaskExpandHtml('Nagelring', 0);
OUT.asks = /class="vtx-ask" data-ask="moved"/.test(html) && /did you move it there\?/.test(html) && /window\.vaultMovedAnswer\('Nagelring',0,true\)/.test(html);
OUT.rowChip = /data-ask="moved"/.test(W._vaultMoveHtml({ tasks: [], locks: [], groups: [{ label: 'X', stash: 'S', rows: [{ name: 'Nagelring', copyIx: 0, task: saved(), witnesses: 1 }] }] }));
W._tvdShadow = true;
OUT.shadow = W.vaultMovedAnswer('Nagelring', 0, true);
OUT.shadowLeft = st(saved());
W._tvdShadow = false;
OUT.yes = W.vaultMovedAnswer('Nagelring', 0, true); H.flush(60, 3);
var y = saved();
OUT.yesTask = y ? { status: y.status, to: [y.to.id, y.to.cell], from: y.from.cell, why: y.retarget && y.retarget.why, away: !!y.elsewhere } : null;
OUT.untick = (W._vaultTaskUntick('Nagelring', 0) || {}).ok; H.flush(60, 3);
OUT.afterUntick = saved() ? saved().status : null;
/* no */
seed(w(savedTask(), read(AWAY, 'S6', 4)));
OUT.no = (W.vaultMovedAnswer('Nagelring', 0, false) || {}).ok; H.flush(60, 3);
var n0 = saved();
OUT.noTask = n0 ? { status: n0.status, away: !!n0.elsewhere, aside: (n0.setAside || []).map(function(x){ return [x.place.cell, x.s, x.said]; }), to: n0.to.cell } : null;
/* a place that is not a locker is refused */
seed(w(savedTask(), read({ holder: 'SOMEONE', location: 'stash', cell: 'stash:c1r1' }, 'S7', 5)));
OUT.notLocker = W.vaultMovedAnswer('Nagelring', 0, true);
/* one session in two places, answered */
seed(w(w(savedTask(), read(to0, 'S8', 6)), read(AWAY, 'S8', 7)));
var _ch = W._vaultTaskExpandHtml('Nagelring', 0);
OUT.cHtml = /data-ask="conflict"/.test(_ch) && /Seen at its target and at [^<]* in the same session[^<]* - which is it\?/.test(_ch);
OUT.cTarget = (W.vaultConflictAnswer('Nagelring', 0, 'target') || {}).ok; H.flush(60, 3);
var ct = saved();
OUT.cTargetTask = ct ? { status: ct.status, seen: (ct.seen || []).map(function(x){ return x.s; }), conflict: !!ct.conflict, aside: (ct.setAside || []).map(function(x){ return x.said; }) } : null;
seed(w(w(savedTask(), read(to0, 'S9', 8)), read(AWAY, 'S9', 9)));
OUT.cElse = (W.vaultConflictAnswer('Nagelring', 0, 'elsewhere') || {}).ok; H.flush(60, 3);
var ce = saved();
OUT.cElseTask = ce ? { status: ce.status, seen: (ce.seen || []).length, away: ce.elsewhere ? ce.elsewhere.place.cell : null, conflict: !!ce.conflict } : null;
/* the same session away first, then at the target: 'at its target' counts that read there */
seed(w(w(savedTask(), read(AWAY, 'S10', 10)), read(to0, 'S10', 11)));
OUT.rTarget = (W.vaultConflictAnswer('Nagelring', 0, 'target') || {}).ok; H.flush(60, 3);
var rt = saved();
OUT.rTargetTask = rt ? { status: rt.status, seen: (rt.seen || []).map(function(x){ return x.s; }), away: !!rt.elsewhere, conflict: !!rt.conflict } : null;
OUT.errors = H.errors.slice(0, 5);
})();
"""


class ACopySeenAwayFromItsSpotIsAsked(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertEqual(self.o["errors"], [])
        self.assertTrue(self.o["havePremise"], "PREMISE: the hand add has no saved move task")

    def test_a_read_away_keeps_where_it_was_seen(self):
        self.assertEqual(self.o["away"], {"status": "moved-elsewhere", "seen": [], "away": ["stash:c5r5", "S1"], "conflict": None}, self.o["away"])
        self.assertEqual(self.o["roundTrip"], self.o["away"], "the saved task drops where it was seen: %r" % self.o["roundTrip"])
        self.assertEqual(self.o["back"]["away"], None, "a read back at its FROM keeps the old question: %r" % self.o["back"])

    def test_one_session_in_two_places_is_a_question_that_moves_nothing(self):
        self.assertEqual(self.o["half"]["seen"], ["S1"], "PREMISE: %r" % self.o["half"])
        c = self.o["conflict"]
        self.assertEqual((c["status"], c["seen"], c["conflict"]), ("to-move", ["S1"], ["S1", "stash:c5r5"]), c)
        r = self.o["reverse"]
        self.assertEqual((r["status"], r["conflict"]), ("moved-elsewhere", ["S4", "stash:c5r5"]), r)

    def test_until_he_answers_it_is_neither_in_place_nor_moved(self):
        v = self.o["verifiedConflict"]
        self.assertEqual((v["status"], v["conflict"]), ("to-move", ["S2", "stash:c5r5"]), "a verified copy seen away by its own session stayed verified: %r" % v)
        ip = self.o["ipAsked"]
        self.assertEqual((ip["n"], ip["m"], ip["asked"]), (1, 2, 1), "a question was counted in place: %r" % ip)
        self.assertIn("UNKNOWN until you answer", ip["say"], ip)

    def test_another_session_settles_it_and_the_rule_as_before_holds(self):
        s = self.o["settled"]
        self.assertEqual((s["status"], s["conflict"]), ("verified", None), s)
        o = self.o["otherSession"]
        self.assertEqual((o["status"], o["seen"], o["away"]), ("moved-elsewhere", [], ["stash:c5r5", "S5"]), o)

    def test_the_row_and_the_opened_row_ask(self):
        self.assertTrue(self.o["rowChip"], "the row says nothing of the sighting away")
        self.assertTrue(self.o["asks"], "the opened row does not ask 'did you move it there?'")
        self.assertTrue(self.o["cHtml"], "the opened row does not ask which place")

    def test_a_shadow_is_read_only(self):
        self.assertEqual((self.o["shadow"] or {}).get("refused"), "shadow", self.o["shadow"])
        self.assertEqual(self.o["shadowLeft"]["status"], "moved-elsewhere", "a shadow's answer wrote: %r" % self.o["shadowLeft"])

    def test_yes_moves_the_spot_through_his_hand_and_can_be_untaken(self):
        self.assertTrue((self.o["yes"] or {}).get("ok"), self.o["yes"])
        y = self.o["yesTask"]
        self.assertEqual((y["status"], y["to"], y["from"], y["away"]), ("moved-manual", ["uni-armor", "stash:c5r5"], "stash:c5r5", False), y)
        self.assertEqual(y["why"], "you moved it here", y)
        self.assertEqual((self.o["untick"], self.o["afterUntick"]), (True, "to-move"), self.o)

    def test_no_keeps_the_task_and_sets_the_sighting_aside_on_record(self):
        self.assertTrue(self.o["no"])
        n = self.o["noTask"]
        self.assertEqual((n["status"], n["away"], n["aside"]), ("to-move", False, [["stash:c5r5", "S6", "no"]]), n)

    def test_a_place_that_is_not_a_locker_is_refused(self):
        r = self.o["notLocker"]
        self.assertFalse(r.get("ok"), r)
        self.assertIn("not one of your lockers", r.get("why", ""), r)

    def test_his_answer_to_which_place(self):
        self.assertTrue(self.o["cTarget"])
        t = self.o["cTargetTask"]
        self.assertEqual((t["seen"], t["conflict"], t["aside"]), (["S8"], False, ["target"]), t)
        self.assertTrue(self.o["cElse"])
        e = self.o["cElseTask"]
        self.assertEqual((e["status"], e["seen"], e["away"], e["conflict"]), ("moved-elsewhere", 0, "stash:c5r5", False), e)
        self.assertTrue(self.o["rTarget"])
        r = self.o["rTargetTask"]
        self.assertEqual((r["status"], r["seen"], r["away"], r["conflict"]), ("to-move", ["S10"], False, False),
                         "'at its target' did not count that session's read there: %r" % r)


RED_PROOF = [
    {"why": "REG-3066 - a read away drops where it was seen",
     "file": "bible.html",
     "find": "    t.elsewhere = _seenHere;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3066 - the saved task drops the sighting away",
     "file": "bible.html",
     "find": "    if (_ew) out.elsewhere = _ew;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3066 - Yes moves nothing: the spot stays where it was",
     "file": "bible.html",
     "find": "      var nt = _vaultMoveRetargetCell(nm, k, mm.id, ew.place.cell, 'you moved it here');   /* REG-2787 his hand moves the spot */\n",
     "replace": "      var nt = t;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3066 - No deletes the sighting instead of setting it aside",
     "file": "bible.html",
     "find": "                                                   setAside: (t.setAside || []).concat([Object.assign({}, ew, { said: 'no', saidAt: Date.now() })]) }));\n",
     "replace": "                                                   setAside: t.setAside }));\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3066 - a shadow's answer writes",
     "file": "bible.html",
     "find": "    if (window._tvdShadow) return { ok: false, refused: 'shadow', why: 'a shadow is read only - answer on your own board' };\n    var a = _vaultMoveAsked(nm, k), t = a.t;\n    if (a.why) return { ok: false, why: a.why };\n    if (!t || !t.elsewhere)",
     "replace": "    var a = _vaultMoveAsked(nm, k), t = a.t;\n    if (a.why) return { ok: false, why: a.why };\n    if (!t || !t.elsewhere)",
     "matches": 1, "needs": "node"},
    {"why": "REG-3066 - the opened row never asks",
     "file": "bible.html",
     "find": "      + _vtxAsk(m)   /* REG-3066 / REG-3067 the question this row asks, and its answers */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3067 - one session away after the target: the newer read wins",
     "file": "bible.html",
     "find": "    if (t.status !== 'moved-manual' && !atTo && _rs.length && (t.seen || []).some(function(x){ return _rs.indexOf(x.s) >= 0; })) {\n",
     "replace": "    if (false) {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3067 - a verified copy with a question stays in place",
     "file": "bible.html",
     "find": "      if (t.status === 'verified') t.status = 'to-move';\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3067 - the readout counts a question in place",
     "file": "bible.html",
     "find": "      if (t.conflict) { asked++; return; }   /* REG-3067 one session in two places: UNKNOWN until he answers */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3067 - one session at the target after away: the newer read wins",
     "file": "bible.html",
     "find": "    if (t.status !== 'moved-manual' && atTo && _rs.length && t.elsewhere && t.elsewhere.s && _rs.indexOf(t.elsewhere.s) >= 0) {\n",
     "replace": "    if (false) {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3067 - a read from another session never settles the question",
     "file": "bible.html",
     "find": "    if (t.conflict && _rs.length && _rs.indexOf(t.conflict.target.s) < 0) delete t.conflict;   /* another session settles it */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3067 - 'at its target' does not count that session's read there",
     "file": "bible.html",
     "find": "      var ok2 = _vaultMoveSeenAtTo(done, [{ s: cf.target.s, at: cf.target.at, frame: cf.target.frame }]);\n",
     "replace": "      var ok2 = false;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
