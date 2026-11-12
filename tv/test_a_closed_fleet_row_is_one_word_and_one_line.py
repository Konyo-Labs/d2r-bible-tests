# -*- coding: utf-8 -*-
"""v3881 (REG-3395) - A CLOSED FLEET ROW SAYS ITS PC IN ONE DIABLO WORD AND ONE SHORT LINE; THE RIVER'S DETAIL OPENS ON A CLICK.

His words, 11-07 21:12, on his live Fleet: "maybe this information collapsed for the fleet? i already mentioned this it gets
cutoff a little bit and needs a better structural design to it with diablo ii language and human language short and simple
and to the point all the desciptions should be in the state of the console we mentioned or collapsed or better hidden".
MEASURED the same evening, each PC's own live /api/fleet (the Mac, the work ALT and the old ALT, read over SSH) drawn with
v3880's code in the 227px rail: the three views agreed row for row, and a CLOSED row still ran 5-8 lines - import progress,
"river stuck", "locks shut - until GitHub's proofs land", "3 shut: frame release - vault sweep - vault apply", "572 reels wait
on the locks" - a 745px list for six PCs. v3880 had already given every PC its word (_pcStatus: ready for battle / healing /
wounded / in town / lost) in the hover card, the Fleet header and the State panel; the row itself never said it.

Now a closed row is its name line plus ONE line: the word, then the one thing it is about - a wounded PC's first wound (a
blind gate leads: it keeps every lock shut whatever the PC proves next), "+N" for the rest, and what is healing it (importing
proofs ~26 min / proving 8 ~12 min); "off since 18:10" for a PC in town (the Grok CLI's cold look could not
tell "IN TOWN" meant switched off, so the plain words ride beside it). The chips draw on an OPEN row (one click) and the State
panel keeps every wound. Same live data after: 2-3 lines a row, a ~400px list. A wounded PC still reads WOUNDED closed, so a
hidden chip never lets a dark PC read healthy (v2249 / v2283 / v2296); a brief that cannot be read leaves the chips showing.

Drives the page's own _pcStatus / _fleetBriefLine / _fleetBriefHtml in node (only the parts reader is stubbed, as REG-3372's
law does). The pixels: test_the_fleet_row_keeps_its_name_whole renders closed rows (brief inked, chips not) and open rows
(every chip inked). RED_PROOF below. [[visual-regression-detector]] [[unknown-stays-unknown]]

v3883 (#116 - GrokBot's v3881 look said STILL): "one line" was a claim the pixels refused. MEASURED on his live Fleet with
the Mac's fonts (scrollWidth of the real brief): the box is 303px at 1512, 213px at 1120, 193px at 1024, and "WOUNDED 2
gates blind +2 · importing proofs ~15 min" needs 465px - it wrapped mid-phrase ("~15 / min") under a stranded middot; at
1024 the name wrapped too ("Konyo · ALT" got 97px of the 115 it needs beside "differs"). No wording of word + wound + what
heals it fits 213px (the shortest needs 278), and a one-line clamp tried first CUT the ETA off ("WOUNDED 2 blind ·…") - his
own complaint was "it gets cutoff". So the brief is a wrapping row of WHOLE units (the word, the wound, what heals it), the
gap the separator: a unit that does not fit moves to the next line whole, never split, never cut. The words are the short
ones (ONE wound, "2 blind", "importing"). (A 1024 window can still wrap a NAME beside its tally word - v3884.)
"""
import io
import json
import os
import re
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
import js_strip  # noqa: E402  - the laws' ONE comment stripper (test_one_comment_stripper_for_the_laws)
NODE = shutil.which("node") or shutil.which("nodejs")
UI_PATH = os.path.join(ROOT, "tv", "control_ui.html")


def _ui():
    with io.open(UI_PATH, encoding="utf-8") as fh:
        return fh.read()


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start)) + len(end)]


def _p(k, f, **o):
    d = {"k": k, "f": f, "t": u" · ".join(f), "why": "w"}
    d.update(o)
    return d


WELL = [_p("films", ["window capture", "1m ago"]), _p("river", ["flowing"]), _p("stuck", ["none"]),
        _p("proved", ["proved", "0 blind"]), _p("readers", ["CLAUDE reads", "GROK reads"])]


