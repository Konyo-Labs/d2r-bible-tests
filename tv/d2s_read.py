# -*- coding: utf-8 -*-
"""READ A D2R CHARACTER SAVE (.d2s, format 105) — every item, byte-exact, or say where it stopped.

`read(path_or_bytes, tables=None) -> dict`. The header, the stats block (named), the 30 skill
bytes, every item with its sockets and properties, merc/golem presence, and a `verify` block that
says whether the decode ended EXACTLY where the file says the player's items end.

⚠⚠ A PARTIAL LIST IS NEVER RETURNED AS COMPLETE. The item bitstream has no per-item length: one
bit read wrong and every later item is garbage that still LOOKS like items. So the only honest
check is the one the file offers — after the declared number of top-level items the next two bytes
must be the corpse section's `JM`. `ok` is False, with the byte where decoding stopped, whenever
that is not so. The file's own size field and checksum are checked too.

=== FORMAT 105, MEASURED ON THREE OF HIS SAVES (49, 67 and 28 top-level items) ===
    0x00 magic 0x55AA55AA · 0x04 version · 0x08 size · 0x0C checksum · 0x14 status · 0x15 progression
    0x18 class · 0x1B level · 0x20 last played · 0x12B name (48 bytes UTF-8)
    0x193 'Woo!' quests · 'WS' waypoints · 'w4' npcs · 'gf' stats · 'if' skills (30 bytes)
    'JM' items: u16 = TOP-LEVEL items only; socketed children follow their parent
    'JM' corpse · 'jf' merc (absent on one save) · 'kf' golem · 'lf'
The stats block uses ItemStatCost `CSvBits`, NOT `Save Bits` — strength is 10 bits there and 8 on an
item; it ends on the `if` tag on all three saves. The checksum is the classic rotate-add with its own
four bytes zeroed; it matches the stored value on all three.

=== THE TWO FORMAT-105 BITS NO OLDER DOCUMENT HAS ===
1. ONE BIT after the type-specific block of every extended item (after durability on armour, after
   the timestamp on a jewel). Without it Jalal's Mane and its Colossal Jewel both derail; with it both
   end exactly on the 0x1FF terminator. Measured first by a scratch study decoder.
2. ONE BIT after the LAST property list, before the item is byte-aligned. ⚠ The study decoder
   recorded this as TWO quirks — "8 zero bits after a runeword's property list" and "a 0x00 pad byte
   before an item", the pad found by sniffing for `00 10`. Across all three saves they are one fact:
   every one of them (Breath of the Dying ×2, Fortitude, Chains of Honor, Mephisto's Brain ×3, two
   Grand Charms) is an item whose last list ends EXACTLY on a byte boundary, and every extended item
   whose list ends off a boundary has no extra byte. One bit, then align, reproduces all 144 top-level
   items with no sniffing. A sniff is a guess about the next item's first byte; this is not.
   ⚠ UNMEASURED: every runeword on hand ends its list on a boundary (4 of 4), so a runeword ending
   off one has never been seen. If this rule is wrong there, the decode derails and `verify` says so.
   ⚠ UNMEASURED: whether a SIMPLE item carries the bit — no simple item on hand ends on a boundary —
   so it is not read there.

Runeword names: a save's 12-bit id minus 26 is the runes.txt row, and on his saves it is also the
`RunewordN` key. The two part company from row 80 (see item_tables.py); where they disagree the
name is None and `runewordWhy` names both candidates. [[unknown-stays-unknown]]
"""
import io
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

FORMAT = 105
MAGIC = 0xAA55AA55
QUESTS_AT = 0x193
CORPSE_TAG = b"JM"

CLASSES = {0: "Amazon", 1: "Sorceress", 2: "Necromancer", 3: "Paladin", 4: "Barbarian",
           5: "Druid", 6: "Assassin"}
LOCATIONS = {0: "stored", 1: "equipped", 2: "belt", 4: "cursor", 6: "socketed"}
SLOTS = {1: "head", 2: "neck", 3: "torso", 4: "right hand", 5: "left hand", 6: "right ring",
         7: "left ring", 8: "belt", 9: "feet", 10: "gloves", 11: "alt right hand", 12: "alt left hand"}
