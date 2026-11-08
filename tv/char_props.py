# -*- coding: utf-8 -*-
"""#174 v-B2 — THE CHARACTER SHEET'S PROPERTY DATA, FROM HIS OWN INSTALL, WRITTEN INTO THE CHARACTER BUILDER.

HIS ORDER, 2026-09-25 ~18:25: *"link the data to the character like physical damage percentage and fire absorb cold
absorb magic dmg % add all the information and data based on the items buffs that it gives it should calculate the
total sum of it all correctly. based on HELL and its data like the resistances starting with -100%"*.

The board's item knowledge was TEXT (ITEM_CODEX prose). A sum needs DATA: which property an item carries, its par /
min / max, which stat that property feeds, how a per-level stat scales, what the difficulty takes away. The game
holds every one of those facts in its own excel tables, so this file pulls them from the CASC of the install on
this machine and writes one compact block into bible.html between two markers, where `window.D2R_CHAR_ENGINE`
(the engine in the same script element) reads it:

    uniqueitems.txt / setitems.txt   each item's prop1..12 with par / min / max, its base code and level
    sets.txt                          partial (2..5 worn) and full-set bonuses
    runes.txt                         each runeword's T1Code1..7 and the runes it is made of (Rune1..6)
    gems.txt                          what a rune or gem adds in a weapon / a helm or armour / a shield
    properties.txt                    property code -> (func, stat, val): res-all feeds FOUR stats, cast2 feeds one
    itemstatcost.txt                  how a per-level stat scales (op base = level, op param = the shift) and the
                                      game's own description string for a stat (used as a row's label)
    difficultylevels.txt              ResistPenalty per difficulty (MEASURED: Normal 0 · Nightmare -40 · Hell -100)
    armor / weapons / misc .txt       a base's defense range, max sockets, level requirement; itemtypes.txt says
                                      whether a rune in it counts as a weapon, a helm/armour or a shield
    skills / skilldesc / charstats    skill id -> name and class; each class's own "+N to <tab> Skills" strings
    magicprefix / magicsuffix /       WHICH property codes a magic / rare / crafted affix may put on an item of a type
      automagic                       (itype / etype through the Equiv chain): the engine makes only those stats
                                      UNKNOWN for an item whose affixes nobody typed - a Small Charm can never roll
                                      Faster Cast Rate, so it must never blank the FCR row (#174 v-B2 fix round)
                                      #174 v-B3: and each spawnable row ITSELF (affixRows, id = p/s/a + row index),
                                      so an item whose affixes he PICKED in the builder's ADD MOD sums them like a
                                      unique's props - typed EXACT, untouched RANGE, never averaged
    qualityitems                      a superior item's modifiers (affixRows q + row index)
    item-names / item-runes / item-modifiers / skills .json   what the game PRINTS (a table key is not a name)
    item-nameaffixes .json            an affix row's printed name ("Vodoun" prints "Mojo") - #174 v-B3 fix round

    python3 tv/char_props.py            # --check: is the block in bible.html what the install says?
    python3 tv/char_props.py --write    # regenerate the block (atomic, honours bible.html.EDIT_LOCK)

    exit 0 fresh · 1 STALE (the install or the generator moved; run --write) · 77 CANNOT TELL (no install here)

⚠ 77 IS NOT GREEN. A CI runner has no game install, so there the block's freshness is UNKNOWN, never "fine".
What CI CAN check without an install is in tv/test_the_character_sheet_sums_the_game_data.py: the engine is
driven on the SHIPPED block with sums worked by hand from these tables, and the block's unique / set names are
compared against tv/item_tables.json, which a DIFFERENT generator wrote from the same install.

⚠ THE PULL IS affix_lexicon._pull, NEVER WRAPPED IN `perl -e 'alarm N; exec'` — /usr/bin/perl is SIP-restricted,
dyld strips DYLD_FRAMEWORK_PATH across that exec, and the extractor then fails exactly like a missing toolchain.

⚠ WHAT IS NOT IN THE EXCEL TABLES AND IS THEREFORE NOT HERE: Anya's resistance scroll (+10 all resistances per
difficulty completed) is a quest REWARD, hard-coded in the game, not a row in any table. The engine applies it as
a stated rule and names it as such in every row it touches. [[unknown-stays-unknown]] [[copy-drift]]
"""
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe
    _console_safe()
