# -*- coding: utf-8 -*-
"""REG-2860 (#230, his ask relayed by GrokBot) - THE VAULT'S GUIDE WALKS THE REAL CONTROLS, TUTORIAL FIRST, AND WRITES NOTHING.

Runewords (the Forge legend) and Tools (the map) each have a tray orb in slot S2 that opens a panel on their tab; the vault
tab had none, so Dean or anyone new had no way into the room without Konyo. The Vault guide is the third orb in that slot,
built on the same chassis (the tray slot, the panel, _toolJump's switch-room / scroll / pulse). This law pins what he asked
for, on the whole page in node (vault_page_node - never a browser on his Mac):

  * every step and every "show me" lights a control that EXISTS: getElementById answers it on the booted page, and its
    id="..." is in the markup exactly once (a duplicate would light the wrong one);
  * TUTORIAL FIRST: "What you need to do" (his own actions, in order) comes before the explanations, and every
    explanation is its own collapsible <details>, closed until he opens it - one for each topic he listed;
  * the guide STORES NOTHING - not on his board (no seen flag, no step, no pref), not on its reveal path (opening the
    Advanced pane shuts MOVE TASKS quietly, so that handler has nothing to remember), and not inside a shadow - where it
    draws exactly what it draws on his board (a shadow renders through the board's own templates and the console's
    shadow bar says whose it is and that it is read only: test_no_screen_of_the_board_branches_on_the_shadow);
  * every control it draws only moves the view: each onclick is vaultGuideTog / vaultGuideGo alone (the shadow lets
    exactly those through - test_shadow_mode_reads_their_console pins that half);
  * the figures it quotes (cells per mule, shared pages, sessions to file) are read off the page when it is drawn, and an
    absent one is said without a number - never a guessed one;
  * a locker is named by what it is called TODAY (a renamed locker keeps its job);
  * what is not built (the guided sweep, the move question, the not-seen log) is said as COMING and is never a control.

The look (on screen, not covered, reachable) is Chrome's: tests/vault_guide_walks_the_real_controls.spec.ts and the
'vault guide' row of tests/v1800_tray_popovers_reachable.spec.ts. CI proves those. RED_PROOF below.
"""
import io
import json
import os
import re
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

BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');\n"
# a control the guide draws may only move the view: one call, to the guide's own two doors
VIEW_ONLY = re.compile(r"^window\.vaultGuide(?:Tog|Go)\((?:-?\d+|'[a-z]+'|true|false)?\)$")
# the topics he listed (#230 c6476237779 + c6476256141), each its own fold
ASKED = ("lockers", "mules", "intake", "tasks", "counts", "profile", "shadow", "safe")

