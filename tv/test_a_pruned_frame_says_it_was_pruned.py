# -*- coding: utf-8 -*-
"""REG-3207 (GrokBot v3864, 2026-11-05) - A FRAME A DELETER TOOK SAYS SO, BY WHOM AND WHEN, AND A GUEST NEVER ASKS TO UPDATE.

MEASURED by GrokBot on v3864: his Mac console's failed requests were 3 /hist 404s; the guest console's 581 failed
requests were /art/* 404s plus /api/update 404s.

/hist: _serve_hist answered a frame that is not on disk with a bare JSON 404, so every <img> that asked for it
(about a dozen sites: the shelf cards, the montage, the theatre film and scrub, the tally sheet) drew a broken picture or
hid itself - opacity 0, display none - and nothing said the frame had been deleted on purpose. Who took a picture
already had ONE answer, read_pictures.who_took (the doctor row 'a read left no picture' and /api/picture_status), over
the retention lane's reel_tombstones.json, the recorder's reel_reaps.jsonl and its refusal record. /hist now asks the
same judge: an <img> (Sec-Fetch-Dest: image, or an Accept that leads with image/) gets a 16:9 placeholder that says
FRAME PRUNED, by whom and when - or FRAME NOT ON THIS PC with UNKNOWN when no record names it; a fetch() keeps its 404,
with the same reason as JSON. A thumbnail (?w=480 or less) gets a compact card whose words stay legible at 46px.

The second eye on the first version (reproduced on a copy of his record):
  * the retention lane trims one reel many times (one reel: 92 tombstones; the first took 2,847 frames down to 49) and
    the reader kept the LAST tombstone per reel, dating the measured frame's prune 28 Oct instead of 9 Oct. Now the
    EARLIEST deleter that could have taken the frame wins: a tombstone counts only if written after the frame was
    filmed and its kept list does not hold it. who_took also read `kept` only as {"frame": ...} dicts, a shape
    reel_retention never writes (it writes bare file names), so every trim read as keeping nothing; both are read now;
  * frames the RECORDER took (reel_reaps.jsonl names them) read "no retention record" - UNKNOWN - when a record existed;
  * the placeholder's 18px words were ~2px tall in the 46px scrub strip.

/api/update: the guest seat is a read-only mirror; `update` is deliberately not mirrored (tv/GUEST_SEAT.md). The console
asked anyway - at launch and every 15 minutes. The mirror's /api/status says `guest: true`, but the guest GrokBot
measured is a scratch copy with no guest key, so the console also remembers the first 404 from /api/update (a real
console's GET never answers 404) and never asks again for the life of the page: the banner, the footer check and
UPDATE NOW all read window._noUpdateHere.

Driven: the real _serve_hist over a fixture shelf and fixture records (never his); the guest half by reading the
console's code (comments stripped, each whole expression). RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
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
import control_app as CA  # noqa: E402
import guest_profile as GP  # noqa: E402
import read_pictures as RP  # noqa: E402

DELETED = 1793000900000          # a fixed deletedTs (ms): 15 min after the fixture frames were filmed
IMG_ACCEPT = "image/webp,image/avif,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5"
# one reel the retention lane trimmed three times (the measured shape: many tombstones for one reel)
T1, T2, T3 = 1791500000000, 1792000000000, 1792500000000
REAPED_AT = 1790951695811        # a recorder read-eviction that named a loose frame


def _when(ms):
    """The stamp written independently of the code under test: local time, 24-hour, day zero-padded."""
    return time.strftime("%d %b %Y %H:%M", time.localtime(ms / 1000.0))


def _svg_text(svg):
    return " ".join(re.findall(r">([^<]+)</text>", svg))


class APrunedFrameSaysItWasPruned(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="hist_gone_")
        self.hist = os.path.join(self.root, "frames", "hist")
        os.makedirs(os.path.join(self.hist, "reel_s_1"))
        with io.open(os.path.join(self.hist, "reel_s_1", "f_1793000002000.jpg"), "wb") as fh:
            fh.write(b"\xff\xd8KEPT-WITNESS")                      # the evidence frame a release keeps
        self.tomb = os.path.join(self.root, "frames", "reel_tombstones.json")
        self.reaps = os.path.join(self.root, RP.REAPS)
        self._write_tombs({"reels": [{"reel": "reel_s_1", "session": "s_1", "deletedTs": DELETED, "why": "spent"}]})
        self.patches = [mock.patch.object(CA, "HIST_DIR", self.hist)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        RP._RECORDS_MEMO.update(key=None, val=None)
        shutil.rmtree(self.root, True)

    def _write_tombs(self, doc):
        with io.open(self.tomb, "w", encoding="utf-8") as fh:
            fh.write(doc if isinstance(doc, str) else json.dumps(doc))
        RP._RECORDS_MEMO.update(key=None, val=None)

    def _write_reaps(self, rows):
        with io.open(self.reaps, "w", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(r) + "\n" for r in rows))
        RP._RECORDS_MEMO.update(key=None, val=None)

    def _get(self, rel, headers, query=""):
        h = CA.Handler.__new__(CA.Handler)
        got = {"headers": {}}
        h.path = "/hist/" + rel + (("?" + query) if query else "")
        h.headers = headers
        h._json = lambda code, obj: got.update(code=code, body=obj)
        h.send_response = lambda code: got.update(code=code)
        h.send_header = lambda k, v: got["headers"].__setitem__(k, v)
        h.end_headers = lambda: None
        h.wfile = io.BytesIO()
        h._serve_hist(rel)
        got["bytes"] = h.wfile.getvalue()
        return got

    def test_the_records_are_the_fixture_ones(self):
        import reel_retention as RR
        self.assertEqual(os.path.realpath(self.tomb), os.path.realpath(RR._tombstone_path(self.hist)),
                         "the lookup would read a tombstone record other than the fixture's (his live one?)")
        self.assertEqual(os.path.realpath(self.root), os.path.realpath(RP.root_of(self.hist)),
                         "the lookup would read a reap record other than the fixture's (his live one?)")

    def test_an_img_asking_for_a_pruned_frame_gets_a_placeholder_that_says_pruned_and_when(self):
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Accept": IMG_ACCEPT})
        self.assertEqual(200, got.get("code"), "an <img> still gets an error it can only draw as a broken picture")
        self.assertEqual("image/svg+xml; charset=utf-8", got["headers"].get("Content-Type"))
        self.assertEqual("no-store", got["headers"].get("Cache-Control"), "a placeholder must never be cached as a frame")
        self.assertEqual("pruned", got["headers"].get("X-Hist-Gone"))
        svg = got["bytes"].decode("utf-8")
        print("   placeholder: %s" % _svg_text(svg)[:220])
        self.assertIn(">FRAME PRUNED<", svg)
        self.assertIn("pruned by the retention lane on %s" % _when(DELETED), _svg_text(svg),
                      "the placeholder does not say WHO pruned it and WHEN")

    def test_sec_fetch_dest_image_is_an_image_whatever_it_accepts(self):
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Sec-Fetch-Dest": "image", "Accept": "*/*"})
        self.assertEqual("image/svg+xml; charset=utf-8", got["headers"].get("Content-Type"))

    def test_a_fetch_still_gets_a_404_with_the_reason(self):
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Accept": "*/*"})
        self.assertEqual(404, got.get("code"), "a fetch() was told a missing frame is there")
        body = got.get("body") or {}
        self.assertEqual("pruned", body.get("gone"))
        self.assertEqual("released", body.get("code"))
        self.assertEqual("the retention lane", body.get("by"))
        self.assertEqual(DELETED, body.get("deletedTs"))
        self.assertEqual("reel_s_1", body.get("reel"))

    def test_a_frame_no_record_names_is_unknown_never_pruned(self):
        for rel in ("reel_s_9/f_1793000001000.jpg", "10_1793000000000.jpg"):
            got = self._get(rel, {"Accept": IMG_ACCEPT})
            svg = got["bytes"].decode("utf-8")
            self.assertEqual("unknown", got["headers"].get("X-Hist-Gone"), rel)
            self.assertIn(">FRAME NOT ON THIS PC<", svg, "%s: a frame no record names was called pruned" % rel)
            self.assertNotIn("PRUNED", svg, rel)
            self.assertIn("UNKNOWN", _svg_text(svg), rel)

    def test_an_unreadable_record_is_unknown_not_none_deleted(self):
        self._write_tombs("{not json")
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Accept": "*/*"})
        body = got.get("body") or {}
        self.assertEqual("unknown", body.get("gone"))
        self.assertIn("the tombstones could not be read", body.get("say") or "",
                      "an unreadable record read as 'no record names it'")

    def test_a_pruned_reel_with_no_deleted_time_says_when_is_unknown(self):
        self._write_tombs({"reels": [{"reel": "reel_s_1", "session": "s_1"}]})
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Accept": "*/*"})
        body = got.get("body") or {}
        self.assertEqual("pruned", body.get("gone"))
        self.assertIsNone(body.get("deletedTs"), "a deletion time nobody recorded was filled in")
        self.assertIn("(when: UNKNOWN)", body.get("say") or "")

    def test_a_reel_trimmed_many_times_dates_each_frame_by_the_trim_that_took_it(self):
        """The measured defect: the LAST tombstone of a reel trimmed 92 times dated a frame the FIRST trim took."""
        self._write_tombs({"reels": [
            {"reel": "reel_s_2", "session": "s_2", "deletedTs": T1, "why": "spent",
             "kept": ["f_1791000001000.jpg", "f_1791000002000.jpg"]},             # the writer's shape: bare names
            {"reel": "reel_s_2", "session": "s_2", "deletedTs": T2, "why": "spent", "kept": ["f_1791000001000.jpg"]},
            {"reel": "reel_s_2", "session": "s_2", "deletedTs": T3, "why": "spent"},   # whole: nothing kept
        ]})
        want = {"f_1791000003000": T1,      # filmed before the first trim, not kept by it
                "f_1791000002000": T2,      # kept by the first trim, not by the second
                "f_1791000001000": T3,      # kept twice, gone with the reel
                "f_1791700000000": T2}      # filmed AFTER the first trim: the first cannot have taken it
        for stem, ts in sorted(want.items()):
            body = self._get("reel_s_2/%s.jpg" % stem, {"Accept": "*/*"}).get("body") or {}
            self.assertEqual(("pruned", ts), (body.get("gone"), body.get("deletedTs")),
                             "%s: dated by the wrong trim (%s, want %s): %s" % (stem, body.get("deletedTs"), ts,
                                                                                body.get("say")))
            self.assertIn(_when(ts), body.get("say") or "")
        late = self._get("reel_s_2/f_1792600000000.jpg", {"Accept": "*/*"}).get("body") or {}
        self.assertEqual("unknown", late.get("gone"),
                         "a frame filmed after every trim was blamed on one of them: %s" % late.get("say"))

    def test_the_doctor_and_hist_ask_one_judge(self):
        """who_took (the doctor row, /api/picture_status) and /hist answer the same frame the same way."""
        self._write_tombs({"reels": [
            {"reel": "reel_s_2", "session": "s_2", "deletedTs": T1, "kept": ["f_1791000002000.jpg"]},
            {"reel": "reel_s_2", "session": "s_2", "deletedTs": T2}]})
        code, words = RP.who_took("reel_s_2/f_1791000002000", [], RP.load_tombstones(self.hist), [])
        self.assertEqual("released", code, words)
        self.assertIn(_when(T2), words, "the doctor's reader still takes a kept frame as released by the first trim")
        body = self._get("reel_s_2/f_1791000002000.jpg", {"Accept": "*/*"}).get("body") or {}
        self.assertEqual(T2, body.get("deletedTs"))

    def test_a_frame_the_recorder_took_names_the_recorder(self):
        self._write_reaps([
            {"ts": REAPED_AT, "reel": "loose", "frames": 1, "removed": True, "shelfBefore": -1,
             "by": "recorder-read-eviction", "names": ["3_1788213448965.jpg"]},
            {"ts": REAPED_AT + 1000, "reel": "reel_s_5", "frames": 40, "removed": True, "shelfBefore": 9,
             "by": "recorder-disk-floor"}])                                          # a whole reel, the old shape
        for rel in ("3_1788213448965.jpg", "reel_s_5/f_1788000000000.jpg"):
            got = self._get(rel, {"Accept": IMG_ACCEPT})
            svg = _svg_text(got["bytes"].decode("utf-8"))
            self.assertEqual("pruned", got["headers"].get("X-Hist-Gone"),
                             "%s: the recorder's own record names it and it still read UNKNOWN: %s" % (rel, svg))
            self.assertIn("pruned by the recorder's disk-floor reaper on", svg, rel)
        body = self._get("3_1788213448965.jpg", {"Accept": "*/*"}).get("body") or {}
        self.assertEqual(("reaped", REAPED_AT), (body.get("code"), body.get("deletedTs")))

    def test_a_thumbnail_gets_words_it_can_read_at_46px(self):
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Accept": IMG_ACCEPT}, query="w=160")
        svg = got["bytes"].decode("utf-8")
        vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
        self.assertIsNotNone(vb)
        height = float(vb.group(2))
        sizes = dict((c, float(px)) for c, px in re.findall(r"\.(\w)\{font:(?:700 )?(\d+)px", svg))
        print("   thumbnail: %s (viewBox %s, fonts %r)" % (_svg_text(svg), vb.group(0), sizes))
        self.assertIn(">PRUNED<", svg)
        self.assertIn(">%s<" % _when(DELETED).rsplit(" ", 1)[0], svg, "the thumbnail drops WHEN")
        # at the scrub strip's 46px, the verdict must be >= ~11px and the date >= ~8px
        self.assertGreaterEqual(sizes.get("h", 0) / height * 46, 11.0, "the verdict is unreadable at 46px")
        self.assertGreaterEqual(sizes.get("d", 0) / height * 46, 8.0, "the date is unreadable at 46px")
        full = self._get("reel_s_1/f_1793000001000.jpg", {"Accept": IMG_ACCEPT}, query="w=1280")["bytes"].decode()
        self.assertIn(">FRAME PRUNED<", full, "the theatre's full frame lost the full card")

    def test_a_caller_with_its_own_fallback_keeps_the_404(self):
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Accept": IMG_ACCEPT}, query="w=440&gone=404")
        self.assertEqual(404, got.get("code"), "gone=404 still drew a placeholder over the drill's raw read text")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = _code(fh.read())
        self.assertEqual(1, ui.count(
            "'<img src=\"/hist/' + encodeURIComponent(f0.frameId) + '.jpg?w=440&gone=404\" alt=\"\" "
            "onerror=\"this.style.display=\\'none\\'\">'"),
            "the reads drill no longer keeps its 404, so a placeholder covers the read's raw text")

    def test_a_frame_on_disk_is_still_served_whole(self):
        got = self._get("reel_s_1/f_1793000002000.jpg", {"Accept": IMG_ACCEPT})
        self.assertEqual(200, got.get("code"))
        self.assertEqual("image/jpeg", got["headers"].get("Content-Type"))
        self.assertEqual(b"\xff\xd8KEPT-WITNESS", got["bytes"])

    def test_a_path_outside_hist_is_still_refused(self):
        got = self._get("../reel_tombstones.jpg", {"Accept": IMG_ACCEPT})
        self.assertEqual(403, got.get("code"))


def _code(src):
    """The console's script with // and /* */ comments blanked (line count kept), so a guard reads code only."""
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    return re.sub(r"(?m)(^|[\s;{}(),])//[^\n]*", r"\1", src)


