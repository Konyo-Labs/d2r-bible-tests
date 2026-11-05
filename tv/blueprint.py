#!/usr/bin/env python3
"""THE MAP OF THIS SYSTEM, GENERATED FROM THE CODE SO IT CANNOT GO STALE.

★ Konyo: "we had a previous achilles project that we worked on with obsidian and we used blueprints
and reverse blueprints and DIAGRAM examples for future sessions and future and other LLMs working
on this repo. is there a way you can check it and also integrate that system maybe not exactly just
harness and extract whats needed for our current workflow".

WHAT WAS HARVESTED FROM ~/achilles-revival, and what was deliberately left there:

  TAKEN — the blueprint is GENERATED, not written. kai_blueprint_generator.py extracts routes and
          engines from the source after every backup, so the map cannot drift from the code. A
          hand-written architecture doc is out of date the first time anyone edits anything, and
          the version that is confidently wrong is worse than none.
  TAKEN — the REVERSE-blueprint doctrine, verbatim from KAI_REVERSE_BLUEPRINT.md: "Normal blueprint
          = design first, build after. Reverse-blueprint = audit what exists, map it truthfully,
          fix what's wrong... NEVER guess. ALWAYS trace." That is the discipline this repo already
          runs on; naming it makes it inheritable.
  LEFT   — the supervisord/SSH/proxy80 topology. That is Achilles' shape, not this one. Copying a
          reference's structure instead of its METHOD is how a map starts describing the wrong
          building. [[copy-drift]]

⚠ IT REPORTS, IT DOES NOT ASSERT. Every number here is counted from the tree at the moment it runs.
Where something cannot be counted it says so rather than printing a zero, because "0 lanes" and "I
could not read the lanes" are opposite facts. [[unknown-stays-unknown]]
"""
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "BLUEPRINT.md")


