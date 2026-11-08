# -*- coding: utf-8 -*-
"""v2731 — A BACKUP THAT RUNS EVERY TEN MINUTES AND HAS NEVER COPIED TWO OF HIS SIX LEDGERS.

MEASURED across all 60 of his real backup files, 2026-09-06 — every single one:
    foundLog   419  ✅        rwMade      —  ❌ ABSENT   (his 99 runewords)
    owned      169  ✅        gameFound   —  ❌ ABSENT   (his 29 in-game records)
    setPieces  123  ✅        route/profile — ❌ NOT RECORDED

His instruction was explicit: *"i want it no wiped · i want that saved · and being able to be
restored · indefinitely"*. Two of the six stores had no automatic copy at all.

⚠⚠ AND IT BLINDED A WATCHER, WHICH IS THE WORSE HALF. `tv/ledger_highwater.py` ratchets
KEYS = (foundLog, setPieces, rwMade, owned) against each key's historic maximum — and since no
snapshot has ever carried `rwMade`, that column can only ever read UNKNOWN. An UNKNOWN column looks
exactly like a column with nothing wrong. A loop that runs every ten minutes and writes a plausible
14 KB file is the most convincing kind of gap there is. [[unknown-stays-unknown]] [[the-unjoined-end]]

=== WHY THE TWO STORES NEEDED DIFFERENT FIXES, AND WHY THE FIRST ATTEMPT WAS WRONG ===
They looked identical and were not:
  · `gameFound` was ALREADY being returned in full (`var gameFound=...raw('d2r_gameFound')`,
    emitted top-level). Pure plumbing: nobody folded it into the backed-up ledger.
  · `rwMade` existed only as a COUNT — `Object.keys(m).length` — so it could be counted and never
    copied. It needed fetching, not plumbing.
⚠ MY FIRST PATCH ASSUMED THEY WERE THE SAME and added fresh reads for both plus a second
`gameFound:` key into the same JS object literal, where the later key silently wins. It was
reverted before it ran. The lesson is the ordinary one: read the literal, then patch it.

=== WHAT THIS PINS ===
The load-bearing law is `test_gameFound_is_NOT_graded_for_truncation`. The truncation check compares
a copy against a count the board reports INDEPENDENTLY. `counts.runewordsMade` is such a count, so
rwMade is graded. There is no independent count for gameFound, so the only comparison available is
the copy against its own length — which cannot fail, and a check that cannot fail is worse than no
check because it reads as coverage. It is skipped, deliberately, and this file says so.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from console_safe import enable
    enable()
except Exception:
    pass

SRC = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()


RED_PROOF = [
    {"why": "v3888 (REG-3482) - a store the board never wrote is sent as null again (Dean's gameFound: MISSING in every backup)",
     "file": "tv/control_app.py",
     "find": "                   \"if(v==null||v==='')return {};var p=JSON.parse(v);\"\n",
     "replace": "                   \"if(v==null||v==='')return null;var p=JSON.parse(v);\"\n",
     "matches": 1, "needs": "node"},
    {"why": "v3888 (REG-3482) - gameFound is read through raw() again (a never-written store and a torn one look alike)",
     "file": "tv/control_app.py",
     "find": "          \"try{gameFound=store('d2r_gameFound');}catch(_g){}\"",
     "replace": "          \"try{var _gp=raw('d2r_gameFound');if(_gp&&typeof _gp==='object'&&!Array.isArray(_gp))gameFound=_gp;}catch(_g){}\"",
     "matches": 1},
    {"why": "v3883 - his un-ticks ride into the backup's ledger block again, a key the restore has no answer for",
     "file": "control_app.py",
     "find": '    led.pop("grailUnfound", None)\n', "replace": "", "matches": 1},
    {"why": "v3882 - an empty gameFound the board sent is left out of the backup again (Dean's doctor: MISSING gameFound)",
     "file": "control_app.py",
     "find": '    if isinstance(got.get("gameFound"), dict):\n        led["gameFound"] = got["gameFound"]\n',
     "replace": '    if isinstance(got.get("gameFound"), dict) and got["gameFound"]:\n        led["gameFound"] = got["gameFound"]\n',
     "matches": 1},
    {"why": "v3882 - an empty rwMade the board sent is left out of the backup again (the ALTs' doctor: MISSING rwMade)",
     "file": "control_app.py",
     "find": '    if isinstance(got.get("rwMadeFull"), dict):\n        led["rwMade"] = got["rwMadeFull"]\n',
     "replace": '    if isinstance(got.get("rwMadeFull"), dict) and got["rwMadeFull"]:\n        led["rwMade"] = got["rwMadeFull"]\n',
     "matches": 1},
    {
        "why": 'the law requires this text in control_app.py, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'control_app.py',
        "find": 'led["gameFound"] = got["gameFound"]',
        "replace": '_HEART2_TAMPERED_',
        "matches": 1,
    },
]

def _between(src, start, end, whence=0):
    """Anchored at BOTH ends — never a fixed window. [[source-reading-guard]]"""
    i = src.find(start, whence)
    if i < 0:
        return None
    j = src.find(end, i + len(start))
    return None if j < 0 else src[i:j + len(end)]


class TheBoardSendsANeverWrittenStoreAsEmpty(unittest.TestCase):
    """v3888 (REG-3482) - the hook on Dean's PC, 11-08: "the newest backup carries 4 of 5 ledgers - MISSING gameFound". MEASURED
    there: none of his 50 backups (09-05 to 11-08) ever named gameFound - his board never wrote d2r_gameFound, and the board read
    (raw) returned the same null for a key never written as for one that will not parse, so the board sent None and v3882's
    "an empty store is a measured zero" (the class below, fed a {} the board never sends) never reached him. Runs the shipped
    store() in node over a stand-in LSR."""

    def _run(self, cases, lsr=True):
        import shutil, subprocess, json as _json
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required to run the board-side read - UNMEASURED here, not a pass")
        import control_app as ca
        js = ("var OUT = {}; var CASES = %s; var window = {};\n" % _json.dumps(cases)
              + ca._BOARD_STORE_JS + "\n"
              + ("window.LSR = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(CASES, k) ? CASES[k] : null; } };\n" if lsr else "")
              + "Object.keys(CASES).concat(['never_written']).forEach(function(k){ OUT[k] = store(k); });\n"
              "process.stdout.write(JSON.stringify(OUT));")
        r = subprocess.run([node, "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        return _json.loads(r.stdout)

    def test_a_store_never_written_is_a_measured_empty_one(self):
        """* THE POINT - Dean's d2r_gameFound: never written, so {} - and an unreadable one stays UNKNOWN (null)"""
        o = self._run({"full": '{"Shako": "05/27/2026"}', "blank": "", "torn": '{"Shako": ', "list": "[1, 2]"})
        self.assertEqual(o["never_written"], {}, "a store the board never wrote is sent as null again (UNKNOWN, not zero)")
        self.assertEqual(o["blank"], {})
        self.assertEqual(o["full"], {"Shako": "05/27/2026"})
        self.assertIsNone(o["torn"], "a store that will not parse was sent as empty - a guess, not a measurement")
        self.assertIsNone(o["list"], "a store of the wrong shape was sent as empty")

    def test_a_board_that_is_not_loaded_sends_nothing(self):
        o = self._run({"x": "{}"}, lsr=False)
        self.assertEqual((o["x"], o["never_written"]), (None, None), "an unloaded board's stores read as measured zeros")

    def test_both_stores_are_read_through_it(self):
        self.assertIn("try{gameFound=store('d2r_gameFound');}catch(_g){}", SRC)
        self.assertIn("try{rwFull=store('d2r_rwMade');}catch(_r){}", SRC)
        self.assertIn("+ _BOARD_STORE_JS +", SRC, "the board read never defines store()")


