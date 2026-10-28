# -*- coding: utf-8 -*-
"""REG-2920 (#252) - A RECOMMENDATION NAMES THIS PC'S OWN CHARACTER, HIS ON HIS LEDGER, AND NEVER HIS NAMES ANYWHERE ELSE.

His rule (2026-09-27): every personal surface is per-PC. CHARS, BOSS_CHAR_REC, BOSS_ACTION_PLAN, BOSSES[].char, the sunder
tables, the zone and rune-source guides and the TZ tab's static zone cards were all typed for HIS roster, and every PC got
them: another PC's boss card said "best char from your roster: Konyolock - Warlock 88". Measured before the fix, on a board
that is not his, every one of the surfaces below printed his character names.

One gate decides, the one the chronicle seeds already use (`_seedsBelongHere`, v2692). On HIS ledger every surface reads
exactly as before - a test build he saved never retitles his card. Anywhere else each name resolves in one order:
  1. this PC's own character of that class (one its console learned, else a build saved here) -> "your <Class> <name>";
  2. else the class and role - never his names.

Driven on the whole page in node (vault_page_node), four fixture worlds, nothing of his: HIS (claimed, ledger KonyoEndgame),
OTHER (claimed, another named ledger), GUEST (an unclaimed store) and OWN (OTHER with a Paladin build saved). The count is
of his names in what each surface renders (its text, plus title/alt/aria-label). The markup's own text nodes are handed to
the page's boot walker through a tree-walker stand-in, so the walker is proven to run at boot, not only to exist.
RED_PROOF below.
"""
import html as _html
import io
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import vault_page_node as VPN  # noqa: E402

NAMES = re.compile(r"Konyo(?:lock|din|ress|ssin)", re.I)
CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');"
BUILD = "localStorage.setItem('d2r_charBuilds', %s);" % json.dumps(json.dumps(
    {"b1": {"name": "Hammerfall", "cls": "Paladin", "level": 85, "sets": [], "active": 0}}))
WORLDS = {
    "his": CLAIM + "localStorage.setItem('d2r_ledgerName', 'KonyoEndgame');",
    "other": CLAIM + "localStorage.setItem('d2r_ledgerName', 'Deans-Own-Ledger');",
    "guest": "",
    "own": CLAIM + "localStorage.setItem('d2r_ledgerName', 'Deans-Own-Ledger');" + BUILD,
}
# the surfaces whose source data names his characters today (read off BOSS_CHAR_REC, BOSS_ACTION_PLAN, BOSSES, the
# sunder tables, TZ_ZONES and RUNE_SOURCES) - each must carry a name on his ledger, or the zero elsewhere means nothing
CARRIERS = ("bossDetail", "bossCards", "itemDetail", "aid", "sunderCharms", "sunderRecipes", "herald", "material",
            "specialDrops", "pandemonium", "zoneDetail", "tzZoneCard", "runeSource")


def static_text_nodes():
    """The markup's text nodes that name him, as the browser's tree walker would hand them to the page. -> [str]"""
    s = io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
    for rx in (r"<script\b[^>]*>[\s\S]*?</script>", r"<style\b[^>]*>[\s\S]*?</style>", r"<!--[\s\S]*?-->",
               r"<textarea\b[^>]*>[\s\S]*?</textarea>"):
        s = re.sub(rx, "", s)
    return [_html.unescape(t) for t in re.split(r"<[^>]+>", s) if re.search(r"Konyo(?:lock|din|ress|ssin)|For Konyo", t, re.I)]


def prelude(world):
    nodes = [{"nodeValue": t, "parentNode": {"nodeName": "DIV"}} for t in static_text_nodes()]
    return (WORLDS[world] + "window.NodeFilter = window.NodeFilter || { SHOW_TEXT: 4 };"
            "window.__STATIC_NODES = %s;"
            "document.createTreeWalker = function(){ var i = -1, N = window.__STATIC_NODES;"
            " return { nextNode: function(){ i++; return i < N.length ? N[i] : null; } }; };" % json.dumps(nodes))