def _with(*swap):
    keys = set(x["k"] for x in swap)
    return [x for x in WELL if x["k"] not in keys] + list(swap)


CURRENT = {"census": "current", "blind": 0, "owed": 0}
CASES = {
    "ready": {"parts": WELL, "heart": CURRENT},
    # v3887 (REG-3475) - his Mac 11-08: READY, current, and one safety-net find RED here that shuts all nine routes, no lock
    "readynet": {"parts": WELL, "heart": dict(CURRENT, netFinds=[{"gate": "test_a_parallel_proof_is_the_same_proof", "verdict": "RED",
                 "seen": 3, "shuts": {"locks": [], "routes": ["chronicle.runeword", "chronicle.set", "chronicle.unique", "fleet.runewords",
                 "fleet.sets", "fleet.uniques", "roster.runeword", "roster.set", "roster.unique"]}}])},
    # an older console's find carries no `shuts`: the closed row still names it, in the words that never under-say the harm
    "readynetold": {"parts": WELL, "heart": dict(CURRENT, netFinds=[{"gate": "test_x", "verdict": "BLIND"}])},
    "healing": {"parts": _with(_p("proved", ["proof out of date", "0 blind", "8 laws owed"], warn=True)),
                "heart": {"census": "stale", "blind": 0, "owed": 8, "ratePerH": 40, "etaS": 720}},
    # his old ALT, 11-07 21:24: stuck, ONE blind gate, stale, importing v3879's proofs ~26 min
    "blind": {"parts": _with(_p("stuck", ["CAPTURE 572 older for 2d"], warn=True),
                             _p("proved", ["proof out of date", "1 blind"], warn=True)),
              "heart": {"census": "stale", "blind": 1, "importing": {"ver": "v3879", "done": 2800, "of": 9294, "etaS": 1560}}},
    # his work ALT: stuck, stale, no blind gate, importing ~82 min
    "importing": {"parts": _with(_p("stuck", ["CAPTURE 1 older for 1d"], warn=True),
                                 _p("proved", ["proof out of date", "0 blind"], warn=True)),
                  "heart": {"census": "stale", "blind": 0, "importing": {"ver": "v3879", "done": 890, "of": 9294, "etaS": 4920}}},
    # v3882 - an import gone quiet (its last reading 3+ min old) says so, never its stale ETA (Dean 11-08: "~5 min" for an hour)
    "importquiet": {"parts": _with(_p("stuck", ["CAPTURE 1 older for 1d"], warn=True),
                                  _p("proved", ["proof out of date", "0 blind"], warn=True)),
                    "heart": {"census": "stale", "blind": 0, "importing": {"ver": "v3880", "done": 3029, "of": 4396, "etaS": None,
                                                                         "quietS": 200}}},
    # an import that has LANDED is not "importing" any more
    "landed": {"parts": _with(_p("stuck", ["CAPTURE 1 older for 1d"], warn=True),
                              _p("proved", ["proof out of date", "0 blind"], warn=True)),
               "heart": {"census": "stale", "blind": 0, "importing": {"ver": "v3879", "landed": True, "etaS": 60}}},
    # stuck while proving: the wound leads, the healing follows
    "stuckproving": {"parts": _with(_p("stuck", ["PRINTER 3 older for 2d"], warn=True),
                                    _p("proved", ["proof out of date", "0 blind", "129 laws owed"], warn=True)),
                     "heart": {"census": "stale", "blind": 0, "owed": 1290, "ratePerH": 90, "etaS": 51840}},
    "town": {"parts": _with(_p("stuck", ["PRINTER 3 older for 2d"], warn=True)), "off": {"since": "18:10"}, "heart": CURRENT},
    # off since an earlier day: the date, not the clock (GrokBot's row, "since Oct 28 00:24", wrapped to a second line)
    "townold": {"parts": WELL, "off": {"since": "Oct 28 00:24"}, "heart": CURRENT},
    "lost": {"parts": [_p(k, ["UNKNOWN"], unk=True) for k in ("films", "river", "stuck", "proved")], "heart": None},
    "many": {"parts": _with(_p("stuck", ["STATION 1 older for 30d"], warn=True), _p("picker", ["broken"], warn=True),
                            _p("readers", ["CLAUDE off", "GROK reads"], warn=True)),
             "heart": {"census": "current", "blind": 2}},
    # a parts reader that throws is caught by _pcStatus itself: LOST, never ready
    "throws": {"parts": "THROW", "heart": CURRENT},
    # the proof wound alone: said once, in the words the parts gave ("proof out of date"), or the census word ("proof stale")
    "proofonly": {"parts": _with(_p("proved", ["proof out of date", "0 blind"], warn=True)), "heart": {"census": "stale", "blind": 0}},
    "proofword": {"parts": [x for x in WELL if x["k"] != "proved"], "heart": {"census": "stale", "blind": 0}},
    # v3896 (REG-3671) - Dean 11-11: proving 67 checks while every pull was refused by local edits, 181 behind
    "pullstuck": {"parts": _with(_p("proved", ["proof out of date", "0 blind", "67 laws owed"], warn=True)),
                  "heart": {"census": "stale", "blind": 0, "owed": 67, "ratePerH": 5, "etaS": 48240, "locksShut": []},
                  "pull": {"can": False, "behind": 181, "why": "local tracked edits - a fast-forward would not be safe here"}},
}


