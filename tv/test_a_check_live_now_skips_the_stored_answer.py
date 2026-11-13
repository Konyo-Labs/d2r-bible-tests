# -*- coding: utf-8 -*-
"""Job E item 2 (Claude's #230 6849292433; he said yes) - A "CHECK LIVE NOW" CONTROL BESIDE THE PRICE.

With his 11-13 freshness ruling a held item is answered from the stored price for 90 days. "Check live now" is his way
past that, on purpose: it SKIPS the stored answer and searches d2jsp now, at the SAME one-a-minute pace every price check
shares (control_app._D2JSP_REFRESH_PACE), then the door folds the read like any other.
Held here:
  * server - _d2jsp_price_check_plan(item, live=True) plans a search for a FRESH held item (it would be "stored"
    otherwise) and stamps the pace; a second press inside the minute is answered "stored" with the wait said and the
    stored price kept; an item the DB lacks is read live; the door reads ?live=1, hands it to the plan and marks the
    answer liveNow;
  * page - every answer but "paused" draws a "Check live now" button just ahead of (floated beside) its price line,
    carrying the typed chunk; pressing it asks /api/d2jsp_quote?live=1&item=<that chunk>; with several results on
    screen only that item's section is repainted; a live read's line says "Checked live just now.".
Fixture DB in a temp dir and the page's own priceSearch in node with a stub fetch; nothing is fetched from d2jsp.
RED_PROOF below (hand-proven red/green, GrokBot box build).
"""
import io
import json
import os
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


def _db(items):
    db = P.empty()
    for i, (name, read_ago) in enumerate(items):
        posts = {}
        for j in range(4):
            link = "https://forums.d2jsp.org/topic.php?t=%d&f=268" % (3000 * (i + 1) + j)
            posts[link] = {"fg": 25, "day": time.strftime("%Y-%m-%d", time.localtime(NOW - DAY)), "link": link, "w": 1,
                           "perfect": False, "src": "mac", "seenAt": NOW}
        db["items"][P.key_of(name)] = {"item": name, "readAt": NOW - read_ago * DAY, "posts": posts}
    return db


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


class TheServerSkipsTheStoredAnswerAtThePace(unittest.TestCase):

    def setUp(self):
        self._cr = P.checks_running
        P.checks_running = lambda env=None: False
        self.addCleanup(setattr, P, "checks_running", self._cr)
        import control_app as CA
        self.CA = CA
        self.d = tempfile.mkdtemp(prefix="price-live-")
        self.addCleanup(shutil.rmtree, self.d, True)
        P.save(os.path.join(self.d, "d2jsp_price_db.json"), _db([("Shako", 2)]))
        old = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.d
        self.addCleanup(lambda: os.environ.pop("TV_HIST", None) if old is None else os.environ.__setitem__("TV_HIST", old))
        self._canon = CA._d2jsp_canon
        CA._d2jsp_canon = lambda item: P.key_of(item)
        self.addCleanup(setattr, CA, "_d2jsp_canon", self._canon)
        self._pace = dict(CA._D2JSP_REFRESH_PACE)
        CA._D2JSP_REFRESH_PACE["at"] = 0.0
        self.addCleanup(CA._D2JSP_REFRESH_PACE.update, self._pace)

    def test_a_fresh_item_is_searched_when_he_asks_live(self):
        self.assertEqual(self.CA._d2jsp_price_check_plan("Shako", now=NOW)["do"], "stored", "PREMISE: Shako is fresh")
        plan = self.CA._d2jsp_price_check_plan("Shako", now=NOW, live=True)
        self.assertEqual((plan["do"], plan.get("live")), ("refresh", True), plan)
        self.assertEqual(self.CA._D2JSP_REFRESH_PACE["at"], NOW, "check live now did not spend the minute's search")

    def test_a_second_press_inside_the_minute_waits_and_keeps_the_stored_price(self):
        self.CA._d2jsp_price_check_plan("Shako", now=NOW, live=True)
        plan = self.CA._d2jsp_price_check_plan("Shako", now=NOW + 20, live=True)
        self.assertEqual(plan["do"], "stored", "two live searches inside one minute")
        ans = plan["answer"]
        self.assertEqual((ans["reason"], ans["wait"], ans.get("liveNow")), ("stored", 40, True), ans)
        self.assertIn("check live now waits 40 s", ans["say"])
        self.assertIsNone(ans["fg"], "a wait claimed a live fg")

    def test_an_item_the_db_lacks_is_read_live(self):
        plan = self.CA._d2jsp_price_check_plan("Gull", now=NOW, live=True)
        self.assertEqual((plan["do"], plan.get("live")), ("live", True), plan)

    def test_the_door_reads_live_and_marks_the_answer(self):
        src = _read("tv/control_app.py")
        a = src.index('        if path == "/api/d2jsp_quote":')
        door = src[a:src.index('        if path == "/api/d2jsp_price_db":', a)]
        self.assertIn('_ask = {"live": True} if (parse_qs(urlparse(self.path).query).get("live") or [""])[0] == "1" else {}', door)
        self.assertIn("_plan = _d2jsp_price_check_plan(_item, **_ask)", door, "the door never hands ?live=1 to the plan")
        self.assertIn('_out["liveNow"] = True', door)
        self.assertLess(door.index("_d2jsp.d2jsp_quote("), door.index('_out["liveNow"] = True'))