except Exception:
    pass                      # console encoding only; a failure here changes no fact the block holds

SKIP = 77
BIBLE = os.path.join(ROOT, "bible.html")
LOCK = BIBLE + ".EDIT_LOCK"
MARK_OPEN = "/* CHAR_PROPS:BEGIN */"
MARK_CLOSE = "/* CHAR_PROPS:END */"
VAR = "var _CE_DATA = "

#: (label, CASC path). ORDER IS FIXED — sourceHash is computed over it.
SOURCES = [
    ("uniqueitems",      r"data:data\global\excel\uniqueitems.txt"),
    ("setitems",         r"data:data\global\excel\setitems.txt"),
    ("sets",             r"data:data\global\excel\sets.txt"),
    ("runes",            r"data:data\global\excel\runes.txt"),
    ("gems",             r"data:data\global\excel\gems.txt"),
    ("properties",       r"data:data\global\excel\properties.txt"),
    ("itemstatcost",     r"data:data\global\excel\itemstatcost.txt"),
    ("difficultylevels", r"data:data\global\excel\difficultylevels.txt"),
    ("armor",            r"data:data\global\excel\armor.txt"),
    ("weapons",          r"data:data\global\excel\weapons.txt"),
    ("misc",             r"data:data\global\excel\misc.txt"),
    ("itemtypes",        r"data:data\global\excel\itemtypes.txt"),
    ("skills",           r"data:data\global\excel\skills.txt"),
    ("skilldesc",        r"data:data\global\excel\skilldesc.txt"),
    ("charstats",        r"data:data\global\excel\charstats.txt"),
    ("magicprefix",      r"data:data\global\excel\magicprefix.txt"),
    ("magicsuffix",      r"data:data\global\excel\magicsuffix.txt"),
    ("automagic",        r"data:data\global\excel\automagic.txt"),
    ("itemnames",        r"data:data\local\lng\strings\item-names.json"),
    ("itemrunes",        r"data:data\local\lng\strings\item-runes.json"),
    ("itemmodifiers",    r"data:data\local\lng\strings\item-modifiers.json"),
    ("skillstrings",     r"data:data\local\lng\strings\skills.json"),
    # #174 v-B3 - APPENDED (the order is the sourceHash's): a superior item's modifiers
    ("qualityitems",     r"data:data\global\excel\qualityitems.txt"),
    # #174 v-B3 fix round - APPENDED: what the game PRINTS for an affix (magicprefix "Vodoun" is "Mojo"), so a sheet
    # row names the affix the item shows - the same string the builder names it by (tv/char_builder_db.py)
    ("nameaffixes",      r"data:data\local\lng\strings\item-nameaffixes.json"),
    # #166 (REG-1868) - APPENDED: RotW's property GROUPS. A code a unique carries that properties.txt does not have
    # ("Breaching-Affix1") is a row here: its properties, each with its range and Chance, and a PickMode
    ("propertygroups",   r"data:data\global\excel\propertygroups.txt"),
]
STRINGS = ("itemnames", "itemrunes", "itemmodifiers", "skillstrings", "nameaffixes")

#: the three funcs whose par names a SKILL (properties.txt: 11 event skill, 19 charges, 22 single / o- / aura skill)
SKILL_FUNCS = (11, 19, 22)


def _pull(casc_path):
    """-> bytes or None. ⚠ NEVER wrap this in `perl -e 'alarm N; exec'` — see affix_lexicon._pull."""
    import affix_lexicon
    return affix_lexicon._pull(casc_path)


def _rows(blob):
    """A tab-separated excel table -> [dict per row], header row as keys. None if nothing arrived."""
    import item_tables as IT
    return IT._rows(blob)


def _strings(blob):
    """item-*.json [{Key, enUS}] -> {Key: enUS}; None when absent OR unparseable (never {})."""
    import item_tables as IT
    return IT._strings(blob)


