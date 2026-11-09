# -*- coding: utf-8 -*-
"""Compare a character-window sheet against cited planner reference values.

#28. Buff calibration stays later. No itemized d2planner export lives on this tree,
so the only numbers used here are the published breakpoint tables already cited in
tv/test_the_breakpoint_row_is_the_next_step.py (maxroll Patch 2.4 breakpoints page,
fetched 2026-10-04). d2planner uses those same published tables for FCR/FHR/FBR/IAS
frames. A key the planner dict does not name is unknown — never invented.
"""
import re

# Sorceress, other weapon, 0% Faster Cast Rate -> 13 frames; next step at 9% / 12 frames.
# Source: maxroll Patch 2.4 breakpoints page (fetched 2026-10-04), TABLES in
# tv/test_the_breakpoint_row_is_the_next_step.py ("fcr", {"cls": "Sorceress", "weapon": "other"}).
CITED_SORC_FCR_0 = {
    "source": ("maxroll Patch 2.4 breakpoints page (fetched 2026-10-04); "
               "d2planner uses the same published tables"),
    "fcr": {"frames": 13, "pct": 0, "next_pct": 9, "next_frames": 12},
}


def _frames_of(row):
    if not isinstance(row, dict):
        return None
    fr = row.get("frames")
    if isinstance(fr, int) and not isinstance(fr, bool):
        return fr
    step = row.get("step")
    if isinstance(step, str):
        m = re.search(r"(\d+)\s+frames", step)
        if m:
            return int(m.group(1))
    return None


def compare_window_to_planner(sheet, planner):
    """Compare character-window rows to cited planner refs.

    planner maps a row key to a dict that must name `frames` and may name `source`.
    A top-level `source` string is citation only. Missing or unusable planner
    values are unknown — this function never fills them in.
    -> list of {key, verdict: agree|conflict|unknown, ...}
    """
    if not isinstance(planner, dict):
        return [{"key": None, "verdict": "unknown", "why": "no planner reference was given"}]
    rows = {}
    if isinstance(sheet, dict):
        for r in sheet.get("rows") or []:
            if isinstance(r, dict) and r.get("key"):
                rows[r["key"]] = r
    out = []
    for key, ref in planner.items():
        if key == "source":
            continue
        if not isinstance(ref, dict) or "frames" not in ref:
            out.append({"key": key, "verdict": "unknown",
                        "why": "planner reference does not name frames"})
            continue
        if not isinstance(ref.get("frames"), int) or isinstance(ref.get("frames"), bool):
            out.append({"key": key, "verdict": "unknown",
                        "why": "planner frames are not a counted number"})
            continue
        row = rows.get(key)
        if not row:
            out.append({"key": key, "verdict": "unknown",
                        "why": "the character window has no %s row" % key})
            continue
        frames = _frames_of(row)
        if frames is None:
            out.append({"key": key, "verdict": "unknown",
                        "why": "the window row does not say its frames"})
            continue
        cite = ref.get("source") or planner.get("source")
        if frames == ref["frames"]:
            rec = {"key": key, "verdict": "agree", "frames": frames}
        else:
            rec = {"key": key, "verdict": "conflict",
                   "window": frames, "planner": ref["frames"]}
        if cite:
            rec["source"] = cite
        out.append(rec)
    return out
