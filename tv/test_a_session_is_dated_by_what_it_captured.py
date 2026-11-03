# -*- coding: utf-8 -*-
"""REG-2736 (#86) - A SESSION IS ORDERED AND DATED BY WHAT IT CAPTURED, NOT BY WHEN SOMETHING WAS LAST WRITTEN ABOUT IT.

MEASURED on his journal 2026-10-28: the Shelf's first eight rows were September and October reels, and its LAST SESSION
digest named an October 10 reel - the KAI closer had re-closed them all morning (the REG-2728 loop) and each re-close
wrote rows with ts = today: kai-funnel receipts (with the frame's captureTs), the KAI closer's "closed the session" note
(ts and captureTs both today, dated from the session's newest row - the previous note - so 59 re-closes walked one
September reel to today) and the watchdog's verdict. split_sessions ordered sessions by their newest ts, and the row
took t0/t1 from the first and last ts, so one reel read a 17-day span (readMs 1,490,631,272).

A row's moment is its frame's capture time when it carries one (replay.row_moment); the KAI ledger and the watchdog
annotate a session after it and are left out of its moments (POST_HOC_LANES), every row counting only when nothing else
is there - and a re-read row with no capture time is never one, even then (REG-2752: such a reel reads UNKNOWN).
Driven on replay.split_sessions and the real Handler._theatre_sessions over a fixture journal and reel tree.
RED_PROOF below.
"""
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
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
import replay as RP  # noqa: E402

OLD, NEW = "s_1790000000000_11", "s_1793000000000_22"
T_OLD = 1790000060000            # the old reel's reads, a minute of them
T_NEW = 1793000060000            # the new reel's reads, two minutes of them
T_LATE = T_NEW + 3600000         # an hour after the new reel ended, the old one is re-read


def _rows():
    rows = []
    for k in range(3):                                   # the old reel: three reads over 60 s
        t = T_OLD + k * 30000
        rows.append({"ts": t, "captureTs": t, "frameId": "%d_%d" % (k + 1, t), "n": k + 1, "names": [],
                     "sessionId": OLD, "scene": "gameplay"})
    for k in range(3):                                   # the new reel: three reads over 120 s
        t = T_NEW + k * 60000
        rows.append({"ts": t, "captureTs": t, "frameId": "%d_%d" % (k + 1, t), "n": k + 1, "names": [],
                     "sessionId": NEW, "scene": "gameplay"})
    # the re-read of the OLD reel, written after the new one ended
    rows.append({"ts": T_LATE, "captureTs": T_OLD + 30000, "completedTs": T_LATE, "lane": "intake", "sessionId": OLD,
                 "intake": {"kind": "kai-funnel", "ok": False, "total": 0, "errors": 1}, "frameId": "2_%d" % (T_OLD + 30000)})
    rows.append({"ts": T_LATE + 1, "captureTs": T_LATE + 1, "lane": "kai", "mode": "kai", "scene": "kai", "sessionId": OLD,
                 "note": "KAI closed the session"})
    rows.append({"ts": T_LATE + 2, "captureTs": T_LATE + 2, "lane": "watchdog", "sessionId": OLD})
    rows.sort(key=lambda r: r["ts"])
    return rows


def _ids(groups):
    return [next((r.get("sessionId") for r in g if r.get("sessionId")), None) for g in groups]


