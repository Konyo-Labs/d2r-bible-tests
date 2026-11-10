# -*- coding: utf-8 -*-
"""v3895 (#190, REG-3590) - RETRO AI CHECKER, FIRST SLICE: WHICH FRAMES TO RE-READ.

A retro checker runs AFTER a reel seals, never in the live loop. It re-reads the
IMPORTANT frames (a grail, a keep, a unique/set/runeword) and the UNCERTAIN ones
(KAI and OCR disagreed, or the live read said so). Calling a second model and
surfacing a GROK verdict is the rest of the checker.
"""

IMPORTANT_KINDS = frozenset(("grail", "keep", "unique", "set", "runeword"))


def pick_frames(journal):
    """Frames a sealed reel's retro checker should re-read.

    journal is an iterable of row dicts (the sealed session's journal).
    -> list of {frame, why, kind}. None when the journal cannot be read.
    [] when nothing in it is important or uncertain (a measured none).
    """
    if journal is None:
        return None
    try:
        rows = list(journal)
    except TypeError:
        return None
    out = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        frame = row.get("frame") or row.get("fid") or row.get("frameId")
        if not frame or frame in seen:
            continue
        kind = str(row.get("kind") or row.get("tier") or "").strip().lower()
        uncertain = (
            row.get("uncertain") is True
            or row.get("disagree") is True
            or (row.get("kai") not in (None, "") and row.get("ocr") not in (None, "")
                and row.get("kai") != row.get("ocr"))
        )
        if kind in IMPORTANT_KINDS:
            why = "important: " + kind
        elif uncertain:
            why = "uncertain: the live readers disagreed"
            kind = kind or "uncertain"
        else:
            continue
        seen.add(frame)
        out.append({"frame": frame, "why": why, "kind": kind})
    return out
