# -*- coding: utf-8 -*-
"""#23 (REG-3123) - THE SHADOW'S VAULT TAB SHOWS THE VAULT'S OWN AGE BESIDE THE BOARD UPLOAD'S.

Two records. console_snapshot.view dates the board upload (ago). roster_publish.vault_line dates
the vault section (sections.vault.asOf) and the route already puts those words on the row.
_shadowFillFromRoster had the row and dropped the line. The Vault tab never said either clock.

The console copies the words. It does not age them. The shadow boot copies them onto
_vaultShadowClockState. The Vault tab paints that state. His own board has no state, so it paints
nothing. A clock that was not handed is UNKNOWN, never the other clock and never this fetch.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable; enable()

NODE = shutil.which("node")
BIBLE = os.path.join(ROOT, "bible.html")
UI = os.path.join(HERE, "control_ui.html")

FNS = [
    "  window._shadowVaultClock = function (d) {",
    "    window._shadowVaultTake = function (snap) {",
    "  window._vaultShadowClocks = function () {",
    "  window._vaultShadowClocksPaint = function () {",
]


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def _cut(src, sig):
    if src.count(sig) != 1:
        raise AssertionError("%r occurs %d times" % (sig, src.count(sig)))
    i = src.index(sig)
    depth = 0
    started = False
    for j in range(src.index("{", i), len(src)):
        if src[j] == "{":
            depth += 1
            started = True
        elif src[j] == "}":
            depth -= 1
            if started and depth == 0:
                return src[i:j + 1] + ";"
    raise AssertionError("%r never closed" % sig)


def _run(scenes):
    if NODE is None:
        raise AssertionError("node is absent — the vault clocks were not driven")
    ui = _read(UI)
    bible = _read(BIBLE)
    code = "\n".join([
        _cut(ui, FNS[0]),
        _cut(bible, FNS[1]),
        _cut(bible, FNS[2]),
        _cut(bible, FNS[3]),
    ])
    prog = r"""
