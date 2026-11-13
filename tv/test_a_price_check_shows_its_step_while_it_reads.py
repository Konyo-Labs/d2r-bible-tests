# -*- coding: utf-8 -*-
"""Job E item 4 - card #221 (his words: "for the READING PRICE for D2JSP it should render this better and more animated and
like loading design style for it instead of it stale like it is now when clicking price check").

Before: one stale sentence ("Reading d2jsp posts dated 2026 or later for shako.") sat in the card until the answer came.
Now a price check shows a DESIGNED LOADING STATE in the console's own look - a gold band that sweeps, and the three steps
with the one it is on lit: reading the stored price -> searching d2jsp -> folding the posts - ending on the answer or an
honest UNKNOWN. The steps are TRUE, not a timer's guess: the page's first ask is ?step=plan (the stored price is read,
nothing is searched, nothing is paced); a stored answer comes straight back; "searching" means a search is due and the
search is the second ask. A stored answer that comes back at once never flashes the animation (it appears only after
D2JSP_LOAD_DELAY_MS). Check live now skips the first step and says so.
Held here: the dry plan spends no pace; the door answers "searching" before any search and only for this console's page;
the page, driven in node with a stub fetch and real timers, paints (a) no loading card for an instant stored answer,
(b) stored -> answer for a slow stored answer, (c) search -> fold -> answer for a read, (d) an honest UNKNOWN when no
reader answers; the CSS moves (keyframes), stops for prefers-reduced-motion, names no cursor and only defined tokens.
Pixels: GrokBot's scratch console at 1440 / 1120 / 901 (REPORT.md). RED_PROOF below (hand-proven red/green).
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
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
import d2jsp_price_db as P  # noqa: E402

NODE = shutil.which("node")
NOW = time.mktime(time.strptime("2026-11-13", "%Y-%m-%d"))
DAY = 86400.0


def _read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _block(src, head):
    a = src.index(head)
    start = src.index("{", a)
    depth = 0
    for k in range(start, len(src)):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[a:k + 1]
    raise AssertionError(head)


class TheFirstAskSpendsNothing(unittest.TestCase):

    def setUp(self):
        self._cr = P.checks_running
        P.checks_running = lambda env=None: False
        self.addCleanup(setattr, P, "checks_running", self._cr)
        import control_app as CA
        self.CA = CA
        self.d = tempfile.mkdtemp(prefix="price-step-")
        self.addCleanup(shutil.rmtree, self.d, True)
        db = P.empty()
        link = "https://forums.d2jsp.org/topic.php?t=4001&f=268"
        db["items"][P.key_of("Gull")] = {"item": "Gull", "readAt": NOW - 95 * DAY, "posts": {link: {
            "fg": 20, "day": "2026-08-01", "link": link, "w": 1, "perfect": False, "src": "mac", "seenAt": 0}}}
        P.save(os.path.join(self.d, "d2jsp_price_db.json"), db)
        old = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.d
        self.addCleanup(lambda: os.environ.pop("TV_HIST", None) if old is None else os.environ.__setitem__("TV_HIST", old))
        self._canon = CA._d2jsp_canon
        CA._d2jsp_canon = lambda item: P.key_of(item)
        self.addCleanup(setattr, CA, "_d2jsp_canon", self._canon)
        self._pace = dict(CA._D2JSP_REFRESH_PACE)
        CA._D2JSP_REFRESH_PACE["at"] = 0.0
        self.addCleanup(CA._D2JSP_REFRESH_PACE.update, self._pace)

    def test_the_dry_plan_says_a_search_is_due_and_spends_no_pace(self):
        dry = self.CA._d2jsp_price_check_plan("Gull", now=NOW, dry=True)
        self.assertEqual(dry["do"], "refresh", dry)
        self.assertEqual(self.CA._D2JSP_REFRESH_PACE["at"], 0.0, "the plan-only ask spent the minute's search")
        real = self.CA._d2jsp_price_check_plan("Gull", now=NOW + 1)
        self.assertEqual(real["do"], "refresh", "the search after the plan was refused its minute")
        self.assertEqual(self.CA._D2JSP_REFRESH_PACE["at"], NOW + 1)

    def test_the_door_says_searching_before_any_search_and_only_to_its_own_page(self):
        src = _read("tv/control_app.py")
        a = src.index('        if path == "/api/d2jsp_quote":')
        door = src[a:src.index('        if path == "/api/d2jsp_price_db":', a)]
        self.assertIn('_dry = (parse_qs(urlparse(self.path).query).get("step") or [""])[0] == "plan"', door)
        say = door.index('"reason": "searching"')
        self.assertLess(door.index('if _plan["do"] == "stored":'), say, "a stored answer would be called a search")
        self.assertLess(say, door.index("_d2jsp.d2jsp_quote("), "the search runs before the page is told it is searching")
        self.assertIn("            if _dry and _own_page:\n", door)


_HARNESS = r"""
var writes = [], outHtml = '';
var out = {textContent: '', querySelectorAll: function(){ return []; }};
Object.defineProperty(out, 'innerHTML', {get: function(){ return outHtml; }, set: function(v){ outHtml = v; writes.push(v); }});
var els = {'d2jsp-price-q': {value: 'shako'}, 'd2jsp-price-out': out};
var document = {getElementById: function(id){ return els[id] || null; }};
var window = {};
var searchGen = 0;
function esc(x){ return String(x).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); }
function d2jspParseSearch(v){ return {item: String(v || '').trim(), roll: null}; }
function d2jspSimilarPrice(){ return null; }
function d2jspBackendHtml(){ return ''; }
function d2jspTierCardsHtml(){ return ''; }
function d2jspEvidenceHtml(){ return ''; }
function d2jspDatabaseButton(){ return ''; }
function d2jspSearchLine(q){ return 'ANSWER ' + q.reason; }
function d2jspSearchChunks(t){ return String(t).split(',').map(function(s){ return s.trim(); }).filter(Boolean); }
var ROUTES = %s, asked = [];
function fetch(u){
  asked.push(u);
  var r = null;
  for (var k = 0; k < ROUTES.length; k++) if (u.indexOf(ROUTES[k][0]) === 0) { r = ROUTES[k]; break; }
  if (!r) return Promise.reject(new Error('404'));
  return new Promise(function(res){ setTimeout(function(){ res({json: function(){ return r[2]; }}); }, r[1]); });
}
%s
%s
%s;
setTimeout(function(){
  var seen = writes.map(function(w){ var m = /data-d2jsp-loading="([a-z]+)"/.exec(w); return m ? m[1] : (w.indexOf('ANSWER') >= 0 ? 'ANSWER' : 'other'); });
  process.stdout.write(JSON.stringify({asked: asked, seen: seen, last: outHtml, writes: writes}));
}, %d);
"""


@unittest.skipUnless(NODE, "no node - the page's price check is not driven here (UNMEASURED)")
class TheCardShowsTheStepItIsOn(unittest.TestCase):

    def _drive(self, routes, call="priceSearch()", wait=2200):
        page = _read("bible.html")
        load = page[page.index("  var D2JSP_LOAD_DELAY_MS"):page.index("  window._d2jspLoadHtml = d2jspLoadHtml;")]
        body = _block(page, "  function priceSearch(){")
        prog = _HARNESS % (json.dumps(routes), load, body, "", wait)
        prog = prog.replace("\n;\nsetTimeout", "\n" + call + ";\nsetTimeout")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        return json.loads(r.stdout)

    def _states(self, seen):
        out = []
        for s in seen:
            if not out or out[-1] != s:
                out.append(s)
        return out

    def test_an_instant_stored_answer_never_flashes_the_loading_card(self):
        got = self._drive([["/api/d2jsp_quote?step=plan&item=", 15, {"reason": "stored", "say": "fresh"}]], wait=900)
        self.assertEqual(self._states(got["seen"]), ["ANSWER"], "an instant stored answer flashed: %r" % got["seen"])
        self.assertEqual(got["asked"], ["/api/d2jsp_quote?step=plan&item=shako"], "a stored answer was searched for")

    def test_a_slow_stored_answer_shows_reading_the_stored_price_then_the_answer(self):
        got = self._drive([["/api/d2jsp_quote?step=plan&item=", 700, {"reason": "stored", "say": "fresh"}]], wait=1300)
        self.assertEqual(self._states(got["seen"]), ["stored", "ANSWER"], got["seen"])
        self.assertNotIn("d2jsp-loading", got["last"], "the card ended on the loading state")

    def test_a_read_walks_search_then_fold_then_the_answer(self):
        got = self._drive([["/api/d2jsp_quote?step=plan&item=", 10, {"reason": "searching", "plan": "refresh"}],
                           ["/api/d2jsp_quote?item=", 800, {"reason": "read", "fg": 20, "n": 4}]], wait=2200)
        self.assertEqual(got["asked"], ["/api/d2jsp_quote?step=plan&item=shako", "/api/d2jsp_quote?item=shako"])
        self.assertEqual(self._states(got["seen"]), ["search", "fold", "ANSWER"], got["seen"])
        lit = [w for w in got["writes"] if 'data-d2jsp-loading="search"' in w][0]
        self.assertIn('data-d2jsp-load-step="stored" data-state="done"', lit, "the stored read is not ticked off")
        self.assertIn('data-d2jsp-load-step="search" data-state="now" aria-current="step"', lit)
        self.assertIn('class="d2jsp-load-band"', lit, "no moving band")
        self.assertIn("Reading d2jsp posts dated 2026 or later for shako.", lit, "the card lost what it reads")
        self.assertIn("ANSWER read", got["last"])

    def test_no_reader_ends_on_an_honest_unknown(self):
        got = self._drive([["/api/d2jsp_quote?step=plan&item=", 10, {"reason": "searching", "plan": "live"}]], wait=1200)
        self.assertEqual(self._states(got["seen"])[-1], "ANSWER", got["seen"])
        self.assertIn("ANSWER unanswered", got["last"], "a check no reader answered did not end on UNKNOWN")
        self.assertNotIn("d2jsp-loading", got["last"])

    def test_check_live_now_skips_the_stored_step_and_says_so(self):
        got = self._drive([["/api/d2jsp_quote?live=1&item=", 700, {"reason": "read", "fg": 30, "n": 2}]],
                          call="priceSearch('shako')", wait=1800)
        first = [w for w in got["writes"] if "d2jsp-loading" in w][0]
        self.assertIn('data-d2jsp-load-step="stored" data-state="skip"', first)
        self.assertIn("skipped - check live now", first)
        self.assertEqual(self._states(got["seen"]), ["search", "fold", "ANSWER"], got["seen"])


class ItIsDrawnInTheConsolesOwnLook(unittest.TestCase):

    def _rules(self):
        page = _read("bible.html")
        a = page.index("    /* Job E item 4 (card #221) - the price check's loading card")
        return page, page[a:page.index("    /* Job E item 2 - \"Check live now\" beside the price line", a)]

    def test_it_moves_and_stops_when_asked(self):
        _page, css = self._rules()
        self.assertIn("@keyframes d2jsp-load-sweep", css)
        self.assertIn("animation:d2jsp-load-sweep", css, "the band does not move")
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("#tab-d2jsp .d2jsp-load-band i{animation:none", css)

    def test_no_cursor_and_only_defined_tokens(self):
        page, css = self._rules()
        self.assertNotIn("cursor", css, "the loading card sets a cursor - the console pointer is the page's own")
        code = re.sub(r"/\*[\s\S]*?\*/", " ", page)
        used = sorted(set(re.findall(r"var\(\s*(--[a-zA-Z0-9-]+)", css)))
        self.assertTrue(used, "PREMISE: the card uses the console's tokens")
        undefined = [t for t in used if not re.search(re.escape(t) + r"\s*:", code)]
        self.assertEqual(undefined, [], "an undefined token (the --warn trap): %r" % undefined)


RED_PROOF = [
    {"why": "#221 - the loading card is drawn at once (no delay), so an instant stored answer flashes it",
     "file": "bible.html",
     "find": "loadShown = true; paintLoad(); } }, D2JSP_LOAD_DELAY_MS)",
     "replace": "loadShown = true; paintLoad(); } }, 0)",
     "matches": 1},
    {"why": "#221 - the page skips the plan ask and searches at once (the steps are a guess again)",
     "file": "bible.html",
     "find": "paths = live ? searchPaths : ['/api/d2jsp_quote?step=plan&item=', '/d2r/api/d2jsp_quote?item='];",
     "replace": "paths = searchPaths;",
     "matches": 1},
    {"why": "#221 - a read lands without ever saying it is folding the posts",
     "file": "bible.html",
     "find": "        setStep(idx, 'fold');\n",
     "replace": "",
     "matches": 1},
    {"why": "#221 - the 'searching' answer is painted as a final answer (the card stops on searching)",
     "file": "bible.html",
     "find": "        if (j && j.reason === 'searching') {",
     "replace": "        if (false) {",
     "matches": 1},
    {"why": "#221 - the plan-only ask spends the minute's search (the real search is then refused)",
     "file": "tv/control_app.py",
     "find": "                               pace=dict(_D2JSP_REFRESH_PACE) if dry else _D2JSP_REFRESH_PACE)",
     "replace": "                               pace=_D2JSP_REFRESH_PACE)",
     "matches": 1},
    {"why": "#221 - the band stops moving",
     "file": "bible.html",
     "find": "animation:d2jsp-load-sweep 1.15s var(--ease-in-out) infinite}",
     "replace": "}",
     "matches": 1},
    {"why": "#221 - the --warn trap: an undefined token in the loading card",
     "file": "bible.html",
     "find": "#tab-d2jsp .d2jsp-load-step[data-state=\"now\"]{color:var(--gold-bright)}",
     "replace": "#tab-d2jsp .d2jsp-load-step[data-state=\"now\"]{color:var(--warn,#ffd27f)}",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
