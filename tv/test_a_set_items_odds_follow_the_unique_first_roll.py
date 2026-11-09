# -*- coding: utf-8 -*-
"""v3890 (#43, REG-3506) - A SET ITEM'S ODDS FOLLOW THE GAME'S UNIQUE-FIRST QUALITY ROLL, NOT THE UNIQUE CURVE.

MEASURED 11-09: the page moved every stored 1:N off silospen's MF-300 base by the unique curve, so Sander's Paragon from
Hell Mephisto read 1:7,381 at MF 1000 where silospen (the source of every stored 1:N) reads 1:10,007 - the game rolls
unique FIRST, so past MF 300 a set at a high-level monster gets RARER (tv/silospen_set_mf.py says the arithmetic). Held:
  * the generated farms reproduce silospen's own checkpoints (tv/data/silospen_set_mf_rotw30.json: 8 set items - normal,
    exceptional, elite and class bases - every boss and super-unique row, MF 0 / 300 / 700 / 1000), in Python AND in the
    page's own JavaScript (the ⟦SET_MF⟧ block and setMfChance, cut from bible.html and run in node);
  * every set item the page's boss tables carry has its base, and every farm is measured or named (SKIPPED_FARMS);
  * effChance hands the item to setMfChance, and every call that has an item passes it.
RED_PROOF below. [[unknown-stays-unknown]] [[the-unjoined-end]]
"""
import io
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import silospen_set_mf as SM  # noqa: E402
import js_strip  # noqa: E402  (one comment stripper for the laws)
try:
    import vault_page_node as VPN  # noqa: E402  (the one node resolver: off PATH too)
    NODE = VPN.NODE
except Exception:
    NODE = None

TOL = SM.FIT_TOL


def _bible():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


def _consts(src):
    head, tail = "/* ⟦SET_MF⟧", "/* ⟦/SET_MF⟧ */"
    assert src.count(head) == 1, "PREMISE: the generated SET_MF block is gone or doubled (%d)" % src.count(head)
    blk = src[src.index(head):src.index(tail)]
    farm = json.loads(re.search(r"const SET_MF_FARM = (\{.*?\});\n", blk).group(1))
    base = json.loads(re.search(r"const SET_MF_BASE = (\{.*?\});\n", blk).group(1))
    return farm, base


def _raw():
    with io.open(SM.DATA, encoding="utf-8") as fh:
        return json.load(fh)


def _points(farm, base):
    """every (farm, diff, item, mf, silospen p, the same cell's MF-300 p) the page's parameters cover"""
    out = []
    for (f, d), cells in sorted(SM.checkpoints(_raw()).items()):
        if d not in farm.get(f, {}):
            continue
        for item, pm in sorted(cells.items()):
            if item not in base or 300 not in pm:
                continue
            for mf in SM.MFS:
                if mf in pm:
                    out.append((f, d, item, mf, pm[mf], pm[300]))
    return out


