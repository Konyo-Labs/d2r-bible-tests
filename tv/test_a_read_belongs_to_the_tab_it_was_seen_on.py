# -*- coding: utf-8 -*-
"""REG-3248 (#67, his call 2026-11-06 07:10 Israel) - A READ BELONGS TO THE TAB IT WAS SEEN ON.

MEASURED on his Mac (/api/vault_ledger, read-only): 11 stash cells were claimed by two or three owned names -
stash:c6r3 Blood Finger and Doom Grip, stash:c9r6 Hellfire Torch and an amulet, two of them inside ONE session. A
witness recorded session, frame, point and cell but NOT which stash tab the cell was on, and the sweep's surface never
names one (OWNERSHIP_SURFACES says "stash", not personal / shared). So the board's full look laid a session's personal
reads and its shared-page reads on ONE container: a missing key dimension read as a collision.

  1. The vault reader is asked the selected TAB and a shared tab's PAGE, off the tab row (VAULT_READ_PROMPT). A reel that
     FOUND items under an older reader is re-read once (his call: paid); a reel that found nothing keeps its seal.
  2. claude_vault_read passes them through; vault_retro.read_tab is their one parser (personal -> "stash", shared + its
     1-based page -> "shared" + the board's 0-based page; anything not said plainly is None).
  3. The sweep's sighting and the banked witness carry tab and page; the container look takes the READ's tab and page.
  4. The board's full look counts a read only on its own tab (and a shared read only on its page). A read from before
     the tab was asked counts on this look's own frame, or when its session showed only this container - else it is
     ambiguous and left out, and the look asks about the cells instead of inventing a collision.
Fixture frames in a temp dir only; the model call is stubbed. RED_PROOF below. [[unknown-stays-unknown]]
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
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()

import tv_diablo as TD  # noqa: E402
import vault_retro as VR  # noqa: E402

ROOT = os.path.dirname(HERE)
NODE = shutil.which("node")


class TheReaderIsAskedTheTab(unittest.TestCase):

    def test_the_prompt_asks_the_tab_and_the_shared_page(self):
        p = TD.VAULT_READ_PROMPT
        self.assertIn('"tab":"personal|shared|runes|gems|materials|null"', p, "the template does not ask the tab")
        self.assertIn('"page":<int or null>', p, "the template does not ask a shared tab's page")
        self.assertIn("counting from the left (1 = the first shared tab)", p, "the page's numbering is not stated")

    def test_the_version_moved_and_asks_the_tab(self):
        self.assertNotEqual(TD.VAULT_PROMPT_VER, "vp-reg2915", "the prompt changed and its version did not")
        self.assertIn(TD.VAULT_PROMPT_VER, TD.VAULT_TAB_ASKED_BY, "the current reader is not marked as asking the tab")
        self.assertNotIn("vp-reg2915", TD.VAULT_TAB_ASKED_BY, "an old reader is counted as having asked the tab")

    def test_the_read_passes_the_tab_through(self):
        from PIL import Image
        d = tempfile.mkdtemp(prefix="tabread-")
        self.addCleanup(shutil.rmtree, d, True)
        f = os.path.join(d, "f_1790000000000.jpg")
        Image.new("RGB", (64, 48), (10, 10, 10)).save(f)
        reply = {"surface": "stash", "tab": "shared", "page": 2, "items": [], "conf": 0.9}
        with mock.patch.object(TD, "_oneshot", lambda *a, **k: json.dumps(reply)), \
                mock.patch.object(TD, "_is_throttled", lambda *a, **k: False), \
                mock.patch.object(TD, "_sub_budget_check", lambda *a, **k: None), \
                mock.patch.object(TD, "_reader_choice", lambda *a, **k: "claude"):
            r = TD.claude_vault_read(f, "stash")
        self.assertEqual((r.get("tab"), r.get("page")), ("shared", 2), "the read's tab never left the reader: %r" % r)


class OnlyReelsThatFoundItemsAreReRead(unittest.TestCase):
    """His call was the re-read; the cost is his subscription. MEASURED 11-06: 99 seals, 66 took nothing - the tab cannot turn
    "nothing here" into items, so those stand; a reel that FOUND items under a reader that never asked the tab reopens once."""

    def setUp(self):
        import control_app as CA
        self.CA = CA
        self.cur = TD.VAULT_PROMPT_VER

    def test_a_reel_that_found_items_reopens_once(self):
        self.assertFalse(self.CA._vault_still_sealed({"rows": 3, "promptVer": "vp-reg2915"}, self.cur),
                         "a reel with items, read before the tab was asked, is not re-read - its witnesses never gain a tab")
        self.assertTrue(self.CA._vault_still_sealed({"rows": 3, "promptVer": self.cur}, self.cur),
                        "a reel re-read by the tab-asking reader reopened again - the re-read would never end")

    def test_a_barren_reel_keeps_its_seal(self):
        for v in ("vp-reg2915", "vp3554", "vp3368"):
            self.assertTrue(self.CA._vault_still_sealed({"rows": 0, "promptVer": v}, self.cur),
                            "a reel that found nothing under %s reopens for the tab question - paid reads for no item" % v)

    def test_a_record_that_will_not_read_stays_sealed(self):
        self.assertTrue(self.CA._vault_still_sealed(None, self.cur))
        self.assertTrue(self.CA._vault_still_sealed({"rows": 2, "promptVer": "vp-reg2915"}, "vpSOMEOTHER"),
                        "a caller asking about another reader reopened a reel")


class OneParser(unittest.TestCase):

    def test_the_tab_in_the_boards_words(self):
        cases = [("personal", None, ("stash", None)), ("Shared", 2, ("shared", 1)), ("shared", "3", ("shared", 2)),
                 ("SHARED", " 4 ", ("shared", 3)), ("shared", True, ("shared", None)), ("shared", 0, ("shared", None)),
                 ("shared", 12, ("shared", None)), ("shared", "2.5", ("shared", None)), ("runes", 1, (None, None)),
                 (None, None, (None, None)), ("personal", 3, ("stash", None))]
        for tab, page, want in cases:
            self.assertEqual(VR.read_tab(tab, page), want, "read_tab(%r, %r)" % (tab, page))


class TheSweepCarriesIt(unittest.TestCase):

    def test_the_container_look_takes_the_reads_tab(self):
        f = "/x/reel_s_1/f_1790000000000.jpg"
        lk = VR.container_look(f, "stash", None, "stash", tab="shared", page=3)
        self.assertEqual((lk["location"], lk["page"]), ("shared", 2))
        lk = VR.container_look(f, "stash", None, "stash", tab="personal")
        self.assertEqual((lk["location"], lk["page"]), ("stash", None))
        self.assertIsNone(VR.container_look(f, "stash", None, "stash")["location"], "no tab said is UNKNOWN")

    def test_the_sighting_and_the_witness_carry_the_tab(self):
        with io.open(os.path.join(HERE, "vault_retro.py"), encoding="utf-8") as fh:
            src = fh.read()
        code = "\n".join(ln.split("#", 1)[0] for ln in src.split("\n"))
        self.assertEqual(code.count('_rtab = read_tab(resp.get("tab"), resp.get("page"))'), 1,
                         "the sweep no longer reads the tab off the read")
        self.assertEqual(code.count('"tab": _rtab[0] if item["lane"] == "stash" else None,'), 1,
                         "the sighting does not carry the tab")
        rows = VR._witness_rows([{"session": "s_1", "frame": "f_1.jpg", "lane": "stash", "conf": 0.9,
                                  "cell": "stash:c6r3", "tab": "shared", "page": 1}])
        self.assertEqual((rows[0].get("tab"), rows[0].get("page")), ("shared", 1), "the witness dropped the tab: %r" % rows)


SCENARIO = r"""
var out = {};
window.MULE_GRID = { stash: [10, 10], shared: [10, 10], inventory: [10, 4] };
var w = function(name, frame, cell, tab, page){ var o = { session: 's_1', frame: frame, cell: cell, conf: 0.9 };
  if (tab) o.tab = tab; if (page != null) o.page = page; return { name: name, witnesses: [o] }; };
