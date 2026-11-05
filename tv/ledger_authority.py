# -*- coding: utf-8 -*-
"""v2746 — THE LEDGER AUTHORITY: one manager over every ledger, and one answer per ledger.

Konyo, 2026-09-06, reading Dean's fleet card — a single warning band sitting above three rows:

    "for this deans chronicle the seed thing. how does that get removed what of him to do? like it
     should read he hasnt yet synced his uniques.. sets and runewords has been verified by him
     already and accepted.. maybe thats like a little toggle also needed to bypass this?"

and then, the shape he asked for:

    "a unified logic maybe or like a manager of them ... a unified ledger extracting from all
     ledgers with all data based on whats needed to be used and routed to the necesary routes and
     end routes based on whereever they came from regardless of the route reel. like the evidence
     is ledgers and proof and the manual is also a bypass we said like witnesses are not needed for
     a manual toggle me or dean.. or user."

and then, the part that makes a constant unusable as an answer:

    "_GRAIL_SEED 245 uniques but this is my owner seed.. and even that is so outdated.. its at
     292/403 we already said and sets 123/135.... it needs to auto update and not be stale"


=== THE DEFECT ===

`onOwnerSeed` is ONE BOOLEAN answering a THREE-LEDGER question. `control_ui.html:19562` renders
`t.onOwnerSeed === true` as one blanket band above SETS, UNIQUES and RUNEWORDS alike, so it cannot
say which of the three is actually inherited. The board computes it as `window._seedsBelongHere`
(`bible.html:4008`) — a whole-BOARD flag. It is not over-broad; it is UNSPECIFIC, which is a
different defect with a different fix.

MEASURED on his own live board 2026-09-06, and the three ledgers do not agree with each other:

    uniques    292/403   246 of the 311 chronicle rows are seed names carrying the SEED'S OWN DATE
    sets       123/135   108 of the 123 rows are seed names       ->  15 are his, found since
    runewords   99/99     99 of the 99 rows are seed names        ->   0 are his, and 99/99 is FULL

One flag over that is not a summary, it is an average of three different sentences.


=== WHY A CONSTANT CANNOT BE THE ANSWER ===

Every seed is a hardcoded literal transcribed from screenshots, and it CARRIES NO TIMESTAMP OF ITS
OWN. The uniques seed holds 245 names against a board at 292 — 47 finds behind — and nothing in the
file says when it was written. This module therefore refuses to hold a single seed number: every
size is PARSED out of `bible.html` on demand, by brace-matching and `json.loads`, never by regex and
never from a constant here. A seed that grows tomorrow must not make this file lie.

⚠ AND THE ONE AGE IT CAN OFFER IS NAMED FOR WHAT IT IS. `newestFindDate` is the newest find-date
RECORDED INSIDE the seed — it is not when the seed was transcribed, and that remains UNKNOWN rather
than being inferred from it. [[stale-reading]] — the age of the THING, not of the fetch.


=== THE MANUAL BYPASS, AND WHY IT NEEDS NO WITNESS ===

Konyo's ruling #166 stands: *"manual anything is enough witness obivously"*. A person declaring
whose chronicle this is supplies the one input no heuristic can — `bible.html:3997` is a HEURISTIC
("a board with a chronicle already on it is the one the seed was written for") and it is the whole
vector, because Dean would never type "KonyoEndgame".

So `manual_accept()` takes no corroboration. It records WHO, WHEN and WHICH LEDGER, and:

  ⛔ IT CANNOT CHANGE A COUNT. The ladder doctrine — a profile toggle must never change a count —
     applies whole. Every count in a `classify_*` result is computed before any manual record is
     consulted, and the record is applied by `_label_only()`, which writes exactly one key:
     `provenance`. `test_ledger_authority.py` proves it by running the classifier with and without
     the record and comparing every other field byte for byte.


=== WHAT IT REFUSES TO DO ===

  * IT NEVER WRITES A LEDGER. It reads stores and reports. The only file it writes is its own
    manual-bypass record. Repairing is `bible.html`'s job and happens on the person's own machine.
  * `0` IS MEASURED-AND-ZERO, `None` IS NOBODY LOOKED. A store that could not be read is None
    everywhere, never 0. [[unknown-stays-unknown]]
  * A NEGATIVE `beyondSeed` IS REPORTED, NEVER CLAMPED. Dean's runewords read 94 against a seed of
    99: `max(0, ...)` would print a tidy 0 and hide that five seeded rows are MISSING from his
    store. The deficit is the finding. [[zero-needs-a-denominator]]
  * NO ITEM NAME EVER CROSSES THE WIRE. `functions/api/console.js` declares that boundary and
    refuses even `ledgerName`/`seedLedger` as identity strings. Remote rows are therefore classified
    from COUNTS ONLY, and every derived figure is marked `derived: True` rather than dressed up as
    a measurement.
"""

import io
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "bible.html")
MANUAL_PATH = os.path.join(HERE, "ledger_manual.json")

#: the FIVE provenance answers, and none of them is a count.
#: ⚠ THIS SAID "four ... there is no fifth" UNTIL 2026-09-07. A fifth was added because the four
#: could not tell the truth about an empty store — see UNSYNCED. Changing the sentence rather than
#: leaving it to rot is the point: a comment that outlived its referent is this repo's most
#: repeated defect. [[label-outlived-referent]]
SEEDED = "SEEDED"      #: rows in this ledger come from the owner's hardcoded seed
SYNCED = "SYNCED"      #: this ledger's rows were earned on this board
MANUAL = "MANUAL"      #: a person declared it accepted — witness-free, ruling #166
UNKNOWN = "UNKNOWN"    #: nobody could look. NOT a pass, NOT a zero.
#: ⚠⚠ HIS CATCH, 2026-09-07, off his own fleet card: Dean's row read "UNIQUES **SYNCED** — that
#: board declared a ledger of its own, so the owner's seed never landed" directly above
#: "UNIQUES 0 / 403 found". *"maybe after he reset it it should read UNSYCNED until he resyncs it
#: again..?"* He is right, and the contradiction is exact: SYNCED means "this ledger's rows were
#: earned on this board", and with zero rows there is nothing that can have been earned. The label
#: outlived its referent. His SETS (130) and RUNEWORDS (96) rows are non-zero, so only the empty
#: ledger was incoherent — which is why the four answers looked sufficient for so long.
#: ⚠ IT IS NOT `UNKNOWN`. This module's own doctrine: "0 IS MEASURED-AND-ZERO, None IS NOBODY
#: LOOKED. A store that could not be read is None everywhere, never 0." Somebody DID look and
#: found nothing, so collapsing this into UNKNOWN would throw away a measurement.
UNSYNCED = "UNSYNCED"  #: it declared its own ledger and that ledger is EMPTY — nothing synced yet

PROVENANCE = (SEEDED, SYNCED, MANUAL, UNKNOWN, UNSYNCED)


#: ── THE LEDGER TABLE ────────────────────────────────────────────────────────────────────────
#: One row per ledger the fleet card draws a bar for, so "which ledger" is a table lookup rather
#: than a fourth copy of the same three names. `seeds` names the bible.html constants that feed it;
#: NO SIZE APPEARS HERE — sizes are parsed from the file at runtime, every time.
#:
#: ⚠ `_SET_SEED` WRITES INTO TWO STORES. bible.html:20618 floors `d2r_setPieces` AND stamps the same
#: names into `d2r_foundLog`, so 108 of his 419 foundLog rows are set pieces wearing a uniques
#: store's clothes. `alsoWrites` records that, and `classify_local` subtracts them out of the uniques
#: ledger — without it the uniques count is inflated by the whole sets seed.
#:
#: ⚠ `_RWV_SEED` IS THE FIFTH SEED AND IT IS NOT A COUNT. It seeds `d2r_rwVerify` with two FAIL
#: VERDICTS ({"Mania":"fail","Hysteria":"fail"}), not two finds. It is carried as `verdictSeed` so
#: the runewords ledger can say its verdicts were inherited too, and it is never added to a tally.
LEDGERS = (
    {"name": "uniques",
     "label": "uniques",
     # ⚠ NO SURFACE COUNTS len(d2r_foundLog) AS THE UNIQUES NUMERATOR, and it must not be compared
     # as if one did: that store legitimately holds 108 set-piece rows and other non-roster names,
     # so its length (419 on his board) was never a claim about uniques. The board's own numerator
     # is `chronFound`, which is ALREADY an intersection against its 403-name roster.
     "usesStoreLength": False,
     "seeds": ("_GRAIL_SEED", "_RULING_SEED"),
     "store": "d2r_foundLog",
     "alsoWrites": ("_SET_SEED",),      # set-piece rows living in this store, excluded from it
     "unfound": "d2r_grailUnfound",
     "verdictSeed": None,
     "verdictStore": None},
    {"name": "sets",
     "label": "set pieces",
     # ⚠ THIS ONE REALLY IS COUNTED BOTH WAYS TODAY. The fleet card's numerator is
     # `d2r_setPieces.length` (control_app.py:11847 via g() at :11715); the Sets tab counts
     # `pieces.filter(p => setPieces.has(p))` (bible.html:23696). They agree only while the store is
     # a SUBSET of the roster, and nothing checks that. This is the pair the invariant grades.
     "usesStoreLength": True,
     "seeds": ("_SET_SEED",),
     "store": "d2r_setPieces",
     "alsoWrites": (),
     "unfound": None,
     "verdictSeed": None,
     "verdictStore": None},
    {"name": "runewords",
     "label": "runewords",
     "usesStoreLength": True,
     "seeds": ("_RWC_SEED",),
     "store": "d2r_rwMade",
     "alsoWrites": (),
     "unfound": "d2r_rwUnmade",
     "verdictSeed": "_RWV_SEED",
     "verdictStore": "d2r_rwVerify"},
)

LEDGER_NAMES = tuple(d["name"] for d in LEDGERS)

#: Where each seed literal is declared. The anchor is matched EXACTLY and both halves are required,
#: so a rename cannot be mistaken for "this seed does not exist" — `seed_table()` reports a missing
#: anchor as a REFUSAL, not as a seed of size 0.
#:
#: ⚠ THE NAMES WERE THE TRAP. A first pass over this feature searched `_RW_SEED` / `_RUNE_SEED` /
#: `_RUNEWORD_SEED`, found nothing, and nearly reported "runewords are never seeded, the warning is
#: over-broad" — which is FALSE. The runeword seed is `_RWC_SEED` and it holds the entire 99-name
#: universe. A guard that cannot find its subject passes having examined nothing.
#: [[feedback-suspect-the-instrument]] [[source-reading-guard]]
SEED_ANCHORS = {
    "_GRAIL_SEED":  "const _GRAIL_SEED = {",
    "_RULING_SEED": "const _RULING_SEED = {",
    "_SET_SEED":    "const _SET_SEED = {",
    "_RWC_SEED":    "const _RWC_SEED = {",
    "_RWV_SEED":    "window._RWV_SEED = {",
}


# ── PARSING THE SEEDS OUT OF bible.html ──────────────────────────────────────────────────────

