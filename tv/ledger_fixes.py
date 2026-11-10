# -*- coding: utf-8 -*-
"""v3895 (#26, REG-3598) - P5: A SURGICAL RETRO FIX LEAVES A RECEIPT.

LEDGER3 §8: append-only per-PC ledger_fixes.jsonl. This is the store and its
write/read doors. Wiring the board, merge, and START buttons is later.
"""
import io
import json
import os

STORE = "ledger_fixes.jsonl"


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

def record(root, fix_id, frame, plan=None, applied=None):
    """Append one fix receipt. -> dict written. Needs an id and a proof frame."""
    fid = str(fix_id or "").strip()
    fr = str(frame or "").strip()
    if not fid or not fr:
        raise ValueError("a ledger fix needs an id and a proof frame")
    return _append(root, {
        "id": fid,
        "frame": fr,
        "plan": plan,
        "applied": applied,
    })


def fixes_of(root, fix_id):
    """Receipts for this fix id. [] if none or absent. None if unreadable."""
    fid = str(fix_id or "").strip()
    if not fid:
        return []
    rows = _read(root)
    if rows is None:
        return None
    return [r for r in rows if str(r.get("id") or "") == fid]