PANELS = {1: "inventory", 4: "cube", 5: "stash"}
QUALITIES = {1: "low", 2: "normal", 3: "superior", 4: "magic", 5: "set", 6: "rare", 7: "unique",
             8: "crafted"}
#: A property id that is followed by N-1 more values with no id of their own (min/max damage pairs).
GROUPS = {17: 2, 48: 2, 50: 2, 52: 2, 54: 3, 57: 3}
#: Stats stored as 8.8 fixed point in the stats block.
FIXED_POINT = ("hitpoints", "maxhp", "mana", "maxmana", "stamina", "maxstamina")

# D2R item-code Huffman tree (index 0 = a 0 bit, 1 = a 1 bit). `[]` is a code no item uses.
TREE = [[[[["w", "u"], [["8", ["y", ["5", ["j", []]]]], "h"]], ["s", [["2", "n"], "x"]]],
         [[["c", ["k", "f"]], "b"], [["t", "m"], ["9", "7"]]]],
        [" ", [[[["e", "d"], "p"], ["g", [[["z", "q"], "3"], ["v", "6"]]]],
               [["r", "l"], ["a", [["1", ["4", "0"]], ["i", "o"]]]]]]]


class D2SError(Exception):
    """A decode that cannot continue. Carries the bit where it stood, so the stop is reported."""

    def __init__(self, why, bit):
        Exception.__init__(self, why)
        self.why, self.bit = why, bit


class _Bits(object):
    """LSB-first bit reader over the whole file."""

    def __init__(self, data, byte_pos):
        self.d, self.p = data, byte_pos * 8

    def r(self, n):
        if (self.p + n + 7) // 8 > len(self.d):
            raise D2SError("ran past the end of the file", self.p)
        v = 0
        for i in range(n):
            v |= ((self.d[self.p >> 3] >> (self.p & 7)) & 1) << i
            self.p += 1
        return v

    def align(self):
        self.p = (self.p + 7) & ~7


def _huff(r):
    at, node = r.p, TREE
    while isinstance(node, list):
        if not node:
            raise D2SError("not an item code", at)
        node = node[r.r(1)]
    return node


def _stat(T, sid, at):
    s = T["stats"].get(str(sid))
    if not s or not s.get("saveBits"):
        raise D2SError("stat id %d is not an item stat on this install" % sid, at)
    return s


def _props(r, T):
    """One property list, flattened to [{stat, id, param, value}], up to the 0x1FF terminator."""
    out = []
    while True:
        at = r.p
        sid = r.r(9)
        if sid == 0x1FF:
            return out
        for k in range(GROUPS.get(sid, 1)):
            s = _stat(T, sid + k, at)
            param = r.r(s["saveParamBits"]) if s["saveParamBits"] else None
            out.append({"stat": s["name"], "id": sid + k, "param": param,
                        "value": r.r(s["saveBits"]) - s["saveAdd"]})


def _runeword(T, rid):
    """-> (name or None, why or None). Named only where the row and the RunewordN key agree."""
    row = rid - 26
    by_row = (T.get("runewords") or {}).get(str(row))
    by_key = next((v for v in (T.get("runewords") or {}).values()
                   if v.get("key") == "Runeword%d" % row), None)
    if by_row and by_key is by_row:
        return by_row["name"], None
    return None, ("UNKNOWN: runeword id %d is row %d (%s) but key Runeword%d (%s) — no save on hand "
                  "tells which the game means" % (rid, row, (by_row or {}).get("name"), row,
                                                  (by_key or {}).get("name")))


