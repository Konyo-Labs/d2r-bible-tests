#!/usr/bin/env python3
"""#255 - THE READER PARITY BENCH: every eye, the same frames, every capture shape, every machine.

His order (2026-11-07): "i want a test for anything visual reading on the macbook like the extractors from the frames all
the eyes we have built and everything related to the resolution from windows to macbook and also from fullscreen to
WINDOWED MODE ... tested by simulation and demonstrated based on the exact sessions and frames both ways so its a valid
test and thorough enough to cross reference each".

WHAT WAS MEASURED BEFORE THIS EXISTED (a Windows PC that plays D2R windowed, client 1507x755):
  * its reels hold 800 px frames - tv_diablo archives capture_win.ps1's eye.jpg (800 px cap, bilinear, JPEG q72) - while
    the Mac's reels hold 1440 px frames from the full capture (FILM_MAX_PX);
  * windowed, capture_win.ps1 PrintWindow(hwnd, hdc, 2) paints the WHOLE window (title bar + borders) into a CLIENT-sized
    bitmap: the frame carries the title bar at the top and loses the bottom of the HUD. Every anchor is shifted.

THE BENCH. A corpus of REAL sessions (default ~/d2r_bench_corpus - PRIVATE, never in the repo). For each sampled frame it
builds VARIANTS - the capture shapes a PC can hand the readers:
    native        the frame as its PC stored it
    win800        exactly capture_win.ps1's eye: longest side capped at 800, bilinear, JPEG q72
    titlebar      the windowed PrintWindow defect: content pushed down by a caption strip and right by a border,
                  cropped back to the frame's size (the HUD's bottom is lost)
    titlebar800   both - what a windowed Windows PC's reel holds today
    untitled      for a frame that ALREADY carries a caption strip: the strip found and cut, the rest kept
and runs every DETERMINISTIC eye on each (no model call, no network):
    stash_class   stash_eye.classify_stash_grid       -> the tab / grid label
    inv_title     stash_eye.inventory_title_visible   -> bool, or UNKNOWN when its OCR did not read (REG-3388)
    aspect_branch stash_eye.crops_for_aspect + last_crop_decision -> which crop law the frame's aspect takes
    chronicle     chronicle_template.detect           -> is_chronicle / tab
    prep_stash    surfaces.prepare(.., "stash")       -> the enlarged crop's size + its sharpness
    prep_runes    surfaces.prepare(.., "runes")       -> the same
    tooltip       tooltip_crop.changed_rect on consecutive frames -> the tooltip box, normalized to the frame
Every answer is compared with the NATIVE frame's answer for the same eye: agree / DIFFERS / UNKNOWN (the eye raised or
could not answer - never counted as agreement). The same command on the Mac and on a Windows PC over the SAME corpus gives
two reports whose native rows must match field for field - a difference there is platform drift (Python, Pillow, JPEG).

    python3 tv/reader_parity.py                       # whole corpus, 8 frames a reel
    python3 tv/reader_parity.py --per-reel 20 --out /tmp/parity.json
    python3 tv/reader_parity.py --compare a.json b.json   # two machines' reports, native rows side by side

Paid reads (the AI) are NOT run here; that is a separate, opt-in measurement (it costs reads and sends pixels out).
[[unknown-stays-unknown]] [[the-unjoined-end]] [[feedback-verify-not-proxy]]
"""
import argparse
import glob
import io
import json
import os
import platform
import sys
import shutil
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:      # #255 - the bench prints Δ and ✓/✗; Dean's cp1255 console must not crash while reporting
    from console_safe import enable as _console_safe_enable
    _console_safe_enable()
except Exception:
    pass

