# -*- coding: utf-8 -*-
"""#158.7 (REG-2915) - THE TOOLTIP CROP IS CUT FROM THE BOX THE READ THAT NAMED THE ITEM RETURNED.

The crop that NAMED an item (#45, v2239) was found by frame differencing: the frame before a hover against the hover. On his
reels the D2R world animates behind the panel, so the change box covers 53-91% of the frame and the 60 KB cap rightly
refuses it - the lane produced nothing. The vision read that names the item already SAW the tooltip, so it now returns the
tooltip's box ("tip": [left, top, right, bottom] in the picture it saw). The sweep places that box on the frame through the
read's own picture map (the one its item points use), pads it, keeps it inside the frame and cuts the crop from it, scaled to
a 512 px longest side; the byte cap stays the backstop. The crop is evidence for him to look at, never a witness.

The box is optional. A read without it behaves as before - the frame-difference crop, or why there is none - and says the box
is UNKNOWN. A box that cannot be placed (no picture map), or that covers more of the frame than a tooltip can, is refused with
its reason: never a full-frame crop. The prompt version moved (vp-reg2915) and lists vp3554 as asking the same question, so
no sealed reel reopens: crops come from reads made from now on.

Driven on a FIXTURE reel whose frames all differ (the world animating), through vault_retro.sweep with a stubbed reader;
his reels are never touched. RED_PROOF below.
"""
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
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import fixture_tmp as _fx  # noqa: E402
_fx.contain()

import chronicle_retro as cr  # noqa: E402
import tooltip_crop as tc  # noqa: E402
import vault_retro as v  # noqa: E402

try:
    from PIL import Image, ImageDraw
except Exception:   # pragma: no cover - the law says so rather than passing
    Image = None

W, H = 1440, 900
SCALE = 0.7                                 # the reader saw a smaller picture than the frame, as a real read does
TIP = (520, 180, 820, 740)                  # the planted tooltip, in the frame: 300 x 560
REEL = "reel_s_1500000000077_1"
NAMES = ("Shako", "Harlequin Crest", "Arachnid Mesh", "War Traveler", "Stone of Jordan")
MAP = {"space": [int(W * SCALE), int(H * SCALE)], "origin": [0, 0], "extent": [W, H], "frame": [W, H]}


