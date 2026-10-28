#!/usr/bin/env python3
"""The tooltip backend keeps a READ FAILURE apart from a measured miss (v3730 / REG-2218 follow-ups).

Three cross-family findings on v3730, each a way the "unknown vs measured" line the tooltip lane is
built on could be crossed in silence:

  (1) A corrupt / locked / unreadable JPEG is a READ FAILURE, not "looked, and no tooltip here".
      density() used to RETURN (None, why) when the frame could not be opened, which locate() passed
      up and _kai_tooltip_place cached as ('measured', None) -- a miss nobody measured. It now RAISES
      LocateFailed, the one signal both callers already treat as unknown, so the kai row records
      tooltip_loc_unknown and files no panel. A MISSING frame and a frame with NO TEXT stay the
      graceful refusals they already were, so measured misses are not turned into unknowns.

  (2) The source frame handle is released. Image.open(...).convert('RGB') never closed the JPEG, so a
      re-sweep on Windows could hit a sharing-violation on the same file. A context manager closes it
      before the tile loop runs.

  (3) The per-frame locate cache keys on (path, reader), not the path alone. Two kai rows can share a
      frame and carry different tooltipReaders; the old key served one reader's rect to the other --
      a fake hit or a skipped real read.
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
    """A real, decodable image. locate() opens the file before it asks the reader."""
    from PIL import Image
    d = tempfile.mkdtemp()
    p = os.path.join(d, "frame.jpg")
    Image.new("RGB", (w, h), (12, 10, 8)).save(p, "JPEG", quality=60)
    return p


def _corrupt_frame():
    """A file that EXISTS (so os.path.isfile passes) but is not a decodable image."""
    d = tempfile.mkdtemp()
    p = os.path.join(d, "frame.jpg")
    with open(p, "wb") as fh:
        fh.write(b"this is not a JPEG, the open must fail")
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


class TestACorruptFrameIsUnknownNotAMeasuredMiss(unittest.TestCase):
    """The exact gap v3730 / REG-2218 set out to close: a frame that cannot be read is UNKNOWN."""

    def test_locate_raises_on_a_frame_it_cannot_open(self):
        # A read failure is not the refusal locate() makes for a frame with too little text.
        with self.assertRaises(TF.LocateFailed):
            TF.locate(_corrupt_frame())

    def test_a_missing_frame_is_still_a_graceful_refusal_not_a_raise(self):
        # Unchanged contract: a path with nothing at it refuses, it does not raise.
        rect, why = TF.locate("/nope/not/here.jpg")
        self.assertIsNone(rect)
        self.assertIn("no frame", why or "")

    def test_the_compile_files_a_corrupt_frame_as_unknown_not_a_panel(self):
        row = _kai({"framePath": _corrupt_frame()})
        reg = {r["name"]: r for r in ca._kai_compile_register([row])}
        filed = (reg.get("Windforce") or {}).get("loc")
        self.assertNotIn(filed, ("stash", "on him"),
                         "a frame that could not be read was filed as a panel: %r" % (filed,))
        self.assertTrue(row.get("tooltip_loc_unknown"),
                        "a read failure read as a measured miss -- the unknown-vs-measured gap")
        self.assertNotIn("Windforce", row.get("names_loc") or {})

    def test_a_frame_that_was_read_with_no_text_stays_a_measured_miss(self):
        # The other side of the line: a frame that WAS read and carried no tooltip is not unknown.
        row = _kai({"framePath": _frame(1440, 936),
                    "tooltipReader": (lambda _p: {"lines": []})})
        ca._kai_compile_register([row])
        self.assertNotIn("tooltip_loc_unknown", row,
                         "a measured miss was mislabelled a read failure")


class TestTheSourceFrameHandleIsReleased(unittest.TestCase):
    """A re-sweep on Windows must not find the JPEG still open from the last sweep."""

    def test_density_closes_the_source_image(self):
        import PIL.Image as _P
        real_open = _P.open
        seen = []

        class _Tracked:
            def __init__(self, img):
                self._img = img
                self.closed = False

            def __enter__(self):
                return self

            def __exit__(self, *a):
                self.close()
                return False

            def convert(self, mode):
                return self._img.convert(mode)

            def close(self):
                self.closed = True
                try:
                    self._img.close()
                except Exception:
                    pass

        def fake_open(path, *a, **k):
            t = _Tracked(real_open(path, *a, **k))
            seen.append(t)
            return t

        _P.open = fake_open
        try:
            d, why = TF.density(_frame(300, 300), cols=2, rows=2,
                                reader=_fake(_grid(2, 2, {(0, 0): 1})))
        finally:
            _P.open = real_open
        self.assertTrue(seen, "density never opened the frame")
        self.assertTrue(seen[0].closed,
                        "the source frame handle was left open -- a re-sweep on Windows locks it")


class TestTwoReadersOnOneFrameDoNotConflate(unittest.TestCase):
    """The locate cache is keyed on (path, reader): different readers never share a verdict."""

    def test_a_second_reader_on_the_same_frame_is_not_served_the_first_ones_rect(self):
        frame = _frame(1440, 936)
        cache = {}
        # Reader A puts the dense text on the LEFT (stash); reader B on the RIGHT (on him).
        left = _kai({"framePath": frame,
                     "tooltipReader": _fake(_grid(6, 6, {(2, 0): 8, (2, 1): 8}))})
        right = _kai({"framePath": frame,
                      "tooltipReader": _fake(_grid(6, 6, {(2, 4): 8, (2, 5): 8}))})
        self.assertEqual(ca._kai_tooltip_place(left, cache), "stash")
        self.assertEqual(ca._kai_tooltip_place(right, cache), "on him",
                         "the second reader was served the first reader's cached rect")

RED_PROOF = [
    {"why": "v3730 - a corrupt or locked JPEG returns (None, why), which the compile caches as a measured miss nobody measured",
     "file": "tv/tooltip_find.py",
     "find": "        raise LocateFailed(\"the frame could not be opened: %s\" % str(e)[:60]) from e\n",
     "replace": "        return None, \"the frame could not be opened: %s\" % str(e)[:60]\n",
     "matches": 1},
    {"why": "a frame that is simply not there raises as a read failure instead of the graceful refusal it is",
     "file": "tv/tooltip_find.py",
     "find": "    if not frame_path or not os.path.isfile(frame_path):\n        return None, \"no frame at %r\" % (frame_path,)\n",
     "replace": "    if not frame_path or not os.path.isfile(frame_path):\n        raise LocateFailed(\"no frame at %r\" % (frame_path,))\n",
     "matches": 1},
    {"why": "the source JPEG handle is left open until GC, so a re-sweep on Windows hits a sharing violation",
     "file": "tv/tooltip_find.py",
     "find": "        with Image.open(frame_path) as _src:\n            im = _src.convert(\"RGB\")\n",
     "replace": "        im = Image.open(frame_path).convert(\"RGB\")\n",
     "matches": 1},
    {"why": "a frame read with too little text is raised as a read failure, so a measured miss is mislabelled unknown",
     "file": "tv/tooltip_find.py",
     "find": "    if total < min_lines:\n        return None, (\"only %d text line(s) in the whole frame",
     "replace": "    if total < min_lines:\n        raise LocateFailed(\"only %d text line(s) in the whole frame\" % total)\n        return None, (\"only %d text line(s) in the whole frame",
     "matches": 1},
    {"why": "the per-frame locate cache keys on the path alone, so a second reader is served the first one's rect",
     "file": "tv/control_app.py",
     "find": "        ck = (path, reader)\n",
     "replace": "        ck = path\n",
     "matches": 1},
]


if __name__ == "__main__":
    try:
        import console_safe as _cs
        _cs.enable()
    except Exception:
        pass
    unittest.main(verbosity=1)
