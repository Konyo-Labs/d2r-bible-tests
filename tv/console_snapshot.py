#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shadow mode: one console's account stores, synced on its Roster profile, so another console can show them read only.

The board collects its active world's stores with _collectProgress (the Backup v2 rule: bare names,
this world only, no pointer or identity keys) and posts them to the console. This module decides what
of that may leave the PC, when it is synced, and what a viewer is told about its age.

What leaves: `d2r_*` stores only, each one a JSON string as the board wrote it, never re-typed. Stores
that are history logs, film evidence or debug routes stay home (DENY). A string that names a path on
disk or an install id is blanked; nothing else in a store is changed, so the viewer's board reads the
same bytes the owner's board reads and draws the same screens, mods and all.

The profile rides the roster publish (same route, same signing key) to its own record `roster:<owner>:profile`
(functions/api/roster.js (profile)). It is change-only and at most once per MIN_GAP_MS, a boot
included (a boot past the gap posts even unchanged); the worker holds the daily cap, and a boot that skipped the gap
spent it on every restart (the ALT, 2026-10-27). A viewer reads that record. When the worker cannot be reached the last
copy this PC fetched is shown with the time it was synced: shadow works whether the other console
is up or not.
"""

import json
import os
import re

import roster_publish as _rp

OWNERS = _rp.OWNERS
# v3862 - WORKERS PAID (confirmed 2026-11-05): 150 uploads a day spread over 24 h is one per 9.6 min; the console waits
# 10 so the worker's daily cap is a backstop, not the pacing. The worker itself only refuses inside 8 min. On the free
# plan it was 20 a day and 75 min - a shadow lagged its owner by up to an hour and a quarter.
MIN_GAP_MS = 10 * 60 * 1000
DAY_CAP = 150
# the worker's frames door cap (functions/api/roster.js FRAMES_DAY_CAP), counted here so the budget names every writer;
# test_shadow_mode_reads_their_console holds the two equal
FRAMES_DAY_CAP = 24
MAX_STORE = 64 * 1024
MAX_TOTAL = 180 * 1024
LIVE_MS = 15 * 60 * 1000

# History, film evidence, AI drafts and debug routes: large, private to that PC, and drawn by no
# screen shadow shows (characters, equipped, inventory, stash, mules, vault).
DENY = frozenset((
    "d2r_tvdHist", "d2r_tvdTallyLog", "d2r_chronicleInboxLog", "d2r_foundEvidence", "d2r_sessionLog",
    "d2r_intakeLog", "d2r_intakeSeen", "d2r_intakeUrl", "d2r_lsrRoute", "d2r_tz_hist_cache",
    "d2r_unseedBackup", "d2r_unseedReport", "d2r_unseedRestoreReport", "d2r_vaultLastReset",
    "d2r_createNow", "d2r_createNowDate", "d2r_createNowAi", "d2r_createNowAiArt", "d2r_createNowAiV",
    "d2r_createNowAiDate", "d2r_aicDraft", "d2r_aicQueue", "d2r_aicThrownLog", "d2r_lastTopScan",
    "d2r_grailFarm", "d2r_storeEmptied", "d2r_installId", "d2r_installIdCache", "d2r_ownerClaim",
    "d2r_activeProfile", "d2r_activeProfileWin", "d2r_activeMachine", "d2r_machineSource",
    "d2r_inboxReader", "d2r_logger", "d2r_testGuest",
))
DENY_PREFIX = ("d2r_quarantine", "d2r_d2jsp_", "d2r_api_")

# Two console answers the board's screens draw beside its stores: the characters this PC's reels learned (with
# what each wore) for the Characters room, and the MAIN gear locks. They ride in the snapshot as d2r_api_<name>,
# the console adds them (a board post may not), and the shadow frame answers GET /api/<name> from them. Only the
# fields the board reads are kept, so a ticking counter does not make every upload "changed".
API_FIELDS = {
    # GrokBot bug 7 (2026-10-27): the shadow's character evidence section ("named on the lobby or the character panel,
    # citing the frame") drew nothing because these two were trimmed. Frame NAMES only, as text - never a picture.
    "chars_learned": ("ok", "chars", "gear", "gearWhy", "minVisits", "tierBars", "cPanel", "surfaceWitnesses", "lobbyBySize",
                      # #36 (REG-2907) - the character each session is on: the shadow's vault draws whose stash a look filmed
                      "sessions", "sessionsWhy",
                      # v3855 pt1198u - who found what, and each character's sessions (answers only, never a password)
                      "identity"),
    "main_locks": ("ok", "locked", "tracked", "floor", "minSightings", "canEverLock", "blockedWhy"),
    "world": ("machine", "profile", "ledger", "os", "cousin"),
    # v3849 (a) - the owner's picture map for the frames the vault cites, and the address its console answers on, so a
    # shadow's magnifier draws the OWNER's frame (never a picture of the viewer's own). Names and words only.
    "pictures": ("ok", "pictures", "origin"),
    # #251 (REG-3079) - why this PC's saves name what they name (no .d2s here, no save folder): the shadow's Characters
    # room says the owner's reason. The names ride in the roster's characters section (REG-2929), not here.
    "saves": ("ok", "state", "d2sWhy", "why"),
}
# The world the owner's board drew in: which machine and profile its stores belong to, the ledger it keeps and the
# OS it reported. The shadow frame takes these instead of the viewer's own, so a Mac viewing a Windows owner draws
# the Windows world (its ribbon, its seed floor, its prefixes). Closed values only: nothing else rides here.
WORLD_VALUES = {"machine": ("mac", "windows"), "profile": ("main", "ladder"),
                "os": ("MAC", "WINDOWS", "LINUX", "ANDROID", "THIS MACHINE")}
_LEDGER = re.compile(r"^[^\x00-\x1f\"<>\\]{0,40}$")
API_PREFIX = "d2r_api_"

_KEY = re.compile(r"^d2r_[A-Za-z0-9_]{1,60}$")
_PRIVATE = (
    re.compile(r"(?:/Users/|/home/|/private/|/var/folders/)[^\s\"']*"),
    re.compile(r"[A-Za-z]:\\\\?(?:Users|Documents and Settings)\\\\?[^\s\"']*"),
    # An install id is crypto.randomUUID() (v4), dashed or not: the version and variant digits pin the shape so
    # an item or reel hash of 32 hex is left alone.
    re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}(?![0-9a-fA-F])"),
    re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![0-9a-fA-F])"),
    re.compile(r"\b(?:ghp_|gho_|ghs_|github_pat_|xox[abposr]-|sk-)[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\b[A-Za-z0-9][A-Za-z0-9\-]{0,62}\.local\b"),
    re.compile(r"\bI?L?·[0-9a-f]{8}·"),
    re.compile(r"data:image/[^\s\"']*"),
)


def budget():
    """KV writes a day (v3862, Workers Paid). `together` is six PCs: presence 4,896 + roster 6x25 + snapshot 6xDAY_CAP.
    `worst` is every owner label writing at both caps. Both under the fleet's own 10,000-a-day ceiling (roster.js)."""
    roster = _rp.budget()
    snap = roster["pcs"] * DAY_CAP
    frames = roster["pcs"] * FRAMES_DAY_CAP
    labels = len(OWNERS)
    worst = roster["presence"] + labels * (roster["perPc"] + DAY_CAP + FRAMES_DAY_CAP)
    return {"presence": roster["presence"], "roster": roster["roster"], "profile": snap, "frames": frames,
            "together": roster["together"] + snap + frames, "worst": worst, "ceiling": roster["ceiling"]}


