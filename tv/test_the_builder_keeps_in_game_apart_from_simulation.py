# -*- coding: utf-8 -*-
"""#103 — THE CHARACTERS HE HAS IN GAME, AND THE BUILDS HE TRIES THINGS WITH, IN TWO SECTIONS.

Konyo, 2026-09-30: "this is specifically for the characters that are known by the console and are legit my character..
so they slowly prove themselves from reels sessions and harden same way as vault.... this is an area to create and test
other builds like simulation style.. so the add character and everything stays as is.. just maybe segregated like with a
section for each so its known that those are the characters ingame we have".

What this law holds, each piece driven through the SHIPPED code (never re-typed here):
  · THE TIER IS THE VAULT'S. tv/char_select.proof counts a character's LOOKS (character-select visits that read it) over
    its TRIALS (visits since it first appeared) and asks vault_evidence.tier - WATCHED under 10, PROVEN at 10, HARDENED
    at 20, and a character the screen stops showing falls back. A visit with no time is UNKNOWN, never a guess, and
    char_select defines no bars of its own (one source).
  · ONE RULE SORTS A BUILD (window._cbSections): made from a learned character (b.from) or carrying its name, folded the
    way the learner folds -> in game, under that character; anything else -> simulation. Level-1 learned characters are
    the mules group. A console that has not answered is UNKNOWN - never "none" - and every build stands in simulation.
  · THE 👤 CHARACTERS ROOM paints two sections, in-game first: a character with builds shows them as its cards, each
    wearing its proof; one with none is a dashed card whose "Plan a build" opens the planner on a draft of it (nothing
    written until he changes it). Simulation is the cards they always were, MAIN first; + New character is untouched.
  · THE PLANNER'S BUILD LIST says the same sections: ⚔ In game (the learned characters, their builds in their place, a
    character with none offered as "not saved yet" with its tier), the mules group, 🧪 Simulation builds + New build.
The room's harness is test_the_characters_tab_is_manual_and_separate's own (imported, not copied), with a console answer
fed through the page's real /api/chars_learned fetch. [[the-unjoined-end]] [[unknown-stays-unknown]] [[copy-drift]]
"""
import ast
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import char_select as CS  # noqa: E402
import test_the_characters_tab_is_manual_and_separate as ROOM  # noqa: E402

NODE = ROOM.NODE

# the console behind the page, as its fetch sees it: answered synchronously so the harness reads the result in one pass
CONSOLE = r"""
var location = { protocol: 'http:', search: '', hash: '', href: 'http://127.0.0.1:17999/', pathname: '/' };
var LEARNED_ANSWER = null, FETCHED = [];
function _syncThen(v){ return { then: function(f){ var r; try { r = f(v); } catch (e) { r = undefined; } return _syncThen(r); },
                                catch: function(){ return this; } }; }
function fetch(url){ FETCHED.push(String(url));
  /* a console that is down REJECTS: the failure reaches a .then(ok, bad) handler as well as a .catch (REG-2683) */
  if (LEARNED_ANSWER === 'FAIL') return { then: function(ok, bad){ if (bad) bad(new Error('down')); return this; }, catch: function(f){ f(new Error('down')); return this; } };
  return _syncThen({ ok: true, json: function(){ return LEARNED_ANSWER; } }); }
"""

