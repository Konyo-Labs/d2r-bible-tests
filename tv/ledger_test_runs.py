# -*- coding: utf-8 -*-
"""v3895 (#26, REG-3597) - P4: A PINPOINTED TEST RUN LEAVES A ROW.

LEDGER3 §8: append-only per-PC test_runs.jsonl. This is the store and its
write/read doors. Wiring the board, merge, and START buttons is later.
"""
import io
import json
import os

STORE = "test_runs.jsonl"


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

def record(root, run_id, session=None, verdict=None):
    """Append one test run. -> dict written. Needs a run id."""
    rid = str(run_id or "").strip()
    if not rid:
        raise ValueError("a test run needs an id")
    return _append(root, {
        "id": rid,
        "session": session,
        "verdict": verdict,
    })


def runs_of(root, run_id):
    """Rows for this run id. [] if none or absent. None if unreadable."""
    rid = str(run_id or "").strip()
    if not rid:
        return []
    rows = _read(root)
    if rows is None:
        return None
    return [r for r in rows if str(r.get("id") or "") == rid]


def open_runs(root):
    """Runs that have no verdict yet. [] if none or absent. None if unreadable."""
    rows = _read(root)
    if rows is None:
        return None
    return [r for r in rows if not r.get("verdict")]


