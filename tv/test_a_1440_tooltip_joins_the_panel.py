#!/usr/bin/env python3
"""A KAI judge row names the panel the tooltip sat on.

The 8% area floor was measured at 2560x1665, where a real tooltip is 33% of the
frame and the HUD impostor is 2.8%. At 1440x936 the same finder reports a
legible tooltip as one or two tiles of the 6x6 sweep — 2.8% or 5.6% — and 8%
refused 4 of 4 Session-1 frames. The floor scales with the capture so that
cluster is admitted, and the calibration-size HUD stays refused.

The compile then joins the rect to a panel and writes names_loc on the kai row:
the left panel is the stash, the right panel is 'on him' (inventory, slot
unknown), and a tooltip that was not located stays None. A read that
failed is not that miss: it is recorded unknown and files no panel. A rect
that only crosses the midline belongs to the side that holds more of it.
"""
import os
import sys
import tempfile
import unittest

import fixture_tmp as _fx_tmp  # noqa: E402  # this run's scratch dirs leave with it
_fx_tmp.contain()

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# The compile reads CONTROL_PORT at import. Point it off his live console.
os.environ.setdefault("TV_CONTROL_PORT", "9")

import tooltip_find as TF  # noqa: E402
import control_app as ca  # noqa: E402


def _frame(w, h):
    """A real image. locate() opens the file before it asks the reader."""
    from PIL import Image
    d = tempfile.mkdtemp()
    p = os.path.join(d, "frame.jpg")
    Image.new("RGB", (w, h), (12, 10, 8)).save(p, "JPEG", quality=60)
    return p


def _fake(grid):
    """N text lines per tile, in the order density() visits them."""
    state = {"i": 0}
    flat = [n for row in grid for n in row]

    def read(_path):
        n = flat[state["i"]] if state["i"] < len(flat) else 0
        state["i"] += 1
        return {"lines": ["a line of text"] * n}
    return read


def _grid(rows, cols, cells):
    g = [[0] * cols for _ in range(rows)]
    for (r, c), n in cells.items():
        g[r][c] = n
    return g


def _kai(extra):
    row = {
        "lane": "kai", "ts": 100, "captureTs": 100,
        "frameId": "f_fixture", "sessionId": "s_fixture",
        "scene": "kai",
        "kai": {"judge": {"name": "Windforce", "tier": "grail", "score": 9}},
    }
    row.update(extra)
    return row


def _loc(row):
    reg = {r["name"]: r for r in ca._kai_compile_register([row])}
    return (row.get("names_loc") or {}).get("Windforce"), (reg.get("Windforce") or {}).get("loc")


class TestTheFloorScalesWithTheCapture(unittest.TestCase):
    """One tile of a 6x6 sweep is 2.8% of any frame. At 1440x936 that is a tooltip.
    At 2560x1665 it is the HUD, and 8% still refuses it."""

    def test_a_one_tile_and_a_two_tile_cluster_at_1440x936_are_admitted(self):
        # The Session-1 measurement: densest text 2.8% (one tile) and 5.6% (two).
        # Both sit under the fixed 8% floor.
        one = _grid(6, 6, {(1, 4): 8})
        rect, why = TF.locate(_frame(1440, 936), reader=_fake(one))
        self.assertIsNotNone(rect, why)
        frac = float(rect[2] * rect[3]) / float(1440 * 936)
        self.assertLess(frac, 0.08, "this cluster is not the one 8%% used to refuse")
        self.assertGreater(frac, 0.02, "a speck was admitted")

        two = _grid(6, 6, {(2, 0): 6, (2, 1): 6})
        rect2, why2 = TF.locate(_frame(1440, 936), reader=_fake(two))
        self.assertIsNotNone(rect2, why2)
        frac2 = float(rect2[2] * rect2[3]) / float(1440 * 936)
        self.assertLess(frac2, 0.08)
        self.assertGreater(frac2, frac)

    def test_the_calibration_hud_is_still_refused(self):
        # (2450, 0, 490, 318) on a 2560-wide frame — one corner tile, 2.8%.
        hud = _grid(6, 6, {(0, 5): 40})
        rect, why = TF.locate(_frame(2560, 1665), reader=_fake(hud))
        self.assertIsNone(rect, "the HUD box at the calibration size was accepted")
        self.assertIn("chrome", why or "")