ROSTER = r"""
var ROSTER = { ok: true, tierBars: { proven: 10, hardened: 20, wilson: 0.722 }, chars: [
  { name: 'HAMMERDIN', cls: 'Paladin', level: 94, pendingLevel: null, visits: 22, tier: 'HARDENED', looks: 22, trials: 22,
    title: 'Patriarch', lastTs: NOW - 3600000 },
  { name: 'Frostnova', cls: 'Sorceress', level: 71, pendingLevel: 72, visits: 11, tier: 'PROVEN', looks: 11, trials: 11,
    title: null, lastTs: NOW - 7200000 },
  { name: 'Mulebox', cls: 'Sorceress', level: 1, pendingLevel: null, visits: 3, tier: 'WATCHED', looks: 3, trials: 3,
    title: null, lastTs: NOW - 86400000 } ] };
function secHtml(k){ var m = new RegExp('<section class="chx-sec[^"]*" data-sec="' + k + '"[^>]*>([\\s\\S]*?)</section>').exec(ELS['chars-list']._html); return m ? m[1] : null; }
function secIds(k){ var h = secHtml(k) || '', out = [], re = /data-build="([^"]*)"/g, m; while ((m = re.exec(h))) out.push(decode(m[1])); return out; }
function ghosts(k){ var h = secHtml(k) || '', out = [], re = /data-learned="([^"]*)"/g, m; while ((m = re.exec(h))) out.push(decode(m[1])); return out; }
function groups(){
  var sel = /<select class="cb-sel" id="cb-build"[^>]*>([\s\S]*?)<\/select>/.exec(ELS['cb-win']._html); if (!sel) return null;
  var out = [], re = /<optgroup label="([^"]*)">([\s\S]*?)<\/optgroup>/g, m;
  while ((m = re.exec(sel[1]))){
    var opts = [], ore = /<option value="([^"]*)"[^>]*>([^<]*)<\/option>/g, o;
    while ((o = ore.exec(m[2]))) opts.push([decode(o[1]), decode(o[2])]);
    out.push({ label: decode(m[1]), opts: opts });
  }
  return out;
}
"""


