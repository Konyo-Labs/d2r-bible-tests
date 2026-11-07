"""WHAT THE VAULT LANE LEARNS MUST SURVIVE THE PROCESS — ESPECIALLY WHAT IT STOPPED PAYING FOR.

⚠⚠ MEASURED 2026-09-10 (#60, REG-900). `control_app._VAULT_AUTOREAD` had **14 write sites and ZERO
persistence sites** — no save, no load, no json anywhere. It held everything the lane had learned:

    reads    how many sweeps completed        tries    how many attempts each reel has cost
    lastTs   when the last one finished       retired  reels the lane STOPPED PAYING FOR

⚠ `retired` is the expensive one. A retirement is the lane's decision not to buy a reel again.
Losing it does not merely forget — it makes the lane pay a second time. That is the "and re-spends
for it" in #60's title, and it was a property of the code, not a suspicion.

⚠⚠ AND IT HAD BEEN LYING TO THE CORROBORATOR. `corroborate.py`'s `vault-lane-has-worked` reads
`lastTs or reads > 0` under the comment *"lastTs is the durable tell — `reads` is a process-local
counter and resets on every restart."* BOTH were process-local; there was no durable tell. That
false distinction is why a RESTART read as "this lane has never swept" — a very different
accusation from the truth, which was "this process is new". Measured on his tree the same day:
`on=True reads=0 lastTs=None owed=8`, while his console had been REPLACED TWICE in one hour (#67).
[[label-outlived-referent]] [[unknown-stays-unknown]]

⚠ NO FOOTAGE AND NO LIVE STORE. Every test here points TV_HIST at a temp directory, so it measures
the same thing on his Mac and on a CI runner — and it cannot touch the store his console is using.
[[feedback-fixtures-never-touch-live-data]]
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import control_app as CA   # noqa: E402


class TheVaultLaneRemembersAcrossARestart(unittest.TestCase):

    def setUp(self):
        self._hist = os.environ.get("TV_HIST")
        self.tmp = tempfile.mkdtemp(prefix="vault-remember-")
        os.environ["TV_HIST"] = self.tmp
        self._snap = dict(CA._VAULT_AUTOREAD)
        self._store = dict(CA._VAULT_AUTOREAD_STORE)

    def tearDown(self):
        # ⚠ put BOTH globals back, or this suite's fixture leaks into the next law — REG-865.
        CA._VAULT_AUTOREAD.clear(); CA._VAULT_AUTOREAD.update(self._snap)
        CA._VAULT_AUTOREAD_STORE.clear(); CA._VAULT_AUTOREAD_STORE.update(self._store)
        if self._hist is None:
            os.environ.pop("TV_HIST", None)
        else:
            os.environ["TV_HIST"] = self._hist
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _restart(self):
        """Everything a new process would start with, and nothing more."""
        CA._VAULT_AUTOREAD.update({"reads": 0, "lastTs": 0, "retired": {}, "tries": {},
                                   "lastWhy": {}, "skipped": {}, "reextract": {}, "cursor": None})
        CA._VAULT_AUTOREAD_STORE.update({"tried": False, "readable": None})

    def test_the_rotation_cursor_survives_a_restart(self):
        """★ v3539 REG-1651 — DRIVEN, because the source law below this class could not see it. v3283 saved the
        store "where the cursor changes", and a law checked that `_vault_autoread_save()` sits beside the
        assignment - it did, and the payload it wrote never carried `cursor`, nor did the loader read one. So
        every relaunch restarted the rotation at the head of the owed list, while the law stayed green."""
        CA._VAULT_AUTOREAD["cursor"] = "reel_s_1500000000042_16510"
        self.assertTrue(CA._vault_autoread_save(), "the store could not be written at all")
        self._restart()
        self.assertIsNone(CA._VAULT_AUTOREAD.get("cursor"), "the fixture did not clear memory - proves nothing")
        self.assertIs(CA._vault_autoread_load(), True)
        self.assertEqual(CA._VAULT_AUTOREAD.get("cursor"), "reel_s_1500000000042_16510",
                         "the rotation position was lost across a restart - the head of the owed list gets "
                         "the first turn after every relaunch")

    def test_a_fresh_store_says_it_exists_once_written(self):
        """REG-1750 — the load remembered its FIRST answer for the life of the process: on a fresh PC that was False
        ("no store yet - this lane has genuinely never recorded a read"), and it stayed False after the lane saved.
        MEASURED on the ALT 2026-10-03: that sentence beside reads 51, until a restart re-read the file."""
        self._restart()
        self.assertIs(CA._vault_autoread_load(), False, "PREMISE: a fresh fixture has no store yet")
        CA._VAULT_AUTOREAD["reads"] = 3
        self.assertTrue(CA._vault_autoread_save(), "the store could not be written at all")
        self.assertIs(CA._vault_autoread_load(), True,
                      "the lane just wrote its store and still says 'no store yet - never recorded a read'")

    def test_a_failed_write_leaves_an_old_file_unread(self):
        """REG-1755 — the finally ran after a FAILED write too. With a file already on disk and the
        cache still False ("no store yet"), it flipped the cache to readable. A write that did not
        land must leave that answer where it was."""
        path = CA._vault_autoread_path()
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write('{"reads": 1, "retired": {"reel_old": {}}}')
        self._restart()
        CA._VAULT_AUTOREAD_STORE.update({"tried": True, "readable": False})
        CA._VAULT_AUTOREAD["reads"] = 9
        with mock.patch("os.replace", side_effect=OSError("law: the replace will not land")):
            self.assertIs(CA._vault_autoread_save(), False, "a replace that raises reported success")
        self.assertIs(CA._VAULT_AUTOREAD_STORE.get("readable"), False,
                      "a failed write flipped 'no store yet' to readable because an older file was already there")
        with io.open(path, encoding="utf-8") as fh:
            still = fh.read()
        self.assertIn("reel_old", still, "the failed write replaced the older store")

    # ── the store must not be able to reach his live console ─────────────────────────────────
    def test_the_store_lives_under_the_fixture_root(self):
        p = CA._vault_autoread_path()
        # #107 - realpath on both sides: Windows' temp dir comes back as an 8.3 short name (RUNNER~1), the store as the long one
        self.assertIn(os.path.normcase(os.path.realpath(self.tmp)), os.path.normcase(os.path.realpath(p)),
                      "the vault store resolved to %r while TV_HIST pointed at a fixture — a suite "
                      "or a render gate would write into his live tv/ and overwrite what his lane "
                      "had retired" % p)

    # ── the whole point ──────────────────────────────────────────────────────────────────────
    def test_a_retirement_survives_a_restart(self):
        CA._VAULT_AUTOREAD["retired"] = {"reel_x": {"why": "3 attempts, still owed", "at": 1}}
        CA._VAULT_AUTOREAD["reads"], CA._VAULT_AUTOREAD["lastTs"] = 3, 1788999999000
        self.assertTrue(CA._vault_autoread_save(), "the store could not be written at all")
        self._restart()
        self.assertEqual(sorted(CA._VAULT_AUTOREAD["retired"]), [],
                         "the fixture did not actually clear memory, so this proves nothing")
        self.assertIs(CA._vault_autoread_load(), True, "the store did not read back")
        self.assertEqual(sorted(CA._VAULT_AUTOREAD["retired"]), ["reel_x"],
                         "a RETIREMENT was lost across a restart — the lane will pay for that reel "
                         "again, which is exactly what #60 is about")
        self.assertEqual(CA._VAULT_AUTOREAD["reads"], 3, "the completed-read count was lost")
        self.assertEqual(CA._VAULT_AUTOREAD["lastTs"], 1788999999000,
                         "lastTs was lost — 'has this lane ever swept' goes back to reading 0")

    def test_has_ever_swept_is_true_again_after_a_restart(self):
        """The corroborator's own predicate, run over a restart."""
        CA._VAULT_AUTOREAD["lastTs"] = 1788999999000
        CA._vault_autoread_save()
        self._restart()
        st = CA._vault_autoread_state() or {}
        left = 1 if (st.get("lastTs") or (st.get("reads") or 0) > 0) else 0
        self.assertEqual(left, 1,
                         "after a restart the lane still reports it has NEVER swept, so "
                         "`vault-lane-has-worked` fires on a new process instead of a broken lane")

    # ── the third outcome, and it is the one that costs money ────────────────────────────────
    def test_an_unreadable_store_is_UNKNOWN_and_not_a_fresh_start(self):
        with io.open(CA._vault_autoread_path(), "w", encoding="utf-8") as fh:
            fh.write("{ this is not json")
        self._restart()
        self.assertIsNone(CA._vault_autoread_load(),
                          "an UNREADABLE store read as a fresh start. An empty `retired` is then a "
                          "CLAIM that nothing was retired, and acting on it re-buys every reel the "
                          "lane had already ruled out")
        st = CA._vault_autoread_state() or {}
        self.assertIsNone(st.get("storeReadable"),
                          "the state does not carry the store's UNKNOWN, so nothing downstream can "
                          "tell an unmeasured retired list from an empty one")
        self.assertIn("UNKNOWN", str(st.get("storeWhy") or ""),
                      "UNKNOWN with no reason attached is not an answer")

    def test_no_store_yet_is_FALSE_not_unknown(self):
        """A first run is a real fact and must not be dressed as UNKNOWN either."""
        self._restart()
        self.assertIs(CA._vault_autoread_load(), False,
                      "a missing store must read as 'no store yet', which is a genuine fresh start")

    # ── the write must not be able to leave a torn file ──────────────────────────────────────
    def test_the_writer_is_atomic(self):
        """⚠ PARSED, NOT GREPPED. This repo has already emptied a 6 MB file with a plain
        open(w). [[source-reading-guard]] [[open-for-write-truncates-first]]"""
        import ast
        with io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        fn = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "_vault_autoread_save"), None)
        self.assertIsNotNone(fn, "_vault_autoread_save is gone — nothing persists the lane")
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == "replace"]
        self.assertTrue(calls,
                        "_vault_autoread_save does not os.replace — it writes the destination "
                        "directly, so a reader can see a half-written store and a crash mid-write "
                        "loses every retirement")


    # ── THE ACTOR, NOT JUST THE REPORTER ─────────────────────────────────────────────────────
    def test_a_tick_after_a_restart_still_knows_what_was_retired(self):
        """⚠⚠ THE MONEY BUG, AND v2901 SHIPPED IT INSIDE THE FIX FOR IT. Raised by the
        cross-family eye: v2901 loaded the store from `_vault_autoread_state()` — the REPORTER —
        and `vault_autoreel_tick()`, the function that SPENDS, read `retired` straight out of
        process memory. Two of its callers never go through state(): the 45s loop's first pass
        after a restart, and the stop-agent nudge that fires as soon as a reel stops. So a tick
        could run with `retired == {}` and pay for every reel the previous process had ruled out.

        Chronicle's sibling had this right already — `chronicle_autoreel_tick` lazy-loads via
        `_chron_reels_retired()`. The persistence was copied; the lesson was not. [[copy-drift]]"""
        CA._VAULT_AUTOREAD["retired"] = {"reel_paid_for_once": {"why": "2 attempts", "at": 1}}
        self.assertTrue(CA._vault_autoread_save())
        self._restart()
        self.assertEqual(sorted(CA._VAULT_AUTOREAD["retired"]), [],
                         "the fixture did not clear memory, so this proves nothing")
        CA.vault_autoreel_tick()          # ⚠ the ACTOR, called directly — no state() first
        self.assertIn("reel_paid_for_once", CA._VAULT_AUTOREAD["retired"],
                      "a tick ran after a restart without restoring the retirements, so the lane "
                      "will pay again for a reel it had already ruled out")

    def test_a_save_before_any_load_cannot_erase_the_store(self):
        """An empty in-memory `retired` written over a good store is strictly worse than not
        persisting at all — the file would then look authoritative while holding nothing."""
        CA._VAULT_AUTOREAD["retired"] = {"reel_paid_for_once": {"why": "2 attempts", "at": 1}}
        self.assertTrue(CA._vault_autoread_save())
        self._restart()
        CA._VAULT_AUTOREAD["reads"] = 1   # something trivial changes, and a save fires
        CA._vault_autoread_save()
        with io.open(CA._vault_autoread_path(), encoding="utf-8") as fh:
            on_disk = json.load(fh)
        self.assertIn("reel_paid_for_once", on_disk.get("retired") or {},
                      "a save that ran before any load wrote empty memory over the store and "
                      "destroyed every retirement on disk")


    # ── THE THIRD OUTCOME, WHICH TWO SHIPS LEFT THEORETICAL ──────────────────────────────────
    def test_a_tick_against_an_unreadable_store_refuses_to_spend(self):
        """⚠⚠ THE MONEY BUG FOR THE `None` CASE, AND IT SURVIVED TWO SHIPS. v2901 loaded only in
        the reporter; v2902 made the actor load and then THREW THE ANSWER AWAY. After a failed load
        `retired` is still {}, so every reel this lane had ruled out looks new and it pays for all
        of them. The tick already refuses when `_vault_owed_reels()` is None instead of collapsing
        that into "owed 0" — `retired` now gets the same treatment.

        The eye's own words: a gate that has never been red for UNKNOWN-then-spend will not catch
        this coming back. So it is pinned here. [[unknown-stays-unknown]]"""
        CA._VAULT_AUTOREAD["retired"] = {"reel_ruled_out": {"why": "2 attempts", "at": 1}}
        self.assertTrue(CA._vault_autoread_save())
        with io.open(CA._vault_autoread_path(), "w", encoding="utf-8") as fh:
            fh.write("{ not json at all")
        self._restart()
        r = CA.vault_autoreel_tick() or {}
        self.assertTrue(r.get("unknown"),
                        "the tick did not refuse against an UNREADABLE store: %r. Its `retired` is "
                        "empty only because the read failed, so it would re-buy every reel the "
                        "lane had already ruled out" % (str(r)[:140],))
        self.assertFalse(r.get("ok"), "an UNKNOWN tick reported ok")

    def test_a_save_against_an_unreadable_store_leaves_the_file_alone(self):
        """An UNKNOWN written out as well-formed JSON is worse than never persisting: the NEXT
        process loads it cleanly as True and pays again."""
        with io.open(CA._vault_autoread_path(), "w", encoding="utf-8") as fh:
            fh.write("{ not json at all")
        self._restart()
        CA._VAULT_AUTOREAD["reads"] = 99
        self.assertFalse(CA._vault_autoread_save(),
                         "the save reported success against an unreadable store")
        with io.open(CA._vault_autoread_path(), encoding="utf-8") as fh:
            still = fh.read()
        self.assertIn("not json", still,
                      "an unreadable store was OVERWRITTEN with empty memory — the only copy of "
                      "those retirements is gone and the next process will trust the emptiness")

    def test_an_unreadable_store_is_retried_not_blind_for_the_process(self):
        """⚠ Chronicle's sibling `_chron_reels_retired()` does not cache a failed read, so a later
        tick can retry. Caching `tried=True` on failure turns one bad read into permanent
        blindness for the life of the console."""
        with io.open(CA._vault_autoread_path(), "w", encoding="utf-8") as fh:
            fh.write("{ not json at all")
        self._restart()
        self.assertIsNone(CA._vault_autoread_load(), "the corrupt store did not read as UNKNOWN")
        # the file is repaired underneath — a later tick must be able to see it
        CA._VAULT_AUTOREAD["retired"] = {"reel_ruled_out": {"why": "x", "at": 1}}
        CA._VAULT_AUTOREAD_STORE.update({"tried": True, "readable": True})
        CA._vault_autoread_save()
        CA._VAULT_AUTOREAD.update({"retired": {}})
        CA._VAULT_AUTOREAD_STORE.update({"tried": False, "readable": None})
        self.assertIs(CA._vault_autoread_load(), True,
                      "a repaired store could not be read back — the failure was cached")