const C = JSON.parse(require('fs').readFileSync(process.argv[1], 'utf8'));
const out = {};
const window = globalThis;
%s
for (const sc of C.scenes) {
  const clock = window._shadowVaultClock(sc.handed);
  const taken = window._shadowVaultTake({ vaultLine: clock.vaultLine, boardAgo: clock.boardAgo, t: sc.now });
  window._vaultShadowClockState = sc.arm ? { vaultLine: taken.vaultLine, boardAgo: taken.boardAgo } : null;
  const el = { hidden: true, textContent: '' };
  window.document = { getElementById: (id) => id === 'vault-shadow-clocks' ? el : null };
  window._vaultShadowClocksPaint();
  out[sc.name] = { line: window._vaultShadowClocks(), hidden: el.hidden, text: el.textContent,
                   vault: clock.vaultLine, ago: clock.boardAgo };
}
process.stdout.write(JSON.stringify(out));
""" % code
    path = "/tmp/reg3123_scenes.json"
    try:
        with io.open(path, "w", encoding="utf-8") as fh:
            json.dump({"scenes": scenes}, fh)
        r = subprocess.run([NODE, "-e", prog, path], capture_output=True, text=True, timeout=30)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    if r.returncode != 0:
        raise AssertionError("the vault clocks would not run — UNKNOWN, not passing: %s"
                             % (r.stderr or r.stdout)[-800:])
    return json.loads(r.stdout)


class TheShadowVaultTabDatesTheVaultByItsOwnClock(unittest.TestCase):
    def test_the_fill_the_boot_and_the_tab_are_joined(self):
        ui = _read(UI)
        bible = _read(BIBLE)
        self.assertEqual(ui.count("vaultLine: (row && row.vaultLine) || null"), 1)
        self.assertEqual(ui.count("handed.vaultLine = clock.vaultLine"), 1)
        self.assertEqual(bible.count("window._shadowVaultTake(snap)"), 1)
        self.assertEqual(bible.count("window._vaultShadowClockState = { vaultLine: _takenVault.vaultLine, boardAgo: _takenVault.boardAgo }"), 1)
        self.assertEqual(bible.count("window._vaultShadowClocksPaint()"), 2)
        self.assertEqual(bible.count('id="vault-shadow-clocks" hidden'), 1)
        for sig in FNS:
            body = _cut(ui if sig in FNS[0] else bible, sig)
            self.assertNotIn("Date.now", body, sig)

    def test_the_two_clocks_stay_two_clocks(self):
        line = {"cls": "roster-stale", "state": "stale", "words": "vault 5 items · as of 3 hr ago · STALE"}
        got = _run([
            {"name": "both", "arm": True, "now": 1793236380000,
             "handed": {"ago": "12 min ago", "t": 1793236380000, "vaultLine": line}},
            {"name": "noVault", "arm": True, "now": 1793236380000,
             "handed": {"ago": "12 min ago", "vaultLine": None}},
            {"name": "noBoard", "arm": True, "now": 1793236380000,
             "handed": {"vaultLine": {"words": "vault 2 items · as of 30 min ago", "cls": "roster-sec", "state": "current"}}},
            {"name": "emptyWords", "arm": True, "now": 1,
             "handed": {"ago": "4 hr ago", "vaultLine": {"words": "", "state": "unknown"}}},
            {"name": "boardAgoWins", "arm": True, "now": 1,
             "handed": {"boardAgo": "2 hr ago", "ago": "under 1 min ago",
                        "vaultLine": {"words": "vault 1 item · as of 5 hr ago", "cls": "", "state": "stale"}}},
            {"name": "his", "arm": False, "now": 1793236380000,
             "handed": {"ago": "12 min ago", "vaultLine": line}},
        ])
        self.assertEqual(got["both"]["line"],
                         "board uploaded 12 min ago · vault 5 items · as of 3 hr ago · STALE")
        self.assertEqual(got["both"]["text"], got["both"]["line"])
        self.assertIs(got["both"]["hidden"], False)
        self.assertNotIn("12 min ago", got["both"]["line"].split(" · ", 1)[1])
        self.assertEqual(got["noVault"]["line"], "board uploaded 12 min ago · vault age UNKNOWN")
        self.assertEqual(got["noBoard"]["line"], "board uploaded, age UNKNOWN · vault 2 items · as of 30 min ago")
        self.assertEqual(got["emptyWords"]["line"], "board uploaded 4 hr ago · vault age UNKNOWN")
        self.assertEqual(got["boardAgoWins"]["line"],
                         "board uploaded 2 hr ago · vault 1 item · as of 5 hr ago")
        self.assertEqual(got["his"]["line"], "")
        self.assertIs(got["his"]["hidden"], True)
        self.assertEqual(got["his"]["text"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "REG-3123 - the vault line is dropped and the tab dates the vault by the board upload",
     "file": "tv/control_ui.html",
     "find": "               words: d.vaultLine.words };\n",
     "replace": "               words: '' };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3123 - a missing vault clock is filled with the board upload's age",
     "file": "bible.html",
     "find": "    var vault = (line && typeof line.words === 'string' && line.words) ? line.words : 'vault age UNKNOWN';\n",
     "replace": "    var vault = (line && typeof line.words === 'string' && line.words) ? line.words : (ago || 'just now');\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3123 - the boot drops the vault line on the way into the tab",
     "file": "bible.html",
     "find": "        line = snap.vaultLine;\n",
     "replace": "        line = null;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3123 - the fill never hands the row's vault line",
     "file": "tv/control_ui.html",
     "find": "                     ago: snap && snap.ago, vaultLine: (row && row.vaultLine) || null };\n",
     "replace": "                     ago: snap && snap.ago, vaultLine: null };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3123 - his own board paints the shadow's clocks",
     "file": "bible.html",
     "find": "    var s = window._vaultShadowClockState;\n    if (!s) return '';\n",
     "replace": "    var s = window._vaultShadowClockState;\n    if (false && !s) return '';\n",
     "matches": 1, "needs": "node"},
]
