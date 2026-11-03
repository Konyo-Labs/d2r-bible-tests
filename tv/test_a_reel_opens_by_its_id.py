# -*- coding: utf-8 -*-
"""REG-1933 - THE THEATRE OPENS THE REEL HE CLICKED, BY ITS ID, NOT BY WHERE IT SAT.

GrokBot (#230, tick 371/372) read three counts of "one" session that disagreed: Session 46's dossier said
FILM FRAMES 49 while the theatre opened from it said "film 64"; S74's card said FILM FRAMES 0 beside a
theatre with "film 11 . 3 AI reads"; the same on S30 and S48. Measured on the Mac's console the same
afternoon (GET only): when the card and the theatre load the SAME reel they agree - 102 = 102, 194 = 194,
594 = 594, 3494 = 3494. What differs is WHICH reel: `/api/session?n=` is a position in a newest-first
list, re-split from the journal on every request, so one session started between the shelf's fetch and
the click moves every reel down a place and `?n=46` answers with the reel that was 45. Nothing checked
the sessionId that came back.

The law: given a sid the server finds the reel by its id in the journal as it is now, whatever n says; a
sid the journal no longer holds is refused, never answered with whatever sits at n; with no sid the old
positional answer is unchanged. The page sends the id it was shown, refuses a reel that comes back under
another id, and the dossier hands in its own reel's id.
Fixtures only: the journal is a list in memory and HIST_DIR is an empty temp dir.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock as mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import control_app as CA  # noqa: E402


def _rows(sid, t0, k=3):
    return [{"ts": t0 + i * 1000, "sessionId": sid, "lane": "deep", "scene": "town", "names": []}
            for i in range(k)]


OLD = _rows("s_1000_1", 1000000) + _rows("s_2000_2", 2000000) + _rows("s_3000_3", 3000000)
NEW = OLD + _rows("s_4000_4", 4000000)      # one more session started after the shelf was drawn
# split_sessions orders reels by their NEWEST row, so a retro lane (kai, intake) writing a row onto an OLD reel
# moves it to the top with no new session at all - the Mac's own list has a Sep-8 reel at n=2 for 850 kai rows.
# REG-2736 - a post-hoc KAI note no longer moves a reel (a session is dated by what it CAPTURED), so the reorder this
# case needs is a reel that genuinely resumed: a read captured later on the old reel.
RETRO = OLD + [{"ts": 5000000, "captureTs": 500000, "sessionId": "s_3000_3", "names": []}]
# v3857 item 20 - the list now sorts by START, so the reorder a late row can cause is an EARLIER capture on the newest reel


class _Fake(object):
    def __init__(self, journal):
        self.journal = journal

    def _load_journal_cached(self):
        return list(self.journal)

    def _prewarm_session_frames(self, *a, **k):
        return None

    def _thin_footage_beats(self, beats, *a, **k):
        return beats


class AReelOpensByItsId(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="reel_by_id_")
        self.p = mock.patch.object(CA, "HIST_DIR", self.d)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        shutil.rmtree(self.d, ignore_errors=True)

    def open(self, journal, n, sid=None):
        return CA.Handler._theatre_session(_Fake(journal), n, pack="debug", sid=sid)

    def test_the_fixture_reproduces_the_shift(self):
        """Baseline: the case can tell the two answers apart - by place, n=2 is a different reel once a
        new session has started."""
        self.assertEqual(self.open(OLD, 2).get("sessionId"), "s_2000_2")
        self.assertEqual(self.open(NEW, 2).get("sessionId"), "s_3000_3",
                         "the fixture no longer shifts, so the law below would pass over nothing")

    def test_the_id_wins_over_a_stale_place(self):
        j = self.open(NEW, 2, sid="s_2000_2")
        self.assertEqual(j.get("sessionId"), "s_2000_2",
                         "the theatre answered ?n=2&sid=s_2000_2 with another reel (REG-1933): %s"
                         % j.get("sessionId"))
        self.assertEqual(j.get("n"), 3, "the reel's place NOW is not reported back")
        self.assertTrue(j.get("beats"), "the reel was found and carried no beats")

    def test_a_retro_row_on_an_old_reel_reorders_the_list_and_the_id_still_wins(self):
        self.assertEqual(self.open(RETRO, 1).get("sessionId"), "s_2000_2",
                         "the fixture no longer reorders on a retro row, so this case measures nothing")
        j = self.open(RETRO, 1, sid="s_3000_3")
        self.assertEqual(j.get("sessionId"), "s_3000_3",
                         "a kai row on an old reel moved the list and ?n=1 opened that reel instead")
        self.assertEqual(j.get("n"), 3)

    def test_a_reel_no_longer_in_the_journal_is_refused(self):
        j = self.open(NEW, 2, sid="s_9999_9")
        self.assertIn("error", j, "a vanished reel was answered with whatever sat at n=2: %s" % j.get("sessionId"))
        self.assertNotIn("beats", j)
        self.assertEqual(j.get("sessionId"), "s_9999_9", "the refusal does not say which reel it could not find")

    def test_film_is_what_is_on_disk_and_the_gone_are_counted(self):
        """The other way two counts of one reel part: the dossier counts the reel directory, the theatre counted
        its index. A frame the index lists and the disk no longer holds is not film."""
        rd = os.path.join(self.d, "reel_s_2000_2")
        os.makedirs(rd)
        names = ["f_2000100.jpg", "f_2000200.jpg", "f_2000300.jpg"]
        with io.open(os.path.join(rd, "index.json"), "w", encoding="utf-8") as fh:
            json.dump({"frames": [{"f": n, "ts": int(n[2:-4])} for n in names]}, fh)
        for n in names[:2]:
            with open(os.path.join(rd, n), "wb") as fh:
                fh.write(b"\xff\xd8\xff\xd9")
        j = self.open(OLD, 2, sid="s_2000_2")
        foot = [b for b in j.get("beats") or [] if b.get("footage")]
        self.assertEqual(sorted(b["frame"].split("/")[-1] for b in foot), names[:2],
                         "the theatre played a frame the disk no longer holds (REG-1933)")
        self.assertEqual(j["stats"]["footage"], 2)
        self.assertEqual(j["stats"].get("indexMissing"), 1, "the frame that fell out was not counted")

    def test_no_sid_keeps_the_old_answer(self):
        self.assertEqual(self.open(NEW, 1).get("sessionId"), "s_4000_4")
        self.assertIn("error", self.open(NEW, 99))


def _code(path):
    with io.open(path, encoding="utf-8") as fh:
        src = fh.read()
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


class ThePageAsksForTheReelItShowed(unittest.TestCase):

    def setUp(self):
        self.ui = _code(os.path.join(HERE, "control_ui.html"))
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            self.app = fh.read()

    def test_the_route_passes_the_id_through(self):
        self.assertEqual(self.app.count("self._theatre_session(num, pack=pack, sid=_sid_q)"), 1,
                         "/api/session drops ?sid=, so the page's id never reaches the lookup")

    def test_the_load_sends_the_id_it_was_shown(self):
        self.assertEqual(self.ui.count("(_wantSid ? '&sid=' + encodeURIComponent(_wantSid) : '')"), 1,
                         "thLoadSession asks by place only")
        self.assertEqual(self.ui.count(
            "var _wantSid = String(sid || ((TH.sessions && TH.sessions[n - 1]) || {}).sessionId || '');"), 1,
            "thLoadSession no longer takes the id from the row he clicked")

    def test_a_reel_under_another_id_is_not_painted(self):
        self.assertEqual(self.ui.count("if (_wantSid && j.sessionId && String(j.sessionId) !== _wantSid){"), 1,
                         "a reel that came back under another id would be painted as the one he chose")

    def test_the_dossier_hands_in_its_own_reel(self):
        self.assertEqual(self.ui.count("thLoadSession(Number(n) || 1, false, DOSSIER.sid)"), 1,
                         "the dossier's ▶ opens by place, not by the reel it describes")

    def test_the_delete_names_the_reel_he_is_watching(self):
        """The delete is the expensive twin: by place, a shifted list removes the journal rows and frames
        of the reel below his. The lookup above decides it, so the route must hand it the id."""
        self.assertEqual(self.app.count("sess = self._theatre_session(n, sid=_sid_d)"), 1,
                         "/api/session/delete finds its reel by place again")
        self.assertEqual(self.app.count('if _sid_d and sess.get("sessionId") != _sid_d:'), 1,
                         "a delete whose reel came back under another id is not refused")
        self.assertEqual(self.ui.count("JSON.stringify({ n: meta.n || TH.sn, sid: TH.sessionId || meta.sessionId || '' })"), 1,
                         "the theatre's delete does not send the id of the reel he is watching")


COUNT_JS = r"""
var frames = 0, seen = [];
function requestAnimationFrame(f){ frames++; if (frames < 50) f(frames * 40); }
var window = {matchMedia: function(){ return {matches: false}; }};
function El(t){ var self = this; this._t = t; this.cls = {}; this.offsetWidth = 1;
  this.classList = {add: function(c){ self.cls[c] = 1; }, remove: function(c){ delete self.cls[c]; }}; }
