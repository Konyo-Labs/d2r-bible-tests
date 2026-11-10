# -*- coding: utf-8 -*-
"""v3895 (#26, REG-3596) - P3: AN ITEM TIER CROSSING LEAVES A LOG ROW.

LEDGER3 §8: append-only per-PC tier_log.jsonl. This is the store and its
write/read doors. Wiring the board, merge, and START buttons is later.
"""
import io
import json
import os

STORE = "tier_log.jsonl"


def store_path(root):
    return os.path.join(root, STORE)


def _append(root, row):
    path = store_path(root)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    line = json.dumps(row, ensure_ascii=False) + "\n"
    tmp = path + ".tmp"
    existing = b""
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            existing = fh.read()
    with open(tmp, "wb") as fh:
        fh.write(existing)
        fh.write(line.encode("utf-8"))
    os.replace(tmp, path)
    return row


def _read(root):
    path = store_path(root)
    try:
        with io.open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except FileNotFoundError:
        return []
    except OSError:
        return None
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            return None
        if not isinstance(row, dict):
            return None
        out.append(row)
    return out

def record(root, name, to_tier, from_tier=None, reel=None, session=None, by=None):
    """Append one tier crossing. -> dict written. Needs a name and the new tier."""
    nm = str(name or "").strip()
    dest = str(to_tier or "").strip()
    if not nm or not dest:
        raise ValueError("a tier crossing needs a name and the new tier")
    return _append(root, {
        "name": nm,
        "fromTier": from_tier,
        "toTier": dest,
        "reel": reel,
        "session": session,
        "by": by,
    })


def crossings_of(root, name):
    """Crossings for this name. [] if none or absent. None if unreadable."""
    nm = str(name or "").strip()
    if not nm:
        return []
    rows = _read(root)
    if rows is None:
        return None
    return [r for r in rows if str(r.get("name") or "") == nm]


