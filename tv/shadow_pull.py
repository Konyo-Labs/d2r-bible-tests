# -*- coding: utf-8 -*-
"""#208 (his ruling 2026-11-12 ~23:50 IST: "Pull to the Mac") - SHADOW SESSIONS PLAY EVERY FRAME, FROM THE MAC'S OWN COPY.

His ask (via GrokBot #230 6836226405): "shadow mode must render full screen and ALL frames of that session locally, and show
the game recording from when play starts". Each console listens only on its own PC and the site carries 3 small key frames a
session, so the frames come to the Mac: after a session is done on a PC, the Mac copies its frames over the network it already
reaches, and the shadow Theatre plays them from that copy.

MEASURED 11-12 on the work ALT's newest 16 reels: 1 to 1,558 frames, up to 528 MB a reel, ~1.2 GB in all - so the copy is
held to a BYTE budget, newest first, and never takes the Mac's free space under his 8 GB floor. Nothing on a PC is ever
deleted or written by this module; the PC keeps its reel.

Here: the pure planner (which reels are done, which frames to copy) - the lane, the ssh listing and the copy sit on top.
Every answer that cannot be measured is None (UNKNOWN), never an empty list that reads as "nothing to copy".
"""
import json
import os

QUIET_S = 600                       # a reel whose newest frame is 10+ min old is no longer being written
BUDGET_BYTES = 3 * 1024 ** 3        # the Mac's shadow copies, all PCs together
FLOOR_BYTES = 8 * 1024 ** 3         # his ON AIR floor: the copy never takes free space under it
CONFIG_NAME = ".shadow_pull.json"   # gitignored: each PC's ssh target never enters the public repo
REEL_PREFIX = "reel_s_"


def done_reels(listing, now_s, rolling=None, quiet_s=QUIET_S):
    """-> [reel] whose writing has ended, newest first; None when the listing is UNKNOWN.

    listing: [{"reel": name, "files": [{"name", "size", "mtime"}]}] as one PC reported it. A reel is done when it is not the
    PC's rolling reel and its newest frame is at least `quiet_s` old. A reel with no frames is not a session to copy."""
    if not isinstance(listing, list):
        return None
    out = []
    for r in listing:
        if not isinstance(r, dict):
            continue
        name = r.get("reel")
        files = r.get("files")
        if not (isinstance(name, str) and name.startswith(REEL_PREFIX)) or not isinstance(files, list) or not files:
            continue
        if rolling and name == rolling:
            continue
        try:
            newest = max(float(f.get("mtime")) for f in files if isinstance(f, dict))
        except (TypeError, ValueError):
            continue                 # a frame without a readable time: its reel's state is UNKNOWN, never copied on a guess
        if now_s - newest >= quiet_s:
            out.append((newest, name))
    return [n for _t, n in sorted(out, reverse=True)]