def _run(body):
    return ROOM._run(ROSTER + body, raw_patch=CONSOLE)


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheRoomHasTwoSections(unittest.TestCase):

    def test_in_game_holds_the_learned_characters_and_their_builds(self):
        out = _run(r"""
          seed(null); LEARNED_ANSWER = ROSTER; window.renderCharsTab();
          OUT.order = (ELS['chars-list']._html.match(/data-sec="(\w+)"/g) || []);
          OUT.ing = secIds('ingame'); OUT.sim = secIds('sim'); OUT.gIng = ghosts('ingame'); OUT.gSim = ghosts('sim');
          OUT.ham = card('bHAM') ? card('bHAM').html : null;
          OUT.frost = (/<article class="chx-card chx-ghost" data-learned="seen:frostnova">([\s\S]*?)<\/article>/.exec(secHtml('ingame') || '') || [])[1] || null;
          OUT.head = /chx-sec-t" title="([^"]*)"/.exec(secHtml('ingame') || '');   /* v3855 item C: the bars ride the hover */
          OUT.head = OUT.head ? decode(OUT.head[1]) : null;
          OUT.fetched = FETCHED.slice(); OUT.ingHtml = secHtml('ingame');
        """)
        self.assertEqual(out["order"], ['data-sec="sim"', 'data-sec="ingame"'], "the room is not two sections, Your builds first (v3855 item D)")
        self.assertEqual(out["ing"], ["bHAM"], "a build carrying a learned character's name is not under that character")
        self.assertEqual(out["sim"], ["bSORC", "bDRU"], "the simulation section is not every other build, newest first")
        self.assertEqual(out["gIng"], ["seen:frostnova", "seen:mulebox"],
                         "a learned character with no build must stand as its own card, the played ones before the mules")
        self.assertEqual(out["gSim"], [])
        self.assertIn('data-tier="HARDENED"', out["ham"])
        self.assertIn('data-seal="yes" role="img" aria-label="Confirmed · 22 of 22 looks', out["ham"], "the in-game card does not wear its confirmed seal (v3855 item E)")
        # the Grok eye on pixels: "level 90 ... the reels saw level 92 - the page does not say which is the character's level"
        self.assertIn("level 94 in game", out["ham"], "an in-game card must lead with the level the reels confirmed")
        self.assertIn("this build says 92", out["ham"], "the build's own, different level went unsaid")
        self.assertIn('data-sub="mules"', out["ingHtml"], "the level-1 characters are not said to be mules")
        self.assertLess(out["ingHtml"].index('data-sub="mules"'), out["ingHtml"].index('data-learned="seen:mulebox"'))
        self.assertIsNotNone(out["frost"], "Frostnova's card is gone")
        self.assertIn("Not confirmed yet · 11 of 11 looks", out["frost"])
        self.assertIn("72 waits for one more look", out["frost"], "a level only one look saw was shown as his level")
        self.assertIn("Confirmed at 20 looks", out["head"], "the section does not say the vault's bars: %r" % out["head"])
        self.assertIn("/api/chars_learned", out["fetched"], "the room never asked its console what the reels learned")

    def test_a_build_made_from_a_learned_character_is_its_card(self):
        out = _run(r"""
          seed(null);
          var all = JSON.parse(RAW['d2r_charBuilds']);
          all.bFROST = b('Frost plan', 'Sorceress', 70, NOW - 60000, [set1()]); all.bFROST.from = 'seen:frostnova';
          RAW['d2r_charBuilds'] = JSON.stringify(all);
          LEARNED_ANSWER = ROSTER; window.renderCharsTab();
          OUT.ing = secIds('ingame'); OUT.gIng = ghosts('ingame'); OUT.sim = secIds('sim');
        """)
        self.assertEqual(out["ing"], ["bHAM", "bFROST"], "a build made from a learned character left its section")
        self.assertEqual(out["gIng"], ["seen:mulebox"], "a character WITH a build still shows as having none")
        self.assertNotIn("bFROST", out["sim"])

    def test_the_link_decides_before_the_name(self):
        # #114 (REG-1621) - the #231 eye on v3528: a build NAMED like one learned character but MADE from another went to
        # whichever the roster listed first (HAMMERDIN before Frostnova), so the link lost to roster order
        out = _run(r"""
          seed(null);
          var all = JSON.parse(RAW['d2r_charBuilds']);
          all.bLINK = b('HAMMERDIN', 'Sorceress', 70, NOW - 60000, [set1()]); all.bLINK.from = 'seen:frostnova';
          RAW['d2r_charBuilds'] = JSON.stringify(all);
          LEARNED_ANSWER = ROSTER; window.renderCharsTab();
          var S = window._cbSections(JSON.parse(RAW['d2r_charBuilds']));
          OUT.groups = S.ingame.map(function(g){ return [g.t.key, g.ids]; });
        """)
        groups = dict((k, ids) for k, ids in out["groups"])
        self.assertIn("bLINK", groups.get("seen:frostnova") or [],
                      "a build made from Frostnova went to the character its NAME matched first: %r" % groups)
        self.assertNotIn("bLINK", groups.get("seen:hammerdin") or [])

    def test_the_main_leads_its_own_section(self):
        out = _run(r"""
          seed('bDRU'); LEARNED_ANSWER = ROSTER; window.renderCharsTab();
          OUT.sim = secIds('sim'); OUT.ing = secIds('ingame'); OUT.badge = card('bDRU').badge;
        """)
        self.assertEqual(out["sim"], ["bDRU", "bSORC"], "the MAIN does not lead its section")
        self.assertTrue(out["badge"])
        self.assertEqual(out["ing"], ["bHAM"])

    def test_learned_characters_stand_with_no_build_made_by_hand(self):
        """#234 - MEASURED on a served board: with no build saved by hand the room returned "No characters yet" before it
        drew the in-game section, so a PC where he never planned a build (the ALT, Dean's PC, a fresh board) never showed
        the characters its console learned. The empty state is only for nothing learned AND nothing built (the manual
        law keeps that case)."""
        out = _run(r"""
          seed(null); delete RAW['d2r_charBuilds']; LEARNED_ANSWER = ROSTER; window.renderCharsTab();
          var h = ELS['chars-list']._html;
          OUT.secs = (h.match(/data-sec="(\w+)"/g) || []);
          OUT.ghosts = ghosts('ingame');
          OUT.empty = /No characters yet/.test(h);
        """)
        self.assertFalse(out["empty"], "a board with no hand build hid the characters its console learned")
        self.assertEqual(out["secs"], ['data-sec="sim"', 'data-sec="ingame"'])
        self.assertEqual(out["ghosts"], ["seen:hammerdin", "seen:frostnova", "seen:mulebox"],
                         "every learned character stands as its own card when nothing was built by hand")

    def test_an_in_game_card_shows_what_it_wears_and_offers_no_plan(self):
        """#234 step 2 — HIS RULING, 2026-10-01: an in-game card (main or mule) is AI-automated, "i want to see the items
        slowly appearing based on the character they were witnessed in... when i click a mule it shouldnt let me do PLAN
        BUILD". It used to carry "Plan a build"; planning by hand lives in Simulation (+ New character). The card shows
        the gear ledger's slots for its character, keyed by the learner's own fold (the card's 'seen:' key stripped)."""
        out = _run(r"""
          seed(null);
          var A = JSON.parse(JSON.stringify(ROSTER));
          var slots = ['helm','amulet','weapon','torso','off-hand','gloves','ring1','belt','ring2','boots'].map(function(s){
            return s === 'helm' ? {slot: s, item: 'Harlequin Crest', sightings: 4, tier: 'PROVEN'}
                                : {slot: s, item: null, sightings: 0, tier: null}; });
          A.gear = { frostnova: { name: 'Frostnova', slots: slots, unplaced: [{item: 'String of Ears', sightings: 2, tier: 'WATCHED'}], reels: 2 } };
          LEARNED_ANSWER = A; window.renderCharsTab();
          var ing = secHtml('ingame') || '';
          OUT.frost = (/<article class="chx-card chx-ghost" data-learned="seen:frostnova">([\s\S]*?)<\/article>/.exec(ing) || [])[1] || '';
          OUT.mule = (/<article class="chx-card chx-ghost" data-learned="seen:mulebox">([\s\S]*?)<\/article>/.exec(ing) || [])[1] || '';
          OUT.plans = (ing.match(/data-act="plan"/g) || []).length;
          LEARNED_ANSWER = ROSTER; window.renderCharsTab();
          OUT.unknown = (/<article class="chx-card chx-ghost" data-learned="seen:frostnova">([\s\S]*?)<\/article>/.exec(secHtml('ingame') || '') || [])[1] || '';
        """)
        self.assertEqual(out["plans"], 0, "an in-game card still offers Plan a build - his ruling: this section is automated")
        self.assertIn('data-slot="helm" data-tier="PROVEN"', out["frost"], "the card does not show what the game showed it wearing")
        self.assertIn("Harlequin Crest", out["frost"])
        self.assertIn("Wearing · 1 of 10 slots", out["frost"])
        self.assertIn('data-slot="boots" data-state="unseen"', out["frost"], "a slot nothing showed is not said as not seen")
        self.assertIn("String of Ears", out["frost"], "a worn item whose slot is not told went unsaid")
        self.assertIn("No gear seen yet", out["mule"], "a character with no gear on file is not said as such")
        self.assertIn("UNKNOWN", out["unknown"], "a console that did not say what its characters wear read as 'nothing'")

    def test_no_console_is_unknown_not_none_and_every_build_stays_in_simulation(self):
        out = _run(r"""
          seed(null); LEARNED_ANSWER = 'FAIL'; window.renderCharsTab();
          OUT.ing = secIds('ingame'); OUT.sim = secIds('sim');
          OUT.empty = /chx-sec-empty" data-state="(\w+)">([^<]*)/.exec(secHtml('ingame') || '');
          OUT.newOk = !ELS['chars-new'].disabled;
        """)
        self.assertEqual(out["ing"], [])
        self.assertEqual(out["sim"], ["bSORC", "bHAM", "bDRU"], "with no console a build left simulation (newest first)")
        self.assertIsNotNone(out["empty"])
        self.assertEqual(out["empty"][1], "unknown", "no answer was read as 'no characters' - it is UNKNOWN")
        self.assertIn("UNKNOWN", out["empty"][2])
        self.assertTrue(out["newOk"], "+ New character must stay exactly as it was")

    def test_a_console_that_learned_nothing_says_none_yet(self):
        out = _run(r"""
          seed(null); LEARNED_ANSWER = { ok: true, chars: [], tierBars: ROSTER.tierBars }; window.renderCharsTab();
          OUT.empty = /chx-sec-empty" data-state="(\w+)"/.exec(secHtml('ingame') || '');
          OUT.sim = secIds('sim');
        """)
        self.assertEqual(out["empty"][1], "none")
        self.assertEqual(out["sim"], ["bSORC", "bHAM", "bDRU"])