def profile_key(owner):
    return ("roster:" + owner + ":profile") if owner in OWNERS else None


def _scrub_text(s):
    out = s
    for rx in _PRIVATE:
        out = rx.sub("", out)
    return out


def _scrub(v):
    """-> (value, changed). Strings that name a path, an install id or a picture are blanked in place."""
    if isinstance(v, str):
        t = _scrub_text(v)
        return t, t != v
    if isinstance(v, list):
        changed = False
        out = []
        for x in v:
            y, c = _scrub(x)
            out.append(y)
            changed = changed or c
        return out, changed
    if isinstance(v, dict):
        changed = False
        out = {}
        for k, x in v.items():
            k2 = _scrub_text(k) if isinstance(k, str) else k
            y, c = _scrub(x)
            out[k2] = y
            changed = changed or c or k2 != k
        return out, changed
    return v, False


def scrub_store(raw):
    """One store's JSON string -> the string that may leave this PC (verbatim when nothing private)."""
    if not isinstance(raw, str):
        return None
    try:
        parsed = json.loads(raw)
    except Exception:
        t = _scrub_text(raw)
        return t
    clean, changed = _scrub(parsed)
    if not changed:
        return raw
    return json.dumps(clean, ensure_ascii=False, separators=(",", ":"))


def allowed_key(k, board=True):
    """May this store leave the PC? board=False also admits the console's own d2r_api_<name> answers."""
    if not isinstance(k, str) or not _KEY.match(k):
        return False
    if not board and k.startswith(API_PREFIX):
        return k[len(API_PREFIX):] in API_FIELDS
    if k in DENY:
        return False
    return not any(k.startswith(p) for p in DENY_PREFIX)