class TestTheCompileJoinsTheRectToThePanel(unittest.TestCase):

    def test_left_is_stash_right_is_on_him_and_missing_is_none(self):
        left = _kai({"tooltipRect": (40, 180, 380, 420), "frameW": 1440, "frameH": 936})
        self.assertEqual(_loc(left), ("stash", "stash"))

        right = _kai({"tooltipRect": (900, 80, 420, 360), "frameW": 1440, "frameH": 936})
        self.assertEqual(_loc(right), ("on him", "on him"))

        absent = _kai({})
        self.assertEqual(_loc(absent), (None, None))

        # A rect that covers both panels equally is not a guess.
        split = _kai({"tooltipRect": (520, 100, 400, 300), "frameW": 1440, "frameH": 936})
        self.assertEqual(_loc(split), (None, None))

        # A place the row already stated is the better witness.
        kept = _kai({
            "names_loc": {"Windforce": "equipped"},
            "tooltipRect": (40, 180, 380, 420), "frameW": 1440, "frameH": 936,
        })
        self.assertEqual(_loc(kept), ("equipped", "equipped"))

    def test_a_rect_that_only_grazes_the_midline_is_the_side_that_holds_more(self):
        """place_of's contract: only an even split is None. A graze is the majority.

        1440 wide, midline at 720. The even case above is 200px against 200px.
        These two cross the line by 10px and the rest stays on one side.
        """
        # 520px on the left, 10px past the line.
        self.assertEqual(TF.place_of((200, 100, 530, 300), 1440, 936), "stash")
        left = _kai({"tooltipRect": (200, 100, 530, 300), "frameW": 1440, "frameH": 936})
        self.assertEqual(_loc(left), ("stash", "stash"))

        # 10px on the left, 390px on the right.
        self.assertEqual(TF.place_of((710, 80, 400, 280), 1440, 936), "on him")
        right = _kai({"tooltipRect": (710, 80, 400, 280), "frameW": 1440, "frameH": 936})
        self.assertEqual(_loc(right), ("on him", "on him"))

    def test_the_compile_locates_the_frame_it_was_handed(self):
        # The real locate(), on the 1440 fixture, through the real compile.
        # One tile on the right: under 8% of the frame, and on him.
        frame = _frame(1440, 936)
        row = _kai({
            "framePath": frame,
            "tooltipReader": _fake(_grid(6, 6, {(1, 4): 8})),
        })
        self.assertEqual(_loc(row), ("on him", "on him"))


class TestAFailedReadIsUnknownAndTheFrameIsReadOnce(unittest.TestCase):
    """A locate that throws is not 'not on a panel', and one frame is read once."""

    def test_a_reader_failure_is_unknown_and_files_no_panel(self):
        calls = {"n": 0}

        def boom(_path):
            calls["n"] += 1
            raise OSError("reader down")

        frame = _frame(1440, 936)
        rows = []
        for i in range(2):
            rows.append(_kai({
                "framePath": frame,
                "frameId": "f_%d" % i,
                "ts": 100 + i,
                "captureTs": 100 + i,
                "tooltipReader": boom,
            }))
        reg = {r["name"]: r for r in ca._kai_compile_register(rows)}
        filed = (reg.get("Windforce") or {}).get("loc")
        self.assertNotIn(filed, ("stash", "on him"),
                         "a reader failure was filed as a panel: %r" % (filed,))
        for row in rows:
            self.assertNotIn("Windforce", row.get("names_loc") or {})
            self.assertTrue(row.get("tooltip_loc_unknown"),
                            "a reader failure is indistinguishable from a measured miss")
            self.assertNotIn(row.get("tooltip_loc_unknown"), ("stash", "on him"))
        # The throw aborts the sweep, and the second row reuses that failure.
        self.assertEqual(calls["n"], 1, "the same frame was read again after it had already failed")

    def test_the_same_frame_is_located_once_for_every_row_on_it(self):
        calls = {"n": 0}

        def read(_path):
            calls["n"] += 1
            return {"lines": ["a line of text"] * 8}

        frame = _frame(1440, 936)
        rows = []
        for i in range(3):
            rows.append(_kai({
                "framePath": frame,
                "frameId": "f_%d" % i,
                "ts": 100 + i,
                "captureTs": 100 + i,
                "tooltipReader": read,
            }))
        ca._kai_compile_register(rows)
        one_sweep = TF.DEFAULT_COLS * TF.DEFAULT_ROWS
        self.assertEqual(calls["n"], one_sweep,
                         "one frame was OCR'd %d times across %d rows (one sweep is %d)"
                         % (calls["n"], len(rows), one_sweep))

    def test_a_frame_with_no_tooltip_is_a_measured_miss_not_unknown(self):
        def read(_path):
            return {"lines": []}

        frame = _frame(1440, 936)
        row = _kai({"framePath": frame, "tooltipReader": read})
        self.assertEqual(_loc(row), (None, None))
        self.assertNotIn("tooltip_loc_unknown", row)