@unittest.skipIf(NODE is None, "node is not on this machine")
class ThePlannersListSaysTheSameSections(unittest.TestCase):

    def test_in_game_mules_then_simulation_with_new_build(self):
        out = _run(r"""
          seed('bSORC'); LEARNED_ANSWER = ROSTER; window._cbLearnedFetch(); window.openCharBuilder('bHAM');
          OUT.g = groups();
        """)
        g = out["g"]
        self.assertIsNotNone(g, "the planner's build list is gone")
        self.assertEqual([x["label"].split(" (")[0] for x in g],
                         ["⚔️ In game — 2 seen on this console's reels", "Level 1 — mules?", "🧪 Simulation builds"])
        self.assertEqual(g[0]["label"], "⚔️ In game — 2 seen on this console's reels")
        self.assertEqual([v for v, _ in g[0]["opts"]], ["bHAM", "tpl:seen:frostnova"],
                         "in game must list each learned character's build in its place, or the character itself")
        self.assertIn("✓ PROVEN · 11 of 11 looks", g[0]["opts"][1][1])
        self.assertIn("not saved yet", g[0]["opts"][1][1])
        self.assertEqual([v for v, _ in g[1]["opts"]], ["tpl:seen:mulebox"])
        self.assertEqual([v for v, _ in g[2]["opts"]], ["bSORC", "bDRU", "__new"],
                         "simulation must be every other build, MAIN first, and + New build")
        self.assertTrue(g[2]["opts"][0][1].startswith("★ MAIN · Blizz Sorc"))

    def test_an_unanswered_console_is_unknown_in_the_list_too(self):
        out = _run(r"""
          seed(null); window.openCharBuilder('bHAM'); OUT.g = groups();
        """)
        g = out["g"]
        self.assertTrue(g[0]["label"].startswith("⚔️ In game — UNKNOWN"), g[0]["label"])
        self.assertEqual([v for v, _ in g[-1]["opts"]], ["bSORC", "bHAM", "bDRU", "__new"])