class AGuestNeverAsksToUpdate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            cls.ui = _code(fh.read())

    def _body(self, start, end):
        self.assertEqual(1, self.ui.count(start), "anchor not unique: %r" % start)
        i = self.ui.index(start)
        j = self.ui.index(end, i)
        return self.ui[i:j]

    def test_the_mirror_says_guest_and_the_console_reads_that_key(self):
        st = GP.rewrite_status({"ver": "v1", "identity": {"computer": "x"}}, {})
        self.assertIs(True, st.get("guest"), "the mirror's status no longer says guest:true")
        f = self._body("window._isGuestSeat = function(){", "\n  };")
        self.assertIn("if (ls && typeof ls === 'object') return Promise.resolve(ls.guest === true);", f,
                      "the guest answer does not read the status the console already holds, by the mirror's key")
        self.assertIn("_guestSeatAsk = fetch(API + '/api/status').then(function(r){ return r.json(); })", f)
        self.assertIn(".then(function(j){ return !!(j && j.guest === true); })", f)
        self.assertIn(".catch(function(){ _guestSeatAsk = null; return false; });", f,
                      "an unreadable status must not make a real console stop checking for good")

    def test_a_404_from_the_update_door_is_remembered(self):
        """The guest GrokBot measured has no guest key; a 404 is the one signal every guest gives."""
        self.assertEqual(1, self.ui.count(
            "window._updateDoorGone = function(r){ if (r && r.status === 404) _updDoorGone = true; return _updDoorGone; };"),
            "a 404 from /api/update is not remembered, so the console keeps asking a server with no such door")
        self.assertEqual(1, self.ui.count(
            "window._noUpdateHere = async function(){ return _updDoorGone || (await window._isGuestSeat()); };"),
            "the callers' one answer no longer covers both the guest key and a remembered 404")
        self.assertEqual(1, self.ui.count("var _updDoorGone = false;"))

    def test_a_real_console_never_answers_404_on_its_update_door(self):
        """The memo is safe only because the real GET route turns every failure into 200 ok:false."""
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            app = fh.read()
        anchor = "            # v817 / v1418 — fleet unity: force-fetch then report behind-count + howTo.\n"
        self.assertEqual(1, app.count(anchor))
        i = app.index(anchor)
        blk = app[i:app.index("\n        if path == ", i)]
        self.assertIn('self._json(200, {"ok": False, "msg": "update check failed: %s" % e})', blk)
        self.assertNotIn("404", blk, "the real update door can answer 404, so a remembered 404 would silence it")

    def _asks_after_check(self, body, fetch_expr, label):
        g = body.find("if (await window._noUpdateHere()){")
        u = body.find(fetch_expr)
        m = body.find("if (window._updateDoorGone(r)){", u)
        jn = body.find("r.json()", u)
        self.assertGreater(g, 0, "%s no longer asks whether this server has an update door" % label)
        self.assertGreater(u, g, "%s asks /api/update before it asks whether it may" % label)
        self.assertIn("return", body[g:u], "%s's check does not stop it asking" % label)
        self.assertGreater(m, u, "%s does not remember a 404 from /api/update" % label)
        self.assertLess(m, jn, "%s reads the 404's body before it remembers the 404" % label)

    def test_the_banner_check_does_not_ask_on_a_guest(self):
        self._asks_after_check(self._body("async function look(){", "\n    look();"),
                               "fetch(API + '/api/update')", "the banner")

    def test_the_footer_check_does_not_ask_on_a_guest(self):
        self._asks_after_check(self._body("window._fleetUpdateCheck = async function(){", "\n  };"),
                               "fetch(API + '/api/update')", "the footer")

    def test_update_now_never_posts_a_pull_on_a_guest(self):
        self._asks_after_check(self._body("go.onclick = async function(){", "\n    };"),
                               "fetch(API + '/api/update', { method: 'POST' })", "UPDATE NOW")


