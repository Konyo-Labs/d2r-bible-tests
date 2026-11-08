#!/usr/bin/env python3
"""A machine's progress as BITS over a shared roster, so the fleet can subtract two ledgers.

WHY THIS EXISTS. Konyo: "for me and my cuzin alone it should cross reference eachother based on what
set items he has that i dont... show me what he has that i dont... so its not messy."

THE FLEET CARRIES COUNTS, AND 116 CANNOT BE SUBTRACTED FROM 120 TO PRODUCE NAMES. Something has to
travel per ITEM. But `functions/api/console.js` states a boundary in as many words —

    "No item names ever cross this boundary — a roster says how many, never which."

— and that boundary is worth keeping. So what travels is a BITMASK over a roster both machines
already have: bit i is set when this machine holds `roster[i]`. 135 set pieces become 18 bytes, and
the server stores an opaque string it never decodes. The subtraction happens on HIS machine, against
HIS copy of the roster, where the names already live.

⚠ THE ONE THING THAT MAKES THIS SAFE OR DANGEROUS IS THE ROSTER FINGERPRINT. A mask is meaningless
without the exact ordered list it was built against: if the roster gains a piece, every bit after
that index shifts, and a mask decoded against the wrong roster produces a confident, wrong list of
items his cousin is "missing". That failure is silent and it looks exactly like a working feature.
So every mask carries `v` — the roster's sourceHash prefix — and a decode against a different `v`
returns UNKNOWN rather than a guess. [[unknown-stays-unknown]] [[stale-reading]]

⚠ AND AN ABSENT MASK IS NOT AN EMPTY ONE. A machine that has never reported has no mask; that is
"we have not heard from him", not "he owns nothing". decode() answers None for absent and a list for
present, and the caller must render those differently — or the box will tell him his cousin is
missing all 135 pieces the first time it opens.
"""

import base64
import hashlib
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# how many characters of the roster's sourceHash ride along. Long enough that two real rosters
# cannot collide, short enough to keep the beacon small.
FINGERPRINT_LEN = 12

# a hard ceiling on what the wire will accept, so a malformed or hostile blob cannot be large.
# 4096 bits is ~30x the set roster and still only 700 bytes of base64.
MAX_BITS = 4096


def roster_fingerprint(source_hash):
    """The identity of the FILE the list came from — NOT of the list. -> str

    ⚠⚠ v2934 (#73) — THE DOCSTRING SAID "the ordered list a mask was built against" AND THAT IS
    NOT WHAT THIS IS. `sourceHash` is a hash of bible.html, and BOTH rosters are generated from it,
    so MEASURED 2026-09-11: set_roster.json and unique_roster.json carry the identical
    `a364e7b4f6114747d79bbcf9` and this returns `a364e7b4f611` for both. The only thing separating
    a 135-piece sets mask from a 398-name uniques mask was `n != len(roster)`.

    MEASURED with the lengths made equal: a SETS mask decoded against a UNIQUES roster and
    confidently named **Alma Negra, Andariel's Visage, Annihilus, Arachnid Mesh** for a machine
    holding Aldur's set pieces. This module's own v2329 comment calls that "the worst failure shape
    this module has — worse than refusing, because it answers". It is held off today by arithmetic
    (135 != 398), not by a check. `list_fingerprint` below is the check.
    [[label-outlived-referent]] [[gate-blind-to-unexercised-input]]
    """
    return str(source_hash or "")[:FINGERPRINT_LEN]


def list_fingerprint(roster):
    """The identity of the ORDERED LIST ITSELF. -> str, or "" when there is no list.

    Order-sensitive on purpose: bit i means roster[i], so two lists with the same names in a
    different order are different rosters for this module's purposes. The NUL separator stops
    ["ab","c"] and ["a","bc"] from hashing alike.
    """
    if not roster:
        return ""
    h = hashlib.sha256()
    for name in roster:
        h.update(str(name).encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:FINGERPRINT_LEN]