def _drive(cases, status_throws=False):
    src = _ui()
    meter = _cut(src, "  var _proofMeterFacts = function (hs) {", "\n  };\n")
    meter += "\n" + _cut(src, "  var _fleetNetShut = function (finds) {", "\n  };\n") + "\nwindow._fleetNetShut = _fleetNetShut;\n"
    block = _cut(src, "  var _PC_WORD = {", "  window._fleetBriefHtml = _fleetBriefHtml;\n")
    js = ("var CASES = " + json.dumps(cases) + ";\nvar window = {};\n"
          "function escC(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;'); }\n"
          "function _fleetName(m){ return m.nickname || m.machine; }\n"
          "function _fleetSysParts(m){ if (CASES[m.machine].parts === 'THROW') throw new Error('x'); return CASES[m.machine].parts; }\n"
          "function _fleetOffline(m){ return CASES[m.machine].off || null; }\n"
          + meter + "\n" + block + "\n"
          + ("_pcStatus = function () { throw new Error('status'); };\n" if status_throws else "") +
          "var OUT = {};\n"
          "Object.keys(CASES).forEach(function (k) {\n"
          "  var m = { machine: k, nickname: 'PC ' + k, system: { river: { heart: CASES[k].heart } }, pull: CASES[k].pull };\n"
          "  var s = null; try { s = _pcStatus(m, 1000); } catch (e) { s = null; }\n"
          "  OUT[k] = { word: s && s.word, key: s && s.key, html: _fleetBriefHtml(m, 1000) };\n"
          "});\n"
          "process.stdout.write(JSON.stringify(OUT));")
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError("node could not drive the page's own functions: " + r.stderr[-800:])
    return json.loads(r.stdout)


def _brief(html):
    m = re.match(r'^<span class="fleet-brief ([\w-]+)" data-pc="(\w+)"><span class="fb-w">([^<]*)</span>'
                 r'((?:<span class="fb-t">[^<]*</span>)*)</span>$', html or "")
    if not m:
        return None
    units = re.findall(r'<span class="fb-t">([^<]*)</span>', m.group(4))
    return {"cls": m.group(1), "key": m.group(2), "word": m.group(3), "units": units, "line": u" · ".join(units)}