def _src(name):
    try:
        with io.open(os.path.join(HERE, name), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return ""


def _code_only(s):
    s = re.sub(r'"""(.*?)"""', "", s, flags=re.S)
    s = re.sub(r"'''(.*?)'''", "", s, flags=re.S)
    return re.sub(r"#[^\n]*", "", s)


def capture_doors():
    """The three ways a recording starts, and which checks each performs at its own door."""
    src = _code_only(_src("control_app.py"))
    if not src:
        return None
    doors = {}
    for door, anchor in (("ON AIR", '"/api/on":'), ("MINI", "def mini_start("),
                         ("shadow", "def shadow_watch_tick(")):
        i = src.find(anchor)
        if i < 0:
            doors[door] = None
            continue
        j = src.find("\ndef ", i + 10)
        body = src[i:j if j > 0 else i + 6000]
        doors[door] = {
            "preflight": "capture_preflight(" in body,
            "grant": "screenRecOk" in body,
            "ledger": "_capture_door_note(" in body,
            "floor": "ON_AIR_FLOOR_GB" in body,
        }
    return doors


def lanes():
    """Background loops — what runs without him touching anything."""
    src = _src("control_app.py")
    if not src:
        return None
    # ⚠ v2403 — THIS MATCHED ON THE NAME, NOT ON THE BEHAVIOUR, AND MISSED FOUR REAL LANES.
    # The pattern was `\ndef (_?[a-z_]*loop[a-z_]*)\(` — a function only counted as a lane if it
    # was CALLED one. Measured against tv/lane_census.py: the blueprint listed 14, the census found
    # 18, and _bridge_prober, _engine_driver, _mini_watchdog and _orphan_watch appeared in neither
    # this map nor the supervisor's roster. Every one carries `while True`; none carries "loop" in
    # its name. A map built from a naming convention describes the names, not the building.
    # Ask what the function DOES. [[workflow-topology]] [[the-unjoined-end]]
    out = []
    lines = src.splitlines()
    # ⚠ `\s` INCLUDES NEWLINES. A first cut wrote `^(\s*)def` and the group swallowed the blank
    # lines above each definition, so `indent` came back as a large number, every body collapsed to
    # one line, and the map fell from 14 lanes to 1. `[ \t]*` is the indent; `\s*` is the indent
    # plus however much whitespace preceded it. [[source-reading-guard]]
    for m in re.finditer(r"^([ \t]*)def ([A-Za-z_]\w*)\(", src, re.M):
        indent, name = len(m.group(1)), m.group(2)
        start = src[:m.start()].count("\n")
        end = len(lines)
        for i in range(start + 1, len(lines)):
            raw = lines[i]
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            if (len(raw) - len(raw.lstrip())) > indent:
                continue
            if re.match(r"[ \t]*[)\]}]", raw):
                continue
            end = i
            break
        body = "\n".join(lines[start:end])
        if not (re.search(r"^\s*while\s+True\s*:", body, re.M)
                or re.search(r"^\s*while\s+not\s+[\w.]+\.is_set\(\)\s*:", body, re.M)):
            continue
        every = re.findall(r"time\.sleep\(([A-Z_0-9a-z\.]+)\)", body)
        out.append((name, ", ".join(every[:2]) or "?"))
    # A thread whose body lives in another module is still a lane. control_app.py only
    # holds the Thread() line, so a scan of its own defs never sees that loop.
    seen = {name for name, _every in out}
    for expr in re.findall(r"target=([A-Za-z_][\w.]*)", src):
        name = expr.split(".")[-1]
        if name in seen:
            continue
        hits = []
        for fn in sorted(os.listdir(HERE)):
            if not fn.endswith(".py") or fn.startswith("test_"):
                continue
            text = _src(fn)
            m = re.search(r"^def %s\(" % re.escape(name), text, re.M)
            if not m:
                continue
            rest = text[m.start():]
            nxt = re.search(r"\n(?=def |class )", rest[1:])
            body = rest[:nxt.start() + 1] if nxt else rest
            hits.append(body)
            if len(hits) > 1:
                break
        if len(hits) != 1:
            continue
        body = hits[0]
        if not (re.search(r"^\s*while\s+True\s*:", body, re.M)
                or re.search(r"^\s*while\s+not\s+[\w.]+\.is_set\(\)\s*:", body, re.M)):
            continue
        every = re.findall(r"time\.sleep\(([A-Z_0-9a-z\.]+)\)", body)
        out.append((name, ", ".join(every[:2]) or "?"))
        seen.add(name)
    return sorted(out)


def ledgers():
    """Durable state this system keeps, and whether it exists yet."""
    out = []
    for f, why in (("capture_doors.json", "per-door Wilson: reels opened vs reels that held film"),
                   ("retro_gate.json", "every retro read graded on what / where / how"),
                   ("main_character.json", "what he wears, learned from repeated sightings"),
                   ("shadow_watch.json", "when the shadow watcher last looked, and what it saw"),
                   ("shadow_seals.jsonl", "every shadow reel opened and closed, with the rule that did it (REG-1675)"),
                   (".grok_prune.jsonl", "every automatic prune of his Grok chats: what went, how big, how old, why (REG-2743)"),
                   ("vault_seen.json", "vault sightings"),
                   ("chronicle_swept.json", "which reels the chronicle lane has read"),
                   (".proof_release.json", "which commit this PC last imported GitHub's proofs for, and how it went (v3862)")):
        p = os.path.join(HERE, f)
        out.append((f, why, os.path.exists(p),
                    (os.path.getsize(p) if os.path.exists(p) else 0)))
    return out


def readers():
    """The two game readers and the surfaces they are declared to serve."""
    try:
        sys.path.insert(0, HERE)
        import surfaces as S
        rows = []
        for name, v in sorted(S.SURFACES.items()):
            e = v.get("enlarge") or ()
            rows.append((name, v.get("reader"), v.get("anchor"),
                         (e[0] if e else "-"), bool(v.get("tooltip"))))
        return rows
    except Exception:
        return None


def wilson_lanes():
    """Everywhere the same statistic is used, so nobody hand-rolls a fourth ratio."""
    out = []
    for f in sorted(os.listdir(HERE)):
        if not f.endswith(".py") or f.startswith("test_"):
            continue
        c = _code_only(_src(f))
        n = len(re.findall(r"\bwilson_lower\s*\(", c))
        if n:
            out.append((f, n))
    return out


def rulings():
    """HIS OWN WORDS, collected from the comments that already quote them. -> {file: [quote, ...]}

    ★ Konyo: "my brain is still processing everything when i start and look from bottom and up i
    keep reminding you :). but its fine its getting annoying to do lol the puzzle is fun but the
    complication is frustrating. so we need to organize and make it clearer".

    MEASURED: 752 quoted rulings across 75 files. His decision history is already IN this tree —
    every real change here carries the sentence that caused it — and it has never been collected,
    which is why he keeps having to say things twice.

    ⚠ THIS IS AN INDEX, NOT AN ARCHIVE. Dumping 752 fragments would swap one kind of overwhelm for
    another. It keeps a few per file so a session reading about a subsystem sees HIS words about
    THAT subsystem, and knows to open the file for the rest. The code stays the source; this is a
    way in.
    """
    import re as _re
    pat = _re.compile(r'(?:Konyo|his words|He ruled|his ruling)\s*[,:]?\s*["\u201c\u2018\']'
                      r'(.{25,170})', _re.I)
    out = {}
    for f in sorted(os.listdir(HERE)):
        if not (f.endswith(".py") or f.endswith(".html")) or f.startswith("test_"):
            continue
        txt = _src(f)
        if not txt:
            continue
        seen, keep = set(), []
        for m in pat.finditer(txt):
            q = " ".join(m.group(1).split()).strip(' "\u201c\u201d\'')
            q = q.split("  ")[0]
            k = q[:40].lower()
            if len(q) < 25 or k in seen:
                continue
            seen.add(k)
            keep.append(q[:150])
            if len(keep) >= 3:
                break
        if keep:
            out[f] = keep
    return out


def gate_count():
    src = _src("run_gates.py")
    return len(re.findall(r"\n    Gate\(", src)) if src else None


def _one_sentence(w):
    """The first sentence of a gate's why, trimmed for an index line. -> str"""
    w = re.sub(r"\s+", " ", str(w or "")).strip()
    if not w:
        return ""
    m = re.search(r"(?<=[.;])\s", w)
    s = w[:m.start()] if (m and m.start() > 40) else w
    s = s.rstrip(" ,;")
    return (s[:150].rstrip() + "…") if len(s) > 150 else s


def gate_index():
    """Every registered gate and what it guards. -> [(name, why), ...] | None

    ⚠⚠ v3020 — THIS SECTION WAS A COUNT AND NOTHING ELSE, AND THE COUNT COST A SESSION.
    It read "322 registered in tv/run_gates.py" and stopped. So the one document meant to show the
    system from above could say HOW MANY laws exist and not WHICH — and on 2026-09-12 that is
    exactly what happened: I searched for laws about slot identity, tooltips and holdings,
    concluded none existed, and was corrected by Konyo — "im pretty sure we already defined them
    too so dont duplicate". There were 32, across six files, written to his own 2026-08-29 spec.
    A `grep BLUEPRINT.md tooltip` would have found them in one step; instead it took six searches
    and nearly produced a duplicate of work that already existed.

    A number is not knowledge. Every gate already carries a `why` — measured, 322 of 322 — so the
    material was always there and simply never rendered. [[the-unjoined-end]]
    [[zero-needs-a-denominator]] [[feedback-read-carved-skills-before-briefing]]

    ⚠ PARSED, NEVER GREPPED. A gate's `why` is usually several adjacent string literals, which a
    regex would cut at the first quote; ast joins them the way Python does. Parsing also keeps
    this module import-free, exactly as `gate_count()` already is — importing run_gates here would
    drag the whole suite into a doc generator. [[source-reading-guard]]
    """
    src = _src("run_gates.py")
    if not src:
        return None
    import ast as _ast
    try:
        tree = _ast.parse(src)
    except Exception:
        return None
    out = []
    for node in _ast.walk(tree):
        if not isinstance(node, _ast.Call):
            continue
        if getattr(node.func, "id", "") != "Gate":
            continue
        name = None
        if node.args and isinstance(node.args[0], _ast.Constant):
            name = node.args[0].value
        why = ""
        for kw in (node.keywords or []):
            if kw.arg == "why" and isinstance(kw.value, _ast.Constant):
                why = kw.value.value
        if name:
            out.append((str(name), str(why or "")))
    return sorted(out, key=lambda r: r[0])


def river():
    """The stations a reel passes through, and where his reels actually sit. -> dict|None

    ⚠⚠ ADDED v2794 BECAUSE THE MAP DID NOT KNOW THE RIVER EXISTED. Measured 2026-09-08 against the
    BLUEPRINT.md then on disk: `station` 0 mentions, `INTAKE` 0, `TOMBSTONE` 0, `printer` 0. The
    river and the printer were both built AFTER the map was last generated, and nothing regenerates
    it — so the one surface meant to show the wiring from above stopped at the day it was written.

    Konyo: *"shouldnt this be a connected and communicating system thats easily seen wired from a
    macro view"*. It should, and it was the map that was missing, not the wiring.

    ⚠ COUNTED FROM THE TREE, NEVER ASSERTED. reel_router owns the stations; this quotes them. If
    the router will not answer, this says so rather than printing an empty river — "0 reels at
    INTAKE" and "I could not ask" are opposite facts. [[unknown-stays-unknown]]
    """
    try:
        import reel_router as _rr
    except Exception as e:
        return {"why": "reel_router is not importable (%s)" % type(e).__name__}
    stations = list(getattr(_rr, "STATIONS", ()) or ())
    out = {"stations": stations, "why": None, "at": {}, "owes": {}, "walked": None}
    try:
        d = _rr.route()
    except Exception as e:
        out["why"] = "the router raised %s, so where his reels SIT is UNKNOWN" % type(e).__name__
        return out
    if not isinstance(d, dict) or not d.get("ok"):
        out["why"] = (d or {}).get("why") or "the router did not answer"
        return out
    rows = [r for r in (d.get("reels") or []) if isinstance(r, dict)]
    out["walked"] = len(rows)
    for r in rows:
        st = r.get("station") or "?"
        out["at"][st] = out["at"].get(st, 0) + 1
        if r.get("owes"):
            out["owes"][st] = out["owes"].get(st, 0) + 1
    try:
        import river_lanes as _rl
        lr = _rl.lanes()
        if lr.get("ok"):
            out["lanes"] = [(l["name"], l.get("count", 0)) for l in (lr.get("lanes") or [])]
            out["reconciles"] = lr.get("reconciles")
    except Exception:
        pass
    return out


def printer_stream():
    """THE 3D/4D PRINTER — one door, one stream, and what it may act on. -> dict|None

    ⚠ The printer QUOTES seven modules and re-derives nothing; this quotes the printer and
    re-derives nothing either. Two maps of one truth is how a badge and a diagram come to disagree.
    [[copy-drift]]
    """
    try:
        import printer as _p
    except Exception as e:
        return {"why": "printer is not importable (%s)" % type(e).__name__}
    try:
        st = _p.stream()
    except Exception as e:
        return {"why": "printer.stream() raised %s" % type(e).__name__}
    if not isinstance(st, dict):
        return {"why": "printer.stream() did not return a report"}
    return {"why": None, "walked": st.get("walked"), "state": st.get("state"),
            "stations": list(st.get("stations") or []),
            "counts": dict(st.get("counts") or {}),
            "tombstoned": st.get("tombstoned"),
            "owners": list((st.get("owners") or {}).keys())
                      if isinstance(st.get("owners"), dict) else list(st.get("owners") or [])}


def stripped_sets():
    """The GROSS reel vs the STRIPPED set — how many frames actually carry a panel. -> dict|None

    His words, 2026-09-08: *"the reels and sessions should have like a gross full lengthed all
    screenshots before the filtering of them ... and then the stripped version of it, with the
    garbage stripped out"*.

    ⚠⚠ IT ALREADY EXISTS AND HAD NO READER. retro_triage records `panelFrames` per reel — the
    frames that CARRY a panel — and measured 2026-09-08 the only references to it in the whole tree
    were river.py counting HOW MANY reels have one, and a census writer. 736 pre-selected frames
    across 30 stuck reels, unread, while the reader walked 4,522 gross frames and found nothing.
    A map that cannot show that gap is a map worth fixing. [[the-unjoined-end]]
    """
    import json as _json
    p = os.path.join(HERE, "retro_triage.json")
    if not os.path.isfile(p):
        return {"why": "retro_triage.json is absent, so nothing is known about panel frames"}
    try:
        d = _json.load(io.open(p, encoding="utf-8"))
    except Exception as e:
        return {"why": "retro_triage.json is unreadable (%s)" % type(e).__name__}
    if not isinstance(d, dict):
        return {"why": "retro_triage.json is not the expected shape"}
    reels = len(d)
    withpf = {k: len(v.get("panelFrames") or {}) for k, v in d.items()
              if isinstance(v, dict) and v.get("panelFrames")}
    gross = sum(int((v or {}).get("frames") or 0) for v in d.values() if isinstance(v, dict))
    panels = sum(int((v or {}).get("panels") or 0) for v in d.values() if isinstance(v, dict))
    return {"why": None, "reels": reels, "withStripped": len(withpf),
            "strippedFrames": sum(withpf.values()), "grossFrames": gross, "panelFrames": panels}


#: ⚠⚠⚠ v2879 — THIS FILE IS TWO THINGS, AND ONLY ONE BELONGS IN GIT.
#: A MAP OF THE CODE — stations, lanes, readers, gates — stable and committable; and a
#: SNAPSHOT OF HIS DATA — how many reels sit where, how large each live ledger is right now —
#: which changes every time the vault lane reads a reel.
#:
#: `--check` stripped only the `generated` line and compared the rest verbatim, so:
#:   · ON HIS MAC it went stale within MINUTES. Measured: two renders 37 minutes apart, no code
#:     change, differed on vault_seen.json 10399 B -> 11650 B, "his 35 reel(s)" -> "29 reel(s)",
#:     STATION 10 -> 8, PRINTER 7 -> 3. Every push needed a regenerate-and-amend.
#:   · ON CI IT COULD NEVER PASS. The runner has no reels, no vault_seen.json, no footage, so a
#:     file committed from his Mac cannot equal what CI renders, whatever anyone does.
#:     test_the_blueprint_cannot_go_stale has been red on the runner for many ships because of it.
#:     A gate that cannot pass on the machine that runs it is not a gate.
#:
#: The snapshot is STILL RENDERED — he reads it, and it is the macro view he asked for. It is
#: simply fenced, and the staleness question is asked of the map alone.
#: [[the-unjoined-end]] [[label-outlived-referent]] [[zero-needs-a-denominator]]
LIVE_BEGIN = "<!-- LIVE:BEGIN — a snapshot of his data, NOT part of the staleness check -->"
LIVE_END = "<!-- LIVE:END -->"


def code_only(text):
    """The part of the blueprint that describes the CODE. -> str

    ⚠ ONE STRIPPER, used by --check and by any future reader alike. Two copies of this rule is
    how a check starts asking a different question from the one the file answers. [[copy-drift]]
    """
    out, live = [], False
    for ln in (text or "").split("\n"):
        s = ln.strip()
        if s.startswith("<!-- LIVE:BEGIN"):
            live = True
            continue
        if s.startswith("<!-- LIVE:END"):
            live = False
            continue
        if live or s.startswith("generated "):
            continue
        out.append(ln)
    return "\n".join(out)


#: v3859 (e) - one parse per file per process. engine_index() is asked 8 times by its own law and once per render; each
#: ask parsed and walked every tv/*.py again (117 s of the law's 147 s). A file is parsed again when its bytes' stat moves.
_IMPORTS_SEEN = {}


def _imports_of(path, _ast):
    """-> the top-level module names one .py file imports (parsed, never grepped); () when it will not parse"""
    try:
        st = os.stat(path)
        key = (st.st_mtime_ns, st.st_size)
    except OSError:
        return ()
    hit = _IMPORTS_SEEN.get(path)
    if hit and hit[0] == key:
        return hit[1]
    try:
        with io.open(path, encoding="utf-8") as fh:
            tree = _ast.parse(fh.read())
    except Exception:
        _IMPORTS_SEEN[path] = (key, ())
        return ()
    names = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            names.extend(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, _ast.ImportFrom) and node.module:
            names.append(node.module.split(".")[0])
    out = tuple(sorted(set(names)))
    _IMPORTS_SEEN[path] = (key, out)
    return out


def engine_index():
    """Every non-test module in tv/, what it does, and what a reader gets wrong. -> (rows, drift)

    ⚠⚠ WHY THIS EXISTS, and it is the same failure `gate_index` above was written for one rung up.
    That one fixed "322 registered" standing where the NAMES of the laws belonged. This one fixes
    the same shape for the CODE: 178 modules and 1,045 public functions, and nothing in this
    document said what any of them were. Konyo, 2026-09-13, after I asked him a question the tree
    already answered: *"so why are you not checkig blueprints before hand :)?"* and then *"make
    sure the blueprint is updated accordignly so you dont need to ask these questions in the future
    and the blueprints speaks for itself."*

    MEASURED before building it, which is the point: `footprint` — a function shipped that same day
    in slot_identity.py that REFUSES an item overhanging the grid — scored **zero hits** anywhere in
    this document. So did `occupancy`, `names_loc`, `terror zone` and five more. The index is
    accepted only when a reader can grep a CONCEPT and land on the owning module in one step; that
    is asserted by test_the_blueprint_names_the_engine.py, not hoped for.

    ⚠ DERIVED AND CURATED ARE DIFFERENT, AND THE SPLIT IS THE WHOLE DESIGN.
      · DERIVED here, every render: which modules exist on disk, and which are imported by another
        module. Those cannot go stale because nothing stores them.
      · CURATED in `tv/engine_index.json`: purpose, territory, gotcha, entry points. A sentence
        about what a module MEANS cannot be re-derived from its AST, so it is written down.
    A curated line CAN go stale, so the drift between the two is reported rather than hidden: a
    module on disk with no entry is UNINDEXED, an entry whose file is gone is STALE. Both are
    printed. A map that quietly omits a module is the failure this whole section exists about.

    ⚠ `noPyImporter` says EXACTLY what it measures — no other module in tv/ imports it — and not
    "dead". Two earlier scans of mine disagreed 12-vs-15 on a "deadEnd" flag, and the cause was one
    of them counting a module's name inside a `why=` PROSE STRING in run_gates.py as a real
    reference. A CLI tool, a hook and a routine are all invoked without an import, so an
    unimported module is a question, never a verdict. [[label-outlived-referent]]
    """
    import ast as _ast
    import json as _json          # per-callsite, this module's own convention
    try:
        with io.open(os.path.join(HERE, "engine_index.json"), encoding="utf-8") as fh:
            curated = _json.load(fh)
    except Exception:
        return None, None
    on_disk = sorted(f for f in os.listdir(HERE)
                     if f.endswith(".py") and not f.startswith("test_"))
    # DERIVED: who imports whom, parsed — never grepped, because a name in a comment or a
    # docstring is not an import and reading it as one is how the 12-vs-15 disagreement happened.
    stems = {f[:-3] for f in on_disk}
    imported = set()
    for f in sorted(os.listdir(HERE)):
        if not f.endswith(".py"):
            continue
        for b in _imports_of(os.path.join(HERE, f), _ast):
            if b in stems and b != f[:-3]:
                imported.add(b)
    rows = []
    for f in on_disk:
        c = curated.get(f)
        if not c:
            continue
        rows.append({"module": f, "territory": c.get("territory") or "unknown",
                     "purpose": c.get("purpose") or "", "gotcha": c.get("gotcha") or "",
                     "entryPoints": c.get("entryPoints") or [],
                     "noPyImporter": f[:-3] not in imported})
    rows.sort(key=lambda d: (d["territory"], d["module"]))
    drift = {"unindexed": sorted(set(on_disk) - set(curated)),
             "stale": sorted(set(curated) - set(on_disk))}
    return rows, drift


def render():
    L = []
    A = L.append
    A("# TV DIABLO — BLUEPRINT")
    A("")
    A("GENERATED by `tv/blueprint.py` from the code in this tree. Do not hand-edit: regenerate it.")
    A("A hand-written map is out of date the first time anyone edits anything, and the version that")
    A("is confidently wrong is worse than no map at all.")
    A("")
    A("    generated %s" % time.strftime("%Y-%m-%d %H:%M"))
    A("")
    A("## THE REVERSE-BLUEPRINT RULE (inherited from ~/achilles-revival)")
    A("")
    A("> Normal blueprint = design first, build after.")
    A("> Reverse-blueprint = audit what exists, map it truthfully, fix what's wrong.")
    A("> **NEVER guess. ALWAYS trace.**")
    A("")
    A("Trace, then change. In one session this rule killed three of my own confident diagnoses:")
    A("the reel size was not the lag, the PNG encoder was not on the primary path, and the tooltip")
    A("cropper was not starved of readers. Each was plausible and each was wrong, and the")
    A("measurement is what said so.")
    A("")
    A("## THE ARCHITECTURE — why every reading is read twice")
    A("")
    A("Konyo, after a defect I reported turned out not to be one: \"this is exactly why LAWS and")
    A("engines are built and secondary accuracy verifiers need and are built — whatever is gapped")
    A("needs to be added and integrated ... we need it properly architectured\".")
    A("")
    A("THE CASE THAT PROVES IT. A register said an item sat at loc=floor. I called that a WHERE")
    A("defect and said it belonged in his stash. Rendering the frame showed RUNE GRIP / RING as a")
    A("FLOOR DROP LABEL in the Rogue Encampment — no tooltip, no stash. The reader was right and")
    A("the reviewer was wrong, and only a SECOND, DIFFERENT look settled it.")
    A("")
    A('## GAME-DATA SOURCE — the 28GB D2R CASC store (footprints, art, tables)')
    A('')
    A('The authoritative source for item inventory FOOTPRINTS (invwidth x invheight), base-item data,')
    A('unique/set tables and HD art is the LOCAL Diablo II Resurrected CASC store on his Mac — never')
    A('memory and never a guess. His rule for #8 (wrong item sizes): "from DATA, never memory".')
    A('')
    A('- CASC store (28GB, TVFS), via the CrossOver bottle (exact path in private memory d2r-casc-toolchain-rebuild):')
    A('    ~/CXPBottles/Battle.net Desktop App/drive_c/Program Files (x86)/Diablo II Resurrected')
    A('- Extractor (in-repo): tv/casc_extract.c ; build in tv/extract_ui_icons.py _need_toolchain(). The /tmp')
    A('  CascLib toolchain does NOT survive — rebuild per that memory (CascLib + g++, needs -DCMAKE_POLICY_VERSION_MINIMUM=3.5).')
    A('- Access files BY PATH with a data: prefix (TVFS, no listfile):')
    A('    data:data/global/excel/armor.txt | weapons.txt | misc.txt | itemtypes.txt | uniqueitems.txt | setitems.txt')
    A('    data:data/local/lng/strings/item-names.json   (enUS display names)')
    A('- Footprints: armor/weapons/misc.txt columns code, invwidth, invheight; uniques/sets map index -> code -> base dims.')
    A('- Extracted dims are cached in-repo at tv/footprints.json so a build need not re-extract every time.')
    A('')
    A("So nothing here trusts a single reading. Four independent kinds of check, and each answers a")
    A("question the others cannot:")
    A("")
    A("    LAW          needs no evidence at all. The Horadric Cube is furniture whether or not")
    A("                 anything has ever seen it. tv/inventory_law.py")
    A("    EVIDENCE     needs repetition, and refuses to conclude from thin data. Wilson, not a raw")
    A("                 ratio: 3-for-3 scores 0.438, not 1.00. tv/confidence.py, six lanes")
    A("    CONTRADICTION  two engines that must agree, asserted continuously. When they part, THAT")
    A("                 is the finding — never averaged. tv/corroborate.py")
    A("    A SECOND READ  the same frame read a second way, graded on WHAT it named, WHERE it")
    A("                 placed it and HOW it read it. tv/retro_gate.py")
    A("")
    A("And one rule underneath all four: an UNMEASURED thing stays unmeasured. `None` is not `0`.")
    A("\"nobody looked\" and \"we looked and found nothing\" are opposite facts, and every ledger")
    A("here keeps them apart.")
    A("")
    A("## CAPTURE — three doors into ONE recording")
    A("")
    A("A MINI *is* the live session wearing a focus and a deadline; all three doors spawn through")
    A("the same `start_agent()`. They differ only in what they check at their own door.")
    A("")
    d = capture_doors()
    if d is None:
        A("    (control_app.py could not be read — the doors are UNKNOWN, not absent)")
    else:
        A("    door      preflight  grant  door-ledger  floor")
        for k, v in d.items():
            if v is None:
                A("    %-9s (not found in the source)" % k)
            else:
                A("    %-9s %-10s %-6s %-12s %s"
                  % (k, v["preflight"], v["grant"], v["ledger"], v["floor"]))
    A("")
    A("## LANES — what runs without him pressing anything")
    A("")
    ln = lanes()
    if ln is None:
        A("    (UNKNOWN — control_app.py could not be read)")
    else:
        for name, every in ln:
            A("    %-26s every %s" % (name, every))
    A("")
    A("## READERS AND SURFACES")
    A("")
    A("Two readers, two coordinate laws, and they are NOT interchangeable: the difference is")
    A("geometry, not preference.")
    A("")
    r = readers()
    if r is None:
        A("    (UNKNOWN — surfaces.py could not be imported)")
    else:
        A("    surface            reader              anchor   enlarge            tooltip")
        for name, rd, anc, enl, tip in r:
            A("    %-18s %-19s %-8s %-18s %s" % (name, rd, anc, enl, tip))
    A("")
    A("## LEDGERS — the durable memory")
    A("")
    A(LIVE_BEGIN)
    for f, why, exists, size in ledgers():
        A("    %-24s %-6s %8s  %s"
          % (f, ("live" if exists else "empty"), (("%d B" % size) if exists else "-"), why))
    A(LIVE_END)
    A("")
    A("## WILSON — one statistic, every lane that scores itself")
    A("")
    for f, n in wilson_lanes():
        A("    %-24s x%d" % (f, n))
    A("")
    A("## HIS RULINGS, BY SUBSYSTEM")
    A("")
    A("Collected from the comments that already quote him — every real change in this tree carries")
    A("the sentence that caused it. This is an INDEX: a few per file, so you know which file holds")
    A("his words on a subject. The code stays the source.")
    A("")
    rl = rulings()
    A("    %d file(s) carry his words" % len(rl))
    A("")
    for f in sorted(rl):
        A("    %s" % f)
        for q in rl[f]:
            A('        "%s"' % q)
    A("")
    # ── ⚠⚠ v2794 — THE MAP DID NOT KNOW THE RIVER OR THE PRINTER EXISTED ────────────────────
    # Measured 2026-09-08 against the BLUEPRINT.md then on disk: `station` 0 mentions, `INTAKE` 0,
    # `TOMBSTONE` 0, `printer` 0, `panelFrames` 0 — and the file had not been regenerated since
    # Sep 2. Both subsystems were built after that date. So the one surface meant to show the
    # wiring from above stopped at the day someone last ran the generator by hand.
    # Konyo: *"shouldnt this be a connected and communicating system thats easily seen wired from
    # a macro view"*. [[the-unjoined-end]]
    rv = river()
    A(LIVE_BEGIN)
    A("## THE RIVER — every reel from the door to the far end")
    A("")
    if not rv or rv.get("why"):
        A("⚠ " + __import__("unknown_shelf").says_unknown((rv or {}).get("why") or "the river could not be read"))
    else:
        A("Stations, in `reel_router.STATIONS` order (the router owns them; this quotes it):")
        A("")
        A("    %s" % " → ".join(rv.get("stations") or []))
        A("")
        A("Where his %s reel(s) sit right now:" % rv.get("walked"))
        A("")
        A("| station | reels | of those, owing work |")
        A("|---|---|---|")
        for st in (rv.get("stations") or []):
            n = (rv.get("at") or {}).get(st, 0)
            o = (rv.get("owes") or {}).get(st, 0)
            if n or o:
                A("| %s | %d | %s |" % (st, n, o or "—"))
        if rv.get("lanes"):
            A("")
            A("Grouped into the four lanes `river_lanes` publishes: %s%s"
              % (" · ".join("%s %d" % (n, c) for n, c in rv["lanes"]),
                 "" if rv.get("reconciles") else "  ⚠ THE LANES AND THE SHELF DISAGREE"))
    A("")
    pr = printer_stream()
    A("## THE PRINTER — one door, one stream, out the other end")
    A("")
    if not pr or pr.get("why"):
        A("⚠ " + __import__("unknown_shelf").says_unknown((pr or {}).get("why") or "the printer could not be read"))
    else:
        A("`tv/printer.py` follows every reel through the stations and QUOTES each owner; it")
        A("re-derives nothing, and it **prints nothing and deletes nothing** — it is a report.")
        A("")
        A("    walked %s reel(s) · state %s" % (pr.get("walked"), pr.get("state")))
        if pr.get("counts"):
            A("")
            for k, v in sorted((pr.get("counts") or {}).items()):
                A("    %-22s %s" % (k, v))
    A("")
    ss = stripped_sets()
    A("## GROSS vs STRIPPED — how much of the footage actually carries a panel")
    A("")
    if not ss or ss.get("why"):
        A("⚠ " + __import__("unknown_shelf").says_unknown((ss or {}).get("why") or "the triage store could not be read"))
    else:
        A("`retro_triage` records, per reel, which frames CARRY a panel (`panelFrames`). That is the")
        A("stripped set; the reel folder is the gross one.")
        A("")
        A("    reels surveyed          %s" % ss.get("reels"))
        A("    with a stripped set     %s" % ss.get("withStripped"))
        A("    frames in those sets    %s" % ss.get("strippedFrames"))
        A("    gross frames surveyed   %s" % ss.get("grossFrames"))
        A("")
        A("⚠ Measured 2026-09-08: the ONLY readers of `panelFrames` were `river.py` counting how")
        A("many reels have one, and a census writer. The stripped sets are recorded and unread.")
    A("")
    A(LIVE_END)
    A("")
    A("## GATES")
    A("")
    g = gate_count()
    idx = gate_index()
    if idx is None:
        A("    %s registered in tv/run_gates.py" % (g if g is not None else "UNKNOWN"))
        A("")
        A("    ⚠ THE INDEX COULD NOT BE PARSED, so this section is a count and nothing more —")
        A("    which is the state that let 32 existing laws go unfound on 2026-09-12. Fix the")
        A("    parse rather than trusting the number.")
    else:
        A("    %d registered in tv/run_gates.py — every one named below with what it guards," % len(idx))
        A("    so that \"does a law already exist for this?\" is answered by reading this file.")
        # ⚠ TWO READERS, ONE FACT. gate_count() regex-counts `Gate(` and gate_index() parses the
        # calls; they measure the same thing two ways, so a disagreement means a Gate is written
        # in a shape one of them cannot see. Printing both is how that stays visible instead of
        # one silently becoming the truth. [[unknown-stays-unknown]]
        if g is not None and g != len(idx):
            A("")
            A("    ⚠ THE TWO READERS DISAGREE: the regex count says %d and the parsed index says" % g)
            A("    %d. A Gate( is written in a shape one of them cannot see." % len(idx))
        A("")
        for _n, _w in idx:
            A("- **%s** — %s" % (_n, _one_sentence(_w) or "(no why declared)"))
    A("")
    A("## THE ENGINE — every module, what it does, and what a reader gets wrong")
    A("")
    _rows, _drift = engine_index()
    if _rows is None:
        A("    tv/engine_index.json could not be read, so this section is UNKNOWN — not empty.")
    else:
        A("Grep a CONCEPT here and land on the module that owns it. That is the whole job, and it is")
        A("asserted by a gate rather than hoped for: `footprint`, `occupancy`, `names_loc`, `terror")
        A("zone`, `slot identity` and `lattice` all scored ZERO hits in this document the day before")
        A("this section existed, while every one of them was a shipped, tested behaviour.")
        A("")
        A("DERIVED every render: which modules exist, and which are imported by another module.")
        A("CURATED in `tv/engine_index.json`: purpose, territory, gotcha, entry points — a sentence")
        A("about what a module MEANS cannot be re-derived from its AST. The drift between the two is")
        A("printed below rather than hidden, because a map that quietly drops a module is the exact")
        A("failure this section was written about.")
        A("")
        A("    %d modules · %d unindexed · %d stale entr%s"
          % (len(_rows), len(_drift["unindexed"]), len(_drift["stale"]),
             "y" if len(_drift["stale"]) == 1 else "ies"))
        if _drift["unindexed"]:
            A("")
            A("    ⚠ UNINDEXED — on disk with no entry, so this map does NOT describe them:")
            for _m in _drift["unindexed"]:
                A("        %s" % _m)
        if _drift["stale"]:
            A("")
            A("    ⚠ STALE — an entry whose file is gone:")
            for _m in _drift["stale"]:
                A("        %s" % _m)
        A("")
        A("`no importer` means no OTHER MODULE IN tv/ IMPORTS IT — measured by parsing, never by")
        A("grepping a name that may be sitting inside a comment. It is not `dead`: a CLI tool, a")
        A("hook and a routine are all reached without an import, so it is a question, not a verdict.")
        _terr = None
        for _r in _rows:
            if _r["territory"] != _terr:
                _terr = _r["territory"]
                _n = sum(1 for _x in _rows if _x["territory"] == _terr)
                A("")
                A("### %s (%d)" % (_terr, _n))
                A("")
            A("- **%s** — %s%s" % (_r["module"], _r["purpose"],
                                   "  ·  *no importer*" if _r["noPyImporter"] else ""))
            if _r["entryPoints"]:
                A("      ↪ %s" % " · ".join(_r["entryPoints"]))
            if _r["gotcha"]:
                A("      ⚠ %s" % _r["gotcha"])
    A("")
    # ⚠ 2026-09-26 (#27) - THIS FILE IS PUBLISHED. A module docstring or a LIVE status line can carry a home path
    # (/Users/<him>/..., an error naming a job dir); the map says ~/ instead. The same on every machine, so --check
    # agrees between his Mac and CI.
    return re.sub(r"/(?:Users|home)/[^/\s\'\"`]+/", "~/", "\n".join(L) + "\n")


def main(argv=None):
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    txt = render()
    argv = argv or []
    if "--print" in argv:
        print(txt)
        return 0
    if "--check" in argv:
        # ⚠⚠ v2794 — THE GATE REFUSES, IT DOES NOT REGENERATE. The pre-push hook grades the
        # WORKING TREE, so a hook that rewrote BLUEPRINT.md mid-push would dirty the tree it is
        # grading AND leave the stale file in the commit actually being pushed. Refuse, let a human
        # run the generator, push again — the same shape the second-eye gate uses.
        # [[d2r-push-grades-the-working-tree]]
        #
        # ⚠ THE TIMESTAMP LINE IS EXCLUDED, AND WITHOUT THAT THIS GATE IS FURNITURE ON DAY ONE.
        # render() stamps `generated YYYY-MM-DD HH:MM`, which changes every minute — a naive diff
        # would be red forever and nobody would read it. Compare the MAP, not the clock.
        try:
            have = io.open(OUT, encoding="utf-8").read()
        except Exception as e:
            print("BLUEPRINT.md could not be read (%s) — regenerate it: python3 tv/blueprint.py"
                  % type(e).__name__)
            return 1
        strip = code_only
        if strip(have) == strip(txt):
            # ⚠⚠ v3302 — CURRENT IS NOT THE SAME QUESTION AS COMPLETE, AND THE GAP SHIPPED A
            # PERMANENTLY-RED CI GATE FOR SEVEN VERSIONS.
            #
            # `--check` asked only "does BLUEPRINT.md match what render() would produce now".
            # render() faithfully WRITES THE DRIFT INTO THE DOCUMENT — "188 modules · 3 unindexed"
            # and then names them — so a tree with unindexed modules produces a document that
            # accurately records the problem, and this check confirmed the document was current
            # and exited 0. **The guard was satisfied by an honest description of the defect.**
            # That is the shape source-reading-guard exists to prevent, arriving from the other
            # side: not prose mistaken for code, but a correct report mistaken for a clean bill.
            #
            # MEASURED 2026-09-18: `rulings.py` landed in v3294 (5ac970a9) with no engine-index
            # entry. Every push since passed this step, and CI's
            # test_the_blueprint_names_the_engine — which asks `engine_index()["unindexed"] == []`
            # — has been RED on every run since that commit. Two gates, one name, and the WEAKER
            # one is the one that blocks the push. [[the-unjoined-end]] [[regression-guard]] §1
            #
            # Asking the same question locally is the whole fix.
            try:
                _rows, _drift = engine_index()
                _un = list(_drift.get("unindexed") or [])
            except Exception as _e:
                # ⚠ UNKNOWN IS NOT CLEAN. If the index cannot be read, say so and refuse, rather
                # than letting an unreadable map pass as a complete one.
                print("BLUEPRINT.md is current, but the engine index could NOT BE READ (%s) — "
                      "refusing, because whether every module is named is now UNKNOWN."
                      % type(_e).__name__)
                return 1
            if _un:
                print("BLUEPRINT.md is current, but %d module(s) on disk have NO engine-index "
                      "entry, so the map does not describe them:" % len(_un))
                for _m in _un:
                    print("     %s" % _m)
                print("   add an entry to tv/engine_index.json (entryPoints / purpose / gotcha / "
                      "territory), then: python3 tv/blueprint.py")
                print("   ⚠ this is the same question CI's test_the_blueprint_names_the_engine "
                      "asks. It was RED there and green here for seven versions.")
                return 1
            print("BLUEPRINT.md is current, and every module on disk is named.")
            return 0
        print("BLUEPRINT.md is STALE — the map no longer matches the code.")
        print("   regenerate it:  python3 tv/blueprint.py")
        return 1
    with io.open(OUT, "w", encoding="utf-8") as fh:
        fh.write(txt)
    print("wrote %s (%d lines)" % (OUT, txt.count("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
