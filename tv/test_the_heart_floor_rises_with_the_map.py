# -*- coding: utf-8 -*-
"""REG-3216 - THE HEART FLOOR RATCHET TIGHTENS WHEN THE MAP RISES, AND ONLY A HUMAN LOWERS IT.

MEASURED 2026-11-05 (GrokBot on glass, #230; re-measured on the claude/v3865 tree): HEART.md said the console watches 8
of 406 painted surfaces and the board 4 of 602, while tv/heart_floor.json still held 7 of 366 (its names omit `bug`) and
1 of 513 (`vault-moved-note` alone). The floor rose only on a hand `--bless`, and --check compared COUNTS: `bug` could
stop being watched and the console would fall back to 7, or the board to 1, with --check green. The ratchet named in
HEART.md ("may not fall without a human saying why") was a ratchet only as far back as the last bless.

WHAT THIS LAW DRIVES (heart_map over FIXTURE pages and a floor in a temp dir; the real tree only in the last case):
  * regenerating RAISES each page's floor to the map when the map still watches every name the floor holds;
  * a floor name the map no longer watches leaves THAT page's floor where it was (never raised around a loss);
  * --check refuses a floor that LAGS the map and names the surfaces missing from it;
  * --check refuses a lost name even when the count held (one gained surface can hide one lost);
  * --bless that would LOWER the floor refuses without --why, and records the reason when given one;
  * the map's text is built BEFORE anything is opened for writing: a render that raises leaves HEART.md as it was
    (the open-for-write-truncates-first scar);
  * the committed tv/heart_floor.json holds the measured map: nothing lags, nothing lost.
RED_PROOF below.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import heart_map as HM  # noqa: E402

CONSOLE = ["bug", "clock", "hero", "phase", "sadv-sha", "sadv-tip", "stage", "th-shelf-x"]
BOARD_SEEN = ["d2jsp-price-advanced", "d2jsp-price-backend", "inventory", "vault-moved-note"]


def _pages(console=None, board=None):
    c = list(CONSOLE if console is None else console)
    b = list(BOARD_SEEN if board is None else board)
    return {"control_ui.html": {"ids": sorted(set(c + ["x%03d" % i for i in range(398)])), "seen": sorted(c)},
            "bible.html": {"ids": sorted(set(b + ["y%03d" % i for i in range(598)])), "seen": sorted(b)}}


def _floor(console, board, cw=None, bw=None):
    return {"_why": "fixture floor", "watched": len(console) if cw is None else cw, "surfaces": 366,
            "names": sorted(console),
            "board": {"watched": len(board) if bw is None else bw, "surfaces": 513, "names": sorted(board)}}


class _Scratch(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="heart-floor-")
        self.saved = (HM.OUT, HM.FLOOR, HM.measure_pages, HM.render)
        HM.OUT = os.path.join(self.tmp, "HEART.md")
        HM.FLOOR = os.path.join(self.tmp, "heart_floor.json")

    def tearDown(self):
        HM.OUT, HM.FLOOR, HM.measure_pages, HM.render = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def use(self, pages, floor):
        HM.measure_pages = lambda: (pages, [])
        if floor is not None:
            with io.open(HM.FLOOR, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(floor, indent=2, sort_keys=True) + "\n")
        with io.open(HM.OUT, "w", encoding="utf-8") as fh:
            fh.write(HM.render())

    def main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = HM.main(list(argv))
        return rc, buf.getvalue()

    def floor(self):
        with io.open(HM.FLOOR, encoding="utf-8") as fh:
            return json.load(fh)


class RegeneratingRaisesTheFloor(_Scratch):

    def test_the_measured_lag_is_raised_on_both_pages(self):
        self.use(_pages(), _floor([n for n in CONSOLE if n != "bug"], ["vault-moved-note"]))
        rc, out = self.main([])
        self.assertEqual(rc, 0, out)
        fl = self.floor()
        self.assertEqual((fl["watched"], fl["names"], fl["surfaces"]), (8, CONSOLE, 406),
                         "the console floor did not rise to the map (7 -> 8, bug): %r" % fl)
        self.assertEqual((fl["board"]["watched"], fl["board"]["names"], fl["board"]["surfaces"]), (4, BOARD_SEEN, 602),
                         "the board floor did not rise to the map (1 -> 4): %r" % fl["board"])
        self.assertEqual(fl["_why"], "fixture floor", "raising the floor rewrote its reason")
        self.assertIn("floor raised 7 -> 8", out)
        rc, out = self.main(["--check"])
        self.assertEqual(rc, 0, "a raised floor does not pass its own check: %s" % out)

    def test_a_lost_name_is_never_raised_around(self):
        floor = _floor(CONSOLE[1:] + ["ghost-x"], ["vault-moved-note"])
        self.use(_pages(), floor)
        rc, out = self.main([])
        self.assertEqual(rc, 0, out)
        fl = self.floor()
        self.assertEqual((fl["watched"], fl["names"]), (floor["watched"], floor["names"]),
                         "the console floor moved although `ghost-x` is no longer watched: %r" % fl)
        self.assertEqual(fl["board"]["watched"], 4, "the board floor did not rise beside a console loss")
        self.assertIn("NOT raised", out)
        self.assertIn("ghost-x", out)

    def test_a_floor_that_matches_is_left_byte_for_byte(self):
        self.use(_pages(), _floor(CONSOLE, BOARD_SEEN))
        with io.open(HM.FLOOR, "rb") as fh:
            before = fh.read()
        rc, out = self.main([])
        self.assertEqual(rc, 0, out)
        with io.open(HM.FLOOR, "rb") as fh:
            self.assertEqual(fh.read(), before, "a floor that already holds the map was rewritten")


class TheCheckNamesALagAndALoss(_Scratch):

    def test_a_floor_that_lags_the_map_is_refused_and_named(self):
        self.use(_pages(), _floor([n for n in CONSOLE if n != "bug"], ["vault-moved-note"]))
        rc, out = self.main(["--check"])
        self.assertEqual(rc, 1, "a floor 7 under a map of 8 passed --check: %s" % out)
        self.assertIn("LAGS", out)
        self.assertIn("bug", out)
        self.assertIn("inventory", out, "the board's lag was not named")

    def test_a_lost_name_is_refused_even_when_the_count_held(self):
        swapped = [n for n in CONSOLE if n != "bug"] + ["ghost-x"]
        self.use(_pages(), _floor(swapped, BOARD_SEEN))
        rc, out = self.main(["--check"])
        self.assertEqual(rc, 1, "a lost console surface passed because a count held: %s" % out)
        self.assertIn("ghost-x", out)
        bswapped = BOARD_SEEN[1:] + ["ghost-b"]
        self.use(_pages(), _floor(CONSOLE, bswapped))
        rc, out = self.main(["--check"])
        self.assertEqual(rc, 1, "a lost board surface passed because a count held: %s" % out)
        self.assertIn("ghost-b", out)

    def test_premise_a_floor_equal_to_the_map_passes(self):
        self.use(_pages(), _floor(CONSOLE, BOARD_SEEN))
        rc, out = self.main(["--check"])
        self.assertEqual(rc, 0, out)


class OnlyAHumanLowersIt(_Scratch):

    def test_a_lowering_bless_needs_a_reason(self):
        self.use(_pages(console=CONSOLE[1:]), _floor(CONSOLE, BOARD_SEEN))
        with io.open(HM.FLOOR, "rb") as fh:
            before = fh.read()
        rc, out = self.main(["--bless"])
        self.assertEqual(rc, 1, "a bless that drops `bug` wrote with no reason: %s" % out)
        self.assertIn("--why", out)
        with io.open(HM.FLOOR, "rb") as fh:
            self.assertEqual(fh.read(), before, "a refused bless still wrote the floor")
        rc, out = self.main(["--bless", "--why", "bug moved into the doctor's probe"])
        self.assertEqual(rc, 0, out)
        fl = self.floor()
        self.assertEqual(fl["watched"], 7)
        self.assertEqual(fl.get("_lowered", {}).get("why"), "bug moved into the doctor's probe")
        self.assertEqual(fl["_lowered"]["dropped"], {"control_ui.html": ["bug"]})

    def test_premise_a_bless_that_lowers_nothing_needs_no_reason(self):
        self.use(_pages(), _floor(CONSOLE[1:], BOARD_SEEN))
        rc, out = self.main(["--bless"])
        self.assertEqual(rc, 0, out)
        self.assertNotIn("_lowered", self.floor())


class TheMapIsBuiltBeforeAnythingIsOpened(_Scratch):

    def test_a_render_that_raises_leaves_the_map_as_it_was(self):
        self.use(_pages(), _floor(CONSOLE, BOARD_SEEN))
        with io.open(HM.OUT, "w", encoding="utf-8") as fh:
            fh.write("THE MAP AS IT WAS\n")

        def boom():
            raise RuntimeError("render failed mid-way")
        HM.render = boom
        with self.assertRaises(RuntimeError):
            self.main([])
        with io.open(HM.OUT, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "THE MAP AS IT WAS\n", "a failed render emptied HEART.md")
        self.assertFalse([f for f in os.listdir(self.tmp) if ".tmp-" in f], "a scratch file was left behind")


class TheCommittedFloorHoldsTheMap(unittest.TestCase):

    def test_nothing_lags_and_nothing_is_lost_on_this_tree(self):
        pages, missing = HM.measure_pages()
        self.assertEqual(missing, [], "a watcher could not be read: %r" % missing)
        with io.open(HM.FLOOR, encoding="utf-8") as fh:
            fl = json.load(fh)
        rows = HM.floor_vs_map(fl, pages)
        self.assertEqual(len(rows), 2, "PREMISE: a page has no floor entry: %r" % rows)
        for r in rows:
            self.assertFalse(r["lost"], "%s: the map no longer watches %r" % (r["label"], r["lost"]))
            self.assertFalse(r["lags"], "%s: the committed floor (%d) lags the map (%d): %r"
                             % (r["label"], r["was"], r["now"], r["gained"]))


RED_PROOF = [
    {"why": "REG-3216 - a regeneration never raises the floor (the 7-of-366 floor stays under a map of 8)",
     "file": "tv/heart_map.py",
     "find": "        rose = True\n",
     "replace": "        rose = False\n",
     "matches": 1},
    {"why": "REG-3216 - a floor is raised around a lost name, so the loss is blessed away by a regeneration",
     "file": "tv/heart_map.py",
     "find": "        if row[\"lost\"]:\n            said.append(\"%s floor NOT raised",
     "replace": "        if False:\n            said.append(\"%s floor NOT raised",
     "matches": 1},
    {"why": "REG-3216 - --check passes a floor that lags the map",
     "file": "tv/heart_map.py",
     "find": "        if lag:\n            for r in lag:\n",
     "replace": "        if False:\n            for r in lag:\n",
     "matches": 1},
    {"why": "REG-3216 - --check compares the console's count only: one gained surface hides one lost",
     "file": "tv/heart_map.py",
     "find": "        if gone:\n            print(\"HEART coverage lost a surface while its count held",
     "replace": "        if False:\n            print(\"HEART coverage lost a surface while its count held",
     "matches": 1},
    {"why": "REG-3216 - --check compares the board's count only: one gained surface hides one lost",
     "file": "tv/heart_map.py",
     "find": "        if bgone:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3216 - a bless lowers the floor with no reason anywhere",
     "file": "tv/heart_map.py",
     "find": "        if dropped and not why:\n",
     "replace": "        if False:\n",
     "matches": 1},
    {"why": "REG-3216 - HEART.md is opened for writing before its text is built (truncated by a failed render)",
     "file": "tv/heart_map.py",
     "find": "    text = render()          # REG-3216 - built BEFORE anything is opened for writing\n",
     "replace": "    io.open(OUT, \"w\", encoding=\"utf-8\").close()\n    text = render()\n",
     "matches": 1},
    {"why": "REG-3216 - the committed floor lags the map again (the measured 7-of-366 shape: `bug` not in it)",
     "file": "tv/heart_floor.json",
     "find": "    \"bug\",\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