@unittest.skipUnless(NODE, "node is required to drive the page's own _pcStatus - UNMEASURED here, not a pass")
class AClosedRowIsOneWordAndOneLine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = _drive(CASES)
        cls.b = dict((k, _brief(v["html"])) for k, v in cls.o.items())

    def test_a_pc_whose_pull_is_refused_says_so_and_no_proof_meter_follows(self):
        """v3896 (REG-3671) - the Grok CLI read "BLOCKED not updating" over "proving 67 checks ~13.4 h" as a contradiction"""
        b = self.b["pullstuck"]
        self.assertEqual(b["word"], "blocked", b)
        self.assertEqual(b["units"], ["181 behind, pull refused"], "the closed row of a PC that cannot pull: %r" % (b,))

    def test_every_brief_is_one_element_with_the_pcs_own_word(self):
        """PREMISE - every case but the throwing one drew a brief, and its word IS _pcStatus's (one source, never a copy)"""
        for k, v in self.o.items():
            if k == "throws":
                continue
            self.assertIsNotNone(self.b[k], "%s: no brief, or not one element: %r" % (k, v["html"]))
            self.assertEqual((self.b[k]["word"], self.b[k]["key"]), (v["word"], v["key"]), k)
            self.assertEqual(self.b[k]["cls"], "pcs-" + v["key"], k)

    def test_the_line_says_the_one_thing_the_word_is_about(self):
        """* THE POINT - his old ALT's and work ALT's live rows, in one line each"""
        b = self.b
        self.assertEqual(b["ready"]["line"], "all proved")              # v3883 (#116) fits 1512 whole
        self.assertEqual(b["healing"]["line"], "proving 8 checks ~12 min")   # v3884 what is proved
        self.assertEqual(b["blind"]["line"], u"1 check blind · import 2,800 of 9,294 ~26\u00a0min")   # REG-3741 the count                  # v3883 (#116) short words
        self.assertEqual(b["importing"]["line"], u"river stuck · import 890 of 9,294 ~82\u00a0min")
        self.assertEqual(b["importquiet"]["line"], u"river stuck · import 3,029 of 4,396 · no progress for 3\u00a0min")   # v3882
        self.assertEqual(b["town"]["line"], "since 18:10")           # v3883: the word itself says OFFLINE (his 11-08 ruling)
        self.assertEqual(b["townold"]["line"], "since Oct 28")
        self.assertEqual(b["lost"]["line"], "no readable report")

    def test_a_blind_gate_leads_the_wounds(self):
        """a blind gate keeps every lock shut whatever the PC proves next - the one wound that will not heal by itself"""
        self.assertTrue(self.b["blind"]["line"].startswith("1 check blind"), self.b["blind"]["line"])
        self.assertTrue(self.b["many"]["line"].startswith("2 checks blind"), self.b["many"]["line"])

    def test_each_unit_is_its_own_element(self):
        """v3883 (#116) - the word, the wound and what heals it are separate elements, so a wrap falls BETWEEN them"""
        self.assertEqual(self.b["blind"]["units"], ["1 check blind", "import 2,800 of 9,294 ~26\u00a0min"])
        self.assertEqual(self.b["stuckproving"]["units"][-1], "proving 1,290 checks ~14.4 h")
        self.assertEqual(self.b["ready"]["units"], ["all proved"])
        self.assertEqual(self.b["importquiet"]["units"], ["river stuck", u"import 3,029 of 4,396 · no progress for 3\u00a0min"])

    def test_the_line_names_one_wound_and_no_count_of_the_rest(self):
        """v3883 (#116) - ONE wound: "+N" spent 3 of a 25-37 character line on what the open row lists"""
        for k, x in self.b.items():
            if x:
                self.assertNotRegex(x["line"], r"\+\d", "%s: %r" % (k, x["line"]))
                self.assertNotIn("gates blind", x["line"], k)
                self.assertNotIn("importing proofs", x["line"], k)

    def test_what_heals_it_follows_the_wound_and_a_landed_import_is_not_importing(self):
        self.assertEqual(self.b["stuckproving"]["key"], "wounded")
        self.assertTrue(self.b["stuckproving"]["line"].endswith(u"· proving 1,290 checks ~14.4 h"), self.b["stuckproving"]["line"])
        self.assertNotIn("import", self.b["landed"]["line"])

    def test_the_proof_wound_never_says_proof_twice(self):
        self.assertNotIn("proof: proof", " ".join(x["line"] for x in self.b.values() if x))
        self.assertEqual(self.b["proofonly"]["line"], "proof out of date")
        self.assertEqual(self.b["proofword"]["line"], "proof stale")

    def test_the_line_stays_short_and_an_offline_pc_wears_no_live_wound(self):
        for k, x in self.b.items():
            if x:
                self.assertLessEqual(len(x["line"]), 64, "%s: %r" % (k, x["line"]))
        self.assertEqual(self.b["town"]["key"], "town")
        self.assertNotIn("stuck", self.b["town"]["line"])

    def test_a_ready_pc_with_a_safety_net_find_says_it_on_the_closed_row(self):
        """* v3887 (REG-3475) - his Mac read "READY all proved" while a find was RED here and shut nine routes"""
        self.assertEqual(self.b["readynet"]["key"], "ready", "PREMISE: the word is not READY - the case is not his Mac's")
        self.assertEqual(self.b["readynet"]["units"], ["1 law red", "shuts 9 routes"])
        self.assertNotIn("all proved", self.b["readynet"]["line"])
        self.assertEqual(self.b["readynetold"]["units"], ["1 law blind", "its locks shut"], "an older find reads healthy or under-says")
        self.assertEqual(self.b["ready"]["line"], "all proved", "a READY PC with no find lost its line")

    def test_an_unreadable_pc_is_lost_never_ready(self):
        self.assertEqual((self.b["throws"]["key"], self.b["lost"]["key"]), ("lost", "lost"))

    def test_a_status_that_throws_draws_no_brief_so_the_chips_stay(self):
        """the CSS hides the chips only AFTER a brief (sibling rule): no brief = the closed row keeps its chips"""
        o = _drive({"ready": CASES["ready"], "blind": CASES["blind"]}, status_throws=True)
        self.assertEqual([o["ready"]["html"], o["blind"]["html"]], ["", ""])