def _ledger(visits, partial=False):
    """a ledger built by the learner's own record(): visits = [(ts, [names])] or [(ts, [names], partial)], each name
    read Paladin level 80; `partial` is what the reader said about the list (False = it saw the whole list)"""
    d = CS._empty()
    for v in visits:
        ts, names = v[0], v[1]
        vid = "reel_x#%d" % ts
        CS.record(d, vid, [{"name": n, "key": CS._fold(n), "cls": "Paladin", "level": 80, "title": None}
                           for n in names], {"reel": "reel_x", "ts": ts, "partial": v[2] if len(v) > 2 else partial})
    return d


class TheTierIsTheVaults(unittest.TestCase):

    def _tier(self, d, name):
        return CS.proof(d, d["chars"][CS._fold(name)])

    def test_it_proves_itself_look_by_look(self):
        for n, want in ((9, "WATCHED"), (10, "PROVEN"), (19, "PROVEN"), (20, "HARDENED")):
            d = _ledger([(1000 * (i + 1), ["Hammerdin"]) for i in range(n)])
            got = self._tier(d, "Hammerdin")
            self.assertEqual((got["tier"], got["looks"], got["trials"]), (want, n, n), "%d looks: %r" % (n, got))

    def test_a_character_the_screen_stops_showing_falls_back(self):
        d = _ledger([(1000 * (i + 1), ["Hammerdin", "Gone"] if i < 20 else ["Hammerdin"]) for i in range(40)])
        gone = self._tier(d, "Gone")
        self.assertEqual((gone["looks"], gone["trials"]), (20, 40))
        self.assertEqual(gone["tier"], "WATCHED", "a character missing from half its looks stayed HARDENED: %r" % gone)
        self.assertEqual(self._tier(d, "Hammerdin")["tier"], "HARDENED")

    def test_only_the_looks_since_it_appeared_are_its_trials(self):
        d = _ledger([(1000 * (i + 1), ["Hammerdin"] + (["Newbie"] if i >= 25 else [])) for i in range(35)])
        new = self._tier(d, "Newbie")
        self.assertEqual((new["looks"], new["trials"], new["tier"]), (10, 10, "PROVEN"),
                         "the looks before it existed were counted against it: %r" % new)

    def test_a_cut_off_list_is_no_evidence_against_a_character(self):
        # MEASURED on his: 9 rows of 13 characters - a character scrolled out of view was not deleted
        for later in (True, None):
            d = _ledger([(1000 * (i + 1), ["Hammerdin", "Scrolled"] if i < 20 else ["Hammerdin"], False if i < 20 else later)
                         for i in range(40)])
            got = self._tier(d, "Scrolled")
            self.assertEqual((got["looks"], got["trials"], got["misses"], got["tier"]), (20, 20, 0, "HARDENED"),
                             "a list that was cut off (partial=%r) counted against a character it did not show: %r" % (later, got))

    def test_one_read_that_saw_the_whole_list_makes_the_visit_whole(self):
        d = CS._empty()
        row = [{"name": "Hammerdin", "key": "hammerdin", "cls": "Paladin", "level": 80, "title": None}]
        CS.record(d, "reel_x#1", row, {"ts": 1, "partial": True})
        CS.record(d, "reel_x#1", row, {"ts": 2, "partial": False})
        CS.record(d, "reel_x#1", row, {"ts": 3, "partial": None})
        self.assertIs(d["visits"]["reel_x#1"]["partial"], False, "a later read undid what an earlier one saw whole")
        CS.record(d, "reel_x#2", row, {"ts": 4, "partial": None})
        self.assertIsNone(d["visits"]["reel_x#2"]["partial"], "a list nobody described was recorded as described")
        self.assertEqual([CS.partial_of(x) for x in ({"partial": False}, '{"partial": true}', {"chars": []}, "no json", None)],
                         [False, True, None, None, None])

    def test_a_visit_with_no_time_is_unknown(self):
        d = _ledger([(1000 * (i + 1), ["Hammerdin"]) for i in range(12)])
        d["visits"]["a-visit-with-no-time"] = {"reads": 1, "rows": 1}
        got = self._tier(d, "Hammerdin")
        self.assertIsNone(got["tier"], "a visit with no time was counted anyway: %r" % got)
        self.assertIn("UNKNOWN", got["why"])

    def test_the_tick_records_what_the_reader_said_about_the_list(self):
        tmp = tempfile.mkdtemp(prefix="cs_partial_")
        try:
            hist = os.path.join(tmp, "hist"); rd = os.path.join(hist, "reel_s_1"); os.makedirs(rd)
            for i in range(2):
                with open(os.path.join(rd, "f_%d.jpg" % (1790000000000 + i * 1000)), "wb") as f:
                    f.write(b"cs")
            os.environ["TV_CHARS_LEARNED"] = os.path.join(tmp, "roster.json")
            orig = CS.panel_crop
            CS.panel_crop = lambda p, out: p
            try:
                r = CS.tick(root=hist, stats=lambda p: (0.03, 0.36, 0.1, 0.22), now=1000000.0,
                            reader=lambda crop: {"screen": "character-select", "partial": False,
                                                 "chars": [{"name": "Testlock", "cls": "Warlock", "level": 88}]})
            finally:
                CS.panel_crop = orig
            self.assertTrue(r["ok"], r)
            v = list(CS.load()["visits"].values())
            self.assertEqual([x.get("partial") for x in v], [False], "the tick dropped what the reader said: %r" % v)
        finally:
            os.environ.pop("TV_CHARS_LEARNED", None)
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_learned_carries_the_tier(self):
        d = _ledger([(1000 * (i + 1), ["Hammerdin"]) for i in range(20)])
        row = [r for r in CS.learned(d) if r["name"] == "Hammerdin"][0]
        self.assertEqual((row["tier"], row["looks"], row["trials"]), ("HARDENED", 20, 20))
        self.assertEqual(CS.tier_bars(), {"proven": 10, "hardened": 20, "wilson": 0.722})

    def test_one_source_the_vaults_function_and_no_bars_of_its_own(self):
        tree = ast.parse(io.open(os.path.join(HERE, "char_select.py"), encoding="utf-8").read())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "tier" and getattr(n.func.value, "id", None) == "_ve"]
        self.assertEqual(len(calls), 1, "char_select no longer asks vault_evidence.tier")
        own = [t.id for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets
               if isinstance(t, ast.Name) and ("TRIALS" in t.id or "WILSON" in t.id)]
        self.assertEqual(own, [], "char_select carries its own copy of the vault's bars: %s" % own)

    def test_the_route_hands_the_page_the_bars(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        # the route's own branch body, by the AST - an if/elif chain's segment would run on into the next routes
        br = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
              and getattr(n.test.left, "id", None) == "path" and len(n.test.comparators) == 1
              and getattr(n.test.comparators[0], "value", None) == "/api/chars_learned"]
        self.assertEqual(len(br), 1, "/api/chars_learned is not one route any more")
        body = "\n".join(ast.get_source_segment(src, b) or "" for b in br[0].body)
        # #203 (v3814) - the route returns the one builder the shadow upload also asks; the bars are read there
        self.assertIn("self._json(200, chars_learned_answer())", body, "/api/chars_learned no longer returns the builder")
        fn = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == "chars_learned_answer"]
        self.assertEqual(len(fn), 1, "chars_learned_answer is not one function")
        body = ast.get_source_segment(src, fn[0]) or ""
        self.assertIn('"tierBars": _cs.tier_bars()', body, "/api/chars_learned stopped carrying the bars")


