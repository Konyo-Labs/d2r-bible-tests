# -*- coding: utf-8 -*-
"""#246 L7 — THE WITNESSED LANE FILES ITS OWN ROWS. The sweep's gate-passing stash rows land, with their witness.

His words: the vault should keep "reading it whenever it can after witnessed verify it it can automatically tag
it in to the mule account". The forensics found the system INVERTED: the witnessed lane could not land its own
items while the found-ever lane filed everything. vault_accum.json held 14 rows that clear the gate — Radiance
and Heart of the Oak among them — and only one was in the vault, filed by the found-ever sorter, not by its
sighting. The unattended feeder had run 12,000+ times and banked 0.

THE CAUSE, and why the name `lane` hid it: vault_retro's lane IS the container (stash / inventory / equipment),
while everywhere else in the board `lane` names which READER produced a row. vaultAccumApply handed chronicleApply
rows carrying `lane` and no `loc`, and chronicleApply's container gate reads `row.loc` — so it was false for every
row this lane ever produced. Worse, "already vaulted" was read from d2r_owned (found-ever), so a name the
found-ever lane had touched first was never offered to the vault door at all, whatever witness arrived.

WHAT THIS LAW HOLDS, end to end — the payload is built by the REAL tv/vault_retro.apply_payload, then applied by
the REAL window.vaultAccumApply in bible.html in its own headless Chrome:
  · a stash row with two independent framed looks FILES to the mule the router names, with a d2r_vaultProv row
    carrying source 'stash', both looks, the gate's own verdict and the stamped confidence bound;
  · it files even though the grail and d2r_owned already knew the name (the found-ever lane got there first);
  · Magefist's real shape — one frameless conf-0.0 look plus one real look — does NOT file, and with no gate
    verdict travelling the BOARD judges each look itself and still refuses it (W3);
  · a found-ever name the sweep never saw does NOT file;
  · a SET PIECE seen in the stash files through the set door with its witness, and ticks its set.
  · #246 review — A WITNESSED NAME WITH NO MULE SAYS SO. A shared-stash name (suggestMule's one null) handed to the
    registrar with two framed looks and a passing gate came back {filed:false, why:''}, and its ledger row read
    "no witness ... waits for a second look" — a second look can never file it. The registrar now answers
    'no-home' in the door's own sentence and the ledger row says the shared stash; a register with NO witness
    still reads 'no-witness'. The sorter, re-filing a witness row the door answers 'no-home' (a row an imported
    store can carry), logs 'no-home' too, never 'no-witness'.
RED_PROOF below.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

from test_found_ever_never_files_to_a_mule import Board, RC, NO_BROWSER  # noqa: E402  ONE harness
import vault_retro as VR  # noqa: E402


def _look(sid, frame, conf):
    return {"session": sid, "frame": frame, "conf": conf, "lane": "stash"}


#: game item names only
GOOD = {"name": "Nagelring", "lane": "stash", "kind": "item", "count": 1, "conf": 0.9,
        "witnesses": [_look("s_a", "f_a.jpg", 0.9), _look("s_b", "f_b.jpg", 0.85)]}
MAGEFIST = {"name": "Magefist", "lane": "stash", "kind": "item", "count": 1, "conf": 0.85,
            "witnesses": [_look("s_1", None, 0.0), _look("s_2", "f_2.jpg", 0.85)]}
# v3849 (6fff0ef41): only a valuable set piece is kept - Aldur's Advance is thrown out now - so the piece is a kept one
PIECE = {"name": "Tal Rasha's Guardianship", "lane": "stash", "kind": "item", "count": 1, "conf": 0.9,
         "witnesses": [_look("s_c", "f_c.jpg", 0.9), _look("s_d", "f_d.jpg", 0.9)]}
FOUND_EVER = "Arachnid Mesh"

_B = {}


def board():
    if "b" not in _B:
        _B["b"] = Board().open()
    return _B["b"]


def tearDownModule():
    b = _B.pop("b", None)
    if b is not None:
        b.close()


class TheWitnessedLaneFilesItsOwnRows(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.payload = VR.apply_payload({"ok": True, "owned": [GOOD, MAGEFIST, PIECE]})
        b = board()
        # the found-ever lane got there first: the grail AND d2r_owned already know Nagelring
        b.seed({"d2r_owned": ["Nagelring", FOUND_EVER], "d2r_muleAssign": {}, "d2r_vaultProv": None,
                "d2r_foundLog": {"Nagelring": "Aug 1, 2026 · 10:00", FOUND_EVER: "Aug 1, 2026 · 10:00"},
                "d2r_setPieces": [], "d2r_laneLock": None, "d2r_rwProfile": "fresh"})
        b.run("window.LSR.setItem('d2r_vaultAutoIntake','on'); window.LSR.setItem('d2r_owned', JSON.stringify(['Nagelring', %s])); window._vaultReloadOwned();"
              % json.dumps(FOUND_EVER))
        cls.out = b.run("var r = window.vaultAccumApply(%s); OUT.applied = r;"
                        "OUT.map = JSON.parse(window.LSR.getItem('d2r_muleAssign') || '{}');"
                        "OUT.prov = JSON.parse(window.LSR.getItem('d2r_vaultProv') || '{}');"
                        "OUT.setPieces = JSON.parse(window.LSR.getItem('d2r_setPieces') || '[]');"
                        % json.dumps(cls.payload))
        # ⚠ AND WITH NO GATE VERDICT TRAVELLING — an older payload, or a caller that ships none. The board's
        # own per-look rule must decide then; above, the Python gate's pass:false decides first, so that
        # case alone could not tell whether the board checks each look at all (heart2 caught it BLIND).
        cls.nogate = b.run("window.vaultAccumApply({ items: [{ name: 'Goldwrap', lane: 'stash', kind: 'item',"
                           " conf: 0.85, witnesses: %s, witnessCount: 2 }] });"
                           "OUT.map = JSON.parse(window.LSR.getItem('d2r_muleAssign') || '{}');"
                           % json.dumps(MAGEFIST["witnesses"]))

    def test_the_payload_carries_the_gates_own_verdict(self):
        items = dict((i["name"], i) for i in self.payload["items"])
        self.assertIs(True, items["Nagelring"]["gate"]["pass"], items["Nagelring"]["gate"])
        self.assertIs(False, items["Magefist"]["gate"]["pass"], "Magefist's frameless look still counts: %r"
                      % items["Magefist"]["gate"])
        self.assertEqual(0.095, items["Magefist"]["gate"]["wilson"], "the confidence bound was not stamped")

    def test_a_gate_passing_stash_row_files_with_its_witness(self):
        m, p = self.out["map"], self.out["prov"]
        self.assertTrue(m.get("Nagelring"), "the witnessed lane could not land its own row: %r" % self.out["applied"])
        row = p.get("Nagelring") or {}
        self.assertEqual("stash", row.get("source"), "the filing carries no stash witness: %r" % row)
        self.assertEqual(2, len(row.get("looks") or []), "the row does not keep both looks: %r" % row)
        self.assertIs(True, (row.get("gate") or {}).get("pass"), "the gate's verdict did not travel: %r" % row)
        self.assertIsNotNone(row.get("wilson"), "the confidence bound did not travel")
        self.assertEqual(m.get("Nagelring"), row.get("mule"), "the row and the map name different homes")

    def test_magefists_shape_and_a_found_ever_name_do_not_file(self):
        self.assertNotIn("Magefist", self.out["map"], "one real look plus a frameless unsure one FILED")
        self.assertNotIn(FOUND_EVER, self.out["map"], "a found-ever name the sweep never saw was filed")

    def test_the_board_judges_each_look_itself_when_no_verdict_travels(self):
        self.assertNotIn("Goldwrap", self.nogate["map"],
                         "with no gate verdict on the row, the BOARD filed one real look plus a frameless "
                         "conf-0.0 one — it does not judge each look itself")

    def test_the_door_itself_drops_a_frameless_or_unsure_look(self):
        # v3845 - heart2 found W3 BLIND: the register wrapper refuses Magefist's shape too, so a door that let a
        # frameless conf-0.0 look through stayed hidden behind it. Ask the door alone, look by look.
        o = board().run("var W = window._vaultWitnessCheck;"
                        "OUT.mage = W({ lane: 'stash', witnesses: %s });"
                        "OUT.unsure = W({ lane: 'stash', witnesses: [{ session: 's_u', frame: 'f_u.jpg', conf: 0.3 },"
                        " { session: 's_v', frame: 'f_v.jpg', conf: 0.9 }] });"
                        "OUT.noconf = W({ lane: 'stash', witnesses: [{ session: 's_n', frame: 'f_n.jpg' },"
                        " { session: 's_m', frame: 'f_m.jpg', conf: 0.9 }] });"
                        "OUT.good = W({ lane: 'stash', witnesses: %s });"
                        % (json.dumps(MAGEFIST["witnesses"]), json.dumps(GOOD["witnesses"])))
        for k in ("mage", "unsure", "noconf"):
            self.assertIs(False, o[k]["ok"], "the door counted a %s look as a witness: %r" % (k, o[k]))
            self.assertEqual(1, o[k].get("dropped"), "the door did not drop the %s look: %r" % (k, o[k]))
            self.assertEqual(1, o[k].get("looks"), o[k])
        self.assertIs(True, o["good"]["ok"], "PREMISE: two framed sure looks pass the door: %r" % o["good"])

    def test_a_witnessed_name_with_no_mule_says_so(self):
        looks = [_look("s_e", "f_e.jpg", 0.7), _look("s_f", "f_f.jpg", 0.85)]
        out = board().run("OUT.r = window.tvVaultRegister('Cold Rupture', { lane: 'stash', sessions: %s,"
                          " gate: { pass: true, why: 'two looks' }, by: 'vault-sweep' });"
                          "OUT.bare = window.tvVaultRegister('Stormshield');"
                          "var L = JSON.parse(window.LSR.getItem('d2r_chronicleInboxLog') || '[]') || [];"
                          "OUT.rows = L.filter(function(x){ return x && (x.name === 'Cold Rupture' || x.name === 'Stormshield'); })"
                          ".map(function(x){ return [x.name, x.status, x.why]; });" % json.dumps(looks))
        r = out["r"]
        self.assertFalse(r.get("filed"), "a shared-stash name was filed to a mule: %r" % r)
        self.assertEqual("no-home", r.get("refused"), "the registrar did not say it has no mule to go to: %r" % r)
        self.assertIn("shared stash", r.get("why") or "", r)
        rows = dict((n, (st, why)) for n, st, why in out["rows"])
        st, why = rows.get("Cold Rupture") or (None, "")
        self.assertEqual("no-home", st, "the ledger row mislabels a witnessed, unroutable register: %r" % (rows,))
        self.assertNotIn("second look", why, "the ledger tells him a second look would file what no mule can hold")
        self.assertEqual("no-witness", (rows.get("Stormshield") or (None,))[0],
                         "a register with NO witness stopped reading 'no-witness': %r" % (rows,))

    def test_the_sorter_says_no_mule_for_a_witnessed_row_it_cannot_home(self):
        row = {"mule": None, "holder": "", "source": "stash", "at": "2026-09-20T10:00:00.000Z", "by": "vault-sweep",
               "sessions": ["s_g", "s_h"], "gate": {"pass": True, "why": "two looks", "looks": 2},
               "looks": [{"id": "s_g", "frame": "f_g.jpg", "conf": 0.9}, {"id": "s_h", "frame": "f_h.jpg", "conf": 0.8}]}
        out = board().run("var P = JSON.parse(window.LSR.getItem('d2r_vaultProv') || '{}'); P['Flame Rift'] = %s;"
                          "window.LSR.setItem('d2r_vaultProv', JSON.stringify(P)); window.vaultAutoAssign();"
                          "var L = JSON.parse(window.LSR.getItem('d2r_chronicleInboxLog') || '[]') || [];"
                          "OUT.row = L.filter(function(x){ return x && x.name === 'Flame Rift'; }).map(function(x){ return [x.status, x.why]; });"
                          "OUT.filed = JSON.parse(window.LSR.getItem('d2r_muleAssign') || '{}')['Flame Rift'] || null;"
                          % json.dumps(row))
        self.assertIsNone(out["filed"], "a shared-stash name was filed to a mule by the sorter: %r" % out)
        self.assertEqual(1, len(out["row"]), "premise: the sorter left no ledger row for the row it could not home")
        self.assertEqual("no-home", out["row"][0][0], "the sorter calls a witnessed row 'no witness': %r" % out["row"])

    def test_a_set_piece_seen_in_the_stash_files_through_the_set_door(self):
        pieces = [k for k in self.out["map"] if k.startswith("Tal Rasha's Guardianship")]
        self.assertTrue(pieces, "a set piece witnessed in the stash was not filed: %r" % self.out["applied"])
        self.assertEqual("stash", (self.out["prov"].get(pieces[0]) or {}).get("source"))
        self.assertIn(pieces[0], self.out["setPieces"], "the set piece did not tick its set")


RED_PROOF = [
    {
        "why": "#246 W2 - the sweep's rows lose `loc` again, the container gate is false for every row, nothing lands",
        "file": "bible.html",
        "find": "source: 'vault-sweep', loc: it.lane, scene: it.scene || null, gate: it.gate });",
        "replace": "source: 'vault-sweep', scene: it.scene || null, gate: it.gate });",
        "matches": 1,
    },
    {
        "why": "#246 W2 - 'already vaulted' is read from found-ever d2r_owned again, so a known name never reaches the door",
        "file": "bible.html",
        "find": "      var map = JSON.parse(window.LSR.getItem('d2r_muleAssign') || '{}') || {};\n      var ks = Object.keys(map);\n",
        "replace": "      var map = {}; (JSON.parse(window.LSR.getItem('d2r_owned') || '[]') || []).forEach(function(o){ map[o] = 1; });\n      var ks = Object.keys(map);\n",
        "matches": 1,
    },
    {
        "why": "#246 review - a witnessed register with no mule to go to comes back with no reason again (reads 'no witness')",
        "file": "bible.html",
        "find": ("        _vf = { ok: false, refused: 'no-home', why: (sg && sg.unsorted && typeof sg.why === 'string' && sg.why.trim())\n"
                 "                ? sg.why.trim() : _vNoHomeWhy(name, sg ? sg.id : null) };\n"),   # REG-2857 re-aim: same sabotage
        "replace": "        _vf = null;\n",
        "matches": 1,
    },
    {
        "why": "#246 review - the ledger row calls an unroutable register 'no-witness' again",
        "file": "bible.html",
        "find": "                 : (r.filed === false ? (r.refused === 'carried' ? 'carried' : r.refused === 'no-home' ? 'no-home'\n",
        "replace": "                 : (r.filed === false ? (r.refused === 'carried' ? 'carried' : false ? 'no-home'\n",
        "matches": 1,
    },
    {
        "why": "#246 review - the sorter logs a witnessed row it cannot home as 'no-witness' again",
        "file": "bible.html",
        "find": "      } else if (_r && _r.refused === 'no-home'){\n",
        "replace": "      } else if (false){\n",
        "matches": 1,
    },
    {
        # re-anchored 2026-10-08 (REG-2022, his #267 ruling) - the rule is unchanged: a frameless or unsure look never counts
        "why": "#246 W3 - the board's door counts a frameless, unsure look as a witness again (Magefist files)",
        "file": "bible.html",
        "find": "      if (!id || !fr || (c == null && _anyConf) || (c != null && c < VAULT_WITNESS_FLOOR)){ dropped++; return; }\n",
        "replace": "      if (!id){ dropped++; return; }\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    if not os.path.exists(RC.CHROME):
        sys.stderr.write("⚪ SKIP — %s. UNMEASURED, declared as a skip (77), never a pass.\n" % NO_BROWSER)
        raise SystemExit(77)
    import unittest as _u
    _u.main(verbosity=2)