CORPUS = os.path.expanduser(os.environ.get("TV_BENCH_CORPUS") or "~/d2r_bench_corpus")
#: the Windows eye, exactly as tv/capture_win.ps1 SaveAll writes it
WIN_EYE_PX, WIN_EYE_Q = 800, 72
#: the windowed caption, as a fraction of the frame height, and the side border (Win10/11 at 100%: ~31 px caption on a
#: ~790 px client, ~8 px border) - measured on the windowed PC's own read.jpg (1568x793: caption strip at the top)
CAPTION_FRAC, BORDER_FRAC = 31.0 / 793.0, 8.0 / 1568.0
EYES = ("stash_class", "inv_title", "aspect_branch", "chronicle", "prep_stash", "prep_runes")
VARIANTS = ("native", "win800", "titlebar", "titlebar800", "untitled")


def _img():
    from PIL import Image
    return Image


def win800(src, dest):
    """capture_win.ps1's eye: longest side capped at 800 (only ever shrunk), bilinear, JPEG quality 72"""
    Image = _img()
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if w > WIN_EYE_PX or h > WIN_EYE_PX:
        s = min(WIN_EYE_PX / float(w), WIN_EYE_PX / float(h))
        im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.BILINEAR)
    im.save(dest, "JPEG", quality=WIN_EYE_Q)
    return dest


def titlebar(src, dest, caption=None, border=None):
    """the windowed PrintWindow defect: the whole window painted into a client-sized bitmap - a caption strip on top, a
    border on the left, the content pushed down/right and cut at the frame's bottom/right edge"""
    Image = _img()
    im = Image.open(src).convert("RGB")
    w, h = im.size
    cap = int(round(h * CAPTION_FRAC)) if caption is None else int(caption)
    bor = int(round(w * BORDER_FRAC)) if border is None else int(border)
    out = Image.new("RGB", (w, h), (32, 32, 32))
    out.paste((243, 243, 243), (0, 0, w, cap))                 # a light Windows caption strip
    out.paste(im, (bor, cap))                                   # PIL clips what falls off the bottom/right
    out.save(dest, "JPEG", quality=92)
    return dest