Object.defineProperty(El.prototype, 'textContent', {get: function(){ return this._t; },
  set: function(v){ seen.push(v); this._t = v; }});
var els = [new El('64'), new El('3 READ'), new El('1,208')];
var root = {querySelectorAll: function(){ return els; }};
%s
_animCounts(root);
process.stdout.write(JSON.stringify({frames: frames, seen: seen, final: els.map(function(e){ return e._t; }),
  popped: els.every(function(e){ return !!e.cls['dsr-pop']; })}));
"""


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class ANumberNeverCountsOnScreen(unittest.TestCase):
    """GrokBot read the dossier's numbers mid-count for four ticks (S41 0 -> 6 -> 8, S175 60 -> 63 -> 61, S53 105/106,
    S74 0/0/0/0 then 3/11/1): the D20 count-up wrote every in-between value, and on a busy machine those frames
    stayed up for seconds. The value is written once; only opacity moves."""

    def test_the_dossier_numbers_are_never_anything_but_their_value(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        lo = ui.find("  function _animCounts(root){")
        self.assertGreaterEqual(lo, 0, "_animCounts is gone from control_ui.html")
        hi = ui.find("\n  }\n", lo)
        p = subprocess.run(["node", "-"], input=COUNT_JS % ui[lo:hi + 4], capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr[-600:])
        out = json.loads(p.stdout)
        self.assertEqual(out["seen"], [], "the dossier wrote numbers that are not the value: %s (REG-1933)" % out["seen"][:8])
        self.assertEqual(out["final"], ["64", "3 READ", "1,208"])
        self.assertEqual(out["frames"], 0, "the numbers are tweened on animation frames again")
        self.assertTrue(out["popped"], "the arrival is no longer marked for its (opacity-only) animation")

    def test_the_live_reads_meter_never_shows_a_number_in_between(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        lo = ui.find("  function tweenReads(target){")
        self.assertGreaterEqual(lo, 0, "tweenReads is gone from control_ui.html")
        hi = ui.find("\n  }\n", lo)
        js = ("var seen = [], frames = 0; function requestAnimationFrame(f){ frames++; if (frames < 50) f(frames * 40); }\n"
              "function cancelAnimationFrame(){}\nvar performance = {now: function(){ return 0; }};\n"
              "var window = {requestAnimationFrame: requestAnimationFrame};\n"
              "var el = {classList: {add: function(){}, remove: function(){}}, offsetWidth: 1};\n"
              "Object.defineProperty(el, 'textContent', {set: function(v){ seen.push(String(v)); }});\n"
              "function $(){ return el; }\nvar _reads = 0, _readsRaf = null, _readsTarget = -1;\n"
              + ui[lo:hi + 4] + "\ntweenReads(5); tweenReads(12);\n"
              "process.stdout.write(JSON.stringify({seen: seen, frames: frames}));")
        p = subprocess.run(["node", "-"], input=js, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr[-600:])
        out = json.loads(p.stdout)
        self.assertEqual(out["seen"], ["5", "12"], "the reads meter wrote numbers in between: %s (REG-1933)" % out["seen"][:10])


RED_PROOF = [
    {
        "why": "REG-1933 - the live reads meter eases between counts again and shows numbers that were never the count",
        "file": "tv/control_ui.html",
        "find": "    _reads = target; el.textContent = target;\n    if (!first)",
        "replace": "    if (!first) el.textContent = Math.round((_reads + target) / 2);\n    _reads = target; el.textContent = target;\n    if (!first)",
        "matches": 1,
    },
    {
        "why": "REG-1933 - the dossier counts its numbers up again: every frame in between shows a number that is not true",
        "file": "tv/control_ui.html",
        "find": "      try { el.classList.remove('dsr-pop'); void el.offsetWidth; el.classList.add('dsr-pop'); } catch (e) {}\n",
        "replace": "      var f = el.textContent; el.textContent = '0'; requestAnimationFrame(function(){ el.textContent = f; });\n",
        "matches": 1,
    },
    {
        "why": "REG-1933 - the server finds the reel by id and then ignores it: ?n=2&sid=... answers with "
               "whatever reel now sits at 2",
        "file": "tv/control_app.py",
        "find": "                    return {\"error\": \"reel %s is no longer in the journal - nothing else was opened\" % sid,\n"
                "                            \"sessionId\": sid}\n                n = _at\n",
        "replace": "                    return {\"error\": \"reel %s is no longer in the journal - nothing else was opened\" % sid,\n"
                   "                            \"sessionId\": sid}\n                pass\n",
        "matches": 1,
    },
    {
        "why": "REG-1933 - a sid the journal no longer holds falls through to the positional answer",
        "file": "tv/control_app.py",
        "find": "                if not _at:\n                    return {\"error\": \"reel %s is no longer",
        "replace": "                if False:\n                    return {\"error\": \"reel %s is no longer",
        "matches": 1,
    },
    {
        "why": "REG-1933 - the route stops passing ?sid= through",
        "file": "tv/control_app.py",
        "find": "self._theatre_session(num, pack=pack, sid=_sid_q)",
        "replace": "self._theatre_session(num, pack=pack)",
        "matches": 1,
    },
    {
        "why": "REG-1933 - the page stops checking which reel came back, so a shifted shelf paints a neighbour",
        "file": "tv/control_ui.html",
        "find": "if (_wantSid && j.sessionId && String(j.sessionId) !== _wantSid){",
        "replace": "if (false){",
        "matches": 1,
    },
    {
        "why": "REG-1933 - film is the index again, not the disk: a frame that is gone plays as a beat with no picture",
        "file": "tv/control_app.py",
        "find": "                            _kept_f = [it for it in _frames if str(it.get(\"f\") or \"\") in _ondisk]\n",
        "replace": "                            _kept_f = list(_frames)\n",
        "matches": 1,
    },
    {
        "why": "REG-1933 - the delete finds its reel by place again: a shifted shelf deletes the reel below his",
        "file": "tv/control_app.py",
        "find": "sess = self._theatre_session(n, sid=_sid_d)",
        "replace": "sess = self._theatre_session(n)",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