def world_of(raw):
    """The board's {machine, profile, ledger, os} -> the same dict when every value is one it may be, else None."""
    if not isinstance(raw, dict):
        return None
    out = {}
    for k, allowed in WORLD_VALUES.items():
        if raw.get(k) not in allowed:
            return None
        out[k] = raw[k]
    # a ledger name the closed set cannot carry is sent as "" (unnamed) rather than losing the whole world
    ledger = raw.get("ledger")
    out["ledger"] = ledger if isinstance(ledger, str) and _LEDGER.match(ledger) else ""
    if not isinstance(raw.get("cousin"), bool):
        return None
    out["cousin"] = raw["cousin"]
    return out


#: REG-2688 (measured on the ALT, 2026-10-27 23:5x) - the fields an answer can travel without, LARGEST FIRST. v3814 added
#: the character evidence (surfaceWitnesses, lobbyBySize) to the upload, and on the ALT surfaceWitnesses alone is 83 KB:
#: the kept answer came to 104,837 bytes, over MAX_STORE, and api_store dropped the WHOLE character list without a word.
#: Over the cap these are left out one at a time until the answer fits; the characters themselves always go up.
API_OPTIONAL = {"chars_learned": ("surfaceWitnesses", "gear", "lobbyBySize", "identity", "sessions")}   # REG-2907: sessions go last


#: v3849 (a) - an address a viewer can open: http(s), a host, an optional port, nothing after it
_ORIGIN = re.compile(r"^https?://[A-Za-z0-9][A-Za-z0-9.\-]{0,252}(?::[0-9]{1,5})?$")
PICTURES_MAX = 40


def pictures_of(raw):
    """The console's picture answer -> {ok, pictures, origin?} with closed shapes, or None.

    pictures: frame id -> {present: True|False|None, code: short word, why: words or None}; at most PICTURES_MAX.
    origin: kept only when it is an address shape (_ORIGIN); anything else is left out, never guessed."""
    if not isinstance(raw, dict) or raw.get("ok") is not True or not isinstance(raw.get("pictures"), dict):
        return None
    pics = {}
    for fid in sorted(raw["pictures"])[:PICTURES_MAX]:
        v = raw["pictures"][fid]
        if not isinstance(fid, str) or not (0 < len(fid) <= 120) or not isinstance(v, dict):
            continue
        pr = v.get("present")
        code, why = v.get("code"), v.get("why")
        pics[fid] = {"present": pr if pr in (True, False) else None,
                     "code": code[:40] if isinstance(code, str) else None,
                     "why": why[:200] if isinstance(why, str) else None}
    out = {"ok": True, "pictures": pics}
    org = raw.get("origin")
    if isinstance(org, str) and _ORIGIN.match(org):
        out["origin"] = org
    return out


