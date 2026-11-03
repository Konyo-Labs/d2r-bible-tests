"""THE ONE PLACE THAT SAYS WHAT A ROUTE COUNTS.

⚠⚠ WHY THIS EXISTS. Three route sets print a number per tab, and until v2484 each read a DIFFERENT
producer. The heart showed this, and every number in it was right:

    tab            chronicle routes   fleet lanes   roster routes
    runeword(s)         105                99            99
    set(s)              135               135           135
    unique(s)           398               403           403

chronicle_routes read the roster ARTIFACT (a file of name strings); fleet_routes and roster_routes
read the live TALLY. Konyo, on being shown the table: "sync and match them obivously.. no reason to
have this gap".

WHAT THE DEMOTED NUMBERS ACTUALLY ARE — neither is wrong and neither is deleted:
  · 105 is runeword_roster.json's length: 101 declared rows + 4 extra BARE forms. Both spellings
    are kept on purpose ("Spirit (sword)" and "Spirit") because a chronicle page prints the bare
    one. It was never a count of runewords. control_app.py already refuses to use it as a
    denominator, in as many words, and that refusal still stands.
  · 398 is unique_roster.json's length — every unique this board can put a NAME on. That roster
    is a different question from the chronicle number, which is the pin.

THE TRUE COUNT PER TAB, and where it comes from:
    runeword  99   var RUNEWORD_CHRONICLE_TOTAL  — his v2192 ruling, 2026-08-27
    set      135   the piece catalogue in bible.html — 34 sets, 135 distinct pieces
    unique   403   the chronicle pin in funiScan: 397 hunt cards + the 6 colossal jewels (Elad,
                   2026-11-03). The six quest items stay off. Nothing subtracts them again.

⚠ IT READS bible.html, NOT THE ARTIFACTS, so the artifacts stop being denominators and become
checked copies. And every failure returns None, never a fallback constant: a number nobody could
read is UNKNOWN, and UNKNOWN must not render as a total. [[unknown-stays-unknown]]

⚠ NOT the same file as tv/chronicle_total.py — that one BANKS the dated CASC measurement for
uniques (439/24/415/403/396) and is the evidence. This one is the reader the surfaces quote.
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")

#: Every spelling either producer emits -> the one key this module answers on. The two vocabularies
#: are real: ct.detect() says "unique", the model says "uniques", the fleet lanes say "runewords".
_ALIASES = {
    "runeword": "runeword", "runewords": "runeword",
    "set": "set", "sets": "set",
    "unique": "unique", "uniques": "unique",
}

#: The word printed after the number. ONE noun per key, because after this change all three
#: surfaces count the same thing — a different word on one of them would be the old bug in prose.
_NOUN = {
    "runeword": " in the chronicle",
    "set": " pieces in the chronicle",
    "unique": " in the chronicle",
}

_WHY = {
    "runeword": ("his v2192 ruling of 2026-08-27, and independently the size of RUNEWORD_TIP, the "
                 "catalogue that holds one key per runeword"),
    "set": ("the piece catalogue in bible.html — 34 sets holding 135 distinct pieces; the "
            "chronicle counts pieces, which is why this says pieces"),
    "unique": ("the chronicle pin in funiScan. The six quest items stay off the card list. "
               "The pin and the tally are the same number, so nothing subtracts them again"),
}


def canonical(key):
    """Any spelling -> the key this module answers on. -> str | None"""
    if not key:
        return None
    return _ALIASES.get(str(key).strip().lower())


def _src():
    try:
        return io.open(BIBLE, encoding="utf-8").read()
    except Exception:
        return None


def _balanced(s, start, open_ch, close_ch):
    """Span of a balanced bracket run from the first `open_ch` at/after start. -> str | None

    ⚠ STRING-AWARE, and it must be. Item names in this file carry apostrophes and parentheses
    ("Tal Rasha's Wrappings (Sorc)"), and a naive depth counter walks straight out of one array
    into the next — which is exactly how a count of runewords once came back as a count of runes.
    Returns None rather than a truncated block if it never balances. [[source-reading-guard]]
    """
    try:
        i = s.index(open_ch, start)
    except ValueError:
        return None
    depth = 0
    instr = None
    j = i
    n = len(s)
    while j < n:
        c = s[j]
        if instr:
            if c == "\\":
                j += 2
                continue
            if c == instr:
                instr = None
        elif c in "\"'":
            instr = c
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return s[i:j + 1]
        j += 1
    return None


def _int_after(s, pattern):
    """The single integer a declaration assigns. -> int | None (None when not EXACTLY one match)"""
    hits = re.findall(pattern, s)
    if len(hits) != 1:
        return None
    try:
        return int(hits[0])
    except Exception:
        return None


def _runeword_total(s):
    # his ruling, one assignment. `var RUNEWORD_CHRONICLE_TOTAL = 99;`
    return _int_after(s, r"var\s+RUNEWORD_CHRONICLE_TOTAL\s*=\s*(\d+)\s*;")


def _file_pin(s):
    """The unique chronicle pin. This is the number surfaces divide by. -> int | None

    The named declaration wins, then the single chronTotal assignment. Two different literals
    are UNKNOWN, not a vote. A comment that merely mentions the number does not match: the
    pattern demands `:` or `=`.
    """
    n = _int_after(s, r"var\s+UNIQUE_CHRONICLE_TOTAL\s*=\s*(\d+)\s*;")
    if n is not None:
        return n
    hits = re.findall(r"chronTotal\s*[:=]\s*(\d+)", s)
    if not hits:
        return None
    uniq = set(hits)
    if len(uniq) != 1:
        return None
    try:
        return int(next(iter(uniq)))
    except Exception:
        return None


def _quest_names(s):
    """The quest uniques kept off the card list. -> [str] | None

    None when the array cannot be read, including an empty array. The chronicle number
    does not depend on this list. These names are a card filter, not a second denominator.
    """
    m = re.search(r"var\s+_CHRON_QUESTS\s*=\s*\[(.*?)\]\s*;", s, re.S)
    if not m:
        return None
    names = []
    for a, b in re.findall(r'"([^"]*)"|\'([^\']*)\'', m.group(1)):
        v = (a or b).strip()
        if v:
            names.append(v)
    return names or None


def file_pin(s=None):
    """The unique chronicle pin. The tally is this same number. -> int | None"""
    if s is None:
        s = _src()
    if s is None:
        return None
    return _file_pin(s)


def quest_names(s=None):
    """The quest items the tally excludes. -> [str] | None"""
    if s is None:
        s = _src()
    if s is None:
        return None
    return _quest_names(s)


def quest_count(s=None):
    """How many quest items the tally excludes. -> int | None"""
    names = quest_names(s)
    return len(names) if names else None


def _unique_total(s):
    """The unique chronicle number. The pin and the tally are the same number. -> int | None

    The six quest names stay on the card filter in bible.html. Subtracting them here would
    print 391. An unreadable pin is UNKNOWN.
    """
    return _file_pin(s)


def set_pieces(s):
    """Distinct set-piece strings declared in bible.html. -> int | None"""
    decls = ("ITEM_SETS", "SET_PIECES_EXTRA", "SET_PIECES_EXTRA2")
    pieces = set()
    seen_any = False
    for name in decls:
        m = re.search(r"(?:const|var|let)\s+%s\s*=\s*\[" % name, s)
        if not m:
            continue
        blk = _balanced(s, m.end() - 1, "[", "]")
        if blk is None:
            # ⚠ THE WALK MUST ASSERT ON ITS OWN REACH. A block that never balanced means the scan
            # ran to end-of-file, and a count taken from that is a count of the rest of the file.
            return None
        # ⚠ THE KEY IS QUOTED IN ONE OF THE THREE, AND A BARE `pieces:` PATTERN MISSED IT ENTIRELY.
        # ITEM_SETS and SET_PIECES_EXTRA write `pieces:[...]`; SET_PIECES_EXTRA2 writes
        # `"pieces": [...]`. The bare pattern found 12 and 7 arrays and then ZERO in the third,
        # giving 81 pieces instead of 135 — a plausible-looking number from a scan that had
        # silently stopped seeing one of its three inputs. The count was the tell.
        for arr in re.finditer(r"[\"']?pieces[\"']?\s*:\s*\[", blk):
            inner = _balanced(blk, arr.end() - 1, "[", "]")
            if inner is None:
                return None
            for p in re.findall(r"\"((?:[^\"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)'", inner):
                v = (p[0] or p[1] or "").strip()
                if v:
                    pieces.add(v)
        seen_any = True
    if not seen_any:
        return None
    return len(pieces) or None


def total(key):
    """The ONE number every route set shows for this tab. -> int | None

    None means the producer could not be read, which is UNKNOWN — never 0, never a default.
    """
    k = canonical(key)
    if not k:
        return None
    s = _src()
    if s is None:
        return None
    if k == "runeword":
        return _runeword_total(s)
    if k == "unique":
        return _unique_total(s)
    if k == "set":
        return set_pieces(s)
    return None


def noun(key):
    """The unit word printed after the number. -> str"""
    return _NOUN.get(canonical(key) or "", "")


def why(key):
    """One sentence naming the ruling this number comes from. -> str"""
    return _WHY.get(canonical(key) or "", "")


def disagreements(rows, own_field="boardCount"):
    """Rows whose OWN reading differs from the producer. -> [ {route, lane, say} ]

    ⚠ THIS IS THE POINT OF THE WHOLE CHANGE. Making three surfaces quote one producer removes the
    contradiction from the screen; it does not make the underlying readings agree. If a lane's own
    number ever differs from the ruling, that is a fact worth saying OUT LOUD, naming BOTH numbers
    and the two different questions they answer — never quietly printing the loser.

    Shape matches what corroborate() already returns, so the existing ODD ONE OUT renderer draws it
    with no new UI. It BADGES; it never blocks. [[unknown-stays-unknown]]
    """
    out = []
    for r in (rows or []):
        if not isinstance(r, dict):
            continue
        key = r.get("key")
        k = canonical(key)
        if not k:
            continue
        mine = r.get(own_field)
        if mine is None:
            continue          # nobody looked is not a disagreement
        ruled = total(k)
        if ruled is None or int(mine) == int(ruled):
            continue
        out.append({
            "route": key,
            "lane": "count",
            "say": ("this lane reads %s and the chronicle counts %s. Both are real: %s. The row "
                    "shows the chronicle number; this is the other one, said out loud rather "
                    "than dropped." % (mine, ruled, why(k))),
        })
    return out


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    for k in ("runeword", "set", "unique"):
        print("%-9s -> %-5s %s" % (k, total(k), noun(k)))