class ASessionIsOrderedByWhatItCaptured(unittest.TestCase):

    def test_a_reel_re_read_later_keeps_its_place(self):
        rows = _rows()
        self.assertGreater(max(r["ts"] for r in rows if r["sessionId"] == OLD),
                           max(r["ts"] for r in rows if r["sessionId"] == NEW),
                           "PREMISE: the old reel was not written to after the new one ended")
        self.assertEqual(_ids(RP.split_sessions(rows)), [NEW, OLD],
                         "a re-read of an old reel moved it above the newer session")

    def test_a_row_moment_is_its_capture_time(self):
        self.assertEqual(RP.row_moment({"ts": 9, "captureTs": 3}), 3)
        self.assertEqual(RP.row_moment({"ts": 9}), 9)
        self.assertEqual(RP.row_moment({"ts": 9, "captureTs": True}), 9, "a boolean is not a time")

    def test_post_hoc_notes_are_left_out_unless_nothing_else_is_there(self):
        g = [{"ts": 5, "captureTs": 5}, {"lane": "kai", "ts": 99, "captureTs": 99}, {"lane": "watchdog", "ts": 98}]
        self.assertEqual(RP.session_moments(g), [5])
        self.assertEqual(RP.session_moments([{"lane": "kai", "ts": 7, "captureTs": 7}]), [7],
                         "a session holding only a KAI note lost its only moment")

    def test_a_re_read_counts_only_through_its_capture_time(self):
        """REG-2744 (the v3821 second eye) - a verify or intake row with no capture time is when the re-read WROTE."""
        live = {"ts": 5, "captureTs": 5}
        self.assertEqual(RP.session_moments([live, {"lane": "verify", "ts": 999}]), [5],
                         "a verify row with no capture time dated the session by when it was written")
        self.assertEqual(RP.session_moments([live, {"lane": "intake", "ts": 999}]), [5])
        self.assertEqual(sorted(RP.session_moments([live, {"lane": "intake", "ts": 999, "captureTs": 7}])), [5, 7],
                         "an intake row's own capture time stopped counting")

    def test_the_fallback_never_lets_a_capture_less_re_read_back_in(self):
        """REG-2752 (the v3823 second eye) - when nothing but notes and re-reads is there, the fallback still counts a
        re-read only through its capture time: a session of capture-less re-reads has no moment, not today's."""
        self.assertEqual(RP.session_moments([{"lane": "intake", "ts": 999}, {"lane": "verify", "ts": 998}]), [],
                         "a session of capture-less re-reads was dated by when they wrote")
        self.assertEqual(RP.session_moments([{"lane": "kai", "ts": 7}, {"lane": "verify", "ts": 999}]), [7],
                         "the fallback dropped the note or kept the re-read's write time")