BODY = r"""
(function(){
var NAMES = /Konyo(?:lock|din|ress|ssin)/gi;
function vis(h){
  h = String(h == null ? '' : h);
  var attrs = []; h.replace(/\b(?:title|alt|aria-label)\s*=\s*"([^"]*)"/g, function(m, v){ attrs.push(v); return m; });
  return h.replace(/<[^>]*>/g, ' ') + ' ' + attrs.join(' ');
}
var S = {}, ERR = [];
function add(k, h){
  var v = vis(h), s = S[k] = S[k] || { n: 0, names: 0, text: '' };
  s.n++; s.names += (v.match(NAMES) || []).length;
  if (s.text.length < 400000) s.text += v.replace(/\s+/g, ' ') + ' | ';
}
function grab(id){ var e = document.getElementById(id); return e ? String(e.innerHTML || '') : ''; }
function tryit(k, f){ try { f(); } catch (e) { ERR.push(k + ': ' + String(e && e.message || e)); } }
/* everything the page painted on its own at boot, before this body draws anything */
OUT.painted = [];
H.ELS.forEach(function(e, id){ var n = (vis(String(e._html || '') + ' ' + String(e._text || '')).match(NAMES) || []).length; if (n) OUT.painted.push(id + ':' + n); });
tryit('bossDetail', function(){ BOSSES.forEach(function(b){ renderBossDetailCard(b.id); add('bossDetail', grab('boss-detail-panel')); }); });
tryit('bossCards', function(){ renderBossCards(); add('bossCards', grab('boss-cards')); });
/* every item: which boss an item card plans for is its BEST source at this board's MF, so a sample can miss them all */
var picked = [];
tryit('pick', function(){ ITEMS.forEach(function(it){ if ((it.sources || []).length) picked.push(it.n); }); });
tryit('itemDetail', function(){ picked.forEach(function(n){ renderItemDetailCard(n); add('itemDetail', grab('item-detail-panel')); }); });
tryit('aid', function(){ picked.forEach(function(n){ add('aid', renderAidCard(n)); }); });
tryit('sunderCharms', function(){ add('sunderCharms', sunderCharmsDetailHtml()); });
tryit('sunderRecipes', function(){ renderSunderRecipes(); add('sunderRecipes', grab('sunder-recipe-grid')); });
tryit('herald', function(){ renderHeraldCard(); add('herald', grab('herald-sunder-rows')); });
tryit('material', function(){ Object.keys(SPECIAL_DROPS).forEach(function(k){ (SPECIAL_DROPS[k].items || []).forEach(function(it){ add('material', materialDetailHtml(it.n)); }); }); });
tryit('specialDrops', function(){ renderSpecialDrops(); add('specialDrops', grab('special-drops-grid')); });
tryit('pandemonium', function(){ add('pandemonium', pandemoniumKeysDetailHtml()); });
tryit('zones', function(){ TZ_ZONES.forEach(function(z, i){ add('zoneDetail', zoneDetailHtml(z)); add('tzZoneCard', tzZoneCardHtml(z, i)); }); });
tryit('runeSources', function(){ RUNE_SOURCES.forEach(function(src){ add('runeSource', runeSourceDetailHtml(src)); }); });
OUT.S = S; OUT.ERR = ERR; OUT.picked = picked.length;
OUT.static = (window.__STATIC_NODES || []).map(function(t){ return t.nodeValue; });
OUT.seeds = window._seedsBelongHere === true;
OUT.card = { konyodin: window._charCard('konyodin'), konyolock: window._charCard('konyolock') };
OUT.say = window._charSay('Konyolock: Enigma TP each level. Konyodin halved by 75% MR.');
})();
"""

_RUNS = {}


def page(world):
    if world not in _RUNS:
        _RUNS[world] = VPN.run(BODY, prelude=prelude(world), timeout=600)
    return _RUNS[world]