RED_PROOF = [
    {"why": "a fixed 8% floor, measured at 2560x1665, refuses a legible one-tile tooltip at 1440x936",
     "file": "tv/tooltip_find.py",
     "find": "    floor = _MIN_AREA_FRAC * (float(w * h) / float(_CAL_W * _CAL_H))\n",
     "replace": "    floor = _MIN_AREA_FRAC\n",
     "matches": 1},
    {"why": "the floor drops below the impostor, so the top-right HUD box is accepted as a tooltip at the calibration size",
     "file": "tv/tooltip_find.py",
     "find": "    if frac < floor:\n        return None, (",
     "replace": "    if frac < floor * 0.25:\n        return None, (",
     "matches": 1},
    {"why": "the left panel is filed as 'on him', so a stash tooltip is placed on his body",
     "file": "tv/tooltip_find.py",
     "find": "    if left > right and left > 0:\n        return \"stash\"\n",
     "replace": "    if left > right and left > 0:\n        return \"on him\"\n",
     "matches": 1},
    {"why": "a rect that only grazes the midline is refused instead of given to the side that holds more of it",
     "file": "tv/tooltip_find.py",
     "find": "    if left > right and left > 0:\n        return \"stash\"\n    if right > left and right > 0:\n        return \"on him\"\n",
     "replace": "    if left > 0 and right == 0:\n        return \"stash\"\n    if right > 0 and left == 0:\n        return \"on him\"\n",
     "matches": 1},
    {"why": "a place the row already stated is overwritten by the tooltip's panel",
     "file": "tv/control_app.py",
     "find": "        if n and not nl.get(n):\n",
     "replace": "        if n:\n",
     "matches": 1},
    {"why": "a reader failure is dropped silently, indistinguishable from a measured miss",
     "file": "tv/control_app.py",
     "find": "    if isinstance(loc, TooltipLocUnknown):\n        row[\"tooltip_loc_unknown\"] = loc.why\n        return\n",
     "replace": "    if isinstance(loc, TooltipLocUnknown):\n        return\n",
     "matches": 1},
    {"why": "a frame whose read already failed is read again for every row on it",
     "file": "tv/control_app.py",
     "find": "                if isinstance(cache, dict):\n                    cache[ck] = (\"unknown\", why, None, None)\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "one frame is OCR'd once per kai row instead of once per compile",
     "file": "tv/control_app.py",
     "find": "                if isinstance(cache, dict):\n                    cache[ck] = (\"measured\", rect, fw, fh)\n",
     "replace": "                pass\n",
     "matches": 1},
    {"why": "the compile never joins the judge row's rect to a panel, so the register keeps loc None",
     "file": "tv/control_app.py",
     "find": "        if isinstance(r, dict) and r.get(\"lane\") == \"kai\":\n            _kai_stamp_tooltip_loc(r, _tip_by_frame)\n",
     "replace": "",
     "matches": 1},
    {"why": "a frame read with no tooltip on it is recorded as UNKNOWN, as if the read had failed",
     "file": "tv/control_app.py",
     "find": "    if not rect or not fw or not fh:\n        return None\n    try:\n        import tooltip_find as _tf\n        return _tf.place_of(rect, fw, fh)\n",
     "replace": "    if not rect or not fw or not fh:\n        return TooltipLocUnknown(\"no rect\")\n    try:\n        import tooltip_find as _tf\n        return _tf.place_of(rect, fw, fh)\n",
     "matches": 1},
]


if __name__ == "__main__":
    try:
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    unittest.main(verbosity=1)
