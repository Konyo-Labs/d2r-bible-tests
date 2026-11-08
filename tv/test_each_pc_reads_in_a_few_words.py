# -*- coding: utf-8 -*-
"""v3880 (his 11-07 ask; GrokBot's third view #6707144313) - EACH PC READS IN A FEW WORDS, AND THE STATE PANEL SAYS THE SAME.

His words: "for fleet i just want to make this a little smoother and more UI and UX friendly and human understandable with
diablo ii language and english ... all this info that hovers i want this more organized and structured better and cleaner
... once and when they are fixed i want it smooth and logical meaning i want to understand short and to the point", and
"the State of the console when clicking the bottom left corner chiliad should be rendering all of this information
regardless right? so its all connected and joined and logical".

GrokBot looked at his live Fleet (six rows hovered) and the State panel, quoted the worst lines (a run-on NATIVE tooltip
that hid the styled card; a State panel whose THE FLEET said only "this machine | current"), and picked the OPERATOR
structure with the PLAYER's words and the MINIMALIST's header. tv/control_ui.html now has ONE function, _pcStatus, that
reads a PC off _fleetSysParts' parts, the proof meter and the presence stamp, and says it as:

    ready for battle · healing · wounded · in town · lost      + up to three things broken + what happens next

Pinned here, driving the page's own _pcStatus / _pcStatusHtml / _pcHeader in node (only the parts reader is stubbed):
  * a fixed PC is ONE word and nothing else; a broken one names where and what next;
  * a PC with nothing readable is LOST and never "ready" - nor is one whose proof census cannot be read;
  * an OFFLINE PC is IN TOWN and its last report's faults are never painted as live wounds;
  * stuck while proving is WOUNDED (the wound outranks the healing) and says it heals itself;
  * the hover card, the Fleet header and the State panel all draw THIS function - one source, so they cannot disagree;
  * the row's verdict word no longer carries the run-on paragraph as a native tooltip (it hid the styled card).
RED_PROOF below. [[unknown-stays-unknown]] [[copy-drift]] [[stale-reading]]
"""
import io
import json
import os
import shutil
import subprocess
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
NODE = shutil.which("node") or shutil.which("nodejs")
UI_PATH = os.path.join(ROOT, "tv", "control_ui.html")


def _ui():
    with io.open(UI_PATH, encoding="utf-8") as fh:
        return fh.read()


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i:j + len(end)]


# a part as _fleetSysParts makes one: {k, f, t, warn?, unk?, why}
def _p(k, f, **o):
    d = {"k": k, "f": f, "t": u" · ".join(f), "why": "w"}
    d.update(o)
    return d


WELL = [_p("films", ["window capture", "1m ago"]), _p("river", ["flowing"]), _p("stuck", ["none — every station is draining"]),
        _p("proved", ["proved", "0 blind"]), _p("readers", ["CLAUDE reads", "GROK reads"])]


def _drive(cases):
    """cases: {name: {"parts": [...] | "THROW", "off": null|{since}, "heart": {...}}} -> {name: {status, html}} + header"""
    src = _ui()
    fn = _cut(src, "  var _proofMeterFacts = function (hs) {", "\n  };\n")
    block = _cut(src, "  var _PC_WORD = {", "  window._PC_ORDER = _PC_ORDER;\n")
    js = ("var CASES = " + json.dumps(cases) + ";\nvar CUR = null;\n"
          "var window = {};\n"
          "function escC(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;'); }\n"
          "function _fleetName(m){ return m.nickname || m.machine; }\n"
          "function _fleetSysParts(m){ if (CASES[m.machine].parts === 'THROW') throw new Error('x'); return CASES[m.machine].parts; }\n"
          "function _fleetOffline(m){ return CASES[m.machine].off || null; }\n"
          + fn + "\n" + block + "\n"
          "var OUT = {}, ALL = [];\n"
          "Object.keys(CASES).forEach(function (k) {\n"
          "  var m = { machine: k, nickname: 'PC ' + k, system: { river: { heart: CASES[k].heart } } };\n"
          "  ALL.push(m);\n"
          "  OUT[k] = { status: _pcStatus(m, 1000), html: _pcStatusHtml(m, 1000, { name: m.nickname }) };\n"
          "});\n"
          "OUT.__header = _pcHeader(ALL, 1000);\n"
          "OUT.__headerHtml = _pcHeaderHtml(ALL, 1000);\n"
          "process.stdout.write(JSON.stringify(OUT));")
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError("node could not drive the page's own functions: " + r.stderr[-800:])
    return json.loads(r.stdout)