def _brace_object(src, anchor):
    """The `{...}` that follows `anchor`, brace-matched and STRING-AWARE. -> (text, line) | (None, None)

    ⚠ NOT A REGEX, AND THAT IS THE WHOLE POINT. Every seed is one line of JSON holding item names
    with apostrophes, escaped quotes (`\\"Gloom's Trap\\"`), unicode escapes (`\\u00b7`) and literal
    `}` inside no value but `{`/`}` counting for real. A non-greedy regex stops at the first `}`
    and reports a seed of 1; a greedy one swallows to the end of the file. Both answers look like
    numbers. This walks the braces and tracks whether it is inside a string, so an apostrophe in
    "Verdungo's Hearty Cord" cannot open a quote and a `}` inside a value cannot close the object.

    ⚠ AND IT IS ANCHORED AT BOTH ENDS BY CONSTRUCTION — there is no fixed-size window anywhere in
    this function. A `src[i:i+N]` slice past the end of a 245-entry literal reads as ABSENT.
    [[source-reading-guard]]
    """
    i = src.find(anchor)
    if i < 0:
        return None, None
    j = src.find("{", i)
    if j < 0:
        return None, None
    depth = 0
    in_str = False
    esc = False
    quote = ""
    k = j
    n = len(src)
    while k < n:
        c = src[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == quote:
                in_str = False
        else:
            if c == '"' or c == "'":
                in_str = True
                quote = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return src[j:k + 1], src.count("\n", 0, i) + 1
        k += 1
    return None, None


_DATE_RE = re.compile(r"^([A-Z][a-z]{2})\s+(\d{1,2}),\s+(\d{4})")
_MONTHS = {m: i + 1 for i, m in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"))}


def _newest_find_date(d):
    """The newest find-date RECORDED INSIDE a seed, as YYYY-MM-DD. -> str | None

    ⚠ THIS IS NOT THE SEED'S AGE AND MUST NEVER BE PRESENTED AS ONE. It is the latest date the seed
    claims a find happened on. When the seed was transcribed into bible.html is not recorded
    anywhere, and inferring it from this would be exactly the shape of a number nobody measured.
    `seed_table()` therefore reports `stampedAt: None` beside it, with the reason.
    [[stale-reading]] [[unknown-stays-unknown]]

    Values that carry no parseable date (the `_RWV_SEED` verdicts are "fail", and _RULING_SEED
    carries a deliberate `"?/27/2026 · ?:15 · partial"`) are skipped, never guessed at. A seed with
    no parseable date at all returns None.
    """
    best = None
    for v in (d or {}).values():
        m = _DATE_RE.match(str(v).strip())
        if not m:
            continue
        mon = _MONTHS.get(m.group(1))
        if not mon:
            continue
        try:
            cand = (int(m.group(3)), mon, int(m.group(2)))
        except (TypeError, ValueError):
            continue
        if best is None or cand > best:
            best = cand
    return "%04d-%02d-%02d" % best if best else None


_SEED_CACHE = {"key": None, "val": None}


def seed_table(path=None, force=False):
    """Every seed in bible.html, PARSED. -> dict

    {ok, why, source, seeds: {NAME: {n, names, dates, line, newestFindDate, stampedAt, stampedWhy}}}

    ⚠ NO SIZE IS EVER RETURNED FROM A CONSTANT IN THIS FILE. That is the requirement Konyo stated
    ("it needs to auto update and not be stale") and the reason this is a parser rather than a
    table: `_GRAIL_SEED` was 243 at v659, is 245 today, and the moment a name is added by hand every
    reader that hardcoded a number starts publishing a wrong one with full confidence.

    ⚠ A MISSING ANCHOR IS A REFUSAL, NOT AN EMPTY SEED. If a literal is renamed, this returns
    ok:False naming the seed — because "the seed holds nothing" and "I could not find the seed" are
    opposite facts, and a law reading the second as the first passes having examined nothing.
    """
    p = path or BIBLE
    try:
        st = os.stat(p)
        key = (p, int(st.st_mtime), int(st.st_size))
    except OSError as e:
        return {"ok": False, "why": "bible.html is unreadable: %s" % str(e)[:100],
                "source": p, "seeds": {}}
    if not force and _SEED_CACHE["key"] == key and _SEED_CACHE["val"] is not None:
        return _SEED_CACHE["val"]
    try:
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except Exception as e:
        return {"ok": False, "why": "bible.html could not be read: %s" % str(e)[:100],
                "source": p, "seeds": {}}

    seeds, missing, unparsed = {}, [], []
    for name, anchor in sorted(SEED_ANCHORS.items()):
        blk, line = _brace_object(src, anchor)
        if blk is None:
            missing.append(name)
            continue
        try:
            obj = json.loads(blk)
        except Exception as e:
            unparsed.append("%s (%s)" % (name, str(e)[:60]))
            continue
        if not isinstance(obj, dict):
            unparsed.append("%s (not an object)" % name)
            continue
        seeds[name] = {
            "n": len(obj),
            "names": sorted(obj.keys()),
            "dates": obj,
            "line": line,
            "newestFindDate": _newest_find_date(obj),
            # the honest half: nothing records when the literal was transcribed
            "stampedAt": None,
            "stampedWhy": "the seed is a hardcoded literal and carries no transcription "
                          "timestamp; newestFindDate is the newest date it RECORDS, which is a "
                          "different fact",
        }
    out = {"ok": not missing and not unparsed, "source": p, "seeds": seeds, "why": ""}
    if missing:
        out["why"] = ("seed literal(s) not found by their declared anchor: %s — renamed or moved. "
                      "Fix SEED_ANCHORS before trusting anything downstream; a parser that cannot "
                      "find its subject would otherwise report a seed of size 0."
                      % ", ".join(sorted(missing)))
    elif unparsed:
        out["why"] = "seed literal(s) found but not parseable: %s" % "; ".join(sorted(unparsed))
    if out["ok"]:
        _SEED_CACHE["key"] = key
        _SEED_CACHE["val"] = out
    return out


def ledger_spec(ledger):
    """-> (spec, None) | (None, why). An unknown ledger is REFUSED, never defaulted.

    Defaulting to `uniques` would answer confidently about a ledger nobody asked about, which is
    the failure `fleet_mask.ledger_spec` already records for the roster path.
    """
    name = str(ledger or "").strip().lower()
    for d in LEDGERS:
        if d["name"] == name:
            return dict(d), None
    return None, ("unknown ledger %r — this authority manages %s"
                  % (ledger, ", ".join(LEDGER_NAMES)))


def seed_names_for(ledger, table=None):
    """The UNION of seed names that can land in one ledger. -> (set, meta) | (None, why)

    ⚠ A UNION, NOT A SUM. `_GRAIL_SEED` (245) and `_RULING_SEED` (10) OVERLAP BY 9 — measured, not
    assumed — so the uniques seed is 246 names and not 255. Adding the two would over-count the
    seed's reach by nine and make nine of his own finds read as inherited.
    """
    spec, why = ledger_spec(ledger)
    if not spec:
        return None, why
    tbl = table if table is not None else seed_table()
    if not tbl.get("ok"):
        return None, tbl.get("why") or "the seeds could not be parsed"
    names, parts = set(), []
    for s in spec["seeds"]:
        row = tbl["seeds"].get(s)
        if row is None:
            return None, "seed %s is missing from the parse" % s
        names |= set(row["names"])
        parts.append({"seed": s, "n": row["n"], "line": row["line"],
                      "newestFindDate": row["newestFindDate"]})
    return names, {"parts": parts, "unionN": len(names),
                   "sumN": sum(p["n"] for p in parts),
                   "overlap": sum(p["n"] for p in parts) - len(names)}


# ── THE MANUAL BYPASS ────────────────────────────────────────────────────────────────────────
#
# Konyo's ruling #166: *"manual anything is enough witness obivously"*. This door takes NO
# corroboration, by design, for him or Dean or any user. What it takes instead is a RECORD.

MANUAL_V = 1


def _now_ms():
    return int(time.time() * 1000)


def _iso(ms):
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(ms) / 1000.0))
    except Exception:
        return None


def world_key(who):
    """The world a declaration belongs to: install id + profile. -> str ("" when unusable)

    Same shape as `control_app._route_key`, deliberately, so a manual record and a banked tally
    describe the SAME world. A record keyed on a nickname would follow the person between machines
    and accept a ledger they have never seen.

    ⚠⚠ AN EMPTY id IS REFUSED, AND THIS WAS A REAL HOLE CAUGHT BY ITS OWN LAW. `_route_key` happily
    returns "|main" for `{"p": "main"}` — truthy, and not equal to "|" — so a declaration made with
    a profile and no install id was ACCEPTED and would then have matched every id-less world at
    once. `_route_key` can afford that because a tally arrives from a route that always carries an
    id; a declaration is typed by a person and must not. Both halves are required here.
    """
    if not isinstance(who, dict):
        return ""
    ident = str(who.get("id") or "").strip()[:40]
    prof = str(who.get("p") or "").strip()[:16]
    if not ident or not prof:
        return ""
    return "%s|%s" % (ident, prof)


def manual_load(path=None):
    """-> {"v", "records": [...]} — an unreadable file is EMPTY-WITH-A-REASON, never a crash."""
    p = path or MANUAL_PATH
    if not os.path.exists(p):
        return {"v": MANUAL_V, "records": [], "why": "no manual declarations have been made"}
    try:
        with io.open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:
        # ⚠ A CORRUPT FILE IS NOT AN ABSENT ONE. Returning a clean empty list here would silently
        # revoke every declaration a person has made and re-flag their board as inherited.
        return {"v": MANUAL_V, "records": [], "corrupt": True,
                "why": "the manual record is unreadable (%s) — declarations are UNKNOWN, not "
                       "absent. Nothing is revoked; the labels fall back to measured provenance."
                       % str(e)[:90]}
    if not isinstance(d, dict) or not isinstance(d.get("records"), list):
        return {"v": MANUAL_V, "records": [], "corrupt": True,
                "why": "the manual record has an unexpected shape"}
    return d


def _manual_write(ledger, who, by, why, path, at, accepted):
    """Append ONE declaration row. -> dict. The single writer, so accept and revoke cannot drift."""
    spec, lwhy = ledger_spec(ledger)
    if not spec:
        return {"ok": False, "why": lwhy}
    key = world_key(who)
    if not key:
        return {"ok": False,
                "why": "a declaration must say which WORLD it is about — BOTH an install id and a "
                       "profile ({id, p}). A record missing either would match every world that "
                       "is also missing it, and accept a ledger on boards the declarer has never "
                       "seen."}
    row = {
        "v": MANUAL_V,
        "ledger": spec["name"],
        "world": key,
        "by": str(by or "")[:60],           # who declared it. Free text: he, Dean, or any user.
        "at": int(at if at is not None else _now_ms()),
        "why": str(why or "")[:400],
        "accepted": bool(accepted),
    }
    row["atIso"] = _iso(row["at"])
    p = path or MANUAL_PATH
    doc = manual_load(p)
    if doc.get("corrupt"):
        # refuse to write over a file we could not read — that would destroy the earlier record
        return {"ok": False, "why": "refusing to write: %s" % doc.get("why")}
    doc = {"v": MANUAL_V, "records": list(doc.get("records") or []) + [row]}
    try:
        tmp = p + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(doc, ensure_ascii=False, indent=1))
        os.replace(tmp, p)
    except Exception as e:
        return {"ok": False, "why": "the declaration could not be saved: %s" % str(e)[:100]}
    return {"ok": True, "record": row}


# ⚠ v3192 — WHY THIS IS STILL UNJOINED, MEASURED RATHER THAN ASSUMED.
#
# An audit and a fan-out both proposed the same one-line join: make control_app.grail_tally call
# `_LA.classify_row(out, world=own.get("route"))` so a declaration can be found. Checked on the
# live tree, and the prescription is wrong twice over:
#
#   · `own` comes from board_ownership(0), which returns {ok, why} ALONE while the board window is
#     shut — no world of any kind. `route` appears ZERO times in grail_tally.
#   · with the board shut, grail_tally never reaches the classify at all: `ledgerVerdict` comes
#     back None on this machine right now.
#
# And `world_key` is deliberately strict — install id + profile, refusing an empty id — precisely
# so a declaration cannot match every id-less world at once. Passing a guessed or empty world here
# would not join anything; it would make a declaration lookup that silently matches the wrong
# world, which is worse than one that finds nothing.
#
# SO THE JOIN IS REAL BUT ITS PREREQUISITE IS A WORLD, and the world needs the board to answer.
# Do it when the board window is open and the route key is in hand — not before.
# [[unknown-stays-unknown]] [[review-after-ship]]
def manual_accept(ledger, who, by="", why="", path=None, at=None):
    """Declare ONE ledger accepted on ONE world. Witness-free. -> dict

    Konyo: *"the manual is also a bypass we said like witnesses are not needed for a manual toggle
    me or dean.. or user."*

    ⛔⛔ THIS CANNOT CHANGE A COUNT, AND THE CODE IS ARRANGED SO IT COULD NOT IF IT TRIED. It writes
    one append-only record and returns. Nothing here reads, derives or emits a tally. The record is
    consumed in exactly one place — `_label_only()` — which assigns `provenance` and touches no
    other key. The ladder doctrine holds: a toggle changes what a row is CALLED, never what it
    counts. [[d2r-ladder-doctrine]]

    ⚠ APPEND-ONLY, AND A REVOCATION IS ITSELF A ROW. `accepted=False` writes a new record rather
    than deleting the old one, so "he never declared it" and "he declared it and changed his mind"
    stay different facts. An erased declaration is testimony destroyed.
    """
    return _manual_write(ledger, who, by, why, path, at, True)


def manual_revoke(ledger, who, by="", why="", path=None, at=None):
    """The other direction, as its own row. -> dict — see manual_accept's append-only note.

    ⚠ ONE WRITER. An earlier cut of this called manual_accept() and then re-wrote the file to flip
    the flag: two writes, and a crash between them would have left a REVOCATION recorded as an
    ACCEPTANCE — the worst possible direction for a record whose whole job is to say what a person
    actually declared. [[copy-drift]]
    """
    return _manual_write(ledger, who, by, why, path, at, False)


def manual_for(ledger, who, path=None):
    """The LATEST declaration for one world+ledger, or None. -> dict | None

    Last write wins, which is the same rule his chronicle already uses for a re-tick. A revocation
    is a later row, so it wins over the acceptance it follows without erasing it.
    """
    key = world_key(who)
    if not key:
        return None
    spec, _ = ledger_spec(ledger)
    if not spec:
        return None
    best = None
    for r in (manual_load(path).get("records") or []):
        if not isinstance(r, dict):
            continue
        if r.get("world") != key or r.get("ledger") != spec["name"]:
            continue
        if best is None or int(r.get("at") or 0) >= int(best.get("at") or 0):
            best = r
    return best if (best and best.get("accepted")) else None


def _label_only(row, declaration):
    """Apply a manual declaration to ONE ledger row. -> the same row.

    ⛔ THE ONLY MUTATION IN THIS MODULE THAT A USER TOGGLE CAN REACH, AND IT WRITES ONE KEY.
    `provenance` and the two record fields that say who said so. Every count — rows, seedRows,
    ownRows, beyondSeed, have, total — is already computed and is not touched, which is what makes
    "a toggle never changes a count" a property of the code rather than a promise in a comment.
    """
    if not declaration:
        return row
    row["provenance"] = MANUAL
    row["manual"] = {"by": declaration.get("by") or "", "at": declaration.get("at"),
                     "atIso": declaration.get("atIso"), "why": declaration.get("why") or ""}
    row["why"] = ("declared accepted by %s%s — a manual declaration needs no witness (ruling #166) "
                  "and changes no count, only what this ledger is called"
                  % (declaration.get("by") or "a user",
                     " on " + declaration["atIso"] if declaration.get("atIso") else ""))
    return row


# ── CLASSIFICATION ───────────────────────────────────────────────────────────────────────────

def _blank(spec, meta):
    """One ledger row with every count UNMEASURED. `None` is the starting state, not 0."""
    return {"ledger": spec["name"], "label": spec["label"], "store": spec["store"],
            "provenance": UNKNOWN, "why": "", "measured": False, "derived": False,
            "rows": None, "seedRows": None, "ownRows": None, "beyondSeed": None,
            "have": None, "total": None,
            "seedN": (meta or {}).get("unionN"),
            "seedParts": (meta or {}).get("parts"),
            "seedOverlap": (meta or {}).get("overlap"),
            "seedStale": None, "manual": None, "unfound": None, "verdicts": None}


