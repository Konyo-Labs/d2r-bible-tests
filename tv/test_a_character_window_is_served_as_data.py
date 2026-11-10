# -*- coding: utf-8 -*-
"""v3889 (#28, REG-3499) - ONE SAVED BUILD'S CHARACTER WINDOW IS SERVED AS DATA, READ-ONLY, FOR GROKBOT'S d2planner ROUNDS.

His 11-08 ~12:40: do #28 now - GrokBot holds the character window against d2planner, round by round. GrokBot 6720536745:
UNKNOWN - "the character window's gear and stats live only in the board's storage"; /api/chars_learned carries class +
level and 3 of 10 slots. Now the board computes the window (bible.html window.charWindowSheet - _cbEngineBuild and the
same eng.sheet call the Stats column paints from, at the window's own difficulty and quests) and the console serves it:
GET /api/char_window?name=<build> (control_app.char_window, the same hop into #tvd-eng board_ownership makes). Nothing is
written; a name the board does not hold is refused with the names it does; a board that does not answer is UNKNOWN.

The board half runs the real builder and engine in node (the builder law's own harness); the console half drives
char_window with a stubbed evaluator. RED_PROOF below. [[the-unjoined-end]] [[unknown-stays-unknown]]
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import test_the_character_builder_is_joined_to_the_engine_and_the_mule_window as JOIN  # noqa: E402

BODY = r"""
sorc();
var id = window._cbState().bid, b = window._cbAll()[id];
OUT.byId = window.charWindowSheet(id);
OUT.byName = window.charWindowSheet('  ' + String(b.name).toUpperCase() + ' ');
OUT.nope = window.charWindowSheet('No Such Build');
var h = statsHtml(), i = h.indexOf('<span class="cb-sl">Faster Cast Rate</span>'), row = h.slice(i, h.indexOf('</div>', i)),
    j = row.indexOf('class="cb-bp"');
OUT.paintedFcr = j < 0 ? null : row.slice(row.indexOf('>', j) + 1, row.indexOf('</span>', j));
OUT.storeBefore = window.LSR.getItem('d2r_charBuilds');
window.charWindowSheet(id);
OUT.storeAfter = window.LSR.getItem('d2r_charBuilds');
"""


@unittest.skipIf(JOIN.NODE is None, "node is absent - the board's window is UNMEASURED here, never a pass")
class TheBoardComputesOneWindow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = JOIN._run(BODY)

    def test_the_window_is_the_builds_own(self):
        """* THE POINT - class, level, the gear the engine read, and the Stats rows"""
        w = self.out["byId"]
        self.assertTrue(w.get("ok"), w)
        self.assertEqual((w["cls"], w["level"]), ("Sorceress", 90))
        names = sorted(str((e or {}).get("name") or "") for e in (w["gear"]["slots"] or {}).values())
        self.assertEqual(names, sorted(["Crown of Ages", "Skin of the Vipermagi", "Mara's Kaleidoscope", "The Oculus"]), names)
        fcr = [r for r in w["rows"] if r["key"] == "fcr"]
        self.assertEqual(len(fcr), 1, "no Faster Cast Rate row")
        self.assertTrue(fcr[0]["value"], fcr[0])

    def test_its_step_is_the_sentence_the_window_paints(self):
        fcr = [r for r in self.out["byId"]["rows"] if r["key"] == "fcr"][0]
        self.assertTrue(self.out["paintedFcr"], "PREMISE: the Stats column painted no FCR step")
        self.assertEqual(fcr["step"], self.out["paintedFcr"], "the served step and the painted one disagree")

    def test_a_name_finds_it_and_an_unknown_name_is_refused_with_the_names(self):
        self.assertEqual(self.out["byName"].get("id"), self.out["byId"].get("id"), "a build's own name did not find it")
        self.assertFalse(self.out["nope"]["ok"])
        self.assertIn(self.out["byId"]["name"], self.out["nope"]["names"])

    def test_nothing_is_written(self):
        self.assertEqual(self.out["storeBefore"], self.out["storeAfter"], "reading the window wrote his builds")


class TheConsoleServesIt(unittest.TestCase):

    def setUp(self):
        import control_app as CA
        self.CA = CA

    def test_it_asks_the_board_and_hands_back_its_answer(self):
        seen = {}

        def ejs(w, js, timeout=0):
            seen["js"] = js
            return json.dumps({"ok": True, "name": "Frostnova", "rows": []})
        got = self.CA.char_window('Frost"nova', ejs=ejs, win=object())
        self.assertEqual(got.get("name"), "Frostnova")
        self.assertIn("charWindowSheet(\"Frost\\\"nova\")", seen["js"], "the name is not passed as a JS string literal")
        self.assertIn("getElementById('tvd-eng')", seen["js"], "no hop into the board iframe")

    def test_a_silent_board_is_unknown_not_empty(self):
        got = self.CA.char_window("Frostnova", ejs=lambda *a, **k: "", win=object())
        self.assertFalse(got["ok"])
        self.assertIn("UNREAD", got["why"])
        self.assertFalse(self.CA.char_window("", ejs=lambda *a, **k: "{}", win=object())["ok"], "an empty name was asked")

    def test_the_route_serves_it(self):
        import io
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('        if path == "/api/char_window":\n', src)
        self.assertIn('            self._json(200, char_window((q.get("name") or [""])[0]))\n', src)


RED_PROOF = [
    {"why": "v3889 (REG-3499) - the window is served without its breakpoint sentences",
     "file": "bible.html",
     "find": "                          step: r.bp ? (_cbBpSay(eng, r.bp, r.key, r, b) || null) : null };",
     "replace": "                          step: null };",
     "matches": 1},
    {"why": "v3889 (REG-3499) - a build's own name no longer finds it",
     "file": "bible.html",
     "find": "String(all[k].name || '').trim().toLowerCase() === want && want) id = k; });",
     "replace": "String(all[k].name || '') === key && want) id = k; });",
     "matches": 1},
    {"why": "v3889 (REG-3499) - a board that does not answer reads as an empty window",
     "file": "tv/control_app.py",
     "find": "        return {\"ok\": False, \"why\": \"the board did not answer in time - the window is UNREAD, not empty\"}\n",
     "replace": "        return {\"ok\": True, \"rows\": []}\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