WALK = r"""
var W = window, VG = W._vaultGuide;
OUT.vg = VG;
var fab = document.getElementById('vault-guide-fab');
OUT.fabClick = fab ? fab.getAttribute('onclick') : null;
function rawNow(){ return JSON.stringify(Array.from(H.RAW.entries()).sort()); }
function pop(){ var p = document.getElementById('vault-guide-pop'); return p ? p.innerHTML : null; }
/* the reveal path: AUTO INTAKE sits in a hidden Advanced pane, and MOVE TASKS is open */
var tasks = document.getElementById('vault-tasks'); if (tasks) tasks.hidden = false;
var ai = document.getElementById('vault-auto-intake');
var pane = { hidden: true, getAttribute: function(k){ return k === 'data-adv' ? 'intake' : null; } };
if (ai) ai.closest = function(sel){ return String(sel).indexOf('.vadv-pane') === 0 ? pane : null; };
OUT.adv = []; var _adv = W.vaultAdvTab; W.vaultAdvTab = function(n){ OUT.adv.push(n); pane.hidden = false; return _adv ? _adv.apply(this, arguments) : false; };
OUT.tog = []; var _tog = W.vaultTasksTog; W.vaultTasksTog = function(){ OUT.tog.push(Array.prototype.slice.call(arguments)); return _tog.apply(this, arguments); };
H.flush(2000, 5);   /* the page's own deferred boot work runs first, so what follows is the guide's alone */
var s0 = H.ls.set, r0 = rawNow();
OUT.opened = W.vaultGuideTog(true);
OUT.list = pop();
OUT.lit = []; OUT.walks = [];
for (var i = 0; i < VG.steps.length; i++) { OUT.lit.push(W.vaultGuideGo(i)); OUT.walks.push(pop()); }
VG.shows.forEach(function(s){ OUT.lit.push(W.vaultGuideGo(s.key)); OUT.walks.push(pop()); });
OUT.back = W.vaultGuideGo(-1);
OUT.closed = W.vaultGuideTog(false);
H.flush(2000, 3);
OUT.tasksHidden = tasks ? tasks.hidden : null;
OUT.sets = H.ls.set - s0; OUT.rawSame = rawNow() === r0;
OUT.roster = (W._vaultRosterNow() || []).map(function(m){ return m.id; });
/* the figures: read when drawn, so a page with other figures says them, and a page without one says no number */
OUT.pageFig = { cap: W.MULE_CAP, pages: W.SHARED_PAGES, wmin: W.VAULT_WITNESS_MIN };
W.MULE_CAP = 777; W.SHARED_PAGES = 9; W.VAULT_WITNESS_MIN = 7;
W.vaultGuideTog(true); OUT.figs = pop(); W.vaultGuideTog(false);
W.MULE_CAP = undefined; W.SHARED_PAGES = undefined; W.VAULT_WITNESS_MIN = undefined;
W.vaultGuideTog(true); OUT.noFigs = pop(); W.vaultGuideTog(false);
W.MULE_CAP = OUT.pageFig.cap; W.SHARED_PAGES = OUT.pageFig.pages; W.VAULT_WITNESS_MIN = OUT.pageFig.wmin;
/* a shadow: the same guide, and still nothing is written */
W._tvdShadow = { owner: 'Dean', t: 1 };
var s1 = H.ls.set, r1 = rawNow();
W.vaultGuideTog(true); OUT.shadowList = pop();
for (var j = 0; j < VG.steps.length; j++) W.vaultGuideGo(j);
OUT.shadowWalk = pop();
W.vaultGuideTog(false); H.flush(2000, 3);
OUT.shadowSets = H.ls.set - s1; OUT.shadowRawSame = rawNow() === r1;
"""


def _markup_ids():
    """id -> how often id="..." appears in bible.html outside its <script> blocks (the page's own markup)."""
    src = io.open(BIBLE, encoding="utf-8").read()
    markup = re.sub(r"<script\b[^>]*>.*?</script>", "", src, flags=re.S)
    counts = {}
    for m in re.finditer(r'\bid="([^"]+)"', markup):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return counts