class TheShelfRowCarriesTheCapturedSpan(unittest.TestCase):

    def test_t0_t1_and_the_read_span_come_from_what_was_captured(self):
        d = tempfile.mkdtemp(prefix="session-dated-")
        self.addCleanup(shutil.rmtree, d, True)
        hist = os.path.join(d, "hist")
        for sid in (OLD, NEW):
            os.makedirs(os.path.join(hist, "reel_" + sid))
        journal = os.path.join(d, "sessions.jsonl")
        with open(journal, "w", encoding="utf-8") as fh:
            for r in _rows():
                fh.write(json.dumps(r) + "\n")
        import control_app as ca
        keep = (ca.HIST_DIR, RP.JOURNAL)
        ca.HIST_DIR, RP.JOURNAL = hist, journal
        cached = ca.__dict__.pop("_JRNL_CACHE", None)
        try:
            h = ca.Handler.__new__(ca.Handler)
            out = ca.Handler._theatre_sessions(h)
        finally:
            ca.HIST_DIR, RP.JOURNAL = keep
            ca.__dict__.pop("_JRNL_CACHE", None)
            if cached is not None:
                ca._JRNL_CACHE = cached
        self.assertIsInstance(out, list, "the shelf answered an error: %r" % (out,))
        by = dict((r.get("sessionId"), r) for r in out)
        self.assertEqual([r.get("sessionId") for r in out][:2], [NEW, OLD], "the Shelf put the re-read reel first")
        old = by[OLD]
        self.assertEqual((old.get("t0"), old.get("t1")), (T_OLD, T_OLD + 60000),
                         "the old reel is dated by when it was last written about: %r" % ({k: old.get(k) for k in ("t0", "t1")},))
        self.assertEqual(old.get("readMs"), 60000, "the read span stretched to the re-read: %r" % old.get("readMs"))
        self.assertEqual(old.get("reads"), 3, "REG-2744 - the watchdog's verdict was counted as a read: %r" % old.get("reads"))
        self.assertEqual((by[NEW].get("t0"), by[NEW].get("t1")), (T_NEW, T_NEW + 120000))

    def test_two_shelves_never_share_a_memo_row(self):
        """v3856 gate - the row memo was keyed by the reel folder's mtime but not the folder itself. Two shelves made in
        one clock tick carried the same mtime_ns, so one shelf's span was served for the other (flaky, both orders)."""
        import control_app as ca
        sess = [{"sessionId": NEW, "ts": T_NEW}]
        a, b = tempfile.mkdtemp(prefix="memo-a-"), tempfile.mkdtemp(prefix="memo-b-")
        self.addCleanup(shutil.rmtree, a, True)
        self.addCleanup(shutil.rmtree, b, True)
        for h in (a, b):
            os.makedirs(os.path.join(h, "reel_" + NEW))
            os.utime(os.path.join(h, "reel_" + NEW), ns=(1, 1))   # the same tick, forced
        self.assertNotEqual(ca._theatre_row_fingerprint(sess, a), ca._theatre_row_fingerprint(sess, b),
                            "two shelves with the same session and mtime share one memo row")

    def test_a_run_with_film_spans_its_film(self):
        """REG-2748 (GrokBot's v3821 pass) - a card read "0m00s" beside "3127 frames · full video": one read, an hour of
        film. The footage stills are captures of the session (f_<capture ms>.jpg), so the span covers them."""
        d = tempfile.mkdtemp(prefix="session-film-")
        self.addCleanup(shutil.rmtree, d, True)
        hist = os.path.join(d, "hist")
        for sid in (OLD, NEW):
            os.makedirs(os.path.join(hist, "reel_" + sid))
        for ts in (T_NEW - 30000, T_NEW + 60000, T_NEW + 600000):
            open(os.path.join(hist, "reel_" + NEW, "f_%d.jpg" % ts), "wb").close()
        journal = os.path.join(d, "sessions.jsonl")
        with open(journal, "w", encoding="utf-8") as fh:
            for r in _rows():
                fh.write(json.dumps(r) + "\n")
        import control_app as ca
        keep = (ca.HIST_DIR, RP.JOURNAL)
        ca.HIST_DIR, RP.JOURNAL = hist, journal
        cached = ca.__dict__.pop("_JRNL_CACHE", None)
        try:
            out = ca.Handler._theatre_sessions(ca.Handler.__new__(ca.Handler))
        finally:
            ca.HIST_DIR, RP.JOURNAL = keep
            ca.__dict__.pop("_JRNL_CACHE", None)
            if cached is not None:
                ca._JRNL_CACHE = cached
        by = dict((r.get("sessionId"), r) for r in out)
        self.assertEqual(by[NEW].get("footageN"), 3, "PREMISE: the film stills were not counted: %r" % by[NEW].get("footageN"))
        self.assertEqual((by[NEW].get("t0"), by[NEW].get("t1")), (T_NEW - 30000, T_NEW + 600000),
                         "the run is dated by its reads alone, not its film: %r" % ({k: by[NEW].get(k) for k in ("t0", "t1")},))
        self.assertEqual((by[OLD].get("t0"), by[OLD].get("t1")), (T_OLD, T_OLD + 60000), "a reel with no film moved")

    def test_the_live_card_spans_its_loose_film_too(self):
        """REG-2766 (the v3824 second eye) - before the reel seals there is no reel_<sid> folder: the LIVE card counts the
        loose f_<ms>.jpg stills at the reel root, and its span must cover them as the sealed path does (REG-2748)."""
        d = tempfile.mkdtemp(prefix="session-live-film-")
        self.addCleanup(shutil.rmtree, d, True)
        hist = os.path.join(d, "hist")
        os.makedirs(os.path.join(hist, "reel_" + OLD))          # the OLD reel sealed; NEW is still recording
        for ts in (T_NEW - 30000, T_NEW + 900000):
            open(os.path.join(hist, "f_%d.jpg" % ts), "wb").close()
        # REG-2774 (GrokBot's v3826 pass) - an ORPHAN still at the root, days before this session began: not its film
        open(os.path.join(hist, "f_%d.jpg" % (T_OLD - 10 * 86400000)), "wb").close()
        journal = os.path.join(d, "sessions.jsonl")
        with open(journal, "w", encoding="utf-8") as fh:
            for r in _rows():
                fh.write(json.dumps(r) + "\n")
        import control_app as ca
        keep = (ca.HIST_DIR, RP.JOURNAL)
        ca.HIST_DIR, RP.JOURNAL = hist, journal
        cached = ca.__dict__.pop("_JRNL_CACHE", None)
        try:
            out = ca.Handler._theatre_sessions(ca.Handler.__new__(ca.Handler))
        finally:
            ca.HIST_DIR, RP.JOURNAL = keep
            ca.__dict__.pop("_JRNL_CACHE", None)
            if cached is not None:
                ca._JRNL_CACHE = cached
        new = next(r for r in out if r.get("sessionId") == NEW)
        self.assertEqual(new.get("footageN"), 2, "the live card counted an orphan still as its film, or missed its own: %r"
                         % new.get("footageN"))
        self.assertEqual((new.get("t0"), new.get("t1")), (T_NEW - 30000, T_NEW + 900000),
                         "the live card counts loose film it does not span: %r" % ({k: new.get(k) for k in ("t0", "t1")},))

    def test_a_reel_of_capture_less_re_reads_is_UNKNOWN_not_today(self):
        """REG-2752 (the v3823 second eye) - the Shelf row's own fallback (the first and last row's ts) let the write time
        back in after the moments had kept it out."""
        RR = "s_1791000000000_33"
        d = tempfile.mkdtemp(prefix="session-reread-")
        self.addCleanup(shutil.rmtree, d, True)
        hist = os.path.join(d, "hist")
        for sid in (OLD, NEW, RR):
            os.makedirs(os.path.join(hist, "reel_" + sid))
        journal = os.path.join(d, "sessions.jsonl")
        rows = _rows() + [{"ts": T_LATE + 10 + k, "lane": "intake", "sessionId": RR, "frameId": "%d_x" % k,
                           "intake": {"kind": "kai-funnel", "ok": True, "total": 0}} for k in range(4)]
        with open(journal, "w", encoding="utf-8") as fh:
            for r in sorted(rows, key=lambda r: r["ts"]):
                fh.write(json.dumps(r) + "\n")
        import control_app as ca
        keep = (ca.HIST_DIR, RP.JOURNAL)
        ca.HIST_DIR, RP.JOURNAL = hist, journal
        cached = ca.__dict__.pop("_JRNL_CACHE", None)
        try:
            out = ca.Handler._theatre_sessions(ca.Handler.__new__(ca.Handler))
        finally:
            ca.HIST_DIR, RP.JOURNAL = keep
            ca.__dict__.pop("_JRNL_CACHE", None)
            if cached is not None:
                ca._JRNL_CACHE = cached
        by = dict((r.get("sessionId"), r) for r in out)
        self.assertIn(RR, by, "PREMISE: the Shelf dropped the re-read reel, so this case measures nothing: %r" % sorted(by))
        self.assertEqual((by[RR].get("t0"), by[RR].get("t1")), (None, None),
                         "a reel of capture-less re-reads was dated by when they wrote: %r"
                         % ({k: by[RR].get(k) for k in ("t0", "t1")},))
        self.assertEqual((by[OLD].get("t0"), by[NEW].get("t0")), (T_OLD, T_NEW), "a dated reel moved")


