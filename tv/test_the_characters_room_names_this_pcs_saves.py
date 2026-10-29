# -*- coding: utf-8 -*-
"""#251 (REG-2927) - THE CHARACTERS ROOM TAKES THIS PC'S SAVE NAMES: EXACT SPELLING, CLASS AND LEVEL FROM THE REELS OR
UNKNOWN.

The console answers GET /api/saves (REG-2926) with the names this PC's save folder holds. The board asks it beside
/api/chars_learned, wherever the room, the builder or the vault asks, and _cbTemplates merges it:
  * a reel name that folds to a save name takes the save's spelling and keeps the reels' class, level and tier (its key
    keeps its fold, so a build made from it still finds it);
  * a name only the saves know joins the in-game list with class and level UNKNOWN - never a guess - and the room's card
    says it is named by this PC's save folder;
  * a row counts only with its id count (the saves' own shape), a failed answer never replaces a good one, and a shadow
    never takes them (their saves are on their PC).
Driven on the whole page in node (tv/vault_page_node), the real functions, a fetch that answers in the same turn.
RED_PROOF below.
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

FAKE = r"""
var FETCHED = [], REPAINTS = 0;
var LEARNED = { ok: true, chars: [ { name: 'KONYOLOCK', cls: 'Warlock', level: 88, visits: 5, tier: 'WATCHED', looks: 5, trials: 5 } ] };
var SAVES = { ok: true, state: 'folder', chars: [ { name: 'Konyolock', ids: 1 }, { name: 'Hammer-Din', ids: 2 } ] };
function _syncThen(v){ return { then: function(f){ var r; try { r = f(v); } catch (e) { r = undefined; } return _syncThen(r); },
                                catch: function(){ return this; } }; }
window.fetch = function(url){ FETCHED.push(String(url));
  return _syncThen({ ok: true, json: function(){ return String(url).indexOf('/api/saves') >= 0 ? SAVES : LEARNED; } }); };
