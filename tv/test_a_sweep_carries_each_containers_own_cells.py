# -*- coding: utf-8 -*-
"""REG-3104 (#158 P4, the intake design's guided sweep) - THE SWEEP CARRIES EACH CONTAINER'S OWN CELLS TO THE BOARD.

The board can stamp a FULL LOOK (window._vaultFullLook, REG-2892) - a frame that shows a whole container, every cell its
item or empty - and nothing produced one: the reader names items from hover tooltips only, and the pixel layer's count of
the taken cells of the panel a read looked at (vault_corpus.stash_occupancy / inventory_occupancy, REG-1889) was used to
cross-check names and then dropped. Now the sweep keeps it - vault_retro.container_look per read frame, the NEWEST per
(session, container) by vault_retro.newest_container_looks - publishes it as the proposal's `containers`, and
apply_payload carries it to the board, which assembles the full look (REG-3105).
  * the container is the panel that was COUNTED: the bag is the inventory; a stash tab's own grid is the personal stash or
    a shared page by the read's tab, and a tab the read did not name is None (UNKNOWN);
  * a shared page's number is never read: `page` is always None, and the board asks him which page it was;
  * an occupancy that would not read is `occupied: None` with its reason - never an empty panel;
  * the capture time is the frame's own (f_<ms>), the session the reel's.
Pure functions on fixture occupancies (no frame is opened); the sweep's join is pinned by its own lines. RED_PROOF below.
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import vault_retro as VR  # noqa: E402

FRAME = "/fixture/hist/reel_s_1790000000001_00001/f_1790000000500.jpg"


def _occ(cols, rows, taken):
    grid = [[(c, r) in taken for c in range(cols)] for r in range(rows)]
    return {"ok": True, "occupied": len(taken), "free": cols * rows - len(taken), "grid": grid}


class TheSweepCarriesEachContainersOwnCells(unittest.TestCase):

    def test_the_bag_is_the_inventory_with_its_own_cells_and_clock(self):
        r = VR.container_look(FRAME, "stash", _occ(10, 4, {(0, 0), (3, 2)}), "inventory")
        self.assertEqual((r["session"], r["frame"], r["capturedAt"]), ("s_1790000000001_00001", "f_1790000000500.jpg", 1790000000500))
        self.assertEqual((r["location"], r["page"], r["grid"]), ("inventory", None, [10, 4]))
        self.assertEqual(r["occupied"], [[0, 0], [3, 2]])

    def test_a_stash_tab_is_its_tab_and_a_shared_page_is_never_numbered(self):
        sh = VR.container_look(FRAME, "shared", _occ(10, 10, {(1, 1)}), "stash")
        self.assertEqual((sh["location"], sh["page"]), ("shared", None))
        self.assertEqual(VR.container_look(FRAME, "personal", _occ(10, 10, set()), "stash")["location"], "stash")
        self.assertIsNone(VR.container_look(FRAME, "stash", _occ(10, 10, set()), "stash")["location"],
                          "a tab the read did not name was given one")

    def test_an_unread_panel_is_unknown_never_empty(self):
        for occ in (None, {"ok": False, "why": "no lattice"}, {"ok": True, "grid": [[True] * 10] * 3}):
            r = VR.container_look(FRAME, "personal", occ, "stash" if occ else None)
            self.assertIsNone(r["occupied"], "an unread panel became %r" % r["occupied"])
            self.assertIn("UNKNOWN", r["why"])

    def test_a_panel_that_is_no_container_is_not_a_look(self):
        self.assertIsNone(VR.container_look(FRAME, "gameplay", None, None))
        self.assertIsNone(VR.container_look(FRAME, "runes", {"ok": True}, None))

    def test_the_newest_look_of_each_container_wins(self):
        a = VR.container_look(FRAME, "personal", _occ(10, 10, {(0, 0)}), "stash")
        b = dict(a, frame="f_1790000000900.jpg", capturedAt=1790000000900, occupied=[[1, 1]])
        c = dict(a, frame="f_x.jpg", capturedAt=None, occupied=[[2, 2]])
        inv = VR.container_look(FRAME, "personal", _occ(10, 4, {(5, 1)}), "inventory")
        out = VR.newest_container_looks([a, c, b, inv, None, {"no": "session"}])
        self.assertEqual(len(out), 2)
        st = [r for r in out if r["location"] == "stash"][0]
        self.assertEqual((st["frame"], st["occupied"]), ("f_1790000000900.jpg", [[1, 1]]))

    def test_the_payload_carries_them_and_the_sweep_publishes_them(self):
        look = VR.container_look(FRAME, "personal", _occ(10, 10, {(0, 0)}), "stash")
        shaped = VR.apply_payload({"ok": True, "owned": [], "containers": [look]})
        self.assertEqual(shaped.get("containers"), [look], "apply_payload dropped the containers")
        with open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            src = fh.read()
        code = re.sub(r"(?m)^\s*#.*$", "", src)
        own = "_oc2, _counted = _own_panel_cells(_vc2, p, surface) if _vc2 else (None, None)"
        call = "_cl = _vault_retro().container_look(p, surface, _oc2, _counted)"
        self.assertEqual((code.count(own), code.count(call)), (1, 1), "the sweep no longer keeps the counted panel's cells")
        self.assertLess(code.index(own), code.index(call))
        self.assertEqual(code.count('prop["containers"] = _vault_retro().newest_container_looks(_containers)'), 1,
                         "the sweep no longer publishes its container looks")


RED_PROOF = [
    {"why": "REG-3104 - a shared tab's look is filed as the personal stash (a page leak)",
     "file": "vault_retro.py",
     "find": '    tab = {"shared": "shared", "personal": "stash"}.get(s)          # a "stash" surface named no tab: UNKNOWN\n',
     "replace": '    tab = {"shared": "stash", "personal": "stash", "stash": "stash"}.get(s)\n',
     "matches": 1},
    {"why": "REG-3104 - an unread panel is reported empty",
     "file": "vault_retro.py",
     "find": '           "grid": list(_CONTAINER_GRIDS.get(loc or "stash")), "occupied": None, "why": None}\n',
     "replace": '           "grid": list(_CONTAINER_GRIDS.get(loc or "stash")), "occupied": [], "why": None}\n',
     "matches": 1},
    {"why": "REG-3104 - apply_payload drops the containers on the way to the board",
     "file": "vault_retro.py",
     "find": '        "containers": p.get("containers") or [],\n',
     "replace": "",
     "matches": 1},
    {"why": "REG-3104 - an older look of a container outranks a newer one",
     "file": "vault_retro.py",
     "find": '        if cur is None or at > (cur.get("capturedAt") if isinstance(cur.get("capturedAt"), int) else -1):\n',
     "replace": '        if cur is None:\n',
     "matches": 1},
    {"why": "REG-3104 - the sweep keeps no container look",
     "file": "control_app.py",
     "find": "                        _cl = _vault_retro().container_look(p, surface, _oc2, _counted)\n",
     "replace": "                        _cl = None\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