def _num(s):
    """'20' -> 20 · '-5' -> -5 · '' -> None. A blank min/max is ABSENT, never 0."""
    s = str(s if s is not None else "").strip()
    if s.lstrip("-").isdigit():
        return int(s)
    return None


def _line(code, par, lo, hi):
    """One property line exactly as the table has it: [code, par, min, max] (par a string, min/max int or None)."""
    return [code, str(par or "").strip(), _num(lo), _num(hi)]


def source_hash(blobs):
    """sha256 over every source's path and content hash, in SOURCES order (an absent one hashes as <ABSENT>)."""
    h = hashlib.sha256()
    for label, path in SOURCES:
        b = blobs.get(label)
        h.update(path.encode("utf-8"))
        h.update(b"\x00")
        h.update(hashlib.sha256(b if b is not None else b"<ABSENT>").hexdigest().encode("ascii"))
    return h.hexdigest()


def assemble(blobs):
    """-> (data dict, None) or (None, why). PURE: every fact from `blobs` ({label: bytes|None}); writes nothing."""
    absent = [label for label, _ in SOURCES if blobs.get(label) is None]
    if absent:
        return None, ("could not pull %s from the install — the character sheet's property data is UNKNOWN "
                      "here, not empty" % ", ".join(absent))
    T = {}
    for label, _ in SOURCES:
        if label in STRINGS:
            T[label] = _strings(blobs[label])
        else:
            T[label] = _rows(blobs[label])
        if not T[label]:
            return None, "%s was pulled but would not parse — a corrupt source is not an empty one" % label
    names, runes_s, mods, sk_s = T["itemnames"], T["itemrunes"], T["itemmodifiers"], T["skillstrings"]

    def shown(key, fallback=None):
        return names.get(key) or runes_s.get(key) or fallback or key

    # ── properties.txt: code -> [[func, stat, val], ...] (func-less rows carry nothing and are left out)
    props = {}
    for r in T["properties"]:
        code = r.get("code") or ""
        fs = []
        for i in range(1, 8):
            f = _num(r.get("func%d" % i))
            if f is None:
                continue
            fs.append([f, r.get("stat%d" % i) or "", _num(r.get("val%d" % i))])
        if code and fs:
            props[code] = fs

    # ── itemstatcost.txt: per-level scaling (op base = level) and each stat's own description string
    perlvl, fmt, fmtg = {}, {}, {}
    for r in T["itemstatcost"]:
        st = r.get("Stat") or ""
        if not st:
            continue
        if (r.get("op base") or "") == "level" and r.get("op stat1"):
            perlvl[st] = [r["op stat1"], _num(r.get("op param")) or 0, _num(r.get("op")) or 0]
        s = mods.get(r.get("descstrpos") or "")
        if s:
            fmt[st] = s
        g = mods.get(r.get("dgrpstrpos") or "") if (r.get("dgrp") or "").strip() else None
        if g:
            fmtg[st] = g

    # ── difficultylevels.txt: ResistPenalty (the expansion column), in the table's own order
    diff = []
    for r in T["difficultylevels"]:
        p = _num(r.get("ResistPenalty"))
        if r.get("Name") and p is not None:
            diff.append([r["Name"], p])
    if len(diff) != 3:
        return None, "difficultylevels.txt names %d difficulties with a ResistPenalty, not 3 — refusing to guess" % len(diff)

    # ── classes: id order is properties.txt's own (func 21 on item_addclassskills carries the class id in `val`)
    cls_code = {}
    for code, fs in props.items():
        for f, st, val in fs:
            if f == 21 and st == "item_addclassskills" and val is not None and len(code) == 3:
                cls_code[val] = code
    cs_rows = [r for r in T["charstats"] if r.get("class") and r.get("StrAllSkills")]
    if not cls_code or len(cs_rows) != len(cls_code):
        return None, ("charstats.txt names %d classes and properties.txt %d class-skill codes — refusing to pair "
                      "them by guess" % (len(cs_rows), len(cls_code)))
    classes = []
    for cid, r in enumerate(cs_rows):
        if cid not in cls_code:
            return None, "no class-skill property carries class id %d (%s)" % (cid, r.get("class"))
        classes.append([cls_code[cid], r["class"], mods.get(r.get("StrAllSkills") or "") or "",
                        mods.get(r.get("StrClassOnly") or "") or "",
                        [mods.get(r.get("StrSkillTab%d" % p) or "") or "" for p in (1, 2, 3)],
                        # [5] v3886 (#141) - APPENDED: charstats.txt `BlockFactor`, the class's own block bonus a shield
                        # adds to (Paladin 30, Amazon / Assassin / Barbarian 25, Druid / Necromancer / Sorceress 20)
                        _num(r.get("BlockFactor"))])
    cid_of = dict((c[0], i) for i, c in enumerate(classes))

    # ── itemtypes.txt: every ancestor of a type through Equiv1/Equiv2
    types = dict((r.get("Code"), r) for r in T["itemtypes"] if r.get("Code"))

    def anc(code, seen=None):
        seen = set() if seen is None else seen
        if not code or code in seen or code not in types:
            return seen
        seen.add(code)
        for e in (types[code].get("Equiv1"), types[code].get("Equiv2")):
            anc(e, seen)
        return seen

    def walk_class(code, seen=()):
        """itemtypes.txt `Class` through the Equiv chain: the class that alone may use a type ('' = anyone)"""
        r = types.get(code)
        if not r or code in seen:
            return ""
        if r.get("Class"):
            return r["Class"]
        for e in (r.get("Equiv1"), r.get("Equiv2")):
            v = walk_class(e, seen + (code,)) if e else ""
            if v:
                return v
        return ""

    # ── bases: code -> [name, host (w weapon · h helm/armour · s shield · '' neither), minac, maxac, maxsock, type,
    #    charm 0/1, levelreq, class]. The host decides which of a rune's three mods applies (gems.txt weapon/helm/
    #    shield); the class (itemtypes.txt Class: 'pal' for an Auric Shield, 'bar' for a Primal Helm, '' for anyone) is
    #    who may wear it - a Sorceress in Herald of Zakarum sums nothing the game would let her wear.
    bases, misc_codes = {}, set()
    for label in ("armor", "weapons", "misc"):
        for r in T[label]:
            code = r.get("code") or ""
            if not code:
                continue
            if label == "misc":
                misc_codes.add(code)
            a = anc(r.get("type") or "")
            host = "s" if "shld" in a else ("w" if "weap" in a else ("h" if "armo" in a else ""))
            bases[code] = [shown(r.get("namestr") or code, r.get("name")), host,
                           _num(r.get("minac")) or 0, _num(r.get("maxac")) or 0, _num(r.get("gemsockets")) or 0,
                           r.get("type") or "", 1 if "char" in a else 0, _num(r.get("levelreq")) or 0,
                           walk_class(r.get("type") or ""),
                           # [9] v3886 (#141) - APPENDED: armor.txt `block`, a shield's base chance to block (Sacred Targe 30)
                           _num(r.get("block")) or 0]

    # ── skills: id -> [display name, class id or -1, table key]; only the ones an item line names are kept (an item
    #    names a skill by id — "54" — or by its KEY — "Battle Command" — so both must resolve on the page)
    sd = dict((r.get("skilldesc"), r) for r in T["skilldesc"] if r.get("skilldesc"))
    sk_by_id, sk_by_key = {}, {}
    for i, r in enumerate(T["skills"]):
        key = r.get("skill") or ""
        if not key:
            continue
        sid = _num(r.get("*Id"))
        sid = i if sid is None else sid
        d = sd.get(r.get("skilldesc") or "")
        nm = (sk_s.get(d.get("str name") or "") if d else None) or key
        cid = cid_of.get(r.get("charclass") or "", -1)
        sk_by_id[str(sid)] = [nm, cid, key]
        sk_by_key.setdefault(key.lower(), sid)
    used_skills = {}

    def note_skill(code, par):
        fs = props.get(code) or []
        if not any(f in SKILL_FUNCS for f, _, _ in fs) or not par:
            return
        sid = str(par) if str(par).isdigit() else (str(sk_by_key[par.lower()]) if par.lower() in sk_by_key else None)
        if sid is not None and sid in sk_by_id:
            used_skills[sid] = sk_by_id[sid]

    def lines_of(r, n, pfx="prop", ppar="par", pmin="min", pmax="max", base=None):
        out = []
        # v3859 - THE GAME CAPS A SOCKET ROLL AT THE BASE. uniqueitems/setitems ask Aldur's Rhythm for 2-5 sockets on a
        # Jagged Star (max 3) and Heaven's Light for 1-3 on a Mighty Scepter (max 2); GrokBot clamped those two rows in
        # bible.html by hand (test_a_socket_range_fits_its_base), and this generator - which never knew the cap - then
        # read the block as hand-edited (the Mac's pre-push, 2026-11-04). The cap lives HERE, where the block is made.
        cap = (bases.get(base) or [None] * 5)[4] if base else 0
        for i in range(1, n + 1):
            c = (r.get("%s%d" % (pfx, i)) or "").strip()
            if not c:
                continue
            ln = _line(c, r.get("%s%d" % (ppar, i)), r.get("%s%d" % (pmin, i)), r.get("%s%d" % (pmax, i)))
            if ln[0] == "sock" and cap and isinstance(ln[3], int) and isinstance(ln[2], int) and ln[3] > cap:
                ln = [ln[0], ln[1], min(ln[2], cap), cap] + list(ln[4:])
            # v3861 - AND A FIXED COUNT IN par. MEASURED on the shipped block: Blade of Ali Baba carries sock par '3' on a
            # Tulwar (max 2) with no min/max, which the range rule above never saw; the page's display door
            # (_cbSockCapLine, REG-3071) was the only thing between that 3 and his screen.
            elif (ln[0] == "sock" and cap and ln[2] is None and ln[3] is None and str(ln[1]).isdigit()
                  and int(ln[1]) > cap):
                ln = [ln[0], str(cap), None, None] + list(ln[4:])
            note_skill(ln[0], ln[1])
            out.append(ln)
        return out

    uniques = []
    for r in T["uniqueitems"]:
        code = r.get("code") or ""
        if not code or not str(r.get("*ID") or "").isdigit():
            continue
        uniques.append([shown(r.get("index")), r.get("index") or "", int(r["*ID"]), code, _num(r.get("lvl req")) or 0,
                        1 if r.get("spawnable") == "1" else 0, lines_of(r, 12, base=code)])

    setnames = dict((r.get("index"), shown(r.get("name") or r.get("index"))) for r in T["sets"] if r.get("index"))
    sets = []
    set_count = {}
    for r in T["setitems"]:
        code = r.get("item") or ""
        if not code or not str(r.get("*ID") or "").isdigit():
            continue
        sk = r.get("set") or ""
        set_count[sk] = set_count.get(sk, 0) + 1
        al = []
        for i in range(1, 6):
            for s in ("a", "b"):
                c = (r.get("aprop%d%s" % (i, s)) or "").strip()
                if c:
                    ln = _line(c, r.get("apar%d%s" % (i, s)), r.get("amin%d%s" % (i, s)), r.get("amax%d%s" % (i, s)))
                    note_skill(ln[0], ln[1])
                    al.append([i + 1] + ln)
        sets.append([shown(r.get("index")), r.get("index") or "", int(r["*ID"]), code, _num(r.get("lvl req")) or 0,
                     setnames.get(sk) or shown(sk), _num(r.get("add func")) or 0, lines_of(r, 9, base=code), al])

    set_bonus = {}
    for r in T["sets"]:
        sk = r.get("index") or ""
        if not sk:
            continue
        part = []
        for n in range(2, 6):
            for s in ("a", "b"):
                c = (r.get("PCode%d%s" % (n, s)) or "").strip()
                if c:
                    ln = _line(c, r.get("PParam%d%s" % (n, s)), r.get("PMin%d%s" % (n, s)), r.get("PMax%d%s" % (n, s)))
                    note_skill(ln[0], ln[1])
                    part.append([n] + ln)
        full = lines_of(r, 8, "FCode", "FParam", "FMin", "FMax")
        set_bonus[setnames.get(sk) or shown(sk)] = [set_count.get(sk, 0), part, full]

    runewords = []
    for r in T["runes"]:
        if r.get("complete") != "1" or not r.get("Name"):
            continue
        rs = [r.get("Rune%d" % i) for i in range(1, 7) if r.get("Rune%d" % i)]
        runewords.append([shown(r["Name"], r.get("*Rune Name")), r["Name"], rs, lines_of(r, 7, "T1Code", "T1Param", "T1Min", "T1Max")])

    gems = {}
    for r in T["gems"]:
        code = r.get("code") or ""
        if not code:
            continue
        # [weapon mods, helm/armour mods, shield mods] — gems.txt names its columns <t>Mod<i>Code/Param/Min/Max
        gems[code] = [[_line(r.get("%sMod%dCode" % (t, i)).strip(), r.get("%sMod%dParam" % (t, i)),
                             r.get("%sMod%dMin" % (t, i)), r.get("%sMod%dMax" % (t, i)))
                       for i in (1, 2, 3) if (r.get("%sMod%dCode" % (t, i)) or "").strip()]
                      for t in ("weapon", "helm", "shield")]

    # only the description strings of stats some property can feed — the rest would be dead weight in the page.
    # funcs 5 / 6 / 7 (dmg-min, dmg-max, dmg%) name no stat in properties.txt; the game prints them through
    # mindamage / maxdamage / damagepercent, so those three are the stats the engine files them under.
    fed = (set(st for fs in props.values() for _, st, _ in fs if st) | set(v[0] for v in perlvl.values())
           | {"mindamage", "maxdamage", "damagepercent"})
    fmt = dict((k, v) for k, v in fmt.items() if k in fed)
    fmtg = dict((k, v) for k, v in fmtg.items() if k in fed)

    # a misc base (potion, key, scroll...) is kept only when something the sheet can hold names it: a unique or
    # set piece built on it, a rune or gem that sits in a socket, a charm, a jewel. The page never needs the rest.
    named_codes = set(u[3] for u in uniques) | set(x[3] for x in sets) | set(gems)
    bases = dict((c, b) for c, b in bases.items()
                 if c not in misc_codes or c in named_codes or b[6] or b[5] == "jewl")

    # ── the affix POOL of an item type: every property code a spawnable magicprefix / magicsuffix / automagic row may
    #    put on it (the type or an ancestor in itype1..7, none in etype1..5). INCLUSIVE on purpose - frequency and
    #    version are not filtered, so the pool can only over-state what an untyped affix may touch, never hide a stat.
    pool = {}
    btypes = set(b[5] for b in bases.values() if b[5])
    for t in sorted(btypes):
        a = anc(t)
        codes = set()
        for label in ("magicprefix", "magicsuffix", "automagic"):
            for r in T[label]:
                if r.get("spawnable") != "1":
                    continue
                it = [r.get("itype%d" % i) for i in range(1, 8) if r.get("itype%d" % i)]
                et = [r.get("etype%d" % i) for i in range(1, 6) if r.get("etype%d" % i)]
                if not any(x in a for x in it) or any(x in a for x in et):
                    continue
                for k in (1, 2, 3):
                    c = (r.get("mod%dcode" % k) or "").strip()
                    if c:
                        codes.add(c)
        if codes:
            pool[t] = sorted(codes)

    # ── #174 v-B3 - THE AFFIX ROWS THEMSELVES, so a magic / rare / superior item whose affixes he PICKED in the builder
    #    sums them exactly like a unique's props: id -> [the table's Name, [[roll key, code, par, min, max], ...]].
    #    id = p / s / a / q + the row's index in magicprefix / magicsuffix / automagic / qualityitems (the same id
    #    tv/char_builder_db.py writes into the builder's af rows); the roll key is the mod's column (m1..m3), the key
    #    the builder stores a typed roll under. Spawnable rows only - the game never rolls the rest.
    #    #174 v-B3 fix round - the NAME is what the game prints (item-nameaffixes.json, then the item strings), never
    #    the table's key: 116 rows read "Mojo Amulet (Vodoun)" on the sheet while the item said "Mojo Amulet".
    naff = T["nameaffixes"]
    rows_of = {}
    for label, kind in (("magicprefix", "p"), ("magicsuffix", "s"), ("automagic", "a"), ("qualityitems", "q")):
        for i, r in enumerate(T[label]):
            if kind != "q" and r.get("spawnable") != "1":
                continue
            ls = []
            for k in (1, 2, 3):
                c = (r.get("mod%dcode" % k) or "").strip()
                if c:
                    ln = _line(c, r.get("mod%dparam" % k), r.get("mod%dmin" % k), r.get("mod%dmax" % k))
                    note_skill(ln[0], ln[1])
                    ls.append(["m%d" % k] + ln)
            if ls:
                nk = (r.get("Name") or "").strip()
                rows_of[kind + str(i)] = [(naff.get(nk) or names.get(nk) or nk) if nk else ("superior" if kind == "q" else ""), ls]

    # #166 (REG-1868) - propertygroups.txt: code -> [PickMode, [[prop, par, min, max, Chance], ...]]. A row whose
    # parameter is a RANGE (ParMin != ParMax) keeps par None: which parameter rolls is not in the tables
    pgroups = {}
    for r in T["propertygroups"]:
        code = (r.get("code") or "").strip()
        if not code:
            continue
        opts = []
        for i in range(1, 9):
            pc = (r.get("Prop%d" % i) or "").strip()
            if not pc:
                continue
            pmin, pmax = (r.get("ParMin%d" % i) or "").strip(), (r.get("ParMax%d" % i) or "").strip()
            ln = _line(pc, pmin if pmin == pmax else "", r.get("ModMin%d" % i), r.get("ModMax%d" % i))
            if pmin != pmax:
                ln[1] = None
            note_skill(ln[0], ln[1])
            opts.append(ln + [_num(r.get("Chance%d" % i))] + ([[pmin, pmax]] if pmin != pmax else []))
        pgroups[code] = [_num(r.get("PickMode")), opts]

    return {
        "sourceHash": source_hash(blobs),
        "affix": pool,
        "pgroups": pgroups,
        "affixRows": rows_of,
        "diff": diff,
        "classes": classes,
        "props": props,
        "perlvl": perlvl,
        "fmt": fmt,
        "fmtGroup": fmtg,
        "skills": used_skills,
        "bases": bases,
        "uniques": uniques,
        "sets": sets,
        "setBonus": set_bonus,
        "runewords": runewords,
        "gems": gems,
    }, None