#: ⚠⚠ v3313 — A SEED NAME COUNT AND A ROSTER-ROW COUNT ARE NOT THE SAME POPULATION, AND
#: SUBTRACTING THEM MANUFACTURES A PERMANENT FAULT. `uniques` publishes its live figure as
#: `funiScan().found` — a walk of the ROSTER asking `_ownedHas` of each row, which resolves a
#: store name to its canonical form before matching. A seed is a list of NAMES the boot floor
#: would write. The two can never be level: the seed legitimately carries alias spellings that
#: have no row of their own (the six `Latent <sunder>` forms are dropped by `_uniItems`, and
#: `Harlequin Crest (Shako)` resolves onto the row spelled `Harlequin Crest`), while his store
#: legitimately holds rows the seed never listed.
#:
#: MEASURED 2026-09-18 on his live board: seed 312 names, `chronFound` 309 rows, and of those 312
#: names ZERO are absent from his store. The gap is not missing work — it is the two figures
#: counting different things. The row read `+63 behind` before a sync and `-3 behind` after one,
#: and neither number named an action that would close it.
#:
#: ⚠ THE FACT WAS ALREADY RECORDED AND NOBODY ASKED. Every ledger declares `usesStoreLength`, and
#: `canonical_figure` already refuses the comparison on exactly that field — *"NOT A COMPARISON,
#: AND SAYING SO MATTERS"*. Two other sites subtracted anyway. [[the-unjoined-end]]
#:
#: ⚠ AND THE REAL FINDING SURVIVES. `sets` and `runewords` ARE store lengths, so their drift is a
#: true subtraction and stays graded — Dean's runewords read 94 against a seed of 99, five seeded
#: rows genuinely missing from his store. Exempting those would be the cure killing the patient.
def seed_drift(spec, seed_n, live):
    """How far a frozen seed sits from its live figure, or why no distance may be taken. -> dict

    Returns `comparable`, `drift`, `stale`, `why`. THREE STATES, and collapsing any two is the
    defect:

        comparable True  + drift int   the figures count one population; the subtraction is real
        comparable False + drift None  they count DIFFERENT populations — no distance exists
        comparable True  + drift None  they would compare, but nobody published a live figure

    ⚠ `comparable` is a property of the LEDGER, not of the reading, so it is decided before the
    live figure is looked at. A ledger that cannot be compared must say so even when the board is
    silent, or a dark board would read as "comparable, just unmeasured" and the exemption would
    vanish the moment anything went quiet. [[unknown-stays-unknown]]
    """
    out = {"drift": None, "stale": None, "comparable": None, "why": ""}
    if not isinstance(spec, dict):
        out["why"] = "no ledger spec was supplied, so whether these two figures may be " \
                     "subtracted is UNKNOWN"
        return out
    if not spec.get("usesStoreLength"):
        out["comparable"] = False
        out["why"] = ("%s does not publish len(%s) as its figure — it publishes a walk of the "
                      "ROSTER, which resolves each store name to a canonical row before matching. "
                      "A seed NAME COUNT and a roster-ROW count are different populations, so no "
                      "drift between them exists to report. This is NOT a fault and NOT an unknown "
                      "age: it is a subtraction that was never valid."
                      % (spec.get("name"), spec.get("store")))
        return out
    out["comparable"] = True
    if not isinstance(seed_n, int) or not isinstance(live, int):
        out["why"] = ("%s would compare (its figure is len(%s)), but no live figure was published, "
                      "so the drift is UNKNOWN rather than zero"
                      % (spec.get("name"), spec.get("store")))
        return out
    out["drift"] = live - seed_n
    out["stale"] = out["drift"] != 0
    out["why"] = ("%s is len(%s), the same population the seed lists, so the subtraction is real: "
                  "live %d against a seed of %d." % (spec.get("name"), spec.get("store"), live,
                                                     seed_n))
    return out


def _stale(seed_n, have, parts, spec=None):
    """How far behind the live tally the seed is, and the age it CANNOT establish. -> dict | None

    Konyo: *"_GRAIL_SEED 245 uniques but this is my owner seed.. and even that is so outdated..
    its at 292/403"*.

    ⚠ `behind` IS SIGNED. A seed LARGER than the live tally is not "0 behind"; it means rows the
    seed carries are absent from the store, which is a different fact and the one Dean's runewords
    are actually in (94 held against 99 seeded). Clamping at zero would print the tidy number and
    lose the finding.
    """
    if not isinstance(seed_n, int):
        return None
    # ⚠ v3313 — ASK THE SAME QUESTION `canonical_figure` ASKS. `behind` used to be taken for every
    # ledger; for one whose figure is a roster walk it is a category difference wearing an
    # arithmetic face, and it is the number that sent 67 names into the seed to close a gap that
    # cannot close. The caveat rides ON the row rather than beside it, so a reader cannot take
    # `behind` without it. [[the-unjoined-end]] [[unknown-stays-unknown]]
    _cmp = seed_drift(spec, seed_n, have) if isinstance(spec, dict) else None
    newest = None
    for p in (parts or []):
        d = p.get("newestFindDate")
        if d and (newest is None or d > newest):
            newest = d
    _comparable = (_cmp or {}).get("comparable")
    return {
        "seedN": seed_n,
        "liveHave": have if isinstance(have, int) else None,
        "comparable": _comparable,
        "comparableWhy": (_cmp or {}).get("why") or "",
        "behind": (None if _comparable is False
                   else ((have - seed_n) if isinstance(have, int) else None)),
        "newestFindDate": newest,
        "stampedAt": None,
        "why": ("the seed is a hardcoded literal with no transcription timestamp, so its AGE is "
                "UNKNOWN. The newest find-date it records is %s, which is not the same fact."
                % (newest or "not parseable from any entry")),
    }


def classify_local(own=None, path=None, table=None):
    """Per-ledger provenance for THIS board, MEASURED name by name. -> dict

    `own` is a `control_app.board_ownership(sample=0, dump_stores=True)` payload; it is fetched if
    not supplied. The full stores are needed because the question is per-ROW, and counts alone
    cannot answer it: 292 uniques is the same number whether 246 of them were inherited or none
    were.

    THE THREE BUCKETS, and the middle one is why this reads dates and not just names:

      seedRows    the name is in the seed AND the row carries the SEED'S OWN DATE STRING. The boot
                  floor writes `_gfl[n] = _GRAIL_SEED[n]` (bible.html:20595) and only when the key
                  is ABSENT, so a seed date is the floor's fingerprint.
      ownRows     the name is in the seed but the row carries a DIFFERENT date — the person ticked
                  it themselves before the floor could reach it. It is theirs.
      beyondSeed  the name is not in the seed at all. Unambiguously earned here.

    ⚠ A LIST STORE CARRIES NO DATES. `d2r_setPieces` is an array of names, so the middle bucket
    cannot exist for it and `datesAvailable` says so, rather than the absence quietly reading as
    "none of his sets are his own".
    """
    tbl = table if table is not None else seed_table()
    out = {"ok": False, "why": "", "scope": "local", "at": _now_ms(),
           "seedTable": {"ok": tbl.get("ok"), "why": tbl.get("why"),
                         "seeds": {k: {"n": v["n"], "line": v["line"],
                                       "newestFindDate": v["newestFindDate"],
                                       "stampedAt": None}
                                   for k, v in (tbl.get("seeds") or {}).items()}},
           "ledgers": []}
    if own is None:
        try:
            import control_app as ca
            own = ca.board_ownership(sample=0, dump_stores=True)
        except Exception as e:
            out["why"] = ("the board could not be asked: %s — every ledger is UNKNOWN, which is "
                          "not the same as clean" % str(e)[:100])
            own = None
    own = own if isinstance(own, dict) else {}

    # the board's own answers, quoted rather than re-derived
    out["ledgerName"] = own.get("ledgerName")
    out["seedLedger"] = own.get("seedLedger")
    out["onOwnerSeed"] = own.get("onOwnerSeed")
    out["owner"] = own.get("owner")
    out["route"] = own.get("route") if isinstance(own.get("route"), dict) else None
    counts = own.get("counts") if isinstance(own.get("counts"), dict) else {}
    stores = own.get("fullStores") if isinstance(own.get("fullStores"), dict) else {}

    def _store(key):
        """A store, parsed. -> (obj, why). Missing and unreadable are DIFFERENT answers."""
        if key not in stores:
            return None, "the board did not dump %s" % key
        raw = stores.get(key)
        if raw is None:
            return None, "%s is absent from this world" % key
        try:
            return json.loads(raw) if isinstance(raw, str) else raw, None
        except Exception as e:
            return None, "%s could not be parsed: %s" % (key, str(e)[:60])

    have_of = {"uniques": counts.get("chronFound"), "sets": counts.get("setPieces"),
               "runewords": counts.get("runewordsMade")}
    total_of = {"uniques": counts.get("chronTotal"), "sets": counts.get("setsTotal"),
                "runewords": counts.get("runewordsTotal")}

    for spec in LEDGERS:
        names, meta = seed_names_for(spec["name"], table=tbl)
        row = _blank(spec, meta if isinstance(meta, dict) else None)
        row["have"] = have_of.get(spec["name"])
        row["total"] = total_of.get(spec["name"])
        if names is None:
            row["why"] = "the seed could not be read: %s" % meta
            out["ledgers"].append(row)
            continue
        row["seedStale"] = _stale(len(names), row["have"], (meta or {}).get("parts"), spec)

        # rows the OTHER seeds wrote into this same store, so they are not counted as this ledger's
        foreign = set()
        for s in spec["alsoWrites"]:
            r = (tbl.get("seeds") or {}).get(s)
            if r:
                foreign |= set(r["names"])

        obj, swhy = _store(spec["store"])
        if obj is None:
            row["why"] = "%s — this ledger is UNKNOWN, not clean" % swhy
            out["ledgers"].append(row)
            continue

        if isinstance(obj, list):
            rows_map, dates_available = dict((n, None) for n in obj), False
        elif isinstance(obj, dict):
            rows_map, dates_available = obj, True
        else:
            row["why"] = "%s has an unexpected shape (%s)" % (spec["store"], type(obj).__name__)
            out["ledgers"].append(row)
            continue

        seed_dates = {}
        for s in spec["seeds"]:
            r = (tbl.get("seeds") or {}).get(s)
            if r:
                # LAST DECLARATION WINS, matching the board: _RULING_SEED is applied after
                # _GRAIL_SEED for the nine names they share.
                seed_dates.update(r["dates"])

        seeded = own_dated = beyond = 0
        for name, val in rows_map.items():
            if name in foreign:
                continue                       # a set piece sitting in d2r_foundLog
            if name in names:
                if not dates_available or str(val) == str(seed_dates.get(name)):
                    seeded += 1
                else:
                    own_dated += 1
            else:
                beyond += 1

        row["measured"] = True
        row["datesAvailable"] = dates_available
        row["rows"] = seeded + own_dated + beyond
        row["seedRows"] = seeded
        row["ownRows"] = own_dated
        row["beyondSeed"] = beyond
        row["foreignRowsExcluded"] = len(foreign & set(rows_map)) if foreign else 0

        if spec["unfound"]:
            u, _ = _store(spec["unfound"])
            row["unfound"] = len(u) if isinstance(u, (dict, list)) else None
        if spec["verdictSeed"] and spec["verdictStore"]:
            vs = (tbl.get("seeds") or {}).get(spec["verdictSeed"])
            v, _ = _store(spec["verdictStore"])
            if isinstance(v, dict) and vs:
                inherited = sum(1 for k, val in v.items()
                                if k in vs["dates"] and str(val) == str(vs["dates"][k]))
                row["verdicts"] = {"store": spec["verdictStore"], "seed": spec["verdictSeed"],
                                   "rows": len(v), "seedRows": inherited,
                                   "why": "verdicts, not finds — never added to a tally"}

        # ── THE VERDICT, and the counts above are already final before this runs ──────────
        if row["seedRows"] == 0 and row.get("rows") == 0:
            # ⚠ the old wording here read "all 0 row(s) were earned on this board", which is
            # vacuously true and reads as an achievement. An empty ledger has earned nothing.
            row["provenance"] = UNSYNCED
            row["why"] = ("this ledger is EMPTY — no row carries a seed name and no row was "
                          "earned here either, so nothing has been synced into it yet")
        elif row["seedRows"] == 0:
            row["provenance"] = SYNCED
            row["why"] = ("no row in this ledger carries a seed name with the seed's own date — "
                          "all %s row(s) were earned on this board" % row["rows"])
        elif own.get("onOwnerSeed") is True or own.get("seedsBelongHere") is True:
            row["provenance"] = SEEDED
            row["why"] = ("%s of %s row(s) are the owner's hardcoded seed; %s were earned here"
                          % (row["seedRows"], row["rows"], row["beyondSeed"] + row["ownRows"]))
        elif own.get("onOwnerSeed") is None:
            row["provenance"] = UNKNOWN
            row["why"] = ("%s row(s) match the seed, but this board did not say whether the seed "
                          "belongs here — that is UNKNOWN, not clean" % row["seedRows"])
        else:
            # not on the seed, yet seed-dated rows are present: they were inherited BEFORE the
            # board was named, and naming it stops new ones without removing these.
            row["provenance"] = SEEDED
            row["why"] = ("this board is no longer seedable, but %s row(s) carrying the seed's own "
                          "dates are still in the store from before it was named"
                          % row["seedRows"])

        _label_only(row, manual_for(spec["name"], out["route"], path=path))
        out["ledgers"].append(row)

    out["ok"] = any(r["measured"] for r in out["ledgers"])
    if not out["ok"] and not out["why"]:
        out["why"] = "no ledger could be measured on this board"
    return out