@unittest.skipUnless(NODE, "no node - the page's price search is not driven here (UNMEASURED)")
class ThePageOffersItBesideThePrice(unittest.TestCase):

    def _drive(self, call, answer, sections=False):
        page = _read("bible.html")
        body = _block(page, "  function priceSearch(){")
        line = _block(page, "function d2jspSearchLine(q, sim, parsed) {")
        prog = (
            "var asked = [], secs = [];\n"
            "function Sec(n){ this.n = n; this.innerHTML = 'OLD ' + n; this.textContent = ''; }\n"
            "Sec.prototype.getAttribute = function(){ return this.n; };\n"
            "var out = {textContent: '', innerHTML: 'ORIG', querySelectorAll: function(){ return secs; }};\n"
            "if (%s) { secs = [new Sec('shako'), new Sec('jmod')]; }\n"
            "var els = {'d2jsp-price-q': {value: 'shako, jmod'}, 'd2jsp-price-out': out};\n"
            "var document = {getElementById: function(id){ return els[id] || null; }};\n"
            "var searchGen = 0;\n"
            "function esc(x){ return String(x).replace(/\"/g, '&quot;'); }\n"
            "function d2jspParseSearch(v){ return {item: String(v || '').trim(), roll: null}; }\n"
            "function d2jspSimilarPrice(){ return null; }\n"
            "function d2jspBackendHtml(){ return ''; }\n"
            "function d2jspTierCardsHtml(){ return ''; }\n"
            "function d2jspEvidenceHtml(){ return ''; }\n"
            "function d2jspDatabaseButton(){ return ''; }\n"
            "function d2jspReadLine(q){ return 'READ ' + q.fg; }\n"
            "function d2jspPriceLine(q){ return 'LINE ' + q.reason; }\n"
            "function d2jspSearchChunks(t){ return String(t).split(',').map(function(s){ return s.trim(); }).filter(Boolean); }\n"
            + line + "\n"
            "function fetch(u){ asked.push(u); return Promise.resolve({json: function(){ return %s; }}); }\n"
            + body + "\n"
            + call + ";\n"
            "setTimeout(function(){ process.stdout.write(JSON.stringify({asked: asked, html: out.innerHTML,"
            " secs: secs.map(function(s){ return s.innerHTML; })})); }, 1500);\n") % ("true" if sections else "false",
                                                                                   json.dumps(answer))
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        return json.loads(r.stdout)

    def test_every_answer_carries_the_control_beside_its_line(self):
        got = self._drive("priceSearch()", {"reason": "stored", "fg": None, "say": "fresh", "dbFirst": None})
        self.assertEqual([u.split("?", 1)[0] for u in got["asked"]], ["/api/d2jsp_quote", "/api/d2jsp_quote"])
        self.assertFalse(any("live=1" in u for u in got["asked"]), "a plain price search skipped the stored answer")
        for item in ("shako", "jmod"):
            self.assertIn('data-d2jsp-live-now="%s"' % item, got["html"], "no Check live now for %s" % item)
        self.assertIn(">Check live now</button><div>LINE stored</div>", got["html"].replace("\n", ""),
                      "the control does not ride just ahead of (beside) the price line")

    def test_pressing_it_asks_live_and_repaints_only_that_item(self):
        got = self._drive("priceSearch('jmod')", {"reason": "read", "fg": 30, "liveNow": True, "n": 4}, sections=True)
        self.assertEqual(got["asked"], ["/api/d2jsp_quote?live=1&item=jmod"], "check live now did not ask live for its item")
        self.assertEqual(got["html"], "ORIG", "a live re-read of one item repainted every result")
        self.assertEqual(got["secs"][0], "OLD shako", "the other item's section was touched")
        self.assertIn("Checked live just now. LINE read", got["secs"][1], "jmod's section does not say it was read live")

    def test_a_paused_console_offers_no_live_check(self):
        got = self._drive("priceSearch()", {"reason": "paused", "fg": None})
        self.assertNotIn("data-d2jsp-live-now", got["html"])

    def test_the_click_reaches_it(self):
        click = _block(_read("bible.html"), "  window._d2jspPriceClick = function(ev){")
        self.assertIn("t.closest('[data-d2jsp-live-now]')", click)
        self.assertIn("priceSearch(_lv.getAttribute('data-d2jsp-live-now') || '');", click)
        self.assertLess(click.index("data-d2jsp-live-now"), click.index("if (!t || !t.id) return false;"),
                        "a button with no id never reaches check live now")