def build(pull=None):
    """-> (data, None) or (None, why). Pulls every source through `pull` (default: the install); writes nothing."""
    pull = pull or _pull
    return assemble(dict((label, pull(path)) for label, path in SOURCES))


def _js(v):
    """JSON a script can hold: U+2028/2029 escaped so no string can end a JS line."""
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"), sort_keys=True).replace(
        "\u2028", "\\u2028").replace("\u2029", "\\u2029")


#: the keys whose value is a long list or map: one entry per line, so a patch reads as a diff of the rows it moved
_LONG = ("uniques", "sets", "runewords", "bases", "gems", "props", "setBonus", "perlvl", "fmt", "fmtGroup", "skills", "affix",
         "affixRows", "pgroups")


def render(data):
    """The block, byte for byte, as it sits in bible.html (markers included). The JSON between `var _CE_DATA = `
    and the closing `;` is one valid JSON object, so the check re-reads exactly what the page reads."""
    out = [MARK_OPEN,
           "  /* GENERATED by tv/char_props.py --write from the D2R CASC (uniqueitems, setitems, sets, runes, gems,"
           " properties, itemstatcost, difficultylevels, armor, weapons, misc, itemtypes, skills, skilldesc,"
           " charstats, magicprefix, magicsuffix, automagic, qualityitems and the string tables). Do not hand-edit -"
           " re-run the generator. */",
           "  " + VAR + "{"]
    keys = sorted(data)
    for n, k in enumerate(keys):
        v = data[k]
        tail = "," if n < len(keys) - 1 else ""
        if k in _LONG and isinstance(v, list):
            body = ",\n".join("    " + _js(x) for x in v)
            out.append("   %s:[\n%s\n   ]%s" % (_js(k), body, tail))
        elif k in _LONG and isinstance(v, dict):
            body = ",\n".join("    %s:%s" % (_js(kk), _js(v[kk])) for kk in sorted(v))
            out.append("   %s:{\n%s\n   }%s" % (_js(k), body, tail))
        else:
            out.append("   %s:%s%s" % (_js(k), _js(v), tail))
    out.append("  };")
    out.append("  " + MARK_CLOSE)
    return "\n".join(out)