# ══ v2329 — TWO LEDGERS, ONE TABLE ═══════════════════════════════════════════════════════════
# Konyo: "i love the FLEET you made it cross reference the SETS now i want it also for Uniques in
# the exact same format."
#
# Everything here was already ledger-agnostic — encode(), compare() and load_roster()'s `key`
# argument were all written for this — and unique_roster.json (398 names) has existed since v1795
# under the same sourceHash as set_roster.json. Three things were not:
#
#   · fleet_compare(machine, ledger="sets") ACCEPTED a ledger it could not honour: it called
#     load_roster() with the SET defaults whatever it was asked for, so uniques bits would have
#     been decoded against the sets roster and named 135 wrong items with total confidence. That
#     is the worst failure shape this module has — worse than refusing, because it answers.
#   · the beacon published a hardcoded {"sets": mask}
#   · the route never passed the argument through
#
# So the ledger stops being a string anyone can invent and becomes a TABLE. A name that is not in
# it is refused; a ledger in it carries its own roster file, its own key inside that file, and its
# own board store — no caller assembles those three by hand ever again. [[copy-drift]]
LEDGERS = {
    # ⚠ `stores` is declared for BOTH ledgers, even though sets needs only one. A field present on
    # one entry and absent on the other is how a caller learns to write `.get("stores") or
    # [spec["store"]]` in three places and forget it in a fourth.
    "sets":    {"roster": "set_roster.json",    "key": "pieces", "store": "d2r_setPieces",
                "stores": ["d2r_setPieces"],
                "label": "set pieces"},
    # ══ v2759 — UNIQUES ANSWERS THE CHRONICLE QUESTION, AS THE TALLY HAS SINCE v2717 ═══════════
    # This read `"store": "d2r_owned"` — the VAULT store — while control_app.py:1997 repointed the
    # uniques TALLY to the chronicle pair at v2717 and renamed the old measure `vaultUniques`.
    # Nothing updated this spec, so the cross-reference modal answered "what is in his vault"
    # under a label meaning "what his Chronicle records", and his own panel read 160/398 beside a
    # board that says 292/403. `ledger_authority.surface_pairs()` has been reporting
    # `uniques sameQuestion: false` about exactly this, with nothing acting on it.
    #
    # ⚠⚠ AND IT IS A UNION, NOT ONE STORE — WHICH IS WHY `stores` EXISTS BESIDE `store`.
    # bible.html's `_ownedNames()` (:42994) IS the definition of "found" on his board:
    # `d2r_owned ∪ keys(d2r_foundLog)`, commented "found = ledger ∪ LEGACY owned". Pointing at
    # `d2r_foundLog` alone would be correct only IF the two happened to be nested today — a
    # coincidence, not a definition, and `d2r_owned` being the legacy store is exactly where a
    # long-running grail keeps its oldest finds. Matching the union is correct by construction.
    #
    # ⚠ `store` STAYS A SINGLE STRING and stays PRIMARY. `ledger_authority.surface_pairs()`
    # compares it to TALLY_STORE as a string to decide `sameQuestion` — the very detector that
    # proves this fix worked — and `corroborate`'s count-and-mask invariant now asks that detector
    # rather than re-declaring its own map. Turning `store` into a list would break the instrument
    # in the same commit that needs it. [[copy-drift]] [[the-unjoined-end]]
    "uniques": {"roster": "unique_roster.json", "key": "names",  "store": "d2r_foundLog",
                "stores": ["d2r_foundLog", "d2r_owned"],
                "label": "uniques"},
    # ══ v3861 — THE SIX COLOSSAL JEWELS TRAVEL IN A MASK OF THEIR OWN ══════════════════════════════
    # His board's unique tally is 403 = 397 hunt cards + these six (route_totals.py, his ruling), but
    # the uniques roster is the hunt-card table and never carried them, so the cross-reference could
    # not say whether either side holds Defender's Bile - and the "both need" column refused itself
    # (his words 2026-11-05: "we both need defenders bile"). A ledger of their own is WIRE-ADDITIVE:
    # the 396-name uniques mask keeps its bits and fingerprint, so a console that has not updated
    # still compares, and simply has not published this one yet. Same stores as uniques: a jewel he
    # ticks is a found-ledger name like any other.
    "colossal": {"roster": "colossal_roster.json", "key": "names", "store": "d2r_foundLog",
                 "stores": ["d2r_foundLog", "d2r_owned"],
                 "label": "colossal jewels"},
    # ══ v3887 (#160) — THE EIGHT RAINBOW FACETS TRAVEL IN A MASK OF THEIR OWN ══════════════════════
    # His 11-08: Dean's board said 384/403 (19 missing) and the cross-reference listed 18. The uniques roster carries ONE
    # "Rainbow Facet" bit, set only by the BARE name - Dean's found log holds six of the eight chronicle variants and no bare
    # name, so his bit read 0 while his board counted the two he lacks. Wire-additive like the jewels: a console that has
    # not updated still compares its uniques and simply has not published the facets.
    "facets": {"roster": "facet_roster.json", "key": "names", "store": "d2r_foundLog",
               "stores": ["d2r_foundLog", "d2r_owned"],
               "label": "rainbow facets"},
}

