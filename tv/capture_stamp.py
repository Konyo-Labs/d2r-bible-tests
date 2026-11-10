# -*- coding: utf-8 -*-
"""What a NEW reel may record about the window it was filmed from.

route, windowLabel, w, h, os, dpi. A field that was not measured is absent.
An old index is never rewritten, and reading one back never fills a route.
"""
import json
import os
import sys

ROUTES = ("native", "geforce-now", "boosteroid", "unknown")
OSES = ("mac", "windows", "linux")
KEYS = ("route", "windowLabel", "w", "h", "os", "dpi")


def os_of_this_process():
    """The machine this process is running on. -> 'mac'|'windows'|'linux'|None"""
    p = sys.platform
    if p == "darwin":
        return "mac"
    if p.startswith("win"):
        return "windows"
    if p.startswith("linux"):
        return "linux"
    return None


def _whole(v, lo=1):
    if isinstance(v, bool) or not isinstance(v, int):
        return None
    return v if v >= lo else None


def from_measured(measured):
    """Copy only fields that were measured. -> dict, possibly empty.

    dpi is copied only when dpiMeasured is True. A fallback number is not a measurement.
    w and h travel together: a width without a height is not a size.
    """
    if not isinstance(measured, dict):
        return {}
    out = {}
    route = measured.get("route")
    if route in ROUTES:
        out["route"] = route
    label = measured.get("windowLabel")
    if isinstance(label, str):
        label = " ".join(label.split())
        if label:
            out["windowLabel"] = label[:120]
    w, h = _whole(measured.get("w")), _whole(measured.get("h"))
    if w and h:
        out["w"] = w
        out["h"] = h
    os_name = measured.get("os")
    if os_name in OSES:
        out["os"] = os_name
    dpi = _whole(measured.get("dpi"), 72)
    if dpi is not None and measured.get("dpiMeasured") is True:
        out["dpi"] = dpi
    return out


def from_index(index):
    """What this reel recorded. Every key is present. Unmeasured is None.

    A route that is not one of the four names is None. Nothing is filled in.
    """
    src = index.get("capture") if isinstance(index, dict) else None
    if not isinstance(src, dict):
        src = {}
    label = src.get("windowLabel")
    if not isinstance(label, str) or not label.strip():
        label = None
    else:
        label = " ".join(label.split())[:120] or None
    w, h = _whole(src.get("w")), _whole(src.get("h"))
    if not (w and h):
        w = h = None
    dpi = _whole(src.get("dpi"), 72)
    return {
        "route": src.get("route") if src.get("route") in ROUTES else None,
        "windowLabel": label,
        "w": w,
        "h": h,
        "os": src.get("os") if src.get("os") in OSES else None,
        "dpi": dpi,
    }


def beside_frame(path):
    """The capture recorded on the reel this frame lives in. -> dict | None

    A loose frame has no reel yet, so this is None. A reel whose index recorded
    nothing is None. The live pin is not consulted: a reel that recorded none
    does not inherit whatever this machine is filming now.
    """
    try:
        parent = os.path.dirname(os.path.abspath(path or ""))
    except Exception:
        return None
    if not os.path.basename(parent).startswith("reel_"):
        return None
    try:
        with open(os.path.join(parent, "index.json"), encoding="utf-8") as fh:
            idx = json.load(fh)
    except Exception:
        return None
    present = {k: v for k, v in from_index(idx).items() if v is not None}
    return present or None