RED_PROOF = [
    {"why": "#114 (REG-1621) - roster order decides again: the first template matching the link OR the name wins",
     "file": "bible.html",
     "find": "      if (b.from) groups.forEach(function(x){ if (!g && b.from === x.t.key) g = x; });\n",
     "replace": "      groups.forEach(function(x){ if (!g && (b.from === x.t.key || (fk && fk === _cbFold(x.t.name)))) g = x; });\n",
     "matches": 1},
    {
        "why": "#103 (Grok eye) - an in-game card leads with the build's level, not the one the reels confirmed",
        "file": "bible.html",
        "find": "    if (t && t.level) lv = 'level ' + (t.level | 0) + ' in game'",
        "replace": "    if (false) lv = 'level ' + (t.level | 0) + ' in game'",
        "matches": 1,
    },
    {
        "why": "#103 (Grok eye) - the level-1 characters stand among the played ones with nothing saying they are mules",
        "file": "bible.html",
        "find": "    if (S.mules.length) cards += '<div class=\"chx-sec-sub\" data-sub=\"mules\">",
        "replace": "    if (false) cards += '<div class=\"chx-sec-sub\" data-sub=\"mules\">",
        "matches": 1,
    },
    {
        "why": "#103 - a build carrying a learned character's name is no longer under that character",
        "file": "bible.html",
        "find": "      if (!g && fk) groups.forEach(function(x){ if (!g && fk === _cbFold(x.t.name)) g = x; });\n",
        "replace": "      if (false) groups.forEach(function(x){ if (!g && fk === _cbFold(x.t.name)) g = x; });\n",
        "matches": 1,
    },
    {
        "why": "#103 - a build made from a learned character is no longer its card",
        "file": "bible.html",
        "find": "      if (b.from) groups.forEach(function(x){ if (!g && b.from === x.t.key) g = x; });\n",
        "replace": "      if (false) groups.forEach(function(x){ if (!g && b.from === x.t.key) g = x; });\n",
        "matches": 1,
    },
    {
        "why": "#103 - the room goes back to one flat list",
        "file": "bible.html",
        "find": "    list.innerHTML = _mainNote(_mainDangling(r.all)) + _sections(r.all, _order(r.all, mainId), mainId);\n",
        "replace": "    list.innerHTML = _mainNote(_mainDangling(r.all)) + _order(r.all, mainId).map(function(id){ return _card(id, r.all[id], id === mainId); }).join('');\n",
        "matches": 1,
    },
    {
        "why": "#103 - a console that has not answered reads as one that learned nothing",
        "file": "bible.html",
        "find": "      state = 'unknown';\n",
        "replace": "      state = 'none';\n",
        "matches": 1,
    },
    {
        "why": "#103 - a learned character with no build vanishes from the room",
        "file": "bible.html",
        "find": ".join('') : _ghost(g.t); };\n",
        "replace": ".join('') : ''; };\n",
        "matches": 1,
    },
    {
        "why": "#103 - the planner's simulation group lists the in-game builds too",
        "file": "bible.html",
        "find": ")\">' + S.sim.map(_bopt).join('') + '<option value=\"__new\">",
        "replace": ")\">' + order.map(_bopt).join('') + '<option value=\"__new\">",
        "matches": 1,
    },
    {
        "why": "#103 - a HARDENED character is said as PROVEN",
        "file": "bible.html",
        "find": "    if (t.tier === 'HARDENED') return '🔒 HARDENED · ' + n;\n",
        "replace": "    if (t.tier === 'HARDENED') return '✓ PROVEN · ' + n;\n",
        "matches": 1,
    },
    {
        "why": "#103 - the looks before a character existed count against it",
        "file": "tv/char_select.py",
        "find": "        if ts >= int(first) and isinstance(v, dict) and v.get(\"partial\") is False:\n",
        "replace": "        if isinstance(v, dict) and v.get(\"partial\") is False:\n",
        "matches": 1,
    },
    {
        "why": "#103 - a cut-off list (9 rows of his 13) counts against every character it did not show",
        "file": "tv/char_select.py",
        "find": "        if ts >= int(first) and isinstance(v, dict) and v.get(\"partial\") is False:\n",
        "replace": "        if ts >= int(first):\n",
        "matches": 1,
    },
    {
        "why": "#103 - a visit with no time is skipped instead of making the tier UNKNOWN",
        "file": "tv/char_select.py",
        "find": "        if ts is None:\n            return {\"tier\": None, \"looks\": looks, \"trials\": None, \"misses\": None, \"bound\": None,\n",
        "replace": "        if ts is None:\n            continue\n            return {\"tier\": None, \"looks\": looks, \"trials\": None, \"misses\": None, \"bound\": None,\n",
        "matches": 1,
    },
    {
        "why": "#103 - the tick drops what the reader said about the list",
        "file": "tv/char_select.py",
        "find": "\"frames\": [os.path.basename(p)], \"partial\": partial_of(raw),\n",
        "replace": "\"frames\": [os.path.basename(p)],\n",
        "matches": 1,
    },
    {
        "why": "#103 - the last read of a visit decides whether its list was whole",
        "file": "tv/char_select.py",
        "find": "        v[\"partial\"] = False if (p is False or prev is False) else (True if (p is True or prev is True) else None)\n",
        "replace": "        v[\"partial\"] = p\n",
        "matches": 1,
    },
    {
        "why": "#103 - the room stops asking its console what the reels learned",
        "file": "bible.html",
        "find": "    try { if (typeof window._cbLearnedFetch === 'function') window._cbLearnedFetch(function(){ _render(); }); } catch (e) {}\n",
        "replace": "",
        "matches": 1,
    },
    {"why": "#234 - the in-game card stops showing what its character wears",
     "file": "../bible.html",
     # c637711e put the Open button between the gear and </article>; the gear line alone is the join
     "find": "      + _gearHtml(t)\n",
     "replace": "",
     "matches": 1},
    {"why": "#234 - the card looks its gear up by the planner's 'seen:' key, so every card reads nothing seen",
     "file": "../bible.html",
     "find": "    var k = String(t.key || ''); if (k.indexOf('seen:') === 0) k = k.slice(5);\n",
     "replace": "    var k = String(t.key || '');\n",
     "matches": 1},
    {"why": "#234 - a console that never said what its characters wear reads as 'nothing seen'",
     "file": "../bible.html",
     "find": "    if (!L || !Object.prototype.hasOwnProperty.call(L, 'gear')) return { state: 'unknown',",
     "replace": "    if (!L) return { state: 'unknown',",
     "matches": 1},
    {"why": "#234 - with no build made by hand the room hides the characters its console learned",
     "file": "../bible.html",
     "find": "    if (!Object.keys(r.all).length && !_learnedAny){\n",
     "replace": "    if (!Object.keys(r.all).length){\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
