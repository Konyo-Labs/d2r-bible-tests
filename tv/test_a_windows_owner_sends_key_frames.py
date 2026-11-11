# -*- coding: utf-8 -*-
"""#218 (REG-3033, GrokBot v3836 glass pass, #230 6485132266) - A WINDOWS OWNER SENDS ITS KEY FRAMES TOO.

In the Mac's shadow of the ALT, 📚 Their sessions listed 16 sessions and every row said "no pictures - this PC has no
thumbnail resizer". The site's ALT frames record (t 03:00:36) held 16 sessions and 0 frames. The digest's resizer was
sips alone, and sips is macOS; Pillow, which every Windows boot installs (start_tvd_win.ps1, #227), was never asked.
Now the default resizer is sips on a Mac, else Pillow: the film-size JPEG (1920 px, never larger than its source) into
the theatre's cache1920, written beside and moved into place. A PC with neither still says "no thumbnail resizer"; a PC
whose resizer failed on one frame says that, not that it has none. v3894 raised the caps so a 1920x1080 frame can ride
(800 KB a frame, 12 MB a record); a 160 px thumb is no longer what the theatre plays.

The PC is made a Windows PC for the length of one call (sys.platform), so this law is RED on the old sips-only default
on a Mac too, where sips would otherwise answer. Driven on fixture frames in a temp dir - never his. RED_PROOF below.
"""
import base64
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx  # noqa: E402
_fx.contain()
import shadow_sessions as SS  # noqa: E402
from PIL import Image  # noqa: E402

SID = "s_1794000000000_7"
T0 = 1794000060000


def _jpeg(path, size):
    im = Image.new("RGB", size)
    px = im.load()
    for x in range(0, size[0], 7):
        for y in range(0, size[1], 5):
            px[x, y] = ((x * 3) % 256, (y * 5) % 256, ((x + y) * 7) % 256)
    im.save(path, "JPEG", quality=90)


def _rows(n=3):
    rows = []
    for k in range(n):
        c = T0 + k * 1000
        rows.append({"ts": c, "captureTs": c, "frameId": "%d_%d" % (k + 1, c), "sessionId": SID, "lane": "deep",
                     "scene": "stash", "names": (["Shako"] if k == 1 else [])})
    return rows


class _NoPillow(object):
    """sys.modules entries of None make `import PIL` / `from PIL import Image` raise ImportError."""

    def __enter__(self):
        self.p = mock.patch.dict(sys.modules, {"PIL": None, "PIL.Image": None})
        self.p.start()
        return self

    def __exit__(self, *a):
        self.p.stop()