def names(texts):
    return sum(len(NAMES.findall(t or "")) for t in texts)


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ARecommendationNamesThisPcsCharacters(unittest.TestCase):

    def test_the_premise_every_world_boots_and_every_surface_renders(self):
        for w in WORLDS:
            o = page(w)
            self.assertEqual(o["__boot"]["errors"], [], "%s: %r" % (w, o["__boot"]))
            self.assertEqual(o["ERR"], [], "%s: a surface threw while rendering: %r" % (w, o["ERR"]))
            self.assertGreater(o["picked"], 0, "%s: no item was picked to render" % w)
            for k in CARRIERS:
                self.assertGreater((o["S"].get(k) or {}).get("n", 0), 0, "%s: surface %s rendered nothing" % (w, k))
        self.assertTrue(page("his")["seeds"], "PREMISE: the HIS world is not his ledger")
        for w in ("other", "guest", "own"):
            self.assertFalse(page(w)["seeds"], "PREMISE: the %s world reads as his ledger" % w)

    def test_his_ledger_keeps_his_names_on_every_surface_that_carries_them(self):
        S = page("his")["S"]
        for k in CARRIERS:
            self.assertGreater(S[k]["names"], 0, "his ledger lost his names on %s: %s" % (k, S[k]["text"][:300]))

    def test_no_other_board_renders_his_names(self):
        for w in ("other", "guest", "own"):
            S = page(w)["S"]
            leaks = dict((k, v["names"]) for k, v in S.items() if v["names"])
            self.assertEqual(leaks, {}, "%s board rendered his character names: %r - e.g. %s" % (
                w, leaks, [S[k]["text"][:240] for k in leaks][:2]))

    def test_nothing_the_page_paints_at_boot_names_him_on_another_board(self):
        for w in ("other", "guest", "own"):
            self.assertEqual(page(w)["painted"], [], "%s board: elements painted at boot name him: %r" % (w, page(w)["painted"]))

    def test_the_markup_text_is_resolved_at_boot_off_his_ledger_only(self):
        src = static_text_nodes()
        self.assertGreater(names(src), 0, "PREMISE: the markup no longer names him - this case measures nothing")
        self.assertEqual(page("his")["static"], src, "his ledger's markup text was rewritten")
        for w in ("other", "guest"):
            got = page(w)["static"]
            self.assertEqual(len(got), len(src))
            self.assertEqual(names(got), 0, "%s board's markup still names him after boot: %r" % (
                w, [t for t in got if NAMES.search(t)][:3]))

    def test_this_pcs_own_character_is_the_one_named(self):
        o = page("own")
        self.assertEqual((o["card"]["konyodin"] or {}).get("name"), "Hammerfall", o["card"])
        self.assertTrue(o["card"]["konyodin"]["mine"], o["card"])
        self.assertIn("Paladin", o["card"]["konyodin"]["build"])
        self.assertIn("Your Paladin Hammerfall halved", o["say"])
        self.assertIn("Hammerfall", o["S"]["bossDetail"]["text"], "the boss card does not name this PC's own Paladin")

    def test_with_no_character_of_that_class_the_class_is_named(self):
        for w in ("other", "own"):
            c = page(w)["card"]["konyolock"]
            self.assertFalse(c["mine"], "%s: a character it does not have is called its own: %r" % (w, c))
            self.assertEqual(c["build"], "Warlock", c)
            self.assertFalse(NAMES.search(c["name"]), c)
        self.assertTrue(page("other")["say"].startswith("A physical melee build: Enigma TP"), page("other")["say"])
        self.assertIn("A Hammerdin halved", page("other")["say"])
        self.assertIn("best character for this boss", page("other")["S"]["bossDetail"]["text"])

    def test_his_ledger_card_is_his_typed_roster(self):
        c = page("his")["card"]["konyolock"]
        self.assertEqual((c["name"], c["build"], c["mine"]), ("Konyolock", "Warlock 88", True), c)
        self.assertEqual(page("his")["say"], "Konyolock: Enigma TP each level. Konyodin halved by 75% MR.")

    def test_a_build_he_saved_never_retitles_his_own_card(self):
        if "his_build" not in _RUNS:
            _RUNS["his_build"] = VPN.run("OUT.seeds = window._seedsBelongHere === true; OUT.card = window._charCard('konyodin');",
                                         prelude=WORLDS["his"] + BUILD, timeout=600)
        o = _RUNS["his_build"]
        self.assertTrue(o["seeds"], "PREMISE: not his ledger")
        self.assertEqual((o["card"]["name"], o["card"]["build"]), ("Konyodin", "Hammerdin 82"),
                         "a saved test build retitled his card: %r" % o["card"])


