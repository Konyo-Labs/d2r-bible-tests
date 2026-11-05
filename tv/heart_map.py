# -*- coding: utf-8 -*-
"""HEART.md — WHICH SURFACES OF THE CONSOLE ARE WATCHED, DERIVED FROM THE CONSOLE ITSELF.

⚠⚠ WHY THIS EXISTS, 2026-09-16. His standing order is JOIN -> GATE -> HEART -> BANK. It was
carved as prose in `join_gate_heart` on 2026-09-06 and I read it and then skipped HEART on FIVE
CONSECUTIVE SHIPS — v3201 through v3205 — every one carrying a law, a red-proof, a registered gate
and a BUGS entry, and not one carrying a heart row. Measured when he asked: 402 gates registered,
61 doctor rows, and `stationbar 0 · sh-filterfold 0 · shr-stkey 0 · sweep-box 0 · fleet-row 0`.

His answer: *"we need it all updated and blueprints updated and heart updated all derived from the
console"*, and then, when I said the heart was the one with no enforcement: *"fix this so it is
like blueprints too and has enforcemnt"*.

THE BLUEPRINT'S SHAPE, MIRRORED EXACTLY, because it is the one artefact here that has never
drifted:
  1. it is DERIVED — nobody writes it by hand, so it cannot disagree with the code
  2. `bump_version.py` REGENERATES it on every bump
  3. the pre-push REFUSES when it is stale, and does NOT regenerate it itself — a hook that
     rewrote the tree would dirty the very bytes it is grading
     [[d2r-push-grades-the-working-tree]]

⚠ AND THE TIMESTAMP IS EXCLUDED FROM THE COMPARISON. blueprint.py records that without it the
gate "is furniture on day one": a clock that changes every minute makes the diff red forever and
nobody reads it. Compare the MAP, not the clock.

WHAT IT MEASURES: the console's rendered surfaces (the ids and classes its own JS paints), against
the names that appear in anything that WATCHES — console_doctor, health_engine, corroborate,
heart2. A surface nobody names is UNWATCHED, and saying so is the whole point.
⚠ UNWATCHED IS NOT A FAILURE. Most surfaces do not need a watcher and never will. What this
refuses is a surface being unwatched SILENTLY — the count is a ratchet, and it may not get worse
without a human saying why. [[zero-needs-a-denominator]] [[unknown-stays-unknown]]

⚠⚠ REG-1555 (2026-09-30) — "APPEARS IN" MEANT THE WATCHER'S WHOLE TEXT, AND THE MAP READ PROSE AS
WATCHING. `seen` was `i in blob` over the four files as written, so a COMMENT naming a surface made
it WATCHED. Measured on the tree that blessed a console floor of 17: nine of the seventeen (`bug`,
`heart-chip`, `sh-stationbar`, `sigil`, `stage-hold`, `th-shelfov`, `theatre`, `vault-body`,
`win-ctl`) stood only in comments and docstrings — `heart-chip` in the very comment recording that
it had been REMOVED from WATCHES "because it could never match" — and `th-shelf` only as the prefix
of `th-shelf-x`. Thirteen of seventeen. The organ built to say a surface is unwatched said WATCHED
for a name a comment had just declared unwatchable. Now a name counts only where a watcher's CODE
names it WHOLE: comments go by the tokenizer, docstrings by the parser, and `th-shelf-x` does not
vouch for `th-shelf`. [[source-reading-guard]] [[regression-guard]]
"""
import ast
import io
import json
import os
import re
import sys
import time
import tokenize

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "HEART.md")
FLOOR = os.path.join(HERE, "heart_floor.json")

WATCHERS = ("console_doctor.py", "health_engine.py", "corroborate.py", "heart2.py")

#: THE PAGES THE HEART MAPS — #41 rank 25 (2026-09-29). This read control_ui.html ONLY, so bible.html's builder,
#: Characters and mule surfaces (measured: 513 ids on the board, 81 of them cb-* / chars-* / mp-* / vault-*) could
#: never be counted as watched OR unwatched — the map said nothing about them and read exactly like a map that had
#: checked them. The board is a second page: its own table, its own watched list, its own ratchet under "board" in
#: heart_floor.json. The console's figures and floor are unchanged. Paths: the console page lives in tv/, the board
#: at the repo root (_read resolves both). [[zero-needs-a-denominator]]
PAGES = (("control_ui.html", "the console"), ("bible.html", "the board"))
BOARD = "bible.html"