def _reel(root, n=5):
    """Frames that ALL differ (the world animating behind the panel), each with the same tooltip planted at TIP."""
    d = os.path.join(root, "frames", "hist", REEL)
    os.makedirs(d)
    rows = []
    for i in range(n):
        base = (20 + 45 * i, 30 + 31 * i, 18 + 52 * i)
        im = Image.new("RGB", (W, H), base)
        dr = ImageDraw.Draw(im)
        k = 0
        for x in range(40, W - 40, 58):
            for y in range(60, H - 60, 58):
                k += 1
                dr.rectangle([x, y, x + 52, y + 52], outline=(52 + i * 20, 46, 38), fill=(26 + 9 * i, 23, 20))
                if k % 3:
                    dr.rectangle([x + 8, y + 8, x + 44, y + 44], fill=((196, 154, 68), (108, 108, 214), (52, 168, 96))[k % 3])
        dr.rectangle(list(TIP), fill=(8, 8, 8), outline=(190, 170, 110))
        for j in range(12):
            dr.text((TIP[0] + 16, TIP[1] + 18 + 40 * j), NAMES[i % len(NAMES)] if j == 0 else "+%d to a stat line" % (j + 1),
                    fill=(190, 170, 110))
        f = "%s_%04d.jpg" % (REEL, i)
        im.save(os.path.join(d, f), "JPEG", quality=90)
        rows.append({"f": f, "ts": 1500000077000 + i * 1000})
    with io.open(os.path.join(d, "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"reel": REEL, "frames": rows, "focus": "stash", "synthetic": True}, fh)
    return d


def tearDownModule():
    """The sweep's frame work wakes the agent's shared OCR worker; it leaves with this law, by its own stop."""
    td = sys.modules.get("tv_diablo")
    if td is not None:
        try:
            td._OCR.stop()
        except Exception:
            pass


def _box_in_read_space():
    return [TIP[0] * SCALE, TIP[1] * SCALE, TIP[2] * SCALE, TIP[3] * SCALE]


@unittest.skipIf(Image is None, "Pillow is absent - the fixture frames cannot be built, so this law is UNMEASURED here")
class TheCropIsCutFromTheReadsBox(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="tip_crop_")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.d = _reel(self.root)
        self.store = os.path.join(self.root, "frames", "hist", v.CROP_DIR)

    def _sweep(self, tip=True):
        def reader(path, surface):
            item = {"name": "Shako", "kind": "item"}
            if tip:
                item["tip"] = _box_in_read_space()
            return {"items": [item], "conf": 0.95, "xy": dict(MAP)}
        res = v.sweep([self.d], sig=cr.jpeg_sig, reader=reader, classify=lambda *a, **k: "stash",
                      panel_gate=lambda p: "stash")
        rows = (res.get("owned") or []) + (res.get("unsure") or [])
        looks = [w for r in rows for w in (r.get("witnesses") or [])]
        self.assertTrue(looks, "PREMISE: the fixture reel produced no looks at all: %s" % str(res.get("why"))[:160])
        return looks

    def test_the_premise_frame_differencing_cannot_find_it(self):
        """As on his reels: what changed between two frames is most of the frame, so the difference box is no tooltip."""
        fs = sorted(f for f in os.listdir(self.d) if f.endswith(".jpg"))
        for a, b in zip(fs, fs[1:]):
            rect, why = tc.changed_rect(os.path.join(self.d, a), os.path.join(self.d, b))
            if rect is not None:
                frac = float((rect[2] - rect[0]) * (rect[3] - rect[1])) / (W * H)
                self.assertGreater(frac, 0.5, "PREMISE: differencing found a tooltip-sized box %r on frames that all differ"
                                   % (rect,))

    def test_every_look_carries_the_crop_cut_from_its_box(self):
        looks = self._sweep(tip=True)
        cut = [w for w in looks if w.get("crop")]
        self.assertEqual(len(cut), len(looks), "a look whose read boxed its tooltip carries no crop: %r"
                         % [w.get("cropWhy") for w in looks if not w.get("crop")][:2])
        self.assertTrue(all(w.get("cropFrom") == "tooltip box" for w in cut), [w.get("cropFrom") for w in cut])
        rect, why = tc.rect_from_read_box(_box_in_read_space(), MAP)
        px, py = tc.TIP_PAD_FRAC * W, tc.TIP_PAD_FRAC * H
        want = (TIP[0] - px, TIP[1] - py, TIP[2] + px, TIP[3] + py)
        self.assertLessEqual(max(abs(rect[i] - want[i]) for i in range(4)), 2,
                             "the read's box was placed at %r on the frame, not around the tooltip %r" % (rect, want))
        for w in cut:
            p = os.path.join(self.root, "frames", "hist", w["crop"])
            self.assertTrue(os.path.isfile(p), "the crop the look names was never written: %s" % w["crop"])
            self.assertLessEqual(os.path.getsize(p), v.CROP_MAX_BYTES)
            im = Image.open(p)
            self.assertLessEqual(max(im.size), tc.TIP_MAX_SIDE, "the crop was kept at %r, past the %d px side"
                                 % (im.size, tc.TIP_MAX_SIDE))
            # the tooltip's own dark body fills the middle of the crop - it is a picture of the tooltip, not the panel
            mid = im.convert("RGB").getpixel((im.size[0] // 2, im.size[1] // 2))
            self.assertLess(sum(mid), 60, "the middle of the crop is not the tooltip: %r" % (mid,))

    def test_a_read_with_no_box_behaves_as_before_and_says_so(self):
        looks = self._sweep(tip=False)
        self.assertEqual([w for w in looks if w.get("crop")], [], "a read with no box got a crop on frames that all differ")
        whys = [w.get("cropWhy") or "" for w in looks]
        for why in whys:
            self.assertTrue(why.startswith("the read gave no tooltip box (UNKNOWN); "), why)
            self.assertNotEqual(why.split("; ", 1)[1], "no reason", "the frame-difference crop's own reason was lost")
        self.assertTrue(any("larger than %d bytes" % v.CROP_MAX_BYTES in w for w in whys),
                        "PREMISE: the byte cap never refused a frame-difference box on this reel: %r" % whys[:3])
        self.assertFalse(os.path.isdir(self.store) and [f for f in os.listdir(self.store) if f.endswith(".jpg")],
                         "a crop was written with no box")

    def test_a_box_too_big_to_be_a_tooltip_is_refused_never_a_full_frame_crop(self):
        rel, why = v._crop_from_box(self.d, sorted(os.listdir(self.d))[0], [0, 0] + MAP["space"], dict(MAP), self.store)
        self.assertIsNone(rel, "a whole-picture box was cut as a crop")
        self.assertIn("not a tooltip", why)
        self.assertFalse(os.path.isdir(self.store) and [f for f in os.listdir(self.store) if f.endswith(".jpg")])

    def test_a_box_with_no_picture_map_is_unknown_never_assumed(self):
        rel, why = v._crop_from_box(self.d, sorted(os.listdir(self.d))[0], _box_in_read_space(), None, self.store)
        self.assertIsNone(rel)
        self.assertIn("UNKNOWN", why)


class TheReaderIsAskedForTheBox(unittest.TestCase):

    def test_the_prompt_asks_for_it_and_its_version_moved(self):
        import tv_diablo as tv
        p = tv.VAULT_READ_PROMPT.format(path="IMG", surface="stash")
        self.assertIn('"tip":[<left>,<top>,<right>,<bottom>] or null', p)
        self.assertNotEqual(tv.VAULT_PROMPT_VER, "vp3554", "the prompt changed and its version did not")
        self.assertEqual(tv.VAULT_PROMPT_ANSWERS_SAME_AS[0], "vp3554",
                         "the reader that only added the box is not listed as asking vp3554's question")

    def test_no_sealed_reel_reopens_for_it(self):
        import control_app as ca
        self.assertTrue(ca._vault_still_sealed({"rows": 0, "promptVer": "vp3554"}),
                        "a vp3554 seal reopened - every old reel would be read and paid for again")

    def test_the_parser_keeps_a_box_and_refuses_a_bad_one(self):
        ok = v.normalize_item({"name": "Shako", "tip": [10, 20, 110, 220]}, "stash", "stash", 0.9)
        self.assertEqual(ok["tip"], [10.0, 20.0, 110.0, 220.0])
        for bad in (None, [1, 2, 3], [10, 20, 5, 30], ["a", 1, 2, 3], [-1, 0, 5, 5]):
            self.assertIsNone(v.normalize_item({"name": "Shako", "tip": bad}, "stash", "stash", 0.9)["tip"], bad)


RED_PROOF = [
    {"why": "REG-2915 - the sweep never cuts a crop from the read's box (the differencing crop alone, which finds nothing)",
     "file": "tv/vault_retro.py",
     "find": "                    if item.get(\"tip\"):\n",
     "replace": "                    if False:\n",
     "matches": 1},
    {"why": "REG-2915 - the parser drops the read's tooltip box",
     "file": "tv/vault_retro.py",
     "find": "        \"tip\": _box_of(raw.get(\"tip\")),\n",
     "replace": "        \"tip\": None,\n",
     "matches": 1},
    {"why": "REG-2915 - the box is placed on the frame without the read's picture scale",
     "file": "tv/tooltip_crop.py",
     "find": "    fx0 = max(0, int(ox + x0 * ew / sw - px))\n",
     "replace": "    fx0 = max(0, int(ox + x0 - px))\n",
     "matches": 1},
    {"why": "REG-2915 - a box covering most of the frame is cut as a crop",
     "file": "tv/tooltip_crop.py",
     "find": "    if frac > MAX_FRAC:\n        return None, (\"the read's tooltip box covers",
     "replace": "    if False:\n        return None, (\"the read's tooltip box covers",
     "matches": 1},
    {"why": "REG-2915 - a read-box crop is kept at full size, up against the byte cap",
     "file": "tv/vault_retro.py",
     "find": "rect, dest, max_side=_tc.TIP_MAX_SIDE)",
     "replace": "rect, dest, max_side=None)",
     "matches": 1},
    {"why": "REG-2915 - a read with no box stops saying the box is UNKNOWN",
     "file": "tv/vault_retro.py",
     "find": "                            _crop_why = \"the read gave no tooltip box (UNKNOWN); \" + str(_crop_why or \"no reason\")\n",
     "replace": "                            pass\n",
     "matches": 1},
    {"why": "REG-2915 - the prompt stops asking for the tooltip box",
     "file": "tv/tv_diablo.py",
     "find": "    '\"tip\":[<left>,<top>,<right>,<bottom>] or null,'\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