class ASetItemsOddsFollowTheUniqueFirstRoll(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _bible()
        cls.farm, cls.base = _consts(cls.src)

    def test_the_model_tells_the_roll_from_the_unique_curve(self):
        """BASELINE: on Hell Mephisto (ilvl 87, bonus 983) a Cap's set odds fall from MF 300 to 1000 - the unique curve
        says they rise - so a check against silospen can tell the two apart"""
        at300, at1000 = SM.p_set(0, 87, 1, 300, 983), SM.p_set(0, 87, 1, 1000, 983)
        self.assertLess(at1000, at300, "the unique-first roll does not make a set rarer at high MF here")
        self.assertLess(9382 * at300 / at1000, 10050)
        self.assertGreater(9382 * at300 / at1000, 9960)

    def test_the_generated_farms_reproduce_silospens_checkpoints(self):
        pts = _points(self.farm, self.base)
        self.assertGreaterEqual(len(pts), 300, "PRINT THE DENOMINATOR: only %d checkpoints are covered" % len(pts))
        bad = []
        for f, d, item, mf, p, p300 in pts:
            ilvl, bonus = self.farm[f][d]
            q, cls = self.base[item]
            pred = p300 * SM.p_set(cls, ilvl, q, mf, bonus) / SM.p_set(cls, ilvl, q, 300, bonus)
            if abs(pred - p) / p > TOL:
                bad.append("%s %s %s MF %d: silospen 1:%d, the model 1:%d" % (f, d, item, mf, round(1 / p), round(1 / pred)))
        self.assertEqual(bad, [], "\n  ".join(bad[:20]))

    def test_the_pages_own_javascript_prints_silospens_figure(self):
        if not NODE:
            self.skipTest("node is absent on this machine - the page's set odds are UNMEASURED here, never a pass")
        head = "/* ⟦SET_MF⟧"
        end = "window.setMfChance = setMfChance;\n"
        self.assertEqual(self.src.count(end), 1)
        cut = self.src[self.src.index(head):self.src.index(end) + len(end)]
        pts = _points(self.farm, self.base)
        cases = [[f, d, item, mf, round(1 / p300), 1 / p] for f, d, item, mf, p, p300 in pts]
        prog = ("var window = {};\n" + cut + "\nvar cases = " + json.dumps(cases) + ";\n"
                "process.stdout.write(JSON.stringify(cases.map(function (c) {"
                " return [c[0], c[1], c[2], c[3], setMfChance(c[4], c[2], c[0], c[1], c[3]), c[5]]; })));\n")
        r = subprocess.run([NODE, "-"], input=prog.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-600:])
        got = json.loads(r.stdout.decode("utf-8"))
        self.assertEqual(len(got), len(cases))
        bad = ["%s %s %s MF %d: the page 1:%s, silospen 1:%d" % (f, d, it, mf, n, round(want))
               for f, d, it, mf, n, want in got if not n or abs(n - want) / want > TOL + 1.0 / max(1.0, want)]
        self.assertEqual(bad, [], "\n  ".join(bad[:20]))
        meph = [n for f, d, it, mf, n, want in got if (f, d, it, mf) == ("mephisto", "hell", "Sander's Paragon", 1000)]
        self.assertTrue(meph and abs(meph[0] - 10007) <= 15, "Sander's Paragon, Hell Mephisto, MF 1000: %s" % meph)

    def test_every_set_on_the_boss_tables_has_its_base_and_every_farm_is_measured_or_named(self):
        i = self.src.index("const BOSSES = [")
        bosses = json.loads(self.src[i + len("const BOSSES = "):self.src.index("\n", i)].rstrip().rstrip(";"))
        sets = sorted(set(d["n"] for b in bosses for d in b.get("dropTable", []) if d.get("tier") == "set"))
        self.assertGreater(len(sets), 100, "PREMISE: the boss tables carry %d set items" % len(sets))
        self.assertEqual([n for n in sets if n not in self.base and n not in SM.SKIPPED_ROWS], [],
                         "a set item on the page has no base and is not named: the roll is skipped unsaid")
        self.assertEqual([n for n in SM.SKIPPED_ROWS if n not in sets], [], "a named whole-set row left the page: unname it")
        farms = sorted(b["id"] for b in bosses if any(d.get("tier") == "set" for d in b.get("dropTable", [])))
        lost = [f for f in farms if f not in self.farm and f not in SM.SKIPPED_FARMS]
        self.assertEqual(lost, [], "a farm with set items is neither measured nor named: %s" % lost)
        for f in self.farm:
            for d in ("nm", "hell"):
                self.assertIn(d, self.farm[f], "%s %s was not fitted - its sets keep the unique curve" % (f, d))

    def test_effchance_hands_every_item_it_has_to_the_set_roll(self):
        code = js_strip.strip_js_comments(self.src)
        self.assertIn("function effChance(base, bossId, diffKey, item){", code)
        self.assertIn("var _set = isEventP(base) ? undefined : setMfChance(base, item, bossId, diffKey, mf);", code)
        self.assertIn("var a = _set !== undefined ? _set : adjustChance(base, mf);", code)
        self.assertIn("diffKey:k,item:d.n};", code, "the registry's sources no longer carry their item")
        three = re.findall(r"effChance\((s|src|z)\.chance, ?\1\.bossId, ?\1\.diffKey\)", code)
        three += re.findall(r"effChance\(d\[k\], boss\.id, k\)", code) + re.findall(r"effChance\(v, boss\.id, dk\)", code)
        self.assertEqual(three, [], "%d call(s) with the item in hand drop it" % len(three))


RED_PROOF = [
    {"why": "v3890 (#43) - effChance never asks the set roll: every set is moved by the unique curve again",
     "file": "bible.html",
     "find": "      var _set = isEventP(base) ? undefined : setMfChance(base, item, bossId, diffKey, mf);\n",
     "replace": "      var _set = undefined;\n",
     "matches": 1},
    {"why": "v3890 (#43) - the set roll forgets the unique roll comes first",
     "file": "bible.html",
     "find": "  return (1 - _setMfRoll(R[0], ilvl, q, m, 250, bonus)) * _setMfRoll(R[1], ilvl, q, m, 500, bonus);\n",
     "replace": "  return _setMfRoll(R[1], ilvl, q, m, 500, bonus);\n",
     "matches": 1, "needs": "node"},
    {"why": "v3890 (#43) - the set roll loses its floor (the 5600 the set chance stops at)",
     "file": "bible.html",
     "find": "  c = Math.max(c, r[2]);\n  c = c - Math.floor(c * bonus / 1024);\n",
     "replace": "  c = c - Math.floor(c * bonus / 1024);\n",
     "matches": 1, "needs": "node"},
    {"why": "v3890 (#43) - the registry's odds sources stop carrying their item",
     "file": "bible.html",
     "find": "diffKey:k,item:d.n};",
     "replace": "diffKey:k};",
     "matches": 1},
    {"why": "v3890 (#43) - one drop-table cell drops the item it has",
     "file": "bible.html",
     "find": "fmtDrop(effChance(v, boss.id, dk, d.n), d.n)",
     "replace": "fmtDrop(effChance(v, boss.id, dk), d.n)",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