def classify_row(tally, world=None, path=None, table=None):
    """Per-ledger provenance for a FLEET row, from COUNTS ONLY. -> dict

    ⚠ EVERY FIGURE HERE IS DERIVED, AND SAYS SO. `functions/api/console.js` declares the boundary
    in as many words — "No item names ever cross this boundary — a roster says how many, never
    which" — and it refuses `ledgerName`/`seedLedger` as identity strings on top of that. So this
    console CANNOT see which of Dean's rows are seed names. What it can do is read the code: when
    `onOwnerSeed` is true the boot floor writes EVERY missing seed name into that store
    (`bible.html:20593`), so the seed's full size is present. `beyondSeed = have - seedN` follows
    from that, and it is marked `derived: True` rather than dressed as a measurement.

    ⚠⚠ AND A NEGATIVE IS KEPT. Dean's runewords read 94 against a seed of 99. `max(0, ...)` prints
    a comfortable 0; the real answer is that five seeded rows are MISSING from his store, which is
    a fact about his board nobody would otherwise see. [[zero-needs-a-denominator]]

    ⚠ WHEN `onOwnerSeed` IS FALSE OR None THE SUBTRACTION IS NOT VALID and is not performed —
    seedRows stays None. A board that never received the seed has no seed rows to subtract, and a
    board that would not say is UNKNOWN.
    """
    tbl = table if table is not None else seed_table()
    t = tally if isinstance(tally, dict) else {}
    on_seed = t.get("onOwnerSeed")
    out = {"ok": bool(t.get("ok")), "scope": "fleet", "at": t.get("at"),
           "onOwnerSeed": on_seed, "ledgers": []}
    for spec in LEDGERS:
        names, meta = seed_names_for(spec["name"], table=tbl)
        row = _blank(spec, meta if isinstance(meta, dict) else None)
        pair = t.get(spec["name"])
        if isinstance(pair, dict):
            row["have"] = pair.get("have")
            row["total"] = pair.get("total")
        if names is None:
            row["why"] = "the seed could not be read: %s" % meta
            out["ledgers"].append(row)
            continue
        seed_n = len(names)
        row["seedStale"] = _stale(seed_n, row["have"], (meta or {}).get("parts"), spec)

        # ⚠⚠ v3313 — THE THIRD COPY OF THE SAME SUBTRACTION, found by sweeping for the class after
        # fixing `_stale` and the FROZEN row builder. `beyondSeed` is `have - seed_n` too, so for a
        # ledger whose figure is a roster walk it is the same category difference wearing an
        # arithmetic face. It surfaced the moment the seed grew: a peer holding 249 against a seed
        # of 312 began reporting "63 seeded row(s) are MISSING from its store", which is a claim
        # about rows derived from a count of names. [[sweep-dont-ask]] [[copy-drift]]
        _cmp = seed_drift(spec, seed_n, row["have"])
        if on_seed is True and _cmp["comparable"] is False:
            # SEEDED is still the right provenance — the seed did land; what cannot be done is
            # split this board's figure into inherited and earned from counts alone.
            row["derived"] = True
            row["seedRows"] = seed_n
            row["beyondSeed"] = None
            row["provenance"] = SEEDED
            row["why"] = ("this board runs on the owner's seed (%s row(s)), but its own progress "
                          "cannot be separated out: %s So how much was earned there is UNKNOWN, "
                          "not zero and not the difference." % (seed_n, _cmp["why"]))
        elif on_seed is True and isinstance(row["have"], int):
            row["derived"] = True
            row["seedRows"] = seed_n
            row["beyondSeed"] = row["have"] - seed_n      # SIGNED. never clamped.
            row["provenance"] = SEEDED
            if row["beyondSeed"] < 0:
                row["why"] = ("the seed can supply %s row(s) and this board reports only %s — %s "
                              "seeded row(s) are MISSING from its store, so its own progress "
                              "cannot be separated out from counts alone"
                              % (seed_n, row["have"], -row["beyondSeed"]))
            else:
                row["why"] = ("of %s, the owner's seed supplies %s — about %s were earned on that "
                              "board. Derived from the counts, because no item name crosses the "
                              "fleet boundary." % (row["have"], seed_n, row["beyondSeed"]))
        elif on_seed is False and row.get("have") == 0:
            # ⚠⚠ HIS CATCH. "SYNCED" over "0 / 403 found" is a contradiction: SYNCED means the rows
            # were earned HERE, and there are none. `have == 0` is trustworthy — this module never
            # writes 0 for an unread store, only None. So this is measured-and-empty, and it gets
            # its own answer rather than borrowing one that claims work happened.
            row["provenance"] = UNSYNCED
            row["why"] = ("that board declared a ledger of its own, so the owner's seed never "
                          "landed — and its own store is EMPTY, so nothing has been synced into "
                          "it yet")
        elif on_seed is False:
            row["provenance"] = SYNCED
            row["why"] = "that board declared a ledger of its own, so the owner's seed never landed"
        else:
            row["provenance"] = UNKNOWN
            row["why"] = ("that console did not report whether the owner's seed belongs to it — "
                          "UNKNOWN, not clean")
        _label_only(row, manual_for(spec["name"], world, path=path))
        out["ledgers"].append(row)
    return out


def authority(path=None):
    """THE UNIFIED VIEW — every ledger on every world this console can see. -> dict

    Konyo: *"a unified ledger extracting from all ledgers with all data ... routed to the necesary
    routes and end routes based on whereever they came from regardless of the route reel."*

    ⚠ THE TWO SCOPES ARE NEVER MIXED. The local board is MEASURED name by name; fleet rows are
    DERIVED from counts, because their names cannot cross the boundary. Presenting them in one list
    without that distinction would let a derived figure be read as a measurement.
    """
    tbl = seed_table()
    out = {"ok": False, "at": _now_ms(), "seedTable": tbl.get("ok"),
           "seedWhy": tbl.get("why"), "local": None, "fleet": [], "why": ""}
    try:
        out["local"] = classify_local(path=path, table=tbl)
    except Exception as e:
        out["why"] = "the local board could not be classified: %s" % str(e)[:120]
    try:
        import control_app as ca
        fl = ca.fleet_presence() or {}
        rows = list(fl.get("online") or []) + list(fl.get("offline") or [])
        for m in rows:
            if not isinstance(m, dict):
                continue
            out["fleet"].append({
                "machine": m.get("machine"), "nickname": m.get("nickname"),
                "install": m.get("install"),
                "verdict": classify_row(m.get("tally"), world=None, path=path, table=tbl)})
    except Exception as e:
        out["fleetWhy"] = "the fleet could not be read: %s" % str(e)[:110]
    out["ok"] = bool(out["local"] and out["local"].get("ok")) or bool(out["fleet"])
    return out


# ── THE EXIT PATH ────────────────────────────────────────────────────────────────────────────
#
# Konyo asked this FIRST — *"how does that get removed what of him to do?"* — and a warning with no
# exit is a label, not a tool. Every step below is a real control in bible.html, cited by line, and
# the effect of each was read out of the code rather than assumed.

def exit_path(ledger=None):
    """What a person actually DOES to clear the seed flag on their own board. -> dict

    ⚠ THE ORDER IS LOAD-BEARING AND IT IS THE OPPOSITE OF THE OBVIOUS ONE. NAMING THE LEDGER COMES
    FIRST. bible.html:10063 records why in the code itself: the un-seed used to name the ledger LAST,
    so a throw part-way through left the store stripped and UNNAMED, `_D2R_LEDGER` resolved to
    'KonyoEndgame' again by the has-a-chronicle heuristic (bible.html:3997), the floors re-seeded
    everything that had just been removed, and the v1692 one-shot flag had already been deleted so
    that migration re-fired too. Naming first means a half-finished exit leaves a NAMED store.

    ⚠ AND "STOP IT HAPPENING" IS NOT "UNDO WHAT HAPPENED". Naming the ledger closes the door;
    the rows already written stay. Both steps exist because they are different jobs.
    """
    steps = [
        {"n": 1,
         "do": 'press "this browser is mine" on the claim bar',
         "where": "bible.html:4587 writes d2r_ownerClaim; :4600-4602 stamps d2r_ledgerName in the "
                  "same click when it is unset",
         "effect": "the board stops being a per-install guest world AND names its own ledger, so "
                   "_D2R_LEDGER can never again equal _SEED_LEDGER — the resolver's first branch "
                   "is `if (n) return n` (bible.html:3963), which makes _seedsBelongHere false "
                   "permanently (bible.html:4008)",
         "clears": "future seeding, on every ledger at once",
         "removesRows": False,
         "ledgers": list(LEDGER_NAMES),
         "reversible": "re-clicking is harmless; the claim is one key and nothing is copied or "
                       "renamed (bible.html:4586)"},
        {"n": 2,
         "do": 'press "🧭 Remove the inherited chronicle — keep what I found"',
         "where": "bible.html:9974, handler window._d2rUnseed at :9988",
         "effect": "names the ledger FIRST (:10064), then deletes only rows whose value still "
                   "equals the seed's own date (:10025) — from d2r_foundLog three times "
                   "(_GRAIL_SEED, _SET_SEED, _RULING_SEED) and from d2r_rwMade once, and clears "
                   "the seeded d2r_rwVerify verdicts. A row the person re-dated themselves does "
                   "not match and is kept.",
         "clears": "the rows already inherited, on all three ledgers",
         "removesRows": True,
         "ledgers": list(LEDGER_NAMES),
         "reversible": 'yes — a full snapshot is written to d2r_unseedBackup before anything is '
                       'removed (bible.html:10014), and "↩️ Undo the un-seed — put this browser '
                       'back" (bible.html:9978, window._d2rUnseedRestore at :10200) puts it back '
                       "including the ledger name"},
        {"n": 3,
         "do": 'press "RESET UNIQUES" in the uniques danger zone — ONLY if step 2 is too broad',
         "where": "bible.html:19567 window._uniqueResetAsk, write at window._uniqueResetDo",
         "effect": "clears the uniques chronicle and registers each cleared name in "
                   "d2r_grailUnfound so the boot floor cannot re-add it, and names the ledger if "
                   "it is unnamed (bible.html:19555-19559)",
         "clears": "the uniques ledger only — bible.html:19560 states that d2r_setPieces and "
                   "d2r_rwMade are never touched here",
         "removesRows": True,
         "ledgers": ["uniques"],
         "reversible": "partly — the dialog counts how many can be restored from the in-game "
                       "Chronicle and how many cannot, and says so before he presses it"},
        {"n": 4,
         "do": "or declare it accepted and keep the rows",
         "where": "ledger_authority.manual_accept(ledger, who, by=...)",
         "effect": "records who declared it, when, and for which ledger. Ruling #166 — a manual "
                   "declaration needs no witness. It changes the PROVENANCE LABEL only and cannot "
                   "touch a count.",
         "clears": "the warning, per ledger, without removing a single row",
         "removesRows": False,
         "ledgers": list(LEDGER_NAMES),
         "reversible": "yes — manual_revoke() writes a later row; nothing is erased"},
    ]
    if ledger:
        spec, why = ledger_spec(ledger)
        if not spec:
            return {"ok": False, "why": why}
        return {"ok": True, "ledger": spec["name"],
                "steps": [s for s in steps if spec["name"] in s["ledgers"]]}
    return {"ok": True, "ledger": None, "steps": steps}


# ══ NAMESPACES — WHICH WORLD A FIGURE WAS READ FROM ═══════════════════════════════════════════
#
# Konyo: *"and also not be mixing with the other consoles and profiles related"*.
#
# `window.LSR` (bible.html:4080) routes every forked `d2r_*` key by world, and the six worlds are:
#
#     owner  main    ''                 owner  ladder  'L·'
#     guest  main    'I·<id8>·'         guest  ladder  'IL·<id8>·'
#     cousin main    'W·'               cousin ladder  'WL·'          (the pre-v1499 shared world)
#
# A figure read WITHOUT the router reads whatever world the reader happens to be in, and a CDP probe
# is a GUEST (`navigator.webdriver && file:` flips `d2r_owned` from bare to `I·<id8>·`). So every
# figure this module returns names the world it came from, and `compare_figures` REFUSES a
# cross-world comparison rather than producing a number that describes two boards at once.

OWNER_MAIN = "owner-main"
OWNER_LADDER = "owner-ladder"
GUEST_MAIN = "guest-main"
GUEST_LADDER = "guest-ladder"
COUSIN_MAIN = "cousin-main"
COUSIN_LADDER = "cousin-ladder"

#: ⚠⚠ KEYS THAT ARE BARE IN EVERY WORLD BY CONSTRUCTION, AND WHY THAT IS NOT AN OVERSIGHT.
#: I read `d2r_ledgerName` being written RAW at five sites (bible.html:4601, 10065, 10261, 10265,
#: 10269) and ROUTED at one (:19557, through `LS = window.LSR || window.localStorage`), plus read
#: routed at :19556 and :19566 — and was about to report that the uniques reset names a PREFIXED key
#: on a ladder profile while the resolver reads the bare one, so the seed would refill after a reset
#: that promised in a dialog it would not.
#: ⛔ THAT IS REFUTED. `LSR.key()` (bible.html:4092-4096) prefixes ONLY keys in `_LP_FORKED` or
#: `_WP_FORKED`, and `d2r_ledgerName` is in NEITHER — measured. So routed and raw resolve to the
#: same bare key in all six worlds, and the comment at :4089 says so in as many words: "UI prefs
#: match no fork set -> bare in every world, so every world LOOKS identical and bare-key presence
#: can never be read as ownership." The inconsistency is cosmetic.
#: Recorded here so nobody spends the afternoon re-deriving it, and because the fact is LOAD-BEARING
#: in the other direction: a board's ledger name being namespace-INVARIANT is exactly what lets one
#: name identify one board across both its profiles. [[measured-true-read-wrong]]
NAMESPACE_INVARIANT_KEYS = {
    "d2r_ledgerName": "in neither _LP_FORKED nor _WP_FORKED, so LSR.key() returns it bare in all "
                      "six worlds — verified against bible.html:4092-4096, not assumed",
    "d2r_ownerClaim": "the claim is what DECIDES the world; it cannot live inside one",
}


def namespace_of(route):
    """Which of the six worlds a reading came from. -> dict

    `route` is the board's own `{id, p, m, pfx}` — it reports its world rather than being asked to
    guess. An absent or malformed route is UNKNOWN, never assumed to be the owner's: assuming owner
    is how a guest world's empty keys get published under his nickname.
    """
    if not isinstance(route, dict):
        return {"key": None, "label": None, "pfx": None, "profile": None,
                "why": "no route was reported, so which world these numbers describe is UNKNOWN"}
    pfx = route.get("pfx")
    prof = route.get("p")
    if not isinstance(pfx, str) or not isinstance(prof, str) or not prof:
        return {"key": None, "label": None, "pfx": pfx, "profile": prof,
                "why": "the route did not carry both a prefix and a profile"}
    ladder = (prof == "ladder")
    if pfx == "":
        key = OWNER_LADDER if ladder else OWNER_MAIN
    elif pfx.startswith("IL·") or (pfx.startswith("I·") and ladder):
        key = GUEST_LADDER
    elif pfx.startswith("I·"):
        key = GUEST_MAIN
    elif pfx.startswith("WL·") or (pfx.startswith("W·") and ladder):
        key = COUSIN_LADDER
    elif pfx.startswith("W·"):
        key = COUSIN_MAIN
    elif pfx == "L·":
        key = OWNER_LADDER
    else:
        return {"key": None, "label": None, "pfx": pfx, "profile": prof,
                "why": "prefix %r matches no known world — UNKNOWN, never defaulted to the "
                       "owner's" % pfx[:16]}
    return {"key": key, "label": key.replace("-", " "), "pfx": pfx, "profile": prof, "why": ""}