# ══ v3861 — ONE SUNDER, ONE NAME, IN THE CROSS-REFERENCE ═══════════════════════════════════════════
# His rulings: v2680 "for the chronicle all sunders 6 of them need to be counted ... as 1 tally for each",
# v3183 "for chronicle there is only one name for it". The board folds Latent/Renewed into the bare
# sunder (bible.html _isUpgradedSunder / _uniItems); the cross-reference diffed the raw roster names, so
# MEASURED 2026-11-05 on the fleet: his console published all six as Latent, Dean's all six as bare, and
# the uniques panel listed the same six charms on BOTH sides ("i have all the latents so something here
# is bugged"). chronicle_key() is the board's fold, for the compare only - the masks keep every spelling,
# because the VAULT still holds each as its own entity (v3183). A law pins this tuple to bible.html.
SUNDER_BASES = ("Bone Break", "Cold Rupture", "Crack of the Heavens", "Flame Rift", "Rotting Fissure",
                "Black Cleft")
#: the board splits ONE roster name, "Rainbow Facet", into this many chronicle variants (bible.html
#: _CHRON_FACETS); the mask carries one bit for all of them. A law pins it to the page.
FACET_VARIANTS = 8
FACET_NAME = "Rainbow Facet"


def chronicle_key(name):
    """The name the chronicle counts this roster name under. -> str. Pure.
    'Latent Cold Rupture' / 'Renewed Cold Rupture' -> 'Cold Rupture'; anything else unchanged."""
    s = str(name)
    for q in ("Latent ", "Renewed "):
        if s.startswith(q) and s[len(q):] in SUNDER_BASES:
            return s[len(q):]
    return s


def ledger_spec(ledger):
    """-> (spec, None) or (None, why). An unknown ledger is REFUSED, never defaulted to sets:
    silently answering about a different ledger than the one asked for is how a cross-reference
    comes back confident and wrong."""
    name = str(ledger or "").strip().lower()
    if name not in LEDGERS:
        return None, ("unknown ledger %r — this machine knows %s"
                      % (ledger, ", ".join(sorted(LEDGERS))))
    # ⚠ v2760 — COPY THE LIST, NOT THE REFERENCE. `dict(...)` is SHALLOW, so the returned
    # spec shared its `stores` list object with the module constant: PROVEN by appending to
    # a returned spec and watching fleet_mask.LEDGERS["uniques"]["stores"] grow for the whole
    # process, beacon included. The hazard arrived WITH the union fix — `store` was an
    # immutable string, so no caller could ever have mutated it by accident before.
    _spec = dict(LEDGERS[name], name=name)
    _spec["stores"] = list(_spec.get("stores") or ())
    return _spec, None