class ACommitmentIsNotARead(unittest.TestCase):
    """REG-2759 (GrokBot's v3823 question) - his session 71 (s_1792317613152_58017) read "3 reads in 310 ms" beside 2
    frames: an ocr row and a deep row on frame 1, and a deep-owed row - the console's note that the frame was committed to
    the deep reader - written 310 ms later. The note was counted as a read and stretched the span to its write time."""

    def test_the_deep_owed_and_chronicle_notes_are_not_reads(self):
        import control_app as ca
        t = 1792317655895
        rows = [{"ts": t, "frameId": "1_%d" % t, "lane": "ocr", "scene": "loot", "mode": "ocr"},
                {"ts": t + 310, "frameId": "snap_0_1.jpg", "lane": "deep-owed"},
                {"ts": t, "captureTs": t, "frameId": "1_%d" % t, "lane": "deep", "scene": "gameplay"},
                {"ts": t + 9000, "lane": "chronicle", "kind": "visit"},
                {"ts": t + 20, "frameId": "1_x", "lane": "known", "mode": "known", "scene": "transition"}]
        got = [r["lane"] for r in rows if ca._is_a_live_read(r)]
        self.assertEqual(got, ["ocr", "deep", "known"], "a note about a frame was counted as a read: %r" % got)


RED_PROOF = [
    {"why": "REG-2774 - the live card counts and spans every loose still at the root, orphans included",
     "file": "control_app.py",
     "find": "                            if _ls0 is not None:\n",
     "replace": "                            if False:\n",
     "matches": 1},
    {"why": "REG-2766 - the live card counts its loose film and never dates it",
     "file": "control_app.py",
     "find": "                                for _lx in (_lf[0], _lf[-1]):\n",
     "replace": "                                for _lx in ():\n",
     "matches": 1},
    {"why": "REG-2759 - the deep reader's commitment note counts as a read again",
     "file": "control_app.py",
     "find": "            and r2.get(\"lane\") not in (\"kai\", \"verify\", \"intake\", \"watchdog\", \"deep-owed\", \"chronicle\"))\n",
     "replace": "            and r2.get(\"lane\") not in (\"kai\", \"verify\", \"intake\", \"watchdog\", \"chronicle\"))\n",
     "matches": 1},
    {"why": "REG-2752 - the moments' fallback counts a capture-less re-read by when it wrote",
     "file": "replay.py",
     "find": "    return m or [x for x in (_session_moment(r) for r in (g or [])) if x > 0]\n",
     "replace": "    return m or [x for x in (row_moment(r) for r in (g or [])) if x > 0]\n",
     "matches": 1},
    {"why": "REG-2752 - the Shelf row's t0 falls back to its first written row",
     "file": "control_app.py",
     "find": "                            \"n\": i, \"t0\": min((_rp.session_moments(sess) or []) + _foot_span or [0]) or None,\n",
     "replace": "                            \"n\": i, \"t0\": min((_rp.session_moments(sess) or []) + _foot_span or [0]) or sess[0].get(\"ts\"),\n",
     "matches": 1},
    {"why": "REG-2748 - a run with film is dated by its reads alone again (0m00s beside an hour of footage)",
     "file": "control_app.py",
     "find": "                                    _foot_span.append(_fts)\n",
     "replace": "                                    pass\n",
     "matches": 1},
    {"why": "REG-2744 - a re-read row with no capture time dates the session by when it wrote",
     "file": "replay.py",
     "find": "        return int(cap) if isinstance(cap, (int, float)) and not isinstance(cap, bool) and cap > 0 else 0\n",
     "replace": "        return row_moment(r)\n",
     "matches": 1},
    {"why": "REG-2744 - the read count keeps its own lane list and counts the watchdog's verdict",
     "file": "control_app.py",
     "find": "                            \"reads\": len([r2 for r2 in sess if _is_a_live_read(r2)]),",
     "replace": "                            \"reads\": len([r2 for r2 in sess if _is_a_live_read(r2) or r2.get(\"lane\") == \"watchdog\"]),",
     "matches": 1},
    {"why": "REG-2736 - sessions are ordered by their newest WRITTEN row again (a re-read reel jumps to the top)",
     "file": "tv/replay.py",
     "find": "    sessions.sort(key=lambda g: min(session_moments(g) or [0]))\n",
     "replace": "    sessions.sort(key=lambda g: max((r.get(\"ts\") or 0) for r in g))\n",
     "matches": 1},
    {"why": "REG-2736 - a row's moment ignores its capture time",
     "file": "tv/replay.py",
     "find": "    c = (r or {}).get(\"captureTs\")\n    if isinstance(c, (int, float)) and not isinstance(c, bool) and c > 0:\n",
     "replace": "    c = None\n    if isinstance(c, (int, float)) and not isinstance(c, bool) and c > 0:\n",
     "matches": 1},
    {"why": "REG-2736 - the KAI ledger and the watchdog date the session again",
     "file": "tv/replay.py",
     "find": "POST_HOC_LANES = (\"kai\", \"watchdog\")\n",
     "replace": "POST_HOC_LANES = ()\n",
     "matches": 1},
    {"why": "REG-2736 - the Shelf row's t1 is its last written row again",
     "file": "tv/control_app.py",
     "find": "                            \"t1\": max((_rp.session_moments(sess) or []) + _foot_span or [0]) or None,\n",
     "replace": "                            \"t1\": sess[-1].get(\"ts\"),\n",
     "matches": 1},
    {"why": "REG-2736 - the watchdog's verdict counts as a read and stretches the read span",
     "file": "tv/control_app.py",
     "find": "            and r2.get(\"lane\") not in (\"kai\", \"verify\", \"intake\", \"watchdog\", \"deep-owed\", \"chronicle\"))\n",
     "replace": "            and r2.get(\"lane\") not in (\"kai\", \"verify\", \"intake\", \"deep-owed\", \"chronicle\"))\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