def plan(listing, done, have, budget_bytes=BUDGET_BYTES, held_bytes=0, free_bytes=None, floor_bytes=FLOOR_BYTES):
    """-> {"copy": [(reel, [file names])], "bytes": n, "why": str}; None when the Mac's free space is UNKNOWN.

    `done`: done_reels() newest first. `have`: {reel: set(file names already copied)}. `held_bytes`: the copies already on
    the Mac. A reel is copied whole or not started (a half reel plays as a hole), newest first, while the budget and the
    floor both hold; a reel already complete costs nothing; a reel bigger than the room left stops the walk (older ones
    are older still - the newest are what he plays)."""
    if free_bytes is None:
        return None
    by = {r.get("reel"): r for r in (listing or []) if isinstance(r, dict)}
    room = min(budget_bytes - held_bytes, free_bytes - floor_bytes)
    out, total, why = [], 0, "every done session is already here"
    for reel in done or []:
        files = by.get(reel, {}).get("files") or []
        got = (have or {}).get(reel) or set()
        want = [f for f in files if isinstance(f, dict) and f.get("name") not in got]
        if not want:
            continue
        cost = sum(int(f.get("size") or 0) for f in want)
        if cost > room - total:
            why = ("the budget (%d MB) is spent" % (budget_bytes // (1024 ** 2))
                   if budget_bytes - held_bytes <= free_bytes - floor_bytes
                   else "his 8 GB free floor would be crossed") + " - %s and older wait" % reel
            break
        out.append((reel, sorted(f.get("name") for f in want)))
        total += cost
        why = "%d session(s) to copy" % len(out)
    return {"copy": out, "bytes": total, "why": why}


def config_load(path):
    """-> {label: {"ssh": target, ...}} | {} (no file: no PC named yet) | None (a file that will not read: UNKNOWN)"""
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    return {k: v for k, v in d.items() if isinstance(k, str) and isinstance(v, dict) and isinstance(v.get("ssh"), str)}


def local_have(root):
    """-> {reel: set(file names)} of the copies under root/<reel>/; {} when nothing is copied yet"""
    out = {}
    if not os.path.isdir(root):
        return out
    for reel in os.listdir(root):
        if not reel.startswith("reel_s_"):      # a literal prefix: the unkeyable-laws ratchet keys a listing by it
            continue
        d = os.path.join(root, reel)
        if os.path.isdir(d):
            out[reel] = set(n for n in os.listdir(d) if n.endswith(".jpg"))
    return out


# ── the I/O: one ssh listing per PC, one sftp batch per reel. Read-only on the PC: ls and get, never a put or a rm. ──
import subprocess  # noqa: E402

LIST_PS = ("$h = Join-Path $env:USERPROFILE 'd2r_bible_tests\\tv\\frames\\hist'; $o = @(); "
           "Get-ChildItem $h -Directory -Filter 'reel_s_*' | Sort-Object LastWriteTime -Descending | Select-Object -First %d | "
           "ForEach-Object { $f = @(Get-ChildItem $_.FullName -File -Filter '*.jpg' | ForEach-Object { @{name=$_.Name; "
           "size=$_.Length; mtime=[int64](($_.LastWriteTimeUtc - [datetime]'1970-01-01').TotalSeconds)} }); "
           "$o += @{reel=$_.Name; files=$f} }; ConvertTo-Json -InputObject $o -Depth 4 -Compress")


def _ps_encoded(script):
    """the PowerShell script as -EncodedCommand (base64 UTF-16LE): the same bytes run under a cmd or a PowerShell ssh shell"""
    import base64
    return "powershell -NoProfile -EncodedCommand " + base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def _ssh_argv(pc, remote_cmd):
    key = os.path.expanduser(pc.get("key") or "")
    return (["ssh"] + (["-i", key] if key else []) + ["-o", "BatchMode=yes", "-o", "ConnectTimeout=8"]
            + list(pc.get("opts") or []) + [pc["ssh"], remote_cmd])


def list_remote(pc, newest=16, timeout=120, run=None):
    """-> one PC's listing (done_reels' input) | None (ssh or the answer did not read: UNKNOWN, never 'no reels')"""
    try:
        r = (run or subprocess.run)(_ssh_argv(pc, _ps_encoded(LIST_PS % int(newest))), capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if getattr(r, "returncode", 1) != 0:
        return None
    raw = (r.stdout or "").strip()
    try:
        d = json.loads(raw) if raw else []
    except ValueError:
        return None
    return d if isinstance(d, list) else ([d] if isinstance(d, dict) else None)


def copy_reel(pc, reel, names, dest_root, timeout=1800, run=None):
    """sftp the named frames of one reel into dest_root/<reel>/ over ONE connection (a batch of `get`s). -> (ok, why)"""
    d = os.path.join(dest_root, reel)
    os.makedirs(d, exist_ok=True)
    repo = (pc.get("repo") or "d2r_bible_tests").replace("\\", "/")
    lines = ["get \"%s/tv/frames/hist/%s/%s\" \"%s\"" % (repo, reel, n, os.path.join(d, n)) for n in names]
    batch = os.path.join(d, ".sftp_batch")
    with open(batch, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    key = os.path.expanduser(pc.get("key") or "")
    argv = (["sftp"] + (["-i", key] if key else []) + ["-o", "BatchMode=yes", "-o", "ConnectTimeout=8"]
            + list(pc.get("opts") or []) + ["-b", batch, pc["ssh"]])
    try:
        r = (run or subprocess.run)(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, "the copy did not finish (%s)" % type(e).__name__
    finally:
        try:
            os.remove(batch)
        except OSError:
            pass
    if getattr(r, "returncode", 1) != 0:
        return False, "sftp exit %s" % getattr(r, "returncode", "?")
    return True, "%d frame(s)" % len(names)


if __name__ == "__main__":
    import argparse
    import shutil
    ap = argparse.ArgumentParser(description="#208 shadow pull - copy done sessions from his PCs to this Mac")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_NAME))
    ap.add_argument("--dest", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames", "shadow"))
    ap.add_argument("--dry-run", action="store_true", help="list and plan, copy nothing")
    a = ap.parse_args()
    import time as _t
    cfg = config_load(a.config)
    if cfg is None:
        raise SystemExit("the shadow pull config would not read - UNKNOWN, nothing copied")
    if not cfg:
        raise SystemExit("no PC is named in %s yet - nothing to pull" % os.path.basename(a.config))
    held = sum(os.path.getsize(os.path.join(dp, f)) for dp, _d, fs in os.walk(a.dest) for f in fs if f.endswith(".jpg")) \
        if os.path.isdir(a.dest) else 0          # the budget is all PCs' copies together
    for label, pc in sorted(cfg.items()):
        root = os.path.join(a.dest, label.replace(" ", "_").replace("·", "-"))
        listing = list_remote(pc)
        if listing is None:
            print("%s: UNKNOWN - its reels could not be listed" % label)
            continue
        done = done_reels(listing, _t.time())
        have = local_have(root)
        free = shutil.disk_usage(os.path.dirname(a.dest) if os.path.isdir(os.path.dirname(a.dest)) else "/").free
        p = plan(listing, done, have, held_bytes=held, free_bytes=free)
        held += (p or {}).get("bytes", 0)
        print("%s: %d reel(s) listed, %d done, plan: %s (%d MB)" % (label, len(listing), len(done or []), p and p["why"],
                                                                   (p or {}).get("bytes", 0) // (1024 ** 2)))
        if a.dry_run or not p:
            continue
        for reel, names in p["copy"]:
            ok, why = copy_reel(pc, reel, names, root)
            print("   %s %s: %s" % ("copied" if ok else "STOPPED", reel, why))
            if not ok:
                break