def _item(r, T):
    at = r.p
    flags = r.r(32)
    it = {"bitStart": at, "identified": bool(flags >> 4 & 1), "ethereal": bool(flags >> 22 & 1),
          "simple": bool(flags >> 21 & 1), "isRuneword": bool(flags >> 26 & 1),
          "quality": None, "ilvl": None, "props": [],      # a simple item has none of these
          "sockets": None, "defense": None, "durability": None}
    socketed_flag, personalized = bool(flags >> 11 & 1), bool(flags >> 24 & 1)
    if flags >> 16 & 1:
        raise D2SError("an ear — its layout is UNMEASURED in format %d" % FORMAT, at)
    r.r(3)                                                  # item format field
    loc, slot, x, y, panel = r.r(3), r.r(4), r.r(4), r.r(4), r.r(3)
    it.update(location=LOCATIONS.get(loc, loc), slot=SLOTS.get(slot) if loc == 1 else None,
              panel=PANELS.get(panel, panel) if loc == 0 else None, x=x, y=y)
    code_at = r.p
    code = "".join(_huff(r) for _ in range(4)).strip()
    row = T["items"].get(code)
    if row is None:
        raise D2SError("item code %r is not in this install's tables — its layout cannot be known"
                       % code, code_at)
    it.update(code=code, name=row["name"], kind=row["kind"])
    n_children = r.r(1) if it["simple"] else r.r(3)
    it["socketedCount"] = n_children
    if not it["simple"]:
        r.r(32)                                             # item id
        it["ilvl"] = r.r(7)
        q_at, q = r.p, r.r(4)
        if q not in QUALITIES:
            raise D2SError("quality %d is not a quality — the stream is already misaligned" % q, q_at)
        it["quality"] = QUALITIES[q]
        if r.r(1):
            it["picture"] = r.r(3)
        if r.r(1):
            it["autoAffix"] = r.r(11)
        if q in (1, 3):
            r.r(3)
        elif q == 4:
            it["magicPrefix"], it["magicSuffix"] = r.r(11), r.r(11)
        elif q == 5:
            sid = r.r(12)
            s = (T.get("setItems") or {}).get(str(sid)) or {}
            it.update(setId=sid, setName=s.get("name"), setOf=s.get("set"))
        elif q == 7:
            uid = r.r(12)
            it.update(uniqueId=uid, uniqueName=((T.get("uniques") or {}).get(str(uid)) or {}).get("name"))
        elif q in (6, 8):
            it["rareNames"] = [r.r(8), r.r(8)]
            it["affixes"] = [(r.r(11) if r.r(1) else None) for _ in range(6)]
        if it["isRuneword"]:
            rid = r.r(12)
            r.r(4)
            it["runewordId"] = rid
            it["runewordName"], why = _runeword(T, rid)
            if why:
                it["runewordWhy"] = why
        if personalized:                                    # 8-bit chars: UNMEASURED in 105 (none on hand)
            name = bytearray()
            while True:
                c = r.r(8)
                if not c:
                    break
                name.append(c)
            it["personalizedName"] = name.decode("utf-8", "replace")
        if code in ("tbk", "ibk"):
            r.r(5)
        r.r(1)                                              # timestamp
        if row["kind"] == "armor":
            s = _stat(T, 31, r.p)
            it["defense"] = r.r(s["saveBits"]) - s["saveAdd"]
        if row["kind"] in ("armor", "weapon"):
            smax = _stat(T, 73, r.p)
            mx = r.r(smax["saveBits"]) - smax["saveAdd"]
            cur = None
            if mx:
                scur = _stat(T, 72, r.p)
                cur = r.r(scur["saveBits"]) - scur["saveAdd"]
            it["durability"] = {"current": cur, "max": mx}
        # FORMAT 105 — ONE BIT after the type-specific block of every extended item. See the docstring.
        r.r(1)
        if row["stackable"]:
            it["quantity"] = r.r(9)
        if socketed_flag:
            it["sockets"] = r.r(4)
        set_lists = r.r(5) if q == 5 else 0
        it["props"] = _props(r, T)
        if q == 5:
            it["setProps"] = [_props(r, T) for b in range(5) if set_lists >> b & 1]
        if it["isRuneword"]:
            it["runewordProps"] = _props(r, T)
        # FORMAT 105 — ONE BIT after the LAST property list, then align. Not a pad, not 8 runeword bits.
        r.r(1)
    r.align()
    it["bits"] = r.p - at
    it["socketed"] = [_item(r, T) for _ in range(n_children)]
    return it


def _item_list(b, pos, T, count):
    """Decode `count` top-level items from byte `pos`. -> (items, end_byte, stop or None)."""
    r = _Bits(b, pos)
    items = []
    try:
        for _ in range(count):
            items.append(_item(r, T))
    except D2SError as e:
        return items, e.bit // 8, {"byte": e.bit // 8, "bit": e.bit, "why": e.why, "item": len(items)}
    return items, r.p // 8, None