var rows = [ w('Blood Finger', 'f_1.jpg', 'stash:c6r3', 'stash'), w('Doom Grip', 'f_2.jpg', 'stash:c6r3', 'shared', 0),
             w('Old Personal', 'f_1.jpg', 'stash:c1r1'), w('Old Elsewhere', 'f_9.jpg', 'stash:c2r2'),
             w('Shared Page 2', 'f_3.jpg', 'stash:c4r4', 'shared', 1) ];
var names = function(look){ return _flReadsOf(look, rows).map(function(r){ return r.name; }).sort(); };
out.personal = names({ session: 's_1', frame: 'f_1.jpg', location: 'stash', sessionLocations: ['stash', 'shared', 'shared'] });
out.shared0 = names({ session: 's_1', frame: 'f_2.jpg', location: 'shared', page: 0, sessionLocations: ['stash', 'shared', 'shared'] });
out.onlyOne = names({ session: 's_1', frame: 'f_1.jpg', location: 'stash', sessionLocations: ['stash'] });
var seen = [];
_flOne = function(lk){ seen.push(lk.sessionLocations); return {}; };
window._vaultIntakeGate = function(){ return null; };
window._vaultFullLooksApply({ containers: [ { session: 's_1', location: 'stash', frame: 'f_1.jpg' },
                                            { session: 's_1', location: 'shared', page: 0, frame: 'f_2.jpg' },
                                            { session: 's_1', location: 'shared', page: 1, frame: 'f_3.jpg' },
                                            { session: 's_2', location: 'stash', frame: 'f_5.jpg' } ], items: [] });