def compare_figures(a, b):
    """-> (ok, why). REFUSES to compare two figures from different worlds.

    ⚠ THIS IS A REFUSAL, NOT A WARNING, and it is the whole of what Konyo asked for with "not be
    mixing with the other consoles and profiles". Subtracting owner-main from guest-main produces a
    perfectly well-formed integer describing nothing. The only safe behaviour is to decline.
    """
    na = (a or {}).get("namespace") or {}
    nb = (b or {}).get("namespace") or {}
    ka, kb = na.get("key"), nb.get("key")
    if ka is None or kb is None:
        return False, ("one side does not know which world it was read from (%r vs %r), so the "
                       "comparison is UNKNOWN rather than equal" % (ka, kb))
    if ka != kb:
        return False, ("refusing to compare %s against %s — these are different worlds with "
                       "different stores, and a difference between them describes neither board"
                       % (ka, kb))
    return True, ""


# ══ FIGURES — EVERY NUMBER CARRIES ITS SOURCE, ITS WORLD AND ITS AGE ══════════════════════════
#
# Konyo: *"connect it all to the heart of the console so nothing becomes stale again"*.
#
# ⚠⚠ AGE OF THE THING, NOT OF THE FETCH, AND THIS IS THE SINGLE MOST LIKELY WAY FOR THIS WHOLE FIX
# TO BE QUIETLY VACUOUS. Re-parsing bible.html gives a FRESH READ of an EQUALLY OLD VALUE. The seed
# has no transcription timestamp anywhere, so its age is not merely unknown today — it is
# structurally unmeasurable, and a watchdog that timed the read would report every seed as seconds
# old forever while it drifted by fifty finds. [[stale-reading]] [[unknown-stays-unknown]]
#
# ⇒ SO A FROZEN CONSTANT IS GRADED BY **DRIFT**, NOT BY AGE. You cannot date the seed; you CAN
#   measure how far it has fallen behind the live figure. Both travel, and neither is presented as
#   the other: `ageKnown: False` with `drift: 46`.

FROZEN = "frozen-constant"     #: a hardcoded literal. Age UNMEASURABLE; graded by DRIFT.
LIVE = "live-read"             #: read from the running board just now
BEACON = "beacon"              #: another machine's heartbeat; as old as its `at`
DECLARATION = "declaration"    #: a person said so; old is fine, that is what a record is for
DERIVED = "derived"            #: computed from other figures; no older than its oldest input

SOURCE_KINDS = (FROZEN, LIVE, BEACON, DECLARATION, DERIVED)

#: ⚠ THE THRESHOLD IS DERIVED FROM THE PIPELINE IT GRADES, NOT INVENTED. A threshold above the
#: ceiling never fires and a threshold below the floor fires constantly; both are indistinguishable
#: from no threshold at all. [[feedback-threshold-above-the-ceiling]]
#: The real periods, read out of control_app rather than restated: the beacon fires every 240 s
#: (control_app.py:10870, :24520), `_TALLY_TTL_S` caches the tally, and `fleet_presence` caches the
#: roster for 60 s. A HEALTHY figure can therefore be that sum old through no fault of anyone, so
#: the stale line is a multiple of the whole pipeline and `beacon_ceiling_ms()` shows its arithmetic.
BEACON_PERIOD_S = 240.0
FLEET_CACHE_S = 60.0
STALE_MULTIPLE = 3


def beacon_ceiling_ms():
    """The oldest a HEALTHY beacon figure can be, with its arithmetic. -> dict

    Read from control_app where the constant lives, so the two cannot drift apart. If it cannot be
    read the fallback is named as a fallback, and the whole figure is marked `derivedFrom` so a
    reader can see the threshold was not measured.
    """
    tally_ttl, how = None, "control_app._TALLY_TTL_S"
    try:
        import control_app as _ca
        tally_ttl = float(getattr(_ca, "_TALLY_TTL_S"))
    except Exception:
        tally_ttl, how = 180.0, "a FALLBACK — control_app could not be read, so this threshold " \
                                "is not measured against the live pipeline"
    ceiling = (BEACON_PERIOD_S + tally_ttl + FLEET_CACHE_S) * 1000.0
    return {"ceilingMs": ceiling, "staleMs": ceiling * STALE_MULTIPLE,
            "parts": {"beaconPeriodS": BEACON_PERIOD_S, "tallyTtlS": tally_ttl,
                      "fleetCacheS": FLEET_CACHE_S, "multiple": STALE_MULTIPLE},
            "how": how}


def figure(value, source, kind, namespace=None, at=None, drift=None, why=""):
    """One number, with everything needed to judge whether it may be believed. -> dict

    ⚠ `ageKnown` IS NOT `at is not None` DRESSED UP. A frozen constant is `ageKnown: False`
    PERMANENTLY, even if someone later stamps an `at` on the read — because the read's time is not
    the value's time. The kind decides, not the presence of a timestamp.
    """
    now = _now_ms()
    age_known = kind not in (FROZEN,) and isinstance(at, (int, float)) and at > 0
    return {
        "value": value,
        "source": source,
        "kind": kind,
        "namespace": namespace,
        "at": int(at) if isinstance(at, (int, float)) and at > 0 else None,
        "ageMs": int(now - at) if age_known else None,
        "ageKnown": bool(age_known),
        "drift": drift,
        "why": why or ("this is a hardcoded literal: re-reading it makes the READ fresh and leaves "
                       "the VALUE exactly as old. Nothing records when it was transcribed, so its "
                       "age is UNKNOWN and it is graded by DRIFT instead."
                       if kind == FROZEN else ""),
    }


# ══ HOW A BOARD CAME TO BE NAMED ══════════════════════════════════════════════════════════════

NAMED_BY_HAND = "NAMED_BY_HAND"            #: someone typed a name of their own
AUTO_NAMED = "AUTO_NAMED"                  #: a post-v2692 claim / un-seed / reset stamped Ledger-xxxxxxxx
UNNAMED_WITH_DATA = "UNNAMED_WITH_DATA"    #: ⚠ THE ACTIONABLE STATE — standing contamination
UNNAMED_EMPTY = "UNNAMED_EMPTY"            #: honest new board; the heuristic gives it a new ledger
NAME_UNKNOWN = "UNKNOWN"                   #: nobody could look

NAME_STATES = (NAMED_BY_HAND, AUTO_NAMED, UNNAMED_WITH_DATA, UNNAMED_EMPTY, NAME_UNKNOWN)

_AUTO_NAME = re.compile(r"^Ledger-[0-9A-Za-z]{1,8}$")

_MISSING = object()


def name_state(own, stored_name=_MISSING):
    """Which of the five naming states a board is in. -> dict

    THE POPULATION THIS EXISTS FOR: boards claimed BEFORE v2692 shipped. bible.html:4596-4599 states
    the exception verbatim — "a board already claimed BEFORE THIS SHIPPED keeps its unnamed-with-data
    reading, WHICH IS WHAT PROTECTS HIS OWN CHRONICLE." Such a board never received the auto-stamp,
    so `d2r_ledgerName` is unset, and the has-a-chronicle heuristic (bible.html:3997) re-derives
    'KonyoEndgame' on EVERY BOOT. It is a standing condition, not a one-time contamination.

    ⚠ AND THERE IS DELIBERATELY NO MIGRATION. A blanket one would rename KONYO'S board too — it is
    unnamed-with-data by the very same test — and stop his chronicle floor restoring his finds. That
    is the v2680 silent subtraction. The circularity is real, and only a person can break it, which
    is why `manual_accept()` exists.

    ⚠⚠ THE CONSOLE CANNOT ANSWER THIS TODAY, AND SAYING SO IS THE POINT. `board_ownership` publishes
    `ledgerName`, but control_app.py:11824 defines it as
        ledgerName = window._D2R_LEDGER
    which is the RESOLVED value, not the stored key — an UNNAMED board with a chronicle resolves to
    'KonyoEndgame' and reports exactly what a hand-named one reports. `d2r_ledgerName` is also absent
    from `_collectProgress()`'s dump (measured on his live board). So the field is named for a key it
    does not carry. [[label-outlived-referent]]
    `stored_name` is therefore an EXPLICIT argument: pass the raw key when the payload gains it (see
    the patch spec), and until then this DERIVES what it honestly can and returns UNKNOWN for the
    rest rather than guessing.
    """
    own = own if isinstance(own, dict) else {}
    route = own.get("route") if isinstance(own.get("route"), dict) else None
    ns = namespace_of(route)
    resolved = own.get("ledgerName")
    seed_ledger = own.get("seedLedger")
    on_seed = own.get("onOwnerSeed")
    if on_seed is None:
        on_seed = own.get("seedsBelongHere")
    counts = own.get("counts") if isinstance(own.get("counts"), dict) else {}
    rows = sum(int(counts.get(k) or 0)
               for k in ("foundLog", "owned", "setPieces") if isinstance(counts.get(k), int))
    has_data = rows > 0 if counts else None

    out = {"state": NAME_UNKNOWN, "namespace": ns, "resolvedLedger": resolved,
           "seedLedger": seed_ledger, "storedName": None, "storedNameKnown": False,
           "rows": rows if counts else None, "why": "", "actionable": False}

    # ── the answer we can only give when the RAW key is supplied ────────────────────────────
    if stored_name is not _MISSING:
        out["storedNameKnown"] = True
        nm = str(stored_name or "").strip()
        out["storedName"] = nm or None
        if not nm:
            if has_data:
                out["state"] = UNNAMED_WITH_DATA
                out["actionable"] = True
                out["why"] = ("this board has never stored a ledger name and holds %d row(s), so "
                              "bible.html:3997's has-a-chronicle heuristic re-derives %r on every "
                              "boot and the seed floor refills it. Claimed before v2692, which "
                              "never auto-stamped." % (rows, seed_ledger or "the seed ledger"))
            elif has_data is False:
                out["state"] = UNNAMED_EMPTY
                out["why"] = ("unnamed and empty — the heuristic gives this board a NEW ledger, "
                              "which is the honest answer for a board that has found nothing")
            else:
                out["why"] = "unnamed, but the row counts were not reported, so which unnamed " \
                             "state this is stays UNKNOWN"
            return out
        if _AUTO_NAME.match(nm):
            out["state"] = AUTO_NAMED
            rid = str((route or {}).get("id") or "")
            out["autoStampMatchesInstall"] = (rid[:8] == nm.split("-", 1)[1][:8]) if rid else None
            out["why"] = ("stamped automatically by a claim (bible.html:4601), an un-seed "
                          "(:10065) or a uniques reset (:19557). The resolver's first branch is "
                          "`if (n) return n`, so the seed can never land here again.")
            return out
        out["state"] = NAMED_BY_HAND
        out["why"] = "this board carries a name of its own, so the seed cannot resolve to it"
        return out

    # ── DERIVATION, when only the resolved value is available ───────────────────────────────
    # An AUTO_NAMED board resolves to 'Ledger-xxxxxxxx', never to the seed ledger, so
    # `_seedsBelongHere` is false there by construction. Therefore onOwnerSeed TRUE narrows the
    # board to exactly two states: it literally stored the seed ledger's name (only its owner would
    # ever type that), or it is UNNAMED_WITH_DATA. Those two cannot be separated from here.
    if on_seed is True and has_data:
        out["state"] = UNNAMED_WITH_DATA
        out["actionable"] = True
        out["why"] = ("DERIVED, not measured: this board resolves to the seed ledger %r while "
                      "holding %d row(s). An auto-stamped board resolves to Ledger-xxxxxxxx and "
                      "could not be here, so it is either unnamed-with-data or a board whose owner "
                      "typed the seed ledger's own name. Only the seed's own owner would type it. "
                      "⚠ To separate the two the console must publish the RAW d2r_ledgerName key; "
                      "it publishes window._D2R_LEDGER instead (control_app.py:11824)."
                      % (seed_ledger or "?", rows))
        return out
    if on_seed is False:
        out["state"] = NAME_UNKNOWN
        out["why"] = ("this board does not resolve to the seed ledger, so it is named or is a "
                      "guest — but which, and by hand or automatically, needs the raw key")
        return out
    out["why"] = ("nothing said whether the seed belongs here, and the raw ledger-name key was not "
                  "supplied — UNKNOWN, which is not the same as clean")
    return out


# ══ THE CANONICAL FIGURE — ONE SOURCE, ONE COUNTING RULE, PER LEDGER ══════════════════════════

#: Konyo: *"sets also needs to be fetched from the right data so it also renders like the sets tab
#: 123/135 counter"*. So each ledger declares ONE store, ONE denominator and ONE counting rule, and
#: both surfaces read this instead of each computing its own.
#:
#: THE RULE IS `|roster ∩ store|`, NOT `len(store)`, AND THE DIFFERENCE IS NOT ACADEMIC. The fleet
#: card's numerator is `d2r_setPieces.length` (control_app.py:11847 via g() at :11715) while the
#: Sets tab counts `pieces.filter(p => setPieces.has(p))` (bible.html:23696). They agree only while
#: the store is a SUBSET of the roster, and nothing checks that. `len(store)` can exceed the
#: denominator; the intersection cannot. A numerator that can pass its own denominator is not a
#: progress figure. MEASURED on his live store: 123 == 123, so the divergence is LATENT here — which
#: is exactly why a gate must exercise the direction his data never takes.
#: [[gate-blind-to-unexercised-input]]
COUNT_RULE = "roster-intersect-store"