def load_roster_for(ledger):
    """The ordered roster for ONE ledger. -> (names, fingerprint) or (None, None).

    Same contract as load_roster: UNREADABLE IS NOT EMPTY. Returning [] would make every mask
    encode as all-zeros and the cross-reference would report that nobody owns anything.
    """
    spec, why = ledger_spec(ledger)
    if not spec:
        return None, None
    return load_roster(os.path.join(HERE, spec["roster"]), key=spec["key"])


def load_roster(path=None, key="pieces"):
    """-> (ordered names, fingerprint) or (None, None) when the roster cannot be read.

    UNREADABLE IS NOT EMPTY: returning [] here would make every mask encode as all-zeros and the
    cross-reference would confidently report that nobody owns anything.
    """
    p = path or os.path.join(HERE, "set_roster.json")
    try:
        with io.open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return None, None
    names = d.get(key)
    if not isinstance(names, list) or not names:
        return None, None
    return [str(n) for n in names], roster_fingerprint(d.get("sourceHash"))


#: v3887 (his 11-08: "cats eye i already have and tallied ... this one is bugged") - the apostrophes one name is written with
_APOS = {"\u2018": "'", "\u2019": "'", "`": "'"}


def _fold(name):
    """A name with every apostrophe written straight - the ONE fold the mask allows. -> str"""
    s = str(name)
    for a, b in _APOS.items():
        s = s.replace(a, b)
    return s


