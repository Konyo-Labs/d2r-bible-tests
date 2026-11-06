#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REG-3275 (#44) - A HELD REEL THE TAB-AWARE VAULT READER RE-READ, THAT STILL BANKS NOTHING, IS RELEASED - ITS PANEL
FRAMES KEPT.

His ruling, 2026-11-06 (the 10-29 question "12 held reels - keep, release as evidence remnants, or a time limit?",
answered "Re-read once, then release"). Measured that morning on his Mac's /api/river: 13 reels older than his newest 16
held by the drain - 8 `panels-never-banked` (the vault reader saw stash panels, the ledger holds no row from the reel)
and 5 `zero-pages` (sealed by a reader that found nothing). v3871's vault reader asks the stash TAB
(tv_diablo.VAULT_TAB_ASKED_BY, REG-3248) and re-reads every barren reel once. Held here, driven through the real plan():
  * a reel whose vault seal was made by a reader in VAULT_TAB_ASKED_BY with rows 0, and whose FULL survey names its
    panel frames, is a candidate, carrying `keepPanels` (exactly those frames) and the ruling - from either hold;
  * it is NEVER released when the seal is an older reader's, has no whole-number rows, banked rows, or the survey
    predates panelFrames (its panel frames cannot be named, so the remnant cannot be kept);
  * apply_plan keeps the panel frames on disk (and the evidence pictures, as before), and the tombstone names the ruling;
  * end_routes' unextracted door asks the same predicate with ITS world's survey row, so the deleter and the doors agree
    (the doctor's end-routes row goes red on a reel the deleter offers while every door refused it).
Fixtures only: a shelf of our own under TV_HIST; frame.release is stubbed only for the selection, as test_reel_retention
does. RED_PROOF below.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import console_safe  # noqa: E402
console_safe.enable()

import reel_retention as RR  # noqa: E402
import end_routes as ER      # noqa: E402
import tv_diablo as TVD      # noqa: E402

TAB = TVD.VAULT_TAB_ASKED_BY[0]
FRAMES = ["f_1700000000.jpg", "f_1700000001.jpg", "f_1700000002.jpg"]
PANELS = {FRAMES[0]: "shared", FRAMES[2]: "personal"}


def _seal(rows=0, pv=TAB):
    return {"rows": rows, "extracted": [], "extractedWhy": "nothing was taken", "agentVer": "fixture", "promptVer": pv}


class _Shelf(object):
    """One old subject reel + KEEP_RECENT newer fillers, on a shelf of our own."""

    def __init__(self, seal, panels=2, panel_frames=PANELS, pages=0, kind="stash"):
        self.tmp = tempfile.mkdtemp(prefix="heldreread_")
        self.hist = os.path.join(self.tmp, "hist")
        os.makedirs(self.hist)
        now = int(time.time() * 1000)
        rows = [(90, panels)] + [(d, 0) for d in range(30, 30 - RR.KEEP_RECENT, -1)]
        survey, chron, vault, self.names = {}, {}, {}, []
        for i, (age, p) in enumerate(rows):
            nm = "reel_s_%d_%03d" % (now - int(age * 86400000), i)
            self.names.append(nm)
            d = os.path.join(self.hist, nm)
            os.makedirs(d)
            for f in FRAMES:
                with io.open(os.path.join(d, f), "w") as fh:
                    fh.write("x")
            survey[nm] = {"full": True, "panels": p, "frames": 3, "kinds": ({(kind if i == 0 else "stash"): p} if p else {})}
            chron[nm] = {"ts": now, "classified": 1, "pages": pages, "looked": True, "framesAtLook": 3, "why": "fixture"}
        self.subject = self.names[0]
        if panel_frames is not None:
            survey[self.subject]["panelFrames"] = dict(panel_frames)
        if seal is not None:
            vault[self.subject] = dict(seal, ts=now)
        for name, body in (("chronicle_swept.json", chron), ("vault_swept.json", vault)):
            with io.open(os.path.join(self.hist, name), "w", encoding="utf-8") as fh:
                fh.write(json.dumps(body))
        self.survey = survey

    def __enter__(self):
        self._old = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = self.hist
        import frame_authority as _fa
        self._fa, self._wi = _fa, _fa.witness_index
        _fa.witness_index = lambda *a, **k: {"haveIndex": True, "ok": True, "frames": set(), "sessions": set(),
                                             "perStore": {}}
        import retro_triage as rt
        with io.open(rt._store_path(), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(self.survey))
        RR._TRIAGE_CACHE["at"] = None
        return self

    def __exit__(self, *a):
        self._fa.witness_index = self._wi
        if self._old is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._old
        RR._TRIAGE_CACHE["at"] = None
        shutil.rmtree(self.tmp, ignore_errors=True)

    def plan(self):
        p = RR.plan(self.hist)
        row = None
        for k in (p.get("kept") or []) + list(p.get("candidates") or []):
            if isinstance(k, dict) and str(k.get("reel", "")).endswith(self.subject):
                row = k
        return p, row


class TheRulingReleases(unittest.TestCase):
    def test_a_barren_reel_the_tab_reader_read_is_released_keeping_its_panels(self):
        with _Shelf(_seal()) as sh:
            p, row = sh.plan()
            self.assertTrue(p.get("ok"), p.get("why"))
            self.assertIsNotNone(row, "premise: the subject reel is on the plan")
            self.assertEqual(row.get("tag"), "eligible", "his ruling did not release it (tag %r)" % row.get("tag"))
            self.assertEqual(row.get("keepPanels"), sorted(PANELS), "the remnant is not exactly its panel frames")
            self.assertEqual(row.get("ruling"), RR.HELD_REREAD_RULING)
            self.assertIn(sh.subject, p.get("releasedAfterReread") or [])
            # REG-3293 - its tombstone sentence names the seals it really held (chronicle and vault here)
            self.assertIn(RR.SEALS_BOTH, row.get("why") or "")
            self.assertNotIn("sealed by BOTH lanes", row.get("why") or "")

    def test_a_reel_with_only_a_chronicle_seal_says_so_on_its_way_out(self):
        """REG-3293 - 529 of his 1,832 tombstones say 'sealed by BOTH lanes' over a reel the vault never sealed."""
        with _Shelf(None, panels=0, panel_frames={}) as sh:
            _p, row = sh.plan()
            self.assertEqual(row.get("tag"), "eligible", "premise: a panel-free, chronicle-sealed reel is eligible: %r"
                             % row.get("tag"))
            self.assertIn("seals held: chronicle only", row.get("why") or "")
            self.assertNotIn(RR.SEALS_BOTH, row.get("why") or "")

    def test_a_zero_pages_hold_yields_to_the_ruling_too(self):
        with _Shelf(_seal(), panels=1, panel_frames={FRAMES[1]: "chronicle"}, kind="chronicle") as sh:
            _p, row = sh.plan()
            self.assertIsNotNone(row)
            self.assertEqual(row.get("tag"), "eligible", "a barren zero-pages reel stayed held: %r" % row.get("tag"))
            self.assertEqual(row.get("keepPanels"), [FRAMES[1]])

    def test_baseline_an_older_readers_seal_still_holds(self):
        with _Shelf(_seal(pv="vp-before-the-tab")) as sh:
            _p, row = sh.plan()
            self.assertEqual(row.get("tag"), "panels-never-banked", "a reel the new reader never read was released")
            self.assertNotIn("keepPanels", row)
        with _Shelf(_seal(pv="vp-before-the-tab"), panels=1, panel_frames={FRAMES[1]: "chronicle"},
                    kind="chronicle") as sh:
            self.assertEqual(sh.plan()[1].get("tag"), "zero-pages", "premise: a Chronicle reel read 0 pages is held")

    def test_a_survey_that_cannot_name_its_panel_frames_holds(self):
        with _Shelf(_seal(), panel_frames=None) as sh:
            self.assertEqual(sh.plan()[1].get("tag"), "panels-never-banked")

    def test_the_predicate_refuses_every_doubt(self):
        row = {"full": True, "panels": 2, "panelFrames": PANELS}
        self.assertTrue(RR.held_reel_released("r", _seal(), row)[0])
        for bad in (None, {"promptVer": TAB}, _seal(rows=True), _seal(rows="0"), _seal(rows=3), _seal(pv="")):
            self.assertFalse(RR.held_reel_released("r", bad, row)[0], bad)
        for bad_row in (None, {"full": False, "panelFrames": PANELS}, {"full": True, "panels": 2}):
            self.assertFalse(RR.held_reel_released("r", _seal(), bad_row)[0], bad_row)


class TheRemnantStays(unittest.TestCase):
    def _allow_release(self):
        import self_arming as _sa
        _real = _sa.may
        _sa.may = lambda name, *a, **k: ((True, "stubbed for this selection law") if name == "frame.release"
                                         else _real(name, *a, **k))
        self.addCleanup(setattr, _sa, "may", _real)

    def test_apply_keeps_the_panel_frames_and_records_the_ruling(self):
        self._allow_release()
        with _Shelf(_seal()) as sh:
            p, row = sh.plan()
            self.assertEqual(row.get("tag"), "eligible")
            p = dict(p, candidates=[row])
            out = RR.apply_plan(p, yes=True)
            d = os.path.join(sh.hist, sh.subject)
            left = sorted(_fx_tmp.list_own(d)) if os.path.isdir(d) else []   # this run's own scratch
            self.assertEqual(left, sorted(PANELS), "the released reel did not keep exactly its panel frames: %r (%r)"
                             % (left, out.get("why")))
            with io.open(RR._tombstone_path(sh.hist), encoding="utf-8") as fh:
                tomb = [t for t in (json.load(fh).get("reels") or []) if t.get("reel") == sh.subject]
            self.assertTrue(tomb, "no tombstone row for the released reel")
            self.assertEqual(tomb[-1].get("ruling"), RR.HELD_REREAD_RULING)
            self.assertEqual(sorted(tomb[-1].get("kept") or []), sorted(PANELS))


class TheDoorsAgree(unittest.TestCase):
    def test_the_unextracted_door_opens_for_a_released_reel(self):
        src = {"structural": {"reel_x": {"full": True, "panels": 2, "panelFrames": PANELS}},
               "vault": {"reel_x": _seal()}}
        opened, gaps, ev = ER.unextracted_door("reel_x", src)
        self.assertIs(opened, True, gaps)
        self.assertEqual(ev.get("ruling"), RR.HELD_REREAD_RULING)

    def test_the_door_still_refuses_an_older_readers_barren_seal(self):
        src = {"structural": {"reel_x": {"full": True, "panels": 2, "panelFrames": PANELS}},
               "vault": {"reel_x": _seal(pv="vp-before-the-tab")}}
        opened, gaps, _ev = ER.unextracted_door("reel_x", src)
        self.assertIs(opened, False)
        self.assertIn("extracted rows before the tombstone", json.dumps(gaps))


RED_PROOF = [
    {"why": "REG-3293 - the eligible sentence claims both seals whatever the reel held again",
     "file": "tv/reel_retention.py",
     "find": "                _seals = (SEALS_BOTH if len(_held) == 2 else\n",
     "replace": "                _seals = (SEALS_BOTH if True else\n",
     "matches": 1},
    {"why": "REG-3275 - the ruling never releases a panels-never-banked reel",
     "file": "tv/reel_retention.py",
     "find": "            elif _panels_never_banked(reel, ve) and not _rel(reel, ve):   # REG-3275 (#44) - his 11-06 ruling\n",
     "replace": "            elif _panels_never_banked(reel, ve):\n",
     "matches": 1},
    {"why": "REG-3275 - a zero-pages reel stays held whatever the re-read found",
     "file": "tv/reel_retention.py",
     "find": "                  and not _rel(reel, ve)):        # REG-3275 (#44) - re-read by the tab reader, still barren: released\n",
     "replace": "                  ):\n",
     "matches": 1},
    {"why": "REG-3275 - a seal by an older reader is released before its re-read",
     "file": "tv/reel_retention.py",
     "find": "        if not asked or pv not in asked:\n",
     "replace": "        if not asked:\n",
     "matches": 1},
    {"why": "REG-3275 - a reel whose survey cannot name its panel frames is released",
     "file": "tv/reel_retention.py",
     "find": "        if not isinstance(pf, dict):\n            return False, None, \"its survey predates panelFrames",
     "replace": "        if not isinstance(pf, dict):\n            pf = {}\n        if False:\n            return False, None, \"its survey predates panelFrames",
     "matches": 1},
    {"why": "REG-3275 - the released reel's panel frames are deleted with it",
     "file": "tv/reel_retention.py",
     "find": "            kept = sorted(f for f in os.listdir(path) if f in _evid or f in _pan)\n",
     "replace": "            kept = sorted(f for f in os.listdir(path) if f in _evid)\n",
     "matches": 1},
    {"why": "REG-3275 - the plan never says which frames the remnant keeps",
     "file": "tv/reel_retention.py",
     "find": "                    _c[\"keepPanels\"] = list(_r[1] or [])\n",
     "replace": "                    pass\n",
     "matches": 1},
    {"why": "REG-3275 - the doors still refuse what the deleter releases",
     "file": "tv/end_routes.py",
     "find": "    if _hrel:\n        ev[\"ruling\"] = _hwhy\n        return True, [], ev\n",
     "replace": "    if False:\n        return True, [], ev\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
