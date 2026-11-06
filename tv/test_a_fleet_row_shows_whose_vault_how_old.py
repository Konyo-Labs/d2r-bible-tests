# -*- coding: utf-8 -*-
"""#250 (REG-3122) - A FLEET ROW AND A ROSTER BUTTON SAY THAT OWNER'S PUBLISHED VAULT: HOW BIG, AND HOW OLD BY ITS OWN CLOCK.

Fleet 3.0's last phase, his 2026-09-28 rule: the vault is viewable across PCs, fetched, shown as THEIRS, and a stale or
failed fetch says so with its age. A viewer saw another PC's vault only by opening its shadow, although every roster row
already publishes it (sections.vault: counts and asOf - when that board last handed its copy records, REG-2817) - and
nothing drew it. Now roster_publish.vault_line writes one line from that section - "vault N items · as of <age>",
"· STALE" past the roster's 2 h TTL, UNKNOWN when the row or its count will not read, "vault never published" when there
is no row or no vault section - aged by the section's OWN asOf, never this fetch's time and never the row's `t`. The
roster route hands it on each owner row (panel_words) and the fleet route on each Fleet row (_fleet_overlay_roster_vault,
owner by the console's own rule, owner_of); the roster person button and the open Fleet row print those words and
compute nothing, so the two cannot say different things.

Driven: vault_line and panel_words over a written and re-read roster cache; the Fleet overlay on a fleet answer (an
owner fetched, one never published, one not in the fetch, a nameless PC, no fetch at all); the console's
_rosterVaultHtml and _fleetOpenEyesHtml cut out of control_ui.html and run in node. RED_PROOF below.
"""
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
from console_safe import enable as _enable  # noqa: E402
_enable()
import roster_publish as RP  # noqa: E402
import control_app as CA  # noqa: E402

NODE = shutil.which("node")
UI = os.path.join(HERE, "control_ui.html")
NOW = 1793260000000
MIN = 60 * 1000


def _row(owner, vault=None, t=NOW, **more):
    """A published, hash-true view of one owner, as the roster cache stores it."""
    sections = {} if vault is None else {"vault": dict(vault)}
    raw = {"owner": owner, "published": True, "t": t, "sections": sections}
    kept = {k: {x: y for x, y in v.items() if x != "age"} for k, v in sections.items()}
    raw["hash"] = RP.hash_of(RP.packed(RP.for_hash(kept)))
    raw.update(more)
    return RP.view_one(owner, raw, NOW)


