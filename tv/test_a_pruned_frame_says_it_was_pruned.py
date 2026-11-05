# -*- coding: utf-8 -*-
"""REG-3207 (GrokBot v3864, 2026-11-05) - A FRAME THE RETENTION LANE PRUNED SAYS SO, AND A GUEST NEVER ASKS TO UPDATE.

MEASURED by GrokBot on v3864: his Mac console's failed requests were 3 /hist 404s; the guest console's 581 failed
requests were /art/* 404s plus /api/update 404s.

/hist: _serve_hist answered a frame that is not on disk with a bare JSON 404, so every <img> that asked for it
(about a dozen sites: the shelf cards, the montage, the theatre film and scrub, the tally sheet) drew a broken picture or
hid itself - opacity 0, display none - and nothing said the frame had been pruned on purpose. The record that says so
already existed: reel_tombstones.json, written by the retention lane BEFORE it removes a reel, with `deletedTs`.
Now a missing frame is looked up there: an <img> (Sec-Fetch-Dest: image, or an Accept that leads with image/) gets a
16:9 placeholder that says FRAME PRUNED and when, or FRAME NOT ON THIS PC with UNKNOWN when no record names its reel;
a fetch() keeps its 404, with the same reason as JSON. A frame that is on disk is served exactly as before.

/api/update: the guest seat is a read-only mirror served by the box's bridge; `update` is deliberately not mirrored
(tv/GUEST_SEAT.md) and its /api/status carries `guest: true` (guest_profile.rewrite_status). The console asked anyway -
at launch and every 15 minutes. Now the banner's check, the footer's check and UPDATE NOW all read that one answer
(window._isGuestSeat) and do not ask when it is true.

Driven: the real _serve_hist over a fixture shelf and a fixture tombstone record (never his); the guest half by
reading the console's code (comments stripped, each whole expression). RED_PROOF below.
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

DELETED = 1793000000000          # a fixed deletedTs (ms) in the fixture record
IMG_ACCEPT = "image/webp,image/avif,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5"


def _when(ms):
    """The stamp written independently of the code under test: local time, 24-hour, no leading zero on the day."""
    t = time.localtime(ms / 1000.0)
    return "%d %s %d %s" % (t.tm_mday, time.strftime("%b", t), t.tm_year, time.strftime("%H:%M", t))


class APrunedFrameSaysItWasPruned(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="hist_gone_")
        self.hist = os.path.join(self.root, "frames", "hist")
        os.makedirs(os.path.join(self.hist, "reel_s_1"))
        with io.open(os.path.join(self.hist, "reel_s_1", "f_1793000002000.jpg"), "wb") as fh:
            fh.write(b"\xff\xd8KEPT-WITNESS")                      # the evidence frame a release keeps
        self.tomb = os.path.join(self.root, "frames", "reel_tombstones.json")
        self._write_tombs({"reels": [{"reel": "reel_s_1", "session": "s_1", "deletedTs": DELETED, "why": "spent"}]})
        self.patches = [mock.patch.object(CA, "HIST_DIR", self.hist)]
        for p in self.patches:
            p.start()
        CA._HIST_GONE_CACHE.update(key=None, rows=None)

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        CA._HIST_GONE_CACHE.update(key=None, rows=None)
        shutil.rmtree(self.root, True)

    def _write_tombs(self, doc):
        with io.open(self.tomb, "w", encoding="utf-8") as fh:
            fh.write(doc if isinstance(doc, str) else json.dumps(doc))
        CA._HIST_GONE_CACHE.update(key=None, rows=None)

    def _get(self, rel, headers):
        h = CA.Handler.__new__(CA.Handler)
        got = {"headers": {}}
        h.path = "/hist/" + rel
        h.headers = headers
        h._json = lambda code, obj: got.update(code=code, body=obj)
        h.send_response = lambda code: got.update(code=code)
        h.send_header = lambda k, v: got["headers"].__setitem__(k, v)
        h.end_headers = lambda: None
        h.wfile = io.BytesIO()
        h._serve_hist(rel)
        got["bytes"] = h.wfile.getvalue()
        return got

    def test_the_tombstone_path_is_the_fixture_one(self):
        import reel_retention as RR
        self.assertEqual(os.path.realpath(self.tomb), os.path.realpath(RR._tombstone_path(self.hist)),
                         "the lookup would read a record other than the fixture's (his live one?)")

    def test_an_img_asking_for_a_pruned_frame_gets_a_placeholder_that_says_pruned_and_when(self):
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Accept": IMG_ACCEPT})
        self.assertEqual(200, got.get("code"), "an <img> still gets an error it can only draw as a broken picture")
        self.assertEqual("image/svg+xml; charset=utf-8", got["headers"].get("Content-Type"))
        self.assertEqual("no-store", got["headers"].get("Cache-Control"), "a placeholder must never be cached as a frame")
        self.assertEqual("pruned", got["headers"].get("X-Hist-Gone"))
        svg = got["bytes"].decode("utf-8")
        print("   placeholder: %s" % re.sub(r"<[^>]+>", " | ", svg).replace(" |  | ", " | ")[:220])
        self.assertIn(">FRAME PRUNED<", svg)
        text = " ".join(re.findall(r">([^<]+)</text>", svg))
        self.assertIn("pruned by the retention lane on %s" % _when(DELETED), text,
                      "the placeholder does not say WHEN the lane pruned it")

    def test_sec_fetch_dest_image_is_an_image_whatever_it_accepts(self):
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Sec-Fetch-Dest": "image", "Accept": "*/*"})
        self.assertEqual("image/svg+xml; charset=utf-8", got["headers"].get("Content-Type"))

    def test_a_fetch_still_gets_a_404_with_the_reason(self):
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Accept": "*/*"})
        self.assertEqual(404, got.get("code"), "a fetch() was told a missing frame is there")
        body = got.get("body") or {}
        self.assertEqual("pruned", body.get("gone"))
        self.assertEqual(DELETED, body.get("deletedTs"))
        self.assertEqual("reel_s_1", body.get("reel"))

    def test_a_frame_no_record_names_is_unknown_never_pruned(self):
        for rel in ("reel_s_9/f_1793000001000.jpg", "10_1793000000000.jpg"):
            got = self._get(rel, {"Accept": IMG_ACCEPT})
            svg = got["bytes"].decode("utf-8")
            self.assertEqual("unknown", got["headers"].get("X-Hist-Gone"), rel)
            self.assertIn(">FRAME NOT ON THIS PC<", svg, "%s: a frame no record names was called pruned" % rel)
            self.assertNotIn("PRUNED", svg, rel)
            self.assertIn("UNKNOWN", " ".join(re.findall(r">([^<]+)</text>", svg)), rel)

    def test_an_unreadable_record_is_unknown_not_none_deleted(self):
        self._write_tombs("{not json")
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Accept": "*/*"})
        body = got.get("body") or {}
        self.assertEqual("unknown", body.get("gone"))
        self.assertIn("would not read", body.get("say") or "", "an unreadable record read as 'no record names it'")

    def test_a_pruned_reel_with_no_deleted_time_says_when_is_unknown(self):
        self._write_tombs({"reels": [{"reel": "reel_s_1", "session": "s_1"}]})
        got = self._get("reel_s_1/f_1793000001000.jpg", {"Accept": "*/*"})
        body = got.get("body") or {}
        self.assertEqual("pruned", body.get("gone"))
        self.assertIsNone(body.get("deletedTs"), "a deletion time nobody recorded was filled in")
        self.assertIn("(when: UNKNOWN)", body.get("say") or "")

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

    def test_the_banner_check_does_not_ask_on_a_guest(self):
        look = self._body("async function look(){", "\n    look();")
        g = look.find("if (await window._isGuestSeat()){ bar.hidden = true; return; }")
        u = look.find("fetch(API + '/api/update')")
        self.assertGreater(g, 0, "the banner's check no longer asks whether this is a guest")
        self.assertGreater(u, g, "the banner asks /api/update before it asks whether this is a guest")

    def test_the_footer_check_does_not_ask_on_a_guest(self):
        f = self._body("window._fleetUpdateCheck = async function(){", "\n  };")
        g = f.find("if (await window._isGuestSeat()){")
        u = f.find("fetch(API + '/api/update')")
        self.assertGreater(g, 0, "the footer's check no longer asks whether this is a guest")
        self.assertGreater(u, g)
        self.assertIn("return;", f[g:u], "the footer's guest check does not stop it asking")

    def test_update_now_never_posts_a_pull_on_a_guest(self):
        go = self._body("go.onclick = async function(){", "\n    };")
        g = go.find("if (await window._isGuestSeat()){")
        u = go.find("fetch(API + '/api/update', { method: 'POST' })")
        self.assertGreater(g, 0, "UPDATE NOW no longer asks whether this is a guest")
        self.assertGreater(u, g)
        self.assertIn("return;", go[g:u])


RED_PROOF = [
    {"why": "REG-3207 - an <img> that leads its Accept with image/ is no longer told apart from a fetch()",
     "file": "tv/control_app.py",
     "find": "        return str(headers.get(\"Accept\") or \"\").strip().lower().startswith(\"image/\")\n",
     "replace": "        return False\n",
     "matches": 1},
    {"why": "REG-3207 - a missing frame is a bare 404 again, drawn as a broken picture",
     "file": "tv/control_app.py",
     "find": "            if _hist_wants_image(getattr(self, \"headers\", None)):\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-3207 - the retention record is never asked, so a pruned frame reads UNKNOWN",
     "file": "tv/control_app.py",
     "find": "    e = rows.get(reel)\n",
     "replace": "    e = None\n",
     "matches": 1},
    {"why": "REG-3207 - the placeholder drops WHEN the lane pruned the frame",
     "file": "tv/control_app.py",
     "find": "        out[\"when\"] = _hist_when(ts)\n",
     "replace": "        out[\"when\"] = None\n",
     "matches": 1},
    {"why": "REG-3207 - a frame no record names is drawn as PRUNED",
     "file": "tv/control_app.py",
     "find": "    head = \"FRAME PRUNED\" if gone.get(\"state\") == \"pruned\" else \"FRAME NOT ON THIS PC\"\n",
     "replace": "    head = \"FRAME PRUNED\"\n",
     "matches": 1},
    {"why": "REG-3207 - an unreadable retention record reads as one that names nothing",
     "file": "tv/control_app.py",
     "find": "    except (OSError, ValueError):\n        return None\n    rows = {}\n",
     "replace": "    except (OSError, ValueError):\n        return {}\n    rows = {}\n",
     "matches": 1},
    {"why": "REG-3207 - the banner asks /api/update on a guest, which has no such route",
     "file": "tv/control_ui.html",
     "find": "        if (await window._isGuestSeat()){ bar.hidden = true; return; }   // REG-3207 - a mirror has nothing to pull\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3207 - the guest answer reads a key the mirror never writes",
     "file": "tv/control_ui.html",
     "find": "    if (ls && typeof ls === 'object') return Promise.resolve(ls.guest === true);\n",
     "replace": "    if (ls && typeof ls === 'object') return Promise.resolve(ls.isGuest === true);\n",
     "matches": 1},
    {"why": "REG-3207 - UPDATE NOW posts a pull to a guest",
     "file": "tv/control_ui.html",
     "find": "      if (await window._isGuestSeat()){   // REG-3207 - the mirror has no checkout; never POST it a pull\n",
     "replace": "      if (false){\n",
     "matches": 1},
    {"why": "REG-3207 - the footer's check asks /api/update on a guest",
     "file": "tv/control_ui.html",
     "find": "      if (await window._isGuestSeat()){\n        toast('this is a guest seat",
     "replace": "      if (false){\n        toast('this is a guest seat",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
