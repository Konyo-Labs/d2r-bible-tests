# -*- coding: utf-8 -*-
"""REG-2877 (#83, his rulings: "Design it now, wire it later"; a traded-out copy is proven gone, so it goes to the Vault
log with an undo, never a question) - THE TRADE SLOT ON A COPY RECORD, AND ONE DOOR FOR TRADE EVENTS.

MEASURED before (whole page, node): a copy record (d2r_vaultRecords) had no place to say it is listed or traded, so a
listing lived nowhere a copy could carry. Nothing could take ONE copy out of the count through the removal journal: the
removal door takes a whole name, and the copy door (vaultCopyAdjust) drops the LAST copy's record and journals nothing.
So trading copy 2 of 3 would leave copy 2's MOVE task standing and delete copy 3's, with no undo.

Now a record carries trade: null | {state: 'listed' | 'traded-out', at, post?}. A rebuild of the records and a commit of a
task both keep it. window._vaultTradeEvent takes listed / unlisted / trade-out / trade-in for a copy:
  - listed and unlisted set and clear the slot; a listed copy still counts;
  - trade-out of one of several copies takes THAT copy's record out. Its move and its slot ride in a removal-journal batch
    on the trade-out lane, the copies after it close up, and the count drops one, so no task for it is left asking where
    it is. vaultRestoreLast puts it back at its copyIx with its own cell. The last copy leaves through vaultRemove on the
    trade-out lane; the removal door leaves its record in the store (measured), so the undo brings back its own cell;
  - trade-in is one more copy through the owned door, with its own MOVE task.
Whole page in node, never a browser and never d2jsp. RED_PROOF below.
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

CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');\n"
TOPIC = "https://forums.d2jsp.org/topic.php?t=9001&f=268"
LIB = r"""
var W = window, GULL = 'Gull (dagger)', SABRE = 'Lightsabre';
function rows(n){ return (JSON.parse(W.LSR.getItem('d2r_vaultRecords') || '{}').records || []).filter(function(r){ return r && r.name === n; })
  .sort(function(a, b){ return (a.copyIx || 0) - (b.copyIx || 0); }).map(function(r){ return { ci: r.copyIx || 0, cell: r.move && r.move.to ? r.move.to.cell : null, trade: r.trade || null }; }); }