class TheRowWearsItAndTheChipsOpenOnAClick(unittest.TestCase):

    def test_the_brief_wraps_whole_units_never_a_cut_and_never_nowrap(self):
        """* v3883 (#116) THE POINT - his live Fleet at 1024: "importing proofs ~15 / min" split under a stranded middot"""
        code = js_strip.strip_js_comments(_ui())
        rule = _cut(code, ".fleet-row > .fleet-brief { grid-column: 1 / -1;", "}")
        for want in ("display: flex;", "flex-wrap: wrap;", "column-gap: 1ch;"):
            self.assertIn(want, rule, "the closed brief is not a wrapping row of whole units: %r missing" % want)
        for banned in ("nowrap", "line-clamp", "ellipsis", "overflow: hidden"):
            self.assertNotIn(banned, rule, "%r: the brief may never cut its words (his 'it gets cutoff') nor pin the row" % banned)


    def test_the_row_draws_the_brief_after_its_word_and_before_its_chips(self):
        src = _ui()
        body = _cut(src, "      var _row = function (m, online) {", "\n      };\n")
        i, j, k = (body.find("escC(w.w) + '</span>'"), body.find("window._fleetBriefHtml(m)"),
                   body.find("_fleetRowChips(m, heard)"))
        self.assertTrue(0 <= i < j < k, "the brief is not between the row's word and its chips: %r" % ((i, j, k),))

    def test_a_closed_row_hides_its_chips_only_after_a_brief(self):
        code = js_strip.strip_js_comments(_ui())
        self.assertEqual(code.count(".fleet-row:not(.fleet-open) > .fleet-brief ~ .fleet-chips { display: none; }"), 1)
        self.assertIn(".fleet-row > .fleet-brief { grid-column: 1 / -1;", code)

    def test_the_closed_row_fits_two_lines_at_1512(self):
        """v3887 (REG-3473) - GrokBot's v3885 look at 1512: Konyo · ALT, OLD PC ALT and Konyo at 88px (3 lines); MEASURED on his live
        Fleet payload in a private console, every closed row there is 48px (two lines) with the brief on the whole row, the
        name line's eyes at 1em with 2px margins, 3px gaps and "import". Font metrics decide a fit, so the law pins the CSS
        that bought it (a geometry pin would be measuring CI's fonts, not his)."""
        code = js_strip.strip_js_comments(_ui())
        self.assertIn("column-gap: 3px; row-gap: 1px; padding: 3px 0;", _cut(code, "  .fleet-row { display: grid;", "}"))
        self.assertIn(".fleet-row > .fleet-brief { grid-column: 1 / -1;", code)
        self.assertIn(".fleet-row > b > .fleet-shadow svg, .fleet-row > b > .fleet-winview svg { width: 1em; }", code)
        self.assertIn(".fleet-row > b > .fleet-shadow { margin-right: 2px; }", code)
        self.assertIn(".fleet-row > b > .fleet-winview { margin: 0 2px 0 0; }", code)

    def test_a_closed_rows_tally_tag_waits_for_the_open_row(self):
        """v3889 (REG-3503, his 11-09 call "Tag moves to open row") - MEASURED on his live Fleet at 1120: the tally tag shared the
        name line and Konyo · ALT ran 3 lines, OLD PC ALT 5; after, every name is one line at 1512 / 1120 / 913. A closed row with
        a brief hides the tag; a row with no brief keeps it (as it keeps its chips); the render gate measures the tag where it
        is drawn, so a hidden one is never read as a collapse."""
        code = js_strip.strip_js_comments(_ui())
        self.assertIn(".fleet-row:not(.fleet-open):has(> .fleet-brief) > .fleet-word { display: none; }", code)
        import render_check as _RC
        sel = _RC.TARGETS["advanced-fleet"]["sel"]
        self.assertIn("#fleet-list .fleet-row.fleet-open > .fleet-word", sel)
        self.assertIn("#fleet-list .fleet-row:not(:has(> .fleet-brief)) > .fleet-word", sel)
        self.assertNotIn("#fleet-list .fleet-word,", sel, "the gate measures a tag the closed row no longer draws")

    def test_the_open_rows_vault_line_takes_its_own_line(self):
        """the both-sides render: the vault line wrapped six lines of ~16 characters beside the eyes in the 227px rail"""
        code = js_strip.strip_js_comments(_ui())
        self.assertIn(".fleet-row.fleet-open > .fleet-open-eyes { flex-wrap: wrap; row-gap: 4px; }", code)
        self.assertIn(".fleet-open-eyes > .fleet-vault { flex-basis: 100%; }", code)