def _span(src):
    """-> (start, end) of the block in bible.html, or None when the markers are not there exactly once."""
    if src.count(MARK_OPEN) != 1 or src.count(MARK_CLOSE) != 1:
        return None
    i = src.index(MARK_OPEN)
    j = src.index(MARK_CLOSE, i) + len(MARK_CLOSE)
    return i, j


def embedded(src=None):
    """-> the data dict bible.html carries between the markers, or None (no block, two blocks, or unparseable)."""
    if src is None:
        with io.open(BIBLE, encoding="utf-8") as f:
            src = f.read()
    sp = _span(src)
    if not sp:
        return None
    blk = src[sp[0]:sp[1]]
    if blk.count(VAR) != 1:
        return None
    a = blk.index(VAR) + len(VAR)
    b = blk.rindex("};") + 1
    try:
        return json.loads(blk[a:b])
    except ValueError:
        return None


def _summary(d):
    return "%d uniques, %d set items (%d sets), %d runewords, %d gems/runes, %d property codes, %d affix rows; %s" % (
        len(d.get("uniques") or []), len(d.get("sets") or []), len(d.get("setBonus") or {}),
        len(d.get("runewords") or []), len(d.get("gems") or {}), len(d.get("props") or {}),
        len(d.get("affixRows") or {}),
        " / ".join("%s %+d" % (n, p) for n, p in d.get("diff") or []))