def _checksum(b):
    c = 0
    for i, x in enumerate(bytearray(b)):
        if 12 <= i < 16:
            x = 0
        c = (((c << 1) & 0xFFFFFFFF) + x + (c >> 31)) & 0xFFFFFFFF
    return c


def _tag_after(b, tag, start, window):
    i = b.find(tag, start, start + window + len(tag))
    return None if i < 0 else i


def read(path_or_bytes, tables=None):
    """-> dict. `ok` is True only when every check in `verify` holds. Never raises on a bad file."""
    path = None
    out = {"ok": False, "why": None, "path": path, "header": None, "stats": None, "skills": None,
           "items": [], "corpse": None, "merc": None, "golem": None,
           "verify": {"bytesConsumed": None, "endsOnCorpseTag": False, "itemCount": 0}}
    v = out["verify"]

    def stop(why):
        out["why"] = why
        return out

    if isinstance(path_or_bytes, (bytes, bytearray)):
        b = bytes(path_or_bytes)
    else:
        path = out["path"] = str(path_or_bytes)
        try:
            with io.open(path, "rb") as fh:
                b = fh.read()
        except OSError as e:
            return stop("could not open %s: %s — nothing was read, so nothing is known" % (path, e))

    if len(b) < QUESTS_AT:
        return stop("the file is %d bytes, shorter than a format-%d header" % (len(b), FORMAT))
    magic, version, size, stored = struct.unpack_from("<IIII", b, 0)
    status = b[0x14]
    h = out["header"] = {
        "magic": "0x%08X" % magic, "version": version, "fileSize": size, "checksum": "0x%08X" % stored,
        "status": status, "hardcore": bool(status & 4), "died": bool(status & 8),
        "expansion": bool(status & 32), "ladder": bool(status & 64), "progression": b[0x15],
        "classId": b[0x18], "className": CLASSES.get(b[0x18]), "level": b[0x1B],
        "lastPlayed": struct.unpack_from("<I", b, 0x20)[0],
        "name": b[0x12B:0x12B + 48].split(b"\0")[0].decode("utf-8", "replace")}
    v["sizeMatches"] = size == len(b)
    v["checksumOk"] = _checksum(b) == stored
    if magic != MAGIC:
        return stop("not a D2 save: magic %s" % h["magic"])
    if version != FORMAT:
        return stop("format %d is UNMEASURED — this reader was proven on format %d only" % (version, FORMAT))
    if tables is None:
        import item_tables
        tables = item_tables.load()
    if not tables or not tables.get("stats") or not tables.get("items"):
        return stop("item tables UNKNOWN — run python3 tv/item_tables.py --write on a machine with the install")
    T = tables

    # ── the sections before the items ──────────────────────────────────────────────────────────
    if b[QUESTS_AT:QUESTS_AT + 4] != b"Woo!":
        return stop("no 'Woo!' at 0x%X" % QUESTS_AT)
    ws = QUESTS_AT + struct.unpack_from("<H", b, QUESTS_AT + 8)[0]
    if b[ws:ws + 2] != b"WS":
        return stop("no 'WS' where the quest section's size says (0x%X)" % ws)
    w4 = _tag_after(b, b"w4", ws + struct.unpack_from("<H", b, ws + 6)[0], 8)
    gf = None if w4 is None else _tag_after(b, b"gf", w4 + 2, 64)
    if gf is None:
        return stop("the 'w4'/'gf' sections are not where format %d puts them" % FORMAT)
    r = _Bits(b, gf + 2)
    stats = {}
    try:
        while True:
            at = r.p
            sid = r.r(9)
            if sid == 0x1FF:
                break
            s = T["stats"].get(str(sid))
            if not s or not s.get("csvBits"):
                raise D2SError("stat id %d is not a character stat" % sid, at)
            if s.get("csvParam"):
                r.r(s["csvParam"])
            val = r.r(s["csvBits"])
            stats[s["name"]] = val / 256.0 if s["name"] in FIXED_POINT else val
    except D2SError as e:
        v["stoppedAt"] = e.bit // 8
        return stop("the stats block stopped at byte 0x%X: %s" % (e.bit // 8, e.why))
    r.align()
    sk = r.p // 8
    out["stats"] = stats
    v["statsEndOnSkillsTag"] = b[sk:sk + 2] == b"if"
    if not v["statsEndOnSkillsTag"]:
        v["stoppedAt"] = sk
        return stop("the stats block ended at byte 0x%X, not on the 'if' tag" % sk)
    out["skills"] = list(bytearray(b[sk + 2:sk + 32]))
    jm = sk + 32
    if b[jm:jm + 2] != b"JM":
        return stop("no item list 'JM' at 0x%X" % jm)

    # ── the items ───────────────────────────────────────────────────────────────────────────────
    count = struct.unpack_from("<H", b, jm + 2)[0]
    items, end, halt = _item_list(b, jm + 4, T, count)
    out["items"] = items
    v.update(declaredItemCount=count, itemCount=len(items), itemsStartAt=jm + 4, bytesConsumed=end)
    if halt:
        v["stoppedAt"] = halt["byte"]
        return stop("decoding stopped inside top-level item %d at byte 0x%X: %s — the %d item(s) before "
                    "it are NOT the whole list" % (halt["item"], halt["byte"], halt["why"], len(items)))
    v["endsOnCorpseTag"] = b[end:end + 2] == CORPSE_TAG
    if not v["endsOnCorpseTag"]:
        v["stoppedAt"] = end
        return stop("%d items decoded but they end at byte 0x%X, which is %r, not the corpse 'JM' — a "
                    "bit was misread somewhere, so NONE of the list can be trusted as complete"
                    % (len(items), end, b[end:end + 2]))

    # ── after the corpse tag: presence only, and only what the bytes show ─────────────────────
    corpses = struct.unpack_from("<H", b, end + 2)[0] if end + 4 <= len(b) else None
    out["corpse"] = {"count": corpses}
    p = end + 4
    merc = {"section": False, "hired": False, "itemCount": 0}
    if corpses == 0 and b[p:p + 2] == b"jf":
        merc["section"] = True
        p += 2
        if b[p:p + 2] == b"JM":
            merc["hired"] = True
            n = struct.unpack_from("<H", b, p + 2)[0]
            mitems, mend, mhalt = _item_list(b, p + 4, T, n)
            merc.update(itemCount=n, items=mitems, itemsEndOnGolemTag=(mhalt is None and b[mend:mend + 2] == b"kf"))
            p = mend
    elif corpses != 0:
        merc = {"section": None, "hired": None, "why": "a corpse is present; its layout is UNMEASURED"}
    out["merc"] = merc
    if corpses == 0 and b[p:p + 2] == b"kf" and p + 2 < len(b):
        out["golem"] = {"present": bool(b[p + 2])}
        v["tail"] = b[p:].hex()
    else:
        out["golem"] = {"present": None, "why": "no 'kf' where it was expected — UNKNOWN"}

    problems = [k for k in ("sizeMatches", "checksumOk") if not v.get(k)]
    if problems:
        return stop("the items decode, but the file's own %s check fails" % " and ".join(problems))
    out["ok"] = True
    return out




# ── WHERE THIS PC KEEPS ITS SAVES (#251, REG-2925) ──────────────────────────────────────────────────────────────────
# Read-only: listdir and stat, nothing opened but a .d2s, nothing ever written.
#
# MEASURED 2026-10-29 on his two PCs. Neither holds a .d2s: his characters are online and Battle.net keeps them. What
# the folder does hold, on both, is one key-binding file per character played on that PC - <Name><id>.ctlo and/or
# <Name><id>.keyo - so the folder names this PC's characters with their exact spelling, and nothing else about them
# (no class, no level). The id is an account id and is never returned (the same character carries the same id on the
# Mac and the ALT; a deleted and remade name gets a new one). A binding file's time is when its BINDINGS were
# written, not when the character was played, so no time leaves this function.
#   * Windows: the Saved Games known folder, \Diablo II Resurrected.
#   * Mac: D2R runs in a CrossOver bottle. The bottles live where CrossOver.conf's "BottlePath" says (his:
#     ~/CXPBottles); the default Library/Application Support/CrossOver/Bottles was EMPTY on his Mac. Every bottle's
#     drive_c/users/<user>/Saved Games/Diablo II Resurrected is looked in.
# A folder that exists and will not list is UNKNOWN (counted in `unread`), never an empty one.
SAVE_DIR_NAME = "Diablo II Resurrected"
#: a D2R name (2-15 letters, at most one '-' or '_'; no digit can be in it) followed by the account id
BIND_FILE = re.compile(r"^([A-Za-z][A-Za-z_-]{1,14})(\d{3,12})\.(?:ctlo|keyo)$")
NO_D2S_SAY = "no .d2s on this PC; online characters live on Battle.net"
_SAVED_GAMES_GUID = "{4C5C32FF-BB9D-43B0-B5B4-2D72E54EAAA4}"   # FOLDERID_SavedGames


def _known_saved_games():
    """Windows' Saved Games folder as the shell knows it (it can be moved), or None."""
    try:
        import ctypes
        from ctypes import wintypes

        class _GUID(ctypes.Structure):
            _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]

        g = _GUID()
        ctypes.oledll.ole32.CLSIDFromString(_SAVED_GAMES_GUID, ctypes.byref(g))
        p = ctypes.c_wchar_p()
        ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(p))
        out = p.value
        ctypes.windll.ole32.CoTaskMemFree(p)
        return out or None
    except Exception:
        return None