RED_PROOF = [
    {"why": "REG-2920 - the resolver gives his names to every board again",
     "file": "bible.html",
     "find": "  if (text == null || window._seedsBelongHere === true) return text;\n  return String(text)\n",
     "replace": "  return text;\n  return String(text)\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the best-character card reads his typed roster on every board",
     "file": "bible.html",
     "find": "  if (window._seedsBelongHere === true && c) return { name: c.name, build: c.build, role: c.role, mine: true };\n",
     "replace": "  if (c) return { name: c.name, build: c.build, role: c.role, mine: true };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - this PC's own build is no longer looked up",
     "file": "bible.html",
     "find": "      var all = (typeof window._cbAll === 'function') ? window._cbAll() : {};\n      Object.keys(all || {}).forEach(function(k){\n",
     "replace": "      var all = {};\n      Object.keys(all || {}).forEach(function(k){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - on his ledger a saved build outranks his typed roster",
     "file": "bible.html",
     "find": "  if (window._seedsBelongHere === true && c) return { name: c.name, build: c.build, role: c.role, mine: true };\n  var own = r ? _yourCharOfClass(r.cls) : null;\n  if (own) return { name: own.name, build: own.cls + (own.level ? ' ' + own.level : ''), role: c ? c.role : '', mine: true };\n",
     "replace": "  var own = r ? _yourCharOfClass(r.cls) : null;\n  if (own) return { name: own.name, build: own.cls + (own.level ? ' ' + own.level : ''), role: c ? c.role : '', mine: true };\n  if (window._seedsBelongHere === true && c) return { name: c.name, build: c.build, role: c.role, mine: true };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the markup's text is never resolved at boot",
     "file": "bible.html",
     "find": "if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ _charSayStatic(); });\n",
     "replace": "if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ });\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the boss cards print BOSSES[].char raw",
     "file": "bible.html",
     "find": "<strong>🎮 Recommended char:</strong> ${_charSay(boss.char)}</div>",
     "replace": "<strong>🎮 Recommended char:</strong> ${boss.char}</div>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the boss detail prints BOSSES[].why raw",
     "file": "bible.html",
     "find": "<div class=\"gbc-why\">${_charSay(boss.why) || 'No specific notes for this boss.'}</div>",
     "replace": "<div class=\"gbc-why\">${boss.why || 'No specific notes for this boss.'}</div>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the boss cards' Why farm prints BOSSES[].why raw",
     "file": "bible.html",
     "find": "<strong>Why farm:</strong> ${_charSay(boss.why)}</div>",
     "replace": "<strong>Why farm:</strong> ${boss.why}</div>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - a special drop's card prints its note raw",
     "file": "bible.html",
     "find": "<span class=\"zd-k\">note</span><span class=\"zd-v\">${_charSay(item.note)}</span>",
     "replace": "<span class=\"zd-k\">note</span><span class=\"zd-v\">${item.note}</span>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the special drops grid prints each note raw",
     "file": "bible.html",
     "find": "<div class=\"sd-item-note\">${_charSay(it.note)}</div>",
     "replace": "<div class=\"sd-item-note\">${it.note}</div>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the item card's build tip prints BOSS_ACTION_PLAN raw",
     "file": "bible.html",
     "find": "<div class=\"gic-action-key\">BUILD TIP</div><div class=\"gic-action-val\">${_charSay(plan.build)}</div>",
     "replace": "<div class=\"gic-action-key\">BUILD TIP</div><div class=\"gic-action-val\">${plan.build}</div>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the sunder recipes print his character as the best wearer",
     "file": "bible.html",
     "find": "best for <span class=\"sun-best\">${_charSay(s.best, true)}</span>",
     "replace": "best for <span class=\"sun-best\">${s.best}</span>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the sunder recipe tile's own 'best for' names his character",
     "file": "bible.html",
     "find": "    const best = _charSay(cc.build ? (cc.star && window._seedsBelongHere === true ? '⭐ ' + cc.build : cc.build) : s.best, true);\n",
     "replace": "    const best = cc.build ? (cc.star ? '⭐ ' + cc.build : cc.build) : s.best;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the Herald table prints his character as the best wearer",
     "file": "bible.html",
     "find": "<td class=\"brk ${s.imm}\">${s.breaks}</td><td>${_charSay(s.best)}</td>",
     "replace": "<td class=\"brk ${s.imm}\">${s.breaks}</td><td>${s.best}</td>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the zone detail prints z.why raw",
     "file": "bible.html",
     "find": "<span class=\"zd-k\">why farm here</span><span class=\"zd-v\">${_charSay(z.why)}</span>",
     "replace": "<span class=\"zd-k\">why farm here</span><span class=\"zd-v\">${z.why}</span>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the TZ zone card prints z.why raw",
     "file": "bible.html",
     "find": "<div class=\"tz-zone-body\">${_charSay(z.why)}</div>",
     "replace": "<div class=\"tz-zone-body\">${z.why}</div>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the rune-source action plan prints his names",
     "file": "bible.html",
     "find": "<strong>📋 Action plan:</strong> '+_charSay(src.action)+'</div>';",
     "replace": "<strong>📋 Action plan:</strong> '+src.action+'</div>';",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the Pandemonium card names Konyolock as the best",
     "file": "bible.html",
     "find": "<strong style=\"color:var(--best)\">${_charSay('Konyolock')}</strong>",
     "replace": "<strong style=\"color:var(--best)\">Konyolock</strong>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the sunder-charm tiles print his build as the best",
     "file": "bible.html",
     "find": "best for ${_charSay(s.star && window._seedsBelongHere === true ? '⭐ '+s.build : s.build, true)}</div>",
     "replace": "best for ${s.star ? '⭐ '+s.build : s.build}</div>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2920 - the sunder material cards print his character in what the charm does",
     "file": "bible.html",
     "find": "<div style=\"font-size:13.5px;line-height:1.6\">${_charSay(item.does)}</div>",
     "replace": "<div style=\"font-size:13.5px;line-height:1.6\">${item.does}</div>",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
