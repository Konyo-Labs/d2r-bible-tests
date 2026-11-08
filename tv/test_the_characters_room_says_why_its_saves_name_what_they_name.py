# -*- coding: utf-8 -*-
"""#251 (REG-3079) - THE CHARACTERS ROOM SAYS WHY THIS PC'S SAVES NAME WHAT THEY NAME; A SHADOW SAYS THE OWNER'S.

His two PCs hold no .d2s (his characters are online), and tv/d2s_read.saves says so: d2sWhy = "no .d2s on this PC;
online characters live on Battle.net". A PC with no save folder, or a platform with no place to look, says why its
list is UNKNOWN. That reason is drawn under the room's in-game list - a hidden reason reads as nothing. In a shadow the
reason is the OWNER's: their console uploads its saves answer (control_app._profile_saves -> console_snapshot.API_FIELDS
"saves" -> the worker's API_NAMES), and the shadow frame answers /api/saves from that upload.
#104 (his 11-06: "through shadow mode for dean ... i cant see any characters being properly synced from his console") - the
upload now carries their save NAMES too, names only (console_snapshot.saves_of; the worker's savesOk refuses an id count),
because a PC with a builds book never sent them (its roster characters section is its builds - REG-2929's NOT DONE). The
shadow keeps them apart from this PC's (_cbSavesShadow) and draws them in its in-game list, class and level UNKNOWN.
The board half is driven on the whole page in node (tv/vault_page_node); the upload half in Python. RED_PROOF below.
"""
import io
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import console_snapshot as CS  # noqa: E402
import d2s_read as D  # noqa: E402
import vault_page_node as VPN  # noqa: E402

FOLDER = {"ok": True, "state": "folder", "folders": 1, "chars": [{"name": "Konyolock", "ids": 1}], "d2s": [],
          "d2sWhy": D.NO_D2S_SAY}
NO_FOLDER = {"ok": True, "state": "no-folder", "chars": None, "d2s": None, "folders": 0,
             "why": "no D2R save folder on this PC (looked in 2 places)"}
WITH_D2S = {"ok": True, "state": "folder", "folders": 1, "chars": [{"name": "Konyolock", "ids": 1}],
            "d2s": [{"file": "Konyolock.d2s", "ok": True}]}

BODY = r"""
var SAVES = %s;
function _syncThen(v){ return { then: function(f){ var r; try { r = f(v); } catch (e) { r = undefined; } return _syncThen(r); },
                                catch: function(){ return this; } }; }
window.fetch = function(url){ return _syncThen({ ok: true, json: function(){
  return String(url).indexOf('/api/saves') >= 0 ? SAVES : { ok: true, chars: [] }; } }); };
if (%s) document.documentElement.classList.add('tvd-shadow');
window.renderCharsTab();
var el = document.getElementById('chars-list'), html = el ? String(el.innerHTML || '') : '';
var m = /<div class="chx-sec-sub" data-sub="saves">([\s\S]*?)<\/div>/.exec(html);
OUT.line = m ? m[1] : null;
OUT.painted = html.length;
OUT.names = window._cbTemplates().map(function(t){ return t.name; });
"""


def _room(answer, shadow=False):
    return VPN.run(BODY % (json.dumps(answer), "true" if shadow else "false"), timeout=600)


def _read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