def caption_rows(src, max_frac=0.08):
    """-> how many top rows are a Windows caption strip (near-uniform and light, unlike any D2R frame's top), 0 when none"""
    Image = _img()
    im = Image.open(src).convert("L")
    w, h = im.size
    px = im.load()
    n = 0
    for y in range(int(h * max_frac)):
        vals = [px[x, y] for x in range(0, w, max(1, w // 160))]
        mean = sum(vals) / float(len(vals))
        light = sum(1 for v in vals if v > 200) / float(len(vals))
        if mean > 180 and light > 0.7:
            n = y + 1
        elif n and y > n + 1:
            break
    return n


def untitled(src, dest):
    """a frame that carries a caption strip: the strip cut off. -> dest, or None when the frame has none"""
    Image = _img()
    n = caption_rows(src)
    if not n:
        return None
    im = Image.open(src).convert("RGB")
    w, h = im.size
    im.crop((0, n, w, h)).save(dest, "JPEG", quality=92)
    return dest


def sharpness(path):
    """mean edge strength of the image (Pillow's FIND_EDGES on greyscale) - higher = crisper; None when unreadable"""
    try:
        from PIL import ImageFilter, ImageStat
        im = _img().open(path).convert("L")
        return round(ImageStat.Stat(im.filter(ImageFilter.FIND_EDGES)).mean[0], 2)
    except Exception:
        return None


def size_of(path):
    try:
        return list(_img().open(path).size)
    except Exception:
        return None


def run_eyes(path, work):
    """-> {eye: answer} for one image; an eye that raises answers {"unknown": why}"""
    import stash_eye as se
    import chronicle_template as ct
    import surfaces as sf
    out = {}

    def guard(name, fn):
        try:
            out[name] = fn()
        except Exception as e:
            out[name] = {"unknown": "%s: %s" % (type(e).__name__, str(e)[:120])}

    def _cls():
        lab, det = se.classify_stash_grid(path)
        return lab
    guard("stash_class", _cls)
    def _inv():
        v = se.inventory_title_visible(path)
        # v3881 (REG-3388) - an OCR that did not read is UNKNOWN, never an agreement with a PC whose OCR did
        return {"unknown": (getattr(se, "_INV_TITLE_LAST", {}) or {}).get("why") or "not read"} if v is None else bool(v)
    guard("inv_title", _inv)

    def _aspect():
        w, h = size_of(path)
        band = se.crops_for_aspect("runes", w / float(h))
        d = se.last_crop_decision() or {}
        return {"branch": d.get("branch"), "band": [round(v, 3) for v in band] if band else None}
    guard("aspect_branch", _aspect)

    def _chron():
        d = ct.detect(path)
        return {"is": bool(d.get("is_chronicle")), "tab": d.get("tab")}
    guard("chronicle", _chron)
    for surf in ("stash", "runes"):
        def _prep(surf=surf):
            p, why = sf.prepare(path, surf, work_dir=work)
            if not p or p == path:
                return {"prepared": False, "why": (why or "")[:80]}
            return {"prepared": True, "size": size_of(p), "sharp": sharpness(p)}
        guard("prep_" + surf, _prep)
    return out


def sample(reel, per_reel):
    fs = sorted(glob.glob(os.path.join(reel, "f_*.jpg")))
    if len(fs) <= per_reel:
        return fs
    step = len(fs) / float(per_reel)
    return [fs[int(i * step)] for i in range(per_reel)]


def bench(corpus=CORPUS, per_reel=8, say=print):
    """-> report dict. Refuses (raises) with no corpus - an empty bench is UNKNOWN, never a pass."""
    reels = sorted(glob.glob(os.path.join(corpus, "*", "reel_s_*")))
    if not reels:
        raise SystemExit("no corpus at %s - the bench has nothing to read (UNKNOWN, not a pass)" % corpus)
    # test_production_scratch_dirs_only_get_fewer (v3881 pre-flight): the scratch copies of every variant are removed when
    # the bench ends, however it ends - only the report leaves this function
    work = tempfile.mkdtemp(prefix="tvd_parity_")
    try:
        rep = {"machine": platform.node(), "os": platform.system(), "python": platform.python_version(),
               "pillow": getattr(__import__("PIL"), "__version__", "?"), "corpus": corpus, "at": int(time.time()),
               "frames": [], "tooltips": []}
        import tooltip_crop as tc
        for reel in reels:
            src = os.path.basename(os.path.dirname(reel))
            frames = sample(reel, per_reel)
            say("  %s/%s: %d frame(s)" % (src, os.path.basename(reel), len(frames)))
            # every variant lives in a scratch copy of ITS reel's folder, beside the same index.json: capture_stamp.
            # beside_frame reads the stamp from the reel a frame sits in, and a variant read stamp-less takes a different
            # path through prep_stash_grid than its native frame did (the first run measured exactly that artefact)
            rdir = os.path.join(work, src, os.path.basename(reel))
            if not os.path.isdir(rdir):
                os.makedirs(rdir)
                ix = os.path.join(reel, "index.json")
                if os.path.isfile(ix):
                    with io.open(ix, "rb") as a_, io.open(os.path.join(rdir, "index.json"), "wb") as b_:
                        b_.write(a_.read())
            for f in frames:
                base = os.path.join(rdir, os.path.basename(f)[:-4])
                paths = {"native": f}
                paths["win800"] = win800(f, base + "_w800.jpg")
                cap = caption_rows(f)
                if not cap:                     # a frame with no caption: what windowed capture would have handed over
                    paths["titlebar"] = titlebar(f, base + "_tb.jpg")
                    paths["titlebar800"] = win800(paths["titlebar"], base + "_tb800.jpg")
                else:                           # a frame that already carries one: the caption cut off
                    paths["untitled"] = untitled(f, base + "_untitled.jpg")
                row = {"set": src, "reel": os.path.basename(reel), "frame": os.path.basename(f), "size": size_of(f),
                       "captionRows": caption_rows(f), "variants": {}}
                for k, p in paths.items():
                    row["variants"][k] = {"size": size_of(p), "sharp": sharpness(p), "eyes": run_eyes(p, work)}
                rep["frames"].append(row)
            for a, b in zip(frames, frames[1:]):
                try:
                    r = tc.changed_rect(a, b)
                except Exception as e:
                    r = {"unknown": str(e)[:80]}
                w, h = size_of(a) or (1, 1)
                if isinstance(r, (list, tuple)) and len(r) == 4:
                    r = [round(r[0] / float(w), 3), round(r[1] / float(h), 3), round(r[2] / float(w), 3),
                         round(r[3] / float(h), 3)]
                rep["tooltips"].append({"reel": os.path.basename(reel), "a": os.path.basename(a), "b": os.path.basename(b),
                                        "rect": r})
        rep["parity"] = parity(rep)
        rep["paritySets"] = dict((s_, parity(rep, s_)) for s_ in sorted(set(r["set"] for r in rep["frames"])))
        return rep
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _same(a, b):
    if isinstance(a, dict) and "unknown" in a or isinstance(b, dict) and "unknown" in b:
        return None
    if isinstance(a, dict) and isinstance(b, dict) and "prepared" in a:
        return a.get("prepared") == b.get("prepared")
    return a == b


def parity(rep, only_set=None):
    """-> {variant: {eye: {"agree": n, "differs": n, "unknown": n, "examples": [...]}}} against each frame's native"""
    out = {}
    for row in rep["frames"]:
        if only_set and row["set"] != only_set:
            continue
        nat = row["variants"]["native"]["eyes"]
        for v, d in row["variants"].items():
            if v == "native":
                continue
            for eye in EYES:
                s = _same(nat.get(eye), d["eyes"].get(eye))
                c = out.setdefault(v, {}).setdefault(eye, {"agree": 0, "differs": 0, "unknown": 0, "examples": []})
                key = "agree" if s is True else ("differs" if s is False else "unknown")
                c[key] += 1
                if s is not True and len(c["examples"]) < 4:
                    c["examples"].append({"frame": row["reel"][-12:] + "/" + row["frame"], "native": nat.get(eye),
                                          v: d["eyes"].get(eye)})
    return out


def say_parity(rep, say=print):
    say("\nmachine %s · %s · python %s · Pillow %s · %d frame(s)" % (rep["machine"], rep["os"], rep["python"],
                                                                     rep["pillow"], len(rep["frames"])))
    for s_, par in (rep.get("paritySets") or {"all": rep["parity"]}).items():
        n = sum(1 for r in rep["frames"] if r["set"] == s_)
        say(" %s (%d frame(s); agree with the native frame / asked):" % (s_, n))
        for v in [x for x in VARIANTS if x in par]:
            say("  %-12s " % v + "  ".join("%s %d/%d%s" % (eye, c["agree"], c["agree"] + c["differs"] + c["unknown"],
                                                            (" (%d UNK)" % c["unknown"]) if c["unknown"] else "")
                                           for eye, c in par[v].items()))


def compare(a, b, say=print):
    """two machines' reports over the same corpus: every NATIVE answer must match. -> number of differences"""
    ka = {(r["reel"], r["frame"]): r for r in a["frames"]}
    diff = 0
    for r in b["frames"]:
        o = ka.get((r["reel"], r["frame"]))
        if not o:
            continue
        for eye in EYES:
            x, y = o["variants"]["native"]["eyes"].get(eye), r["variants"]["native"]["eyes"].get(eye)
            if x != y:
                diff += 1
                if diff <= 12:
                    say("  DIFFERS %s/%s %s: %s=%s  %s=%s" % (r["reel"][-12:], r["frame"], eye, a["machine"], x,
                                                             b["machine"], y))
    say("%d native answer(s) differ between %s and %s" % (diff, a["machine"], b["machine"]))
    return diff


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", default=CORPUS)
    ap.add_argument("--per-reel", type=int, default=8)
    ap.add_argument("--out", default=None)
    ap.add_argument("--compare", nargs=2, default=None)
    a = ap.parse_args(argv)
    if a.compare:
        x, y = (json.load(io.open(p, encoding="utf-8")) for p in a.compare)
        return 1 if compare(x, y) else 0
    rep = bench(a.corpus, a.per_reel)
    say_parity(rep)
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=1)
        print("report: %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
