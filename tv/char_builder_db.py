# -*- coding: utf-8 -*-
"""#174 v-B2 — THE CHARACTER BUILDER'S ITEM DATABASE, TAKEN FROM HIS OWN INSTALL, WRITTEN INTO THE BOARD.

His words: "if i click on helmet lets say.. it shold give me the options from the entire database to put as a
helmet or runeword and based on the base item.. exactly like the d2r one to one". The board had no such database:
ITEM_CODEX holds 320 names and ITEM_TIP 301, while the game he plays (Reign of the Warlock) has ~440 uniques, 140
set items, 181 runewords, every crafted recipe and every base. A picker that offered only what the board happened
to have typed would be a picker that lies by omission.

So this file pulls the game's own excel tables and display strings from the CASC of the install on this machine
(the same `_pull` tv/item_tables.py and tv/mule_slot_map.py use), and writes ONE generated JSON block into
bible.html between two markers:

    python3 tv/char_builder_db.py            # --check: is the block in bible.html what the install says?
    python3 tv/char_builder_db.py --write    # regenerate it (atomic, honours bible.html.EDIT_LOCK)

WHAT IS IN IT, AND WHERE EACH FACT COMES FROM
  · cls   the classes, in charstats.txt order (the game's class index), with the strings the game prints for
          "+N to <Class> Skill Levels", the three skill tabs and "(<Class> Only)"
  · ty    every item type the doll or the inventory can hold: its UI category (itemtypes.txt `UICategory`, the
          game's own grouping — pelts are `druid`, primal helms `barbh`), the class that alone may use it
          (`Class` through the `Equiv` chain) and its socket ceiling by item level (`MaxSockets1..3` with
          their level thresholds)
  · rail  per doll slot, which UI categories it takes — the slot's "base categories" the picker's left rail lists
  · b     every base: display name (item-names.json), type, tier and its normal/exceptional/elite family
          (`normcode`/`ubercode`/`ultracode`), sockets (`gemsockets`), requirements, defense or damage, which
          hands it needs (weapons.txt `2handed`/`1or2handed`), its inventory size, whether it can be ethereal
          (it has durability — an item with none cannot be)
  · it    every unique (uniqueitems.txt, the disabled ones left out), set item (setitems.txt), runeword
          (runes.txt `complete` = 1, with the item types it may be made in and the ones excluded) and crafted
          recipe (cubemain.txt rows that output a crafted item), each with its PROPERTY LINES rendered from the
          game's own words: properties.txt maps a property to its stats, itemstatcost.txt says how each stat is
          described (`descfunc` / `descstrpos` / `descpriority`), and item-modifiers.json holds the text — "All
          Resistances %+d", "%d%% Chance to cast level %d %s on striking". A rolled value is a RANGE the page
          draws as a box; a fixed one is a number.
  · sk    what fits a socket: every rune and gem (gems.txt: its weapon / helm-and-armor / shield modifiers)
  · T     the line templates, stored once and referenced by index (the block is ~40% smaller for it)
  · af    #174 v-B3 — every SPAWNABLE magicprefix / magicsuffix / automagic row: its display name
          (item-nameaffixes.json), level / maxlevel / levelreq, the rare flag, its group, the class it is tied to
          (`classspecific`), its item types and excluded types, its lines (roll keys m1..m3 = its mod columns) and its
          frequency — the ADD MOD list of the Edit tab, filtered on the page by the base's types, the item level, the
          groups already used, the rare flag and the quality's limits. A base's automagic group is its b[22]
          (`auto prefix`), its `magic lvl` its b[23] (the page holds an affix's level against the AFFIX level
          alvl, from the item level, qlvl b[18] and magic lvl - never the item level itself). An affix's [13] is
          its class level requirement (`class` / `classlevelreq`: of Magic Arrows 11, an Amazon 1). A charged
          skill whose table values are NEGATIVE (all 112 "of <Skill>" charges) is set by the item level in the
          game's code: an UNKNOWN line ("Level ? Magic Arrow (?/? Charges)"), never "Level -10".
  · rn    the rare name words (rareprefix / raresuffix), each with the item types it may name and whether a string
          table names it (a key no table names would be kept, flagged 0, never offered as a name). The game asks
          EVERY string table: six words are named only by monsters.json (GhoulRI "Ghoul", Wraithra "Wraith",
          Fiendra "Fiend", crusher "Crusher", scarab "Scarab") and ui.json (strap "Strap") - #174 v-B3 fix round
  · qm    a superior item's modifiers (qualityitems.txt rows and the columns they apply to), the low-quality words
          (lowqualityitems.txt), which qualityitems column each item type reads, and which qualities each type may
          drop in (itemtypes.txt Normal / Magic / Rare, the type's OWN flags)

  · #174 v-B4 — THE IN-GAME TOOLTIP, TRUE TO THE TABLES (APPENDED, nothing reordered):
          b[24] weapons.txt `speed`, b[25] the base's durability (0 = none to print), b[26] / b[27] `wclass` /
          `2handedwclass`; ty[t][5] the "<Class> Class - %s" string key its weapons print (WCLASS_KEY, "" = no table
          names one); it[8] 1 when the item's own properties change its durability; cls[i].tok its plrtype.txt Token;
          TK — aligned with T, each template's [descpriority, descfunc, stat id, several-stats] (one template is one
          stat's words: the page merges a runeword's lines with its runes' and orders them by it); tip — the tooltip's
          own strings by key (Durability / Required ... / Defense / One-Hand / Two-Hand Damage / Socketed / Charmdes /
          RuneQuote / WeaponDesc* / WeaponAttack*), each rune's short name (r26L "Vex"), every class's Attack1 frames
          and rate per weapon class (animdata.d2) and the stat ids the tooltip reads lines by. all-stats (one roll, four
          stats = itemstatcost dgrp 1) prints the group's own "+N to all Attributes", once.
          Fix round: tip.dg - the game's stat groups (itemstatcost dgrp: the group line's template and each member's
          stat id and templates), so the page prints a group's one line only when every member is on the item and all
          are equal (Duress: Cold Resist +45% and three +15%, never "All Resistances +15" beside "Cold Resist +30%");
          tip.st.poisonmindam - two poison sources are one stat, combined by the game's code (the page says UNKNOWN).

A ROLL'S KEY IS THE GAME'S. Each rolled value carries the column it comes from — `p3` is uniqueitems.txt
prop3 / setitems.txt prop3 / runes.txt T1Code3 / cubemain.txt `mod 3`, `a2b` a set item's aprop2b. The builder
stores a typed roll under that key (d2r_charBuilds ...slots[slot].rolls = {p3: 25}), so the stats engine, which
reads the same tables, can join a typed roll to the property it belongs to without parsing any text.

⚠ WHAT IS NOT HERE, SAID RATHER THAN FILLED: a property the tables name but do not describe (RotW's sunder-charm
affix groups, a few commented-out rows) becomes an UNKNOWN line naming its code — never dropped, never guessed.
A monster a reanimate property names is its id, not its name (monstats is not read). A magic jewel's or a
crafted item's RANDOM affixes are not listed: only what the recipe guarantees.

⚠ NO INSTALL = UNKNOWN (exit 77), never "the block is fine". The block is still checked in CI without one:
test_the_character_builder_is_their_builder.py proves every base, unique, set item and runeword name in it is
the name the committed tv/item_tables.json carries for it. [[unknown-stays-unknown]] [[copy-drift]]
"""
import hashlib
import io
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe
    _console_safe()
except Exception:
    pass                      # console encoding only; a failure here changes no fact the block holds

SKIP = 77
BIBLE = os.path.join(ROOT, "bible.html")
LOCK = BIBLE + ".EDIT_LOCK"
MARK_OPEN = "<!-- ⟦CB_DB⟧ GENERATED by tv/char_builder_db.py --write"
MARK_CLOSE = "<!-- ⟦/CB_DB⟧ -->"
BLOCK_ID = "cb-db"

