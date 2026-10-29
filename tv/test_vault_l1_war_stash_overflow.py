# -*- coding: utf-8 -*-
"""Vault L1 - every hand copy is its own item, cell and row; the war stash uses its 5 pages, then WAR1, WAR2.

Elad, live v3774 (2026-10-20): "a 2nd Aldur's Deception I added vanished - no row, no cell, no error". He owns
2-3 Arachnid Mesh, ~4 Andariel's Visage, ~3 Vampire Gaze, all war-stash (SHARED STASH) gear. His rulings:
  - a duplicate hand add is another physical copy: its own copyIx, the next free cell beside the first, its own
    MANUAL -> cell row (the Grief x2 copies[] store; a set piece he types twice is the spare he asked for);
  - the war stash has 5 pages (10x10 each), all used before any overflow;
  - overflow fills the mules named WAR1, then WAR2 ... (case-insensitive), in order;
  - none / all full: SUPERSEDED 2026-10-28 ~17:50 IDT (REG-2803) - his words: "yea the board should automatically create a
    mule and name it War1/War2 for each mule and prompt me to create that same mule ingame so i get tasked to do it". The
    board now makes WAR1 (then WAR2 ...) itself, the copies land on it, and MOVE TASKS asks him first to create it in the
    game. Until then (2026-10-20) it read: the item keeps NO cell and MOVE TASKS says so; a mule is never created. A WAR
    mule he took back (deleted) is not made again; the board makes the next one (REG-2997, his ruling 2026-10-29).
    The board names war mule n by letter, WAR-A, WAR-B ... (REG-2980: a D2R name holds no digit); the cases read that name
    from the page (_vaultWarName), never pin it.
    The WAR mules a case starts with are seeded into the roster store, the way his saved roster holds them.
Driven on the SHIPPED page through the real door (window.vaultHandAdd), AUTO INTAKE off. RED_PROOF below.
NO CHROME AT ALL = a declared skip, never a pass. [[regression-guard]]
"""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_vault_l1_a_hand_add_routes_by_type as T  # noqa: E402  (its board, door and reader)
H = T.H

READ = T.READ + r"""
function mv(re){ return recs().filter(function(r){ return re.test(r.name) && r.move; }).map(function(r){ return { n: r.name, c: r.copyIx || 0, to: r.move.to }; }); }
function rows(re){ var h = document.getElementById('vault-move-list'); return h ? Array.prototype.filter.call(h.querySelectorAll('.vtk-list:not([data-sec="done"]) .vmv-row'), function(r){ return re.test(r.getAttribute('data-name') || ''); }).map(function(r){ return r.textContent.replace(/\s+/g, ' '); }) : null; }
"""
_MAKE = ("var _ml = (document.getElementById('vault-move-list') || {}).innerHTML || '';"
         "OUT.make = Array.prototype.map.call(document.querySelectorAll('#vault-move-list li.vtk-make'), function(e){ return e.textContent; });"
         "OUT.makeFirst = _ml.indexOf('data-sec=\"make\"') >= 0 && (_ml.indexOf('data-sec=\"moves\"') < 0 || _ml.indexOf('data-sec=\"make\"') < _ml.indexOf('data-sec=\"moves\"'));")
BELT_PER_GRID = 100    # a 1x1 ring on a 10x10 grid (rings / amulets keep every copy in the war stash)
BELT = "The Stone of Jordan"   # the page-fill filler: the only war gear with no copy cap
CAP_BELT = "Arachnid Mesh"     # a 2x1 belt: at most 4 copies in the war stash (Elad 2026-10-20 22:05)


def tearDownModule():
    T.tearDownModule()


def roster_with(names, declined=None):
    """the saved roster, plus mules named `names` (seeded like his saved store - never the Add mule button); `declined` = the
    WAR mules he took back (REG-2803: kept on the shared stash's entry, so the board does not make them again).

    HIS board is owner-claimed. The scratch Chrome opens file:// on an empty profile with no claim, which is a GUEST world,
    and a guest never makes a mule (REG-2803's own rule). Measured in node on that world (v3834): _vaultWarAuto.why was
    "a guest world makes no mule", WAR1 was never made, and four cases failed on CI. So the world is claimed for this
    install before the seed, and the claim is a premise the case asserts."""
    T.board().run("localStorage.setItem('d2r_ownerClaim', window._D2R_INSTALL || '*');")
    T.board().navigate()
    T.fresh()
    r = T.board().run("OUT.r = JSON.parse(window.LSR.getItem('d2r_muleRoster') || 'null') || (window._vaultRosterNow && window._vaultRosterNow());")["r"]
    assert isinstance(r, list) and r, "PREMISE: the page saved no roster to extend: %r" % (r,)
    r = [m for m in r if not re.match(r"^war\s*\d*$", str(m.get("name", "")), re.I)
         and not str(m.get("id", "")).startswith("war-law-") and m.get("role") != "war"]  # a renamed WAR box from another test
    # REG-2968 - a WAR mule is one by its STORED role and number (REG-2804), never its name: seeding a name-only "WAR1" into a
    # roster whose one-time legacy stamp (warRoleV) another case already saved made an ordinary mule, and the board minted
    # WAR3 (CI on ci/claude-v3836). The law seeds them as the board stores them: role war, warN in order.
    for i, n in enumerate(names):
        r.append({"id": "war-law-%d" % i, "name": n, "role": "war", "warN": i + 1})
    for m in r:
        if m.get("id") == "shared":
            m.pop("warDeclined", None)
            if declined:
                m["warDeclined"] = list(declined)
    T.board().seed({"d2r_muleRoster": r, "d2r_owned": [], "d2r_vaultProv": {}, "d2r_muleAssign": {},
                    "d2r_vaultRecords": None, "d2r_copies": {}, "d2r_multiKeep": {}})
    owner = T.board().run("OUT.o = window._D2R_OWNER === true;")["o"]
    assert owner, "PREMISE: the board is a guest world, where no mule is ever made - not his board"