class TheLineSaysTheVaultAndItsOwnAge(unittest.TestCase):

    def say(self, row):
        got = RP.vault_line(row, NOW)
        return (got["state"], got["words"], got["cls"]) if got else None

    def test_a_fresh_vault(self):
        self.assertEqual(self.say(_row("Dean", {"counts": 12, "asOf": NOW - 12 * MIN, "rows": []})),
                         ("current", "vault 12 items · as of 12 min ago", "roster-sec"))
        self.assertEqual(self.say(_row("Dean", {"counts": 1, "asOf": NOW - 30 * 1000, "rows": []}))[1],
                         "vault 1 item · as of under 1 min ago")

    def test_both_stores_are_said_each_with_its_own_age(self):
        """v3866 (his call 2026-11-06: "show both numbers on the fleet row") - the Mac's row read "vault 1 item · STALE"
        while the console's vault routes said 92: two stores (the board's records; the sweep's evidence ledger), one
        number shown. Both are said now, each aged by its own store, never one folded into the other."""
        row = _row("Konyo \u00b7 Mac", {"counts": 1, "asOf": NOW - 3 * MIN, "rows": [],
                                        "sweep": {"owned": 92, "asOf": NOW - 86 * MIN}})
        self.assertEqual(self.say(row), ("current", "vault 1 item \u00b7 as of 3 min ago \u00b7 sweep evidence 92 (not filed) "
                                                    "\u00b7 86 min ago", "roster-sec"))
        stale = _row("Dean", {"counts": 40, "asOf": NOW - 3 * 60 * MIN, "rows": [], "sweep": {"owned": 5, "asOf": 0}})
        self.assertEqual(self.say(stale)[1], "vault 40 items \u00b7 as of 3 hr ago \u00b7 STALE",
                         "a sweep pair whose age will not read was said")
        self.assertIsNone(RP.sweep_of({"owned": True, "asOf": NOW}), "a bool was taken as a count")
        self.assertIsNone(RP.sweep_of({"owned": -1, "asOf": NOW}))

    def test_the_hash_takes_the_sweeps_count_never_its_age(self):
        a = RP.for_hash({"vault": {"counts": 1, "asOf": 5, "rows": [], "sweep": {"owned": 92, "asOf": 100}}})
        b = RP.for_hash({"vault": {"counts": 1, "asOf": 5, "rows": [], "sweep": {"owned": 92, "asOf": 999}}})
        c = RP.for_hash({"vault": {"counts": 1, "asOf": 5, "rows": [], "sweep": {"owned": 93, "asOf": 100}}})
        self.assertEqual(a, b, "every touch of the ledger file would republish the roster row")
        self.assertNotEqual(a, c, "a new grounded row would never reach the Fleet")

    @unittest.skipUnless(NODE, "node is absent - the worker is UNMEASURED here, never a pass")
    def test_the_worker_keeps_the_pair_and_hashes_the_count(self):
        import io
        script = r"""
import { pathToFileURL } from 'node:url';
import { readFileSync } from 'node:fs';
const CFG = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const m = await import(pathToFileURL(CFG.file).href);
const base = { asOf: 5, counts: 1, rows: [{ name: 'x' }] };
const a = m.shapeSection(Object.assign({}, base, { sweep: { owned: 92, asOf: 100 } }));
const b = m.shapeSection(Object.assign({}, base, { sweep: { owned: 92, asOf: 999 } }));
const bad = m.shapeSection(Object.assign({}, base, { sweep: { owned: 'x', asOf: 100 } }));
process.stdout.write(JSON.stringify({ kept: a.sweep, bad: bad.sweep || null,
  same: m.forHash({ vault: a }) === m.forHash({ vault: b }) }));
"""
        d = tempfile.mkdtemp(prefix="vault-sweep-worker-")
        try:
            h, c = os.path.join(d, "h.mjs"), os.path.join(d, "cfg.json")
            io.open(h, "w", encoding="utf-8").write(script)
            io.open(c, "w", encoding="utf-8").write(json.dumps({"file": os.path.join(os.path.dirname(HERE), "functions", "api",
                                                                                      "roster.js")}))
            r = subprocess.run([NODE, h, c], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        finally:
            shutil.rmtree(d, True)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        o = json.loads(r.stdout)
        self.assertEqual(o["kept"], {"owned": 92, "asOf": 100}, "the worker drops the sweep's number")
        self.assertIsNone(o["bad"], "the worker kept a count that is not a number")
        self.assertTrue(o["same"], "the worker hashes the sweep's age, so the PC and the worker disagree on every touch")

    def test_past_the_ttl_it_says_stale(self):
        self.assertEqual(self.say(_row("Dean", {"counts": 40, "asOf": NOW - 3 * 60 * MIN, "rows": []})),
                         ("stale", "vault 40 items · as of 3 hr ago · STALE", "roster-stale"))

    def test_the_age_is_the_vaults_own_never_the_copys(self):
        # the site stored this copy a minute ago (t), and the board handed these records three hours ago (asOf)
        row = _row("Konyo · ALT", {"counts": 7, "asOf": NOW - 3 * 60 * MIN, "rows": []}, t=NOW - MIN)
        self.assertEqual(row["age"], "current", "premise: the copy itself is fresh")
        self.assertEqual(self.say(row)[0], "stale", "the line dated the vault by the copy, not by the vault's own asOf")

    def test_an_age_that_will_not_read_is_unknown(self):
        self.assertEqual(self.say(_row("Dean", {"counts": 3, "rows": []}))[:2], ("unknown", "vault 3 items · age UNKNOWN"))
        self.assertEqual(self.say(_row("Dean", {"counts": 3, "asOf": NOW + 2 * 60 * MIN, "rows": []}))[0], "unknown",
                         "a vault stamped in the future read as fresh")

    def test_a_count_that_will_not_read_is_unknown(self):
        for bad in ("12", True, -1, None):
            self.assertEqual(self.say(_row("Dean", {"counts": bad, "asOf": NOW - MIN, "rows": []}))[:2],
                             ("unknown", "vault UNKNOWN (its count would not read)"), "counts %r" % (bad,))

    def test_no_row_or_no_vault_is_never_published(self):
        self.assertEqual(self.say({"owner": "Wife PC", "published": False})[:2], ("never", "vault never published"))
        self.assertEqual(self.say(_row("Dean"))[:2], ("never", "vault never published"))
        self.assertEqual(self.say({"owner": "Dean", "published": True, "corrupt": True})[:2],
                         ("unknown", "vault UNKNOWN (the roster row is corrupt)"))
        self.assertIsNone(RP.vault_line({"owner": "Somebody"}, NOW))

    def test_the_roster_route_hands_every_owner_its_line(self):
        d = tempfile.mkdtemp(prefix="vault_line_")
        try:
            views = [_row("Dean", {"counts": 5, "asOf": NOW - 20 * MIN, "rows": []}), _row("Konyo · Mac")]
            views += [{"owner": o, "published": False} for o in RP.OWNERS if o not in ("Dean", "Konyo · Mac")]
            RP.write_cache(d, views)
            payload = RP.panel_words(RP.read_cache(d, NOW + 10 * MIN))
        finally:
            shutil.rmtree(d, True)
        by = {r["owner"]: r.get("vaultLine") for r in payload["owners"]}
        self.assertEqual(sorted(by), sorted(RP.OWNERS))
        self.assertNotIn(None, list(by.values()), "the roster route handed an owner no vault line")
        self.assertEqual(by["Dean"]["words"], "vault 5 items · as of 30 min ago", "aged by this read, from its own asOf")
        self.assertEqual(by["Konyo · Mac"]["words"], "vault never published")
        self.assertEqual(by["Wife PC"]["words"], "vault never published")


class EachFleetRowCarriesItsOwnersLine(unittest.TestCase):

    def fleet(self):
        return {"online": [{"machine": "MacBook", "nickname": "Konyo", "platform": "mac"},
                           {"machine": "DEAN-PC", "nickname": "Dean", "platform": "windows"},
                           {"machine": "GROK", "nickname": "Grok", "platform": "mac", "vaultLine": {"words": "old"}}],
                "offline": [{"machine": "WIFE", "nickname": "Wife PC", "platform": "windows"}]}

    def test_each_owner_row_gets_its_line_and_a_nameless_pc_none(self):
        payload = {"ok": True, "fetched": True, "now": NOW,
                   "owners": [_row("Konyo · Mac", {"counts": 9, "asOf": NOW - 5 * MIN, "rows": []}),
                              _row("Dean", {"counts": 2, "asOf": NOW - 4 * 60 * MIN, "rows": []})]}
        fl = self.fleet()
        self.assertEqual(CA._fleet_overlay_roster_vault(fl, payload), 3)
        on, off = fl["online"], fl["offline"]
        self.assertEqual(on[0]["vaultLine"]["words"], "vault 9 items · as of 5 min ago", "Konyo on a mac is Konyo · Mac")
        self.assertEqual(on[1]["vaultLine"]["state"], "stale")
        self.assertNotIn("vaultLine", on[2], "a PC with no roster profile kept a vault line")
        self.assertEqual(off[0]["vaultLine"]["words"], "vault UNKNOWN (not in this PC's last roster fetch)")

    def test_no_fetch_is_unknown_never_none(self):
        fl = self.fleet()
        CA._fleet_overlay_roster_vault(fl, {"ok": True, "fetched": False, "owners": []})
        self.assertEqual(fl["online"][1]["vaultLine"], {"cls": "roster-unknown", "state": "unknown",
                                                       "words": "vault UNKNOWN (this PC has not fetched a roster yet)"})

    def test_the_fleet_route_lays_it_on(self):
        src = open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        anchor = '        if path == "/api/fleet":'
        self.assertEqual(src.count(anchor), 1, "the fleet route anchor is no longer one place")
        i = src.index(anchor)
        nxt = src.find("\n        if path == ", i + len(anchor))
        self.assertGreater(nxt, i, "the fleet route never ends at the next route")
        seg = src[i:nxt]
        self.assertIn("_fleet_overlay_roster_vault(_fl)", seg, "the fleet route does not lay the vault line on")


def _cut(src, sig):
    if src.count(sig) != 1:
        raise AssertionError("%r occurs %d times - this law cannot see its subject" % (sig, src.count(sig)))
    i = src.index(sig)
    depth = 0
    for j in range(src.index("{", i), len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1] + ";"
    raise AssertionError("%r never closed - harness fault, not a pass" % sig)


SCENARIO = r"""
function escC(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; }); }
var window = {};
var line = { cls: 'roster-stale', state: 'stale', words: 'vault 40 items · as of 3 hr ago · STALE' };
var out = {
  other: _fleetOpenEyesHtml({ nickname: 'Dean', vaultLine: line }, false),
  me: _fleetOpenEyesHtml({ nickname: 'Konyo', platform: 'mac', vaultLine: line }, true),
  meNone: _fleetOpenEyesHtml({ nickname: 'Konyo', platform: 'mac' }, true),
  nameless: _fleetOpenEyesHtml({ nickname: 'Grok', platform: 'mac' }, false),
  button: _rosterVaultHtml(line, 'roster-vault'),
  bad: _rosterVaultHtml({ cls: 'x' }, 'roster-vault')
};
process.stdout.write(JSON.stringify(out));
"""


class TheConsolePrintsTheRoutesWords(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.src = open(UI, encoding="utf-8").read()
        code = "\n".join([
            "var _FLEET_ROSTER_OWNERS = ['Konyo \\u00b7 Mac', 'Konyo \\u00b7 ALT', 'Konyo \\u00b7 GrokBot', 'Dean', 'Wife PC'];",
            _cut(cls.src, "  var _fleetRosterOwner = function (m) {"),
            _cut(cls.src, "  var _rosterVaultHtml = function (line, cls) {"),
            _cut(cls.src, "  var _fleetOpenEyesHtml = function (m, isMe) {")])
        r = subprocess.run([NODE, "-"], input=code + "\n" + SCENARIO, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("the console's row did not run in node: %s" % r.stderr[-900:])
        cls.o = json.loads(r.stdout)

    def test_an_open_fleet_row_says_its_vault_beside_its_eyes(self):
        o = self.o["other"]
        self.assertIn('<span class="fleet-vault roster-stale" data-vault-state="stale">vault 40 items · as of 3 hr ago · STALE</span>', o)
        self.assertLess(o.index("fleet-vault"), o.index("fleet-hd-eyes"), "the eyes no longer sit at the line's end (REG-2768)")

    def test_his_own_row_says_what_the_others_see_of_him(self):
        self.assertEqual(self.o["me"], '<div class="fleet-open-eyes"><span class="fleet-vault roster-stale" data-vault-state="stale">'
                                       'vault 40 items · as of 3 hr ago · STALE</span></div>')
        self.assertEqual(self.o["meNone"], "", "his row grew a strip with nothing in it")

    def test_a_pc_with_no_profile_draws_no_vault(self):
        self.assertNotIn("fleet-vault", self.o["nameless"])

    def test_the_roster_button_prints_the_same_words(self):
        self.assertEqual(self.o["button"], '<span class="roster-vault roster-stale" data-vault-state="stale">'
                                           'vault 40 items · as of 3 hr ago · STALE</span>')
        self.assertEqual(self.o["bad"], "", "a line with no words drew an empty span")
        anchor = "        var sig = _rosterSig(row);"
        self.assertEqual(self.src.count(anchor), 1, "the roster button anchor is no longer one place")
        i = self.src.index(anchor)
        end = self.src.find("}).join('');", i)
        self.assertGreater(end, i, "the roster button row never closed")
        seg = self.src[i:end]
        self.assertIn("window._rosterVaultHtml(row.vaultLine, 'roster-vault')", seg, "the roster button does not print its vault line")
        self.assertLess(seg.index("_rosterVaultHtml"), seg.index("roster-sig"), "the vault line must sit before the signature")


RED_PROOF = [
    {"why": "v3866 - the Fleet row says one store's number again (the sweep's 92 never reaches the row)",
     "file": "tv/roster_publish.py",
     "find": "    sw = sweep_of(sec.get(\"sweep\"))\n    tail = \"\"\n",
     "replace": "    sw = None\n    tail = \"\"\n",
     "matches": 1},
    {"why": "v3866 - every touch of the sweep ledger republishes the roster row (its age is hashed)",
     "file": "tv/roster_publish.py",
     "find": "            kept[\"sweep\"] = {\"owned\": kept[\"sweep\"].get(\"owned\")}",
     "replace": "            kept[\"sweep\"] = kept[\"sweep\"]",
     "matches": 1},
    {"why": "v3866 - the worker drops the sweep pair on arrival",
     "file": "functions/api/roster.js",
     "find": "&& typeof sw.asOf === \"number\" && Number.isFinite(sw.asOf) && sw.asOf > 0) out.sweep = { owned: sw.owned, asOf: sw.asOf };",
     "replace": "&& typeof sw.asOf === \"number\" && Number.isFinite(sw.asOf) && sw.asOf > 0) {}",
     "matches": 1},
    {"why": "REG-3122 - the line dates the vault by the copy's time, not the vault's own asOf",
     "file": "tv/roster_publish.py",
     "find": "    state, words = _ago(sec.get(\"asOf\"), now_ms)\n    head = \"vault %d item%s\"",
     "replace": "    state, words = _ago(row.get(\"t\"), now_ms)\n    head = \"vault %d item%s\"",
     "matches": 1},
    {"why": "REG-3122 - a vault past the TTL reads as current",
     "file": "tv/roster_publish.py",
     "find": "    if state == \"stale\":\n        return {\"cls\": \"roster-stale\", \"state\": \"stale\", \"words\": head + \" \\u00b7 as of \" + words + \" \\u00b7 STALE\" + tail}\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3122 - a row with no vault section reads as an empty vault",
     "file": "tv/roster_publish.py",
     "find": "    if not isinstance(sec, dict):\n        return {\"cls\": \"roster-never\", \"state\": \"never\", \"words\": \"vault never published\"}\n",
     "replace": "    if not isinstance(sec, dict):\n        sec = {\"counts\": 0, \"asOf\": now_ms}\n",
     "matches": 1},
    {"why": "REG-3122 - a count that will not read is drawn as a number",
     "file": "tv/roster_publish.py",
     "find": "    if isinstance(n, bool) or not isinstance(n, int) or n < 0:\n        return {\"cls\": \"roster-unknown\", \"state\": \"unknown\", \"words\": \"vault UNKNOWN (its count would not read)\"}\n",
     "replace": "    n = n if isinstance(n, int) else 0\n",
     "matches": 1},
    {"why": "REG-3122 - the roster route hands no vault line",
     "file": "tv/roster_publish.py",
     "find": "            row[\"vaultLine\"] = vault_line(row, payload.get(\"now\"))   # #250 (REG-3122) - its vault, aged by its own asOf\n",
     "replace": "            pass\n",
     "matches": 1},
    {"why": "REG-3122 - the fleet route lays no vault line on its rows",
     "file": "tv/control_app.py",
     "find": "                    try: _fleet_overlay_roster_vault(_fl)\n",
     "replace": "                    try: pass\n",
     "matches": 1},
    {"why": "REG-3122 - an owner this PC never fetched reads as never published",
     "file": "tv/control_app.py",
     "find": "            elif owner not in by:\n                line = {\"cls\": \"roster-unknown\", \"state\": \"unknown\", \"words\": \"vault UNKNOWN (not in this PC's last roster fetch)\"}\n",
     "replace": "            elif owner not in by:\n                line = _rp.vault_line({\"owner\": owner, \"published\": False}, data.get(\"now\"))\n",
     "matches": 1},
    {"why": "REG-3122 - the open Fleet row drops its vault line",
     "file": "tv/control_ui.html",
     "find": "    return '<div class=\"fleet-open-eyes\">' + vault + '<button type=\"button\" class=\"fleet-hd-eyes\" data-roster-owner=\"' + escC(owner) + '\"'",
     "replace": "    return '<div class=\"fleet-open-eyes\"><button type=\"button\" class=\"fleet-hd-eyes\" data-roster-owner=\"' + escC(owner) + '\"'",
     "matches": 1},
    {"why": "REG-3122 - the roster button drops its vault line",
     "file": "tv/control_ui.html",
     "find": "          + (row && row.published === true && window._rosterVaultHtml ? window._rosterVaultHtml(row.vaultLine, 'roster-vault') : '')   /* #250 (REG-3122) */\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