function T(){ return window._cbTemplates().map(function(t){ return { key: t.key, name: t.name, cls: t.cls, level: t.level, tier: t.tier, save: !!t.save }; }); }
"""


def _run(body):
    return VPN.run(FAKE + body, timeout=600)


@unittest.skipIf(VPN.NODE is None, "node is absent - this law is UNMEASURED here, not passing")
class TheCharactersRoomNamesThisPcsSaves(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = _run(r"""
        window._cbLearnedFetch(function(){ REPAINTS++; });
        OUT.fetched = FETCHED.slice(); OUT.repaints = REPAINTS;
        OUT.t = T();
        var S = window._cbSections({}, []);
        OUT.s = { state: S.state, savesOnly: S.savesOnly, ingame: S.ingame.map(function(g){ return g.t.name; }),
                  mules: S.mules.map(function(g){ return g.t.name; }) };
        window.renderCharsTab();
        var el = document.getElementById('chars-list');
        OUT.room = el ? String(el.innerHTML || '') : null;
        """)

    def _t(self, name):
        hit = [t for t in self.o["t"] if t["name"] == name]
        self.assertEqual(len(hit), 1, "PREMISE: %r is not one template: %r" % (name, self.o["t"]))
        return hit[0]

    def test_the_board_asks_its_console_for_the_save_names(self):
        self.assertIn("/api/chars_learned", self.o["fetched"])
        self.assertIn("/api/saves", self.o["fetched"], "the builder's ask never asked the console for this PC's save names")
        self.assertEqual(self.o["repaints"], 2, "the save names did not repaint on their own answer")

    def test_a_reel_name_takes_the_saves_spelling_and_keeps_what_the_reels_saw(self):
        t = self._t("Konyolock")
        self.assertEqual((t["key"], t["cls"], t["level"], t["tier"]), ("seen:konyolock", "Warlock", 88, "WATCHED"))
        self.assertNotIn("KONYOLOCK", [x["name"] for x in self.o["t"]], "the reels' spelling stood beside the save's")

    def test_a_name_only_the_saves_know_joins_with_class_and_level_unknown(self):
        t = self._t("Hammer-Din")
        self.assertEqual((t["key"], t["cls"], t["level"], t["save"]), ("seen:hammerdin", None, None, True))
        self.assertEqual(self.o["s"]["ingame"], ["Konyolock", "Hammer-Din"])
        self.assertEqual(self.o["s"]["mules"], [])
        self.assertEqual(self.o["s"]["savesOnly"], 1)

    def test_the_room_says_where_a_save_only_name_comes_from(self):
        room = self.o["room"] or ""
        self.assertIn("Hammer-Din", room, "PREMISE: the room did not paint: %r" % room[:300])
        self.assertIn("class UNKNOWN", room)
        self.assertIn('data-tier="SAVE"', room, "a save-only card wears a tier it never earned")

    def test_only_the_saves_own_shape_counts_and_a_failure_never_replaces_an_answer(self):
        o = _run(r"""
        window._cbSavesTakeForLaw({ ok: true, chars: [ { name: 'Ghost', cls: 'Paladin', level: 9 } ] });   // no id count
        OUT.shapeless = T().map(function(t){ return t.name; });
        window._cbSavesTakeForLaw({ ok: true, state: 'folder', chars: [ { name: 'Mule-A', ids: 1 } ] });
        window._cbSavesTakeForLaw({ ok: false, chars: null, why: 'down' });
        OUT.after = T().map(function(t){ return t.name; });
        """)
        self.assertEqual(o["shapeless"], [], "a row with no id count was taken as a save name")
        self.assertEqual(o["after"], ["Mule-A"], "a failed answer replaced the save names it had")

    def test_a_shadow_never_takes_this_pcs_saves(self):
        o = _run(r"""
        window._cbSavesTakeForLaw(SAVES);
        document.documentElement.classList.add('tvd-shadow');
        OUT.t = T().map(function(t){ return t.name; });
        """)
        self.assertEqual(o["t"], [], "a shadow drew this PC's save names as theirs")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "#251 (REG-2927) - the builder's ask never asks /api/saves, so the room never learns the save names",
     "file": "bible.html",
     "find": "      _cbSavesAsk().then(function(){ if (then) then(); });   /* #251 (REG-2927) - the save names repaint on their own answer */\n    } catch (e) { _cbLearnedAsking",
     "replace": "    } catch (e) { _cbLearnedAsking",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-2927) - a reel name that folds to a save name keeps the reels' spelling",
     "file": "bible.html",
     "find": "        if (hit){ hit.name = S.name; hit.save = true; return; }\n",
     "replace": "        if (hit){ hit.save = true; return; }\n",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-2927) - a name only the saves know is not drawn at all",
     "file": "bible.html",
     "find": "        out.push({ key: 'seen:' + _cbFold(S.name), name: S.name, cls: null, level: null, words: '', strengths: [], weaknesses: [],\n",
     "replace": "        if (0) out.push({ key: 'seen:' + _cbFold(S.name), name: S.name, cls: null, level: null, words: '', strengths: [], weaknesses: [],\n",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-2927) - any answer's rows count as save names, so a learned-shaped row with a guessed class is taken",
     "file": "bible.html",
     "find": "&& r.name && typeof r.ids === 'number'; });",
     "replace": "&& r.name; });",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-2927) - a shadow takes this PC's save names as theirs",
     "file": "bible.html",
     "find": "  function _cbSaveRows(){\n    if (document.documentElement.classList.contains('tvd-shadow')) return [];\n",
     "replace": "  function _cbSaveRows(){\n",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-2927) - a save-only card wears the reels' tier line instead of saying where its name comes from",
     "file": "bible.html",
     "find": "    if (t && t.save && !t.seen) return '<div class=\"chx-proof\" data-tier=\"SAVE\">",
     "replace": "    if (0) return '<div class=\"chx-proof\" data-tier=\"SAVE\">",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-2927) - a failed saves answer replaces the names it had",
     "file": "bible.html",
     "find": "    if (d.ok === true || !(_cbSaves && _cbSaves.ok === true)) _cbSaves = d;\n",
     "replace": "    _cbSaves = d;\n",
     "matches": 1, "needs": "node"},
]
