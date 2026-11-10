# -*- coding: utf-8 -*-
"""Known CI flakes: auto-rerun a failed job only when the ledger says it is a flake
(or when the runner, not the test, ended it). Prune an entry after N consecutive
clean runs so a healed flake does not buy a silent retry forever.

N_CLEAN defaults to 3. ship_when_green records a clean or a fail after each round.
"""
from __future__ import print_function

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except ImportError:
    pass

NAME = "flake_ledger.json"
N_CLEAN = 3
# GitHub's words, already used by REG-3292, plus a job cancelled by the ceiling.
INFRA = (
    "The runner has received a shutdown signal",
    "The runner has encountered an error",
    "The operation was canceled",
)


def path(root=None):
    return os.path.join(root or REPO, "tv", NAME)


def load(root=None):
    p = path(root)
    try:
        with open(p, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {"nClean": N_CLEAN, "entries": {}}
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    data.setdefault("nClean", N_CLEAN)
    data.setdefault("entries", {})
    return data


def save(data, root=None):
    p = path(root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return p


def is_infra(text):
    blob = text or ""
    return any(s in blob for s in INFRA)


def is_flake(name, data=None, root=None):
    data = data if data is not None else load(root)
    if not data:
        return False
    return name in (data.get("entries") or {})


def should_rerun(name, log_text=None, data=None, root=None):
    """A failed job is re-run once when it is a known flake, or when the runner ended it."""
    if is_infra(log_text):
        return True, "runner or cancellation, not the test"
    if is_flake(name, data=data, root=root):
        return True, "known flake"
    return False, "not a known flake and not an infrastructure kill"


def record(name, failed, data=None, root=None, now=None, save_file=True):
    """failed=True resets the clean streak; failed=False increments it and prunes at nClean.
    -> the updated ledger. A name that was never a flake is not added on a clean run."""
    data = data if data is not None else (load(root) or {"nClean": N_CLEAN, "entries": {}})
    entries = data.setdefault("entries", {})
    n_clean = int(data.get("nClean") or N_CLEAN)
    at = int(now if now is not None else time.time())
    if failed:
        row = entries.get(name) or {"fails": 0, "cleans": 0}
        row["fails"] = int(row.get("fails") or 0) + 1
        row["cleans"] = 0
        row["last"] = at
        entries[name] = row
    else:
        row = entries.get(name)
        if row is not None:
            row["cleans"] = int(row.get("cleans") or 0) + 1
            row["last"] = at
            if row["cleans"] >= n_clean:
                entries.pop(name, None)
            else:
                entries[name] = row
    if save_file:
        save(data, root)
    return data


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    data = load()
    if data is None:
        print("flake ledger will not read - UNKNOWN")
        return 2
    if "--show" in argv:
        print("nClean=%s  entries=%d" % (data.get("nClean"), len(data.get("entries") or {})))
        for k, v in sorted((data.get("entries") or {}).items()):
            print("  %-40s fails=%s cleans=%s" % (k, v.get("fails"), v.get("cleans")))
        return 0
    print("usage: flake_ledger.py --show")
    return 0


if __name__ == "__main__":
    sys.exit(main())