def api_store(name, payload, left_out=None):
    """-> (store name, JSON string) for one console answer, or None when it is not one the shadow serves.

    `left_out`, a list, gets the optional fields (API_OPTIONAL) dropped to fit MAX_STORE, so the caller can say so."""
    fields = API_FIELDS.get(name)
    if name == "world":
        payload = world_of(payload)
    if name == "pictures":
        payload = pictures_of(payload)
    if not fields or not isinstance(payload, dict):
        return None
    kept = {f: payload[f] for f in fields if f in payload}
    text = scrub_store(json.dumps(kept, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    for opt in API_OPTIONAL.get(name, ()):
        if text is not None and len(text) <= MAX_STORE:
            break
        if opt in kept:
            kept.pop(opt)
            if isinstance(left_out, list):
                left_out.append(opt)
            text = scrub_store(json.dumps(kept, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    if text is None or len(text) > MAX_STORE:
        return None
    return API_PREFIX + name, text


def with_api(stores, answers, report=None):
    """The board's cleaned stores plus the console answers that could be read. A failed read stays out.

    `report`, a dict, gets {name: [fields left out to fit]} and {name: None} for an answer that would not fit at all."""
    out = dict(stores or {})
    for name in sorted(answers or {}):
        left = []
        got = api_store(name, answers[name], left)
        if got:
            out[got[0]] = got[1]
            if left and isinstance(report, dict):
                report[name] = left
        elif isinstance(report, dict) and name in API_OPTIONAL and isinstance(answers[name], dict):
            report[name] = None
    return out


def clean(body):
    """The board's post -> {"stores": {name: json string}, "dropped": [names]} or None.

    A store that is not allowed, not a string, or too big is dropped and NAMED, never sent empty.
    The total is capped by dropping the largest stores first, so the small account stores
    (builds, mules, vault records) are the last to go."""
    if not isinstance(body, dict):
        return None
    stores = body.get("stores")
    if not isinstance(stores, dict):
        return None
    out, dropped = {}, []
    for k in sorted(stores):
        v = stores[k]
        if not allowed_key(k) or not isinstance(v, str):
            dropped.append(str(k)[:60])
            continue
        s = scrub_store(v)
        if s is None or len(s) > MAX_STORE:
            dropped.append(k)
            continue
        out[k] = s
    total = sum(len(k) + len(v) for k, v in out.items())
    for k in sorted(out, key=lambda n: (-len(out[n]), n)):
        if total <= MAX_TOTAL:
            break
        total -= len(k) + len(out[k])
        del out[k]
        dropped.append(k)
    if not out:
        return None
    dropped = sorted(set(dropped))
    return {"stores": out, "dropped": dropped, "unsent": unsent_of(dropped)}


#: #210 - how many left-out names an upload names; past it the banner says "and N more".
UNSENT_MAX = 40


def unsent_of(dropped):
    """#210 (GrokBot) - the stores a shadow is MISSING: dropped for size, for carrying something private, or for not being
    a string. A store kept home on purpose (DENY, DENY_PREFIX) is not missing, and a name that is not a d2r_ store is
    not a store. -> sorted [names] (at most UNSENT_MAX)"""
    out = []
    for k in dropped or []:
        if isinstance(k, str) and _KEY.match(k) and k not in DENY and not any(k.startswith(p) for p in DENY_PREFIX):
            out.append(k)
    return sorted(set(out))[:UNSENT_MAX]


def digest(stores):
    """FNV-1a over the packed stores: the same hash functions/api/roster.js (profile) computes."""
    return _rp.hash_of(_rp.packed(stores or {}))


def gate(state, now_ms, boot):
    """#203 - could an upload go now, whatever the stores say? -> (open, why). The time half of due(), asked BEFORE the
    console's answers are built, so a tick inside the gap costs nothing. A refusal waits MIN_GAP_MS, and the last upload
    must be MIN_GAP_MS old - for a boot post too.

    THE QUOTA (measured on the ALT 2026-10-27 23:32): the site takes 20 profile uploads a day per owner, and a boot post
    skipped the gap, so every self-update restart spent one. After an evening of ships the ALT's .roster_profile_state.json
    read "quota: 20 uploads a day", the upload carrying its character list (v3814) was refused, and nothing could go up
    until the site's day turned. A boot inside the gap now waits like any tick; a boot past it still skips "unchanged"."""
    state = state if isinstance(state, dict) else {}
    refused = state.get("refuseAt")
    if isinstance(refused, int) and not isinstance(refused, bool) and now_ms - refused < MIN_GAP_MS:
        return False, state.get("why") or "the snapshot was refused"
    last = state.get("at")
    if isinstance(last, int) and not isinstance(last, bool) and now_ms - last < MIN_GAP_MS:   # the quota - boot too
        return False, "within %d min of the last upload" % (MIN_GAP_MS // 60000)
    return True, "open"


def due(state, owner, stores, now_ms, boot, unsent=None):
    """-> (body or None, why). Change-only, MIN_GAP_MS apart (a boot too - the quota, see gate); a boot past the gap
    posts even unchanged; a refusal waits MIN_GAP_MS. #210 - `unsent` (the book's unsent_of list) rides beside the
    stores so the shadow can name what it is missing; it is not in the hash."""
    state = state if isinstance(state, dict) else {}
    if not profile_key(owner):
        return None, "the owner is not one of the five labels"
    if not stores:
        return None, "the board has not posted its stores"
    d = digest(stores)
    refused = state.get("refuseAt")
    if isinstance(refused, int) and not isinstance(refused, bool) and now_ms - refused < MIN_GAP_MS:
        return None, state.get("why") or "the snapshot was refused"
    _last_ok = state.get("at") if isinstance(state.get("at"), int) and not isinstance(state.get("at"), bool) else None
    stale = _last_ok is not None and now_ms - _last_ok > STALE_MS
    if state.get("hash") == d and not boot and not stale:
        return None, "unchanged"
    _open, _why = gate(state, now_ms, boot)
    if not _open:
        return None, _why
    stores, fit_out = fit_body(stores)
    if not stores:
        return None, "the snapshot does not fit the site's %d byte cap even with the board stores left out" % PROFILE_MAX_BODY
    d = digest(stores)
    body = {"kind": "profile", "owner": owner, "boot": bool(boot), "signedAt": now_ms, "hash": d, "stores": stores}
    if isinstance(unsent, list) or fit_out:
        body["unsent"] = unsent_of(list(unsent or []) + fit_out)
    return body, "post"


#: v3856 - THE WORKER'S PROFILE CAP (functions/api/roster.js PROFILE_MAX_BODY), measured on the WIRE body. clean() caps the
#: board's stores at MAX_TOTAL, then with_api() adds the console's answers (up to MAX_STORE each) and json.dumps escapes
#: every quote inside each store string - so a heavy player's body passed 200,000 bytes and the worker refused it
#: ("the body is larger than 200000 bytes") every 75 min, forever: his shadow froze on his last small upload.
PROFILE_MAX_BODY = 200000
_WIRE_MARGIN = 2000      # owner, hash, signedAt, unsent list


def wire_len(stores):
    """Bytes the stores take inside the posted body, as the console's post serializes it (json.dumps, ensure_ascii off)."""
    return len(json.dumps({"stores": stores}, ensure_ascii=False).encode("utf-8"))


def fit_body(stores):
    """-> (stores that fit PROFILE_MAX_BODY on the wire, [names left out]). Board stores go largest first; the console's
    own answers (API_PREFIX) are kept, they are what a shadow's Characters and Vault draw."""
    out, left = dict(stores or {}), []
    budget = PROFILE_MAX_BODY - _WIRE_MARGIN
    order = sorted((k for k in out if not k.startswith(API_PREFIX)), key=lambda n: (-len(out[n]), n))
    for k in order:
        if wire_len(out) <= budget:
            break
        del out[k]
        left.append(k)
    if wire_len(out) > budget:
        return {}, left
    return out, left


def apply_reply(state, stores, reply, now_ms):
    state = dict(state or {})
    reply = reply if isinstance(reply, dict) else {}
    d = digest(stores or {})
    stored = reply.get("stored") or []
    state["post"] = {"at": now_ms, "ok": reply.get("ok") is True,
                     "why": str(reply.get("why") or ("stored" if "profile" in stored else
                                                    ",".join(s for s in (reply.get("skipped") or []) if isinstance(s, str))))[:200],
                     "signed": bool((reply.get("signing") or {}).get("signed"))}
    if reply.get("ok") is True and "profile" in stored:
        state.update(hash=d, at=now_ms, why="uploaded")
        state.pop("refuseAt", None)
        return state
    if reply.get("ok") is True:
        skipped = [s for s in (reply.get("skipped") or []) if isinstance(s, str)]
        if "unchanged" in skipped:
            state["hash"] = d
        state["at"] = now_ms
        state["why"] = "skipped: " + ",".join(skipped)
        return state
    state["refuseAt"] = now_ms
    why = reply.get("why")
    state["why"] = str(why)[:200] if isinstance(why, str) and why else "refused"
    return state


def record_ok(rec, owner):
    """A worker/cache record is usable only when it is this owner's and its hash matches its stores."""
    if not isinstance(rec, dict) or rec.get("owner") != owner:
        return False
    stores = rec.get("stores")
    if not isinstance(stores, dict) or not stores:
        return False
    if not all(allowed_key(k, board=False) and isinstance(v, str) for k, v in stores.items()):
        return False
    t = rec.get("t")
    if not isinstance(t, int) or isinstance(t, bool) or t <= 0:
        return False
    return rec.get("hash") == digest(stores)


def cache_path(directory, owner):
    name = _rp.cache_file_name(owner)
    if not name or not isinstance(directory, str) or not directory:
        return None
    path = os.path.abspath(os.path.join(directory, name))
    if os.path.dirname(path) != os.path.abspath(directory):
        return None
    return path


def write_cache(directory, rec):
    owner = rec.get("owner") if isinstance(rec, dict) else None
    if not record_ok(rec, owner):
        return False
    os.makedirs(directory, exist_ok=True)
    path = cache_path(directory, owner)
    if not path:
        return False
    keep = {k: rec[k] for k in ("owner", "t", "hash", "stores", "intentVerified", "keyId", "dropped", "unsent")
            if k in rec}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(keep, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)
    return True


def read_cache(directory, owner):
    path = cache_path(directory, owner)
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
    except Exception:
        return None
    return rec if record_ok(rec, owner) else None


def online_of(owner, fleet):
    """True / False from the presence fleet, None when the fleet was not read or names nobody as this owner."""
    if not isinstance(fleet, dict) or fleet.get("ok") is False:
        return None
    for state, rows in ((True, fleet.get("online")), (False, fleet.get("offline"))):
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            plat = row.get("platform")
            plat = "mac" if plat in ("darwin", "mac", "macos") else plat
            if _rp.owner_of(row.get("nickname"), plat) == owner:
                # v3850 - the ONE presence function decides: a row still listed but past its refresh is offline
                import fleet_presence as _fp
                return _fp.presence_of(row, state).get("online")
    return None


#: v3856 - a board older than this while its console was seen online is a STALLED upload, said on the banner, and the
#: console itself re-posts even an unchanged board past it (the site may have lost or refused the last one).
STALE_MS = 6 * 60 * 60 * 1000


def seen_of(owner, fleet):
    """v3856 - the ONE presence source (the Fleet row fleet_presence grades): -> epoch ms this owner's console was last
    seen, or None. The same row online_of reads."""
    if not isinstance(fleet, dict) or fleet.get("ok") is False:
        return None
    import datetime as _dt
    for rows in (fleet.get("online"), fleet.get("offline")):
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            plat = row.get("platform")
            plat = "mac" if plat in ("darwin", "mac", "macos") else plat
            if _rp.owner_of(row.get("nickname"), plat) != owner:
                continue
            t = row.get("t")
            try:
                return int(_dt.datetime.fromisoformat(str(t).replace("Z", "+00:00")).timestamp() * 1000)
            except (TypeError, ValueError):
                return None
    return None


def stall_of(rec_t, seen_ms, now_ms):
    """-> words when the console was seen online well after its board upload (an upload that stalled), else None."""
    if not isinstance(rec_t, int) or not isinstance(seen_ms, int) or seen_ms - rec_t <= STALE_MS:
        return None
    return "online %s but board %s old: upload stalled" % (_ago_words(now_ms - seen_ms), _ago_words(now_ms - rec_t).replace(" ago", ""))


def _ago_words(ms):
    m = max(0, ms) // 60000
    if m < 1:
        return "under 1 min ago"
    if m < 120:
        return "%d min ago" % m
    if m < 48 * 60:
        return "%d hr ago" % (m // 60)
    return "%d days ago" % (m // (24 * 60))


def view(owner, rec, now_ms, online=None, source="worker", fetch_why=None, seen=None):
    """What /api/roster-cache?profile= serves. `live` is the owner's console being up right now; the stores are
    always the last upload, and `words` always says when that upload was made.

    REG-3034 - AND WHAT IT WAS AN UPLOAD OF. The words said "last upload 44 min ago" while the same shadow's sessions list
    said "uploaded 12 min ago" (GrokBot v3836, #230 6485132266): two true ages of two different records - this board
    snapshot, held by the 75 min gap above, and the sessions digest posted at the owner's 03:00 restart - each read as the
    owner's last upload. An age names the thing it dates: here the board."""
    if owner not in OWNERS:
        return {"ok": False, "owner": owner, "why": "not one of the five owner labels"}
    if not record_ok(rec, owner):
        why = "%s has not uploaded a console snapshot yet" % owner
        if fetch_why and source == "cache":
            why += " (and the site could not be read: %s)" % str(fetch_why)[:80]
        elif fetch_why:
            why += " (the site says: %s)" % str(fetch_why)[:120]
        return {"ok": False, "owner": owner, "why": why, "source": source}
    t = rec["t"]
    ago = _ago_words(now_ms - t)
    if online is True:
        # #214 (GrokBot) - "live" beside "uploaded 20 min ago" read as a live view; the CONSOLE is online, the stores are the upload
        state, words = "live", "%s · online now · board uploaded %s" % (owner, ago)
    elif online is False:
        state, words = "offline", "%s · offline · board uploaded %s" % (owner, ago)
    else:
        state, words = "unknown", "%s · online UNKNOWN · board uploaded %s" % (owner, ago)
    if source == "cache":
        words += " · the site could not be read, showing this PC's last copy"
    stall = stall_of(t, seen, now_ms)      # v3856 - Fleet saw the console long after this board was uploaded
    if stall:
        words += " · " + stall
    # #210 (GrokBot) - a store the owner's PC could not send is MISSING here, and the banner says which. An upload from
    # before the list (no `unsent`) is UNKNOWN, never "everything was sent".
    unsent = unsent_of(rec.get("unsent")) if isinstance(rec.get("unsent"), list) else None
    if unsent:
        words += " · not sent (too big or private): " + ", ".join(unsent[:5]) + (
            " and %d more" % (len(unsent) - 5) if len(unsent) > 5 else "")
    out = {"ok": True, "owner": owner, "t": t, "hash": rec["hash"], "stores": rec["stores"],
           "state": state, "words": words, "source": source, "ago": ago, "unsent": unsent, "stall": stall,
           "seenAgo": _ago_words(now_ms - seen) if isinstance(seen, int) else None}
    iv = rec.get("intentVerified")
    out["intentVerified"] = iv if isinstance(iv, bool) else None
    kid = _rp.short_key_id(rec.get("keyId"))
    if kid:
        out["keyId"] = kid
    return out