CURRENT = {"census": "current", "blind": 0}
PROVING = {"census": "stale", "blind": 0, "owed": 15, "ratePerH": 18, "etaS": 3060}

CASES = {
    "well": {"parts": WELL, "off": None, "heart": CURRENT},
    "proving": {"parts": [x for x in WELL if x["k"] != "proved"] + [_p("proved", ["proof out of date", "0 blind", "15 laws owed"], warn=True)],
                "off": None, "heart": PROVING},
    "stuck": {"parts": [x for x in WELL if x["k"] not in ("stuck", "proved")]
              + [_p("stuck", ["PRINTER 3 older for 2d", "ROUTED 36 older for 2d"], warn=True),
                 _p("proved", ["proof out of date", "3 blind", "129 laws owed"], warn=True)],
              "off": None, "heart": {"census": "stale", "blind": 3, "owed": 129, "ratePerH": 8.9, "etaS": 51840}},
    "away": {"parts": [x for x in WELL if x["k"] != "stuck"] + [_p("stuck", ["PRINTER 3 older for 2d"], warn=True)],
             "off": {"since": "06:28"}, "heart": CURRENT},
    "silent": {"parts": [_p(k, ["UNKNOWN", "an older build"], unk=True) for k in ("films", "river", "stuck", "proved")],
               "off": None, "heart": None},
    "broken": {"parts": "THROW", "off": None, "heart": CURRENT},
    # the parts reader answered NOTHING while the census reads current: still lost (the census alone is not a report)
    "empty": {"parts": [], "off": None, "heart": CURRENT},
    "nocensus": {"parts": [x for x in WELL if x["k"] != "proved"] + [_p("proved", ["UNKNOWN"], unk=True)],
                 "off": None, "heart": {"census": "unknown"}},
    "many": {"parts": [x for x in WELL if x["k"] not in ("stuck", "readers")]
             + [_p("stuck", ["STATION 1 older for 30d"], warn=True), _p("repairs", ["2 failed"], warn=True),
                _p("picker", ["broken", "count failed"], warn=True), _p("readers", ["CLAUDE off", "GROK reads"], warn=True)],
             "off": None, "heart": {"census": "current", "blind": 2}},
    # its repair book's leftovers are code's, not a wound: still ready, with a dim "code owes" line
    "owed": {"parts": WELL + [_p("repairs", ["8 unknown faults"], warn=True)], "off": None, "heart": CURRENT},
    "tagged": {"parts": [x for x in WELL if x["k"] != "stuck"] + [_p("stuck", ["<b>x</b> & y"], warn=True)],
               "off": None, "heart": CURRENT},
}