class TheHeadOfTheOwedListCannotStarveTheRest(unittest.TestCase):
    """★ v3282 — HE ASKED WHY THREE REELS WERE NOT FLOWING, AND THE ANSWER WAS A PERMANENT HEAD.

    Konyo, on the census showing 3 reels tagged `panels-never-banked`: *"why lol? why is it not
    extraced and unified logic and flowing like the others whats makes it special?"*

    Nothing makes them special. MEASURED on his console:

        OWED by the doctrine          TRIED by this lane
          ..._12001   tries=0           ..._9654    tries=1
          ..._36946   NEVER TRIED       ..._12211   tries=1
          ..._92772   NEVER TRIED       ..._42457   tries=0
                                        ..._42840   tries=2
                                        ..._75324   tries=2
        retired [] · skipped {} · lane on, storeReadable, every 45s, reads 3750

    ⚠ My first reading of that was WRONG and is corrected here: I took the five tried-but-not-owed
    reels as proof the queue was a different list. It is not — the tick iterates
    `_vault_owed_reels()` directly, and `tries` is HISTORY, not the queue. Reading the loop showed
    the real mechanism.

    The loop always walked the owed list from index 0 and RETURNS as soon as it acts. The head
    reel exhausts `_VAULT_AUTOREAD_MAX_TRIES`, hits the `panels-never-banked` branch — which resets
    its tries to 0 and returns, *"back to the top of the river"* — and the next tick starts on the
    same reel again. It can never get past position 0, so positions 1 and 2 are unreachable: not
    skipped, not retired, **NEVER TRIED**. A queue with a permanent head is not a queue.

    Simulated over six ticks with a head that always refuses: before, `A A A A A A`; after,
    `A B C A B C`.
    """

    def _tick_src(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = src.find("def vault_autoreel_tick(")
        self.assertGreater(i, -1, "the vault auto-read tick is gone or renamed")
        j = src.find("\ndef ", i + 10)
        return src[i:j if j > i else i + 9000]

    def test_the_owed_list_is_ROTATED_so_no_reel_owns_the_head(self):
        body = self._tick_src()
        self.assertIn('_VAULT_AUTOREAD.get("cursor")', body,
                      "the tick never reads a cursor, so it always starts at index 0 and a reel "
                      "that cannot clear keeps every turn for itself")
        self.assertIn("owed_list[_k:]", body,
                      "the owed list is not rotated, so position 0 is permanent")

    def test_the_cursor_advances_on_EVERY_reel_considered_not_only_on_success(self):
        """⚠ THE SUBTLE HALF. Advancing only after a successful sweep would leave a reel that
        always refuses sitting at the head again next tick — the same starvation, one level down."""
        body = self._tick_src()
        # ⚠ BOTH ENDS ANCHORED ON REAL CODE. The first cut sliced a fixed 420 chars from the
        # loop head; adding a comment above the assignment pushed it past the window and the law
        # went red over code that was correct. A window that runs out is a law about my guess.
        # [[source-window-shortcut]]
        i = body.find("for d in owed_list:")
        self.assertGreater(i, -1, "the loop over the owed list is gone")
        j = body.find('if rid in _VAULT_AUTOREAD["retired"]:', i)
        self.assertGreater(j, i, "the first decision in the loop is gone — anchor lost")
        head = body[i:j]
        self.assertIn('_VAULT_AUTOREAD["cursor"] = rid', head,
                      "the cursor is not set at the top of the loop, so it can only advance on "
                      "paths that succeed")

    def test_the_cursor_is_PERSISTED_where_it_changes_not_only_where_it_acts(self):
        """★ raised by the cross-family eye on v3282, and real.

        The cursor was written in memory and saved only by the requeue / retire / success
        branches. A tick that ended on a `continue` — retired, still growing, already sealed — or
        on the `deferred` early return left the position unsaved. In-process that is invisible,
        because the dict survives between ticks; across a RESTART the rotation resumes from a
        stale point and the fairness this whole version buys is partly lost.

        ⚠ This suite is named for exactly that failure mode: the vault lane REMEMBERS ACROSS A
        RESTART. A field that only some paths persist does not.
        """
        body = self._tick_src()
        i = body.find('_VAULT_AUTOREAD["cursor"] = rid')
        self.assertGreater(i, -1, "the cursor is no longer set in the loop")
        near = body[max(0, i - 200):i + 260]
        self.assertIn("_vault_autoread_save()", near,
                      "the cursor is set without being persisted, so a restart loses the rotation "
                      "position on every path that does not act")
        self.assertIn('_VAULT_AUTOREAD.get("cursor") != rid', near,
                      "the save is unconditional, so an unchanged cursor rewrites the store on "
                      "every reel of every tick")

    def test_the_list_itself_is_STILL_the_doctrine_and_was_not_widened(self):
        """⚠⚠ MONEY. The vault lane SPENDS on reads. v2877 records a rewrite that would have
        queued 26 reels, 10 of them explicitly held, at up to 97 paid reads. This change decides
        WHICH owed reel gets the one turn per tick — it must never change WHICH reels are owed."""
        body = self._tick_src()
        self.assertIn("owed_list = _vault_owed_reels()", body,
                      "the owed list no longer comes from the doctrine — the money guard is gone")
        for widen in ("reel_router.route(", "os.listdir(", "glob.glob("):
            self.assertNotIn(widen, body,
                             "the tick now enumerates reels itself (%s) instead of asking the "
                             "doctrine, which is how a sweep starts paying for held reels" % widen)


RED_PROOF = [
    {
        'why': 'dropping the restore: every restart goes back to reporting a lane that has never swept, and every retirement is bought again',
        'file': 'control_app.py',
        'find': '        _st_readable = _vault_autoread_load()',
        'replace': '        _st_readable = False',
        'matches': 1,
    },
    {
        'why': "returning False instead of None on an unreadable store — the load then reports a corrupt file as a FRESH START, and an empty `retired` becomes a claim nobody measured. The previous sabotage here tampered a cached flag the next load overwrites, which changed no behaviour: a green sabotage is the sabotage's fault",
        'file': 'control_app.py',
        'find': '            return None                  # ⚠ `tried` stays False so a later tick may retry',
        'replace': '            return False',
        'matches': 1,
    },
    {
        'why': 'writing the store in place instead of tmp + os.replace — a crash mid-write loses every retirement, and a reader can see a torn file',
        'file': 'control_app.py',
        'find': '        os.replace(tmp, dest)\n        return True',
        'replace': '        shutil.copyfile(tmp, dest)\n        return True',
        'matches': 1,
    },
    {
        'why': 'unloading the ACTOR: a tick after a restart then sees no retirements and pays again for every reel the previous process had ruled out — the money bug v2901 shipped inside its own fix',
        'file': 'control_app.py',
        'find': '    _mem = _vault_autoread_load()\n    if _mem is None:\n        return {"ok": False, "unknown": True, "owed": None,',
        'replace': '    _mem = False\n    if _mem is None:\n        return {"ok": False, "unknown": True, "owed": None,',
        'matches': 1,
    },
    {
        'why': 'letting a save run before any load: empty memory is written over a good store and every retirement on disk is destroyed',
        'file': 'control_app.py',
        'find': '    _mem = _VAULT_AUTOREAD_STORE.get("readable")\n    if not _VAULT_AUTOREAD_STORE.get("tried"):\n        _mem = _vault_autoread_load()',
        'replace': '    _mem = True',
        'matches': 1,
    },
    {
        'why': 'letting the TICK spend against an unreadable store — its `retired` is empty only because the read failed, so it re-buys every reel the lane had ruled out',
        'file': 'control_app.py',
        'find': '    if _mem is None:\n        return {"ok": False, "unknown": True, "owed": None,',
        'replace': '    if False:\n        return {"ok": False, "unknown": True, "owed": None,',
        'matches': 1,
    },
    {
        'why': 'letting the SAVE overwrite an unreadable store: UNKNOWN becomes well-formed JSON saying nothing was retired, and the next process trusts it',
        'file': 'control_app.py',
        'find': '    if _mem is None:\n        return False\n    try:\n        dest = _vault_autoread_path()',
        'replace': '    if False:\n        return False\n    try:\n        dest = _vault_autoread_path()',
        'matches': 1,
    },
    {
        'why': 'REG-1651 - the writer leaves the cursor out again: every relaunch restarts the rotation at the head',
        'file': 'control_app.py',
        'find': '               "cursor": _VAULT_AUTOREAD.get("cursor")}\n',
        'replace': '               }\n',
        'matches': 1,
    },
    {
        'why': 'REG-1651 - the loader ignores a saved cursor: the position is on disk and never comes back',
        'file': 'control_app.py',
        'find': '        if isinstance(d.get("cursor"), str) and d.get("cursor"):\n            _VAULT_AUTOREAD["cursor"] = d["cursor"]\n',
        'replace': '',
        'matches': 1,
    },
    {
        'why': 'REG-1750 - a written store is still reported as "no store yet": the load keeps its first answer',
        'file': 'control_app.py',
        'find': '            _VAULT_AUTOREAD_STORE["tried"], _VAULT_AUTOREAD_STORE["readable"] = True, True\n',
        'replace': '            pass\n',
        'matches': 1,
    },
    {
        'why': 'REG-1755 - a failed write still marks an old file as a fresh store: the cache flips from no-store-yet to readable',
        'file': 'control_app.py',
        'find': '        if not locals().get("_failed"):\n            _vault_autoread_note_written()          # REG-1750\n',
        'replace': '        _vault_autoread_note_written()          # REG-1750\n',
        'matches': 1,
    }
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
