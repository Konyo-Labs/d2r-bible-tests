#!/usr/bin/env python3
"""A7 — every reel store has ONE declared owner, and everyone else is a declared reader.

His ask: *"all reels need to be processed the same way all unified logic"* — no reel gets a special
path, a bypass, or a second implementation, and any lane that differs is *"declared, in code, as a
deliberate exception with a reason"*.

⚠⚠ WHAT THIS DOES **NOT** DO, SAID FIRST BECAUSE IT IS THE THING A READER WOULD ASSUME. It does not
prove single-writer. I tried to measure that two ways before writing this and BOTH RETURNED ZERO
WRITERS for all four stores:

    a filename-adjacency grep      0 — the store name is never beside the write verb
    an AST walk resolving constants 0 — paths are bound in helpers (`TOMBSTONE_PATH = _tombstone_path()`)
                                        and threaded through arguments, which by-name resolution
                                        cannot follow

Two zeros in a row measured MY INSTRUMENTS, not the code, and a third detector would have been the
same mistake with more effort. So this takes the technique the codebase already uses and makes it
checkable instead: `reel_index.py` says "THE ONLY WRITER" in its docstring, `reel_repair.py` says
"exactly one writer of an index in the repo" — real declarations, in prose, that nothing verified.

WHAT IT DOES CHECK, and it is a ratchet rather than a proof:

  · every store names an OWNER, and that owner's source actually mentions the store — a
    declaration naming a module that has never heard of the file is worse than none
  · every OTHER module that mentions the store is listed as a declared reader WITH A REASON
  · a module that starts touching a store and is not declared FAILS, so a second implementation
    has to be argued in rather than appearing

That is evidence about COUPLING, not about writes. [[unknown-stays-unknown]] [[copy-drift]] §1

    python3 tv/store_owners.py
    python3 tv/store_owners.py --json
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

#: store -> who owns it, what it holds, and every module allowed to mention it.
#: ⚠ A reader is listed WITH ITS REASON. "It appears in the file" is not a reason; the point of the
#: list is that adding to it makes someone say out loud why another module needs this store.
STORES = {
    "retro_triage.json": {
        "owner": "retro_triage",
        "holds": "per-reel structural verdict: frames, panels, kinds",
        "readers": {
            "reel_custody":  "READS it through end_routes.sources() to name the station a reel stands at in its\n"
                             "                              custody record, and names the file in its station labels.\n"
                             "                              Read-only (REG-1544): writes, moves and deletes nothing",
            "blueprint":     "v2794 — reads `panelFrames` per reel to print the PRINTER section of\n"
                             "                              BLUEPRINT.md: how much of the film actually carried a panel.\n"
                             "                              READ-ONLY and it degrades honestly — absent, unreadable and\n"
                             "                              wrong-shape each return their own `why` rather than a zero, so\n"
                             "                              a missing store can never print as `0 panel frames`",
            "end_routes":    "reads it to DERIVE the end-route predicate from the reels that\n                              already reached it, rather than inventing one. His ruling\n                              settled the DESTINATION and named the METHOD: 'reverse\n                              engineeer it if needed the ones that are working'.\n                              READ-ONLY: it decides nothing and deletes nothing - a second\n                              prune authority over footage that has no un-delete is\n                              exactly what this file exists to refuse.",
            "lane_liveness":  "NOT a toucher — its DOCSTRING cites this store as an example of a\n                              lane that leaves a dated row, which is the argument for why a\n                              heartbeat was NOT built as a second copy of that fact. Prose,\n                              never a read. Declared so the mention is accounted for",
            "verdict_provenance": "reads ONE row to ask whether it can name what produced it.\n                              44 stores swept 2026-09-11, 16 SILENT. It writes nothing, back-fills\n                              nothing and never repairs — naming the gap is the product",
            "run_gates":      "NOT a toucher — a gate DESCRIPTION names this file while\n                              explaining what the gate is for. Prose in a `why` string",

            "write_census":      "NOT a writer of THIS file — it calls retro_triage.remember() with a "
                                 "SCRATCH root and watches which module the write is attributed to. It is "
                                 "the A7 measurement-by-observation, and the only one of the five stores "
                                 "that can be exercised at all. Declared so the mention is accounted for "
                                 "rather than reading as a second writer",
            "control_app":   "serves it to the console surfaces",
            "corroborate":   "NOT a toucher — the 'triage starved' NO_JOINT_YET sentence (2026-09-28) NAMES this\n"
                             "                              store while explaining why that row has no independent witness yet.\n"
                             "                              Prose in a string, never a read. Declared so the mention is accounted for",
            "printer_reach": "the printer-zone acceptance test reads panels to find the A4 case",
            "declared_vs_content": "A15 — asks whether a reel's route is derived from its CONTENT "
                                   "or guessed from a declared stamp, so it needs what the "
                                   "structural pass actually found",
            "one_funnel":    "A15 clause 2 — counts how many reels this store has a DATED row for. "
                             "It quotes retro_triage.STORE rather than naming the file (REG-534)",
            "write_witness": "NOT a reader — it patches open/io.open/os.replace process-wide to "
                             "ATTRIBUTE writes, so it names this path only to report who wrote it",
            "reel_router":   "A7·ROUTE — the survey's verdict IS a station on the river, so the "
                             "router reads `panels` (via worth_reading, through printer.stream) "
                             "and `ts` to say WHEN a reel was surveyed. ⚠ It reads through "
                             "retro_triage's own load(), never the file, and writes nothing",
        },
    },
    "reel_tombstones.json": {
        "owner": "reel_retention",
        "holds": "reels that were pruned, and when — the record that a reel existed",
        "readers": {
            "reel_custody":  "READS it through end_routes.sources() to name the station a reel stands at in its\n"
                             "                              custody record, and names the file in its station labels.\n"
                             "                              Read-only (REG-1544): writes, moves and deletes nothing",
            # v2844 — the render harness WRITES this, and that is deliberate rather than a second
            # authority: the TOMBSTONE lane on the river strip has nothing to draw unless closed-out
            # rows exist, so the target seeds a synthetic ledger. ⚠ IT WRITES INTO THE RENDER
            # SANDBOX (`_hist`), never tv/ — the isolation v1867 was carved for. It appeared here as
            # an undeclared toucher only once the scan stopped counting comments, which is the scan
            # working: this is a real write and it should have been argued in, not discovered.
            # REG-1470..1479 (evidence route round 5) — two READERS, both asking the owner first.
            "read_pictures": "READS it (load_tombstones) so a picture whose reel is gone says WHEN it went,\n"
                             "                              instead of reading as a broken link. Asks\n"
                             "                              reel_retention._tombstone_path(hist) for the path and joins\n"
                             "                              its own only if that import fails. Read-only; returns None\n"
                             "                              (UNKNOWN) on an unreadable file, never []",
            "vault_evidence": "READS it (_tombstone_times) to DATE a gone frame's loss, so a missing\n"
                              "                              picture says 'deleted at T' rather than 'undated'. Trusts\n"
                              "                              reel_retention._tombstone_path(root) and refuses the one\n"
                              "                              answer that would date a FIXTURE root with his real record.\n"
                              "                              Read-only; deletes and writes nothing",
            # #165 (REG-2472/2473) - a THIRD reader that asks the owner first, for one provenance question.
            "counter_ledger": "READS it (_tombstone_rows) for ONE question: is the reel a shipped Remaining page\n"
                              "                              was filmed on one THIS PC pruned? If so the page is this PC's\n"
                              "                              and may judge its board. The owner answers twice: the path\n"
                              "                              (reel_retention._tombstone_path) and the read\n"
                              "                              (reel_retention._load_state), so an unreadable file is\n"
                              "                              UNKNOWN, never 'not this PC's'. Read-only; writes nothing",
            "render_check":  "SEEDS a synthetic tombstone ledger inside the render sandbox so the\n"
                             "                              TOMBSTONE lane has rows to photograph. Writes to <hist>,\n"
                             "                              never to tv/, and reads nothing back from his real store",
            "end_routes":    "reads it to DERIVE the end-route predicate from the reels that\n                              already reached it, rather than inventing one. His ruling\n                              settled the DESTINATION and named the METHOD: 'reverse\n                              engineeer it if needed the ones that are working'.\n                              READ-ONLY: it decides nothing and deletes nothing - a second\n                              prune authority over footage that has no un-delete is\n                              exactly what this file exists to refuse.",
            "tv_diablo":     "NOT a toucher — a v2639 comment explains that the recorder's\n                              emergency reaper is deliberately NOT a second writer of this\n                              store; reel_retention._tombstone stays the one writer, and the\n                              recorder records to its own reel_reaps.jsonl instead. Prose",
            "run_gates":     "NOT a toucher — a gate DESCRIPTION names this file while saying\n                              the reaper is not a second writer of it. Prose in a `why` string",

            "lane_liveness":  "NOT a toucher — its DOCSTRING cites this store as an example of a\n                              lane that leaves a dated row, which is the argument for why a\n                              heartbeat was NOT built as a second copy of that fact. Prose,\n                              never a read. Declared so the mention is accounted for",

            "write_census":      "NOT a writer and never can be — it names this store to record that only "
                                 "an actual DELETION writes a tombstone, and the prune stays OFF by his "
                                 "standing ruling, so its exercise is declared None WITH that reason. "
                                 "Naming what cannot be measured is the whole point of the census",
            "printer":           "READS it, once per snapshot, for the seventh station. v2692 gave "
                                 "the printer a `tombstone` station so the river ends where a reel "
                                 "actually ends -- 'if it is gone, what closed it out? (and this "
                                 "one is still here)'. It resolves the path through "
                                 "reel_retention._tombstone_path() rather than joining its own, so "
                                 "reel_retention stays the one authority on WHERE the store lives "
                                 "even though the printer is now a second READER of it. A failure "
                                 "to load leaves `tombstones` None, never {} -- nobody-looked and "
                                 "measured-empty are different answers here",
            "control_app":       "renders the tombstones on the shelf",
            "second_eye_ledger": "NOT a coupling — its docstring cites this file as the example of "
                                 "an untracked store living beside the reels. Declared so the "
                                 "mention is accounted for rather than looking like a second writer",
            "dead_field":        "reads it to ask whether a field is recorded on every row and "
                                 "filled on none — it found `startedTs` dead across 410 rows. It "
                                 "asks the OWNER for the path (reel_retention._tombstone_path) "
                                 "rather than resolving one itself, which is REG-540",
            "write_witness":     "NOT a reader — it patches open/io.open/os.replace process-wide "
                                 "to ATTRIBUTE writes, so it names this path only to report who "
                                 "wrote it. It is an instrument pointed at the store, never a "
                                 "second writer of it",
        },
    },
    # #41 rank 16 (REG-1560) — the tooltip oracle lane's receipt: one verdict per oracle row, the bible.html it
    # measured, the lane's lifetime counters. Written by ONE module; the doctor row and the corroborate joint read
    # it only through that module's read_receipt(), so no other module names the file.
    ".tooltip_oracle_receipt.json": {
        "owner": "tooltip_oracle_lane",
        "holds": "per oracle row: is the shipped tooltip theirs (runeword, base, agree, why) + the bible.html "
                 "stamp it measured + node + lifetime runs",
        "readers": {},
    },
    "vault_accum.json": {
        "owner": "vault_retro",
        "holds": "what the vault sweep accumulated per reel",
        "readers": {
            "vault_forget_wilson": "v3905 (REG-3819) - NAMES this store to build its sabotage harness's box: every write\n"
                             "                              goes into a TemporaryDirectory copy (_Box), never his file - the\n"
                             "                              forget door is attacked there, and only there",
            "corroborate":   "2026-09-28 (Ledger P0) — the per-item tier joint ('a tier stands on the looks the gate\n"
                             "                              counts') opens the witness ledger (TV_VAULT_LEDGER or this file)\n"
                             "                              READ-ONLY and hands it to vault_evidence.tier_census and\n"
                             "                              vault_retro.gate, comparing the two per item. It writes nothing",
            "vault_bank":    "v3171 — the ONE reader for the stash-side bank. It reads this store and\n"
                             "                              vault_swept.json together and reports what the sweep took,\n"
                             "                              folding two different wordings of 'empty' and SAYING that it\n"
                             "                              folded them. Read-only: it reads back the output of the sweep\n"
                             "                              that wrote it, which is why the corroborator files its check as\n"
                             "                              a self-report rather than a joint",
            "vault_backup":  "NAMES this store in its copy list — it is one of the files backed up\n"
                             "                              aside so a bad write can be undone. It reads the live file to\n"
                             "                              copy it and never writes back to this path",
            "trace_spine":   "v3183 — reads it to follow ONE item across reel, ledger, routing and\n"
                             "                              endpoint, and to prove the NEGATIVE half: that a chronicle or\n"
                             "                              farming scenario deposited nothing here. Reports only; the\n"
                             "                              witnessed machinery stays the sole writer",
            "render_check":  "v2778 — NAMES this store as one of eleven it COPIES into a throwaway\n"
                             "                              sandbox before rendering, so a render never reads or writes\n"
                             "                              his live one. It reads the live file exactly once, to copy it;\n"
                             "                              every write during the render lands in the sandbox. The copy\n"
                             "                              list is NAMED, never globbed, and an oversized file is skipped\n"
                             "                              rather than aborting the rest — v2780 fixed a `break` there that\n"
                             "                              would have silently un-isolated every store after it",
            "read_names_lane":  "v2753 — REPORTS ONLY. It works out which already-read names would\n"
                                "                              auto-tally and which fall to his hand, and never\n"
                                "                              writes: banking a name RELEASES that reel's footage\n"
                                "                              for pruning (`rows-not-banked` is a retention hold),\n"
                                "                              so a reporter that could write would be a deleter.\n"
                                "                              Its own gate proves the write ban from the AST.",
            "vault_witness":    "v2759 — REPORTS ONLY. Holds the STORED owned rows beside a re-gate\n"
                                "                              of their own witnesses at today's live bars, and\n"
                                "                              publishes the DISAGREEMENT. It exists because\n"
                                "                              vault_apply's re-gate lives inside `if\n"
                                "                              caller_supplied` and the console's button posts no\n"
                                "                              body, so a stored result gated under an older bar is\n"
                                "                              applied as-is — 6 of 7 of his rows, measured.",
            "tv_diablo":     "v2639 — the disk-floor reel reaper READS the witness sessions so it\n                              can refuse to delete a reel the vault still cites as evidence.\n                              Read only, through a cached mtime check, and it writes nothing here.\n                              Its first victim would otherwise have been the reel behind\n                              'Chaotic Grand Charm'",

            "write_census":      "NOT a writer — it names this store to record that the vault lane writes "
                                 "it during a PAID sweep, and a sweep spends money and must not be started "
                                 "to satisfy a census. Exercise declared None, with that reason",
            "console_doctor":  "checks the vault stores are readable",
            "console_healer":  "repairs it when it will not parse",
            "control_app":     "serves the vault surfaces",
            "write_witness":   "NOT a reader — it patches open/io.open/os.replace process-wide to "
                               "ATTRIBUTE writes, so it names this path only to report who wrote it",
            "frame_authority": "the deletion authority reads it to protect witness frames",
            "reel_retention":  "eligibility consults what the vault took",
            "vault_doctor":    "audits the vault lane",
        },
    },
    "vault_swept.json": {
        "owner": "frame_authority",
        "holds": "the seal store — which sessions the vault sweep has sealed, and what it extracted",
        "readers": {
            "vault_forget_wilson": "v3905 (REG-3819) - NAMES this store to build its sabotage harness's box: every write\n"
                             "                              goes into a TemporaryDirectory copy (_Box), never his file - the\n"
                             "                              forget door is attacked there, and only there",
            "reel_custody":  "READS it through end_routes.sources() to name the station a reel stands at in its\n"
                             "                              custody record, and names the file in its station labels.\n"
                             "                              Read-only (REG-1544): writes, moves and deletes nothing",
            "vault_bank":    "v3171 — reads this store beside vault_accum to answer how many sweeps\n"
                             "                              actually took something (45 swept, 36 silent when measured).\n"
                             "                              Read-only, and the ONE reader of the pair",
            "vault_backup":  "NAMES this store in its copy list — backed up aside so a bad write can\n"
                             "                              be undone. Reads the live file to copy it, never writes here",
            "render_check":  "v2778 — NAMES this store as one of eleven it COPIES into a throwaway\n"
                             "                              sandbox before rendering, so a render never reads or writes\n"
                             "                              his live one. It reads the live file exactly once, to copy it;\n"
                             "                              every write during the render lands in the sandbox. The copy\n"
                             "                              list is NAMED, never globbed, and an oversized file is skipped\n"
                             "                              rather than aborting the rest — v2780 fixed a `break` there that\n"
                             "                              would have silently un-isolated every store after it",
            "end_routes":    "reads it to DERIVE the end-route predicate from the reels that\n                              already reached it, rather than inventing one. His ruling\n                              settled the DESTINATION and named the METHOD: 'reverse\n                              engineeer it if needed the ones that are working'.\n                              READ-ONLY: it decides nothing and deletes nothing - a second\n                              prune authority over footage that has no un-delete is\n                              exactly what this file exists to refuse.",
            "lane_liveness":  "NOT a toucher — its DOCSTRING cites this store as an example of a\n                              lane that leaves a dated row, which is the argument for why a\n                              heartbeat was NOT built as a second copy of that fact. Prose,\n                              never a read. Declared so the mention is accounted for",
            "verdict_provenance": "reads ONE row to ask whether it can name what produced it.\n                              44 stores swept 2026-09-11, 16 SILENT. It writes nothing, back-fills\n                              nothing and never repairs — naming the gap is the product",

            "write_census":      "NOT a writer — same as vault_accum: the vault lane writes this as a paid "
                                 "sweep completes, so the exercise is declared None rather than run. "
                                 "UNEXERCISED and NO-WRITERS are different facts",
            "console_doctor":  "checks the vault stores are readable",
            "console_healer":  "repairs it when it will not parse",
            "control_app":     "serves the seal state to the console",
            "lane_health":     "reports whether the vault lane is moving",
            "reel_retention":  "asks whether both lanes are finished with a reel",
            "run_gates":       "names it in the list of stores a gate must not clobber",
            "vault_doctor":    "audits the vault lane",
            "vault_retro":     "writes what it swept, through the owner",
            "one_funnel":      "A15 clause 2 — counts how many reels this store has a DATED row "
                               "for, which is one of only two rungs on the six-rung ladder that "
                               "leaves a waypoint at all. It quotes frame_authority.SEAL_STORE "
                               "rather than naming the file, which is REG-534",
            "write_witness":   "NOT a reader — it patches open/io.open/os.replace process-wide to "
                               "ATTRIBUTE writes, so it names this path only to report who wrote it",
        },
    },
}


def _modules():
    """-> {module_name: source}. Test files and conftest are not part of the product graph."""
    out = {}
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py") or fn.startswith("test_") or fn == "conftest.py":
            continue
        # ⚠⚠ THE REGISTRY MUST NOT COUNT ITSELF, AND IT CAUGHT ITSELF ON ITS FIRST RUN. This file
        # names every store — that IS the declaration — so it appeared as an undeclared toucher of
        # all four. Excluding it is only honest while it never actually OPENS one, which is not a
        # promise here: test_store_owners asserts this module contains no read or write of a store
        # path. An instrument that counts itself is a defect this console has produced before
        # (the deriver that counted itself as a watcher).
        if fn == "store_owners.py":
            continue
        # ⚠⚠ THE RAW SOURCE, COMMENTS AND ALL — AND I TRIED STRIPPING THEM AND MADE IT WORSE.
        # `audit()` asks `store in src`, so ANY mention of a store's filename reads as coupling.
        # On 2026-09-05 a comment I added to `run_gates.py`, naming the healer backups its
        # live-state net had been missing, made this report one undeclared toucher — and the only
        # occurrence in that file was that comment.
        #
        # The obvious fix is [[source-reading-guard]] §3.5's: grade code, not prose. I applied it,
        # and it BROKE THREE THINGS. Modules reach these stores through helpers rather than
        # literals, so the filename appears in their comments only — strip those and three honest
        # declarations turn into "stale allowances". ONE false positive became THREE.
        # ⚠ And the strip's own comment contained `open("<a store name>")` as an example, which
        # tripped the OTHER guard here — the one asserting this registry never opens what it
        # declares. The same defect, one level up, inside the fix for it.
        #
        # So the scan stays raw and the RULE is on the prose instead: **do not write a store's
        # literal filename in a comment in this tree.** Name it by role — "the healer backups",
        # "the vault accumulator" — which is more readable anyway. That is v1853's ruling applied
        # unchanged: the honest fix was to move MY comment out of someone else's window, not to
        # widen their window to accommodate me.
        try:
            out[fn[:-3]] = io.open(os.path.join(HERE, fn), encoding="utf-8").read()
        except Exception:
            pass
    return out


def _code_only(src):
    """`src` with comments AND DOCSTRINGS removed; ordinary string literals KEPT. -> str

    ⚠⚠ v3246 — A DOCSTRING IS PROSE, AND THIS FUNCTION USED TO COUNT IT AS CODE. The rule below
    about string literals is right and stays: a real toucher opens a store BY NAME —
    `os.path.join(HERE, "vault_accum.json")` — and that name is a string, so stripping all strings
    would blind the graph to every genuine coupling. But a DOCSTRING is not a reference at all,
    and this dropped only `#`-leading lines, so prose in a triple-quoted block counted as a touch.
    Measured: `live_store.py` was reported as an undeclared toucher of `vault_accum.json` on the
    strength of ONE LINE OF ITS MODULE DOCSTRING — a table of his untracked stores explaining why
    the module exists. It opens nothing; it is handed paths by its callers.

    ⚠ THIS IS NOT A SECOND IMPLEMENTATION. `frame_authority._executable_only` already answers
    exactly this question, for exactly this reason, and it is the one that carries the evidence:
    it was written after prose-named reels held 4.8 GB of his footage under a false reason. Two
    strippers with one job drift, and the weaker one is always the one still running somewhere.
    [[copy-drift]] [[source-reading-guard]] [[feedback-comments-vs-code]]

    The fallback is the OLD behaviour, deliberately: if that import ever fails, this must still
    strip comments rather than count them, because holding a false coupling is quieter than
    dropping a real one.
    """
    try:
        from frame_authority import _executable_only
        return _executable_only(src, ".py")
    except Exception:
        return "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))


def audit():
    """-> {"ok", "rows", "why"}. Undeclared couplings are the finding."""
    mods = _modules()
    if not mods:
        return {"ok": False, "rows": [],
                "why": "no module could be read at all — UNKNOWN, not a clean graph"}
    rows = []
    for store, spec in sorted(STORES.items()):
        owner = spec["owner"]
        declared = set(spec["readers"]) | {owner}
        # ⚠⚠ v2844 — CODE, NOT COMMENTS. This was a plain `store in src` over the whole file, so
        # a module that merely NAMES a store while explaining something became an undeclared
        # toucher. Measured: `reel_router` was reported as touching reel_tombstones.json on the
        # strength of one comment at line 512 describing a bug — it opens nothing. A coupling
        # graph built from prose reports couplings that do not exist, and the fix is to make it
        # read what runs. [[source-reading-guard]] [[feedback-comments-vs-code]]
        touching = {m for m, src in mods.items() if store in _code_only(src)}
        undeclared = sorted(touching - declared)
        # ⚠⚠ THE TWO QUESTIONS ARE NOT THE SAME QUESTION, AND ONE SCAN CANNOT ANSWER BOTH.
        # v2844, measured: making the scan comment-free (correctly) stopped four DECLARED readers
        # from matching — dead_field, reel_retention, one_funnel, vault_retro — and the `stale`
        # check called them dead allowances. They are not. Each resolves its path through the
        # module's path authority, so the literal filename survives only in the comment recording
        # that the hardcoded version was REMOVED (`THE FIRST CUT HARDCODED "reel_tombstones.json"`).
        # This file's own docstring already said a literal-name scan under-reports writers by
        # construction; the `stale` half had simply been passing on that prose.
        #
        # So they are asked differently, on purpose:
        #   · UNDECLARED — does EXECUTABLE code in a module nobody declared name this store? Strict
        #     and comment-free, because this is the safety-critical direction: a second writer
        #     appearing unannounced is the defect the registry exists to catch.
        #   · STALE — does the declared module still refer to this store AT ALL, prose included?
        #     Deliberately weaker. A strict answer is not available while paths are threaded
        #     through helpers, and a strict scan would report every indirection-using owner as
        #     stale — 4 of them here — which is a false alarm that would train him to ignore it.
        # [[unknown-stays-unknown]] [[source-reading-guard]]
        mentions = {m for m, src in mods.items() if store in src}
        stale = sorted(declared - mentions)
        # ⚠ A DECLARED READER THAT NO LONGER TOUCHES THE STORE IS ALSO A FINDING — the list stops
        # describing the code, and a stale allowance is how the next undeclared module slips in
        # under a name nobody re-checked.
        rows.append({
            "store": store, "owner": owner, "holds": spec["holds"],
            # ⚠ v3246 — THE WEAK QUESTION, ANSWERED WITH THE STRICT SET. This read `touching`,
            # which is the comment-free scan built for the OTHER question. The paragraph
            # directly above says these two are asked differently on purpose, and this line
            # sat one statement before it doing the opposite. It only stayed quiet because
            # `_code_only` still counted docstrings: `vault_retro` names vault_accum.json
            # nowhere but its docstring, so the moment the strict scan became correctly
            # strict, the owner of a store it genuinely owns was reported as never having
            # heard of it. "Does this module refer to the store at all" is the prose-
            # inclusive question, and `mentions` is the set that answers it.
            "ownerMentionsIt": owner in mentions,
            "declared": len(declared), "touching": len(touching),
            "undeclared": undeclared, "stale": stale,
        })
    bad = [r for r in rows if r["undeclared"] or r["stale"] or not r["ownerMentionsIt"]]
    return {
        "ok": not bad, "rows": rows,
        "why": ("%d store(s) declared, every module that mentions them accounted for. ⚠ This is "
                "COUPLING, not proof of a single writer — two static attempts to measure writers "
                "returned zero and were measuring the instrument." % len(rows)) if not bad else
               ("%d store(s) disagree with their declaration" % len(bad)),
    }


def main(argv):
    r = audit()
    if "--json" in argv:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    print("\nSTORE OWNERS — one owner per reel store, everyone else declared\n")
    for row in r["rows"]:
        flag = "  " if not (row["undeclared"] or row["stale"]) else "⚠ "
        print("%s%-22s owner %-16s %d declared / %d touching"
              % (flag, row["store"], row["owner"], row["declared"], row["touching"]))
        if not row["ownerMentionsIt"]:
            print("     ⚠ the declared owner never mentions this store")
        for u in row["undeclared"]:
            print("     ⚠ UNDECLARED: %s touches this store and nothing says why" % u)
        for s in row["stale"]:
            print("     ⚠ STALE: %s is declared but no longer touches it" % s)
    print("\n  %s" % r["why"])
    return 0 if r["ok"] else 0        # reports; never fails a build


if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    raise SystemExit(main(sys.argv[1:]))