def _onclicks(html):
    return re.findall(r'onclick="([^"]*)"', html or "")


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class TheVaultGuideWalksTheRealControls(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(WALK, prelude=CLAIM, timeout=300)
        cls.vg = cls.o.get("vg") or {}
        if not cls.vg.get("steps"):
            raise AssertionError("PREMISE: the page has no Vault guide (window._vaultGuide): %r" % (cls.vg,))
        # a renamed locker, the way his saved roster holds it, in a second boot
        base = VPN.run("OUT.r = window._vaultRosterNow && window._vaultRosterNow();", prelude=CLAIM, timeout=300).get("r")
        if not isinstance(base, list) or not base:
            raise AssertionError("PREMISE: the page has no default roster to rename in: %r" % (base,))
        roster = [dict(m, name="RINGS N THINGS") if m.get("id") == "uni-small" else m for m in base]
        cls.renamed = VPN.run("window.vaultGuideTog(true); OUT.html = document.getElementById('vault-guide-pop').innerHTML;",
                              prelude=CLAIM + "localStorage.setItem('d2r_muleRoster', %s);\n" % json.dumps(json.dumps(roster)),
                              timeout=300).get("html")

    def _targets(self):
        return [s["target"] for s in self.vg["steps"]] + [s["target"] for s in self.vg["shows"]]

    def test_every_step_lights_a_control_that_is_on_the_page(self):
        want = self._targets()
        self.assertEqual(self.o["lit"], want, "a step or a show lit nothing (null) or the wrong control: %r" % self.o["lit"])
        ids = _markup_ids()
        for t in want:
            self.assertEqual(ids.get(t, 0), 1, "%r is in the page's markup %d times - the guide must name a control that "
                                               "is there exactly once" % (t, ids.get(t, 0)))

    def test_what_you_need_to_do_comes_first_then_the_folds(self):
        h = self.o["list"] or ""
        do, how = h.find('data-vgd="do"'), h.find('data-vgd="how"')
        self.assertTrue(0 <= do < how, "the explanations come before (or without) 'What you need to do': do=%d how=%d" % (do, how))
        self.assertLess(do, h.find("<details"), "a fold opens before his own steps")
        self.assertIn("What you need to do", h[do:how])
        at = [h.find(">" + s["title"].replace("&", "&amp;") + "<", do) for s in self.vg["steps"]]
        self.assertTrue(all(do < a < how for a in at), "a step is not inside 'What you need to do': %r" % at)
        self.assertEqual(at, sorted(at), "his steps are not drawn in their order of priority: %r" % at)
        self.assertGreater(len(self.vg["steps"]), 1)

    def test_every_explanation_is_a_closed_fold_one_per_topic_he_listed(self):
        h = self.o["list"] or ""
        folds = re.findall(r'<details class="vgd-sec" data-sec="([a-z]+)"(\s+open)?><summary>', h)
        self.assertEqual([f[0] for f in folds], self.vg["sections"], "a section is not a collapsible <details> fold")
        self.assertEqual([f for f in folds if f[1]], [], "a fold opens by itself - each is closed until he opens it")
        for k in ASKED:
            self.assertIn(k, self.vg["sections"], "his topic %r has no fold" % k)

    def test_the_guide_writes_nothing(self):
        self.assertEqual(self.o["sets"], 0, "the guide wrote %d store(s) while it opened, walked and closed" % self.o["sets"])
        self.assertTrue(self.o["rawSame"], "a store changed while the guide opened, walked and closed")
        # the reveal path ran: the Advanced pane was opened, and MOVE TASKS was shut quietly (nothing to remember)
        self.assertEqual(self.o["adv"], ["intake"], "the AUTO INTAKE step did not open its Advanced pane: %r" % self.o["adv"])
        self.assertTrue(self.o["tasksHidden"], "MOVE TASKS stayed open beside the Advanced drawer")
        self.assertEqual(self.o["tog"], [[False, True]], "MOVE TASKS was shut by a call that remembers it: %r" % self.o["tog"])

    def test_a_shadow_draws_the_same_guide_and_writes_nothing(self):
        n = len(self.vg["steps"])
        self.assertTrue(self.o["list"], "the guide drew nothing")
        self.assertEqual(self.o["shadowList"], self.o["list"], "the guide draws differently inside a shadow")
        self.assertEqual(self.o["shadowWalk"], self.o["walks"][n - 1], "a step draws differently inside a shadow")
        self.assertEqual(self.o["shadowSets"], 0, "the guide wrote inside a shadow")
        self.assertTrue(self.o["shadowRawSame"])

    def test_every_control_it_draws_only_moves_the_view(self):
        clicks = [self.o["fabClick"]] + _onclicks(self.o["list"]) + [c for w in self.o["walks"] for c in _onclicks(w)]
        self.assertGreater(len(clicks), len(self._targets()))
        bad = [c for c in clicks if not (c and VIEW_ONLY.match(c))]
        self.assertEqual(bad, [], "a guide control does more than move the view (a shadow would stop it): %r" % bad)

    def test_the_figures_are_the_pages_own(self):
        pf = self.o["pageFig"]
        for k in ("cap", "pages", "wmin"):
            self.assertIsInstance(pf.get(k), int, "the page does not publish %s for the guide to read: %r" % (k, pf))
        h = self.o["figs"] or ""
        self.assertIn("777 cells", h, "the cells per mule are not the page's MULE_CAP")
        self.assertIn("9 pages", h, "the shared pages are not the page's SHARED_PAGES")
        self.assertIn("7 different sessions", h, "the sessions to file are not the page's VAULT_WITNESS_MIN")
        n = self.o["noFigs"] or ""
        for junk in ("undefined", "NaN", "null", "777", "9 pages", "7 different"):
            self.assertNotIn(junk, n, "with a figure absent the guide still printed %r" % junk)
        self.assertIn("more than one session", n)

    def test_a_locker_is_called_what_it_is_called_today(self):
        self.assertTrue(set(self.vg["lockers"]) <= set(self.o["roster"]),
                        "the guide names a locker the roster does not have: %r" % sorted(set(self.vg["lockers"]) - set(self.o["roster"])))
        self.assertIn("<b>RINGS N THINGS</b>", self.renamed or "", "a renamed locker is still called by its old name")
        self.assertNotIn("<b>UNI-SMALL</b>", self.renamed or "")

    def test_what_is_not_built_is_said_as_coming_never_drawn_as_a_control(self):
        h = self.o["list"] or ""
        m = re.search(r'<p class="vgd-soon">(.*?)</p>', h)
        self.assertIsNotNone(m, "the not-yet-built items are not marked as coming")
        soon = m.group(1)
        self.assertIn("not on this board yet", soon)
        self.assertIn("Did &lt;item&gt; move to &lt;mule&gt;, cell (c,r)?", soon)
        self.assertNotIn("onclick", soon)


RED_PROOF = [
    {"why": "REG-2860 - a step names a control that is not on the page",
     "file": "bible.html",
     "find": "    { target: 'vault-sort-btn', where: 'the toolbar', title: 'Sort the loose items',\n",
     "replace": "    { target: 'vault-sort-button', where: 'the toolbar', title: 'Sort the loose items',\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - the sort button loses the id the guide lights it by",
     "file": "bible.html",
     "find": ' onclick="window.vaultAutoSortByHand()" id="vault-sort-btn" title=',
     "replace": ' onclick="window.vaultAutoSortByHand()" title=',
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - the explanations are drawn before what he needs to do",
     "file": "bible.html",
     "find": "      + doBlock + howBlock;\n",
     "replace": "      + howBlock + doBlock;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - a section is a plain block, not a collapsible fold",
     "file": "bible.html",
     "find": "          return '<details class=\"vgd-sec\" data-sec=\"' + s.key + '\"><summary>'",
     "replace": "          return '<details class=\"vgd-sec\" data-sec=\"' + s.key + '\" open><summary>'",
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - the guide remembers its step in a store",
     "file": "bible.html",
     "find": "    var el = light(it ? it.target : null, it ? it.alt : null);\n",
     "replace": "    try { window.LSR.setItem('d2r_vaultGuideStep', String(i)); } catch (eW) {}\n    var el = light(it ? it.target : null, it ? it.alt : null);\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - the reveal shuts MOVE TASKS through the call that remembers it",
     "file": "bible.html",
     "find": "window.vaultTasksTog(false, true);\n        if (typeof window.vaultAdvTab === 'function')",
     "replace": "window.vaultTasksTog(false);\n        if (typeof window.vaultAdvTab === 'function')",
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - the guide draws something else inside a shadow",
     "file": "bible.html",
     "find": "      + '<p class=\"vgd-h\">🎒 The Vault — guide</p>';\n",
     "replace": "      + '<p class=\"vgd-h\">🎒 The Vault — guide</p>' + (window._tvdShadow ? '<p>read only</p>' : '');\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - a guide button does a write as well as moving the view",
     "file": "bible.html",
     "find": "class=\"vgd-start\" onclick=\"window.vaultGuideGo(0)\">",
     "replace": "class=\"vgd-start\" onclick=\"window.vaultGuideGo(0);window.vaultAutoSortByHand()\">",
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - the cells per mule are a number copied into the guide, not the page's MULE_CAP",
     "file": "bible.html",
     "find": "      var cap = num('MULE_CAP'), pages = num('SHARED_PAGES');\n",
     "replace": "      var cap = 140, pages = num('SHARED_PAGES');\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - the shared stash's page count is not published for the guide",
     "file": "bible.html",
     "find": "  try { window.SHARED_PAGES = SHARED_PAGES; } catch (eSp) {}",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - a renamed locker is called by its old name",
     "file": "bible.html",
     "find": "      for (var i = 0; r && i < r.length; i++) if (r[i] && r[i].id === id && r[i].name) return String(r[i].name);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2860 - the not-yet-built items are drawn without being marked as coming",
     "file": "bible.html",
     "find": "<b>Coming</b>, not on this board yet: ",
     "replace": "Next: ",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