# A surface is something the console PAINTS and he can therefore see go wrong. Ids are the honest
# unit: a class may be shared by forty nodes, an id names one thing.
_ID_RX = re.compile(r"""id=\\?["']([a-zA-Z][\w-]{2,})\\?["']""")
#: REG-1555 — a name in a watcher's code, the same shape as an id: it stands WHOLE or it is not there.
_NAME_RX = re.compile(r"[A-Za-z][\w-]{2,}")


def _code_only(text):
    """-> a watcher's Python text with every comment and docstring blanked (the line count kept), or None when it
    does not parse as Python. A watcher that does not parse watches nothing, and watched() names it MISSING rather
    than reading its text as prose. Comments are found by the tokenizer, docstrings by the parser (the first
    statement of a module, class or function when it is a string). REG-1555. [[source-reading-guard]]
    """
    try:
        tree = ast.parse(text)
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except Exception:
        return None
    doc_lines = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and body
                and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant)
                and isinstance(body[0].value.value, str)):
            doc_lines.add(body[0].value.lineno)
    spans = []
    for t in toks:
        if t.type == tokenize.COMMENT:
            spans.append((t.start, t.end))
        elif t.type == tokenize.STRING and t.start[0] in doc_lines:
            spans.append((t.start, t.end))
    lines = text.splitlines(keepends=True)
    for (r1, c1), (r2, c2) in spans:
        for r in range(r1, r2 + 1):
            line = lines[r - 1]
            a = c1 if r == r1 else 0
            b = c2 if r == r2 else len(line.rstrip("\r\n"))
            lines[r - 1] = line[:a] + " " * max(0, b - a) + line[b:]
    return "".join(lines)


def _seen(ids, blob):
    """-> the ids of a page that the watchers' CODE names whole, sorted. ONE rule for every page (REG-1555): a name
    inside a longer one (`th-shelf` inside `th-shelf-x`) is not that name, and `blob` is code only (see watched())."""
    names = set(_NAME_RX.findall(blob))
    return sorted(i for i in ids if i in names)