@unittest.skipIf(VPN.NODE is None, "node is absent - this law is UNMEASURED here, not passing")
class TheRoomSaysTheSavesReason(unittest.TestCase):

    def test_no_d2s_on_this_pc_is_said(self):
        o = _room(FOLDER)
        self.assertGreater(o["painted"], 0, "PREMISE: the room did not paint")
        self.assertEqual(o["line"], "<b>This PC’s saves:</b> " + D.NO_D2S_SAY)

    def test_why_the_list_is_unknown_is_said(self):
        self.assertEqual(_room(NO_FOLDER)["line"], "<b>This PC’s saves:</b> " + NO_FOLDER["why"])

    def test_a_pc_whose_saves_hold_a_d2s_says_nothing(self):
        self.assertIsNone(_room(WITH_D2S)["line"])

    def test_a_shadow_says_the_owners_reason_and_draws_their_names(self):
        o = _room(FOLDER, shadow=True)
        self.assertEqual(o["line"], "<b>Their PC’s saves:</b> " + D.NO_D2S_SAY,
                         "a shadow's room hid the owner's reason, or said it as this PC's")
        self.assertIn("Konyolock", o["names"], "#104 - a shadow's in-game list never draws the owner's save names")

    def test_a_shadow_draws_only_d2r_names_and_none_after_it_leaves(self):
        o = VPN.run(r"""
        var SAVES = { ok: true, state: 'folder', chars: [ { name: 'Crest' }, { name: 'Morph' }, { name: '<b>x</b>' } ] };
        function _syncThen(v){ return { then: function(f){ var r; try { r = f(v); } catch (e) { r = undefined; } return _syncThen(r); },
                                        catch: function(){ return this; } }; }
        document.documentElement.classList.add('tvd-shadow');
        window._cbSavesTakeForLaw(SAVES);
        OUT.shadow = window._cbTemplates().map(function(t){ return t.name; });
        document.documentElement.classList.remove('tvd-shadow');
        OUT.home = window._cbTemplates().map(function(t){ return t.name; });
        """, timeout=600)
        self.assertEqual(o["shadow"], ["Crest", "Morph"], "the owner's names did not draw, or a non-D2R name drew")
        self.assertEqual(o["home"], [], "the owner's save names stayed on this page after the shadow ended")


