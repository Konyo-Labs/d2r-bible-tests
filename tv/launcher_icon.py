# -*- coding: utf-8 -*-
"""v3849 (Elad 11:31) - THE DESKTOP LAUNCHER WEARS THE SHIPPED LOGO.

install-tvd.sh copies tv/appicon.icns into the TV DIABLO.app it makes, ONCE. A later logo (v3844 skull TV, v3847
stretched) never reached the Desktop launcher, so his double-click icon still showed the old art. Every launch now
re-checks: each TV DIABLO.app in ~/Desktop and ~/Applications whose launcher runs THIS repo's start_tvd_mac.sh gets
the repo's appicon.icns as its AppIcon.icns when the bytes differ, and the bundle is touched so Finder redraws it.
Only the icon resource is replaced; a bundle is never moved, renamed or deleted, and one that runs another tree is
left alone.
"""
import os, shutil, sys

APP_NAMES = ("TV DIABLO.app",)


def candidates(home):
    return [os.path.join(home, d, n) for d in ("Desktop", "Applications") for n in APP_NAMES]


def _runs_this_repo(app, repo):
    try:
        with open(os.path.join(app, "Contents", "MacOS", "launcher"), encoding="utf-8", errors="replace") as f:
            return os.path.join(repo, "tv", "start_tvd_mac.sh") in f.read()
    except OSError:
        return False


def _same(a, b):
    try:
        with open(a, "rb") as fa, open(b, "rb") as fb:
            return fa.read() == fb.read()
    except OSError:
        return False


def refresh(home, repo):
    """-> list of (app, verdict) with verdict in updated / current / other-tree / no-bundle / failed: <why>."""
    src = os.path.join(repo, "tv", "appicon.icns")
    out = []
    if not os.path.isfile(src):
        return [("-", "failed: no tv/appicon.icns in this tree")]
    for app in candidates(home):
        if not os.path.isdir(app):
            out.append((app, "no-bundle")); continue
        if not _runs_this_repo(app, repo):
            out.append((app, "other-tree")); continue
        dst = os.path.join(app, "Contents", "Resources", "AppIcon.icns")
        if _same(src, dst):
            out.append((app, "current")); continue
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            os.utime(app, None)   # Finder re-reads a bundle's icon when the bundle itself changes
            out.append((app, "updated"))
        except OSError as e:
            out.append((app, "failed: %s" % type(e).__name__))
    return out


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    for app, v in refresh(os.path.expanduser("~"), os.path.dirname(here)):
        if v in ("updated",) or v.startswith("failed"):
            print("launcher icon: %s - %s" % (os.path.basename(app), v))