_X = "data:data\\global\\excel\\"
_S = "data:data\\local\\lng\\strings\\"
#: (label, CASC path). ORDER IS FIXED — sourceHash is computed over it.
SOURCES = [
    ("armor", _X + "armor.txt"), ("weapons", _X + "weapons.txt"), ("misc", _X + "misc.txt"),
    ("itemtypes", _X + "itemtypes.txt"), ("uniqueitems", _X + "uniqueitems.txt"),
    ("setitems", _X + "setitems.txt"), ("sets", _X + "sets.txt"), ("runes", _X + "runes.txt"),
    ("gems", _X + "gems.txt"), ("properties", _X + "properties.txt"), ("itemstatcost", _X + "itemstatcost.txt"),
    ("skills", _X + "skills.txt"), ("skilldesc", _X + "skilldesc.txt"), ("charstats", _X + "charstats.txt"),
    ("playerclass", _X + "playerclass.txt"), ("cubemain", _X + "cubemain.txt"),
    ("itemnames", _S + "item-names.json"), ("itemrunes", _S + "item-runes.json"),
    ("itemmods", _S + "item-modifiers.json"), ("skillnames", _S + "skills.json"),
    # #174 v-B3 — APPENDED, never inserted: the affix tables a magic / rare / superior / low item is built from, and
    # the string table that names an affix ("Sturdy", "of Vita") and a rare word ("Havoc", "Shell")
    ("magicprefix", _X + "magicprefix.txt"), ("magicsuffix", _X + "magicsuffix.txt"),
    ("automagic", _X + "automagic.txt"), ("rareprefix", _X + "rareprefix.txt"), ("raresuffix", _X + "raresuffix.txt"),
    ("qualityitems", _X + "qualityitems.txt"), ("lowqualityitems", _X + "lowqualityitems.txt"),
    ("nameaffixes", _S + "item-nameaffixes.json"),
    # #174 v-B3 fix round — APPENDED: the game looks a rare word up in EVERY string table, and six of them are named
    # only outside the item tables (monsters.json GhoulRI "Ghoul", Wraithra "Wraith", Fiendra "Fiend", crusher
    # "Crusher", scarab "Scarab"; ui.json strap "Strap") - read last, after the item strings, for a key none of those has
    ("monsters", _S + "monsters.json"), ("ui", _S + "ui.json"),
    # #174 v-B4 — APPENDED: what the in-game tooltip's "<Class> Class - <Speed> Attack Speed" line is worked out from. The
    # speed word is the character's attack frames (animdata.d2: frames per direction and animation rate, by the class's
    # plrtype.txt Token, the Attack1 mode's plrmode.txt Token and the weapon's weapons.txt wclass) against the base's
    # speed and the item's own Increased Attack Speed - measured against every row of THEIR tooltip (the law)
    ("plrtype", _X + "plrtype.txt"), ("plrmode", _X + "plrmode.txt"), ("animdata", "data:data\\global\\animdata.d2"),
    # #166 (REG-1868) — APPENDED: RotW's property GROUPS. uniqueitems.txt names codes properties.txt does not have
    # ("Breaching-Affix1" on Renewed Bone Break): each is a row HERE - its properties, each with its own range and Chance,
    # and a PickMode. The block printed them "an effect the game's tables name ... but do not describe" while this table,
    # which the generator never pulled, described every one but Gelid-Affix5.
    ("propertygroups", _X + "propertygroups.txt"),
]
#: #174 v-B3 — the affix tables, their one-letter kind (the id's first letter) and the ADD MOD group they list under
AFFIX_TABLES = (("magicprefix", "p"), ("magicsuffix", "s"), ("automagic", "a"))
#: qualityitems.txt's columns, and the ancestor item type that puts a base under each. WHICH column a base reads is
#: the game's own code (qualityitems.txt names the columns and never the types) - stated here as a rule, in the order
#: it is asked: a shield is armour too, so the specific column wins. [[unknown-stays-unknown]]
QCAT = (("shield", "shld"), ("boots", "boot"), ("gloves", "glov"), ("belt", "belt"), ("armor", "armo"),
        ("scepter", "scep"), ("wand", "wand"), ("staff", "staf"), ("bow", "miss"), ("weapon", "weap"))

#: the doll's slots (the game's BodyLoc codes, the same keys the mule window uses) and the inventory
SLOTS = ("head", "neck", "tors", "rarm", "larm", "rrin", "lrin", "belt", "feet", "glov")
#: UI category (itemtypes.txt `UICategory`) -> the words the rail prints. PRESENTATION ONLY: which categories a
#: slot takes, and which bases and items sit in each, is the data's; these are plural English labels.
UI_LABEL = {
    "helms": "Helmets", "circl": "Circlets", "druid": "Pelts", "barbh": "Primal Helms", "armor": "Body Armor",
    "shlds": "Shields", "palad": "Auric Shields", "necro": "Voodoo Heads", "warlo": "Grimoires",
    "glove": "Gloves", "boots": "Boots", "belts": "Belts", "amule": "Amulets", "rings": "Rings",
    "axes": "Axes", "sword": "Swords", "daggs": "Daggers", "maces": "Maces", "scept": "Scepters",
    "wands": "Wands", "stave": "Staves", "bows": "Bows", "xbows": "Crossbows", "spear": "Spears",
    "poles": "Polearms", "javel": "Javelins", "throw": "Throwing Weapons", "assas": "Claws", "sorce": "Orbs",
    "amazo": "Amazon Weapons", "ammo": "Quivers", "jewel": "Jewels",
}
#: which UI categories each doll slot takes, in the rail's order. The categories themselves come from the data
#: (a type whose UICategory is `druid` is a pelt because the game says so); this is only which slot shows which.
SLOT_UI = {
    "head": ["helms", "circl", "druid", "barbh"],
    "tors": ["armor"],
    "rarm": ["axes", "sword", "daggs", "maces", "scept", "wands", "stave", "spear", "poles", "javel", "throw",
             "bows", "xbows", "assas", "sorce", "amazo"],
    "larm": ["shlds", "palad", "necro", "warlo", "ammo", "assas", "@offhand"],
    "glov": ["glove"], "feet": ["boots"], "belt": ["belts"], "neck": ["amule"], "rrin": ["rings"],
    "lrin": ["rings"],
}
#: the inventory's rail: charms by their type, each labelled by the BASE the game names (cm2 "Large Charm" is the
#: type `mcha`, "Medium Charm" — naming the rail by the type would print the wrong word)
INV_TYPES = ("scha", "mcha", "lcha", "csch")
#: two display names, one item: which property tells the duplicates apart (Rainbow Facet x8)
DUP_WORD = {"extra-fire": "Fire", "extra-cold": "Cold", "extra-ltng": "Lightning", "extra-pois": "Poison",
            "death-skill": "on Death", "levelup-skill": "on Level-up"}
#: #174 v-B4 — WHICH "<Class> Class - %s" STRING A WEAPON PRINTS. The strings are the game's (item-modifiers.json); WHICH
#: one a base reads is the game's code (no table names it) - stated here as a rule over the item type's Equiv chain,
#: asked in order (a throwing knife is a knife, a staff is a rod is blunt: the specific type wins). MEASURED in their
#: tooltip on every oracle row: axe · bow · xbow · hamm + mace ("Mace Class") · pole · spea · staf. Named by the key
#: itself where no oracle row reaches: h2h (Claw), orb, knif (Dagger), jave, club (the game's "maces" UI category), and
#: swor, whose key the table spells "WeaponDescSword - %s" (their planner asks for "WeaponDescSword", finds nothing and
#: prints no class line on a sword; the game names its strings by id and prints it). A wand or a scepter: no key names
#: it - the class word is UNKNOWN there, never borrowed from the mace. [[unknown-stays-unknown]]
WCLASS_KEY = (("h2h", "WeaponDescH2H"), ("orb", "WeaponDescOrb"), ("swor", "WeaponDescSword - %s"),
              ("knif", "WeaponDescDagger"), ("jave", "WeaponDescJavelin"), ("spea", "WeaponDescSpear"),
              ("pole", "WeaponDescPoleArm"), ("axe", "WeaponDescAxe"), ("xbow", "WeaponDescCrossBow"),
              ("bow", "WeaponDescBow"), ("staf", "WeaponDescStaff"), ("mace", "WeaponDescMace"),
              ("hamm", "WeaponDescMace"), ("club", "WeaponDescMace"))
#: the speed words, fastest first (item-modifiers.json); the page picks one by the attack's frames (its measured bands)
SPEED_KEYS = ("WeaponAttackFastest", "WeaponAttackVeryFast", "WeaponAttackFast", "WeaponAttackNormal",
              "WeaponAttackSlow", "WeaponAttackVerySlow", "WeaponAttackSlowest")
#: every other string the in-game tooltip prints, by the game's own key: Durability / Required Strength / Required
#: Dexterity / Defense (and its range form) / One-Hand / Two-Hand Damage / Required Level / Socketed / the charm's
#: "Keep in Inventory to Gain Bonus" / the quote around a runeword's rune string / Ethereal / and the label of a blunt
#: weapon's bonus against the undead (ui.json "Damage to Undead") - its NUMBER is the game's code, no table holds it
TIP_KEYS = ("ItemStats1d", "ItemStats1e", "ItemStats1f", "ItemStats1h", "ItemStats1hRange", "ItemStats1l",
            "ItemStats1m", "ItemStats1p", "Socketable", "Charmdes", "RuneQuote", "strethereal", "strMaceSpecialDamage")
_PULLED = {}


def _pull_all():
    """{label: bytes or None}. CB_DB_FROM=<dir> reads <dir>/<label>.<txt|json> instead (a local copy of the same
    tables, for iteration); the sourceHash is over the bytes either way, so a copy that differs says so."""
    if _PULLED:
        return _PULLED
    src_dir = os.environ.get("CB_DB_FROM")
    if src_dir:
        for label, path in SOURCES:
            p = os.path.join(src_dir, label + (os.path.splitext(path.replace("\\", "/"))[1] or ".txt"))
            _PULLED[label] = open(p, "rb").read() if os.path.exists(p) else None
        return _PULLED
    import item_tables as IT
    for label, path in SOURCES:
        _PULLED[label] = IT._pull(path)
    return _PULLED


def _rows(blob):
    import item_tables as IT
    return IT._rows(blob) or []


def _index_codes(rows):
    """code -> row, plus a case-folded index. Two different codes that fold together are a clash:
    a lookup that is not an exact code then stays unknown, rather than picking one."""
    exact, fold, clash = {}, {}, set()
    for r in rows or []:
        code = r.get("code")
        if not code:
            continue
        exact[code] = r
        k = code.casefold()
        prev = fold.get(k)
        if prev is None:
            fold[k] = r
        elif prev.get("code") != code:
            clash.add(k)
    return exact, fold, clash


def _lookup_code(exact, fold, clash, code):
    """The row for `code`. An exact code wins. Otherwise the one row whose code differs only by case.
    A clash, or no row, is None."""
    if code is None or code == "":
        return None
    if code in exact:
        return exact[code]
    k = str(code).casefold()
    if k in clash:
        return None
    return fold.get(k)