RED_PROOF = [
    {"why": "REG-3207 - an <img> that leads its Accept with image/ is no longer told apart from a fetch()",
     "file": "tv/control_app.py",
     "find": "        return str(headers.get(\"Accept\") or \"\").strip().lower().startswith(\"image/\")\n",
     "replace": "        return False\n",
     "matches": 1},
    {"why": "REG-3207 - a missing frame is a bare 404 again, drawn as a broken picture",
     "file": "tv/control_app.py",
     "find": "            if _hist_wants_image(getattr(self, \"headers\", None)) and (qs.get(\"gone\") or [\"\"])[0] != \"404\":\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3207 - the drill's opt-out is ignored, so a placeholder covers the read's raw text",
     "file": "tv/control_app.py",
     "find": " and (qs.get(\"gone\") or [\"\"])[0] != \"404\":\n",
     "replace": ":\n",
     "matches": 1},
    {"why": "REG-3207 - the reads drill stops asking for the 404 it falls back on",
     "file": "tv/control_ui.html",
     "find": ".jpg?w=440&gone=404\" alt=\"\"",
     "replace": ".jpg?w=440\" alt=\"\"",
     "matches": 1},
    {"why": "REG-3207 - a frame no record names is drawn as PRUNED",
     "file": "tv/control_app.py",
     "find": "    out[\"state\"] = (\"pruned\" if code in (\"released\", \"reaped\")\n",
     "replace": "    out[\"state\"] = (\"pruned\" if True\n",
     "matches": 1},
    {"why": "REG-3207 - the placeholder drops WHEN the frame was pruned",
     "file": "tv/control_app.py",
     "find": "    out[\"deletedTs\"], out[\"when\"], out[\"by\"] = g.get(\"ts\"), g.get(\"when\"), g.get(\"by\")\n",
     "replace": "    out[\"deletedTs\"], out[\"when\"], out[\"by\"] = g.get(\"ts\"), None, g.get(\"by\")\n",
     "matches": 1},
    {"why": "REG-3207 - an unreadable tombstone record reads as one that names nothing",
     "file": "tv/read_pictures.py",
     "find": "        return [r for r in (rows or []) if isinstance(r, dict)]\n    except Exception:\n        return None\n",
     "replace": "        return [r for r in (rows or []) if isinstance(r, dict)]\n    except Exception:\n        return []\n",
     "matches": 1},
    {"why": "REG-3207 (second eye) - the LAST tombstone of a many-times-trimmed reel dates the frame, not the first",
     "file": "tv/read_pictures.py",
     "find": "        i = min(range(len(events)), key=lambda j: (events[j][0] is None, events[j][0] or 0, j))\n",
     "replace": "        i = len(events) - 1\n",
     "matches": 1},
    {"why": "REG-3207 (second eye) - a trim that KEPT the frame is blamed for taking it",
     "file": "tv/read_pictures.py",
     "find": "            if stem and stem in _kept_stems(tb):\n                continue                      # this trim KEPT it\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3207 (second eye) - kept lists in the writer's own shape (bare file names) are not read",
     "file": "tv/read_pictures.py",
     "find": "        if isinstance(k, dict):\n            k = k.get(\"frame\")\n        if isinstance(k, str) and k:\n",
     "replace": "        if not isinstance(k, dict):\n            continue\n        k = k.get(\"frame\")\n        if isinstance(k, str) and k:\n",
     "matches": 1},
    {"why": "REG-3207 (second eye) - a tombstone written before the frame was filmed is blamed for it",
     "file": "tv/read_pictures.py",
     "find": "            if filmed and t and t < filmed:\n                continue\n            events.append((t, \"released\",",
     "replace": "            events.append((t, \"released\",",
     "matches": 1},
    {"why": "REG-3207 (second eye) - frames the recorder's reap record names read as UNKNOWN",
     "file": "tv/read_pictures.py",
     "find": "            names.setdefault(_stem(n), []).append(r)\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-3207 (second eye) - a thumbnail gets the full card, its words ~2px tall in the scrub strip",
     "file": "tv/control_app.py",
     "find": "compact=(_gw.isdigit() and 0 < int(_gw) <= 480))",
     "replace": "compact=False)",
     "matches": 1},
    {"why": "REG-3207 - the banner asks /api/update on a guest, which has no such route",
     "file": "tv/control_ui.html",
     "find": "        if (await window._noUpdateHere()){ bar.hidden = true; return; }   // REG-3207 - a mirror has nothing to pull\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3207 - the guest answer reads a key the mirror never writes",
     "file": "tv/control_ui.html",
     "find": "    if (ls && typeof ls === 'object') return Promise.resolve(ls.guest === true);\n",
     "replace": "    if (ls && typeof ls === 'object') return Promise.resolve(ls.isGuest === true);\n",
     "matches": 1},
    {"why": "REG-3207 (second eye) - a 404 from /api/update is never remembered, so a keyless guest is asked forever",
     "file": "tv/control_ui.html",
     "find": "if (r && r.status === 404) _updDoorGone = true;",
     "replace": "if (false) _updDoorGone = true;",
     "matches": 1},
    {"why": "REG-3207 (second eye) - the banner reads the 404 instead of remembering it",
     "file": "tv/control_ui.html",
     "find": "        if (window._updateDoorGone(r)){ bar.hidden = true; return; }   // REG-3207 - no update door on this server: never ask again\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3207 - UPDATE NOW posts a pull to a guest",
     "file": "tv/control_ui.html",
     "find": "      if (await window._noUpdateHere()){   // REG-3207 - the mirror has no checkout; never POST it a pull\n",
     "replace": "      if (false){\n",
     "matches": 1},
    {"why": "REG-3207 - the footer's check asks /api/update on a guest",
     "file": "tv/control_ui.html",
     "find": "      if (await window._noUpdateHere()){\n        toast('this is a guest seat",
     "replace": "      if (false){\n        toast('this is a guest seat",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
