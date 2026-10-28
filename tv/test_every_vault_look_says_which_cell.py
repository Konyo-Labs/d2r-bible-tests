# -*- coding: utf-8 -*-
"""#146 step 3b (v3554, REG-1706) - EVERY VAULT LOOK SAYS WHICH CELL, FROM NOW ON.

His words, 2026-10-01: "the items being witnessed also need coordinates based on where they were witnessed", and on the
cost: "thats even better" to asking from now on without re-reading his old footage. v3552 asked the deep reader; this
asks the VAULT reader, whose looks are what the vault and the character window are built from.

MEASURED before it was written: 16 vault items, 158 looks, 0 with a cell. And one trap the build had to close first:
the item lanes sent the RAW reel frame (up to HIST_MAX_PX, 2560 px) and the reader scales anything over 1568 px down
before it looks - so a point it returned would have lived in a space nobody recorded.

What this law drives:
  * the question - VAULT_READ_PROMPT asks each item's point (the ITEM, never its tooltip), and only ADDS it: vp3368's
    seals still stand, a reader that asked a different question still reopens
  * the space - the real claude_vault_read sends a frame no wider than 1568 px and returns the map of where its points
    live (space / origin / extent / frame); a tally band's crop carries its own origin
  * the placing - vault_retro.place_on_grid scales a point to the frame and names the stash/inventory cell or the doll
    slot, and says why when it cannot
  * the record - the banked witness keeps the point and the cell
RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import tv_diablo as tv  # noqa: E402
import control_app as ca  # noqa: E402
import vault_retro as vr  # noqa: E402
import slot_identity as SI  # noqa: E402

try:
    from PIL import Image as _Img
except Exception:          # pragma: no cover - Pillow is installed in CI and on his Mac
    _Img = None


def _jpeg(path, w, h):
    _Img.new("RGB", (w, h), (20, 20, 20)).save(path, quality=80)
    return path


class TheReaderIsAskedWhere(unittest.TestCase):

    def test_the_item_shape_has_a_point(self):
        p = tv.VAULT_READ_PROMPT.format(path="IMG", surface="stash")
        self.assertIn('"xy":[<x>,<y>] or null', p)
        self.assertIn("NEVER the tooltip box", p, "a point on the tooltip would file the item where the tooltip floats")

    def test_a_vp3368_seal_still_stands(self):
        # REG-2915 - vp-reg2915 only added the tooltip box, so it lists vp3554 too; vp3368 still stands
        self.assertIn("vp3368", tv.VAULT_PROMPT_ANSWERS_SAME_AS)
        self.assertTrue(ca._vault_still_sealed({"rows": 0, "promptVer": "vp3368"}),
                        "an old empty vault seal reopened - every old reel would be read and paid for again")
        self.assertTrue(ca._vault_still_sealed({"rows": 0, "promptVer": tv.VAULT_PROMPT_VER}))

    def test_a_reader_that_asked_a_different_question_still_reopens(self):
        self.assertFalse(ca._vault_still_sealed({"rows": 0, "promptVer": "vp2017"}))
        self.assertFalse(ca._vault_still_sealed({"rows": 0, "promptVer": "vp3368"}, "vp-other"),
                         "the same-as list leaked onto a reader that is not the current one")


@unittest.skipIf(_Img is None, "Pillow is absent - the reader's picture cannot be built, UNMEASURED")
class TheReaderSeesAPictureOfKnownSize(unittest.TestCase):

    def setUp(self):
        self.td = tempfile.mkdtemp(prefix="vault_cell_")
        self.addCleanup(shutil.rmtree, self.td, True)
        self.sent = []
        saved = (tv._oneshot, tv._is_throttled, tv._sub_budget_check)
        self.addCleanup(lambda: (setattr(tv, "_oneshot", saved[0]), setattr(tv, "_is_throttled", saved[1]),
                                 setattr(tv, "_sub_budget_check", saved[2])))
        tv._is_throttled = lambda *a, **k: False
        tv._sub_budget_check = lambda *a, **k: None

        def fake(path, model, timeout=90, prompt=None, raw_json=False, **_extra):
            self.sent.append(path)
            return {"items": [{"name": "Shako", "kind": "item", "xy": [10, 20]}], "conf": 0.9}
        tv._oneshot = fake

    def test_a_big_item_frame_goes_at_the_read_spec_and_says_its_space(self):
        frame = _jpeg(os.path.join(self.td, "f_1.jpg"), 2560, 1600)
        got = tv.claude_vault_read(frame, "stash")
        self.assertEqual(len(self.sent), 1, self.sent)
        import equipped_ledger as EL
        w, h = EL.jpeg_size(self.sent[0])
        self.assertLessEqual(max(w, h), 1568, "the reader was sent %dx%d - it scales that itself, invisibly" % (w, h))
        self.assertEqual(got["xy"], {"space": [w, h], "origin": [0, 0], "extent": [2560, 1600], "frame": [2560, 1600]})

    def test_a_frame_within_the_spec_is_sent_as_it_is(self):
        frame = _jpeg(os.path.join(self.td, "f_2.jpg"), 1440, 904)
        got = tv.claude_vault_read(frame, "stash")
        self.assertEqual(self.sent, [os.path.abspath(frame)])
        self.assertEqual(got["xy"]["space"], [1440, 904])

    def test_a_tally_crop_carries_its_origin(self):
        frame = _jpeg(os.path.join(self.td, "f_3.jpg"), 1440, 904)
        got = tv.claude_vault_read(frame, "runes")
        m = got.get("xy")
        self.assertIsNotNone(m)
        if m["extent"] == [1440, 904]:
            self.skipTest("no calibrated tally band at this aspect - the crop path did not run, UNMEASURED here")
        self.assertGreater(m["origin"][0] + m["origin"][1], 0, m)
        self.assertEqual(m["frame"], [1440, 904])


class ThePointLandsInItsCell(unittest.TestCase):
    """his Mac's frames are 1440x904; a reader shown a half-size copy points at 720x452"""

    def setUp(self):
        box, why = SI.panel_box_for(1440, 904, container="stash")
        self.assertIsNotNone(box, why)
        (self.fx, self.fy), _ = SI.point_of_cell(3, 4, box, "stash")
        self.half = {"space": [720, 452], "origin": [0, 0], "extent": [1440, 904], "frame": [1440, 904]}

    def test_a_point_from_a_half_size_picture_lands_in_its_cell(self):
        got = vr.place_on_grid([self.fx / 2.0, self.fy / 2.0], self.half, "stash")
        self.assertEqual(got["cell"], "stash:c3r4", got)
        self.assertIsNone(got["why"])

    def test_without_its_space_the_same_point_lands_elsewhere(self):
        """premise: the case above can only pass by scaling"""
        same = dict(self.half, space=[1440, 904])
        got = vr.place_on_grid([self.fx / 2.0, self.fy / 2.0], same, "stash")
        self.assertNotEqual(got["cell"], "stash:c3r4", got)

    def test_a_crop_origin_is_added_back(self):
        crop = {"space": [400, 300], "origin": [self.fx - 100, self.fy - 100], "extent": [400, 300],
                "frame": [1440, 904]}
        self.assertEqual(vr.place_on_grid([100, 100], crop, "stash")["cell"], "stash:c3r4")

    def test_every_refusal_says_why(self):
        self.assertIn("no point", vr.place_on_grid(None, self.half, "stash")["why"])
        self.assertIn("unknown", vr.place_on_grid([1, 1], None, "stash")["why"])
        self.assertIn("outside", vr.place_on_grid([9999, 1], self.half, "stash")["why"])
        self.assertIsNone(vr.place_on_grid([9999, 1], self.half, "stash")["cell"])

    def test_the_parser_keeps_a_point_and_drops_a_malformed_one(self):
        self.assertEqual(vr.normalize_item({"name": "Shako", "xy": [10, 20]}, "stash", "stash", 0.9)["xy"], [10.0, 20.0])
        for bad in ([1], "10,20", [-1, 5], [None, 2], {"x": 1}):
            self.assertIsNone(vr.normalize_item({"name": "Shako", "xy": bad}, "stash", "stash", 0.9)["xy"], bad)