def check(src=None, pull=None):
    """-> (code, say). 0 the block is what the install says · 1 it is not (STALE) · 77 cannot tell (NOT green)."""
    have = embedded(src)
    if have is None:
        return 1, ("bible.html carries no CHAR_PROPS block (or two, or one that will not parse) — the character "
                   "sheet has no property data to sum")
    fresh, why = build(pull)
    if fresh is None:
        return SKIP, "cannot re-derive here (%s), so whether the block matches the install is UNKNOWN" % why
    if fresh == have:
        return 0, "the character sheet's property data matches the install (%s)" % _summary(fresh)
    if fresh.get("sourceHash") != have.get("sourceHash"):
        return 1, ("the install has changed since the CHAR_PROPS block was generated: stored %s, now %s — "
                   "run: python3 tv/char_props.py --write" % (str(have.get("sourceHash"))[:12],
                                                              str(fresh.get("sourceHash"))[:12]))
    diff = sorted(k for k in set(fresh) | set(have) if fresh.get(k) != have.get(k))
    return 1, ("the block in bible.html is not what this generator derives from the same install (%s differ) — "
               "hand-edited, or the generator changed without a --write" % ", ".join(diff))


def write(pull=None, path=None):
    path = path or BIBLE
    if os.path.exists(path + ".EDIT_LOCK"):
        return 1, "bible.html.EDIT_LOCK is held — another writer owns bible.html; nothing written"
    fresh, why = build(pull)
    if fresh is None:
        return SKIP, "not written: %s" % why
    with io.open(path, encoding="utf-8") as f:
        src = f.read()
    sp = _span(src)
    if not sp:
        return 1, "the CHAR_PROPS markers are not in bible.html exactly once — refusing to guess where it goes"
    new = src[:sp[0]] + render(fresh) + src[sp[1]:]
    if new == src:
        return 0, "already current (%s)" % _summary(fresh)
    from bump_version import atomic_write
    atomic_write(path, new)
    return 0, "wrote the CHAR_PROPS block (%s)" % _summary(fresh)


def main(argv):
    code, say = write() if "--write" in argv else check()
    print(("   ✅ " if code == 0 else "   ⚠ ") + say)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