out.sessionLocations = seen;
process.stdout.write(JSON.stringify(out));
"""


def _cut(src, start, end, inclusive=False):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i:j + (len(end) if inclusive else 0)]


@unittest.skipUnless(NODE, "node is required to drive the board's full look")
class TheBoardCountsAReadOnItsOwnTab(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            src = fh.read()
        reads = _cut(src, "  function _flReadsOf(look, rows){", "  window._vaultFullLookReads = _flReadsOf;")
        apply_ = _cut(src, "  window._vaultFullLooksApply = function(payload){", "\n  };\n", inclusive=True)
        prog = "var window = {};\nvar _flOne;\n" + reads + "\n" + apply_ + "\n" + SCENARIO
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2000:])
        cls.o = json.loads(r.stdout.strip().splitlines()[-1])

    def test_a_named_read_counts_only_on_its_tab_and_page(self):
        self.assertNotIn("Doom Grip", self.o["personal"], "a shared-page read was laid on the personal stash (c6r3)")
        self.assertIn("Blood Finger", self.o["personal"])
        self.assertEqual(self.o["shared0"], ["Doom Grip"], "shared page 1's look took another tab's or page's reads")

    def test_an_old_read_is_certain_only_on_its_frame_or_a_one_container_session(self):
        self.assertIn("Old Personal", self.o["personal"], "an old read on the look's own frame is that tab")
        self.assertNotIn("Old Elsewhere", self.o["personal"],
                         "an old read from another frame of a two-container session was guessed onto this one")
        self.assertIn("Old Elsewhere", self.o["onlyOne"], "a one-container session's old reads stopped counting")

    def test_each_look_carries_its_sessions_containers(self):
        sl = self.o["sessionLocations"]
        self.assertEqual(len(sl), 4)
        self.assertEqual(sorted(sl[0]), ["shared", "shared", "stash"], "two shared pages are two containers")
        self.assertEqual(sl[3], ["stash"])


RED_PROOF = [
    {"why": "REG-3248 - a reel that found items is never re-read, so its witnesses never gain their tab", "file": "tv/control_app.py",
     "find": "        return not _vault_tab_owed(rec, prompt_ver)   # REG-3248 (#67) - found items, never asked their tab: re-read ONCE\n",
     "replace": "        return True\n",
     "matches": 1},
    {"why": "REG-3248 - every barren reel reopens for the tab question (paid reads for no item)", "file": "tv/tv_diablo.py",
     "find": "VAULT_PROMPT_ANSWERS_SAME_AS = (\"vp3554\", \"vp3368\", \"vp-reg2915\")\n",
     "replace": "VAULT_PROMPT_ANSWERS_SAME_AS = (\"vp3554\", \"vp3368\")\n",
     "matches": 1},
    {"why": "REG-3248 - the prompt stops asking the tab", "file": "tv/tv_diablo.py",
     "find": "    '{{\"surface\":\"{surface}\",\"tab\":\"personal|shared|runes|gems|materials|null\",\"page\":<int or null>,\"items\":[],\"conf\":0.0}}\\n'\n",
     "replace": "    '{{\"surface\":\"{surface}\",\"items\":[],\"conf\":0.0}}\\n'\n",
     "matches": 1},
    {"why": "REG-3248 - the reader drops the tab it was told", "file": "tv/tv_diablo.py",
     "find": "    for _tk in (\"tab\", \"page\"):\n",
     "replace": "    for _tk in ():\n",
     "matches": 1},
    {"why": "REG-3248 - the witness drops the tab", "file": "tv/vault_retro.py",
     "find": "\"cellWhy\", \"holder\", \"tab\", \"page\"):",
     "replace": "\"cellWhy\", \"holder\"):",
     "matches": 1},
    {"why": "REG-3248 - a shared page's number is read off by one (the board counts from 0)", "file": "tv/vault_retro.py",
     "find": "                pg = n - 1\n",
     "replace": "                pg = n\n",
     "matches": 1},
    {"why": "REG-3248 - the board lays every tab's reads on one container again", "file": "bible.html",
     "find": "            if (_wt !== loc) return;\n",
     "replace": "            if (false) return;\n",
     "matches": 1},
    {"why": "REG-3248 - an old read from another frame of a two-container session is guessed onto this one", "file": "bible.html",
     "find": "            if (!_sl || _sl.length !== 1 || _sl[0] !== loc) return;\n",
     "replace": "            if (false) return;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
