# -*- coding: utf-8 -*-
"""v2735 — THE WIRE BETWEEN THE AUTOMATIC BACKUP AND THE DOOR THAT CAN PUT IT BACK.

Konyo: *"i want this automated not relying on the user.. i want a backup and restore point updated
and able to be repaired/restored thats why we coded all this already in parts just needs to be
wired properly."*

He was exactly right about the shape of it. MEASURED:

    BACKUP   automatic every 600s, all five ledgers + route, census-driven   ✅ v2731
    REBUILD  derives a chronicle from the other ledgers                      ✅ v2732
    DOORS    /api/chronicle_apply and /api/vault_apply — live, and the
             console UI already calls both                                   ✅
    RESTORE  ~/d2r_ledger_backups/restore_ledger.py — a manual CLI OUTSIDE
             the repo, dry-run by default, picking a file by HEURISTIC and
             never asking which profile                                      ❌ NOT WIRED

Nothing joined a backup file to those doors. The only "restore" reachable from the console was
`board_restore_dates`, which rewrites DATES on rows that still exist and cannot recover a loss.
[[the-unjoined-end]] [[plumbing-with-no-tap]]

=== WHY THIS IS SAFE TO BUILD NOW AND WAS NOT BEFORE ===
v2731 stamped the ROUTE into every backup file. Before that, a restore could only act on "whatever
board is currently showing" and nothing in the file would contradict a cross-world restore — the
Dean defect in reverse. Picking by route is now possible, so this refuses rather than guesses.

=== AND WHY THE APPLY IS ADDITIVE BY CONSTRUCTION ===
`chronicle_apply` routes through the board's own `window.chronicleApply`, which its own docstring
describes as "dated, merge-max, undoable". MERGE-MAX means a restore can only put back what is
missing; it cannot overwrite a newer find with an older one. So the dangerous direction — an old
snapshot clobbering good data — is closed by the door itself, not by a promise here.

⚠⚠ THIS MODULE WRITES NOTHING AND CANNOT. It reads backups, compares, and returns a PROPOSAL in the
shape the board already accepts (`{wouldAdd: {uniques, sets}}`). The console never writes the
ledger — every existing path asks the board to press its own door, and a second writer into his
chronicle is the drift this repo keeps finding.

⚠ THE RESTORE IS NOT AUTOMATIC, DELIBERATELY. "Able to be restored" is his phrase. The BACKUP is
the automated half and he never touches it; putting a ledger back is a deliberate act, and a plan
that ran itself could resurrect a state he had intentionally left behind.
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.expanduser("~/d2r_ledger_backups")

#: The stores a restore can put back through the board's own door, and which half of the
#: proposal each belongs to. ⚠ rwMade and gameFound are BACKED UP (v2731) but are NOT restorable
#: through `chronicleApply` — it accepts uniques and sets. Saying so is the point: a restore that
#: silently covered three of five stores while reporting success would be the worst kind.
RESTORABLE = {"foundLog": "uniques", "setPieces": "sets"}

#: ⚠⚠ THE THREE THAT CANNOT TRAVEL BACK, AND WHY EACH — because the obvious "fix" for one of them
#: would defeat a gate that exists on purpose. Measured 2026-09-06:
#:
#:   owned      `/api/vault_apply` exists and looks like the door for it. It is NOT.
#:              vault_apply RE-GATES any caller-supplied proposal through `_vault_retro()` —
#:              KEEP_MIN_WITNESSES = 3, KEEP_CONF_FLOOR = 0.55 — and a restore has a backup FILE,
#:              not three distinct sessions of testimony. Posting a restore through it would either
#:              be rejected (correct) or, if someone widened the gate to let it through, would put
#:              uncorroborated rows in his stash with nothing behind them. That gate was added in
#:              v1595 precisely because a hand-made body used to go straight through, and a
#:              cross-family pass on v2641 found two more holes in it. Do not reopen them for this.
#:   rwMade     the board exposes no apply door for forged runewords at all
#:   gameFound  in-game records the board writes from the game, not from a tick
#:
#: They are still BACKED UP, which is the half that matters most — the data survives. Getting them
#: back is a door that does not exist yet, and saying so on every plan is the point: a restore that
#: silently covered two of five stores while reporting success is the worst kind.
BACKED_UP_ONLY = ("rwMade", "gameFound", "owned")

# ══ THE DROP — ONE DEFINITION, READ BY THE RESTORE PLAN *AND* BY THE BACKUP LOOP'S WATCHER ══════
# MEASURED 2026-09-27 on his real backup dir (shape only): ledger_2026-09-27_024127.json held
# setPieces 134 / owned 223, the 033127 file held 0 / 0 (a vault reset), and every backup after it
# held 0. `plan()` took hits[0] — the NEWEST — so the restore door would have put back NOTHING, and
# nothing opened an episode (d2r_storeEmptied only opens when the FOUND ledger comes up empty at
# load), so the 02:41 file survived only because the prune had not reached it yet. Luck is not a
# retention policy. [[the-unjoined-end]] [[unknown-stays-unknown]]
#
# ⚠ ONE function decides what a drop is, and both halves call it: `plan()` replays the chain to
# pick a per-store source, and control_app's `_ledger_drop_watch` steps it once per snapshot to open
# and close the durable episode record the prune honours. Two definitions would drift, and the day
# they disagree is the day the prune deletes the file the plan was about to restore from. [[copy-drift]]

#: Every store the automatic backup carries, in the order a drop is reported.
BACKED_UP = ("foundLog", "setPieces", "owned", "rwMade", "gameFound")
#: A fall is a DROP when the store reaches 0, or falls by at least max(DROP_MIN, DROP_FRAC x before).
#: The floor keeps a small store's ordinary churn (30 -> 21) from crying wolf; the fraction keeps a
#: large store's real loss (445 -> 300) from hiding under a fixed count.
DROP_MIN = 10
DROP_FRAC = 0.25
#: A threshold for drops_between / step_episodes meaning EVERY fall, however small. board_tally
#: passes it (his ruling 2026-09-28, "keep what was recorded before"): a single un-tick or a 3-set
#: fall on the board is still written down as an episode. The backup watcher and plan() never pass
#: one, so their drop line above is unchanged.
ANY_FALL = 1
#: The count the board reports INDEPENDENTLY for a store a snapshot OMITS - since v3882 `_ledger_snapshot_once`
#: writes rwMade/gameFound whenever the board SENT them (empty included: a measured zero), so an absent one is a
#: board that did not send it, or a snapshot from before v3882 (which left an EMPTY store out). An absent rwMade
#: beside `counts.runewordsMade == 0` is still a measured zero. gameFound has no independent count, so an absent
#: gameFound is UNKNOWN and can never be read as a drop to zero.
_COUNT_KEY = {"foundLog": "foundLog", "setPieces": "setPieces", "owned": "owned",
              "rwMade": "runewordsMade"}

# ══ HIS HAND-MADE STORES — WATCHED LIKE HIS LEDGER (#41 rank 5, 2026-09-29, REG-1481) ═══════════════
# His builds (the Character Builder) and his hand placements (the mule window) have travelled in the
# automatic backup since v2737 — `allStores` is the board's complete export — and NO watcher judged them:
# a wiped d2r_charBuilds opened no episode, raised nothing, and the prune could take the last file that
# held it. MEASURED read-only on his real backups (2026-09-29): the newest snapshot HOLDS d2r_charBuilds
# (1 build) and d2r_muleEquip; control_app and console_doctor had 0 matches for charBuilds / muleEquip.
# ⚠ THE SAME DROP LINE AS THE LEDGER, ON PURPOSE: to 0, or by >= max(DROP_MIN, DROP_FRAC x before).
# His own Delete + Undo of one build never pages (3 -> 2 is neither), while a wiped store opens an
# episode naming the file to restore from — and that file is then kept from the prune like any other.
# ⚠ COUNTED FROM `allStores`, WHERE EACH VALUE IS THE STORE'S OWN JSON TEXT as the board keeps it. There
# is no independent count for these (the board publishes none). WHAT IS UNKNOWN AND WHAT IS ZERO — the
# second eye on REG-1481 corrected the first cut here: `allStores` is `_collectProgress()`, which walks the
# RAW store END TO END (`for i < RAW.length`) for the active world, so a key ABSENT from a dict allStores
# was LOOKED FOR and not found — that is a measured 0, and it is exactly the shape the owner wipe leaves
# (`RAW.removeItem`, so the wiped store is not empty, it is GONE). Reading it as UNKNOWN made the watch
# blind to the one wipe that actually removes the key. Only NO allStores (not a dict: the board could not
# be asked) or text that is not a JSON dict/list stays None — "nobody looked" and "he had none" still
# never read the same. [[unknown-stays-unknown]] [[the-unjoined-end]]
HAND_MADE = ("charBuilds", "muleEquip", "muleAssign")
#: d2r_cbMain is the MAIN pointer INTO charBuilds and is deliberately NOT counted: the Characters tab
#: clears it with removeItem when the MAIN build is deleted (a choice with an Undo, never a loss), and
#: any wipe that takes it takes charBuilds with it, which IS counted. Named here so its absence from
#: HAND_MADE reads as a decision, not an oversight.
HAND_MADE_POINTERS = ("cbMain",)
#: Where each hand-made store comes back from, in his words — the doctor prints this beside the episode.
#: None of them travels through the chronicle door (RESTORABLE) or an /api/*_restore door; the backup FILE
#: is the way back: its `allStores` is the board's own export (_collectProgress), so the store's exact text
#: is there to put back by hand, or wrapped as a grail-progress snapshot through Backup & Share.
#: ⚠ ONE KEY, NEVER THE WHOLE allStores (the second eye on REG-1481). `_applyProgress` setItem()s EVERY
#: string key it is handed, so importing the file's whole allStores puts back the builds AND rolls foundLog /
#: setPieces / owned / rwMade / gameFound back to that file's moment — every find since, discarded, behind a
#: confirm that only says "OVERWRITES the chronicle / wishlist / settings". A door that puts back more than
#: what fell is the chronicle-plan mistake wearing the other coat, so every door names its ONE key and says
#: what the whole file would cost. One template, three stores — a copy per store is how one of them drifts.
_HAND_MADE_WRAP = ('wrap ONLY that one key as a grail-progress snapshot — {"app":"d2r-bible","kind":"grail-progress",'
                   '"data":{"d2r_%(store)s": <its text from that allStores>}} — and import it through Backup & Share; '
                   'importing the whole allStores rolls every other store back to that file')


def _hand_made_door(store, what):
    """The door text for one hand-made store: what it is, where the file keeps it, and the ONE-key way back."""
    return ("%s — d2r_%s in the named backup's allStores, the board's own export; put back by hand, or "
            % (what, store)) + _HAND_MADE_WRAP % {"store": store}


HAND_MADE_DOOR = {
    "charBuilds": _hand_made_door("charBuilds", "his builds"),
    "muleEquip": _hand_made_door("muleEquip", "his hand placements on the mules' dolls"),
    "muleAssign": _hand_made_door("muleAssign", "which mule holds which item"),
}


def _hand_made_count(x, store):
    """A hand-made store's count off a backup blob's `allStores`. -> int, or None = UNKNOWN.

    The value is the board's own JSON text (a dict of builds / placements / assignments). Not a blob or
    no allStores (nobody could look) = None; text that is not a JSON dict or list = None. The key ABSENT
    from a dict allStores = 0: the export is a complete walk of the store, so absent means looked-for and
    not there — the shape `RAW.removeItem` (the owner wipe) leaves, and the one the first cut of this
    read as UNKNOWN, which made the watch blind to it. [[unknown-stays-unknown]]
    """
    al = x.get("allStores") if isinstance(x, dict) else None
    if not isinstance(al, dict):
        return None
    raw = al.get("d2r_" + store)
    if raw is None:
        return 0                    # a complete export without the key: he has none (or it was removed)
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None
    if isinstance(raw, (dict, list)) and not isinstance(raw, bool):
        return len(raw)             # a hand-made store's rows, as the board keeps them
    return None


def hand_made_counts(all_stores):
    """{store: count | None} for every HAND_MADE store in a board export (`fullStores` / `allStores`).

    The backup loop compares this beside the ledger counts to decide whether anything changed: a build
    wiped between two snapshots with nothing FOUND in between used to produce NO snapshot at all, and
    the drop watcher only judges snapshots. [[the-unjoined-end]]
    """
    blob = {"allStores": all_stores if isinstance(all_stores, dict) else None}
    return dict((s, _hand_made_count(blob, s)) for s in HAND_MADE)


def _ledger_of(x):
    """A backup blob or a bare ledger -> (ledger dict, counts dict)."""
    if isinstance(x, dict) and isinstance(x.get("ledger"), dict):
        return x["ledger"], (x.get("counts") if isinstance(x.get("counts"), dict) else {})
    return (x if isinstance(x, dict) else {}), {}


def store_count(x, store):
    """How many rows `store` held in a backup blob (or a bare ledger). -> int, or None = UNKNOWN.

    A store the file does not carry is NOT zero unless the board's own independent count says so —
    "nobody copied it" and "he had none" must never read the same. [[unknown-stays-unknown]]
    A HAND_MADE store is counted off the blob's `allStores` (REG-1481); it has no independent count, and
    the complete export IS the "independent" say-so for an absent key: absent from a dict allStores is 0.
    """
    if store in HAND_MADE:
        return _hand_made_count(x, store)
    led, counts = _ledger_of(x)
    v = led.get(store)
    if isinstance(v, (list, dict)):
        return len(v)
    ck = _COUNT_KEY.get(store)
    c = counts.get(ck) if ck else None
    if isinstance(c, int) and not isinstance(c, bool) and c >= 0:
        return c
    return None


def drops_between(prev_ledger, next_ledger, threshold=None):
    """Every backed-up store that DROPPED from one snapshot to the next. -> [{store, from, to}]

    Takes a backup blob or a bare ledger on either side. A store whose count is UNKNOWN on either
    side is never a drop — an unreadable reading is not a loss, and reporting one would send him to
    restore rows he never lost.

    `threshold` None is THIS module's drop line: to 0, or by >= max(DROP_MIN, DROP_FRAC x before).
    An int n >= 1 is "a fall of at least n rows" instead (ANY_FALL = every fall). It exists for
    board_tally, which records every fall of his published progress; the default path is the exact
    code it always was, so the backup watcher and plan() cannot drift with it. [[copy-drift]]
    """
    if threshold is not None and (isinstance(threshold, bool) or not isinstance(threshold, int)
                                  or threshold < 1):
        raise ValueError("a drop threshold is None or an int >= 1, not %r" % (threshold,))
    out = []
    # REG-1481 — his hand-made stores are judged on the same line, in the same pass; a bare ledger or a
    # counts-only blob (board_tally) carries no allStores, so for it they are UNKNOWN and never a drop.
    for store in BACKED_UP + HAND_MADE:
        a = store_count(prev_ledger, store)
        b = store_count(next_ledger, store)
        if a is None or b is None or a <= 0 or b >= a:
            continue
        if threshold is not None:
            if (a - b) >= threshold:
                out.append({"store": store, "from": a, "to": b})
            continue
        if b == 0 or (a - b) >= max(DROP_MIN, DROP_FRAC * a):
            out.append({"store": store, "from": a, "to": b})
    return out


def stamp_ms(name_or_stamp):
    """'ledger_2026-09-27_033127.json' or '2026-09-27_033127' -> epoch ms, or None.

    The writer stamps with `time.strftime` (the machine's LOCAL clock), so this reads it back with
    the local clock too. An unparseable stamp is None, never "now". [[stale-reading]]
    """
    import re
    import time
    m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{6})", str(name_or_stamp or ""))
    if not m:
        return None
    try:
        return int(time.mktime(time.strptime(m.group(1), "%Y-%m-%d_%H%M%S")) * 1000)
    except Exception:
        return None


def step_episodes(episodes, prev, nxt, prev_file, next_file, route_key=None, at_ms=None,
                  threshold=None):
    """ONE step of the drop watcher. Mutates `episodes`; writes nothing. -> (opened, closed)

    1. every OPEN episode for this route whose store is back to >= its `from` CLOSES — a store the
       new snapshot cannot count stays open (UNKNOWN is not a recovery);
    2. every drop between `prev` and `nxt` OPENS an episode naming the file BEFORE it, which is the
       file a restore needs and the file the prune must not take while the episode is open.

    `threshold` is handed to drops_between unchanged; None keeps this module's own drop line.
    """
    opened, closed = [], []
    for ep in episodes:
        if not (isinstance(ep, dict) and ep.get("open")) or ep.get("routeKey") != route_key:
            continue
        n = store_count(nxt, ep.get("store"))
        try:
            back = n is not None and n >= int(ep.get("from") or 0)
        except (TypeError, ValueError):
            back = False
        if back:
            ep.update({"open": False, "closedAt": at_ms, "closedBy": next_file, "closedCount": n})
            closed.append(ep)
    for dr in drops_between(prev, nxt, threshold):
        ep = {"store": dr["store"], "from": dr["from"], "to": dr["to"],
              "beforeFile": prev_file, "afterFile": next_file, "at": at_ms,
              "routeKey": route_key, "open": True}
        episodes.append(ep)
        opened.append(ep)
    return opened, closed


def accept_episodes(episodes, store, reason, at_ms=None, closed_count=None, route_key=None):
    """Close OPEN episodes of `store` because the drop was deliberate. Mutates; writes nothing.

    A reason is required. closedBy is 'accepted: <reason>', so a recovery and an acceptance stay
    different facts. A ratchet that can only close when the count comes back stays red forever
    the first time he clears a store on purpose.
    """
    why_reason = str(reason or "").strip()
    if not why_reason:
        return [], "a reason is required — closing a drop without one is the same as not recording it"
    if not store:
        return [], "no store was named"
    closed = []
    for ep in episodes or []:
        if not (isinstance(ep, dict) and ep.get("open") and ep.get("store") == store):
            continue
        if route_key is not None and ep.get("routeKey") != route_key:
            continue
        ep.update({"open": False, "closedAt": at_ms,
                   "closedBy": "accepted: %s" % why_reason[:300],
                   "closedCount": closed_count})
        closed.append(ep)
    if not closed:
        return [], "no open drop for %s" % store
    return closed, ""


def replay(chain, route_key=None):
    """Run the watcher over a chain of one route's backups, OLDEST FIRST. -> every episode.

    `chain` is [(file_name, blob), ...]. The same `step_episodes` the backup loop runs once per
    snapshot, so a plan and the durable record cannot disagree about what a drop is.
    """
    eps = []
    for (pf, pb), (nf, nb) in zip(chain, chain[1:]):
        step_episodes(eps, pb, nb, pf, nf, route_key=route_key, at_ms=stamp_ms(nf))
    return eps


def _route_key(route):
    """A route dict -> the key a backup file is matched on. -> str or None."""
    if not isinstance(route, dict):
        return None
    rid = str(route.get("id") or "").strip()
    prof = str(route.get("p") or "").strip()
    if not rid:
        return None
    return "%s|%s" % (rid, prof or "main")


def backups_for(route, d=None):
    """Every backup file whose stamped route matches, newest first. -> (list, why)

    ⚠ MATCHED ON THE ROUTE, NEVER PICKED BY HEURISTIC. `restore_ledger.py` chose "the file with the
    most unique-like names", which is a guess wearing a measurement's clothes and could cross
    worlds. Files written before v2731 carry no route at all and are SKIPPED with a reason — an
    unrouted backup is not this profile's backup, it is a backup whose owner is unknown.
    [[unknown-stays-unknown]]
    """
    want = _route_key(route)
    if not want:
        return [], "no route was given, so no backup can be matched to a profile"
    d = d or BACKUP_DIR
    if not os.path.isdir(d):
        return [], "there is no backup directory at %s" % d
    hits, unrouted = [], 0
    try:
        names = sorted(os.listdir(d), reverse=True)
    except Exception as e:
        return [], "the backup directory could not be read (%s)" % str(e)[:60]
    for n in names:
        if not (n.startswith("ledger_") and n.endswith(".json")):
            continue
        p = os.path.join(d, n)
        try:
            with io.open(p, encoding="utf-8") as fh:
                blob = json.load(fh)
        except Exception:
            continue                       # unreadable file: not a candidate, and not an error here
        got = _route_key((blob or {}).get("route"))
        if got is None:
            unrouted += 1
            continue
        if got == want:
            hits.append((p, blob))
    why = ""
    if not hits:
        why = ("no backup carries this profile's route (%s); %d file(s) predate the route stamp "
               "and cannot be attributed to anyone" % (want, unrouted))
    elif unrouted:
        why = ("%d file(s) predate the route stamp and were skipped — they may be this profile's "
               "and there is no way to tell" % unrouted)
    return hits, why


def explicit_backup(route, name, d=None):
    """The backup HE NAMED, validated. -> ((path, blob), "") or (None, why). Reads only.

    ⚠ A NAME, NEVER A PATH. The door takes a basename that must resolve to a `ledger_*.json` file
    directly inside the backup directory (after symlinks), carrying THIS profile's route. Anything
    else — `../x.json`, an absolute path, a sub-directory, a symlink that points out, an unrouted
    file, another profile's file — is refused with the reason, because a restore door that can be
    pointed at an arbitrary file is a door that can put anyone's ledger into his.
    """
    if not isinstance(name, str) or not name.strip():
        return None, "no backup file was named"
    name = name.strip()
    if (os.path.basename(name) != name or "/" in name or "\\" in name or "\x00" in name
            or name in (".", "..")):
        return None, ("refused %r — a backup is named by its file name inside the backup "
                      "directory, never by a path" % name[:80])
    if not (name.startswith("ledger_") and name.endswith(".json")):
        return None, "refused %r — not a ledger backup (ledger_*.json)" % name[:80]
    d = d or BACKUP_DIR
    want = _route_key(route)
    if not want:
        return None, "no route was given, so no backup can be matched to a profile"
    try:
        real_d = os.path.realpath(d)
        real_p = os.path.realpath(os.path.join(d, name))
    except Exception as e:
        return None, "refused %r — its location could not be resolved (%s)" % (name[:80], type(e).__name__)
    if os.path.dirname(real_p) != real_d:
        return None, "refused %r — it resolves OUTSIDE the backup directory" % name[:80]
    if not os.path.isfile(real_p):
        return None, "there is no backup named %r in the backup directory" % name[:80]
    try:
        with io.open(real_p, encoding="utf-8") as fh:
            blob = json.load(fh)
    except Exception as e:
        return None, "the backup %r will not parse (%s)" % (name[:80], type(e).__name__)
    got = _route_key((blob or {}).get("route") if isinstance(blob, dict) else None)
    if got is None:
        return None, ("refused %r — it predates the route stamp, so whose ledger it holds cannot be "
                      "told" % name[:80])
    if got != want:
        return None, "refused %r — it is ANOTHER profile's backup, not this one's" % name[:80]
    return (real_p, blob), ""


def record_covers_dir(d, doc):
    """True when this drop record is ABOUT the backups in `d`, not some other world's files.

    An empty record that has never judged a file in `d` is not authority over `d`. Replaying is
    then the bootstrap. A record that names one of these files, or whose lastJudged names one, is
    the authority — including when it holds no open episode.
    """
    if not isinstance(doc, dict) or not d:
        return False
    try:
        names = set(os.listdir(d))
    except Exception:
        return False
    eps = doc.get("episodes") or []
    if any(isinstance(e, dict) and (e.get("beforeFile") in names or e.get("afterFile") in names)
           for e in eps):
        return True
    judged = doc.get("lastJudged") or {}
    return any(str(v) in names for v in judged.values() if v)


def _sources_after_drops(route, hits, episodes=None):
    """Per store, which backup a restore should read. -> ({store: (path, blob, why)}, [open drop])

    The newest backup is the source for every store UNLESS it sits after an unrecovered drop of that
    store; then the source is the last backup BEFORE the drop. When a store dropped more than once
    and never came back, the open drop with the HIGHEST `from` wins — it holds the most, and the
    door is add-only, so an older source can only add back what is missing.

    `episodes` is the durable record when the caller has one for THESE files. None means the record
    is absent, and the chain is replayed. A passed list, even an empty one, is not replayed: a
    thinned keeper chain invents drops the watcher, stepping every snapshot, never opened.
    """
    rk = _route_key(route)
    newest_p, newest_b = hits[0]
    newest = os.path.basename(newest_p)
    byname = dict((os.path.basename(p), (p, b)) for p, b in hits)
    if episodes is None:
        eps = replay([(os.path.basename(p), b) for p, b in reversed(hits)], route_key=rk)
    else:
        eps = [e for e in episodes if isinstance(e, dict)]
    sources, drops = {}, []
    for s in BACKED_UP:
        live = [e for e in eps if e.get("open") and e.get("store") == s
                and e.get("beforeFile") in byname]
        if not live:
            sources[s] = (newest_p, newest_b, "the newest backup")
            continue
        best = max(live, key=lambda e: (e.get("from") or 0, e.get("beforeFile") or ""))
        bp, bb = byname[best["beforeFile"]]
        drops.append({"store": s, "from": best["from"], "to": best["to"],
                      "beforeFile": best["beforeFile"], "afterFile": best["afterFile"]})
        sources[s] = (bp, bb, "the newest backup (%s) sits AFTER a drop — %s fell %d -> %d in %s — "
                              "so %s comes from %s, the last backup BEFORE the drop"
                      % (newest, s, best["from"], best["to"], best["afterFile"], s,
                         best["beforeFile"]))
    return sources, drops


def _names(v):
    """A store's names, list or dict alike."""
    if isinstance(v, list):
        return list(v)
    if isinstance(v, dict):
        return list(v.keys())
    return []


def plan(route, current, d=None, file=None, episodes=None):
    """What the backups for this profile would put back. -> dict. Reads only.

    `current` is the board's ledger as it stands now: {"foundLog": {...}, "setPieces": [...], ...}
    A store the caller could not read must be passed as None, not {} — restoring INTO an unknown
    is how a restore invents a loss.

    `file` — a backup HE NAMED wins outright (validated by `explicit_backup`): every store comes
    from it. Without one, each store reads the newest backup unless that backup sits after an
    unrecovered DROP of the store, in which case the store reads the last backup BEFORE the drop —
    and says so, per store, in `source` / `sourceWhy` and in the plan's `why`.
    """
    if file is not None:
        pick, fwhy = explicit_backup(route, file, d)
        if pick is None:
            return {"ok": False, "why": fwhy}
        path, blob = pick
        sources = dict((s, (path, blob, "you named %s, so every store comes from it"
                            % os.path.basename(path))) for s in BACKED_UP)
        drops = []
    else:
        hits, why = backups_for(route, d)
        if not hits:
            return {"ok": False, "why": why or "no matching backup"}
        path, blob = hits[0]
        sources, drops = _sources_after_drops(route, hits, episodes=episodes)
    out, missing_total = {}, 0
    for store, half in sorted(RESTORABLE.items()):
        spath, sblob, swhy = sources[store]
        src = {"source": os.path.basename(spath), "sourceWhy": swhy}
        led = (sblob or {}).get("ledger") or {}
        have = current.get(store)
        if have is None:
            out[store] = dict(src, half=half, missing=None,
                              why="the board's %s could not be read, so what is missing from it is "
                                  "UNKNOWN — not everything, and not nothing" % store)
            continue
        backed = led.get(store)
        if not isinstance(backed, (dict, list)):
            out[store] = dict(src, half=half, missing=None,
                              why="the backup carries no %s to restore from" % store)
            continue
        have_set = set(have if isinstance(have, list) else have.keys())
        back_keys = list(backed if isinstance(backed, list) else backed.keys())
        gap = [k for k in back_keys if k not in have_set]
        missing_total += len(gap)
        out[store] = dict(src, **{"half": half, "missing": gap, "count": len(gap),
                                  "inBackup": len(back_keys), "onBoard": len(have_set),
                                  "why": "%d name(s) are in %s and not on the board"
                                         % (len(gap), os.path.basename(spath))})
    # #246 W0c — the backup's own set-piece list, so proposal_from can send a set-piece key through
    # the SETS half. A backup's d2r_foundLog carries every set piece too (toggleSetPiece writes the
    # found ledger by design), and sent as a "unique" a piece fell into d2r_owned and was filed.
    # ⚠ THE UNION OVER EVERY FILE THIS PLAN READS. After a vault reset the NEWEST backup holds
    # setPieces [] while foundLog still carries the pieces — taking the list from the newest alone
    # would send every piece down the uniques half, the exact #246 W0c refill.
    _pieces = set()
    for _sp, _sb, _sw in [(path, blob, "")] + list(sources.values()):
        _pieces.update(_names(((_sb or {}).get("ledger") or {}).get("setPieces")))
    names_out = dict((s, os.path.basename(v[0])) for s, v in sources.items())
    moved = sorted(s for s in names_out if names_out[s] != os.path.basename(path))
    from_say = os.path.basename(path) + (
        " (%s)" % "; ".join("%s from %s" % (s, names_out[s]) for s in moved) if moved else "")
    base_why = ("%s would put back %d name(s) across %d store(s); %s are backed up but cannot be "
                "restored through the chronicle door and need their own path"
                % (from_say, missing_total, len(RESTORABLE), ", ".join(BACKED_UP_ONLY)))
    return {
        "ok": True, "file": os.path.basename(path), "takenAt": (blob or {}).get("takenAt"),
        "route": (blob or {}).get("route"), "stores": out, "missingTotal": missing_total,
        "setPieceNames": sorted(_pieces),
        # every backed-up store's source, so the doors for the stores this one cannot carry read
        # the SAME file the plan chose for them rather than re-deciding. [[copy-drift]]
        "sources": names_out, "fromSay": from_say, "drops": drops,
        "named": file is not None,
        # ⚠ SAID, NOT SILENTLY OMITTED. Three backed-up stores cannot travel through this door.
        "notRestorableHere": list(BACKED_UP_ONLY),
        "why": (("DROP-AWARE: %s. " % "; ".join(sources[s][2] for s in moved) if drops and moved
                 else "") + base_why),
    }


def backed_up_only_from(plan_out, d=None):
    """The three stores the chronicle door cannot carry, out of the SAME backup plan() chose.

    ══ v3215 — THE OTHER HALF OF `BACKED_UP_ONLY`, WHICH HAS BEEN A SENTENCE SINCE v2735 ════════
    `plan()['why']` has always ended "...are backed up but cannot be restored through the chronicle
    door and need their own path", and `notRestorableHere` publishes the list. v3213 and v3214
    built two of those paths — `rw_restore` and `owned_restore` — and a cross-family review then
    found the obvious thing: **nothing called them.** Two doors, a route each, and no caller
    anywhere in the tree. control_ui.html:8099 already records CI reddening v2735 for exactly this
    with `/api/ledger_restore_*`: "a route with no caller is plumbing with no tap".

    ⚠ IT RETURNS WHAT THE BACKUP HOLDS, NOT A DIFF. `owned` and `rwMade` go through union-only
    doors that skip what is already present, so the gap is computed by the board against its own
    live store rather than guessed at here from a snapshot that may be older than the screen.
    `gameFound` still has no door and is reported as such rather than silently dropped.
    [[the-unjoined-end]] [[plumbing-with-no-tap]]
    """
    if not (isinstance(plan_out, dict) and plan_out.get("ok") and plan_out.get("file")):
        return {}, "no plan to read a backup from"
    d = d or BACKUP_DIR
    # ⚠ EACH STORE FROM THE FILE THE PLAN CHOSE FOR IT. After a drop, owned/rwMade may come from the
    # last backup BEFORE the drop rather than the newest; re-reading `file` here would hand the
    # runeword door the emptied snapshot. basename() because this names a file in `d`, never a path.
    _srcs = plan_out.get("sources") if isinstance(plan_out.get("sources"), dict) else {}
    _cache = {}

    def _led_for(store):
        n = os.path.basename(str(_srcs.get(store) or plan_out["file"]))
        if n not in _cache:
            with io.open(os.path.join(d, n), encoding="utf-8") as fh:
                _cache[n] = (json.load(fh) or {}).get("ledger") or {}
        return _cache[n]
    try:
        led_owned, led_rw, led_gf = _led_for("owned"), _led_for("rwMade"), _led_for("gameFound")
    except Exception as e:
        return {}, "the backup could not be re-read (%s)" % str(e)[:60]
    out = {}
    owned = led_owned.get("owned")
    if isinstance(owned, list) and owned:
        out["owned"] = owned
    rw = led_rw.get("rwMade")
    if isinstance(rw, dict) and rw:
        out["rwMade"] = rw
    why = ""
    if isinstance(led_gf.get("gameFound"), dict) and led_gf["gameFound"]:
        why = ("gameFound carries %d row(s) and still has no door — it is NOT restored here, and "
               "saying so is the point" % len(led_gf["gameFound"]))
    return out, why


def proposal_from(plan_out):
    """Shape a plan into what the BOARD already accepts. -> dict or None. Writes nothing.

    The board's `window.chronicleApply` reads `proposal.wouldAdd`, so a restore is expressed in the
    same vocabulary a sweep uses. Nothing new is invented at the door.
    """
    if not (isinstance(plan_out, dict) and plan_out.get("ok")):
        return None
    add = {}
    for store, row in (plan_out.get("stores") or {}).items():
        gap = row.get("missing")
        if not gap:
            continue
        half = row.get("half")
        add.setdefault(half, [])
        for name in gap:
            # a restore asserts only that the name BELONGED — the board owns dating it, exactly as
            # it does for a hand tick. Inventing a date here would put a time on his screen that
            # nothing witnessed. [[unknown-stays-unknown]]
            #
            # ⚠⚠ v3213 — A LIST OF ROWS, NOT A DICT. THIS DOOR HAD NEVER APPLIED ANYTHING.
            # This built `add[half][name] = []`, a DICT keyed by name. `bible.html`'s
            # `chronicleApply` does `(add.uniques || []).forEach(...)`, and a plain object has no
            # `forEach`, so every restore that ever reached the board died with
            # *"(add.uniques || []).forEach is not a function"*. MEASURED 2026-09-16 on his live
            # board, restoring 85 uniques + 50 sets: the call reached bible.html (the TypeError
            # quotes bible.html's own v2690 comment) and wrote NOTHING.
            #
            # The shape was never guessed — a real sweep already ships
            # `"wouldAdd": {lg: [{"name": n, ...}, ...]}` at two call sites in control_app.py, and
            # this function's own docstring promises "the same vocabulary a sweep uses". It said
            # so and did the other thing.
            #
            # ⚠ WHY NOTHING CAUGHT IT: `plan()` is read-only and its counts were always right, so
            # every test and every dry run looked correct. The only half that was wrong was the one
            # that crosses into the board, and nothing on this side of that boundary could see it.
            # [[the-unjoined-end]] [[plumbing-with-no-tap]]
            add[half].append({"name": name})
    # ══ #246 W0c — A SET PIECE TRAVELS AS A SET. The foundLog half carries every set piece as well
    # (toggleSetPiece writes the found ledger), so a piece rode the UNIQUES half, the board's uniques
    # branch called toggleOwned, and toggleOwned's else-branch put the piece in d2r_owned — 19 set pieces
    # became mule filings that way on 2026-09-16 (15:28:34). A name the backup lists as a set piece goes
    # through `sets` only, once. [[the-unjoined-end]]
    _pieces = set(plan_out.get("setPieceNames") or [])
    if _pieces and add.get("uniques"):
        _moved = [r for r in add["uniques"] if r.get("name") in _pieces]
        add["uniques"] = [r for r in add["uniques"] if r.get("name") not in _pieces]
        if _moved:
            _have = {r.get("name") for r in add.get("sets") or []}
            add.setdefault("sets", [])
            add["sets"].extend(r for r in _moved if r.get("name") not in _have)
        if not add["uniques"]:
            del add["uniques"]
    if not add:
        return None
    return {"wouldAdd": add, "source": "ledger_restore", "file": plan_out.get("file")}