RED_PROOF = [
    {"why": "v3889 (REG-3503) - a closed row's tally tag takes the name's line again (3-5 lines at 1120)",
     "file": "tv/control_ui.html",
     "find": "  .fleet-row:not(.fleet-open):has(> .fleet-brief) > .fleet-word { display: none; }\n",
     "replace": "",
     "matches": 1},
    {"why": "v3889 (REG-3503) - the render gate measures every row's tag, hidden or not (a hidden tag reads as a collapse)",
     "file": "tv/render_check.py",
     "find": "\"#fleet-list .fleet-row.fleet-open > .fleet-word, #fleet-list .fleet-row:not(:has(> .fleet-brief)) > .fleet-word, \"",
     "replace": "\"#fleet-list .fleet-word, \"",
     "matches": 1},
    {"why": "v3887 (REG-3475) - a READY row says 'all proved' over a safety-net find that shuts nine routes",
     "file": "tv/control_ui.html",
     "find": "      if (_nf.length) {\n        var _ns = (typeof window._fleetNetShut",
     "replace": "      if (false) {\n        var _ns = (typeof window._fleetNetShut",
     "matches": 1},
    {"why": "v3887 (REG-3473) - the brief starts under the name again and wraps at 1512 (303px for 338px)",
     "file": "tv/control_ui.html",
     "find": "  .fleet-row > .fleet-brief { grid-column: 1 / -1; min-width: 0;",
     "replace": "  .fleet-row > .fleet-brief { grid-column: 2 / -1; min-width: 0;",
     "matches": 1},
    {"why": "v3887 (REG-3473) - the name line's eyes are full size again and the name wraps at 1512",
     "file": "tv/control_ui.html",
     "find": "  .fleet-row > b > .fleet-shadow svg, .fleet-row > b > .fleet-winview svg { width: 1em; }\n",
     "replace": "",
     "matches": 1},
    {"why": "v3884 - a blind count says 'blind' of nothing again ('2 blind' - of what?)",
     "file": "tv/control_ui.html",
     "find": "return / gate blind$/.test(m) ? ' check blind' : ' checks blind'; }) : '';",
     "replace": "return ' blind'; }) : '';", "matches": 1},
    {"why": "v3884 - a proving count says 'proving 102' of nothing again",
     "file": "tv/control_ui.html",
     "find": "'proving ' + _n(hs.owed) + (hs.owed === 1 ? ' check' : ' checks')\n",   # v3885: the wait or the time follows on the next line
     "replace": "'proving ' + _n(hs.owed)\n", "matches": 1},
    {"why": "v3883 (#116) - the brief wraps mid-phrase again (one inline run: '~15 / min' under a stranded middot)",
     "file": "tv/control_ui.html",
     "find": "                              display: flex; flex-wrap: wrap; align-items: baseline; column-gap: 1ch; }\n",
     "replace": "                              display: inline; }\n", "matches": 1},
    {"why": "v3883 (#116) - the brief draws as ONE run again, so a wrap can split a unit",
     "file": "tv/control_ui.html",
     "find": "      + '</span>' + t.map(function (u) { return '<span class=\"fb-t\">' + escC(u) + '</span>'; }).join('') + '</span>';",
     "replace": "      + '</span>' + (t.length ? '<span class=\"fb-t\">' + escC(t.join(' \\u00b7 ')) + '</span>' : '') + '</span>';",
     "matches": 1},
    {"why": "v3883 (#116) - the closed line counts the other wounds again (+N)",
     "file": "tv/control_ui.html",
     "find": "return / gate blind$/.test(m) ? ' check blind' : ' checks blind'; }) : '';\n",
     "replace": "return / gate blind$/.test(m) ? ' check blind' : ' checks blind'; }) + (hurt.length > 1 ? ' +' + (hurt.length - 1) : '') : '';\n",   # v3884 re-anchor
     "matches": 1},
    {"why": "v3882 - a quiet import's closed row repeats a stale ETA (or says nothing) instead of how long it has been quiet",
     "file": "tv/control_ui.html", "find": "    if (imp && whole(imp.quietS) && imp.quietS > 0) {\n",   # v3900 REG-3741 re-anchor: the one import unit
     "replace": "    if (false) {\n", "matches": 1},
    {"why": "REG-3395 / v3883 - an offline PC's line no longer says since when",
     "file": "tv/control_ui.html",
     "find": "      return since ? ['since ' + since] : [];", "replace": "      return [];",   # v3883 re-anchor: OFFLINE, and since when
     "matches": 1},
    {"why": "REG-3395 - a closed row draws every river chip again (the 5-8 line rows he asked to collapse)",
     "file": "tv/control_ui.html",
     "find": "  .fleet-row:not(.fleet-open) > .fleet-brief ~ .fleet-chips { display: none; }\n", "replace": "\n", "matches": 1},
    {"why": "REG-3395 - the row never draws its PC's word",
     "file": "tv/control_ui.html",
     "find": "                + (window._fleetBriefHtml ? window._fleetBriefHtml(m) : '')", "replace": "                + ''",
     "matches": 1},
    {"why": "REG-3395 - the brief's word is a fixed word, not the PC's own (_pcStatus)",
     "file": "tv/control_ui.html",
     "find": "<span class=\"fb-w\">' + escC(s.word)", "replace": "<span class=\"fb-w\">' + escC('ready for battle')",
     "matches": 1},
    {"why": "REG-3395 - a blind gate no longer leads a wounded PC's line",
     "file": "tv/control_ui.html",
     "find": "    var hurt = s.hurt.slice().filter(function (x) { return x !== s.drainAlert; }).sort(function (a, b) { return (/ blind$/.test(b) ? 1 : 0) - (/ blind$/.test(a) ? 1 : 0); });",
     "replace": "    var hurt = s.hurt.slice().filter(function (x) { return x !== s.drainAlert; });", "matches": 1},
    {"why": "REG-3395 - the line no longer says what is healing the PC (the import)",
     "file": "tv/control_ui.html",
     "find": "    var heal = imp ? _fleetImportUnit(imp) : proving;", "replace": "    var heal = proving;",   # v3900 REG-3741 re-anchor
     "matches": 1},
    {"why": "REG-3395 - a status that throws hides the chips anyway (no brief, still hidden)",
     "file": "tv/control_ui.html",
     "find": "    if (!s || !s.word) return '';", "replace": "    if (!s || !s.word) return '<span class=\"fleet-brief\"></span>';",
     "matches": 1},
    {"why": "REG-3395 - the open row's vault line is squeezed beside the eyes again",
     "file": "tv/control_ui.html",
     "find": "  .fleet-open-eyes > .fleet-vault { flex-basis: 100%; }\n", "replace": "\n", "matches": 1},
    {"why": "v3896 (REG-3671) - a PC whose pull is refused shows its proof meter on its one line again, under BLOCKED",
     "file": "tv/control_ui.html",
     "find": "    if (typeof s.pullBehind === 'number' && s.pullBehind > 0) {\n",
     "replace": "    if (false) {\n",
     "matches": 1}
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