class TheOwnersReasonRidesTheUpload(unittest.TestCase):

    def test_the_snapshot_keeps_the_reason_and_the_names_only(self):
        raw = dict(FOLDER, chars=[{"name": "Konyolock", "ids": 1}, {"name": "Crest", "ids": 3}, {"name": "x1"},
                                  {"name": "Konyolock", "ids": 1}])
        name, text = CS.api_store("saves", raw)
        self.assertEqual(name, "d2r_api_saves")
        self.assertEqual(json.loads(text), {"ok": True, "state": "folder", "d2sWhy": D.NO_D2S_SAY,
                                            "chars": [{"name": "Konyolock"}, {"name": "Crest"}]},
                         "the saves answer did not ride, or carried an id count, a folder count or a non-D2R name")
        name, text = CS.api_store("saves", dict(NO_FOLDER))
        self.assertIsNone(json.loads(text)["chars"], "a list that would not read became a list")

    def test_the_worker_refuses_anything_but_names(self):
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node is absent - the worker's check is UNMEASURED here, not passing")
        prog = ("import('" + os.path.join(ROOT, "functions", "api", "roster.js").replace("\\", "/") + "').then(m => {"
                "const f = (o) => m.apiOk('saves', JSON.stringify(o));"
                "process.stdout.write(JSON.stringify([f({ok: true, chars: [{name: 'Crest'}]}), f({ok: true, chars: [{name: 'Crest', ids: 2}]}),"
                " f({ok: true, chars: [{name: '../x'}]}), f({ok: false, chars: null, why: 'w'}), f({ok: true, folders: 1})]));});")
        r = subprocess.run([node, "--input-type=module", "-"], input=prog, capture_output=True, text=True, timeout=60)   # #242 - stdin
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        self.assertEqual(json.loads(r.stdout), [True, False, False, True, False],
                         "the worker took an id count, a non-D2R name or a field the console never sends")

    def test_the_worker_takes_what_the_console_sends(self):
        js = _read("functions/api/roster.js")
        names = re.findall(r'"([^"]+)"', re.search(r"export const API_NAMES = \[([^\]]*)\]", js).group(1))
        self.assertIn("saves", names, "the worker refuses a profile that carries d2r_api_saves")
        fields = re.findall(r'"([^"]+)"', re.search(r"\n  saves: \[([^\]]*)\]", js).group(1))
        self.assertEqual(fields, list(CS.API_FIELDS["saves"]), "the worker's saves fields drifted from the console's")

    def test_the_console_uploads_it_and_the_shadow_frame_answers_it(self):
        src = _read("tv/control_app.py")
        self.assertTrue(re.search(r'\("main_locks", main_locks_view\),(?:\s+\("pictures", _profile_pictures\),)?\s+\("saves", _profile_saves\)\)\):', src),
                        "the profile upload does not read this PC's saves answer")
        self.assertIn("def _profile_saves():\n", src)
        page = _read("bible.html")
        self.assertIn("var hit = /^\\/api\\/(chars_learned|main_locks|saves)$/.exec(path);", page,
                      "the shadow frame does not answer /api/saves from the owner's upload")

    def test_a_platform_with_no_place_to_look_is_a_completed_look(self):
        got = D.saves(platform="linux")
        self.assertIs(got["ok"], True, "a platform with no save place read as a failed look - every upload a miss")
        self.assertIsNone(got["chars"])


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "#104 - a shadow's in-game list never draws the owner's save names again",
     "file": "bible.html",
     "find": "      return o.filter(function(r){ return r && typeof r.name === 'string' && /^[A-Za-z][A-Za-z_-]{1,14}$/.test(r.name); });\n",
     "replace": "      return [];\n",
     "matches": 1, "needs": "node"},
    {"why": "#104 - the owner's saves land in this PC's slot, so their names stay on the page after the shadow",
     "file": "bible.html",
     "find": "      if (d.ok === true || !(_cbSavesShadow && _cbSavesShadow.ok === true)) _cbSavesShadow = d;\n      return;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#104 - the upload carries the id counts beside the names",
     "file": "tv/console_snapshot.py",
     "find": "        out[\"chars\"] = [{\"name\": n} for n in names]\n",
     "replace": "        out[\"chars\"] = ch\n",
     "matches": 1},
    {"why": "#104 - the worker takes any saves row, id counts and all",
     "file": "functions/api/roster.js",
     "find": "  if (name === \"saves\") return savesOk(text);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-3079) - the room never draws the saves' reason",
     "file": "bible.html",
     "find": "'<div class=\"chx-sec-list\">' + cards + _savesSayHtml() + _surfaceWitnessHtml()",
     "replace": "'<div class=\"chx-sec-list\">' + cards + _surfaceWitnessHtml()",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-3079) - only the .d2s line is said; a list UNKNOWN for want of a save folder says nothing",
     "file": "bible.html",
     "find": "    if (!Array.isArray(S.chars) && typeof S.why === 'string' && S.why) return S.why;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-3079) - a shadow never asks, so the owner's reason is hidden",
     "file": "bible.html",
     "find": "    if (document.documentElement.classList.contains('tvd-shadow')) return _cbLearnedQuiet(then);\n",   # v3864 - a shadow asks through v3856's quiet read, which asks the saves too
     "replace": "    if (document.documentElement.classList.contains('tvd-shadow')) return;\n",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-3079) - a shadow says the owner's reason as this PC's",
     "file": "bible.html",
     "find": "(shadow ? 'Their PC\\u2019s saves' : 'This PC\\u2019s saves')",
     "replace": "'This PC\\u2019s saves'",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-3079) - the snapshot keeps no saves answer, so the owner's reason never leaves their PC",
     "file": "tv/console_snapshot.py",
     "find": "    \"saves\": (\"ok\", \"state\", \"d2sWhy\", \"why\", \"chars\"),\n",
     "replace": "",
     "matches": 1},
    {"why": "#251 (REG-3079) - the worker refuses a profile that carries d2r_api_saves",
     "file": "functions/api/roster.js",
     "find": "export const API_NAMES = [\"chars_learned\", \"main_locks\", \"world\", \"pictures\", \"saves\", \"d2jsp_login\"];",
     "replace": "export const API_NAMES = [\"chars_learned\", \"main_locks\", \"world\", \"pictures\", \"d2jsp_login\"];",
     "matches": 1},
    {"why": "#251 (REG-3079) - the profile upload never reads this PC's saves answer",
     "file": "tv/control_app.py",
     "find": "                                 (\"saves\", _profile_saves), (\"d2jsp_login\", _profile_d2jsp_login))):\n",
     "replace": "                                 (\"d2jsp_login\", _profile_d2jsp_login))):\n",
     "matches": 1},
    {"why": "#251 (REG-3079) - the shadow frame does not answer /api/saves from the owner's upload",
     "file": "bible.html",
     "find": "var hit = /^\\/api\\/(chars_learned|main_locks|saves)$/.exec(path);",
     "replace": "var hit = /^\\/api\\/(chars_learned|main_locks)$/.exec(path);",
     "matches": 1},
]