@unittest.skipUnless(NODE, "node is required to drive the page's own _pcStatus - UNMEASURED here, not a pass")
class EachPcInAFewWords(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = _drive(CASES)

    def _s(self, k):
        return self.out[k]["status"]

    def test_a_fixed_pc_is_one_word_and_nothing_else(self):
        s = self._s("well")
        self.assertEqual((s["key"], s["word"]), ("ready", "ready"))   # v3883 plain words
        self.assertEqual(s["hurt"], [], "a PC with nothing broken still lists something broken")
        self.assertEqual(s["next"], "", "a PC with nothing to do still says what happens next")

    def test_proving_is_healing_and_says_nothing_is_owed_by_him(self):
        s = self._s("proving")
        self.assertEqual(s["key"], "healing")
        self.assertIn("15 laws owed", s["next"])
        self.assertIn("nothing for you to do", s["next"])

    def test_stuck_while_proving_is_wounded_and_names_where(self):
        """* THE POINT (his OLD PC ALT, GrokBot's example): the wound outranks the healing, and it says where and what next"""
        s = self._s("stuck")
        self.assertEqual(s["key"], "wounded")
        self.assertTrue(any(h.startswith("river stuck: PRINTER 3 older for 2d") for h in s["hurt"]), s["hurt"])
        self.assertIn("3 gates blind", s["hurt"])
        self.assertIn("it heals itself", s["next"])
        self.assertIn("129 laws owed", s["next"])

    def test_what_code_owes_is_a_dim_line_never_a_wound(self):
        """his own console read WOUNDED for 8 eagle faults no repair is known for - those are CODE's (GrokBot: owed by code)"""
        s = self._s("owed")
        self.assertEqual(s["key"], "ready", "code's leftovers made a PC wounded")
        self.assertEqual(s["owed"], [u"the code\u2019s to fix, not yours: 8 unknown faults"])
        self.assertIn(u'<span class="pcs-owed">the code\u2019s to fix, not yours: 8 unknown faults</span>', self.out["owed"]["html"])

    def test_an_offline_pc_is_in_town_and_its_last_faults_are_not_live_wounds(self):
        s = self._s("away")
        self.assertEqual((s["key"], s["word"]), ("town", "offline"))   # v3883 plain words
        self.assertEqual(s["hurt"], [], "an offline PC's last report was painted as live wounds")
        self.assertIn("06:28", s["next"])

    def test_nothing_readable_is_lost_never_ready(self):
        for k in ("silent", "broken", "nocensus", "empty"):
            with self.subTest(case=k):
                self.assertEqual(self._s(k)["key"], "lost", "%s read as %s" % (k, self._s(k)["key"]))

    def test_the_fleet_words_are_plain_never_diablo(self):
        """v3883 - HIS RULING 11-08 ~09:46: "intown is not proper wording or the correct language for offline.. simply write
        OFFLINE and others like this make it more simple to the point forget about the diablo ii language when it comes to
        the fleet data". One table draws every surface's word; it holds the plain ones."""
        words = dict((k, self._s(c)["word"]) for k, c in (("ready", "well"), ("town", "away")))
        self.assertEqual(words, {"ready": "ready", "town": "offline"})
        src = io.open(UI_PATH, encoding="utf-8").read()
        i = src.index("  var _PC_WORD = {")
        table = src[i:src.index("};", i)]
        for diablo in ("in town", "ready for battle", "wounded", "healing", "'lost'"):
            self.assertNotIn("w: " + (diablo if diablo.startswith("'") else "'%s'" % diablo), table,
                             "a Diablo word is back in the Fleet's table: %r" % diablo)
        for plain in ("'ready'", "'updating'", "'blocked'", "'offline'", "'unknown'"):
            self.assertIn("w: " + plain, table)

    def test_the_lines_are_one_element_capped_and_escaped(self):
        h = self.out["many"]["html"]
        self.assertTrue(h.startswith('<div class="pcs pcs-wounded">') and h.endswith("</div>"), h[:80])
        self.assertEqual(h.count("<div"), 1, "the status is not ONE element a reader or a law can lift whole")
        self.assertEqual(h.count('class="pcs-hurt"'), 3, "more than three wounds drawn on the card")
        self.assertIn("+1 more", h)
        self.assertIn(u'class="pcs-owed">the code\u2019s to fix, not yours: 2 failed', h)
        t = self.out["tagged"]["html"]
        self.assertNotIn("<b>", t)
        self.assertIn("&lt;b&gt;x&lt;/b&gt; &amp; y", t)

    def test_the_header_counts_each_word_worst_first(self):
        hd = self.out["__header"]
        self.assertEqual(hd, u"11 PCs: 3\u00a0blocked · 1\u00a0updating · 4\u00a0unknown · 1\u00a0offline · 2\u00a0ready")

    def test_the_fleet_header_draws_each_fact_as_its_own_unit(self):
        """* v3887 (REG-3476) - no separator glyph to strand; the units are the header's own facts, in its order"""
        import re
        h = self.out["__headerHtml"]
        self.assertNotIn(u"\u00b7", h, "a separator glyph is drawn - it strands at a wrapped line's end")
        units = re.findall(r'<span class="pcs-h-[nf]">([^<]*)</span>', h)
        self.assertEqual(units, [u"11 PCs:", u"3\u00a0blocked", u"1\u00a0updating", u"4\u00a0unknown", u"1\u00a0offline", u"2\u00a0ready"])
        self.assertEqual(units[0] + " " + u" · ".join(units[1:]), self.out["__header"], "the units and the State panel's line disagree")


class EverySurfaceDrawsTheOneFunction(unittest.TestCase):
    """the joins, read off the page's code (comments stripped): one function behind the card, the header and the State panel"""

    @classmethod
    def setUpClass(cls):
        import re
        cls.code = re.sub(r"/\*.*?\*/", "", _ui(), flags=re.S)

    def test_the_hover_card_leads_with_it_in_both_branches(self):
        self.assertIn("+ '</div>' + _pcStatusHtml(m, Date.now(), { max: 2 }) + '<div class=\"ftt-none\">nothing recorded'", self.code)
        self.assertIn("+ '</span></div>' + _pcStatusHtml(m, Date.now(), { max: 2 }) + seeded + (bars ||", self.code)

    def test_the_fleet_header_and_the_state_panel_draw_it(self):
        self.assertIn("+ _pcHeaderHtml(_pcAll, Date.now()) + '</div>') : '';", self.code)   # v3887 (REG-3476) - whole units
        self.assertIn("pcRows.push('<div class=\"vx-row vx-pc\">' + window._pcStatusHtml(x.m, _now, { name: x.n, max: 3, where: 'state' }) + '</div>');",
                      self.code)
        self.assertIn("+ _vxSection('EVERY PC' + (_pcHead ? ' \\u2014 ' + _pcHead : ''), pcRows)", self.code)

    def test_the_fleet_header_is_whole_units_and_no_separator_glyph(self):
        """v3887 (REG-3476) - the 1512 render of his live Fleet: "6 PCs: 3 blocked · 2 offline ·" / "1 ready" - a middot stranded
        at a wrapped line's end. Each fact is its own element, the gap is the separator, and the text is the same facts."""
        import re
        code = self.code
        rule = code[code.index("  .pcs-head { margin: 2px 0 6px;"):]
        rule = rule[:rule.index("}") + 1]
        for want in ("display: flex;", "flex-wrap: wrap;", "column-gap: 1.4ch;"):
            self.assertIn(want, rule, "the Fleet header is not a wrapping row of whole units: %r missing" % want)
        self.assertNotIn("nowrap", rule)

    def test_the_row_word_carries_no_run_on_native_tooltip(self):
        """GrokBot's worst line #1: a hovered [title] hides the styled card, so the paragraph was what he met first"""
        self.assertNotIn("+ ' title=\"' + escC(w.t + (plain ? ('  \\u2014  ' + plain) : '')) + '\">'", self.code)
        self.assertIn("+ ' aria-label=\"' + escC(w.w + ' \\u2014 ' + w.t + (plain ? ('  \\u2014  ' + plain) : '')) + '\">'",
                      self.code)


class TheOpenRowStaysBalanced(unittest.TestCase):
    """v3881 (his 11-07 screenshot: Dean's open row wrapped its vault line into a narrow column beside an eyes box stretched
    four lines tall). MEASURED in Chrome at his 1120x628: the eyes button was 56x70 (stretched to the text) and is 56x24."""

    def test_the_eyes_keep_their_size_beside_a_vault_line_that_takes_the_width(self):
        import re
        code = re.sub(r"/\*.*?\*/", "", _ui(), flags=re.S)
        self.assertIn(".fleet-row.fleet-open > .fleet-open-eyes { align-items: center; gap: 10px; }", code)
        self.assertIn(".fleet-open-eyes > .fleet-vault { flex: 1 1 auto; min-width: 0; }", code)
        self.assertIn(".fleet-open-eyes > .fleet-hd-eyes { flex: 0 0 auto; align-self: center; }", code,
                      "the eyes stretch to the vault line's height again")


RED_PROOF = [
    {"why": "v3887 (REG-3476) - the Fleet header is one joined string again (a middot strands at a wrapped line's end)",
     "file": "tv/control_ui.html",
     "find": "THE STATE OF THIS CONSOLE\">' + _pcHeaderHtml(_pcAll, Date.now()) + '</div>') : '';",
     "replace": "THE STATE OF THIS CONSOLE\">' + escC(_pcHeader(_pcAll, Date.now())) + '</div>') : '';",
     "matches": 1},
    {"why": "v3887 (REG-3476) - the header's units are drawn joined by a middot",
     "file": "tv/control_ui.html",
     "find": "      + u.bits.map(function (b) { return '<span class=\"pcs-h-f\">' + escC(b) + '</span>'; }).join('');",
     "replace": "      + u.bits.map(function (b) { return '<span class=\"pcs-h-f\">' + escC(b) + '</span>'; }).join(' \u00b7 ');",
     "matches": 1},
    {"why": "v3884 - the header can split a count from its word again ('... 3 offline · 1' / 'ready' at 1512)",
     "file": "tv/control_ui.html",
     "find": "return n[k] + '\\u00a0' + _PC_WORD[k].w; });", "replace": "return n[k] + ' ' + _PC_WORD[k].w; });", "matches": 1},
    {"why": "v3883 - the Fleet says IN TOWN again for an offline PC (his 11-08 ruling: simply write OFFLINE)",
     "file": "tv/control_ui.html",
     "find": "    town:    { w: 'offline',          c: 'pcs-town',", "replace": "    town:    { w: 'in town',          c: 'pcs-town',",
     "matches": 1},
    {"why": "v3883 - the Fleet says READY FOR BATTLE again (his 11-08 ruling: forget the Diablo language for fleet data)",
     "file": "tv/control_ui.html",
     "find": "    ready:   { w: 'ready',            c: 'pcs-ready',", "replace": "    ready:   { w: 'ready for battle', c: 'pcs-ready',",
     "matches": 1},
    {"why": "v3881 - the open row's eyes button stretches to the wrapped vault line again (his 11-07 screenshot)",
     "file": "tv/control_ui.html",
     "find": "  .fleet-open-eyes > .fleet-hd-eyes { flex: 0 0 auto; align-self: center; }\n", "replace": "\n", "matches": 1},
    {"why": "v3880 - an offline PC's last report is painted as live wounds again",
     "file": "tv/control_ui.html",
     "find": "      key = 'town'; hurt = [];\n", "replace": "      key = 'town';\n", "matches": 1},
    {"why": "v3880 - a PC with nothing readable reads as ready for battle",
     "file": "tv/control_ui.html",
     "find": "    } else if (!parts || !known) {\n      key = 'lost';", "replace": "    } else if (!parts) {\n      key = 'lost';",
     "matches": 1},
    {"why": "v3880 - a PC whose proof census cannot be read reads as ready for battle",
     "file": "tv/control_ui.html",
     "find": "    } else if (!hs || !hs.census || hs.census === 'unknown') {\n      key = 'lost';",
     "replace": "    } else if (false) {\n      key = 'lost';", "matches": 1},
    {"why": "v3880 - stuck while proving reads as healing (the wound hidden under the healing)",
     "file": "tv/control_ui.html",
     "find": "    } else if (hurt.length) {\n      key = 'wounded';", "replace": "    } else if (hurt.length && !proving) {\n      key = 'wounded';",
     "matches": 1},
    {"why": "v3880 - the hover card stops leading with the PC's status",
     "file": "tv/control_ui.html",
     "find": "          + '</span></div>' + _pcStatusHtml(m, Date.now(), { max: 2 }) + seeded + (bars ||",
     "replace": "          + '</span></div>' + seeded + (bars ||", "matches": 1},
    {"why": "v3880 - the State panel stops drawing every PC with the Fleet's own function",
     "file": "tv/control_ui.html",
     "find": "window._pcStatusHtml(x.m, _now, { name: x.n, max: 3, where: 'state' })", "replace": "''", "matches": 1},
    {"why": "v3880 - the row word's run-on paragraph is a native tooltip again (it hides the styled card)",
     "file": "tv/control_ui.html",
     "find": "                + ' aria-label=\"' + escC(w.w + ' \\u2014 ' + w.t + (plain ? ('  \\u2014  ' + plain) : '')) + '\">'",
     "replace": "                + ' title=\"' + escC(w.t + (plain ? ('  \\u2014  ' + plain) : '')) + '\">'", "matches": 1},
    {"why": "v3880 - code's leftovers (the repair book) make a PC wounded again",
     "file": "tv/control_ui.html",
     "find": "    var owed = by.repairs ? ['the code\\u2019s to fix, not yours: ' + by.repairs.t] : [];",
     "replace": "    var owed = []; if (by.repairs) hurt.push('repair book: ' + by.repairs.t);", "matches": 1},
    {"why": "v3880 - more than three wounds crowd the card",
     "file": "tv/control_ui.html",
     "find": "    s.hurt.slice(0, max).forEach(", "replace": "    s.hurt.forEach(", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
