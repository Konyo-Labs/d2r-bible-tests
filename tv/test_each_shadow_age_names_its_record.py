# -*- coding: utf-8 -*-
"""#218 (REG-3034, GrokBot v3836 glass pass, #230 6485132266) - EACH AGE IN A SHADOW NAMES THE RECORD IT DATES.

At 03:13 the Mac's shadow of the ALT said "last upload 44 min ago · snapshot Oct 29 02:28" on its bar, and "uploaded 12 min
ago" atop 📚 Their sessions in the same view. Measured on the site at 03:49: the ALT's board snapshot (the profile record)
t 03:43:39, exactly 02:28 + the console's 75 min profile gap (console_snapshot.MIN_GAP_MS, REG-2684, which holds a boot
post too); its sessions digest t 03:00:36; its roster row t 03:00:34. So the 03:00 restart published a row and a digest
and no board - the shadow loaded the newest board there was, and nothing older over anything newer. Both ages were true;
each read as "the owner's last upload". Now the bar says "board uploaded N ago" (console_snapshot.view) and the list
says "sessions uploaded N ago" (control_ui _shadowSessionsHtml), so the two ages never read as one.

Driven: console_snapshot.view and shadow_sessions.view in Python; the list's header and its helpers cut out of
control_ui.html and run in node over the real shadow_sessions.view answer. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
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
import console_snapshot as CS  # noqa: E402
import shadow_sessions as SS  # noqa: E402

NODE = shutil.which("node")
UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
OWNER = "Konyo · ALT"
NOW = 1793236380000                                   # the 03:13 look
BOARD_T = NOW - (44 * 60 + 30) * 1000                 # the board snapshot, held by the 75 min gap
SESS_T = NOW - (12 * 60 + 30) * 1000                  # the sessions digest posted at the 03:00 restart
FNS = ["  function esc(s){", "  function _lsWhenSay(t0){", "  function _runSpanSay(t0, t1){",
       "  function _shadowSessionRow(s, ix){", "  function _shadowSessionsHead(owner){", "  function _shadowSessionsHtml(d){"]
LINES = ["  var _SSV_B64 = "]


def _cut(sig):
    if UI.count(sig) != 1:
        raise AssertionError("%r occurs %d times - this law cannot see its subject" % (sig, UI.count(sig)))
    i = UI.index(sig)
    depth = 0
    for j in range(UI.index("{", i), len(UI)):
        if UI[j] == "{":
            depth += 1
        elif UI[j] == "}":
            depth -= 1
            if depth == 0:
                return UI[i:j + 1]
    raise AssertionError("%r never closed - harness fault, not a pass" % sig)


def _line(start):
    if UI.count(start) != 1:
        raise AssertionError("%r occurs %d times - this law cannot see its subject" % (start, UI.count(start)))
    i = UI.index(start)
    return UI[i:UI.index("\n", i)]


def _board():
    stores = {"d2r_api_world": json.dumps({"machine": "windows"}), "d2r_owned": json.dumps(["Shako"])}
    return {"owner": OWNER, "t": BOARD_T, "hash": CS.digest(stores), "stores": stores}


def _sessions_view(t=SESS_T):
    rec = {"owner": OWNER, "published": True, "t": t,
           "digest": {"sessions": [{"sessionId": "s_1", "t0": SESS_T - 3600000, "t1": SESS_T - 60000, "reads": 2,
                                    "names": [], "namesMore": 0, "frames": [], "why": "w"}]}}
    return SS.view(OWNER, rec, NOW)


def _html(views):
    if not NODE:
        raise AssertionError("node is not on this machine - this law does not skip")
    code = "\n".join([_line(x) for x in LINES] + [_cut(f) for f in FNS])
    d = tempfile.mkdtemp(prefix="shadow_ages_")
    try:
        h = os.path.join(d, "h.mjs")
        with io.open(h, "w", encoding="utf-8") as fh:
            fh.write("import { readFileSync } from 'node:fs';\n"
                     "const C = JSON.parse(readFileSync(process.argv[2], 'utf8'));\n"
                     "const f = new Function(C.code + '\\nreturn _shadowSessionsHtml;')();\n"
                     "console.log(JSON.stringify(C.views.map(function (v) { return f(v); })));\n")
        c = os.path.join(d, "c.json")
        with io.open(c, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"code": code, "views": views}))
        r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=60, env=dict(os.environ, TZ="UTC", LANG="en_US.UTF-8"))
    finally:
        shutil.rmtree(d, True)
    if r.returncode != 0:
        raise AssertionError("node failed: %s" % r.stderr[-900:])
    return json.loads(r.stdout)


class TheBarDatesTheBoard(unittest.TestCase):

    def test_every_state_names_the_board(self):
        for online, lead in ((True, "online now"), (False, "offline"), (None, "online UNKNOWN")):
            w = CS.view(OWNER, _board(), NOW, online=online)["words"]
            self.assertEqual(w, "%s · %s · board uploaded 44 min ago" % (OWNER, lead), w)
            self.assertNotIn("last upload", w, "the bar's age does not say what it dates")

    def test_this_pcs_copy_still_names_the_board(self):
        w = CS.view(OWNER, _board(), NOW, online=False, source="cache")["words"]
        self.assertTrue(w.startswith(OWNER + " · offline · board uploaded 44 min ago · the site could not be read"), w)


class TheListDatesItsSessions(unittest.TestCase):

    def test_the_list_names_its_sessions_and_an_unknown_age_stays_named(self):
        v = _sessions_view()
        noage = dict(v, ago=None)
        html, unk = _html([v, noage])
        self.assertIn("sessions uploaded 12 min ago", html)
        self.assertIn("sessions upload age UNKNOWN", unk)

    def test_the_0313_view_says_two_named_ages_never_one_contradiction(self):
        bar = CS.view(OWNER, _board(), NOW, online=True)["words"]
        html = _html([_sessions_view()])[0]
        self.assertIn("board uploaded 44 min ago", bar)
        self.assertIn("sessions uploaded 12 min ago", html)
        for said in (bar, html):
            self.assertNotRegex(said, r"(?<!board )(?<!sessions )\buploaded \d+ min ago",
                                "an age in the shadow does not name its record: %r" % said[:200])


RED_PROOF = [
    {"why": "REG-3034 - the bar says 'last upload' while the console is online",
     "file": "tv/console_snapshot.py",
     "find": "        state, words = \"live\", \"%s · online now · board uploaded %s\" % (owner, ago)\n",
     "replace": "        state, words = \"live\", \"%s · online now · last upload %s\" % (owner, ago)\n",
     "matches": 1},
    {"why": "REG-3034 - the bar says 'last upload' while the console is offline",
     "file": "tv/console_snapshot.py",
     "find": "        state, words = \"offline\", \"%s · offline · board uploaded %s\" % (owner, ago)\n",
     "replace": "        state, words = \"offline\", \"%s · offline · last upload %s\" % (owner, ago)\n",
     "matches": 1},
    {"why": "REG-3034 - the bar says 'last upload' when the fleet was not read",
     "file": "tv/console_snapshot.py",
     "find": "        state, words = \"unknown\", \"%s · online UNKNOWN · board uploaded %s\" % (owner, ago)\n",
     "replace": "        state, words = \"unknown\", \"%s · online UNKNOWN · last upload %s\" % (owner, ago)\n",
     "matches": 1},
    {"why": "REG-3034 - the sessions list's age does not name its sessions",
     "file": "tv/control_ui.html",
     "find": "? 'sessions uploaded ' + d.ago : ",
     "replace": "? 'uploaded ' + d.ago : ",
     "matches": 1},
    {"why": "REG-3034 - the sessions list's unknown age does not name its sessions",
     "file": "tv/control_ui.html",
     "find": ": 'sessions upload age UNKNOWN')",
     "replace": ": 'upload age UNKNOWN')",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