def ledger_figure(ledger, own=None, table=None):
    # ⚠ NAMED `ledger_figure`, NOT `canonical*`, AND THE RENAME IS THE HONEST FIX RATHER THAN A
    # DODGE. tv/test_resolver_ratchet.py is a RATCHET on NAME RESOLVERS — places that answer "what
    # is this thing CALLED" without asking one_name — and it matches on SHAPE (`def canonical*(`)
    # deliberately, because "a name is how these get missed". This function answers a different
    # question entirely: what is this ledger's canonical FIGURE, |roster n store|. It resolves no
    # names at all. Baselining it would have diluted a ratchet whose whole value is that it may
    # only FALL; renaming it makes the name describe the work. Caught by CI, not by the pre-push,
    # which runs three suites and not run_gates.py.
    # ⚠ `canonical_figure` WAS NOT ENOUGH — the pattern is `canonical\w*`, so it still matched. The
    # concept is still "the canonical figure" and the messages still say so; it is the FUNCTION NAME
    # that must not advertise a canonicaliser, because that is what the ratchet reads.
    """THE authoritative figure for one ledger, with its rule stated. -> dict

    ⚠ IT DOES NOT FALL BACK TO `len(store)` WHEN THE ROSTER IS MISSING. An unreadable roster means
    the denominator is unknown, and a numerator counted by a different rule under the same label is
    the whole defect. Both numbers are returned when both can be had — never averaged, never
    silently one of them. [[feedback-contradiction-is-the-finding]]
    """
    spec, why = ledger_spec(ledger)
    if not spec:
        return {"ok": False, "why": why}
    own = own if isinstance(own, dict) else {}
    ns = namespace_of(own.get("route") if isinstance(own.get("route"), dict) else None)
    out = {"ok": False, "ledger": spec["name"], "store": spec["store"], "rule": COUNT_RULE,
           "namespace": ns, "byIntersection": None, "byStoreLength": None,
           "agree": None, "total": None, "why": ""}

    stores = own.get("fullStores") if isinstance(own.get("fullStores"), dict) else {}
    raw = stores.get(spec["store"])
    if raw is None:
        out["why"] = ("the board did not dump %s, so this ledger's canonical figure is UNKNOWN — "
                      "not zero, and not the other surface's number" % spec["store"])
        return out
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as e:
        out["why"] = "%s could not be parsed: %s" % (spec["store"], str(e)[:70])
        return out
    names = set(obj) if isinstance(obj, (dict, list)) else None
    if names is None:
        out["why"] = "%s has an unexpected shape (%s)" % (spec["store"], type(obj).__name__)
        return out
    out["byStoreLength"] = len(obj)
    out["usesStoreLength"] = spec["usesStoreLength"]

    # what the BOARD itself publishes for this ledger — an independent third number
    counts = own.get("counts") if isinstance(own.get("counts"), dict) else {}
    board_have = {"uniques": counts.get("chronFound"), "sets": counts.get("setPieces"),
                  "runewords": counts.get("runewordsMade")}.get(spec["name"])
    board_total = {"uniques": counts.get("chronTotal"), "sets": counts.get("setsTotal"),
                   "runewords": counts.get("runewordsTotal")}.get(spec["name"])
    out["boardHave"] = board_have
    out["boardTotal"] = board_total

    roster, rwhy = _roster_for(spec["name"])
    if roster is None:
        # ⚠ HONEST DEGRADATION, NAMED — NOT A SILENT CHANGE OF METHOD. Without a roster there is no
        # intersection to take, so the rule genuinely becomes store-length and `rule` SAYS SO. A
        # figure counted by a different rule under an unchanged label is the whole defect here.
        out["rule"] = "store-length"
        out["ruleWhy"] = ("this machine has no %s roster (%s), so no intersection can be taken. "
                          "The figure is the store's length and the rule is relabelled to match — "
                          "it is NOT presented as the intersection." % (spec["name"], rwhy))
        out["total"] = board_total
        out["value"] = out["byStoreLength"]
        out["ok"] = board_total is not None
        out["why"] = out["ruleWhy"]
        out["boardAgrees"] = (board_have == out["value"]) if isinstance(board_have, int) else None
        return out

    out["total"] = len(roster)
    out["byIntersection"] = len(names & set(roster))
    out["outsideRoster"] = sorted(names - set(roster))[:8]
    out["outsideRosterN"] = len(names - set(roster))
    out["ok"] = True
    out["value"] = out["byIntersection"]

    # ⚠ THE THIRD NUMBER, AND IT IS THE ONE THAT MATTERS. `byIntersection` is computed HERE, from
    # the raw store and a roster file on this disk; `boardHave` was computed INSIDE the board by its
    # own code against its own roster. Two independent walks over one ledger. MEASURED on his live
    # board: uniques 292 == 292 and sets 123 == 123 — which is what makes the sets figure below
    # trustworthy rather than merely self-consistent. [[feedback-verify-not-proxy]]
    out["boardAgrees"] = (board_have == out["byIntersection"]) if isinstance(board_have, int) else None
    if isinstance(board_total, int) and board_total != out["total"]:
        out["rosterDrift"] = ("the board counts against %d and this machine's roster holds %d — "
                              "the denominators are different rosters, so a percentage from one "
                              "must never be drawn against the other"
                              % (board_total, out["total"]))

    if not spec["usesStoreLength"]:
        # ⚠ NOT A COMPARISON, AND SAYING SO MATTERS. Nothing publishes len(store) for this ledger,
        # so "the methods disagree" would be a finding about a method nobody uses. `agree` stays
        # None — UNKNOWN by non-applicability, never a false red. [[unknown-stays-unknown]]
        out["agree"] = None
        out["why"] = ("|roster ∩ store| = %s. len(store) is %s and is NOT compared: no surface "
                      "uses it as this ledger's numerator (%s legitimately holds other rows). "
                      "The board's own figure is %s — %s."
                      % (out["byIntersection"], out["byStoreLength"], spec["store"], board_have,
                         "they AGREE" if out["boardAgrees"] else
                         ("they DISAGREE" if out["boardAgrees"] is False else "it did not say")))
        return out

    out["agree"] = (out["byIntersection"] == out["byStoreLength"])
    if not out["agree"]:
        out["why"] = ("the two methods DISAGREE: |roster ∩ store| = %d and len(store) = %d, "
                      "because %d row(s) in this store are not on the roster. The canonical figure "
                      "is the intersection — a numerator that can exceed its own denominator is "
                      "not a progress figure. Both are reported; neither is averaged."
                      % (out["byIntersection"], out["byStoreLength"], out["outsideRosterN"]))
    else:
        out["why"] = ("both methods agree at %d, so the divergence is LATENT on this board rather "
                      "than absent — which is exactly why a gate must exercise the direction his "
                      "data never takes" % out["byIntersection"])
    return out


def _roster_for(ledger):
    """The ordered roster for one ledger. -> (names, why). UNREADABLE IS NOT EMPTY.

    Delegates to fleet_mask, which already owns the roster files, rather than opening them again —
    two readers of one roster is two things that drift apart. [[copy-drift]]
    """
    try:
        import fleet_mask as _fm
    except Exception as e:
        return None, "fleet_mask will not import (%s)" % str(e)[:60]
    try:
        roster, _fp = _fm.load_roster_for(ledger)
    except Exception as e:
        return None, "the roster could not be loaded (%s)" % str(e)[:60]
    if not roster:
        return None, "this machine has no roster for %r, so the denominator is UNKNOWN" % ledger
    return roster, ""


# ══ THE BACKUP — THE LIVE TRUTH WITH A REAL AGE, WHICH THE SEED IS NOT ════════════════════════
#
# Konyo's instruction: the seed must not be "refreshed"; the authority must PREFER THE BACKUP, and
# the card must stop presenting a June constant as his current chronicle.
#
# The two sources are not the same kind of thing and must never be swapped for one another:
#
#     THE SEED     245/108/99, hardcoded in bible.html, NO TIMESTAMP ANYWHERE.
#                  It is a FLOOR — the minimum the boot path re-asserts — not a reading.
#     THE BACKUP   ~/d2r_ledger_backups, keyed by ROUTE, carrying `takenAt` and `allStores`.
#                  MEASURED on his tree: 62 restore points, newest 43.8 min old, cadence 15-25 min,
#                  counts chronFound 292 · setPieces 123 · runewordsMade 99.
#
# So the backup is the live truth WITH an age, and the seed is a frozen floor WITHOUT one. Preferring
# the backup is not a fallback ordering — it is the difference between a reading and a constant.

BACKUP = "backup"              #: a restore point; a real reading with a real timestamp
BACKUP_DIR = os.path.expanduser("~/d2r_ledger_backups")

#: ⚠⚠ THE SIX KEYS `_collectProgress()` DELIBERATELY NEVER EXPORTS (bible.html, its `PTRS` map).
#: THIS LIST IS WHAT MAKES AN ABSENCE READABLE. `d2r_ownerClaim` is missing from every dump on his
#: board and he is unquestionably the owner — so absence there proves nothing. `d2r_ledgerName` is
#: NOT in this list, and the export rule is `if (LSR.key(bare) === rk) out[bare] = ...`, which the
#: key satisfies in every world (it is in neither fork set). So its absence from a dump IS evidence
#: that the key does not exist in the store.
#: Without this distinction the same missing key would mean two opposite things and nothing could
#: tell them apart. [[feedback-silence-is-not-evidence]] [[zero-needs-a-denominator]]
PROGRESS_DUMP_EXCLUDES = frozenset((
    "d2r_activeProfile", "d2r_activeProfileWin", "d2r_activeMachine",
    "d2r_ownerClaim", "d2r_installIdCache", "d2r_installId",
))


def stored_name_from_dump(all_stores):
    """The raw d2r_ledgerName out of a store dump. -> (value, known)

    `known=False` means the dump could not answer — either it is not a dump, or the key is one the
    exporter strips. `known=True` with `value=None` means MEASURED ABSENT: the key is exportable and
    was not exported, so it is not in the store.
    """
    if not isinstance(all_stores, dict):
        return None, False
    if "d2r_ledgerName" in PROGRESS_DUMP_EXCLUDES:
        return None, False          # defensive: if it is ever added to PTRS this stops lying
    v = all_stores.get("d2r_ledgerName")
    if v is None:
        return None, True           # exportable and absent -> genuinely unset
    return (str(v).strip() or None), True


def _backup_ts(taken_at):
    """'2026-09-06_214158' -> epoch ms, or None. An unparseable stamp is UNKNOWN, never now()."""
    try:
        return int(time.mktime(time.strptime(str(taken_at), "%Y-%m-%d_%H%M%S")) * 1000)
    except Exception:
        return None


def backup_points(directory=None, route=None, limit=200):
    """The restore points on this machine, newest first. -> dict

    ⚠ KEYED BY ROUTE, AND THE FILTER IS NOT OPTIONAL. Each point records the world it was taken in;
    reading another world's backup as this board's is the cross-namespace mix `compare_figures`
    exists to refuse, arriving through a directory listing instead of a subtraction.
    """
    import glob
    d = directory or BACKUP_DIR
    out = {"ok": False, "dir": d, "points": [], "why": ""}
    if not os.path.isdir(d):
        out["why"] = ("no backup directory at %s — the live truth is UNAVAILABLE, which is not the "
                      "same as the seed being current" % d)
        return out
    want = world_key(route) if route else None
    rows = []
    for p in sorted(glob.glob(os.path.join(d, "*.json")), reverse=True)[:limit]:
        try:
            with io.open(p, encoding="utf-8") as fh:
                j = json.load(fh)
        except Exception:
            continue                 # an unreadable point is skipped, never counted as empty
        r = j.get("route") if isinstance(j.get("route"), dict) else None
        key = world_key(r)
        if want and key != want:
            continue
        at = _backup_ts(j.get("takenAt"))
        rows.append({"path": p, "takenAt": j.get("takenAt"), "at": at,
                     "ageMs": (_now_ms() - at) if at else None,
                     "world": key or None, "namespace": namespace_of(r),
                     "counts": j.get("counts") if isinstance(j.get("counts"), dict) else None,
                     "allStores": j.get("allStores") if isinstance(j.get("allStores"), dict) else None})
    rows.sort(key=lambda x: (x["at"] or 0), reverse=True)
    out["points"] = rows
    out["ok"] = bool(rows)
    if not rows:
        out["why"] = ("no restore point matches %s — UNKNOWN, and the seed must not be presented "
                      "as his current chronicle in its place" % (want or "any world"))
    return out


def newest_backup(directory=None, route=None):
    """The newest restore point for ONE world, with its real age. -> dict | None"""
    d = backup_points(directory=directory, route=route)
    return d["points"][0] if d.get("ok") else None


def preferred_source(own=None, directory=None):
    """WHICH source the card should quote for this board, and why. -> dict

    THE ORDER, and each step is a different KIND of answer rather than a fallback:
      1. the LIVE board read      — a reading, age ~0
      2. the newest BACKUP        — a reading, with a real `takenAt`
      3. the SEED                 — a FLOOR, no age at all. Never quoted as his current chronicle.

    ⚠ STEP 3 IS NOT A SOURCE OF PROGRESS AND THIS FUNCTION SAYS SO. If neither reading is available
    the answer is UNKNOWN — the seed is what the boot path will re-assert, not what he has found.
    Quoting 245 as his uniques when the live figure is 292 is the whole defect.
    """
    own = own if isinstance(own, dict) else {}
    route = own.get("route") if isinstance(own.get("route"), dict) else None
    if own.get("ok") and own.get("boardLoaded"):
        return {"source": LIVE, "at": _now_ms(), "ageMs": 0, "ageKnown": True,
                "counts": own.get("counts"), "namespace": namespace_of(route),
                "why": "the board answered directly, so this is a reading taken just now"}
    b = newest_backup(directory=directory, route=route)
    if b:
        return {"source": BACKUP, "at": b["at"], "ageMs": b["ageMs"],
                "ageKnown": b["at"] is not None, "counts": b["counts"],
                "namespace": b["namespace"], "takenAt": b["takenAt"],
                "why": ("the board could not be read, so the newest restore point for this world "
                        "is quoted — it is a READING with a real timestamp (%s), which the "
                        "hardcoded seed is not" % b["takenAt"])}
    return {"source": None, "at": None, "ageMs": None, "ageKnown": False, "counts": None,
            "namespace": namespace_of(route),
            "why": ("neither the board nor a restore point for this world could be read. The seed "
                    "is NOT offered here: it is the floor the boot path re-asserts, not a record "
                    "of what he has found, and quoting it would present a constant with no "
                    "timestamp as his current chronicle.")}


# ══ THE STALENESS WATCHDOG — GENERAL, NOT SEED-SPECIFIC ═══════════════════════════════════════