class AnEmptyStoreIsWrittenAsMeasured(unittest.TestCase):
    """v3882 (the doctor on Dean's PC and both ALTs, 11-08: "the newest backup carries 3 of 5 ledgers - MISSING rwMade,
    gameFound"). Both folds asked for a NON-EMPTY store, so a board with none wrote no key: "he has none" read as "nobody
    copied it". Drives the real _ledger_snapshot_once over a stand-in board and a temp backup dir - never his."""

    def _snap(self, game_found, rw_full, rw_count):
        import json, shutil, tempfile
        from unittest import mock
        import fixture_tmp as _fx
        _fx.contain()
        import control_app as ca
        d = tempfile.mkdtemp(prefix="ledger-backup-")
        self.addCleanup(shutil.rmtree, d, True)
        board = {"ok": True, "route": {"key": "fixture"},
                 "counts": {"foundLog": 2, "owned": 1, "setPieces": 1, "runewordsMade": rw_count},
                 "sample": dict({"foundLog": ["A", "B"], "owned": ["C"], "setPieces": ["D"]},
                                **(getattr(self, "_sample_extra", None) or {})),
                 "gameFound": game_found, "rwMadeFull": rw_full, "fullStores": {}}
        with mock.patch.object(ca, "board_ownership", lambda **k: dict(board)), \
                mock.patch.object(ca, "_LEDGER_BACKUP_DIR", d), \
                mock.patch.dict(ca._LEDGER_BACKUP_STATE, {"counts": None, "handMade": None}):
            out, why = ca._ledger_snapshot_once(force=True)
        self.assertTrue(out, "PREMISE: the stand-in board was not snapshotted: %r" % why)
        with io.open(out, encoding="utf-8") as fh:
            return json.load(fh)["ledger"]

    def test_an_empty_store_the_board_sent_is_written_empty(self):
        """* THE POINT - Dean: no in-game records yet, so d2r_gameFound is {} - a measured zero, written as one"""
        led = self._snap({}, {}, 0)
        self.assertEqual(led.get("gameFound"), {}, "an empty gameFound the board sent left no key: %r" % sorted(led))
        self.assertEqual(led.get("rwMade"), {}, "an empty rwMade the board sent left no key")

    def test_a_store_the_board_did_not_send_stays_out(self):
        """UNKNOWN stays unknown: a board that sent no gameFound (None) writes no key, never an invented {}"""
        led = self._snap(None, None, None)
        self.assertNotIn("gameFound", led)
        self.assertNotIn("rwMade", led)

    def test_every_key_of_the_ledger_is_one_the_restore_knows(self):
        """v3883 - his un-ticks rode the board's SAMPLE (REG-1906) into every backup's ledger from ~10-15, a sixth key
        ledger_restore has no answer for: the corroborator's backup-restore-vocabulary pair disagreed for weeks. They are
        backed up in allStores (d2r_grailUnfound, the complete export) - beside the ledger, never inside it"""
        import ledger_restore as LR
        self._sample_extra = {"grailUnfound": ["Arkaine's Valor"]}
        led = self._snap({}, {}, 0)
        self.assertNotIn("grailUnfound", led, "his un-ticks were copied into the ledger block again")
        known = set(LR.RESTORABLE) | set(LR.BACKED_UP_ONLY)
        self.assertEqual(sorted(k for k in led if k not in known), [], "a backup ledger key the restore has no answer for")

    def test_a_full_store_is_written_whole(self):
        led = self._snap({"Shako": "05/27/2026"}, {"Spirit": 1}, 1)
        self.assertEqual(led.get("gameFound"), {"Shako": "05/27/2026"})
        self.assertEqual(led.get("rwMade"), {"Spirit": 1})