class AWindowsOwnerSendsItsKeyFrames(unittest.TestCase):

    def setUp(self):
        import control_app as ca
        self.is_read = ca._is_a_live_read
        self.d = tempfile.mkdtemp(prefix="win_key_frames_")
        for r in _rows():
            _jpeg(os.path.join(self.d, r["frameId"] + ".jpg"), (1920, 1080))

    def tearDown(self):
        shutil.rmtree(self.d, True)

    def _digest_as_windows(self, rows=None):
        with mock.patch.object(SS.sys, "platform", "win32"):
            return SS.digest(rows or _rows(), self.d, self.is_read, T0 + 3600000)

    def test_a_pc_with_no_sips_makes_a_film_jpeg_and_sends_it(self):
        o = self._digest_as_windows()
        s = o["sessions"][0]
        self.assertTrue(s["frames"], "a PC with no sips sent no picture: %r" % s["why"])
        self.assertIsNone(s["why"])
        for f in s["frames"]:
            data = base64.b64decode(f["jpg"])
            self.assertEqual(data[:3], b"\xff\xd8\xff", "a key frame is not a JPEG")
            self.assertLessEqual(len(data), SS.MAX_THUMB)
            with Image.open(io.BytesIO(data)) as im:
                self.assertEqual(max(im.size), SS.SHADOW_FRAME_PX, "a 1920 px frame did not ride at film size: %r"
                                 % (im.size,))
            self.assertTrue(os.path.isfile(os.path.join(self.d, SS.SHADOW_CACHE, f["id"] + ".jpg")),
                            "the film frame was not kept in the shadow cache")
        self.assertEqual([x for x in _fx.list_own(os.path.join(self.d, SS.SHADOW_CACHE)) if x.endswith(".part")], [])

    def test_a_small_frame_is_never_enlarged(self):
        rows = _rows(1)
        _jpeg(os.path.join(self.d, rows[0]["frameId"] + ".jpg"), (120, 68))
        o = self._digest_as_windows(rows)
        data = base64.b64decode(o["sessions"][0]["frames"][0]["jpg"])
        with Image.open(io.BytesIO(data)) as im:
            self.assertEqual(im.size, (120, 68), "a small frame was resized up")

    def test_a_pc_with_neither_resizer_still_says_so(self):
        with _NoPillow():
            with mock.patch.object(SS.sys, "platform", "win32"):
                self.assertEqual(SS.resizers(), [], "a PC with neither sips nor Pillow listed a resizer")
            o = self._digest_as_windows()
        s = o["sessions"][0]
        self.assertEqual(s["frames"], [])
        self.assertIn("no thumbnail resizer", s["why"] or "", "a PC with no resizer said nothing true: %r" % s["why"])

    def test_a_resizer_that_failed_is_not_a_pc_without_one(self):
        rows = _rows(1)
        with open(os.path.join(self.d, rows[0]["frameId"] + ".jpg"), "wb") as fh:
            fh.write(b"\xff\xd8 not a picture")
        o = self._digest_as_windows(rows)
        s = o["sessions"][0]
        self.assertEqual(s["frames"], [])
        self.assertIn("could not be made (Pillow failed on it)", s["why"] or "",
                      "a failed resize read as a PC with no resizer: %r" % s["why"])
        self.assertEqual(_fx.list_own(os.path.join(self.d, SS.SHADOW_CACHE)), [],
                         "a failed resize left a file the next pass would take as the thumbnail")

    def test_a_write_that_fails_leaves_no_half_file(self):
        rows = _rows(1)
        with mock.patch.object(SS.os, "replace", side_effect=OSError("disk full")):
            o = self._digest_as_windows(rows)
        self.assertEqual(o["sessions"][0]["frames"], [])
        self.assertEqual(_fx.list_own(os.path.join(self.d, SS.SHADOW_CACHE)), [],
                         "a resize that failed after writing left its part file behind")


RED_PROOF = [
    {"why": "REG-3033 - the digest asks sips alone again (a Windows owner sends no picture)",
     "file": "shadow_sessions.py",
     "find": "def digest(rows, hist_dir, is_read, now_ms, make=_make_thumb, witness_ids=None, chron_count=None, is_game=None,\n",
     "replace": "def digest(rows, hist_dir, is_read, now_ms, make=_sips_thumb, witness_ids=None, chron_count=None, is_game=None,\n",
     "matches": 1},
    {"why": "REG-3033 - the default resizer never falls back to Pillow",
     "file": "shadow_sessions.py",
     "find": "    return _sips_thumb(src, dst, SHADOW_FRAME_PX, SHADOW_JPEG_Q) or _pil_thumb(src, dst, SHADOW_FRAME_PX, SHADOW_JPEG_Q)\n",
     "replace": "    return _sips_thumb(src, dst)\n",
     "matches": 1},
    {"why": "REG-3582 - Pillow shrinks the film frame to a 160 px thumbnail the theatre would magnify",
     "file": "shadow_sessions.py",
     "find": "            small.thumbnail((max_px, max_px))  # never enlarges a small frame\n",
     "replace": "            small.thumbnail((160, 160))  # the old shadow thumb\n",
     "matches": 1},
    {"why": "REG-3033 - Pillow enlarges a small frame to 160 px",
     "file": "shadow_sessions.py",
     "find": "            small.thumbnail((max_px, max_px))  # never enlarges a small frame\n",
     "replace": "            small = small.resize((max_px, max_px * small.size[1] // small.size[0]))\n",
     "matches": 1},
    {"why": "REG-3033 - a resizer that failed on one frame says the PC has none",
     "file": "shadow_sessions.py",
     "find": "            if make is _make_thumb and resizers():\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3033 - a PC with no Pillow is counted as having it",
     "file": "shadow_sessions.py",
     "find": "        import PIL.Image  # noqa: F401\n        out.append(\"Pillow\")\n    except Exception:\n        pass\n",
     "replace": "        import PIL.Image  # noqa: F401\n    except Exception:\n        pass\n    out.append(\"Pillow\")\n",
     "matches": 1},
    {"why": "REG-3033 - a failed resize leaves its half-written file behind",
     "file": "shadow_sessions.py",
     "find": "        try:\n            os.remove(tmp)\n        except OSError:\n            pass\n        return False\n",
     "replace": "        return False\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