def encode(owned, roster, fingerprint):
    """Which of `roster` this machine holds, as base64url bits. -> dict, or None if it cannot say.

    Bit i (LSB-first inside each byte) is roster[i]. Comparison is by EXACT name, deliberately: the
    roster is generated from bible.html by roster_sync.py and the board stores the same strings, so
    a fuzzy match here would paper over a roster drift that the fingerprint is supposed to catch.
    ⚠ v3887 - EXACT, BUT FOR THE APOSTROPHE. The roster spells four uniques with the game's curly one (Atma’s Scarab,
    Saracen’s Chance, Seraph’s Hymn, The Cat’s Eye) and the board stores whichever the path that ticked it wrote: his found
    log held "The Cat's Eye" straight ONLY (measured 11-08 on a copy of his board's store), so his bit was 0 and the
    cross-reference with Dean said "they have - you do not" for an amulet he owns. A curly and a straight apostrophe are one
    character to him; nothing else is folded.
    """
    if not roster or owned is None:
        return None
    have = {_fold(n) for n in owned}
    n = len(roster)
    if n > MAX_BITS:
        return None
    buf = bytearray((n + 7) // 8)
    hits = 0
    for i, name in enumerate(roster):
        if _fold(name) in have:
            buf[i // 8] |= (1 << (i % 8))
            hits += 1
    # ⚠ `r` IS ADDITIVE AND OLD MASKS HAVE NONE. decode() checks it only when present, so every
    # mask already stored keeps decoding exactly as before while everything minted from here is
    # bound to the list and not merely to the file it came from. [[copy-drift]]
    return {"v": fingerprint, "r": list_fingerprint(roster), "n": n, "have": hits,
            "b": base64.urlsafe_b64encode(bytes(buf)).decode("ascii").rstrip("=")}


def decode(mask, roster, fingerprint, side="that machine"):
    """-> (names, why). `names` is None whenever the answer would be a guess.

    Every refusal says WHY, because "he owns none of these" and "I could not read this" reach the
    same box and must never render the same.

    ⚠ v2456 — `side` EXISTS BECAUSE THIS FUNCTION SERVES BOTH SIDES AND ONLY KNEW ONE NOUN.
    Konyo: "cross reference for the fleet might b estuck.. my cuzin says he clicks it and its not
    working from his end". His own console was fine — measured live against his cousin's row:
    ok, mine 121, theirs 124, both 118, six they have that he does not. What his cousin sees when
    his OWN mask is missing is `your side: no mask reported by that machine yet` — a sentence that
    says "your side" and then blames "that machine" in the same breath. Read from either end it
    accuses the other person, so both of them conclude the other one is broken and nobody looks at
    the side that is actually silent. The measurement was right and its attribution was not, which
    is the borrowed-surface rule arriving on a fleet card. [[borrowed-surface]]
    [[label-outlived-referent]]
    """
    if not isinstance(mask, dict):
        return None, "no mask has been reported by %s yet" % side
    if not roster:
        return None, "this machine cannot read its own roster, so it cannot decode anyone's mask"
    got = str(mask.get("v") or "")
    if not got:
        return None, "the mask does not say which roster it was built against"
    if got != fingerprint:
        return None, ("that machine is on a different item roster (%s vs %s) — the bits would "
                      "line up with the wrong items, so the comparison is refused rather than "
                      "guessed" % (got, fingerprint))
    n = mask.get("n")
    if not isinstance(n, int) or n != len(roster):
        return None, ("the mask covers %r items and this roster has %d — refusing rather than "
                      "truncating" % (n, len(roster)))
    # ⚠⚠ v2934 (#73) — THE LIST, NOT JUST THE FILE. `v` cannot separate the two ledgers: both
    # rosters are built from bible.html and carry the same sourceHash. A mask minted since v2934
    # also carries `r`, the digest of the ordered list, and that is what actually distinguishes
    # them. Checked BEFORE the length test because it is the stronger statement, and skipped
    # entirely when absent so no stored mask is invalidated.
    _r = str(mask.get("r") or "")
    if _r and _r != list_fingerprint(roster):
        return None, ("that mask was built against a DIFFERENT item list (%s vs %s) — same source "
                      "file, different roster, so the bits would name the wrong items and the "
                      "comparison is refused rather than guessed"
                      % (_r, list_fingerprint(roster)))
    b = str(mask.get("b") or "")
    try:
        raw = base64.urlsafe_b64decode(b + "=" * (-len(b) % 4))
    except Exception:
        return None, "the mask is not readable base64"
    if len(raw) != (n + 7) // 8:
        return None, ("the mask is %d bytes and %d items need %d — refusing a partial read"
                      % (len(raw), n, (n + 7) // 8))
    out = []
    for i, name in enumerate(roster):
        if raw[i // 8] & (1 << (i % 8)):
            out.append(name)
    return out, None


def compare(mine, theirs, roster, fingerprint, fold=None):
    """The whole point: what THEY have that I do not, and what I have that THEY do not.

    -> {"ok", "why", "theyHaveIDont": [...], "iHaveTheyDont": [...], "neitherHas": [...],
        "rosterN": n, "both": n, "mineN", "theirsN"}

    ⚠ `neitherHas` IS A DIFFERENT KIND OF CLAIM from the two lists beside it — a COMPLEMENT, true
    only if the roster is the whole universe, where a DIFFERENCE is true over any roster. It ships
    with `rosterN` so no caller can render it without the denominator it is valid against, and the
    caller must refuse to show it when a posted ledger total disagrees with that number. See the
    note on the return statement.

    ⚠ EITHER SIDE UNKNOWN MAKES THE ANSWER UNKNOWN. Subtracting a list I could not read from one I
    could produces a complete, confident, wrong answer — every one of my items would look like
    something he is missing.
    """
    a, why_a = decode(mine, roster, fingerprint, side="this console")
    b, why_b = decode(theirs, roster, fingerprint, side="that machine")
    if a is None:
        # names the side that is silent, and says what to do about it — a refusal a person cannot
        # act on is the same as a hang, which is exactly how this one was reported.
        return {"ok": False, "why": "YOUR side is the one missing: %s. Open the board on this "
                                    "machine and it publishes on the next heartbeat; nothing is "
                                    "wrong with the other console." % why_a}
    if b is None:
        return {"ok": False, "why": "THEIR side is the one missing: %s." % why_b}
    sa, sb = set(a), set(b)
    if fold is not None:
        # v3861 - every side's names folded to the key they are COUNTED under, and each key listed once,
        # at its first roster position. rosterN stays the bit count; foldedN is the folded universe.
        sa, sb = {fold(n) for n in sa}, {fold(n) for n in sb}
        _keys, _seen = [], set()
        for n in roster:
            k = fold(n)
            if k not in _seen:
                _seen.add(k)
                _keys.append(k)
        return {"ok": True, "why": None,
                "theyHaveIDont": [n for n in _keys if n in sb and n not in sa],
                "iHaveTheyDont": [n for n in _keys if n in sa and n not in sb],
                "neitherHas": [n for n in _keys if n not in sa and n not in sb],
                "rosterN": len(roster), "foldedN": len(_keys),
                "both": len(sa & sb), "mineN": len(sa), "theirsN": len(sb)}
    # ⚠⚠ v3021 — `neitherHas` IS NOT THE SAME KIND OF STATEMENT AS THE TWO LISTS ABOVE IT, and the
    # difference decides whether it can be published. His ask: "tell me the items we BOTH need
    # combined not only the items we each have that the other doesnt".
    #
    # A DIFFERENCE IS SAFE OVER ANY ROSTER. `theyHaveIDont` asks "which roster names are in their
    # mask and not mine" — true whatever exists OUTSIDE the roster, because a name nobody enrolled
    # simply never enters the question.
    #
    # A COMPLEMENT IS A CLAIM ABOUT THE WHOLE UNIVERSE. "Neither of us has X" is only true if the
    # roster IS the universe. MEASURED 2026-09-12: sets roster 135 against his board's posted total
    # 135 (safe), but uniques roster 398 against a posted total of 403 (NOT safe) — five names he
    # has pinned could never appear in a list claiming to be exhaustive. So this list is the first
    # thing in this panel a wrong denominator can falsify, and the two beside it never were.
    # [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
    #
    # ⚠ THE GUARD IS NOT HERE ON PURPOSE. This module holds no board totals — it is handed two
    # masks and a roster and nothing else, and inventing a totals read here would give it a second
    # job and a second way to be wrong. It returns the complement over the roster it was given,
    # which is exactly true of that roster, and publishes `rosterN` BESIDE it so the caller cannot
    # render the list without the denominator it is only valid against. control_app.fleet_compare
    # owns the decision to show it or to answer None. [[the-unjoined-end]]
    return {"ok": True, "why": None,
            "theyHaveIDont": [n for n in roster if n in sb and n not in sa],
            "iHaveTheyDont": [n for n in roster if n in sa and n not in sb],
            "neitherHas": [n for n in roster if n not in sa and n not in sb],
            "rosterN": len(roster),
            "both": len(sa & sb), "mineN": len(sa), "theirsN": len(sb)}


def sanitize_for_wire(mask):
    """What a SERVER may store: shape only, never meaning. -> dict or None.

    The worker mirrors this in JS. It exists so a hostile or broken client cannot put anything
    large or strange into the fleet record, and so the server still never learns an item name.
    """
    if not isinstance(mask, dict):
        return None
    v = str(mask.get("v") or "")[:32]
    n = mask.get("n")
    b = str(mask.get("b") or "")
    have = mask.get("have")
    if not v or not isinstance(n, int) or n <= 0 or n > MAX_BITS:
        return None
    # base64url of ceil(n/8) bytes, unpadded
    want = ((n + 7) // 8 + 2) // 3 * 4
    if not b or len(b) > want or len(b) > 4096:
        return None
    if any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in b):
        return None
    # ⚠ v2938 — AND THE WIRE MUST CARRY IT. The keep-list was v/n/b/have, so an `r` reaching
    # here was DROPPED and the mask arrived unidentifiable by list — the third and last place
    # v2934's guard was severed from the live path. Capped like `v`, omitted when absent so
    # masks minted before v2938 are unchanged. [[the-unjoined-end]]
    out = {"v": v, "n": n, "b": b}
    _r = str(mask.get("r") or "")[:32]
    if _r:
        out["r"] = _r
    if isinstance(have, int) and 0 <= have <= n:
        out["have"] = have
    return out