def _bottle_roots(home):
    """Every folder CrossOver keeps bottles in: CrossOver.conf's BottlePath lines first, then the default."""
    base = os.path.join(home, "Library", "Application Support", "CrossOver")
    roots = []
    try:
        with io.open(os.path.join(base, "CrossOver.conf"), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r'\s*"BottlePath"\s*=\s*"([^"]*)"', line)
                if m and m.group(1).strip():
                    roots.append(os.path.expanduser(m.group(1).strip()))
    except FileNotFoundError:
        pass        # no CrossOver.conf: the default bottle folder is the only place (a conf that will not open raises)
    roots.append(os.path.join(base, "Bottles"))
    out = []
    for r in roots:
        if r not in out:
            out.append(r)
    return out


def _subdirs(p):
    """-> the folder's subfolder names; [] when the folder does not exist (nothing there); None when it exists and will
    not list - UNKNOWN, which the caller counts as a place it could not look, never as an empty one."""
    try:
        names = os.listdir(p)
    except FileNotFoundError:
        return []
    except OSError:
        return None
    return sorted(n for n in names if os.path.isdir(os.path.join(p, n)))


def save_dirs(platform=None, home=None, saved_games=None):
    """-> (dirs, looked, why, unread). `dirs` holds every D2R save folder that exists on this PC; `looked` is where it
    looked (said when nothing is found); `unread` the folders that exist and would not list, so a short list says it
    is short. why is None unless this platform has no place to look."""
    platform = platform or ("windows" if os.name == "nt" else ("mac" if sys.platform == "darwin" else sys.platform))
    home = home or os.path.expanduser("~")
    looked, dirs, unread = [], [], []
    if platform == "windows":
        roots = [saved_games] if saved_games else []
        if not roots:
            k = _known_saved_games()
            if k:
                roots.append(k)
            roots.append(os.path.join(os.environ.get("USERPROFILE") or home, "Saved Games"))
        for r in roots:
            d = os.path.join(r, SAVE_DIR_NAME)
            if d in looked:
                continue
            looked.append(d)
            if os.path.isdir(d):
                dirs.append(d)
    elif platform == "mac":
        for root in _bottle_roots(home):
            looked.append(root)
            bottles = _subdirs(root)
            if bottles is None:
                unread.append(root)
                continue
            for bottle in bottles:
                users = os.path.join(root, bottle, "drive_c", "users")
                people = _subdirs(users)
                if people is None:
                    unread.append(users)
                    continue
                for user in people:
                    d = os.path.join(users, user, "Saved Games", SAVE_DIR_NAME)
                    if os.path.isdir(d):
                        dirs.append(d)
    else:
        return [], [], "D2R saves are looked for on Windows and in a CrossOver bottle on a Mac; this PC is %s" % platform, []
    return dirs, looked, None, unread