def staleness(own=None, fleet=None, table=None):
    """Every ledger figure this console can see, with its age or an honest UNKNOWN. -> dict

    Konyo: *"connect it all to the heart of the console so nothing becomes stale again"*.

    THE GENERAL FORM OF THE SEED DEFECT. The uniques seed sat at 245 against a live 292 for months
    and nothing noticed, because nothing was watching AGE at all. A seed-specific check would leave
    the next frozen constant to rot in exactly the same way, so this walks every figure by KIND:

        FROZEN       age is UNMEASURABLE. Graded by DRIFT against the live figure.
        LIVE         read from the board just now
        BEACON       another machine's heartbeat, graded against beacon_ceiling_ms()
        DECLARATION  a person said so; age is information, never a fault

    ⚠ A FROZEN CONSTANT MUST NEVER READ AS FRESH. That is the way this whole fix would go vacuous:
    re-parsing bible.html every tick makes the READ new and the VALUE just as old. `ageKnown` is
    False for FROZEN by kind, not by whether a timestamp happens to be present.
    """
    tbl = table if table is not None else seed_table()
    rows = []
    ceiling = beacon_ceiling_ms()

    # ── the frozen constants: no age, graded by drift ───────────────────────────────────────
    live_by_ledger = {}
    ns = None
    if own is None:
        try:
            import control_app as ca
            own = ca.board_ownership(sample=0, dump_stores=True)
        except Exception:
            own = None
    if isinstance(own, dict) and own.get("ok"):
        ns = namespace_of(own.get("route") if isinstance(own.get("route"), dict) else None)
        c = own.get("counts") if isinstance(own.get("counts"), dict) else {}
        live_by_ledger = {"uniques": c.get("chronFound"), "sets": c.get("setPieces"),
                          "runewords": c.get("runewordsMade")}
        for k, v in live_by_ledger.items():
            rows.append(dict(figure(v, "board_ownership.counts", LIVE, namespace=ns,
                                    at=_now_ms()), name="%s live" % k, stale=False))

    for spec in LEDGERS:
        names, meta = seed_names_for(spec["name"], table=tbl)
        if names is None:
            rows.append(dict(figure(None, "bible.html", FROZEN, why=str(meta)),
                             name="%s seed" % spec["name"], stale=None))
            continue
        live = live_by_ledger.get(spec["name"])
        # v3313 — ONE definition of "may these two be subtracted", shared with `_stale`. This site
        # and that one drifted from `canonical_figure`, which already refused the comparison.
        _sd = seed_drift(spec, len(names), live)
        drift = _sd["drift"]
        f = figure(len(names), "bible.html:%s" % ",".join(spec["seeds"]), FROZEN,
                   namespace=ns, drift=drift)
        f["name"] = "%s seed" % spec["name"]
        f["comparable"] = _sd["comparable"]
        f["comparableWhy"] = _sd["why"]
        f["newestFindDate"] = max([p["newestFindDate"] for p in (meta or {}).get("parts") or []
                                   if p.get("newestFindDate")] or [None])
        # ⚠ DRIFT, NOT AGE, IS THE VERDICT HERE — and `None` drift is UNKNOWN, never fine.
        # ⚠ v3313 — except where no drift EXISTS. `stale` is None for both, which is why the row
        # also carries `comparable`: the doctor must tell "nobody could date this" apart from
        # "this was never a distance", and only one of those is a gap in knowledge.
        f["stale"] = _sd["stale"]
        f["why"] = (f["why"] + " Live figure is %s; the seed is %s behind."
                    % (live, drift) if drift else f["why"])
        rows.append(f)

    # ── the newest restore point: a READING with a real timestamp, unlike the seed ──────────
    _route = (own or {}).get("route") if isinstance(own, dict) else None
    try:
        _b = newest_backup(route=_route if isinstance(_route, dict) else None)
    except Exception:
        _b = None
    if _b:
        _bf = figure((_b.get("counts") or {}).get("chronFound"), "backup:%s" % _b["takenAt"],
                     BACKUP, namespace=_b["namespace"], at=_b["at"])
        _bf["name"] = "newest restore point"
        # graded against the SAME ceiling as a beacon: both are periodic snapshots, and the backup
        # cadence measured on his tree (15-25 min) sits inside it.
        _bf["stale"] = (_bf["ageMs"] > ceiling["staleMs"]) if _bf["ageKnown"] else None
        _bf["staleMs"] = ceiling["staleMs"]
        rows.append(_bf)
    else:
        # ⚠ NO RESTORE POINT IS UNKNOWN, NEVER FINE — and it must not promote the seed into the gap.
        rows.append(dict(figure(None, "backup", BACKUP, namespace=ns),
                         name="newest restore point", stale=None,
                         why="no restore point for this world could be read, so the live truth is "
                             "UNAVAILABLE — the seed is not a substitute for it"))

    # ── the beacons ─────────────────────────────────────────────────────────────────────────
    if fleet is None:
        try:
            import control_app as ca
            fleet = ca.fleet_presence() or {}
        except Exception:
            fleet = None
    # ⚠⚠ v3268 — A MACHINE THAT IS SWITCHED OFF IS NOT A LEDGER FIGURE GOING STALE, AND THIS
    # LOOP COULD NOT TELL THE DIFFERENCE BECAUSE IT THREW THE ROSTERS TOGETHER FIRST.
    # MEASURED on his console 2026-09-17:
    #     online   GrokBot  v3266  uniques 310/403   age 0.5 min
    #     online   Konyo    v3267  uniques 309/403   age 1.0 min
    #     offline  Dean     v3156  uniques   0/403   age 3625 min   (last event: `boot`)
    # The doctor reported "3 of 10 ledger figure(s) are out of date", and the third was Dean's
    # Windows laptop, which has been off since 2026-09-15. `/api/fleet` ALREADY publishes that
    # fact — it put him in `offline`, not `online` — and this walk concatenated the two rosters on
    # the first line, so the one authority that knew was discarded before any grading happened.
    # Same shape as v3265 (BLOCKED vs STOPPED) and v3267 (UNBUILT vs DRY): a thing that is
    # correctly not-running, graded as a thing that is broken. [[label-outlived-referent]]
    #
    # ⚠ `stale` is left exactly as it was computed — the figure IS old, and no other reader's
    # meaning changes. What is added is WHY, so a surface can stop calling a dark laptop a stale
    # ledger. A peer that is ONLINE and has gone quiet is still STALE, which is the real fault
    # this beacon check exists to catch, and it must not be able to hide behind this flag.
    _roster = ([(m, False) for m in (list((fleet or {}).get("online") or []))]
               + [(m, True) for m in (list((fleet or {}).get("offline") or []))])
    for m, _off in _roster:
        t = (m or {}).get("tally")
        if not isinstance(t, dict):
            continue
        who = m.get("nickname") or m.get("machine") or "?"
        f = figure(t.get("uniques"), "beacon:%s" % who, BEACON, at=t.get("at"))
        f["name"] = "%s tally" % who
        # ⚠ AN UNDATED BEACON IS UNKNOWN, NEVER FRESH. A row with no `at` cannot be graded, and
        # grading it as current is how a machine that stopped reporting looks healthy.
        f["stale"] = (f["ageMs"] > ceiling["staleMs"]) if f["ageKnown"] else None
        f["staleMs"] = ceiling["staleMs"]
        # ⚠ DECLARED BY THE ROSTER, never inferred from the age — otherwise "old" would define
        # "off" and the distinction would be circular.
        f["machineOff"] = bool(_off)
        if _off:
            f["machine"] = m.get("machine") or ""
            f["lastSeen"] = m.get("t") or ""
            # ⚠ #225 — "switched off" was a GUESS. The roster's offline flag means "no console beacon",
            # and MEASURED 2026-09-24 the ALT box it called switched off had been up since 09-18 with
            # him logged in — only its console had died. Say what is known, not why.
            # ⚠⚠ #227 — AND WHEN ITS LAST REPORT SHOWS IT MID-RELAUNCH, SAY SO. The ALT box's last
            # beacon (MEASURED 2026-09-24) ran v3417 with v3419 on disk and a relaunch armed; its
            # console died in that relaunch and the heart read it as a machine switched off. A peer
            # whose last word was "about to replace myself" and then silence is the one case where
            # the cause IS knowable from here, and the fix is a start, not a wait.
            _ver, _dv = m.get("ver"), m.get("diskVer")
            _rl = m.get("relaunch") if isinstance(m.get("relaunch"), dict) else {}
            f["diedRelaunching"] = bool(_ver and _dv and _dv != _ver and _rl.get("armed") and _rl.get("may"))
            if f["diedRelaunching"]:
                f["why"] = ("%s's machine (%s) went silent MID-RELAUNCH: its last report, at %s, was "
                            "running %s with %s on disk and a relaunch armed, and nothing came back — "
                            "its console most likely died relaunching (measured once, on the Windows "
                            "ALT). Starting TV DIABLO on that machine brings it back and pulls the fix. "
                            "Its figures are its LAST KNOWN ones, not current."
                            % (who, f["machine"] or "unknown", f["lastSeen"] or "unknown", _ver, _dv))
            else:
                f["why"] = ("%s's machine (%s) has not reported since %s — its console is not "
                            "beaconing, which means the console is down OR the machine is off; this "
                            "console cannot tell which. Its figures are its LAST KNOWN ones, not "
                            "current, and nothing here can refresh them until that console reports "
                            "again." % (who, f["machine"] or "unknown", f["lastSeen"] or "unknown"))
        rows.append(f)

    # ⚠ v3268 — `stale` keeps its old meaning (the figure IS old) so no existing reader shifts
    # under its feet; `staleHere` is the subset that is actually THIS console's problem, and
    # `machineOff` is published beside it so an offline peer can be named rather than miscounted.
    stale = [r for r in rows if r.get("stale") is True]
    off = [r for r in rows if r.get("machineOff")]
    stale_here = [r for r in stale if not r.get("machineOff")]
    unknown = [r for r in rows if r.get("stale") is None]
    return {"ok": True, "ceiling": ceiling, "rows": rows,
            "staleN": len(stale), "unknownN": len(unknown), "totalN": len(rows),
            "staleHereN": len(stale_here), "machineOffN": len(off),
            "machineOff": [r["name"] for r in off],
            "stale": [r["name"] for r in stale], "unknown": [r["name"] for r in unknown]}


# ══ TWO SURFACES, ONE NAME — THE DISAGREEMENT CLASS ═══════════════════════════════════════════

def surface_pairs():
    """Every figure this console publishes under one name from two independent computations.

    -> [{ledger, tallyStore, maskStore, tallyTotal, maskRosterN, comparable, why}]

    ONE decidable flag: `comparable`. The rest are facts for a reader, not a second
    filter to get wrong.

    ⚠⚠ THE ONE THAT IS ALREADY WRONG, MEASURED LIVE 2026-09-06. `fleet_mask.LEDGERS["uniques"]`
    reads `d2r_owned` — the VAULT — while `grail_tally` moved the `uniques` pair to `chronFound`,
    the CHRONICLE, in v2717 ("`uniques` NOW ANSWERS THE SAME QUESTION THE BOARD'S TABS DO",
    control_app.py:2004). control_app renamed the vault pair to `vaultUniques`; fleet_mask did not
    follow. So `fleet_compare(machine, "uniques")` — his "show me what he has that i dont" — decodes
    a VAULT mask and labels it uniques, beside a card showing a CHRONICLE number.

        MEASURED, popcount vs tally, on the live fleet:
            sets     Dean 128 vs 128     Konyo 123 vs 123     <- same store, agrees
            uniques  Dean 249 vs   0     Konyo 292 vs 160     <- different stores, same label

    Dean's vault mask is EMPTY, so a uniques cross-reference against him answers "he owns none"
    while his card reads 249/403. Both numbers are honest about different questions.
    [[label-outlived-referent]] [[feedback-contradiction-is-the-finding]]
    """
    #: the store each tally pair is counted from, named where control_app counts it
    TALLY_STORE = {"uniques": "d2r_foundLog", "sets": "d2r_setPieces",
                   "runewords": "d2r_rwMade",
                   # v3861 - the six colossal jewels: the board counts them inside the uniques tally (403 = 397 + 6),
                   # from the same found ledger their own mask reads
                   "colossal": "d2r_foundLog"}
    out = []
    try:
        import fleet_mask as _fm
        masks = dict(_fm.LEDGERS)
    except Exception as e:
        return [{"ledger": None, "why": "fleet_mask will not import (%s)" % str(e)[:60]}]
    for name, spec in sorted(masks.items()):
        ms = spec.get("store")
        ts = TALLY_STORE.get(name)
        # ⚠⚠ v2945 (#63) — ONE FLAG, BECAUSE TWO IS TWO CHANCES TO ASK THE WRONG ONE.
        # Konyo, on seeing a first cut that published `sameQuestion` AND `sameUniverse` side by
        # side: *"why is there two separte ones? it needs to be unified as one.. not two filters
        # that way you wont be able to look at the worng key?"* — and he is right, because that is
        # EXACTLY what had already happened: the corroborator asked `sameQuestion`, got True, and
        # compared `tally.have = 300 of 403` against `mask.have = 301 of 398`.
        #
        # It is the same instruction he gave once before, quoted in
        # test_the_cross_reference_asks_one_question: *"which one is it really?!!? is it 398 or 403
        # make a unifed logic"*. That gate also RULED on the numbers:
        #     403  chronTotal — HIS PINNED RULING, the game's own Chronicle count
        #     392  funiScan().total — the carded roster
        #     398  "produced by neither, and NO array on the page is this size"
        # So 398 is not a rival universe to reconcile; it is the number already declared wrong.
        #
        # `comparable` is the ONE question a caller may decide on: may these two numbers be set
        # against each other at all? The raw facts stay as fields for DIAGNOSIS — never as a second
        # thing to test. [[label-outlived-referent]] [[zero-needs-a-denominator]]
        _tot = _rn = None
        try:
            import fleet_mask as _fm2
            _rr, _fpp = _fm2.load_roster_for(name)
            _rn = len(_rr) if _rr else None
        except Exception:
            _rn = None
        # ⚠⚠ v2947 — THE LIVE PROBE IS GONE, NOT JUST UNGATED.
        # This used to call control_app.grail_tally() on every pair. Two problems, both real:
        # (1) it made a TABLE WALK depend on whether THIS console's board had POSTed, and
        # (2) `total` is a per-ROW fact — two machines can post different totals for one ledger —
        # so a single console-wide number could not be right for both even when it was readable.
        # The universe check now happens in mask_cross_check against the ROW's own `total`.
        # `tallyTotal` is not published here any more: a field that answered a per-row question
        # with a console-wide number is a label that outlived its referent.
        # [[label-outlived-referent]] [[gate-blind-to-unexercised-input]]
        _tot = None
        _store_ok = (ms == ts) if (ms and ts) else None
        _univ_ok = None if (_tot is None or _rn is None) else (_tot == _rn)
        # ⚠ UNKNOWN PROPAGATES. If either half could not be measured the answer is None, never
        # False — "I could not check" and "I checked and they differ" are different facts, and
        # collapsing them is how a pair goes quiet for the wrong reason.
        # ⚠⚠ v2947 — `comparable` MUST NOT DEPEND ON A LIVE PROBE OF *THIS* CONSOLE.
        # v2946's second eye (a different model family) caught this and it is a real regression:
        # `_tot` comes from `grail_tally()`, which answers nothing when the board window is not
        # open and no `board_tally.json` is banked — CI, a fresh clone, the Windows box before the
        # board has POSTed. Every pair then went `comparable=None`, `mask_cross_check` excluded ALL
        # of them, and the cross-check went DARK — including `sets`, whose stores AND universes
        # genuinely match (135 == 135). The fleet payload was always enough for the
        # have-vs-popcount arithmetic; requiring a local denominator silently made it not enough.
        # Worse, `test_the_cross_check_parts_when_a_store_holds_an_OFF_ROSTER_name` asserts (1,1)
        # THROUGH the real surface_pairs(), so it passed here and would have failed on CI.
        # ⇒ The one decidable flag is the STORE question, which is answerable from the table alone.
        # The UNIVERSE question is per-ROW and belongs where the row's own `total` lives, in
        # mask_cross_check. `tallyTotal` stays published as a FACT for a reader — never a gate.
        # [[gate-blind-to-unexercised-input]] [[stale-reading]] [[zero-needs-a-denominator]]
        if _store_ok is None:
            _comparable = None
        else:
            _comparable = bool(_store_ok)
        if _comparable:
            _why = ""
        elif _store_ok is False:
            _why = ("the mask counts %s and the tally counts %s — two questions under one label, "
                    "so their numbers are not comparable and a cross-reference names the wrong "
                    "ledger" % (ms, ts))
        elif _univ_ok is False:
            # ⚠⚠ v3026 — THIS BRANCH IS UNREACHABLE AND HAS BEEN SINCE v2947, WHICH IS WHY A
            # RED_PROOF POINTED AT IT AND MEASURED **BLIND**. `_tot` is hardcoded None twelve lines
            # up — v2947 removed the live probe on purpose ("comparable MUST NOT DEPEND ON A LIVE
            # PROBE OF *THIS* CONSOLE") and moved the universe question per-ROW into
            # mask_cross_check, where each machine's own posted `total` lives. With `_tot` always
            # None, `_univ_ok` is always None, so `_univ_ok is False` can never be true.
            #
            # THE COST WAS NOT COSMETIC: heart2 reported this whole gate BLIND, and
            # self_arming._heart_says_watched() fails closed on any blind instrument — so ONE dead
            # branch closed ALL TEN self-arming locks. A proof aimed at code that cannot run is a
            # proof that can never go red, and a gate that cannot go red is measuring nothing.
            #
            # KEPT, NOT DELETED, and kept EMPTY: if a future change ever restores a local total,
            # this is where the reason belongs — and leaving the old sentence here would have it
            # read as live prose describing a rule that moved. The live reason is in
            # mask_cross_check below. [[the-unjoined-end]] [[gate-blind-to-unexercised-input]]
            _why = ("the universes disagree, and this branch cannot currently be reached — the "
                    "per-row universe gate lives in mask_cross_check, which names both numbers")
        else:
            _why = ("whether these two figures are comparable is UNKNOWN: store %s, tally total "
                    "%r, roster %r" % ("ok" if _store_ok else "unmeasured", _tot, _rn))
        out.append({"ledger": name, "tallyStore": ts, "maskStore": ms,
                    "maskRosterN": _rn,
                    "comparable": _comparable, "why": _why})
    return out