def _strings(*blobs):
    import item_tables as IT
    out = {}
    for b in blobs:
        m = IT._strings(b) or {}
        for k, v in m.items():
            out.setdefault(k, v)
    return out


def _int(s, d=0):
    s = str(s if s is not None else "").strip()
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return d


def _pois(v, frames):
    """poison is stored per frame in 256ths; the tooltip prints the total, rounded as the game rounds it
    (Blacktongue: 192 x 150 frames -> 113, not 112)"""
    return (int(v) * int(frames) + 128) // 256


def source_hash(blobs):
    h = hashlib.sha256()
    for label, _ in SOURCES:
        b = blobs.get(label)
        h.update(label.encode())
        h.update(b"\0")
        h.update(hashlib.sha256(b or b"").digest())
    return h.hexdigest()


class _Tpl(object):
    """the template table: every distinct line text stored once"""

    def __init__(self):
        self.list, self.ix = [], {}

    def id(self, t):
        if t not in self.ix:
            self.ix[t] = len(self.list)
            self.list.append(t)
        return self.ix[t]


def _printf(fmt, vals):
    """C format -> the block's template. %+d -> {+N}, %d / %i -> {N}, %s -> the literal given, %% -> %.
    `vals` is a list: an int means a placeholder index; a str is substituted literally."""
    out, i, n = [], 0, 0
    while i < len(fmt):
        c = fmt[i]
        if c != "%":
            out.append(c)
            i += 1
            continue
        j = i + 1
        if j < len(fmt) and fmt[j] == "%":
            out.append("%")
            i = j + 1
            continue
        m = re.match(r"%(\+?)(\d*)([dis])", fmt[i:])
        if not m:
            # D2R's reanimate string uses %0 / %1 (positional); treat as a value / a literal
            m2 = re.match(r"%(\d)", fmt[i:])
            if m2:
                v = vals[int(m2.group(1))] if int(m2.group(1)) < len(vals) else ""
                out.append(("{%d}" % v) if isinstance(v, int) else str(v))
                i += 2
                continue
            out.append(c)
            i += 1
            continue
        v = vals[n] if n < len(vals) else ""
        n += 1
        if m.group(3) == "s" or not isinstance(v, int):
            out.append(str(v))
        else:
            out.append("{%s%d}" % ("+" if m.group(1) else "", v))
        i += len(m.group(0))
    return "".join(out)


