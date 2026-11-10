# -*- coding: utf-8 -*-
"""v3895 (#26, REG-3588) - P2: A SEALED REEL LEAVES A ROUTE RECEIPT.

LEDGER3 §8 P2: an append-only reel_routes.jsonl written at seal
{reel, name, frameKey, routedTo, why, gate}. This is the store and the write/read
doors. Wiring it into the sealer, the funnel click, and the shelf card is the rest
of P2. P3-P5 (tier log, test runs, ledger fixes) are later slices.
"""
import io
import json
import os

STORE = "reel_routes.jsonl"
FIELDS = ("reel", "name", "frameKey", "routedTo", "why", "gate")


def store_path(root):
    """Where this tree's route receipts live."""
    return os.path.join(root, STORE)


def record(root, reel, name=None, frameKey=None, routedTo=None, why=None, gate=None):
    """Append one seal receipt. -> dict written. Raises if reel is missing."""
    rid = str(reel or "").strip()
    if not rid:
        raise ValueError("a route receipt needs a reel")
    row = {
        "reel": rid,
        "name": name,
        "frameKey": frameKey,
        "routedTo": routedTo,
        "why": why,
        "gate": gate,
    }
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


def routes_of(root, reel):
    """Receipts for this reel. [] if none or the store is absent. None if unreadable."""
    rid = str(reel or "").strip()
    if not rid:
        return []
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
        if str(row.get("reel") or "") == rid:
            out.append(row)
    return out


def missing_receipts(root, sealed_reels):
    """Sealed reel ids that have no receipt. None if the store cannot be read."""
    wanted = [str(r).strip() for r in (sealed_reels or []) if str(r).strip()]
    if not wanted:
        return []
    path = store_path(root)
    try:
        with io.open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except FileNotFoundError:
        return list(wanted)
    except OSError:
        return None
    have = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            return None
        if isinstance(row, dict) and row.get("reel"):
            have.add(str(row.get("reel")))
    return [r for r in wanted if r not in have]