class LedgerBackupCoversEveryStore(unittest.TestCase):

    def test_the_guard_can_find_the_snapshot_at_all(self):
        """⚠ A law that finds nothing to grade passes having examined ZERO candidates."""
        self.assertIn("_ledger_snapshot_once", SRC,
                      "the backup writer is gone or renamed — fix this guard before trusting it")
        self.assertIn("board_ownership", SRC, "the snapshot no longer asks the board")

    # ── the two stores are actually fetched ───────────────────────────────────────────────────
    def test_rwMade_CONTENTS_are_fetched_not_only_counted(self):
        """`rwMade` was a COUNT for its whole life — countable, never copyable."""
        self.assertRegex(   # v3888 (REG-3482) - through store(), which tells a never-written store from an unreadable one
            SRC, r"rwFull=store\('d2r_rwMade'\)",
            "nothing fetches the CONTENTS of d2r_rwMade. The pre-existing `var rwMade=` is "
            "Object.keys(m).length — a count. His 99 runewords could be counted and never copied, "
            "which is exactly how they stayed out of 60 consecutive backups."
        )
        # ⚠⚠ v2735 — THIS ASSERTION USED TO PIN `rwMadeFull:(dump?rwFull:null)`, AND PINNING IT IS
        # WHAT LET THE DEFECT LIVE. There is no JS variable named `dump`; dump_stores is
        # interpolated as a bare true/false LITERAL, so the name resolved to nothing and the whole
        # board read threw `Can't find variable: dump`. His automatic backup wrote ZERO files for a
        # day with this law green — because the law pinned the BYTES rather than the property.
        # The bytes are now pinned loosely and the real property is checked by
        # `test_board_read_js_has_no_free_variables`, which parses the emitted JS.
        # [[regression-guard]] — pin the LAW, not the number.
        self.assertRegex(SRC, r"rwMadeFull\s*:\s*rwFull",
                         "the fetched contents are never emitted, so the fetch is dead code")

    def test_both_stores_reach_the_BACKED_UP_ledger(self):
        blk = _between(SRC, 'led = dict(got.get("sample") or {})', "_TRUNC")
        self.assertIsNotNone(blk, "could not read the block that assembles the backed-up ledger")
        self.assertIn('led["gameFound"] = got["gameFound"]', blk,
                      "gameFound is returned in full by the board and STILL not folded into the "
                      "ledger being written — the plumbing half of this defect")
        self.assertIn('led["rwMade"] = got["rwMadeFull"]', blk,
                      "the fetched rwMade contents never reach the file")

    # ── the file says whose ledgers it holds ──────────────────────────────────────────────────
    def test_the_snapshot_records_its_ROUTE(self):
        blk = _between(SRC, 'json.dump({"takenAt": stamp', "ensure_ascii=False)")
        self.assertIsNotNone(blk, "could not read the snapshot write")
        self.assertIn(
            '"route": got.get("route")', blk,
            "the snapshot records no route. restore_ledger.py restores into whatever board is "
            "showing and picks a file by heuristic, so a snapshot of one profile could be restored "
            "into another and nothing in the file would contradict it. board_ownership ALREADY "
            "fetches the route — not recording it is dropping it on the floor."
        )

    # ── ⚠ THE LOAD-BEARING LAW ────────────────────────────────────────────────────────────────
    def test_gameFound_is_NOT_graded_for_truncation(self):
        """A check that cannot fail is worse than no check, because it reads as coverage.

        Truncation is graded by comparing a copy against a count the BOARD reports independently.
        `counts.runewordsMade` is such a count. There is none for gameFound, so the only available
        comparison is the copy against its own length — circular by construction.
        """
        blk = _between(SRC, "_TRUNC = (", "for k, _ck in _TRUNC:")
        self.assertIsNotNone(blk, "the truncation table is gone")
        self.assertNotIn(
            "gameFound", blk,
            "gameFound is in the truncation table. The board publishes no independent count for "
            "it, so it would be compared against its own length and could never fail — coverage "
            "in appearance only. [[unknown-stays-unknown]]"
        )
        self.assertIn('("rwMade", "runewordsMade")', blk,
                      "rwMade is not graded against counts.runewordsMade, which the board DOES "
                      "report independently — so the one new store that CAN be checked is not")

    def test_an_absent_count_is_skipped_not_treated_as_zero(self):
        blk = _between(SRC, "for k, _ck in _TRUNC:", "if not force and")
        self.assertIsNotNone(blk, "could not read the truncation loop")
        self.assertRegex(
            blk, r"if\s+_want\s+is\s+None\s*:\s*\n\s*continue",
            "a missing count is not skipped. `int(None or 0)` is 0 and `n < 0` never fires, so an "
            "unanswerable store would pass silently as though it had been checked."
        )

    # ── the refusals that make the loop trustworthy must not have moved ───────────────────────
    def test_the_EMPTINESS_refusal_still_counts_only_the_original_three(self):
        """⚠ A board can honestly hold zero runewords. Folding the new stores into the emptiness
        total would let a TRUE state refuse every snapshot forever — a fact turned into an outage.
        """
        m = re.search(r'total = sum\(int\(counts\.get\(k\) or 0\) for k in \(([^)]*)\)\)', SRC)
        self.assertIsNotNone(m, "the emptiness total is gone")
        got = m.group(1)
        for bad in ("rwMade", "gameFound", "runewordsMade"):
            self.assertNotIn(bad, got,
                             "%s joined the EMPTINESS total. Zero runewords is a legitimate board "
                             "state, and refusing every snapshot over it converts a true reading "
                             "into a permanent backup outage." % bad)

    # ── ⚠⚠ v2737 — THE COMPLETE EXPORT, AND WHERE IT IS ALLOWED TO LIVE ───────────────────────
    def test_the_snapshot_asks_the_board_for_its_OWN_complete_export(self):
        """CENSUS of bible.html's `setItem('d2r_*')` writers: it writes 91 stores, the manual
        Backup & Share button exports 85, and this automatic loop copied FIVE.

        Konyo: *"i want this automated not relying on the user"* — and that is exactly the line the
        coverage fell on. The complete path needed him to click; the path needing nothing from him
        held five ledgers. Missing included `d2r_tally` (his 292/403 counters), `d2r_grailUnfound`
        (the un-tick decisions a reset must write) and the craft/gem/rune/material stashes.

        ⚠ THE FIX CALLS THE EXPORTER THAT ALREADY EXISTS rather than widening the hand-rolled list.
        `_collectProgress` walks the RAW store, emits only the ACTIVE account's view under bare
        names, and refuses the six identity PTRS so a restore can neither transfer nor revoke
        ownership. The five-store assembly was a subset of it, and that is precisely why rwMade and
        gameFound were absent from 60 consecutive files. [[copy-drift]]
        """
        self.assertIn("window._collectProgress", SRC,
                      "the snapshot no longer asks the board for its own complete export, so it is "
                      "back to hand-picking a subset of a function that already does the job")
        self.assertIn("fullStores:fullStores", SRC,
                      "the export is fetched and never emitted, so the fetch is dead code")

    def test_the_complete_export_lands_BESIDE_the_ledger_not_INSIDE_it(self):
        """⚠ LOAD-BEARING, AND IT IS ABOUT KEEPING A LAW HONEST.

        `led` holds exactly five named stores. The v2735 corroborator invariant
        `backup-restore-vocabulary` fails on any store in `led` that ledger_restore does not know —
        which is the whole point of it: a sixth store joining the backup with nobody deciding
        whether it can be put back would otherwise be copied faithfully forever and be
        unrestorable. Dropping the full dump INTO `led` would have tripped that law, and the
        tempting fix would have been to widen the law to admit a key that is not a store at all.
        Beside it, both stay true. Every existing reader and ratchet also keys off led's five.
        """
        blk = _between(SRC, 'json.dump({"takenAt": stamp', "ensure_ascii=False)")
        self.assertIsNotNone(blk, "could not read the snapshot write")
        self.assertIn('"allStores"', blk,
                      "the complete export never reaches the file")
        led_blk = _between(SRC, 'led = dict(got.get("sample") or {})', "_TRUNC")
        self.assertIsNotNone(led_blk, "could not read the ledger assembly")
        self.assertNotIn("allStores", led_blk,
                         "the complete export was folded INTO `led`. That breaks the "
                         "backup-restore-vocabulary invariant, whose value is exactly that it "
                         "fails on an unknown store — and the fix would be to weaken the law.")

    def test_the_complete_export_is_NOT_graded_for_truncation(self):
        """Same reason gameFound is not: no independent count exists for these, so the only
        available comparison is the copy against its own length — which cannot fail, and a check
        that cannot fail is worse than none because it reads as coverage."""
        blk = _between(SRC, "_TRUNC = (", "for k, _ck in _TRUNC:")
        self.assertIsNotNone(blk, "the truncation table is gone")
        self.assertNotIn("allStores", blk,
                         "allStores joined the truncation table and could never fail there")

    def test_the_truncation_refusal_still_refuses(self):
        self.assertIn("a partial ledger is not a backup", SRC,
                      "the truncation refusal is gone — a short read could overwrite a good backup")


if __name__ == "__main__":
    unittest.main(verbosity=2)