RED_PROOF = [
    {"why": "Job E - live is ignored: a fresh item is answered stored even when he asks live",
     "file": "tv/control_app.py",
     "find": "    if live:\n        return _d2jsp_live_now_plan(item, now, first, held is not None, dry=dry)\n",
     "replace": "",
     "matches": 1},
    {"why": "Job E - check live now skips the pace (two searches inside one minute)",
     "file": "tv/control_app.py",
     "find": "        left = _PDB.REFRESH_GAP_S - (now - last)\n        if left > 0:\n            wait = int(math.ceil(left))\n",
     "replace": "        left = 0\n        if left > 0:\n            wait = int(math.ceil(left))\n",
     "matches": 1},
    {"why": "Job E - the door never reads ?live=1",
     "file": "tv/control_app.py",
     "find": "            _ask = {\"live\": True} if (parse_qs(urlparse(self.path).query).get(\"live\") or [\"\"])[0] == \"1\" else {}\n",
     "replace": "            _ask = {}\n",
     "matches": 1},
    {"why": "Job E - the page draws no Check live now control",
     "file": "bible.html",
     "find": "      if (j && j.reason !== 'paused') {\n        _first += '<button",
     "replace": "      if (false) {\n        _first += '<button",
     "matches": 1},
    {"why": "Job E - the control asks the plain (stored-first) door",
     "file": "bible.html",
     "find": "searchPaths = live ? ['/api/d2jsp_quote?live=1&item=', '/d2r/api/d2jsp_quote?item=']",
     "replace": "searchPaths = live ? ['/api/d2jsp_quote?item=', '/d2r/api/d2jsp_quote?item=']",
     "matches": 1},
    {"why": "Job E - a live re-read of one item repaints every result",
     "file": "bible.html",
     "find": "    if (live && out.querySelectorAll) {",
     "replace": "    if (false) {",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