class DB(object):
    def __init__(self, blobs):
        self.blobs = blobs
        self.S = _strings(blobs.get("itemnames"), blobs.get("itemrunes"), blobs.get("itemmods"),
                          blobs.get("skillnames"))
        self.T = _Tpl()
        # #174 v-B3: an affix's or a rare word's display string (item-nameaffixes.json), then the item strings
        self.NA = _strings(blobs.get("nameaffixes"))
        # #174 v-B3 fix round: the game's other string tables, asked LAST, only for a key no item table names (the six
        # rare words "no string names it" claimed were named all along - by monsters.json and ui.json)
        self.OS = _strings(blobs.get("monsters"), blobs.get("ui"))
        # A unique that spells a real property in another case (RotW's Colossal jewels: "Gethit-skill",
        # properties.txt "gethit-skill") is that property. Two codes that differ only by case are a clash
        # and stay unknown. [[unknown-stays-unknown]]
        self.P, self._Pfold, self._Pclash = _index_codes(_rows(blobs["properties"]))
        # #166 (REG-1868) — a group code -> its propertygroups.txt row; self.PG fills as lines() meets each one
        self.G, self._Gfold, self._Gclash = _index_codes(_rows(blobs.get("propertygroups")))
        self.PG = {}
        self.I = dict((r["Stat"], r) for r in _rows(blobs["itemstatcost"]) if r.get("Stat"))
        self.types = dict((r["Code"], r) for r in _rows(blobs["itemtypes"]) if r.get("Code"))
        self.skills_by_id, self.skills_by_name = {}, {}
        sd = dict((r.get("skilldesc"), r) for r in _rows(blobs["skilldesc"]) if r.get("skilldesc"))
        for r in _rows(blobs["skills"]):
            if not r.get("skill"):
                continue
            d = sd.get(r.get("skilldesc") or "")
            nm = self.S.get((d or {}).get("str name") or "") or r["skill"]
            rec = (nm, r.get("charclass") or "")
            self.skills_by_id[_int(r.get("*Id"), -1)] = rec
            self.skills_by_name[r["skill"].lower()] = rec
        self.classes = []
        codes = [r.get("Code") for r in _rows(blobs["playerclass"])]
        for i, r in enumerate(_rows(blobs["charstats"])):
            if r.get("class") == "Expansion" or not r.get("StrAllSkills"):
                continue
            code = codes[i] if i < len(codes) else ""
            self.classes.append({
                "n": r["class"], "c": code, "all": self.S.get(r["StrAllSkills"], ""),
                "tabs": [self.S.get(r.get("StrSkillTab%d" % k) or "", "") for k in (1, 2, 3)],
                "only": self.S.get(r.get("StrClassOnly") or "", ""),
                "attr": [_int(r.get(a)) for a in ("str", "dex", "int", "vit")]})
        self.cls_by_code = dict((c["c"], i) for i, c in enumerate(self.classes))
        # #174 v-B4: each class's animation token (plrtype.txt Token, by the class's own name: Sorceress SO, Warlock WK) -
        # the key its attack frames sit under in animdata.d2. A class plrtype does not name keeps "" (its speed UNKNOWN)
        tok = dict((r.get("Name"), r.get("Token") or "") for r in _rows(blobs.get("plrtype")) if r.get("Name"))
        for c in self.classes:
            c["tok"] = tok.get(c["n"], "")
        # #174 v-B4: the template table's per-template sort keys, filled by lines(): {template id: [descpriority,
        # descfunc, stat id, group]} - and any template two different keys claimed (the page could not order it)
        self.TK, self.TK_BAD = {}, set()

    def _prop(self, code):
        return _lookup_code(self.P, self._Pfold, self._Pclash, code)

    def _group(self, code):
        return _lookup_code(self.G, self._Gfold, self._Gclash, code)

    # ---- item types -------------------------------------------------------------------------------------------
    def walk(self, code, col, seen=()):
        r = self.types.get(code)
        if not r or code in seen:
            return ""
        if r.get(col):
            return r[col]
        for e in (r.get("Equiv1"), r.get("Equiv2")):
            if e:
                v = self.walk(e, col, seen + (code,))
                if v:
                    return v
        return ""

    def ancestors(self, code, seen=None):
        seen = set() if seen is None else seen
        if not code or code in seen:
            return seen
        seen.add(code)
        r = self.types.get(code) or {}
        for e in (r.get("Equiv1"), r.get("Equiv2")):
            if e:
                self.ancestors(e, seen)
        return seen

    # ---- property text ----------------------------------------------------------------------------------------
    def skill(self, par):
        if par is None or str(par).strip() == "":
            return None
        p = str(par).strip()
        if re.match(r"^-?\d+$", p):
            return self.skills_by_id.get(int(p))
        return self.skills_by_name.get(p.lower())

    def class_only(self, cc):
        i = self.cls_by_code.get(cc)
        return self.classes[i]["only"] if i is not None else ""

    def lines(self, props, set_bonus=False):
        """props = [(key, code, par, min, max)] -> [[tpl, ranges, prio, flag]]. flag 0 plain · 1 set bonus ·
        2 UNKNOWN (the tables do not describe it) · 3 a flag the item carries (ethereal)."""
        out = []
        have = {}
        for (key, code, par, lo, hi) in props:
            have.setdefault(code, (key, par, lo, hi))
        used = set()
        flag = 1 if set_bonus else 0

        def rng(a, b, key):
            a, b = _int(a), _int(b)
            if b < a:
                b = a
            return [a, b, key]

        cur = [""]                                        # the property code the next line belongs to

        # st = the itemstatcost stat whose descpriority placed the line (#174 v-B4: the page merges lines from several
        # sources - a runeword and its runes - and orders them by it); grp = 1 for ONE line standing for SEVERAL stats: a
        # stat GROUP's own string ("+N to all Attributes", "All Resistances +N": itemstatcost dgrp) and Enhanced Damage
        # (min% + max%) - the lines whose sign their tooltip keeps on a range
        def emit(fmt, vals, ranges, prio, f=None, st=None, grp=0):
            if st is None:
                st = (self.P.get(cur[0]) or {}).get("stat1") or None
            out.append([self.T.id(_printf(fmt, vals)), ranges, prio, flag if f is None else f, cur[0], st, grp])

        def stat_prio(st):
            return _int((self.I.get(st) or {}).get("descpriority"), 0)

        # the game's own merges: a damage pair is one line; poison is per-frame over a length
        def pair(mn, mx, ln, word, rng_key, single_key, prio_stat):
            a, b = have.get(mn), have.get(mx)
            if not (a and b):
                return False
            used.update([mn, mx])
            cur[0] = mn
            ra, rb = rng(a[2], a[3], a[0]), rng(b[2], b[3], b[0])
            if word == "pois":
                L = have.get(ln)
                used.add(ln)
                frames = _int(L[2]) if L else 0
                ra = [_pois(ra[0], frames), _pois(ra[1], frames), ra[2]]
                rb = [_pois(rb[0], frames), _pois(rb[1], frames), rb[2]]
                emit(self.S.get("strModPoisonDamageRange", "Adds %d-%d poison damage over %d seconds"),
                     [0, 1, str(int(round(frames / 25.0)))], [ra, rb], stat_prio(prio_stat))
                return True
            if ln:
                used.add(ln)
            emit(self.S.get(rng_key), [0, 1], [ra, rb], stat_prio(prio_stat))
            return True

        pair("fire-min", "fire-max", None, "fire", "strModFireDamageRange", None, "firemindam")
        pair("ltng-min", "ltng-max", None, "ltng", "strModLightningDamageRange", None, "lightmindam")
        pair("cold-min", "cold-max", "cold-len", "cold", "strModColdDamageRange", None, "coldmindam")
        pair("pois-min", "pois-max", "pois-len", "pois", "strModPoisonDamageRange", None, "poisonmindam")

        # the game's GROUPS (itemstatcost `dgrp`): four equal attributes print as "+N to all Attributes", four equal
        # resistances as "All Resistances +N". Only FIXED values can be equal; a rolled range never groups.
        single = {}
        for (key, code, par, lo, hi) in props:
            p = self._prop(code) or {}
            if _int(p.get("func1")) == 1 and not p.get("stat2") and p.get("stat1"):
                single.setdefault(p["stat1"], (code, _int(lo), _int(hi)))
        groups = {}
        for st, r in self.I.items():
            if r.get("dgrp"):
                groups.setdefault(r["dgrp"], []).append(st)
        grouped = set()
        for g, members in sorted(groups.items()):
            got = [single.get(st) for st in members]
            if not all(got) or len(set((x[1], x[2]) for x in got)) != 1 or got[0][1] != got[0][2]:
                continue
            d0 = self.I[members[0]]
            fmt = self.S.get(d0.get("dgrpstrpos") or "")
            if not fmt:
                continue
            v = got[0][1]
            k0 = have[got[0][0]][0]
            cur[0] = "+".join(x[0] for x in got)
            top = max(members, key=lambda m: _int(self.I[m].get("descpriority")))
            emit(fmt, [0], [[v, v, k0]], max(_int(self.I[m].get("descpriority")) for m in members), st=top, grp=1)
            grouped.update(x[0] for x in got)

        for (key, code, par, lo, hi) in props:
            if code in used and code in ("fire-min", "fire-max", "ltng-min", "ltng-max", "cold-min", "cold-max",
                                         "cold-len", "pois-min", "pois-max", "pois-len"):
                continue
            if code in grouped:
                continue
            cur[0] = code
            if code.startswith("*"):
                continue                                  # a row the game itself comments out
            p = self._prop(code)
            grow = None if p else self._group(code)
            # the line's code is the table's own spelling, so a later reader finds gethit-skill, not Gethit-skill
            if (p or grow) and (p or grow).get("code") and (p or grow).get("code") != code:
                code = (p or grow)["code"]
                cur[0] = code
            if not p and grow:
                # #166 (REG-1868) — A PROPERTY GROUP: one line that stands for the group, flag 4, carrying its roll
                # column; its options (their own lines, in the game's own words, roll key "@") are in the block's `pg`
                prio = self.group(code)
                out.append([self.T.id("the game's property group %s" % code), [], prio, 4, code, None, 0, key])
                continue
            if not p:
                out.append([self.T.id("an effect the game's tables name %s but do not describe" % code), [], 0, 2, code])
                continue
            f1, st1 = _int(p.get("func1")), p.get("stat1") or ""
            d = self.I.get(st1) or {}
            prio = _int(d.get("descpriority"), 0)
            R = rng(lo, hi, key)
            if code in ("dmg-fire", "dmg-ltng", "dmg-cold", "dmg-mag", "dmg-norm", "dmg-pois"):
                word = {"dmg-fire": "Fire", "dmg-ltng": "Lightning", "dmg-cold": "Cold", "dmg-mag": "Magic",
                        "dmg-norm": "Min", "dmg-pois": "Poison"}[code]
                a, b = _int(lo), _int(hi)
                if code == "dmg-pois":
                    frames = _int(par)
                    a, b = _pois(a, frames), _pois(b, frames)
                    fmt = self.S.get("strModPoisonDamageRange") if a != b else self.S.get("strModPoisonDamage")
                    vals = [0, 1, str(int(round(frames / 25.0)))] if a != b else [0, str(int(round(frames / 25.0)))]
                    emit(fmt, vals, [[a, a, key], [b, b, key]] if a != b else [[a, a, key]], prio)
                    continue
                if a != b:
                    emit(self.S.get("strMod%sDamageRange" % word), [0, 1], [[a, a, key], [b, b, key]], prio)
                else:
                    emit(self.S.get("strMod%sDamage" % word), [0], [[a, a, key]], prio)
                continue
            if code == "dmg-elem":
                a, b = _int(lo), _int(hi)
                for word, st in (("Fire", "firemindam"), ("Lightning", "lightmindam"), ("Cold", "coldmindam")):
                    emit(self.S.get("strMod%sDamageRange" % word), [0, 1], [[a, a, key], [b, b, key]], stat_prio(st), st=st)
                continue
            if code == "res-all":
                emit(self.S.get("strModAllResistances"), [0], [R], _int(self.I["fireresist"].get("descpriority")),
                     st="fireresist", grp=1)
                continue
            # a property that feeds SEVERAL stats with no group string (res-all-max: properties.txt func1
            # maxfireresist, func3 maxlightresist / maxcoldresist / maxpoisonresist; itemstatcost gives the four no
            # dgrp) prints every stat in its own words - "+15% to Maximum Fire Resist" alone said a quarter of it
            multi = [p.get("stat%d" % k) for k in range(1, 8) if _int(p.get("func%d" % k)) in (1, 3) and p.get("stat%d" % k)]
            if f1 == 1 and len(multi) > 1 and len(multi) == len([k for k in range(1, 8) if p.get("func%d" % k)]):
                # #174 v-B4 - ONE ROLL THAT IS A WHOLE STAT GROUP PRINTS THE GROUP'S STRING. all-stats (properties.txt
                # func1..4: strength / energy / dexterity / vitality, one min..max) is itemstatcost dgrp 1 exactly: the
                # four stats always equal, so the game prints "+10-20 to all Attributes" once (Annihilus, Breath of the
                # Dying). It printed four lines here, each "+10-20 to <Attribute>", and a separate all-stats branch below
                # was never reached. A property whose stats are NOT one whole group (res-all-max: no dgrp) still
                # prints each stat in its own words. The roll key is the property's one key (p2) - one value.
                dg = set((self.I.get(st) or {}).get("dgrp") or "" for st in multi)
                g0 = dg.pop() if len(dg) == 1 else ""
                if g0 and sorted(multi) == sorted(s for s, r in self.I.items() if r.get("dgrp") == g0):
                    gfmt = self.S.get((self.I.get(multi[0]) or {}).get("dgrpstrpos") or "", "")
                    if gfmt:
                        top = max(multi, key=lambda m: _int((self.I.get(m) or {}).get("descpriority")))
                        emit(gfmt, [0], [R], _int((self.I.get(top) or {}).get("descpriority")), st=top, grp=1)
                        continue
                for st in multi:
                    ds = self.I.get(st) or {}
                    fp = self.S.get(ds.get("descstrpos") or "", "")
                    if not fp:
                        out.append([self.T.id("an effect (%s) the tables do not describe" % st), [R], 0, 2, code])
                        continue
                    emit(fp, [0] if re.search(r"%[+]?\d*[di]", fp) else [], [R], _int(ds.get("descpriority"), 0), st=st)
                continue
            if code == "all-stats":
                emit(self.S.get("Moditem2allattrib"), [0], [R], _int(self.I["strength"].get("descpriority")),
                     st="strength", grp=1)
                continue
            if f1 == 7:                                   # dmg%: the game prints one Enhanced Damage line
                # grp=1: like a stat group's string, ONE line standing for SEVERAL stats (item_maxdamage_percent and
                # item_mindamage_percent) - their tooltip keeps its sign on a range there too ("+350-400% Enhanced Damage")
                emit(self.S.get("strModEnhancedDamage"), [0], [R], stat_prio("item_maxdamage_percent"),
                     st="item_maxdamage_percent", grp=1)
                continue
            if f1 in (5, 6):                              # dmg-min / dmg-max
                st = "mindamage" if f1 == 5 else "maxdamage"
                emit(self.S.get((self.I.get(st) or {}).get("descstrpos") or ""), [0], [R], stat_prio(st), st=st)
                continue
            if f1 == 14:                                  # sockets
                n = [_int(par), _int(par), key] if str(par or "").strip() else R
                emit(self.S.get("Socketable", "Socketed (%i)"), [0], [n], 0)
                continue
            if f1 == 20:
                emit(self.S.get("ModStre9s", "Indestructible"), [], [], stat_prio("item_indesctructible"),
                     st="item_indesctructible")
                continue
            if f1 == 23:
                emit(self.S.get("strethereal", "Ethereal (Cannot be Repaired)"), [], [], 0, 3)
                continue
            if f1 == 12:                                  # a random skill from an id range
                emit("%+d to a random skill (skill ids " + str(_int(lo)) + "-" + str(_int(hi)) + ")", [0],
                     [[_int(par), _int(par), key]], prio, 2)
                continue
            if f1 == 36:
                # +N to ONE random class's skills (Hellfire Torch): properties.txt val1 is the N (3); min..max is the
                # range of CLASS IDS it may roll, never a skill bonus. The value is fixed; the roll is WHICH class:
                # ["C", lo, key, hi] - the builder draws a class choice, never a 0-7 number box.
                n = _int(p.get("val1"))
                emit("%+d to %s Skill Levels", [0, "{1}"], [[n, n, key], ["C", min(_int(lo), _int(hi)), key, max(_int(lo), _int(hi))]], prio)
                continue
            if f1 == 17 and code.endswith("/lvl") or (d.get("descstr2") == "increaseswithplaylevelX"):
                txt = self.S.get(d.get("descstrpos") or "", "")
                if not txt:
                    continue
                tail = self.S.get(d.get("descstr2") or "", "")
                # PER LEVEL: ["L", lo, key, hi, shift] - the table's value per level (the par when it fixes one, else
                # the min..max roll: Fortitude hp/lvl par '' 8..12), and itemstatcost's `op param` for the stat the
                # value is kept in: the character gets floor(value x level / 2^shift). Attack rating per level is
                # shift 1 (Eaglehorn 12 -> 6 per level), life per level shift 3 (8 -> 1 per level). A blank par with
                # a blank min is a value the table does not give: UNKNOWN, never a 0.
                sh = _int(d.get("op param"), 0)
                if str(par or "").strip():
                    a = b = _int(par)
                elif str(lo or "").strip():
                    a, b = _int(lo), _int(hi if str(hi or "").strip() else lo)
                    if b < a:
                        a, b = b, a
                else:
                    out.append([self.T.id("a per-level effect (%s) the table gives no value" % code), [], prio, 2, code])
                    continue
                emit(txt + (" " + tail if tail else ""), [0], [["L", a, key, b, sh]], prio)
                continue
            df = _int(d.get("descfunc"), -1)
            pos = self.S.get(d.get("descstrpos") or "", "")
            neg = self.S.get(d.get("descstrneg") or "", "") or pos
            if df == 19 or df == 1 or df == 2 or df == 3 or df == 4:
                fmt = pos if _int(lo) >= 0 else neg
                if not fmt:
                    continue
                vals = [0] if re.search(r"%[+]?\d*[di]", fmt) else []
                emit(fmt, vals, [R] if vals else [], prio)
            elif df == 29:
                fmt = pos if _int(lo) >= 0 else neg
                emit(fmt, [0], [[abs(R[0]), abs(R[1]), key]] if _int(lo) < 0 else [R], prio)
            elif df == 13:                                # +N to <class> Skill Levels
                ci = _int(p.get("val1"), -1)
                c = self.classes[ci] if 0 <= ci < len(self.classes) else None
                if not c:
                    out.append([self.T.id("class skills for a class index the tables do not name (%s)" % p.get("val1")), [R], prio, 2, code])
                    continue
                emit(c["all"], [0], [R], prio)
            elif df == 14:                                # +N to <tab> Skills (<Class> Only)
                pi = _int(par)
                ci, tab = pi // 3, pi % 3
                c = self.classes[ci] if 0 <= ci < len(self.classes) else None
                if not c:
                    out.append([self.T.id("a skill tab (%s) of a class the tables do not name" % par), [R], prio, 2, code])
                    continue
                emit(c["tabs"][tab] + " " + c["only"], [0], [R], prio)
            elif df in (27, 28, 16):
                sk = self.skill(par)
                if not sk:
                    out.append([self.T.id("a skill (%s) the tables do not name" % par), [R], prio, 2, code])
                    continue
                if df == 27:
                    emit(pos, [0, sk[0], self.class_only(sk[1])], [R], prio)
                elif df == 28:
                    emit(pos, [0, sk[0]], [R], prio)
                else:
                    emit(pos, [0, sk[0]], [R], prio)
            elif df == 15:                                # N% chance to cast level L <skill> on ...
                sk = self.skill(par)
                if not sk:
                    out.append([self.T.id("a chance-to-cast skill (%s) the tables do not name" % par), [], prio, 2, code])
                    continue
                emit(pos, [0, 1, sk[0]], [[_int(lo), _int(lo), key], [_int(hi), _int(hi), key]], prio)
            elif df == 24:                                # Level L <skill> (C/C Charges)
                sk = self.skill(par)
                if not sk:
                    out.append([self.T.id("a charged skill (%s) the tables do not name" % par), [], prio, 2, code])
                    continue
                if _int(lo) < 0 or _int(hi) < 0:
                    # #174 v-B3 fix round - a NEGATIVE level or charge count is not a roll: the affix tables' charged
                    # skills (magicsuffix "of Magic Arrows": mod1min -30, mod1max -10 - all 112 "of <Skill>" rows)
                    # are worked out from the item level by the game's own code, which no table holds. It printed
                    # "Level -10 Magic Arrow (-30/-30 Charges)", a number no item ever shows. UNKNOWN, said.
                    out.append([self.T.id("Level ? %s (?/? Charges) - set by the item level (the game's code, not a "
                                          "table value)" % sk[0]), [], prio, 2, code])
                    continue
                emit(pos, [0, sk[0], 1, 1], [[_int(hi), _int(hi), key], [_int(lo), _int(lo), key]], prio)
            elif df == 12:
                if _int(lo) == 1 and _int(hi) <= 1:
                    emit(pos, [], [], prio)
                else:
                    emit(pos + " %+d", [0], [R], prio)
            elif df == 11:                                # repairs 1 durability in 100/N seconds
                n = _int(par) or _int(lo)
                if n <= 0:
                    continue
                secs = int(round(100.0 / n))
                emit(self.S.get("ModStre9u", "Repairs %d durability in %d seconds"), ["1", str(secs)], [], prio)
            elif df == 5:                                 # howl: the stat is in 128ths
                emit(pos, [0], [[_int(lo) * 100 // 128, _int(hi) * 100 // 128, key]], prio)
            elif df == 23:                                # reanimate: the monster is an id here
                emit(pos, [0, "monster #" + str(par)], [R], prio, 2)
            else:
                # descfunc empty: the game prints nothing for it (durability, poison length, a visual state)
                continue
        # #174 v-B4 - each template's sort key, for the page: [descpriority, descfunc, stat id, group]. A template is one
        # stat's words, so it has ONE key (measured: 568 templates, 0 claimed twice); a template two keys claim is
        # recorded as a defect the build refuses on (the page could not order it), never resolved by the first seen
        for q in out:
            st = q[5] if len(q) > 5 else None
            ds = self.I.get(st) or {}
            k = [q[2], _int(ds.get("descfunc"), 0), _int(ds.get("*ID"), -1) if st else -1, q[6] if len(q) > 6 else 0]
            if self.TK.setdefault(q[0], k) != k:
                self.TK_BAD.add(q[0])
        # the game orders lines by descpriority, highest first; ties keep the table's order
        idx = list(range(len(out)))
        idx.sort(key=lambda i: (-out[i][2], i))
        # a line as the block stores it: [template index, ranges, flag, property code] (+ the set-bonus count; a property
        # group's line, flag 4, + its roll column)
        return [[out[i][0], out[i][1], out[i][3], out[i][4]] + ([out[i][7]] if out[i][3] == 4 else []) for i in idx]

    def group(self, code):
        """#166 (REG-1868) — propertygroups.txt row `code` -> self.PG[code] = [PickMode, [[Chance, lines], ...]], each
        option's lines rendered by lines() itself, roll key "@" (the page puts the item's own column there). Returns the
        highest descpriority among the options' stats, which orders the group's line. A row whose parameter is itself a
        RANGE (ParMin != ParMax: skilltab-war 21..23) is a choice the table does not spell out - that option is one
        UNKNOWN line, never a guessed parameter. What PickMode means is the game's code, not a table value: the block
        carries the number, and the page says what it knows."""
        if code in self.PG:
            return self.PG[code][2]
        r = self.G[code]
        opts, prio = [], 0
        self.PG[code] = [_int(r.get("PickMode")), opts, 0]           # placed first: a group that names itself ends here
        for i in range(1, 9):
            pc = (r.get("Prop%d" % i) or "").strip()
            if not pc:
                continue
            pmin, pmax = (r.get("ParMin%d" % i) or "").strip(), (r.get("ParMax%d" % i) or "").strip()
            lo, hi = r.get("ModMin%d" % i) or "", r.get("ModMax%d" % i) or ""
            if pmin != pmax:
                sub = [[self.T.id("%s with a parameter the game picks from %s to %s - which one is not in the tables"
                                  % (pc, pmin, pmax)), [], 2, pc]]
            else:
                sub = self.lines([("@", pc, pmin, lo, hi)])
            st = (self._prop(pc) or {}).get("stat1") or ""
            prio = max(prio, _int((self.I.get(st) or {}).get("descpriority"), 0))
            opts.append([_int(r.get("Chance%d" % i)), sub])
        self.PG[code][2] = prio
        return prio

    # ---- the tables -------------------------------------------------------------------------------------------
    def build(self):
        B = {}
        spawnable = set()
        for label in ("armor", "weapons", "misc"):
            for r in _rows(self.blobs[label]):
                code = r.get("code") or ""
                if not code or code in B:
                    continue
                t = r.get("type") or ""
                shown = self.S.get(r.get("namestr") or "") or self.S.get(code) or r.get("name") or code
                fam = [r.get("normcode") or "", r.get("ubercode") or "", r.get("ultracode") or ""]
                tier = fam.index(code) if code in fam else 0
                hands = 0
                if label == "weapons":
                    hands = 12 if r.get("1or2handed") == "1" else (2 if r.get("2handed") == "1" else 1)
                eth = 1 if (label != "misc" and r.get("nodurability") != "1" and _int(r.get("durability")) > 0) else 0
                B[code] = [shown, t, tier, fam, _int(r.get("gemsockets")), _int(r.get("levelreq")),
                           _int(r.get("reqstr")), _int(r.get("reqdex")), _int(r.get("minac")), _int(r.get("maxac")),
                           _int(r.get("mindam")), _int(r.get("maxdam")), _int(r.get("2handmindam")),
                           _int(r.get("2handmaxdam")), hands, _int(r.get("invwidth"), 1),
                           _int(r.get("invheight"), 1), eth, _int(r.get("level")), _int(r.get("block")),
                           1 if r.get("spawnable") == "1" else 0, label[0],
                           # [22] #174 v-B3: the automagic.txt group this base draws its AUTOMOD from (armor /
                           # weapons.txt `auto prefix`: an Amazon bow's 300 is its +skill-tab automod), 0 = none
                           _int(r.get("auto prefix")),
                           # [23] #174 v-B3 fix round: armor / weapons / misc.txt `magic lvl` - a circlet's, wand's, staff's
                           # or orb's bonus to the AFFIX level (Diadem 18): alvl = ilvl + magic lvl when it is > 0, the
                           # level an affix's level / maxlevel is held against (with qlvl [18]); 0 = none
                           _int(r.get("magic lvl"))]
                # #174 v-B4 - APPENDED, never reordered:
                B[code] += [
                    # [24] weapons.txt `speed` - the base's weapon speed (Crowbill -10, Berserker Axe 0); 0 for armour
                    # and misc, which print no attack speed line
                    _int(r.get("speed")) if label == "weapons" else 0,
                    # [25] its durability ("Durability: 26 of 26"); 0 = it has none to print (`nodurability` 1 - a
                    # bow, a Phase Blade - or a misc item)
                    (_int(r.get("durability")) if label != "misc" and r.get("nodurability") != "1" else 0),
                    # [26] [27] weapons.txt `wclass` / `2handedwclass` - which of the character's attack animations
                    # (animdata.d2) swings it one-handed / with both hands; "" off a weapon
                    (r.get("wclass") or "") if label == "weapons" else "",
                    (r.get("2handedwclass") or "") if label == "weapons" else ""]
                if r.get("spawnable") == "1":
                    spawnable.add(code)
        # two bases, one printed name (RotW's Colossal Jewel prints "Jewel"): the later one keeps its TABLE name, so
        # the picker never lists two rows it cannot tell apart
        rows_by_code = dict((r.get("code"), r) for lab in ("armor", "weapons", "misc") for r in _rows(self.blobs[lab])
                            if r.get("code"))
        groups = {}
        for code, b in B.items():
            if b[20]:
                groups.setdefault(b[0], []).append(code)
        for shown, codes in groups.items():
            if len(codes) < 2:
                continue
            for code in codes:
                nm = (rows_by_code.get(code) or {}).get("name") or ""
                if nm and nm != shown:
                    B[code][0] = nm
        self.B = B
        # item types the builder shows: every type a base has, its UI category, class and socket ceiling
        TY = {}
        for code, b in B.items():
            t = b[1]
            if t in TY or t not in self.types:
                continue
            r = self.types[t]
            cc = self.walk(t, "Class")
            TY[t] = [r.get("ItemType") or t, r.get("UICategory") or self.walk(t, "UICategory") or "",
                     self.cls_by_code.get(cc, -1),
                     [_int(r.get("MaxSockets1")), _int(r.get("MaxSocketsLevelThreshold1")),
                      _int(r.get("MaxSockets2")), _int(r.get("MaxSocketsLevelThreshold2")), _int(r.get("MaxSockets3"))],
                     sorted(self.ancestors(t)),
                     # [5] #174 v-B4: the "<Class> Class - %s" string key a weapon of this type prints (WCLASS_KEY,
                     # asked in order down its Equiv chain); "" = none names it (a wand, a scepter: UNKNOWN on the page)
                     next((k for anc, k in WCLASS_KEY if anc in self.ancestors(t)), "")]
        self.TY = TY
        items = []
        names = {}

        def add(rec):
            items.append(rec)

        # uniques
        for r in _rows(self.blobs["uniqueitems"]):
            if not r.get("index") or r.get("disabled") == "1" or not r.get("code"):
                continue
            if r.get("spawnable") == "0":
                continue                                  # the game never drops it (a legacy Azurewrath, a quest ring)
            if r["code"] not in B:
                continue
            props = [("p%d" % i, r.get("prop%d" % i), r.get("par%d" % i), r.get("min%d" % i), r.get("max%d" % i))
                     for i in range(1, 13) if r.get("prop%d" % i)]
            add(["u" + (r.get("*ID") or str(len(items))), self.S.get(r["index"]) or r["index"], "u", r["code"],
                 _int(r.get("lvl")), _int(r.get("lvl req")), self.lines(props), None, props])
        # sets: the set's own name, its partial bonuses per item
        for r in _rows(self.blobs["setitems"]):
            if not r.get("index") or not r.get("item") or r["item"] not in B:
                continue
            props = [("p%d" % i, r.get("prop%d" % i), r.get("par%d" % i), r.get("min%d" % i), r.get("max%d" % i))
                     for i in range(1, 10) if r.get("prop%d" % i)]
            bonus = []
            for i in range(1, 6):
                for s in "ab":
                    c = r.get("aprop%d%s" % (i, s))
                    if c:
                        ln = self.lines([("a%d%s" % (i, s), c, r.get("apar%d%s" % (i, s)), r.get("amin%d%s" % (i, s)),
                                          r.get("amax%d%s" % (i, s)))], set_bonus=True)
                        for l in ln:
                            l.append(i + 1)             # "(N items)" — worn with N pieces of the set
                        bonus += ln
            add(["s" + (r.get("*ID") or str(len(items))), self.S.get(r["index"]) or r["index"], "s", r["item"],
                 _int(r.get("lvl")), _int(r.get("lvl req")), self.lines(props),
                 {"set": self.S.get(r.get("set") or "") or r.get("set"), "bonus": bonus,
                  "addf": _int(r.get("add func"))}, props])
        # runewords
        rune_code = {}
        for r in _rows(self.blobs["misc"]):
            if r.get("type") == "rune" and r.get("code"):
                rune_code[r["code"]] = r
        for r in _rows(self.blobs["runes"]):
            if r.get("complete") != "1" or not r.get("Name"):
                continue
            runes = [r.get("Rune%d" % i) for i in range(1, 7) if r.get("Rune%d" % i)]
            if not runes or any(x not in rune_code for x in runes):
                continue
            props = [("p%d" % i, r.get("T1Code%d" % i), r.get("T1Param%d" % i), r.get("T1Min%d" % i),
                      r.get("T1Max%d" % i)) for i in range(1, 8) if r.get("T1Code%d" % i)]
            rl = max(_int(rune_code[x].get("levelreq")) for x in runes)
            add(["r" + r["Name"].replace("Runeword", ""), self.S.get(r["Name"]) or r.get("*Rune Name") or r["Name"],
                 "r", "", 0, rl, self.lines(props),
                 {"runes": runes, "it": [r.get("itype%d" % i) for i in range(1, 7) if r.get("itype%d" % i)],
                  "et": [r.get("etype%d" % i) for i in range(1, 4) if r.get("etype%d" % i)],
                  "lad": 1 if str(r.get("firstLadderSeason") or "").strip() and not str(r.get("lastLadderSeason") or "").strip() else 0},
                 props])
        # crafted: cube recipes whose output is a crafted item
        for i, r in enumerate(_rows(self.blobs["cubemain"])):
            if r.get("enabled") != "1" or "crf" not in (r.get("output") or ""):
                continue
            d = r.get("description") or ""
            nm = d.split("->")[-1].strip() if "->" in d else d.strip()
            inp = (r.get("input 1") or "").strip('"').split(",")
            base = inp[0] if inp else ""
            if base in B:
                bref = base
            elif base in self.types:
                bref = "@" + base
            else:
                continue
            props = [("p%d" % k, r.get("mod %d" % k), r.get("mod %d param" % k), r.get("mod %d min" % k),
                      r.get("mod %d max" % k)) for k in range(1, 6) if r.get("mod %d" % k)]
            add(["c%d" % i, nm, "c", bref, _int(r.get("lvl")), 0, self.lines(props),
                 {"upg": 1 if "upg" in inp else 0, "recipe": d}, props])
        # two display names, one item (Rainbow Facet x8): tell them apart by the property that differs
        by = {}
        for rec in items:
            by.setdefault((rec[2], rec[1]), []).append(rec)
        for (q, nm), recs in by.items():
            if len(recs) < 2:
                continue
            for k, rec in enumerate(recs):
                words = [DUP_WORD[c] for (_, c, _, _, _) in rec[8] if c in DUP_WORD]
                rec[1] = "%s (%s)" % (nm, ", ".join(words) if words else "#%d" % (k + 1))
        seen = {}
        for rec in items:
            key = (rec[2], rec[1])
            if key in seen:
                seen[key] += 1
                rec[1] = "%s #%d" % (rec[1], seen[key])
            else:
                seen[key] = 1
        # socketables: runes and gems (gems.txt), by the three slot classes the game gives them
        SK = []
        misc = dict((r["code"], r) for r in _rows(self.blobs["misc"]) if r.get("code"))
        for r in _rows(self.blobs["gems"]):
            code = r.get("code")
            if not code or code not in misc:
                continue
            m = misc[code]
            kind = "rune" if m.get("type") == "rune" else "gem"
            per = []
            for pre in ("weaponMod", "helmMod", "shieldMod"):
                props = [("%s%d" % (pre[0], k), r.get("%s%dCode" % (pre, k)), r.get("%s%dParam" % (pre, k)),
                          r.get("%s%dMin" % (pre, k)), r.get("%s%dMax" % (pre, k))) for k in range(1, 4)
                         if r.get("%s%dCode" % (pre, k))]
                per.append(self.lines(props))
            SK.append([code, self.S.get(m.get("namestr") or "") or self.S.get(code) or m.get("name") or code, kind,
                       _int(m.get("levelreq")), per[0], per[1], per[2]])
        rail = {}
        for slot, cats in SLOT_UI.items():
            rows = []
            for ui in cats:
                if ui == "@offhand":
                    rows.append(["Second Weapons", ["@offhand"], self.cls_by_code.get("bar", -1)])
                    continue
                tys = sorted(t for t, v in TY.items() if v[1] == ui)
                if not tys:
                    continue
                cls = set(TY[t][2] for t in tys)
                rows.append([UI_LABEL.get(ui, ui), tys, cls.pop() if len(cls) == 1 else -1])
            rail[slot] = rows
        inv, said = [], set()
        for t in INV_TYPES:
            if t not in TY:
                continue
            bn = [b[0] for c, b in sorted(B.items()) if b[1] == t]
            label = (bn[0] + "s") if bn else TY[t][0] + "s"
            if label in said:                             # cs2 prints "Grand Charm" too: its TYPE names it apart
                label = TY[t][0] + "s"
            said.add(label)
            inv.append([label, [t], -1])
        rail["inv"] = inv
        for rec in items:
            raw = rec.pop()                               # the raw props were for naming only
            # [8] #174 v-B4: 1 when the item's own properties change its durability (`dur` - maxdurability, which
            # prints no line - or `dur%`): how the game combines them with the base's is its code, so the page prints
            # the Durability line UNKNOWN for it rather than the base's number (37 uniques, Natalya's Soul)
            rec.append(1 if any(c in ("dur", "dur%") for (_, c, _, _, _) in raw) else 0)
        AF, RN, QM = self.affixes()
        TIP = self.tip_data(B, TY, SK)
        return {
            "v": 1, "gen": "tv/char_builder_db.py", "cls": self.classes, "ty": TY, "rail": rail, "b": B,
            "T": self.T.list, "it": items, "sk": SK, "af": AF, "rn": RN, "qm": QM, "tip": TIP,
            # #166 (REG-1868): {group code: [PickMode, [[Chance, option lines], ...]]} - the lines flag 4 stands for
            "pg": dict((k, v[:2]) for k, v in sorted(self.PG.items())),
            # #174 v-B4: aligned with T - each template's [descpriority, descfunc, stat id, group] (lines() fills it),
            # so the page can merge a runeword's lines with its runes' and order them as the game does
            "TK": [self.TK.get(i, [0, 0, -1, 0]) for i in range(len(self.T.list))],
            "counts": {"bases": len(B), "uniques": sum(1 for x in items if x[2] == "u"),
                       "sets": sum(1 for x in items if x[2] == "s"), "runewords": sum(1 for x in items if x[2] == "r"),
                       "crafted": sum(1 for x in items if x[2] == "c"), "socketables": len(SK),
                       "affixes": len(AF), "prefixes": sum(1 for x in AF if x[1] == "p"),
                       "suffixes": sum(1 for x in AF if x[1] == "s"), "automods": sum(1 for x in AF if x[1] == "a"),
                       "rareWords": [len(RN[0]), len(RN[1])], "superior": len(QM["sup"])},
        }

    # ---- #174 v-B4: what the in-game tooltip prints beyond the property lines ---------------------------------
    def tip_data(self, B, TY, SK):
        """-> {ui, rs, an, a1}.
        ui  the tooltip's own strings by the game's key (TIP_KEYS, every WCLASS_KEY, the seven SPEED_KEYS) - a key no
            string table has is left out, so the page says UNKNOWN rather than print a word nobody read
        rs  each rune's short name (item-runes.json r01L "El"): a runeword's rune string is RuneQuote + these + RuneQuote
        a1  the Attack1 mode's token (plrmode.txt: "A1")
        an  {class token: {weapon class: [frames per direction, animation rate]}} - animdata.d2's Attack1 record of
            every class (plrtype.txt Token) with every weapon class a base swings (weapons.txt wclass / 2handedwclass).
            The page works the frames per attack out of it (the game's formula) and prints the speed word the
            measured bands give; a record the file does not hold is absent - that speed is UNKNOWN."""
        ui = {}
        for k in TIP_KEYS + SPEED_KEYS + tuple(sorted(set(k for _, k in WCLASS_KEY))):
            v = self.S.get(k)
            if v is None:
                v = (self.OS or {}).get(k)
            if v is not None:
                ui[k] = v
        rs = {}
        for s in SK:
            if s[2] == "rune":
                v = self.S.get(s[0] + "L")
                if v:
                    rs[s[0]] = v
        a1 = next((r.get("Token") or "" for r in _rows(self.blobs.get("plrmode")) if r.get("Name") == "Attack1"), "")
        want = set()
        for b in B.values():
            for wc in (b[26], b[27]):
                if wc:
                    want.add(wc.upper())
        toks = set(c.get("tok") for c in self.classes if c.get("tok"))
        an = {}
        blob = self.blobs.get("animdata") or b""
        # animdata.d2: blocks of <u32 count> + count records of 160 bytes - an 8-byte name ("SOA11HS": class token,
        # mode token, weapon class), u32 frames per direction, u32 animation rate, then 144 bytes of frame flags
        i = 0
        while a1 and i + 4 <= len(blob):
            n = struct.unpack_from("<I", blob, i)[0]
            i += 4
            for _ in range(n):
                if i + 160 > len(blob):
                    break
                raw, frames, rate = struct.unpack_from("<8sII", blob, i)
                nm = raw.split(b"\0")[0].decode("ascii", "replace")
                i += 160
                tk, mode, wc = nm[:2], nm[2:4], nm[4:]
                if tk in toks and mode == a1 and wc in want:
                    an.setdefault(tk, {})[wc] = [frames, rate]
        # st: the itemstatcost ids of the stats the tooltip reads lines by (TK[tpl][2]) - its attack speed, its undead
        # damage (a blunt weapon's bonus), Indestructible (no Durability line) and the requirement percent
        st = {}
        # #174 v-B4 fix round: + poisonmindam - the stat every poison line is placed by (two sources are ONE stat in the
        # game, combined by its own code: the page says that line UNKNOWN rather than print two)
        for s in ("item_fasterattackrate", "item_undeaddamage_percent", "item_indesctructible", "item_req_percent",
                  "poisonmindam"):
            if s in self.I:
                st[s] = _int(self.I[s].get("*ID"), -1)
        return {"ui": ui, "rs": rs, "a1": a1, "an": an, "st": st, "dg": self.stat_groups()}

    def stat_groups(self):
        """#174 v-B4 fix round - THE GAME'S STAT GROUPS (itemstatcost `dgrp`), for the tooltip's one list.
        -> {dgrp: {"t": the group's line template (its dgrpstrpos: "{+0} to all Attributes", "All Resistances {+0}"),
                   "m": [[stat id, template when >= 0, template when < 0], ...] - every member, in the table's order}}
        The game prints a group's own line only when EVERY member stat is on the item and all are EQUAL; otherwise each
        member prints in its own words. The runeword and its runes are one stat list in the game, so Duress (its own
        All Resistances +15, a Thul's Cold Resist +30) is "Cold Resist +45%" and three "+15%", and a Monarch holding
        Ral Ort Tal Thul is ONE "All Resistances +35". A member's template is the one lines() gives that stat (descfunc
        1-4 / 19: descstrpos / descstrneg, one value), appended to T when no item used it yet, with its TK. A group
        whose line or any member the strings cannot word is left out - the page then changes nothing for it."""
        groups = {}
        for s, r in self.I.items():
            if (r.get("dgrp") or "").strip():
                groups.setdefault(r["dgrp"].strip(), []).append(s)
        out = {}
        for g, members in sorted(groups.items()):
            gfmt = self.S.get((self.I[members[0]].get("dgrpstrpos") or "").strip(), "")
            if not gfmt or not re.search(r"%[+]?\d*[di]", gfmt):
                continue
            m, ok = [], True
            for s in members:
                ds = self.I[s]
                df = _int(ds.get("descfunc"), -1)
                pos = self.S.get(ds.get("descstrpos") or "", "")
                neg = self.S.get(ds.get("descstrneg") or "", "") or pos
                if df not in (1, 2, 3, 4, 19) or not pos or not re.search(r"%[+]?\d*[di]", pos) \
                        or not re.search(r"%[+]?\d*[di]", neg):
                    ok = False
                    break
                k = [_int(ds.get("descpriority"), 0), df, _int(ds.get("*ID"), -1), 0]
                ids = []
                for fmt in (pos, neg):
                    t = self.T.id(_printf(fmt, [0]))
                    if self.TK.setdefault(t, k) != k:
                        self.TK_BAD.add(t)
                    ids.append(t)
                m.append([k[2]] + ids)
            if not ok:
                continue
            gt = self.T.id(_printf(gfmt, [0]))
            if gt not in self.TK:
                # the dgrp branch of lines(): the highest member's descpriority and stat (no item carried the line yet)
                top = max(members, key=lambda s: _int(self.I[s].get("descpriority"), 0))
                self.TK[gt] = [_int(self.I[top].get("descpriority"), 0), _int(self.I[top].get("descfunc"), 0),
                               _int(self.I[top].get("*ID"), -1), 1]
            out[g] = {"t": gt, "m": m}
        return out

    # ---- #174 v-B3: the affixes a magic / rare / superior item is built from -----------------------------------
    def shown_affix(self, key):
        """an affix's or a rare word's display string -> (text, 1) · the table's own key when no string table has
        it -> (key, 0). The 0 is kept: "no string names it" and "named" must not read the same."""
        k = str(key or "").strip()
        for src in (self.NA or {}, self.S, self.OS or {}):
            if k in src:
                return src[k], 1
        return k, 0

    def class_req(self, r):
        """an affix row's class level requirement: [class index, classlevelreq] when its `class` column names one of
        the classes, else None. Separate from `classspecific` (who may ROLL it): this is only who may WEAR it sooner."""
        c = (r.get("class") or "").strip()
        if not c or not str(r.get("classlevelreq") or "").strip():
            return None
        ci = self.cls_by_code.get(c, -1)
        return [ci, _int(r.get("classlevelreq"))] if ci >= 0 else None

    def affixes(self):
        """-> (af, rn, qm).
        af  one row per SPAWNABLE magicprefix / magicsuffix / automagic row, the table's own order:
            [id, kind 'p'|'s'|'a', name, level, maxlevel (None = no ceiling), levelreq, rare 0|1, group,
             class index (classspecific; -1 = any), itypes, etypes, lines, frequency,
             [class index, classlevelreq] | None (the level requirement for one class: `class` / `classlevelreq`)]
            id = kind + the row's index in its table (the index tv/char_props.py keys the engine's rows by), each mod's
            roll key m1..m3 = its column (mod1..mod3), so a typed roll joins the engine's line without any text.
        rn  the rare name words: [[word, itypes, etypes, named 1|0] per rareprefix row], [... per raresuffix row]]
        qm  {sup: [[id 'q'+row, lines, [qualityitems columns it applies to]]], low: [lowqualityitems words],
             cat: {item type: the qualityitems column its bases read}, can: {item type: the qualities it may drop in,
             from itemtypes.txt Normal / Magic / Rare}}"""
        af = []
        for label, kind in AFFIX_TABLES:
            for i, r in enumerate(_rows(self.blobs[label])):
                if r.get("spawnable") != "1" or not (r.get("Name") or "").strip():
                    continue                              # a blank separator row the game never rolls
                props = [("m%d" % j, r.get("mod%dcode" % j), r.get("mod%dparam" % j), r.get("mod%dmin" % j),
                          r.get("mod%dmax" % j)) for j in (1, 2, 3) if (r.get("mod%dcode" % j) or "").strip()]
                if not props:
                    continue
                mx = (r.get("maxlevel") or "").strip()
                af.append([kind + str(i), kind, self.shown_affix(r["Name"])[0], _int(r.get("level")),
                           _int(mx) if mx else None, _int(r.get("levelreq")), 1 if r.get("rare") == "1" else 0,
                           _int(r.get("group")), self.cls_by_code.get((r.get("classspecific") or "").strip(), -1),
                           [r.get("itype%d" % j) for j in range(1, 8) if r.get("itype%d" % j)],
                           [r.get("etype%d" % j) for j in range(1, 6) if r.get("etype%d" % j)],
                           self.lines(props), _int(r.get("frequency")),
                           # [13] #174 v-B3 fix round: magicsuffix.txt `class` + `classlevelreq` - the level requirement
                           # for THAT class (of Magic Arrows: levelreq 11, an Amazon 1); None = the same for every class
                           self.class_req(r)])
        rn = []
        for label in ("rareprefix", "raresuffix"):
            words = []
            for r in _rows(self.blobs[label]):
                if not (r.get("name") or "").strip():
                    continue
                w, named = self.shown_affix(r["name"])
                words.append([w, [r.get("itype%d" % j) for j in range(1, 8) if r.get("itype%d" % j)],
                              [r.get("etype%d" % j) for j in range(1, 5) if r.get("etype%d" % j)], named])
            rn.append(words)
        cols = [c for c, _ in QCAT]
        sup = []
        for i, r in enumerate(_rows(self.blobs["qualityitems"])):
            props = [("m%d" % j, r.get("mod%dcode" % j), r.get("mod%dparam" % j), r.get("mod%dmin" % j),
                      r.get("mod%dmax" % j)) for j in (1, 2) if (r.get("mod%dcode" % j) or "").strip()]
            if props:
                sup.append(["q%d" % i, self.lines(props), [c for c in cols if r.get(c) == "1"]])
        low = [self.shown_affix(r.get("Name"))[0] for r in _rows(self.blobs["lowqualityitems"]) if r.get("Name")]
        cat, can = {}, {}
        for t in self.TY:
            a = self.ancestors(t)
            col = next((c for c, anc in QCAT if anc in a), None)
            if col:
                cat[t] = col
            # the type's OWN flags, never inherited: a Large Charm's row leaves Rare blank while its ancestor `misc`
            # says 1, and a charm never drops rare (walking the Equiv chain offered "Rare Grand Charm")
            own = self.types.get(t) or {}
            rare = ["rare"] if own.get("Rare") == "1" else []
            if own.get("Normal") == "1":
                can[t] = ["b"]                            # always normal (a quiver)
            elif own.get("Magic") == "1":
                can[t] = rare + ["m"]                     # always magic: a ring, an amulet, a charm, a jewel
            else:
                can[t] = rare + ["m"] + (["sup"] if col else []) + ["b"] + (["low"] if col else [])
        return af, rn, {"sup": sup, "low": low, "cat": cat, "can": can}


def build():
    """-> (db dict, None) or (None, why). Pulls; writes nothing."""
    blobs = _pull_all()
    absent = [label for label, _ in SOURCES if blobs.get(label) is None]
    if absent:
        return None, ("could not pull %s from the install — the builder's database is UNKNOWN here, not empty"
                      % ", ".join(absent))
    d = DB(blobs)
    db = d.build()
    if d.TK_BAD:
        # #174 v-B4: a template two sort keys claim cannot be ordered on the page - a defect, never UNKNOWN (77)
        raise RuntimeError("templates with two sort keys (the page could not order them): %s"
                           % ", ".join(repr(db["T"][i]) for i in sorted(d.TK_BAD)[:5]))
    db["sourceHash"] = source_hash(blobs)
    return db, None


def render(db):
    """the block, byte for byte, as it sits in bible.html (markers included). `</` is escaped so no string in the
    data can close the script element."""
    body = json.dumps(db, ensure_ascii=False, separators=(",", ":"), sort_keys=True).replace("</", "<\\/")
    return (MARK_OPEN + " from the D2R CASC (excel + strings) — do not hand-edit, re-run the generator -->\n"
            + '<script type="application/json" id="%s">' % BLOCK_ID + body + "</script>\n" + MARK_CLOSE)


def _span(src):
    if src.count(MARK_OPEN) != 1 or src.count(MARK_CLOSE) != 1:
        return None
    i = src.index(MARK_OPEN)
    return i, src.index(MARK_CLOSE, i) + len(MARK_CLOSE)


def embedded(src=None):
    """-> the db dict bible.html carries, or None"""
    if src is None:
        with io.open(BIBLE, encoding="utf-8") as f:
            src = f.read()
    sp = _span(src)
    if not sp:
        return None
    blk = src[sp[0]:sp[1]]
    a = blk.index('id="%s">' % BLOCK_ID) + len('id="%s">' % BLOCK_ID)
    b = blk.index("</script>", a)
    return json.loads(blk[a:b])


def check():
    """-> (code, say). 0 the block is what the install says · 1 it is not · 77 cannot tell (NOT green)."""
    try:
        have = embedded()
    except ValueError as e:
        return 1, "the builder's database block does not parse (%s)" % e
    if have is None:
        return 1, "bible.html carries no ⟦CB_DB⟧ block (or carries two) — the builder has nothing to list"
    fresh, why = build()
    if fresh is None:
        return SKIP, "cannot re-derive here (%s), so whether the block matches the install is UNKNOWN" % why
    if fresh == have:
        c = fresh["counts"]
        return 0, ("the builder's database matches the install (%d bases, %d uniques, %d set items, %d runewords, "
                   "%d crafted recipes, %d socketables, %d affixes; source %s)" % (
                       c["bases"], c["uniques"], c["sets"], c["runewords"], c["crafted"], c["socketables"],
                       c["affixes"], fresh["sourceHash"][:12]))
    diff = [k for k in sorted(set(fresh) | set(have)) if fresh.get(k) != have.get(k)]
    return 1, "the install disagrees with the block in bible.html (%s differ) — run --write" % ", ".join(diff)


def write():
    if os.path.exists(LOCK):
        return 1, "bible.html.EDIT_LOCK is held — another writer owns bible.html; nothing written"
    fresh, why = build()
    if fresh is None:
        return SKIP, "not written: %s" % why
    with io.open(BIBLE, encoding="utf-8") as f:
        src = f.read()
    sp = _span(src)
    if not sp:
        return 1, "the ⟦CB_DB⟧ markers are not in bible.html exactly once — refusing to guess where it goes"
    new = src[:sp[0]] + render(fresh) + src[sp[1]:]
    if new == src:
        return 0, "already current"
    from bump_version import atomic_write
    atomic_write(BIBLE, new)
    c = fresh["counts"]
    return 0, "wrote the builder's database: %s" % ", ".join("%s %s" % (v, k) for k, v in sorted(c.items()))


def main(argv):
    if "--dump" in argv:
        db, why = build()
        if db is None:
            print("   ⚠ " + why)
            return SKIP
        sys.stdout.write(render(db))
        return 0
    code, say = write() if "--write" in argv else check()
    print(("   ✅ " if code == 0 else "   ⚠ ") + say)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
