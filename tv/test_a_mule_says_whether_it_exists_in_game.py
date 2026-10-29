# -*- coding: utf-8 -*-
"""#251 (REG-2928) - A VAULT MULE SAYS WHETHER IT EXISTS IN GAME, AND THE ANSWER NEVER BLOCKS ANYTHING.

window._vaultMuleSaveSay(m) answers from this PC's save names (GET /api/saves, REG-2926) and the game's own naming rule:
  * "a D2R name is letters only, so this exact name cannot be made in game" - the name is no D2R name (2-15 characters,
    letters, at most one '-' or '_'), whatever the saves say;
  * "on this account (seen in this PC's saves)" - the save folder names it, compared without case;
  * "not in this PC's saves" - the saves answered and do not name it.
Saves that never answered, a PC with no save folder and a shadow say nothing about the account, and SHARED STASH is no
character. The mule card draws the line under its plate; nothing else asks the rule, so it can never stop a filing.
Driven on the whole page in node (tv/vault_page_node). RED_PROOF below.
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

import vault_page_node as VPN  # noqa: E402

INVALID = "a D2R name is letters only, so this exact name cannot be made in game"
SEEN = "on this account (seen in this PC’s saves)"
ABSENT = "not in this PC’s saves"

BODY = r"""
function say(name, id){ var v = window._vaultMuleSaveSay({ id: id || 'm1', name: name }); return v ? [v.kind, v.say] : null; }
var NAMES = ['Konyolock', 'Hammer-Din', 'Old_Name', 'UNI-ARMOR', 'konyolock', 'WAR1', 'MAGIC & RARE', 'SETS-TAL-IK', 'K',
             'Abcdefghijklmnop', 'Mule A'];
OUT.before = NAMES.map(function(n){ return say(n); });
window._cbSavesTakeForLaw({ ok: true, state: 'no-folder', chars: null });
OUT.noFolder = say('Konyolock');
window._cbSavesTakeForLaw({ ok: true, state: 'folder', chars: [ { name: 'KONYOLOCK', ids: 1 }, { name: 'Uni-Armor', ids: 1 } ] });
OUT.after = NAMES.map(function(n){ return say(n); });
OUT.shared = say('SHARED STASH', 'shared');
try { window.renderVault(); } catch (e) { OUT.err = String(e); }
H.flush(60, 3);
var host = document.getElementById('vault-shelf'), html = host ? String(host._html || '') : '';
var re = /<span class="vm-name">([^<]*)<\/span>[\s\S]*?(?:data-save="(\w+)"[^>]*>([^<]*)<|<div class="vm-body">)/g, m, rows = [];
while ((m = re.exec(html))) rows.push([m[1], m[2] || null, m[3] || null]);
OUT.rows = rows;
document.documentElement.classList.add('tvd-shadow');
OUT.shadow = say('Konyolock');
"""


@unittest.skipIf(VPN.NODE is None, "node is absent - this law is UNMEASURED here, not passing")
class AMuleSaysWhetherItExistsInGame(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, timeout=600)

    def test_a_name_the_game_cannot_make_says_so_whatever_the_saves_say(self):
        for o in (self.o["before"], self.o["after"]):
            for i in (5, 6, 7, 8, 9, 10):
                self.assertEqual(o[i], ["invalid", INVALID], "index %d: %r" % (i, o[i]))

    def test_with_no_saves_answer_a_legal_name_says_nothing(self):
        self.assertEqual(self.o["before"][:5], [None] * 5, "a mule claimed or denied an account nobody read")
        self.assertIsNone(self.o["noFolder"], "a PC with no save folder said the mule is not on the account")

    def test_the_saves_decide_on_this_account_or_not(self):
        a = self.o["after"]
        self.assertEqual(a[0], ["seen", SEEN], "Konyolock against a save named KONYOLOCK")
        self.assertEqual(a[4], ["seen", SEEN])
        self.assertEqual(a[3], ["seen", SEEN])
        self.assertEqual(a[1], ["absent", ABSENT])
        self.assertEqual(a[2], ["absent", ABSENT])

    def test_the_shared_stash_and_a_shadow_say_nothing(self):
        self.assertIsNone(self.o["shared"])
        self.assertIsNone(self.o["shadow"], "a shadow judged their mule against this PC's saves")

    def test_the_mule_card_draws_the_line(self):
        rows = {r[0]: (r[1], r[2]) for r in self.o["rows"]}
        self.assertIsNone(self.o.get("err"), self.o.get("err"))
        self.assertIn("UNI-ARMOR", rows, "PREMISE: the vault did not paint its lockers: %r" % self.o["rows"])
        self.assertEqual(rows["UNI-ARMOR"][0], "seen")
        self.assertEqual(rows["MAGIC &amp; RARE"][0], "invalid")
        self.assertEqual(rows["SHARED STASH"], (None, None))

    def test_nothing_but_the_card_asks_the_rule_so_it_never_blocks(self):
        page = io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
        calls = re.findall(r"_vaultMuleSaveSay\(", page)
        self.assertEqual(len(calls), 1, "the mule check is called %d times - only its card may ask it, so it is only ever "
                         "said, never a gate" % len(calls))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "#251 (REG-2928) - a name with a digit, a space or a second hyphen passes as a D2R name",
     "file": "bible.html",
     "find": "    var ok = /^[A-Za-z][A-Za-z_-]{1,14}$/.test(nm) && (nm.match(/[-_]/g) || []).length <= 1;\n",
     "replace": "    var ok = /^[A-Za-z][A-Za-z0-9 &_-]{1,14}$/.test(nm);\n",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-2928) - the save names are compared with their case, so KONYOLOCK is not Konyolock",
     "file": "bible.html",
     "find": "    S.chars.forEach(function(c){ if (c && typeof c.name === 'string' && c.name.toLowerCase() === want) hit = true; });\n",
     "replace": "    S.chars.forEach(function(c){ if (c && typeof c.name === 'string' && c.name === nm) hit = true; });\n",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-2928) - saves nobody read say the mule is not on the account",
     "file": "bible.html",
     "find": "    if (!S || S.ok !== true || !Array.isArray(S.chars)) return null;\n    var want = nm.toLowerCase(), hit = false;\n",
     "replace": "    if (!S || S.ok !== true || !Array.isArray(S.chars)) return { kind: 'absent', say: _VM_SAVE_SAY.absent };\n    var want = nm.toLowerCase(), hit = false;\n",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-2928) - the mule card never draws the check",
     "file": "bible.html",
     "find": "            return v ? '<div class=\"vm-note vm-save\" data-save=\"' + esc(v.kind)",
     "replace": "            return (v = null) ? '<div class=\"vm-note vm-save\" data-save=\"' + esc(v.kind)",
     "matches": 1, "needs": "node"},
    {"why": "#251 (REG-2928) - SHARED STASH is judged as a character",
     "file": "bible.html",
     "find": "    if (!m || m.id === 'shared') return null;\n    var nm = String(m.name == null ? '' : m.name);\n",
     "replace": "    if (!m) return null;\n    var nm = String(m.name == null ? '' : m.name);\n",
     "matches": 1, "needs": "node"},
]