def mask_cross_check(fleet=None):
    """tally.have vs popcount(mask), for every ledger where BOTH read the same store. -> dict

    The second source is genuinely independent: the tally is a COUNT the other machine posted, and
    the popcount is decoded HERE from an opaque bitmask against a roster file on this disk. Neither
    is derived from the other, and no item name crosses the wire in either direction.

    ⚠ LEDGERS WHOSE TWO SIDES READ DIFFERENT STORES ARE EXCLUDED AND SAID SO OUT LOUD — never
    silently. An exemption nobody can audit is an exemption that grows.
    """
    if fleet is None:
        try:
            import control_app as ca
            fleet = ca.fleet_presence() or {}
        except Exception:
            return {"ok": False, "why": "the fleet could not be read", "rows": [], "excluded": []}
    try:
        import fleet_mask as _fm
    except Exception as e:
        return {"ok": False, "why": "fleet_mask will not import (%s)" % str(e)[:60],
                "rows": [], "excluded": []}
    pairs = {p["ledger"]: p for p in surface_pairs()}
    excluded = [{"ledger": k, "why": v["why"]}
                for k, v in sorted(pairs.items()) if v.get("comparable") is not True]
    rows = []
    for m in (list((fleet or {}).get("online") or []) + list((fleet or {}).get("offline") or [])):
        who = (m or {}).get("nickname") or (m or {}).get("machine") or "?"
        for led, pair in sorted(pairs.items()):
            # ⚠⚠ v2945 — `comparable`, NOT merely "same store". A mask can only REPRESENT the
            # names on the roster it was built against, so a tally counted out of a LARGER universe
            # produces a popcount below its `have` for items the mask has no bit for — a
            # disagreement manufactured by the instrument. `uniques` is exactly this: both sides
            # read d2r_foundLog, the tally counts out of 403, the mask can only carry 398.
            # Excluded and NAMED in `excluded`, never silently skipped.
            if pair.get("comparable") is not True:
                continue
            mk = ((m or {}).get("masks") or {}).get(led)
            t = ((m or {}).get("tally") or {}).get(led)
            if not isinstance(mk, dict) or not isinstance(t, dict):
                continue
            roster, _why = _roster_for(led)
            if roster is None:
                continue
            # ⚠⚠ v2947 — THE UNIVERSE CHECK, PER ROW, FROM THE ROW'S OWN EVIDENCE.
            # This machine posted `total`; the mask can only represent `len(roster)` names. If
            # those differ, its `have` is counted out of a universe the mask cannot encode and the
            # comparison would manufacture a disagreement. That is the 403-vs-398 case exactly.
            # Asked HERE and not in surface_pairs() because `total` belongs to the ROW: two
            # machines can post different totals for one ledger, and a single console-wide answer
            # cannot be right for both. Absent `total` -> compare anyway, which is the pre-v2945
            # behaviour and the only one that works on a venue with no local tally.
            _rowTot = t.get("total") if isinstance(t.get("total"), int) else None
            if _rowTot is not None and _rowTot != len(roster):
                excluded.append({"ledger": led, "why":
                    "%s posts %s out of %d while the %s mask can only represent %d roster names, "
                    "so their counts are not comparable" % (who, t.get("have"), _rowTot, led,
                                                            len(roster))})
                continue
            try:
                _r, fp = _fm.load_roster_for(led)
                names, dwhy = _fm.decode(mk, roster, fp, side=who)
            except Exception as e:
                names, dwhy = None, str(e)[:60]
            rows.append({"who": who, "ledger": led,
                         "tallyHave": t.get("have"),
                         "popcount": len(names) if names is not None else None,
                         "agree": (names is not None and t.get("have") == len(names)),
                         "why": "" if names is not None else "the mask could not be decoded: %s"
                                                             % str(dwhy)[:80]})
    return {"ok": True, "rows": rows, "excluded": excluded,
            "agreeN": sum(1 for r in rows if r["agree"]),
            "comparableN": sum(1 for r in rows if r["popcount"] is not None)}


# ── SELF-PROVING ─────────────────────────────────────────────────────────────────────────────

def selftest():
    """Drive every law here to a RED verdict against synthetic input. -> (ok, [(what, passed)])

    A law nobody has seen fail is the green that lies. Each row below is a SABOTAGE: the state is
    constructed so the answer MUST change, and the test is that it does. [[regression-guard]]
    """
    out = []
    tbl = seed_table()
    out.append(("the seed table parses at all", bool(tbl.get("ok"))))
    out.append(("every declared seed anchor was found",
                set(tbl.get("seeds") or {}) == set(SEED_ANCHORS)))

    # SABOTAGE 1 — a renamed seed literal must REFUSE, not report a seed of size 0
    bad = seed_table(path=os.path.join(HERE, "__nope__.html"))
    out.append(("a missing bible refuses rather than reporting empty seeds",
                bad.get("ok") is False and not bad.get("seeds")))

    # SABOTAGE 2 — the union must not be the sum
    names, meta = seed_names_for("uniques", table=tbl)
    out.append(("the uniques seed is a UNION, not a sum",
                names is not None and meta["unionN"] < meta["sumN"] and meta["overlap"] > 0))

    # SABOTAGE 3 — a store the board did not dump is UNKNOWN, never SYNCED
    r = classify_local(own={"ok": True, "onOwnerSeed": True, "counts": {}, "fullStores": {}},
                       table=tbl)
    out.append(("an undumped store is UNKNOWN, not clean",
                all(x["provenance"] == UNKNOWN and x["rows"] is None for x in r["ledgers"])))

    # SABOTAGE 4 — a negative beyondSeed survives
    n_rw = len(seed_names_for("runewords", table=tbl)[0] or [])
    fr = classify_row({"ok": True, "onOwnerSeed": True,
                       "runewords": {"have": n_rw - 5, "total": n_rw}}, table=tbl)
    rw = [x for x in fr["ledgers"] if x["ledger"] == "runewords"][0]
    out.append(("a deficit is reported as negative, not clamped to 0", rw["beyondSeed"] == -5))

    # SABOTAGE 5 — onOwnerSeed None must not become SYNCED
    n_set = len(seed_names_for("sets", table=tbl)[0] or [])
    fr = classify_row({"ok": True, "onOwnerSeed": None,
                       "sets": {"have": n_set + 20, "total": None}}, table=tbl)
    out.append(("an unanswered console is UNKNOWN, never SYNCED",
                all(x["provenance"] == UNKNOWN for x in fr["ledgers"])))

    # SABOTAGE 6 — an unknown ledger is refused
    out.append(("an unknown ledger is refused, not defaulted",
                ledger_spec("uniqes")[0] is None and seed_names_for("uniqes")[0] is None))

    # SABOTAGE 7 — a frozen constant handed a perfectly good timestamp must STILL be undated
    _f = figure(1, "bible.html", FROZEN, at=_now_ms())
    out.append(("a hardcoded constant is never fresh, even with a timestamp",
                _f["ageKnown"] is False and _f["ageMs"] is None))

    # SABOTAGE 8 — a cross-world comparison is refused rather than subtracted
    _a = figure(1, "x", LIVE, namespace=namespace_of({"pfx": "", "p": "main"}))
    _b = figure(1, "y", LIVE, namespace=namespace_of({"pfx": "I·abcdef01·", "p": "main"}))
    out.append(("two different worlds are refused a comparison",
                compare_figures(_a, _b)[0] is False and compare_figures(_a, _a)[0] is True))

    # SABOTAGE 9 — an unrecognised world is UNKNOWN, never the owner's
    out.append(("an unrecognised prefix is UNKNOWN, never owner-main",
                namespace_of({"pfx": "??", "p": "main"})["key"] is None
                and namespace_of({"pfx": "", "p": "main"})["key"] == OWNER_MAIN))

    # SABOTAGE 10 — the canonical rule is the intersection, exercised in the direction his data
    # never takes: a store holding a name the roster does not have.
    _roster, _rw = _roster_for("sets")
    if _roster:
        _st = list(_roster)[:5] + ["Not On Any Roster At All"]
        _c = ledger_figure("sets", own={"ok": True, "route": {"pfx": "", "p": "main"},
                                    "counts": {},
                                    "fullStores": {"d2r_setPieces": json.dumps(_st)}})
        out.append(("the canonical figure is |roster n store|, not len(store)",
                    _c.get("byIntersection") == 5 and _c.get("byStoreLength") == 6
                    and _c.get("value") == 5 and _c.get("agree") is False))
    else:
        out.append(("the canonical rule could be exercised at all (roster: %s)" % _rw, False))

    # SABOTAGE 12 — an absence in an EXCLUDED key proves nothing; in an exportable key it is proof
    _v, _k = stored_name_from_dump({"d2r_foundLog": "{}"})
    out.append(("an exportable key missing from a dump is MEASURED absent",
                _v is None and _k is True))
    _v2, _k2 = stored_name_from_dump(None)
    out.append(("a non-dump answers UNKNOWN rather than absent", _v2 is None and _k2 is False))
    out.append(("the six pointer keys the exporter strips are declared",
                "d2r_ownerClaim" in PROGRESS_DUMP_EXCLUDES
                and "d2r_ledgerName" not in PROGRESS_DUMP_EXCLUDES))

    # SABOTAGE 13 — an unparseable backup stamp is UNKNOWN, never now()
    out.append(("an unparseable restore-point stamp is UNKNOWN, never now()",
                _backup_ts("not a date") is None and _backup_ts("2026-09-06_214158") is not None))

    # SABOTAGE 14 — with no reading available the seed is NOT offered as his chronicle
    _ps = preferred_source(own={"ok": False, "route": {"id": "NOBODY-AT-ALL", "p": "main",
                                                       "pfx": ""}})
    out.append(("with no reading available the SEED is refused as a source",
                _ps["source"] is None and _ps["counts"] is None))

    # SABOTAGE 11 — the stale line must sit ABOVE the age a healthy figure legitimately reaches
    _ce = beacon_ceiling_ms()
    out.append(("the stale threshold is above the healthy ceiling",
                _ce["staleMs"] > _ce["ceilingMs"] > 0))
    return all(p for _, p in out), out


def main(argv=None):
    import sys
    argv = list(argv if argv is not None else sys.argv[1:])
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    if "--selftest" in argv:
        ok, rows = selftest()
        for what, passed in rows:
            print("%s %s" % ("PASS" if passed else "FAIL", what))
        return 0 if ok else 1
    if "--seeds" in argv:
        t = seed_table()
        print(json.dumps({"ok": t["ok"], "why": t["why"],
                          "seeds": {k: {"n": v["n"], "line": v["line"],
                                        "newestFindDate": v["newestFindDate"],
                                        "stampedAt": v["stampedAt"]}
                                    for k, v in t["seeds"].items()}},
                         indent=2, ensure_ascii=False))
        return 0
    if "--exit-path" in argv:
        print(json.dumps(exit_path(), indent=2, ensure_ascii=False))
        return 0
    print(json.dumps(authority(), indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