def save_roster(dirs):
    """The characters this PC's save folders name -> {chars: [{name, ids}], d2s: [path], files, unread}. `ids` is HOW
    MANY account ids carry that name here (2 = a name deleted and made again), never the ids themselves. `unread` counts
    the save folders that would not list, so a short list says it is short."""
    by, d2s, files, unread = {}, [], 0, 0
    for d in dirs:
        try:
            names = os.listdir(d)
        except OSError:
            unread += 1
            continue
        for n in names:
            files += 1
            if n.lower().endswith(".d2s"):
                d2s.append(os.path.join(d, n))
                continue
            m = BIND_FILE.match(n)
            if m:
                by.setdefault(m.group(1), set()).add(m.group(2))
    chars = [{"name": k, "ids": len(v)} for k, v in sorted(by.items(), key=lambda kv: kv[0].lower())]
    return {"chars": chars, "d2s": sorted(d2s), "files": files, "unread": unread}


def saves(platform=None, home=None, saved_games=None):
    """THIS PC's characters as its save folders name them. -> dict, never raises.

      state "no-folder": no D2R save folder on this PC - chars None (UNKNOWN), never an empty list
      state "folder":    chars is what the folder names (a measured list; [] only when it names nobody)
      d2s None with the folder unknown; [] with d2sWhy = NO_D2S_SAY when the folder holds none; else each
      .d2s read through read(), with its verify."""
    try:
        dirs, looked, why, unread = save_dirs(platform, home, saved_games)
    except Exception as e:
        return {"ok": False, "state": "unknown", "chars": None, "d2s": None, "why": "looking for the save folder raised %s" % type(e).__name__}
    if why:
        # REG-3079 - a completed look with its reason (this platform has no place D2R keeps saves): ok, chars UNKNOWN
        return {"ok": True, "state": "unsupported", "chars": None, "d2s": None, "why": why}
    if not dirs and unread:
        return {"ok": False, "state": "unknown", "chars": None, "d2s": None, "folders": 0,
                "why": "%d folder%s where D2R saves can live would not list - UNKNOWN, not 'none'"
                       % (len(unread), "" if len(unread) == 1 else "s")}
    if not dirs:
        return {"ok": True, "state": "no-folder", "chars": None, "d2s": None, "folders": 0,
                "why": "no D2R save folder on this PC (looked in %d place%s)" % (len(looked), "" if len(looked) == 1 else "s")}
    r = save_roster(dirs)
    out = {"ok": True, "state": "folder", "folders": len(dirs), "chars": r["chars"], "d2s": [], "files": r["files"]}
    short = len(unread) + r["unread"]
    if short:
        out["unread"] = short
        out["why"] = ("%d folder%s would not list, so this list may be short"
                      % (short, "" if short == 1 else "s"))
    if not r["d2s"]:
        out["d2sWhy"] = NO_D2S_SAY
    for p in r["d2s"]:
        got = read(p)
        h = got.get("header") or {}
        out["d2s"].append({"file": os.path.basename(p), "ok": bool(got.get("ok")), "why": got.get("why"),
                           "name": h.get("name"), "className": h.get("className"), "level": h.get("level"),
                           "checksumOk": bool((got.get("verify") or {}).get("checksumOk"))})
    return out


def _label(it):
    return (it.get("runewordName") or it.get("uniqueName") or it.get("setName") or it.get("name")
            or it.get("code"))


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print("usage: python3 tv/d2s_read.py SAVE.d2s [--json]")
        return 2
    res = read(args[0])
    if "--json" in argv:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res["ok"] else 1
    h, v = res.get("header") or {}, res["verify"]
    print("%s — %s level %s, format %s" % (h.get("name"), h.get("className"), h.get("level"), h.get("version")))
    print("ok %s · %d/%s top-level items · ends on corpse tag %s · checksum %s%s"
          % (res["ok"], v.get("itemCount"), v.get("declaredItemCount"), v.get("endsOnCorpseTag"),
             v.get("checksumOk"), "" if res["ok"] else " · WHY: %s" % res["why"]))
    for it in res["items"]:
        where = it["location"] + ((" " + it["slot"]) if it.get("slot") else "") + (
            (" %s (%d,%d)" % (it["panel"], it["x"], it["y"])) if it.get("panel") else "")
        kids = ", ".join(k["code"] for k in it["socketed"])
        print("  %-26s %-9s %s%s" % (where, it.get("quality", "simple"), _label(it),
                                     (" [%s]" % kids) if kids else ""))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