function paint(){ W.renderVault(); H.flush(60, 3); }
function lastBatch(){ var l = W.vaultRemovalLog() || []; return l[l.length - 1] || null; }
function taskRows(n){ var h = (document.getElementById('vault-move-list') || {}).innerHTML || '';
  return (h.match(/<li class="vmv-row[^>]*>/g) || []).filter(function(x){ return x.indexOf('data-name="' + n + '"') >= 0; }).map(function(x){ return +((x.match(/data-copy="(\d+)"/) || [])[1]); }); }
"""
BODY = LIB + r"""
W._vaultAutoIntakeSet(false);
['Gull', 'Gull', 'Gull'].forEach(function(n){ W.vaultHandAdd(n); }); paint();
OUT.start = rows(GULL);
OUT.list = W._vaultTradeEvent({ kind: 'listed', name: GULL, copyIx: 1, at: '2026-10-28T20:00:00Z', post: %(topic)s });
OUT.listed = rows(GULL);
W.vaultHandAdd(SABRE); paint();
OUT.afterRebuild = rows(GULL);
W._vaultMoveMark(GULL, 1); paint();
OUT.afterTick = rows(GULL);
OUT.out = W._vaultTradeEvent({ kind: 'trade-out', name: GULL, at: '2026-10-28T21:00:00Z' });
paint();
OUT.afterOut = { rows: rows(GULL), count: copyCount(GULL), batch: lastBatch(), tasks: taskRows(GULL) };
OUT.undo = W.vaultRestoreLast(); paint();
OUT.afterUndo = { rows: rows(GULL), count: copyCount(GULL) };
// the last copy of a name
W._vaultMoveRetargetCell(SABRE, 0, 'uni-weap', 'stash:c6r5', 'law');
OUT.sabreBefore = rows(SABRE);
OUT.sabreOut = W._vaultTradeEvent({ kind: 'trade-out', name: SABRE });
paint();
OUT.sabreGone = { owned: owned.has(SABRE), batch: lastBatch() };
OUT.sabreUndo = W.vaultRestoreLast(); paint();
OUT.sabreBack = { owned: owned.has(SABRE), rows: rows(SABRE) };
// a copy comes back
OUT.inBefore = copyCount(GULL);
OUT.tin = W._vaultTradeEvent({ kind: 'trade-in', name: GULL }); paint();
OUT.inAfter = { count: copyCount(GULL), rows: rows(GULL) };
// refusals
OUT.bad = W._vaultTradeEvent({ kind: 'sold', name: GULL });
OUT.absent = W._vaultTradeEvent({ kind: 'listed', name: 'The Grandfather' });
""" % {"topic": json.dumps(TOPIC)}


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ATradedCopyLeavesThroughTheVaultLog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=CLAIM, timeout=600)

    def test_a_listing_is_a_slot_on_its_copy_and_survives_a_rebuild_and_a_commit(self):
        o = self.o
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertEqual(len(o["start"]), 3, "PREMISE: %r" % o["start"])
        self.assertTrue(o["list"]["ok"], o["list"])
        want = {"state": "listed", "at": "2026-10-28T20:00:00Z", "post": TOPIC}
        self.assertEqual([r["trade"] for r in o["listed"]], [None, want, None], o["listed"])
        self.assertEqual([r["trade"] for r in o["afterRebuild"]], [None, want, None], "a rebuild of the records dropped the slot")
        self.assertEqual([r["trade"] for r in o["afterTick"]], [None, want, None], "a commit of a task dropped the slot")

    def test_trading_one_copy_out_takes_that_copy_and_the_rest_close_up(self):
        o, s = self.o, self.o["start"]
        a = o["afterOut"]
        self.assertTrue(o["out"]["ok"], o["out"])
        self.assertEqual(o["out"]["copyIx"], 1, "the listed copy is not the one traded out: %r" % o["out"])
        self.assertEqual(a["count"], 2, "the count did not drop one: %r" % a)
        self.assertEqual([r["cell"] for r in a["rows"]], [s[0]["cell"], s[2]["cell"]],
                         "the copies after it did not close up (or another copy's task left): %r vs %r" % (a["rows"], s))
        self.assertEqual(sorted(a["tasks"]), [0, 1], "a task is left for a copy that is gone: %r" % a["tasks"])
        b = a["batch"]
        self.assertEqual((b["lane"], b["copyOut"]["name"], b["copyOut"]["copyIx"]), ("trade-out", "Gull (dagger)", 1), b)
        self.assertEqual(b["copyOut"]["row"]["move"]["to"]["cell"], s[1]["cell"], "the batch does not carry the copy's own task")
        self.assertEqual(b["copyOut"]["row"]["trade"]["state"], "traded-out", b["copyOut"]["row"])

    def test_the_undo_puts_the_copy_back_where_it_was(self):
        o, s = self.o, self.o["start"]
        u = o["afterUndo"]
        self.assertEqual(o["undo"]["restored"], 1, o["undo"])
        self.assertEqual(u["count"], 3, u)
        self.assertEqual([r["cell"] for r in u["rows"]], [r["cell"] for r in s], "the undo did not restore each copy's own cell: %r" % u["rows"])
        self.assertEqual([r["trade"] for r in u["rows"]], [None, None, None], "a restored copy still reads traded or listed")

    def test_the_last_copy_leaves_through_the_removal_door_and_comes_back_with_its_cell(self):
        o = self.o
        self.assertEqual(o["sabreBefore"][0]["cell"], "stash:c6r5", "PREMISE: %r" % o["sabreBefore"])
        self.assertTrue(o["sabreOut"]["ok"], o["sabreOut"])
        g = o["sabreGone"]
        self.assertFalse(g["owned"])
        self.assertEqual((g["batch"]["lane"], g["batch"]["names"]), ("trade-out", ["Lightsabre"]), g["batch"])
        self.assertTrue(o["sabreBack"]["owned"])
        self.assertEqual(o["sabreBack"]["rows"][0]["cell"], "stash:c6r5", "the undo lost the last copy's own cell: %r" % o["sabreBack"])

    def test_a_trade_in_is_one_more_copy_with_its_own_task_and_bad_events_are_refused(self):
        o = self.o
        self.assertTrue(o["tin"]["ok"], o["tin"])
        self.assertEqual(o["inAfter"]["count"], o["inBefore"] + 1)
        self.assertTrue(o["inAfter"]["rows"][-1]["cell"], "the copy that came back has no task cell: %r" % o["inAfter"])
        self.assertFalse(o["bad"]["ok"])
        self.assertIn("not a trade event", o["bad"]["why"])
        self.assertFalse(o["absent"]["ok"])
        self.assertIn("not in the vault", o["absent"]["why"])


RED_PROOF = [
    {"why": "REG-2877 - a copy record has no trade slot",
     "file": "bible.html",
     "find": "      row.trade = { state: _tr.state, at: (typeof _tr.at === 'string' && _tr.at) ? _tr.at.slice(0, 40) : null };\n      if (typeof _tr.post === 'string' && _tr.post) row.trade.post = _tr.post.slice(0, 200);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2877 - a rebuild of the records drops the slot",
     "file": "bible.html",
     "find": "          trade: priorTrade[String(r.name) + '\\u0000' + (r.copyIx || 0)] || null, /* REG-2877 trade carry */\n",
     "replace": "          trade: null,\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2877 - a commit of a task drops the slot",
     "file": "bible.html",
     "find": "          move: t, trade: row.trade || null, prov: row.prov,",
     "replace": "          move: t, trade: null, prov: row.prov,",
     "matches": 1, "needs": "node"},
    {"why": "REG-2877 - the copies after a traded one do not close up (its task stays, the last one's goes)",
     "file": "bible.html",
     "find": "      if (r && r.name === nm && (r.copyIx || 0) > k) { var c = {}; for (var x in r) c[x] = r[x]; c.copyIx = (r.copyIx || 0) - 1; return c; }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2877 - a traded-out copy leaves no batch in the removal journal (no undo)",
     "file": "bible.html",
     "find": "               why: why, lane: 'trade-out', keepFiling: true, copyOut: { name: nm, copyIx: k, row: row } });\n",
     "replace": "               why: why, lane: 'trade-out', keepFiling: true });\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2877 - the undo does not put a traded-out copy back",
     "file": "bible.html",
     "find": "    if (last.copyOut && last.copyOut.name && last.copyOut.row) {\n",
     "replace": "    if (false) {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2877 - an event with no copyIx trades out the last copy instead of the listed one",
     "file": "bible.html",
     "find": "    else pick = mine.filter(listedOf)[0] || (kind === 'trade-out' ? mine[mine.length - 1] : null);\n",
     "replace": "    else pick = (kind === 'trade-out' ? mine[mine.length - 1] : mine.filter(listedOf)[0]) || null;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