class TheWitnessKeepsWhere(unittest.TestCase):

    def test_the_banked_witness_keeps_the_point_and_the_cell(self):
        e = {"session": "s1", "frame": "f1", "lane": "stash", "point": [530.5, 702.0], "cell": "stash:c3r4",
             "cellWhy": None}
        row = vr._witness_rows([e])[0]
        self.assertEqual(row.get("point"), [530.5, 702.0])
        self.assertEqual(row.get("cell"), "stash:c3r4")

    def test_the_sighting_literal_names_where(self):
        import ast
        with io.open(os.path.join(HERE, "vault_retro.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        keys = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict) and any(
                    isinstance(t, ast.Name) and t.id == "sight" for t in node.targets):
                keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
        self.assertIsNotNone(keys)
        for k in ("point", "cell", "cellWhy"):
            self.assertIn(k, keys)


class WhereItWasOutranksWhatItWasCalled(unittest.TestCase):
    """REG-1911 - a 'stash' sighting whose point is on the INVENTORY grid is filed as inventory (held, never a
    locker); an 'inventory' sighting whose point is on the stash grid is NOT promoted to stash."""

    def setUp(self):
        self.map = {"space": [1440, 904], "origin": [0, 0], "extent": [1440, 904], "frame": [1440, 904]}
        ibox, why = SI.panel_box_for(1440, 904, container="inventory")
        self.assertIsNotNone(ibox, why)
        (self.ix, self.iy), _ = SI.point_of_cell(2, 1, ibox, "inventory")
        sbox, why = SI.panel_box_for(1440, 904, container="stash")
        (self.sx, self.sy), _ = SI.point_of_cell(3, 4, sbox, "stash")

    def test_the_premise_the_inventory_point_is_on_no_stash_cell(self):
        self.assertIsNone(vr.place_on_grid([self.ix, self.iy], self.map, "stash")["cell"])

    def test_a_stash_label_on_an_inventory_point_is_filed_as_inventory(self):
        lane, pl = vr.lane_by_point("stash", [self.ix, self.iy], self.map)
        self.assertEqual(lane, "inventory", "an inventory tooltip was banked as a stash witness (REG-1911)")
        self.assertTrue(str(pl["cell"]).startswith("inventory:"), pl)
        self.assertIn("reader said stash", pl["why"])

    def test_a_stash_point_stays_stash(self):
        lane, pl = vr.lane_by_point("stash", [self.sx, self.sy], self.map)
        self.assertEqual((lane, pl["cell"]), ("stash", "stash:c3r4"))

    def test_an_inventory_label_is_never_promoted_to_stash(self):
        lane, _ = vr.lane_by_point("inventory", [self.sx, self.sy], self.map)
        self.assertEqual(lane, "inventory", "a pointing error promoted an inventory read to a vault witness")

    def test_the_sweep_files_by_the_point(self):
        with io.open(os.path.join(HERE, "vault_retro.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count('item["lane"], _pl = lane_by_point(item["lane"], item.get("xy"), resp.get("xy"))'), 1,
                         "the sweep no longer files a sighting by where it was seen")


RED_PROOF = [
    {
        "why": "v3554 - the vault reader stops being asked where each item is",
        "file": "tv_diablo.py",
        "find": "    '\"quality\":\"white|blue|gold|unique|set|null\",\"xy\":[<x>,<y>] or null,'\n",
        "replace": "    '\"quality\":\"white|blue|gold|unique|set|null\",'\n",
        "matches": 1,
    },
    {
        "why": "v3554 - an old empty vault seal reopens: every old reel is read and paid for again",
        "file": "control_app.py",
        "find": "    return str(rec.get(\"promptVer\") or \"\") in (str(want),) + _vault_prompt_vers_same_as(want)\n",
        "replace": "    return str(rec.get(\"promptVer\") or \"\") == str(want)\n",
        "matches": 1,
    },
    {
        "why": "v3554 - a big item frame goes to the reader raw again, and its points live in an unrecorded space",
        "file": "tv_diablo.py",
        "find": "            _read_path = _readable_frame(ap, os.path.join(tempfile.gettempdir(), \"tvd_vault_read_%d.jpg\" % os.getpid()))\n",
        "replace": "            pass\n",
        "matches": 1,
    },
    {
        "why": "v3554 - a point is placed without scaling it from the reader's picture to the frame",
        "file": "vault_retro.py",
        "find": "    pt = [round(ox + xy[0] * ew / sw, 1), round(oy + xy[1] * eh / sh, 1)]\n",
        "replace": "    pt = [round(ox + xy[0], 1), round(oy + xy[1], 1)]\n",
        "matches": 1,
    },
    {
        "why": "v3554 - the banked witness drops the point and the cell",
        "file": "vault_retro.py",
        "find": "        for _vf in (\"sockets\", \"eth\", \"quality\", \"promptVer\", \"point\", \"cell\", \"cellWhy\", \"holder\"):   # v3767 - who holds it, and where",
        "replace": "        for _vf in (\"sockets\", \"eth\", \"quality\", \"promptVer\", \"holder\"):   # v3767 - who holds it, and where",
        "matches": 1,
    },    {
        "why": "REG-1911 - the point is ignored again: an inventory tooltip labelled stash is banked as a vault witness",
        "file": "vault_retro.py",
        "find": "    if lane == \"stash\" and pl.get(\"cell\") is None and pl.get(\"point\") is not None:\n",
        "replace": "    if False:\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