def _read(name):
    """-> the file's text, or None when it could not be read. NEVER "".

    ⚠⚠ IT RETURNED "" AND THAT MADE THE HEART MAP ITSELF THE LIE. `surfaces()` runs the id regex
    over this string, so an unreadable `control_ui.html` yields an EMPTY SET — and `render()`
    would then write, into the file the pre-push gate compares against the tree:

        | surfaces the console paints | **0** |
        | of those, watched           | **0** |
        | coverage                    | **0.0%** |

    A heart map stating that the console paints nothing, banked into the repo, from a failed open.
    The organ that exists to notice blindness would have gone blind in exactly the shape it was
    built to catch. [[zero-needs-a-denominator]] [[unknown-stays-unknown]]
    """
    try:
        # the board page lives at the repo root; every other file this map reads lives in tv/
        with io.open(os.path.join(REPO if name == BOARD else HERE, name), encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return None


def surfaces(name="control_ui.html"):
    """-> sorted ids the page paints, or None when that page could not be read. The console by default."""
    ui = _read(name)
    if ui is None:
        return None
    return sorted({m.group(1) for m in _ID_RX.finditer(ui)})


def watched():
    """-> (blob of every watcher's CODE — comments and docstrings blanked, REG-1555 — , [watchers that could not be read])

    A watcher that cannot be read makes every surface it covers look UNWATCHED — which would
    report as a coverage collapse and, worse, as a real one. It is named instead of skipped.
    A watcher that does not PARSE is named the same way: its text is prose to this map, not code.
    """
    parts, missing = [], []
    for w in WATCHERS:
        t = _read(w)
        c = None if t is None else _code_only(t)
        if c is None:
            missing.append(w)
            continue
        parts.append(c)
    return "\n".join(parts), missing


def measure():
    """-> (ids, seen, missing).

    `ids` is None ONLY when control_ui.html itself could not be read. `seen` is None whenever the
    map cannot be trusted — that is the unmeasurable signal, and it covers the watcher case where
    `ids` is a real list. `missing` names every watcher that could not be read.
    ⚠ v3237 — this used to say "`ids` is None when the map cannot be measured at all", which is
    what let a caller use `ids is None` as the "the page was unreadable" fact. The sentence
    outlived the shape it described. [[label-outlived-referent]]"""
    ids = surfaces()
    blob, missing = watched()
    # ⚠⚠ v3237 — `ids is None` MUST MEAN THE PAGE, AND IT DID NOT. This collapsed BOTH failures
    # into `ids = None`, and v3235 then handed `ids is None` to `_why_unmeasurable` as the
    # "control_ui.html could not be read" fact. So a perfectly readable page plus ONE unreadable
    # watcher printed "control_ui.html could not be read AND these watchers could not be read:
    # ..." — naming a healthy file first and sending the reader straight to it.
    #
    # A cross-family review of v3235 caught it AND named why the new law missed it: the test
    # calls the helper with a literal True and never goes through measure(), so the proxy itself
    # was never exercised. A fact passed as a PROXY is only ever as true as the proxy.
    # [[label-outlived-referent]] [[the-unjoined-end]]
    if ids is None:
        return None, None, missing          # the page itself could not be read
    if missing:
        return ids, None, missing           # the page is FINE; only watchers are missing
    seen = _seen(ids, blob)
    return ids, seen, missing


def measure_pages():
    """Every page in PAGES, by the same rule measure() applies to the console. -> ({name: {"ids", "seen"}}, missing)

    `ids` is None only when THAT page could not be read. `seen` is None whenever the map cannot be trusted for it —
    the page unreadable, or any watcher missing (a missing watcher blinds every page at once). A page that reads and
    has nothing watched is `seen: []`, which is a measurement. #41 rank 25. [[unknown-stays-unknown]]
    """
    blob, missing = watched()
    out = {}
    for name, _label in PAGES:
        ids = surfaces(name)
        if ids is None or missing:
            out[name] = {"ids": ids, "seen": None}
        else:
            out[name] = {"ids": ids, "seen": _seen(ids, blob)}
    return out, missing


def _why_unmeasurable(missing, page_unreadable, unreadable_pages=()):
    """Say every reason the map could not be built, not the first one. -> str

    ⚠ THE CALLER TELLS IT; IT DOES NOT LOOK AGAIN. The first cut called `surfaces()` here, which
    re-opens control_ui.html — so between `measure()` deciding the page was unreadable and this
    sentence being built, the file could become readable again and the reason would VANISH from
    a refusal that still fires. Not hypothetical in this repo: `bump_version.py` writes the
    surfaces with an ATOMIC REPLACE, and an atomic replace is exactly a window in which a path
    is briefly missing and then fine. The refusal would read "no reason recorded".
    Found by a cross-family review of v3233, the version that added this helper.
    [[stale-reading]] [[unknown-stays-unknown]]
    """
    bits = []
    if page_unreadable:
        bits.append("control_ui.html could not be read")
    for name in unreadable_pages:
        if name != "control_ui.html" or not page_unreadable:
            bits.append("%s could not be read" % name)
    if missing:
        bits.append("these watchers could not be read: %s" % ", ".join(missing))
    return " AND ".join(bits) or "no reason recorded"


def _unreadable_pages(pages):
    return [name for name, _label in PAGES if pages.get(name, {}).get("ids") is None]


def render():
    pages, missing = measure_pages()
    ids, seen = pages["control_ui.html"]["ids"], pages["control_ui.html"]["seen"]
    gone = _unreadable_pages(pages)
    # ⚠ REFUSE, DO NOT RENDER A ZERO. Writing the map is what banks it: the pre-push gate compares
    # HEART.md against the tree, so a map built from a failed read becomes the committed truth.
    # v3237 — refuse on EITHER failure, now that `ids` is no longer the single signal.
    # #41 rank 25 — and on the BOARD page too: a map with the console's table and no board table
    # would read as a board with nothing to say, which is the silence this section exists to end.
    if ids is None or missing or gone:
        raise RuntimeError(
            # ⚠ the counterfactual must match the FAILURE. A watcher-only failure would not
            # have written "0 surfaces" — ids is the real list; what it would have written is a
            # COVERAGE figure computed without a watcher, which reads as a real collapse.
            "the heart map could not be measured: %s. Refusing to write it: an unreadable file "
            "is UNKNOWN, not empty, and a coverage figure missing a watcher is a collapse that "
            "did not happen."
            # v3233 — NAME BOTH. `missing` being non-empty used to hide that the console page
            # was ALSO unreadable, so a double failure reported as a watcher problem and sent
            # the reader to the wrong file. [[zero-needs-a-denominator]]
            % _why_unmeasurable(missing, ids is None, gone))
    pct = (100.0 * len(seen) / len(ids)) if ids else 0.0
    lines = [
        "# THE HEART — what watches the console",
        "",
        "Derived by `tv/heart_map.py`. Do not edit by hand: it is regenerated on every bump and",
        "the pre-push refuses when it is stale, exactly like BLUEPRINT.md.",
        "",
        "A surface here is an `id` the console paints — the honest unit, because a class may be",
        "shared by forty nodes while an id names one thing. WATCHED means the CODE of",
        "`console_doctor.py`, `health_engine.py`, `corroborate.py` or `heart2.py` names it whole:",
        "a comment or docstring naming it does not count, and a longer id (`th-shelf-x`) does not",
        "vouch for its prefix (`th-shelf`). Before 2026-09-30 both did, and 13 of the console's 17",
        "\"watched\" surfaces were named nowhere but in prose (REG-1555).",
        "",
        "⚠ UNWATCHED IS NOT A DEFECT. Most surfaces neither need nor will ever have a watcher.",
        "What is refused is a surface going unwatched SILENTLY — the count below is a ratchet and",
        "may not fall without a human saying why in `heart_floor.json`.",
        "",
        "| | |",
        "|---|---|",
        "| surfaces the console paints | **%d** |" % len(ids),
        "| of those, watched | **%d** |" % len(seen),
        "| coverage | **%.1f%%** |" % pct,
        "",
        "## Watched",
        "",
    ]
    lines += ["- `%s`" % s for s in seen] or ["_none_"]
    # #41 rank 25 — THE BOARD, by the same rule, with its own ratchet ("board" in heart_floor.json).
    bids, bseen = pages[BOARD]["ids"], pages[BOARD]["seen"]
    bpct = (100.0 * len(bseen) / len(bids)) if bids else 0.0
    lines += [
        "",
        "## The board — `bible.html`",
        "",
        "The page the console runs in its window: the builder, the 👤 Characters tab, the mule",
        "window and the Vault paint their surfaces here. Same unit (an `id`), same watchers, its own",
        "ratchet under `board` in `heart_floor.json`. Before 2026-09-29 this page was not mapped at",
        "all, so its surfaces could be neither watched nor unwatched — only unsaid.",
        "",
        "| | |",
        "|---|---|",
        "| surfaces the board paints | **%d** |" % len(bids),
        "| of those, watched | **%d** |" % len(bseen),
        "| coverage | **%.1f%%** |" % bpct,
        "",
        "### Watched on the board",
        "",
    ]
    lines += ["- `%s`" % s for s in bseen] or ["_none_"]
    return "\n".join(lines) + "\n"


def _floor():
    try:
        with io.open(FLOOR, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


# REG-3216 - THE RATCHET NEVER TIGHTENED. Measured 2026-11-05 (GrokBot, #230): HEART.md said the console watches 8 of 406
# painted surfaces and the board 4 of 602, while heart_floor.json still held 7 of 366 (its names omit `bug`) and 1 of 513
# (`vault-moved-note` alone). The floor rose only on a hand --bless, so every surface watched since then could stop being
# watched and --check would still pass: the console could fall back to 7 and the board to 1, silently. Now a
# regeneration RAISES a page's floor to the map whenever the map still watches every name the floor holds; --check
# refuses a floor that lags the map, and a floor name the map no longer watches, even when the count held. Only a
# human LOWERS a floor, and --bless asks why. [[regression-guard]] [[zero-needs-a-denominator]]
def _entry(fl, name):
    """A page's floor entry: the console's is the top level, the board's sits under "board". -> dict | None"""
    if not isinstance(fl, dict):
        return None
    if name == BOARD:
        e = fl.get("board")
        return e if isinstance(e, dict) else None
    return fl


def floor_vs_map(fl, pages):
    """Each page's floor against the map. -> [{page, label, was, now, lost, gained, lags}] for every page with a floor

    lost   floor names the map no longer watches (a fall, even when the count held)
    gained names the map watches that the floor does not hold
    lags   the map holds every floor name and watches more: a regeneration raises this floor"""
    out = []
    for name, label in PAGES:
        e, pg = _entry(fl, name), pages.get(name) or {}
        seen = pg.get("seen")
        if e is None or seen is None:
            continue
        have = set(e.get("names") or [])
        was = int(e.get("watched") or 0)
        lost = sorted(have - set(seen))
        gained = sorted(set(seen) - have)
        out.append({"page": name, "label": label, "was": was, "now": len(seen), "lost": lost, "gained": gained,
                    "lags": (not lost) and len(seen) >= was and (len(seen) > was or bool(gained))})
    return out


def tighten(fl, pages):
    """The floor a regeneration writes. -> (new floor dict, or None when nothing rose; [what it said])

    A page's floor rises to the map only when the map still watches every name the floor holds. It never falls here:
    a lost name leaves that page's floor where it was, for --check to refuse and a human to lower with a reason."""
    if not isinstance(fl, dict):
        return None, []
    new = json.loads(json.dumps(fl))
    said, rose = [], False
    for row in floor_vs_map(fl, pages):
        if row["lost"]:
            said.append("%s floor NOT raised: %s no longer watched - only a human lowers a floor, saying why"
                        % (row["label"], ", ".join(row["lost"][:8])))
            continue
        if row["now"] < row["was"] or not (row["now"] > row["was"] or row["gained"]):
            continue                    # nothing new is watched: there is nothing to raise
        pg = pages[row["page"]]
        e = _entry(new, row["page"])
        e["watched"], e["surfaces"], e["names"] = len(pg["seen"]), len(pg["ids"]), list(pg["seen"])
        rose = True
        said.append("%s floor raised %d -> %d (now also: %s)"
                    % (row["label"], row["was"], row["now"], ", ".join(row["gained"][:8]) or "-"))
    return (new if rose else None), said


def _write_whole(path, text):
    """Write `text` to `path` whole or not at all. -> None

    `io.open(OUT, "w").write(render())` TRUNCATED HEART.md before render() ran, so a render that raised left the map
    empty in the tree the pre-push grades - the open-for-write-truncates-first scar. The text is built first, written
    beside the file and swapped in."""
    tmp = "%s.tmp-%d" % (path, os.getpid())
    try:
        with io.open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _arg(argv, flag):
    """The value after `flag` (or `flag=value`) in argv, "" when absent or when it is another flag. -> str"""
    for i, a in enumerate(argv):
        if a == flag:
            v = argv[i + 1] if i + 1 < len(argv) else ""
            return "" if v.startswith("--") else v.strip()
        if a.startswith(flag + "="):
            return a[len(flag) + 1:].strip()
    return ""


def main(argv=None):
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    argv = argv or []
    pages, missing = measure_pages()
    ids, seen = pages["control_ui.html"]["ids"], pages["control_ui.html"]["seen"]
    gone_pages = _unreadable_pages(pages)
    # v3231 — an unmeasurable map is a REFUSAL at every door, not a quiet zero in one of them.
    # #41 rank 25 — the board page is a door too.
    if ids is None or missing or gone_pages:
        print("🔴 the heart map could not be measured: %s"
              % _why_unmeasurable(missing, ids is None, gone_pages))
        print("   UNKNOWN is not a measurement. Refusing rather than banking a coverage figure "
              "nobody could take.")
        return 1
    bids, bseen = pages[BOARD]["ids"], pages[BOARD]["seen"]
    if "--print" in argv:
        print(render())
        return 0
    if "--check" in argv:
        # ⚠ REFUSE, NEVER REGENERATE — the pre-push grades the working tree.
        try:
            with io.open(OUT, encoding="utf-8") as _fh:
                have = _fh.read()
        except Exception:
            print("HEART.md is missing — run: python3 tv/heart_map.py")
            return 1
        if have.strip() != render().strip():
            print("HEART.md does not match the code — run: python3 tv/heart_map.py")
            return 1
        fl = _floor()
        if fl is None:
            print("heart_floor.json has never been written, so whether coverage SHRANK is "
                  "UNKNOWN — run: python3 tv/heart_map.py --bless")
            return 1
        was = int(fl.get("watched") or 0)
        gone = sorted(set(fl.get("names") or []) - set(seen))
        if len(seen) < was:
            print("HEART coverage FELL %d -> %d. A surface that was watched no longer is: %s"
                  % (was, len(seen), ", ".join(gone[:8]) or "(names not recorded)"))
            print("If that is deliberate, lower it by hand in tv/heart_floor.json and say why.")
            return 1
        # REG-3216 - A NAME IS THE FLOOR, NOT ONLY A COUNT: one surface gained can hide one surface lost
        if gone:
            print("HEART coverage lost a surface while its count held (%d): no longer watched: %s"
                  % (len(seen), ", ".join(gone[:8])))
            print("If that is deliberate, lower it with: python3 tv/heart_map.py --bless --why \"<why>\"")
            return 1
        # #41 rank 25 — the board's own ratchet. A floor with no "board" entry has never measured the
        # board, so whether ITS coverage shrank is UNKNOWN — a refusal, never a pass by omission.
        bfl = fl.get("board")
        if not isinstance(bfl, dict):
            print("heart_floor.json carries no board floor, so whether the board's coverage SHRANK is "
                  "UNKNOWN — run: python3 tv/heart_map.py --bless")
            return 1
        bwas = int(bfl.get("watched") or 0)
        bgone = sorted(set(bfl.get("names") or []) - set(bseen))
        if len(bseen) < bwas:
            print("HEART coverage on the board FELL %d -> %d. A board surface that was watched no longer is: %s"
                  % (bwas, len(bseen), ", ".join(bgone[:8]) or "(names not recorded)"))
            print("If that is deliberate, lower it by hand under \"board\" in tv/heart_floor.json and say why.")
            return 1
        if bgone:
            print("HEART coverage on the board lost a surface while its count held (%d): no longer watched: %s"
                  % (len(bseen), ", ".join(bgone[:8])))
            print("If that is deliberate, lower it with: python3 tv/heart_map.py --bless --why \"<why>\"")
            return 1
        # REG-3216 - A FLOOR THAT LAGS THE MAP IS NAMED AND REFUSED: below the map, a watched surface can stop being
        # watched and the ratchet says nothing. The fix is the regeneration the bump already runs.
        lag = [r for r in floor_vs_map(fl, pages) if r["lags"]]
        if lag:
            for r in lag:
                print("HEART floor LAGS the map on %s: the map watches %d, the floor holds %d - not in the floor: %s"
                      % (r["label"], r["now"], r["was"], ", ".join(r["gained"][:8]) or "-"))
            print("Below the map, those surfaces could stop being watched and nothing would say so. Raise it: "
                  "python3 tv/heart_map.py (then commit tv/heart_floor.json).")
            return 1
        print("heart: %d of %d painted surfaces watched (floor %d) · board: %d of %d watched (floor %d)"
              % (len(seen), len(ids), was, len(bseen), len(bids), bwas))
        return 0
    text = render()          # REG-3216 - built BEFORE anything is opened for writing
    if "--bless" in argv:
        # REG-3216 - A BLESS THAT LOWERS SAYS WHY. --bless wrote whatever the map measured, so a surface that stopped
        # being watched could be blessed away with no reason anywhere. Lowering is a human's call; this asks for it.
        old = _floor()
        dropped = dict((r["page"], r["lost"]) for r in floor_vs_map(old, pages)
                       if r["lost"] or r["now"] < r["was"])
        why = _arg(argv, "--why")
        if dropped and not why:
            print("REFUSED: this bless would LOWER the heart floor (%s). Say why: "
                  "python3 tv/heart_map.py --bless --why \"<why>\" - nothing written."
                  % "; ".join("%s: %s" % (k, ", ".join(v) or "count fell") for k, v in sorted(dropped.items())))
            return 1
        record = {"_why": "HEART coverage ratchet — it may only RISE. A fall means a surface this "
                          "console used to watch is no longer watched, which in a green run reads "
                          "exactly like clean. A surface is watched only where a watcher's CODE names "
                          "it whole (REG-1555): the floor of 17 blessed on 2026-09-29 counted 13 names "
                          "that stood only in comments, docstrings or inside a longer id, and was "
                          "lowered to the measured count on 2026-09-30 for that reason.",
                  "watched": len(seen), "surfaces": len(ids), "names": seen,
                  # #41 rank 25 — the board's ratchet, same rule, its own numbers
                  "board": {"watched": len(bseen), "surfaces": len(bids), "names": bseen}}
        if dropped:
            record["_lowered"] = {"why": why[:400], "dropped": dropped,
                                  "at": time.strftime("%Y-%m-%d")}
        _write_whole(FLOOR, json.dumps(record, indent=2, sort_keys=True) + "\n")
        print("  blessed heart floor at %d of %d (board %d of %d)" % (len(seen), len(ids), len(bseen), len(bids)))
    else:
        # REG-3216 - THE RATCHET TIGHTENS ON ITS OWN: every name the floor holds is still watched, so the floor rises
        # to the map. A lost name leaves the floor where it was, for --check to refuse.
        new, said = tighten(_floor(), pages)
        if new is not None:
            _write_whole(FLOOR, json.dumps(new, indent=2, sort_keys=True) + "\n")
        for line in said:
            print("  " + line)
    _write_whole(OUT, text)
    print("  wrote %s — %d of %d painted surfaces watched · board %d of %d"
          % (os.path.relpath(OUT, REPO), len(seen), len(ids), len(bseen), len(bids)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
