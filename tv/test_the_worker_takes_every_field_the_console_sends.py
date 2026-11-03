# -*- coding: utf-8 -*-
"""REG-3080 - THE ROSTER WORKER TAKES EVERY FIELD THE CONSOLE SENDS IN ITS ANSWERS.

REG-2907 (#36, v3837) added `sessions` and `sessionsWhy` to the characters answer on the console side
(tv/console_snapshot.API_FIELDS) but not on the worker's (functions/api/roster.js API_FIELDS), and the worker's apiOk refuses
any field outside its list - and then refuses the WHOLE profile. Measured live on 2026-10-29: the Mac console on v3838 read
"roster would not take this profile: d2r_api_chars_learned is not the console answer it names", so every profile upload
carrying a characters answer was refused and every shadow froze on its last profile. Found by agent-guide while building
REG-3079. The old law (test_shadow_mode_reads_their_console) held only the API NAMES equal, never each name's fields.

This law holds each name's FIELD list equal on both sides, and runs the worker's own storesOk in node on the store the
console's own api_store builds from a full answer - the round trip, not two lists read side by side. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import console_snapshot as CS  # noqa: E402

WORKER = os.path.join(ROOT, "functions", "api", "roster.js")
NODE = shutil.which("node")


def _worker_fields():
    s = io.open(WORKER, encoding="utf-8").read()
    i = s.index("export const API_FIELDS = {")
    body = s[i:s.index("\n};", i)]
    body = re.sub(r"//[^\n]*", "", body)
    out = {}
    for m in re.finditer(r"(\w+):\s*\[([^\]]*)\]", body, re.S):
        out[m.group(1)] = sorted(re.findall(r'"([^"]+)"', m.group(2)))
    return out


class TheWorkerTakesEveryFieldTheConsoleSends(unittest.TestCase):

    def test_each_answer_names_the_same_fields_on_both_sides(self):
        w = _worker_fields()
        self.assertTrue(w, "PREMISE: the worker's API_FIELDS did not read")
        for name, fields in CS.API_FIELDS.items():
            self.assertIn(name, w, "the worker has no field list for the console answer %r" % name)
            self.assertEqual(sorted(fields), w[name], "the console sends %r fields the worker does not list (or the reverse): "
                             "console %r, worker %r" % (name, sorted(fields), w[name]))

    @unittest.skipUnless(NODE, "node is absent - the worker's own check is UNMEASURED here, never a pass")
    def test_the_worker_takes_the_store_the_console_builds(self):
        answer = {f: ("x" if f.endswith("Why") else 1) for f in CS.API_FIELDS["chars_learned"]}
        answer["ok"] = True
        store = CS.api_store("chars_learned", answer)
        self.assertTrue(store, "PREMISE: the console built no characters store from a full answer: %r" % (store,))
        name, text = store   # api_store -> (store name, JSON text)
        self.assertEqual(name, CS.API_PREFIX + "chars_learned", "PREMISE: the console named its store %r" % name)
        js = ("import { apiOk } from %s;\nconsole.log(JSON.stringify([apiOk('chars_learned', %s), "
              "apiOk('chars_learned', JSON.stringify({ok: true, notAField: 1}))]));\n" % (json.dumps("file://" + WORKER), json.dumps(text)))
        r = subprocess.run([NODE, "--input-type=module", "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        took, stranger = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertFalse(stranger, "PREMISE: the worker takes a field nobody sends, so this check measures nothing")
        self.assertTrue(took, "the worker refuses the characters store the console builds from a full answer")


RED_PROOF = [
    {"why": "REG-3080 - the console sends a new characters field the worker's list never got (the REG-2907 drift, console side)",
     "file": "console_snapshot.py",
     "find": "    \"chars_learned\": (\"ok\", \"chars\",",
     "replace": "    \"chars_learned\": (\"aNewFieldOnlyTheConsoleKnows\", \"ok\", \"chars\",",
     "matches": 1},
    {"why": "REG-3080 - the worker's characters list drops sessions/sessionsWhy again, so every profile is refused whole",
     "file": "functions/api/roster.js",
     "find": '"lobbyBySize",\n                  "sessions", "sessionsWhy", "identity"],',
     "replace": '"lobbyBySize", "identity"],',
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