def add_many(names, step=20):
    """hand-add in batches: one page call per batch, so a 500-copy fill never outlives one CDP call"""
    for i in range(0, len(names), step):
        T.add_all(names[i:i + step])


def war_name(n):
    """REG-2980 - the name the board gives war mule n, read from the page (one rule, never a pinned string)"""
    return T.board().run("OUT.n = window._vaultWarName(%d);" % n)["n"]


def war_makes(o, name):
    """the make rows for the war mule `name` - the CHARMS mule the board makes (REG-2895) has its own make row too, first
    (roster order), so a case never reads the war mule's row as make row [0] (REG-2888's node finding, the same here)"""
    return [t for t in (o.get("make") or []) if ("Create mule %s in the game" % name) in t]


def cells(moves):
    return [(m["to"] or {}).get("holder", None) and ((m["to"]["holder"], m["to"]["cell"])) for m in moves]


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class WarStashOverflow(unittest.TestCase):

    def test_two_hand_copies_of_a_set_piece_are_two_items_two_cells_two_rows(self):
        T.fresh()
        a = T.add_all(["Aldur's Deception", "Aldur's Deception"])["add"]
        o = T.board().run(READ + "OUT.m = mv(/^Aldur's Deception/); OUT.rows = rows(/^Aldur's Deception/);")
        self.assertEqual(len(o["m"]), 2, "the 2nd copy vanished: %r / %r" % (o["m"], a))
        self.assertEqual(sorted(m["c"] for m in o["m"]), [0, 1], o["m"])
        cs = cells(o["m"])
        self.assertTrue(all(c and c[1] for c in cs), "a copy has no cell: %r" % cs)
        self.assertEqual(len(set(cs)), 2, "two copies share one cell: %r" % cs)
        self.assertEqual(len(set(c[0] for c in cs)), 1, "the copies split mules: %r" % cs)
        self.assertEqual(len(o["rows"]), 2, "not two MOVE TASKS rows: %r" % o["rows"])
        for r in o["rows"]:
            self.assertRegex(r, r"MANUAL → SETS-[A-Z\-]+ · (?:Mule \d+ · )?[A-Z][a-z]+(?: stash)? · col \d+ · row \d+")   # REG-3062

    def test_three_and_four_war_copies_each_get_a_cell_and_a_row(self):
        """Elad 2026-10-20: a BIG item keeps ONE copy in the war stash; every extra copy goes to the WAR mules (never its
        normal mule), each with its own cell and row. Small gear (Arachnid Mesh, a 2x1 belt) keeps up to 4 there."""
        roster_with(["WAR1"])
        T.add_all(["Andariel's Visage"] * 4 + ["Vampire Gaze"] * 3 + ["Arachnid Mesh"] * 3)
        for nm, n in (("Andariel's Visage", 4), ("Vampire Gaze", 3)):
            o = T.board().run(READ + "OUT.m = mv(new RegExp('^' + %s)); OUT.rows = rows(new RegExp('^' + %s));" % (json.dumps(nm), json.dumps(nm)))
            cs = cells(o["m"])
            self.assertEqual(len(cs), n, "%s: %d copies, %d items: %r" % (nm, n, len(cs), cs))
            self.assertEqual(len(set(cs)), n, "%s copies share cells: %r" % (nm, cs))
            by = {m["c"]: m["to"]["holder"] for m in o["m"]}
            self.assertEqual(by[0], "SHARED STASH", "%s: the first-witnessed copy left the war stash: %r" % (nm, by))
            self.assertEqual([c for c, h in by.items() if h == "SHARED STASH"], [0], "%s: more than one big copy in the war stash: %r" % (nm, by))
            self.assertTrue(all(h == "WAR1" for c, h in by.items() if c), "%s extras not on the WAR1 mule: %r" % (nm, by))
            self.assertEqual(len(o["rows"]), n, "%s: not %d rows: %r" % (nm, n, o["rows"]))
        for nm, n in (("Arachnid Mesh", 3),):
            o = T.board().run(READ + "OUT.m = mv(new RegExp('^' + %s)); OUT.rows = rows(new RegExp('^' + %s));" % (json.dumps(nm), json.dumps(nm)))
            cs = cells(o["m"])
            self.assertEqual(len(cs), n, "%s: %d copies, %d items: %r" % (nm, n, len(cs), cs))
            self.assertEqual(len(set(cs)), n, "%s copies share cells: %r" % (nm, cs))
            self.assertTrue(all(c and c[0] == "SHARED STASH" for c in cs), "%s left the war stash: %r" % (nm, cs))
            self.assertEqual(len(o["rows"]), n, "%s: not %d rows: %r" % (nm, n, o["rows"]))
            for r in o["rows"]:
                self.assertRegex(r, r"MANUAL → SHARED STASH · Page [1-5] · col \d+ · row \d+")   # REG-2802 "page"; REG-3005 the one spelling

    def test_all_five_pages_fill_then_war1_then_war2(self):
        # the 600-copy fill leaves its page busy for minutes; the next test opens a fresh board instead of timing out on it
        self.addCleanup(T.tearDownModule)
        roster_with(["war1", "WAR2"])     # case-insensitive names
        # PREMISE before the 601-copy fill: the filler keeps every copy. A capped filler spills all but 4 to the WAR
        # mules and re-plans a full vault per add - the census's tampered run of red-proof [21] hit its 960 s timeout
        # there (UNPROVABLE, and it set the shard's wall time). Asked here, it fails in one call.
        cap = T.board().run("var c = window._vaultWarCap(%s); OUT.c = c === Infinity ? 'all' : c;" % json.dumps(BELT))["c"]
        self.assertEqual(cap, "all", "PREMISE: %s (the page-fill filler) must keep every copy in the war stash, got %r - "
                         "the fill would measure a spill, not the 5 pages" % (BELT, cap))
        n = 5 * BELT_PER_GRID + BELT_PER_GRID + 1
        add_many([BELT] * n, step=5)  # each add re-plans every copy; small batches keep each CDP call short late in the fill
        o = T.board().run(READ + "OUT.m = mv(/^The Stone of Jordan$/); OUT.full = window._vaultWarFull || [];"
                          "OUT.badge = Array.prototype.map.call(document.querySelectorAll('.vm-warbadge'), function(e){ return e.textContent; });"
                          "OUT.rows = rows(/^The Stone of Jordan$/).filter(function(t){ return /war1|WAR2/.test(t); });")
        cs = cells(o["m"])
        self.assertEqual(len(cs), n, "copies were dropped: %d of %d" % (len(cs), n))
        pages = {}
        for h, c in cs:
            if h == "SHARED STASH":
                y = int(re.match(r"^shared:c\d+r(\d+)$", c).group(1))
                pages[y // 10] = pages.get(y // 10, 0) + 1
        self.assertEqual(pages, {p: BELT_PER_GRID for p in range(5)}, "the 5 war-stash pages were not all filled first: %r" % pages)
        self.assertEqual(sum(1 for h, _ in cs if h == "war1"), BELT_PER_GRID, "WAR1 did not fill next: %r" % cs[-20:])
        self.assertEqual(sum(1 for h, _ in cs if h == "WAR2"), 1, "the spill did not reach WAR2: %r" % cs[-5:])
        self.assertEqual(len(set(cs)), n, "two copies share a cell")
        self.assertEqual(o["full"], [])
        self.assertTrue(o["rows"] and all("SHARED STASH · overflow" in t for t in o["rows"]),
                        "a WAR row does not say it is the Shared Stash overflow: %r" % o["rows"][:3])

    def test_no_war_mule_the_board_makes_war1_and_tasks_him(self):
        """REG-2803 (his ruling 2026-10-28): the 5 pages full and no WAR mule - the board makes WAR1, the copy lands on it,
        and MOVE TASKS asks him first to create WAR1 in the game."""
        roster_with([])
        n = 5 * BELT_PER_GRID + 1
        add_many([BELT] * n, step=5)  # each add re-plans every copy; small batches keep each CDP call short late in the fill
        o = T.board().run(READ + "OUT.m = mv(/^The Stone of Jordan$/); OUT.line = ((document.querySelector('#vault-move-list .vmv-warfull') || {}).textContent || '');"
                          "OUT.wars = JSON.parse(window.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return /^war/i.test(m.name); })"
                          ".map(function(m){ return [m.name, (m.auto || {}).by || null]; });" + _MAKE)
        placed = [m for m in o["m"] if (m["to"] or {}).get("cell")]
        w1 = war_name(1)
        self.assertEqual(len(placed), n, "a copy kept no cell: %d of %d" % (len(placed), n))
        self.assertEqual(sum(1 for m in placed if (m["to"] or {}).get("holder") == w1), 1, "the 501st copy is not on %s" % w1)
        self.assertEqual(o["wars"], [[w1, "board"]], "the board did not make exactly one war mule 1: %r" % o["wars"])
        self.assertEqual(o["line"], "", "MOVE TASKS still says there is no WAR mule: %r" % o["line"])
        self.assertEqual(len(war_makes(o, w1)), 1, o["make"])
        self.assertTrue(o["makeFirst"], "the make task is not above the moves")

    def test_utility_proc_and_charge_gear_routes_to_the_war_stash(self):
        """Elad 2026-10-20: Demon Limb (Enchant charges), Metamorphosis (Mark of Bear/Wolf), Treachery (Fade) -> SHARED STASH"""
        o = T.board().run("OUT.r = {}; ['Demon Limb', 'Metamorphosis', 'Treachery', \"Guillaume's Face\", 'Arachnid Mesh', \"Andariel's Visage\", 'Vampire Gaze']"
                          ".forEach(function(n){ var s = window.suggestMule(n); OUT.r[n] = s && s.id; });")
        for n, mid in o["r"].items():
            self.assertEqual(mid, "shared", "%s routed to %r, not the war stash" % (n, mid))

    def test_guillaumes_face_goes_to_the_war_stash_not_sets_rest(self):
        """Elad 2026-10-19: Guillaume's Face -> the war stash (Shared Stash); war gear beats the keep-set rule"""
        o = T.board().run("var s = window.suggestMule(\"Guillaume's Face\"); OUT.id = s && s.id; OUT.why = s && s.why;"
                          "OUT.set = !!(window.findSetPiece && window.findSetPiece(\"Guillaume's Face\"));"
                          "OUT.role = window.vaultWarGearRole(\"Guillaume's Face\");")
        self.assertTrue(o["set"], "PREMISE: Guillaume's Face is a set piece (the keep-set rule would claim it)")
        self.assertEqual(o["id"], "shared", "Guillaume's Face routed to %r (%s), not the war stash" % (o["id"], o["why"]))
        self.assertIn("war gear", o["why"] or "")
        self.assertTrue(o["role"])

    def test_size_is_read_off_the_footprint_not_a_name_list(self):
        o = T.board().run("OUT.r = {}; ['Stone of Jordan', 'Raven Frost', \"Mara's Kaleidoscope\", \"Thundergod's Vigor\", 'Shako', \"Guillaume's Face\", 'Demon Limb', 'Enigma']"
                          ".forEach(function(n){ OUT.r[n] = { small: window._vaultWarSmall(n), cells: window._itemCells ? window._itemCells(n) : null }; });")
        for n in ("Stone of Jordan", "Raven Frost", "Mara's Kaleidoscope", "Thundergod's Vigor"):
            self.assertTrue(o["r"][n]["small"], "%s is small gear: %r" % (n, o["r"][n]))
        for n in ("Shako", "Guillaume's Face", "Demon Limb", "Enigma"):
            self.assertFalse(o["r"][n]["small"], "%s is big gear: %r" % (n, o["r"][n]))

    def test_small_war_gear_keeps_every_copy_grouped_in_the_war_stash(self):
        roster_with([])
        T.add_all(["The Stone of Jordan"] * 5 + ["Raven Frost"] * 5)
        for nm in ("The Stone of Jordan", "Raven Frost"):
            o = T.board().run(READ + "OUT.m = mv(new RegExp('^' + %s + '$'));" % json.dumps(nm))
            cs = cells(o["m"])
            self.assertEqual(len(cs), 5, cs)
            self.assertTrue(all(c[0] == "SHARED STASH" for c in cs), "%s copies left the war stash: %r" % (nm, cs))
            xy = sorted((int(a), int(b)) for a, b in (re.match(r"^shared:c(\d+)r(\d+)$", c[1]).groups() for c in cs))
            self.assertLessEqual(max(x for x, _ in xy) - min(x for x, _ in xy) + max(y for _, y in xy) - min(y for _, y in xy), 5,
                                 "%s copies are not grouped: %r" % (nm, xy))

    def test_big_war_gear_keeper_is_stable_and_copies_never_swap(self):
        roster_with([])
        T.add_all(["Andariel's Visage"] * 3)
        a = T.board().run(READ + "OUT.m = mv(/^Andariel.s Visage$/);")["m"]
        T.add_all(["Andariel's Visage"])
        b = T.board().run(READ + "window._movePackCache = null; window._warKeepBag = null; OUT.m = mv(/^Andariel.s Visage$/);")["m"]
        A = {m["c"]: (m["to"]["holder"], m["to"]["cell"]) for m in a}
        B = {m["c"]: (m["to"]["holder"], m["to"]["cell"]) for m in b}
        self.assertEqual(A[0][0], "SHARED STASH", A)
        self.assertTrue(all(A[c] == B[c] for c in A), "a copy moved or swapped after another add: %r -> %r" % (A, B))
        self.assertEqual(sum(1 for v in B.values() if v[0] == "SHARED STASH" and v[1]), 1, B)
        # REG-2803: with no WAR mule of his, the board makes WAR1 and the extra copies land on it
        self.assertTrue(all(v[0] == war_name(1) and v[1] for c, v in B.items() if c != 0), "an extra copy is not on the board's war mule 1: %r" % B)

    def test_renaming_a_war_mule_keeps_its_tasks_colour_and_place(self):
        """Elad 2026-10-20: mule names get renamed to character names later - routing, tasks, colour and place bind to the id"""
        roster_with(["WAR1"])
        T.add_all(["Andariel's Visage"] * 3)   # big war gear: 1 kept, 2 over the cap -> WAR1 (cheap, no page fill)
        q = (READ + "OUT.m = mv(/^Andariel.s Visage$/).filter(function(m){ return m.to && m.to.holder !== 'SHARED STASH'; })"
             ".map(function(m){ return [m.c, m.to.id, m.to.cell]; });"
             "OUT.rows = rows(/^Andariel.s Visage$/).filter(function(t){ return /overflow/.test(t); });"
             "var c = document.querySelector('.vault-mule[data-vault-mule=\"war-law-0\"]'); OUT.cls = c ? c.className : null;"
             "OUT.badge = c ? !!c.querySelector('.vm-warbadge') : null; OUT.order = c ? getComputedStyle(c).order : null;"
             "var sh = document.querySelector('.vault-mule.vm-shared'); OUT.sorder = sh ? getComputedStyle(sh).order : null;")
        a = T.board().run(q)
        T.board().run("window.prompt = function(){ return 'DEANSORC'; }; window.vaultRenameMule('war-law-0');"
                      "window._movePackCache = null; window._warKeepBag = null; if (window.renderVault) window.renderVault();")
        b = T.board().run(q)
        self.assertEqual(len(a["m"]), 2, a["m"])
        self.assertEqual(a["m"], b["m"], "a rename moved or dropped WAR1's copies: %r -> %r" % (a["m"], b["m"]))
        self.assertTrue(all(x[1] == "war-law-0" for x in b["m"]), b["m"])
        self.assertEqual(len(b["rows"]), 2, b["rows"])
        self.assertTrue(all("DEANSORC (SHARED STASH · overflow)" in t for t in b["rows"]), b["rows"])
        for o in (a, b):
            self.assertIn("vm-war", o["cls"] or "", "the WAR box lost the shared-stash colour: %r" % o["cls"])
            self.assertTrue(o["badge"])
            self.assertLess(int(o["sorder"]), int(o["order"]), "SHARED STASH is not above its WAR box")
            self.assertLess(int(o["order"]), 0, "the WAR box is not ahead of the other mules: %r" % o["order"])

    def _cap_case(self, wars, declined=None):
        roster_with(wars, declined)
        T.add_all([CAP_BELT] * 9 + ["The Stone of Jordan"] * 6)
        return T.board().run(READ + "OUT.m = mv(/^Arachnid Mesh$/); OUT.rows = rows(/^Arachnid Mesh$/); OUT.soj = mv(/^The Stone of Jordan$/);"
                             "OUT.line = ((document.querySelector('#vault-move-list .vmv-warfull') || {}).textContent || '');"
                             "OUT.roster = JSON.parse(window.LSR.getItem('d2r_muleRoster') || '[]').map(function(m){ return m.name; });"
                             "var _w1 = JSON.parse(window.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return window._vaultWarRole(m) === 1; })[0] || {};"
                             "var _w2 = JSON.parse(window.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return window._vaultWarRole(m) === 2; })[0] || {};"
                             "OUT.war2 = { id: _w2.id || null, name: _w2.name || null, auto: (_w2.auto || {}).by || null };"
                             "OUT.war1 = { id: _w1.id || null, auto: (_w1.auto || {}).by || null };"
                             "var ss = document.querySelector('.vault-mule[data-vault-mule=\"shared\"]'), w = _w1.id ? document.querySelector('.vault-mule[data-vault-mule=\"' + _w1.id + '\"]') : null;"
                             "function n(c){ return c ? c.querySelectorAll('.vm-cell[data-vault-item=\"Arachnid Mesh\"]').length : null; }"
                             "OUT.card = n(ss); OUT.wcard = n(w); OUT.sojcard = ss ? ss.querySelectorAll('.vm-cell[data-vault-item=\"The Stone of Jordan\"]').length : null;" + _MAKE)

    def test_nine_belts_keep_four_in_the_war_stash_and_five_go_to_war1(self):
        """Elad 2026-10-20 22:05 (live v3776: 9 Arachnid Mesh in the war stash, 'that cant happen'): rings and amulets
        keep every copy, any other small item at most 4, big gear 1; the rest go to WAR1, WAR2 ... each with its row."""
        o = self._cap_case(["WAR1"])
        by = [(m["c"], (m["to"] or {}).get("holder"), (m["to"] or {}).get("cell")) for m in o["m"]]
        self.assertEqual(len(by), 9, by)
        self.assertEqual(sum(1 for _, h, _c in by if h == "SHARED STASH"), 4, "not 4 belts in the war stash: %r" % by)
        self.assertEqual(sum(1 for _, h, c in by if h == "WAR1" and c), 5, "not 5 belts on WAR1: %r" % by)
        self.assertEqual(len(set((h, c) for _, h, c in by)), 9, "two belts share a cell: %r" % by)
        self.assertEqual(sum(1 for r in o["rows"] if "WAR1 (SHARED STASH · overflow)" in r), 5, "not 5 rows to WAR1: %r" % o["rows"])
        self.assertEqual(len(o["rows"]), 9, o["rows"])
        self.assertEqual(o["card"], 4, "the SHARED STASH card draws %r belts, not 4" % o["card"])
        self.assertEqual(o["wcard"], 5, "the WAR1 card draws %r belts, not 5" % o["wcard"])
        self.assertEqual(sum(1 for m in o["soj"] if (m["to"] or {}).get("holder") == "SHARED STASH"), 6, "6 rings must all stay: %r" % o["soj"])
        self.assertEqual(o["sojcard"], 6)
        self.assertEqual(o["line"], "", "no overflow line when WAR1 holds the extras: %r" % o["line"])

    def test_nine_belts_with_no_war_mule_the_board_makes_war1_and_tasks_him(self):
        """REG-2803 (his ruling 2026-10-28): 9 belts, no WAR mule - the war stash keeps 4, the board makes WAR1, the other 5
        land on it with their rows, and MOVE TASKS asks him first to create WAR1 in the game."""
        o = self._cap_case([])
        by = [(m["c"], (m["to"] or {}).get("holder"), (m["to"] or {}).get("cell")) for m in o["m"]]
        self.assertEqual(sum(1 for _, h, c in by if h == "SHARED STASH" and c), 4, by)
        w1 = war_name(1)
        self.assertEqual(sum(1 for _, h, c in by if h == w1 and c), 5, "the 5 extra belts are not on the board's war mule 1: %r" % by)
        self.assertFalse(any(h not in (w1, "SHARED STASH") for _, h, _c in by), "an extra went to a normal mule: %r" % by)
        self.assertEqual(len(o["rows"]), 9, "every copy keeps its own row: %r" % o["rows"])
        self.assertEqual(o["war1"]["auto"], "board", "WAR1 was not made by the board: %r" % o["war1"])
        self.assertEqual([x for x in o["roster"] if re.match(r"^war", str(x), re.I)], [w1], "not exactly one WAR mule: %r" % o["roster"])
        self.assertEqual(o["line"], "", "MOVE TASKS still says to make %s by hand: %r" % (w1, o["line"]))
        self.assertEqual(o["card"], 4)
        self.assertEqual(o["wcard"], 5, "the board's WAR1 card draws %r belts, not 5" % o["wcard"])
        self.assertTrue(war_makes(o, w1) and o["makeFirst"], o["make"])

    def test_a_war_mule_he_took_back_is_not_made_again_and_the_next_one_is(self):
        """REG-2803: a WAR mule he deleted is kept on the shared stash's entry - the board does not make it again.
        REG-2997 (his ruling 2026-10-29, Q2): the board makes the next one instead, the extras land on it, and MOVE TASKS
        asks him to make it in the game."""
        o = self._cap_case([], declined=["WAR1"])
        by = [(m["c"], (m["to"] or {}).get("holder"), (m["to"] or {}).get("cell")) for m in o["m"]]
        w2 = war_name(2)
        self.assertIsNone(o["war1"]["id"], "the board made the war mule 1 he took back: %r" % o["roster"])
        self.assertEqual((o["war2"]["name"], o["war2"]["auto"]), (w2, "board"), "the board did not make war mule 2: %r" % o["war2"])
        self.assertEqual([x for x in o["roster"] if re.match(r"^war", str(x), re.I)], [w2], "not exactly one WAR mule: %r" % o["roster"])
        self.assertEqual(sum(1 for _, h, c in by if h == "SHARED STASH" and c), 4, by)
        self.assertEqual(sum(1 for _, h, c in by if h == w2 and c), 5, "the 5 extra belts are not on war mule 2: %r" % by)
        self.assertEqual(o["line"], "", "MOVE TASKS still says the extras keep no cell: %r" % o["line"])
        self.assertTrue(war_makes(o, w2) and o["makeFirst"], o["make"])

    def test_the_cap_is_read_off_footprint_and_base_not_a_name_list(self):
        o = T.board().run("OUT.r = {}; ['The Stone of Jordan', 'Raven Frost', \"Mara's Kaleidoscope\", \"Highlord's Wrath\", 'Arachnid Mesh', \"Thundergod's Vigor\", 'Enigma', \"Andariel's Visage\", 'Demon Limb']"
                          ".forEach(function(n){ var c = window._vaultWarCap(n); OUT.r[n] = c === Infinity ? 'all' : c; });")
        for n in ("The Stone of Jordan", "Raven Frost", "Mara's Kaleidoscope", "Highlord's Wrath"):
            self.assertEqual(o["r"][n], "all", "%s (ring/amulet) must keep every copy: %r" % (n, o["r"]))
        for n in ("Arachnid Mesh", "Thundergod's Vigor"):
            self.assertEqual(o["r"][n], 4, "%s (belt) caps at 4: %r" % (n, o["r"]))
        for n in ("Enigma", "Andariel's Visage", "Demon Limb"):
            self.assertEqual(o["r"][n], 1, "%s (big) caps at 1: %r" % (n, o["r"]))

    def test_distinct_attacks_clear_the_vault_apply_wilson_bar(self):
        from confidence import wilson_lower
        import self_arming as SA
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        print("vault L1 war stash: %d distinct attacks, wilson %.4f vs bar %.3f" % (n, w, SA.LOCKS["vault.apply"]["bar"]))
        self.assertGreaterEqual(w, SA.LOCKS["vault.apply"]["bar"])


RED_PROOF = [
    {"why": "A hand add of a name he owns is 'already yours - nothing changed' again: the 2nd copy vanishes.",
     "file": "bible.html", "find": "      if (!(opts && opts.by) && typeof copies !== 'undefined' && copies) {",
     "replace": "      if (false) {", "matches": 1},
    {"why": "The hand copy gets no move row of its own.",
     "file": "bible.html", "find": "if (typeof _vaultMoveNoteAdded === 'function') _cMv = _vaultMoveNoteAdded(pre.name, _cN - 1); } catch (eMc) {} /* L1 hand copy row */",
     "replace": "} catch (eMc) {} /* L1 hand copy row */", "matches": 1},
    {"why": "Every copy's row is written onto copy 0, so copies collapse to one row.",
     "file": "bible.html", "find": "    var wrote = _vaultMoveCommit([{ name: nm, copyIx: copyIx, task: hand }]); /* v3773 manual row */",
     "replace": "    var wrote = _vaultMoveCommit([{ name: nm, copyIx: 0, task: hand }]); /* v3773 manual row */", "matches": 1},
    # REG-2935 - BLIND since REG-2786 (v3830): the hand door raises the target in TWO places - the set-piece line and
    # REG-2786's "any name counted from its cells" line - and the second covers a set piece too (its presence span is 1
    # with no target), so breaking the first alone changed nothing the law can see. The property is that his typed
    # spare is kept, so the proof breaks both raises.
    {"why": "A set piece typed twice stays one presence item: the spare he typed is dropped (both target raises gone).",
     "file": "bible.html", "find": '&& !(_mkWant(pre.name) >= _cN)) _mkSetWant(pre.name, _cN); } catch (eMk) {} /* L1 hand set copy */\n        /* REG-2786 (#111) - THE SAME ASK FOR ANY NAME THE VAULT COUNTS FROM ITS CELLS. Once a look names a cell the count is\n           the distinct cells (v3767), so a copy typed past them answered "x5 - another copy, its own row and cell" and drew\n           nothing: measured, Griswold\'s Edge seen in 3 cells and typed twice more read 3 on the card, the mule card and the\n           records. The target follows his hand only when the count would not hold the copy he typed. */\n        try { if (typeof multiKeep !== \'undefined\' && multiKeep && !(_mkWant(pre.name) >= _cN) && typeof window._vaultPresenceSpan === \'function\'\n                  && window._vaultPresenceSpan(pre.name, _cN) < _cN) _mkSetWant(pre.name, _cN); } catch (eMkC) {} /* REG-2786 hand copy past the cells */',
     "replace": '&& !(_mkWant(pre.name) >= _cN)) void 0; } catch (eMk) {} /* L1 hand set copy */\n        /* REG-2786 (#111) - THE SAME ASK FOR ANY NAME THE VAULT COUNTS FROM ITS CELLS. Once a look names a cell the count is\n           the distinct cells (v3767), so a copy typed past them answered "x5 - another copy, its own row and cell" and drew\n           nothing: measured, Griswold\'s Edge seen in 3 cells and typed twice more read 3 on the card, the mule card and the\n           records. The target follows his hand only when the count would not hold the copy he typed. */\n        try { if (typeof multiKeep !== \'undefined\' && multiKeep && !(_mkWant(pre.name) >= _cN) && typeof window._vaultPresenceSpan === \'function\'\n                  && window._vaultPresenceSpan(pre.name, _cN) < _cN) void 0; } catch (eMkC) {} /* REG-2786 hand copy past the cells */', "matches": 1},
    {"why": "The war stash is one page again.",
     "file": "bible.html", "find": "      var left = items.filter(function(it){ return !it.over; }), SHARED_TABS = 5;",
     "replace": "      var left = items.filter(function(it){ return !it.over; }), SHARED_TABS = 1;", "matches": 1},
    {"why": "Every page packs over page 1's cells (the page offset is lost).",
     "file": "bible.html", "find": "cell: 'shared:c' + q.x + 'r' + (q.y + pg * 10) }; });",
     "replace": "cell: 'shared:c' + q.x + 'r' + q.y }; });", "matches": 1},
    {"why": "Overflow never reaches a WAR mule.",
     "file": "bible.html", "find": "      var wars = (typeof _vaultWarMules === 'function') ? _vaultWarMules() : [];",
     "replace": "      var wars = [];", "matches": 1},
    {"why": "REG-2970 - a WAR mule is no longer recognised by its STORED role (REG-2804), so the seeded war1 takes no overflow (re-aimed: REG-2968 seeds the law's war mules by role, so the old name-regex proof changed nothing - BLIND on the v3836 push)",
     "file": "bible.html", "find": "    if (m.role === 'war') return +m.warN || 1;\n",
     "replace": '    if (false) return +m.warN || 1;\n', "matches": 1},
    {"why": "A rename drops the WAR role: the renamed mule stops being the overflow.",
     "file": "bible.html", "find": "    if (m.role === 'war') return +m.warN || 1;",
     "replace": "", "matches": 1},
    {"why": "A target binds to the display name again, so a rename orphans the task.",
     "file": "bible.html", "find": "    if (id != null) pl.id = id; /* L1 a target binds to the mule's stable id */",
     "replace": "", "matches": 1},
    {"why": "The WAR box loses the Shared Stash colour and place.",
     "file": "bible.html", "find": "+((window._vaultWarRole&&window._vaultWarRole(m))?' vm-war':'')",
     "replace": "", "matches": 1},
    {"why": "WAR mules fill in roster order, not WAR1 then WAR2.",
     "file": "bible.html", "find": "    return r.sort(function(a, b){ return a.n - b.n || (a.name < b.name ? -1 : 1); });",
     "replace": "    return r.reverse();", "matches": 1},
    {"why": "Demon Limb (Enchant charges) goes back to a mule.",
     "file": "bible.html", "find": "    'demon limb': 'enchant charges - utility charge flail',\n",
     "replace": "", "matches": 1},
    {"why": "Metamorphosis (Mark of Bear/Wolf) goes back to the runewords mule.",
     "file": "bible.html", "find": "    'metamorphosis': 'mark of the bear / wolf on striking - utility proc helm',\n",
     "replace": "", "matches": 1},
    {"why": "Treachery (Fade) goes back to the runewords mule.",
     "file": "bible.html", "find": "    'treachery': 'fade on striking - utility proc armour',\n",
     "replace": "", "matches": 1},
    {"why": "Guillaume's Face falls back to SETS-REST (the keep-set rule wins over war gear).",
     "file": "bible.html", "find": "    \"guillaume's face\": 'crushing blow + deadly strike helm - war set piece'\n",
     "replace": "    \"guillaume_x\": 'x'\n", "matches": 1},
    {"why": "A full war stash says nothing.",
     "file": "bible.html", "find": "    if (_wf.length) unrHtml += '<p class=\"vmv-warfull\"",
     "replace": "    if (false) unrHtml += '<p class=\"vmv-warfull\"", "matches": 1},
    {"why": "The tab and in-page row are not read off the shared cell.",
     "file": "bible.html", "find": "        return h + ' · ' + _sharedSpotSay(Math.floor((+m[2]) / 10), +m[1], (+m[2]) % 10);   /* REG-3005 the one spelling */",
     "replace": "        return h + ' (' + ((+m[1]) + 1) + ',' + ((+m[2]) + 1) + ')';", "matches": 1},
    {"why": "Every copy of a war item stays in the war stash again: 9 belts, 7 Enigmas (Elad 22:05 'that cant happen').",
     "file": "bible.html", "find": "      return _vaultWarOver(name, copyIx) ? { id: 'shared', holder: 'SHARED STASH', location: 'shared', over: true }",
     "replace": "      return false ? { id: 'shared', holder: 'SHARED STASH', location: 'shared', over: true }", "matches": 1},
    {"why": "Small war gear (belts) is cut to one copy too.",
     "file": "bible.html", "find": "    if ((s[0] || 1) * (s[1] || 1) <= 2) return true;",
     "replace": "    if (false) return true;", "matches": 1},
    {"why": "Belts and charms keep every copy like rings (no cap of 4).",
     "file": "bible.html", "find": "  var _WAR_SMALL_CAP = 4;", "replace": "  var _WAR_SMALL_CAP = Infinity;", "matches": 1},
    {"why": "Rings and amulets get capped at 4 like belts.",
     "file": "bible.html", "find": "    if (area === 1 && /\\b(ring|amulet)\\b/i.test(base)) return Infinity;", "replace": "", "matches": 1},
    {"why": "Over-cap copies fill the 5 war-stash pages instead of going to WAR1.",
     "file": "bible.html", "find": "      var left = items.filter(function(it){ return !it.over; }), SHARED_TABS = 5;",
     "replace": "      var left = items, SHARED_TABS = 5; overIt = [];", "matches": 1},
    {"why": "Over-cap copies route to the item's normal mule (Elad 22:10: they go to the WAR mules).",
     "file": "bible.html", "find": "    var _xw = null; /* L1 over-cap copies stay war-stash homed */",
     "replace": "      var _xw = (seam && seam.loc === 'shared') ? _vaultWarExtra(name, copyIx) : null; if (_xw) seam = _xw;", "matches": 1},
    {"why": "The SHARED STASH card draws every owned copy again (the 9 belts in his shot).",
     "file": "bible.html", "find": "var _cap = window._vaultWarCap(n); if (c > _cap) c = _cap;", "replace": "var _cap = 0;", "matches": 1},
    {"why": "The WAR mule card does not show the copies planned on it.",
     "file": "bible.html", "find": "if (_wOn) Object.keys(_wOn).forEach(function(n){ if (items.indexOf(n) < 0) items.push(n); });",
     "replace": "", "matches": 1},
    {"why": "The kept copies are not the first-witnessed ones (keeper order lost).",
     "file": "bible.html", "find": "    for (var j = 0; j < cc && out.length < cap; j++) if (out.indexOf(j) < 0) out.push(j);",
     "replace": "    for (var j = cc - 1; j >= 0 && out.length < cap; j--) if (out.indexOf(j) < 0) out.push(j);", "matches": 1},
    {"why": "The keeper is not the first-witnessed copy (the last one stays instead).",
     "file": "bible.html", "find": "    return best == null ? 0 : best; /* L1 else the first-witnessed copy */",
     "replace": "    return best == null ? 99 : best; /* L1 else the first-witnessed copy */", "matches": 1},
    {"why": "A WAR mule row does not say it is the Shared Stash overflow.",
     "file": "bible.html", "find": "      if (_pm && _vaultWarRole(_pm)) h = h + ' (SHARED STASH · overflow)'; /* L1 a WAR mule reads as the war stash; REG-2804 by its role, never its name */",
     "replace": "", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
