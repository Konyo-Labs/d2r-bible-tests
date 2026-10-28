#!/usr/bin/env python3
"""v3009 (#81) — RETENTION SIZED FROM HIS OWN LOSS, WITH THE ONE FILE THAT ANSWERS IT PROTECTED.

The 2026-09-08 emptying was noticed ~3 days late and the oldest backup on disk was 69 hours too
young to say which backup predates the loss. His ruling: "it gets auto saved daily in a ledger
just incase if needed to restore." The policy: 48h rolling + first-of-day keepers for 90 days +
an EPISODE GUARD — while a d2r_storeEmptied episode is OPEN, the newest backup older than its
`at` is protected whatever its age, because deleting it would be the backup system deleting its
own reason to exist.

⚠ Deletion is the irreversible act, so every law here drives the SHIPPED function on a fixture
dir and counts what survived. [[unknown-stays-unknown]]
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #173 - its scratch is its own, so listing it keeps the law keyable
_fx_tmp.contain()

import control_app as CA  # noqa: E402

DAY = 24 * 3600.0


class TheBackupPruneNeverOrphansALoss(unittest.TestCase):

    #: ⚠⚠ v3014 — A PINNED CLOCK, BECAUSE THE WALL CLOCK MADE THIS GATE FLAKE 2 HOURS IN 24.
    #: The keeper law spaces two snapshots 7200s apart and expects ONE to survive as that day's
    #: first. With `now = time.time()` those two straddle a UTC midnight whenever the run happens
    #: between 00:00 and 02:00 UTC — both become first-of-day keepers and NOTHING prunes.
    #: MEASURED by sweeping `now` across all 24 hours: fails at 00:30 and 01:30 (pruned=0,
    #: keepers=2), passes the other 22. Flagged by the post-ship review before it died on a
    #: session limit; reproduced here rather than taken on its word. A green that depends on when
    #: you look is not a green. [[feedback-blind-fixture-green-gate]] [[stale-reading]]
    #: 2026-06-15 12:00:00 UTC — mid-day, so day arithmetic is stable at every offset used below.
    PINNED_NOW = 1781524800.0

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="ledgerprune.")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.now = self.PINNED_NOW
        # ⚠ 2026-09-27 — the prune now also reads the backup loop's LEDGER-DROP record, resolved at
        # call time through _fixture_root_for_state(). Without a fixture world this law would read
        # HIS live record, and a damaged one (the prune then deletes nothing, by design) would turn
        # these cases red for a reason that is his machine, not the code. Guard the fixture.
        # [[feedback-fixtures-never-touch-live-data]]
        _world = tempfile.mkdtemp(prefix="ledgerprune.world.")
        self.addCleanup(shutil.rmtree, _world, True)
        _old = os.environ.get("TV_HIST")
        os.environ["TV_HIST"] = _world
        self.addCleanup(lambda: os.environ.__setitem__("TV_HIST", _old) if _old is not None
                        else os.environ.pop("TV_HIST", None))

    def _snap(self, name, age_s, emptied=None):
        p = os.path.join(self.d, name)
        doc = {"d2r_foundLog": "[]"}
        if emptied is not None:
            doc["d2r_storeEmptied"] = json.dumps(emptied)
        io.open(p, "w", encoding="utf-8").write(json.dumps(doc))
        t = self.now - age_s
        os.utime(p, (t, t))
        return name

    def _left(self):
        return sorted(_fx_tmp.list_own(self.d))

    def test_the_rolling_window_is_kept(self):
        a = self._snap("ledger_a.json", 3600)
        b = self._snap("ledger_b.json", 47 * 3600)
        r = CA._ledger_backup_prune(self.d, now=self.now)
        self.assertEqual(self._left(), sorted([a, b]))
        self.assertEqual(r["pruned"], 0)

    def test_an_old_non_keeper_is_pruned_and_the_days_first_survives(self):
        """Two snapshots on one old day: the FIRST is the keeper, the second goes."""
        first = self._snap("ledger_day_first.json", 10 * DAY + 7200)
        self._snap("ledger_day_second.json", 10 * DAY)
        fresh = self._snap("ledger_fresh.json", 60)
        r = CA._ledger_backup_prune(self.d, now=self.now)
        self.assertEqual(self._left(), sorted([first, fresh]),
                         "the day's first snapshot is the daily keeper his ruling asked for; "
                         "the day's second is redundant history")
        self.assertEqual(r["pruned"], 1)
        self.assertEqual(r["keepers"], 1)

    def test_a_keeper_older_than_ninety_days_retires(self):
        self._snap("ledger_ancient.json", 91 * DAY)
        fresh = self._snap("ledger_fresh.json", 60)
        CA._ledger_backup_prune(self.d, now=self.now)
        self.assertEqual(self._left(), [fresh])

    def test_an_open_loss_protects_the_backup_that_predates_it(self):
        """⚠ THE GUARD THAT OUTRANKS EVERY RULE. Loss at T; the newest backup OLDER than T is the
        only file that answers 'which backup predates the loss'. While the episode is OPEN it
        survives whatever its age."""
        loss_at_ms = (self.now - 100 * DAY) * 1000.0
        old = self._snap("ledger_predates.json", 101 * DAY)          # older than the loss
        self._snap("ledger_between.json", 50 * DAY)                  # after the loss, prunable
        fresh = self._snap("ledger_newest.json", 60,
                           emptied={"at": loss_at_ms, "boots": 3})   # OPEN: no recoveredAt
        r = CA._ledger_backup_prune(self.d, now=self.now)
        self.assertIn(old, self._left(),
                      "the one backup predating an OPEN loss was pruned — the backup system "
                      "deleted its own reason to exist")
        self.assertEqual(r["protected"], old)
        self.assertIn(fresh, self._left())

    def test_a_closed_loss_protects_nothing_extra(self):
        loss_at_ms = (self.now - 100 * DAY) * 1000.0
        self._snap("ledger_predates.json", 101 * DAY)
        fresh = self._snap("ledger_newest.json", 60,
                           emptied={"at": loss_at_ms, "boots": 3,
                                    "recoveredAt": (self.now - 99 * DAY) * 1000.0})
        r = CA._ledger_backup_prune(self.d, now=self.now)
        self.assertIsNone(r["protected"],
                          "a CLOSED episode is history; its predating backup ages out normally")
        self.assertNotIn("ledger_predates.json", self._left())
        self.assertIn(fresh, self._left())

    def test_the_keeper_verdict_does_not_depend_on_the_hour_of_the_run(self):
        """⚠ THE FLAKE ITSELF, MADE A LAW — but the law the policy can actually keep.

        The first cut of this swept `now` across 24 hours with the fixture above (two snapshots
        7200s apart) and demanded one verdict. It went RED, and the RED was MINE: a day-bucketing
        policy is SUPPOSED to answer differently when a pair straddles a midnight, so that law
        asserted something false about the code it guards. Two snapshots two hours apart genuinely
        are on two days at 00:30 UTC.

        What IS invariant — and what the keeper test always meant — is that holding the UTC-DAY
        LAYOUT fixed, the hour you happen to run at must not change the answer. So the fixture here
        is anchored to a day boundary rather than to `now`: both snapshots sit at 12:00 and 14:00
        UTC of the same day, ten days back, whatever hour `now` is. If the verdict still moves, the
        policy is reading the clock instead of the layout. [[unknown-stays-unknown]]"""
        import calendar
        import datetime
        verdicts = {}
        for hour in range(24):
            now = calendar.timegm(datetime.datetime(2026, 6, 15, hour, 30, 0).timetuple())
            #: ⚠ TWO old days, not one. With a single day this fixture was BLIND to the day
            #: bucket being keyed off `now` instead of each file's own mtime — MEASURED: the
            #: tampered prune returned the identical (1, 1, True). Both bucketings pick the same
            #: survivor when everything is on one day, so the fixture could not tell them apart.
            #: With two days the correct policy keeps ONE PER DAY (2 keepers) and the broken one
            #: collapses every file into today's bucket and keeps a single global oldest.
            today = datetime.datetime.utcfromtimestamp(now).date()
            dayA = today - datetime.timedelta(days=10)
            dayB = today - datetime.timedelta(days=9)

            def _at(d, h):
                return calendar.timegm(
                    datetime.datetime.combine(d, datetime.time(h, 0)).timetuple())

            anchored = {
                "ledger_a_first.json": _at(dayA, 12),
                "ledger_a_later.json": _at(dayA, 14),
                "ledger_b_first.json": _at(dayB, 12),
                "ledger_b_later.json": _at(dayB, 14),
                "ledger_fresh.json": now - 60,
            }
            d = tempfile.mkdtemp(prefix="sweep.")
            self.addCleanup(shutil.rmtree, d, True)
            for name, when in anchored.items():
                p = os.path.join(d, name)
                with io.open(p, "w", encoding="utf-8") as fh:
                    fh.write(json.dumps({"d2r_foundLog": "[]"}))
                os.utime(p, (when, when))
            r = CA._ledger_backup_prune(d, now=now)
            left = set(_fx_tmp.list_own(d))
            verdicts[hour] = (r["pruned"], r["keepers"],
                              "ledger_a_first.json" in left, "ledger_b_first.json" in left)

        distinct = sorted(set(verdicts.values()))
        self.assertEqual(len(distinct), 1,
                         "the verdict moves with the hour of the run even though the UTC-day "
                         "layout is identical at every hour: %s — that is the clock leaking into "
                         "a day-bucketing policy" % distinct)
        #: and it must be the RIGHT single verdict, not merely a stable wrong one — the day's
        #: FIRST survives as its keeper, the second goes, the fresh one is inside 48h.
        self.assertEqual(distinct[0], (2, 2, True, True),
                         "stable, but not the keeper policy — expected each old day to keep its "
                         "OWN first (2 kept, 2 pruned, both firsts alive); got %r" % (distinct[0],))

    def test_the_predating_backup_answers_what_the_store_HELD(self):
        """⚠⚠ v3030 (#81) — THE DENOMINATOR A RECOVERY IS JUDGED AGAINST.

        v3005 made the recovered row publish what the store holds NOW and said in its own words
        what it could not do: "one recovered name stamps it just as fully as four hundred." A count
        with nothing to compare it to cannot be argued with — 440 back out of 445 and 440 back out
        of 900 print identically.

        The number is on disk. v3009's retention keeps the newest snapshot PREDATING an open
        episode alive for exactly this question, and this reads it.

        ⚠ NEWEST-BEFORE, NOT OLDEST — an older snapshot understates what was lost and makes the
        recovery look better than it was, which is the flattering direction and therefore the one
        that must be refused. [[zero-needs-a-denominator]]"""
        now = self.PINNED_NOW
        # three snapshots, all older than the loss, with DIFFERENT counts
        for name, age, fl in (("ledger_old.json", 6 * DAY, 300),
                              ("ledger_mid.json", 4 * DAY, 400),
                              ("ledger_near.json", 2 * DAY, 445)):
            pp = os.path.join(self.d, name)
            with io.open(pp, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"counts": {"foundLog": fl, "setPieces": 129},
                                     "allStores": {}}))
            os.utime(pp, (now - age, now - age))
        loss_at = (now - 1 * DAY) * 1000.0
        got, why = CA.ledger_counts_before(loss_at, bdir=self.d)
        self.assertIsInstance(got, dict, "no predating backup was found: %s" % why)
        self.assertEqual(
            got.get("foundLog"), 445,
            "it answered %r — the NEWEST snapshot before the loss holds 445; anything older "
            "understates what was lost and flatters the recovery" % got.get("foundLog"))
        self.assertIn("near", str(why), "the reason does not name which backup answered: %r" % why)

    def test_the_denominator_says_HOW_CLOSE_it_was_to_the_loss(self):
        """⚠⚠ v3032 — THE DENOMINATOR DEGRADES SILENTLY AND UPWARD, and only its DISTANCE from the
        loss can detect it. Found by the post-ship review of v3030, and the path is specific:

          · the true newest-before is a mid-day snapshot; the day's FIRST snapshot is the keeper
          · the episode CLOSES, so the open-episode guard lifts its protection
          · the mid-day file is now past 48h and is not first-of-day, so the prune takes it
          · the OLD keeper survives on the 90-day rule and inherits the role

        `ledger_counts_before` still finds a predating file, so it never answers UNKNOWN — it just
        returns a smaller, older number. The count itself cannot reveal that; a snapshot minutes
        before the emptying is the store as it stood, one eleven hours before is a different day's
        store, and both are "a backup predating the loss". [[zero-needs-a-denominator]]"""
        now = self.PINNED_NOW
        # the degraded case: only an OLD keeper survives, hours before the loss
        pp = os.path.join(self.d, "ledger_keeper.json")
        with io.open(pp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"counts": {"foundLog": 400, "setPieces": 120}, "allStores": {}}))
        os.utime(pp, (now - 12 * 3600.0, now - 12 * 3600.0))
        got, why = CA.ledger_counts_before(now * 1000.0, bdir=self.d)
        self.assertIsInstance(got, dict, "no predating backup found: %s" % why)
        self.assertIn("before the loss", why,
                      "the answer does not say how close the snapshot was: %r" % why)
        self.assertIn("UNDERSTATED", why,
                      "a denominator 12h before the loss was reported without qualification, so a "
                      "degraded keeper reads exactly like the true before-picture: %r" % why)

    def test_a_CLOSE_denominator_is_not_dressed_as_suspect(self):
        """⚠ THE OTHER SIDE. A snapshot minutes before the loss IS the store as it stood, and
        qualifying it would train the reader to ignore the warning that matters."""
        now = self.PINNED_NOW
        pp = os.path.join(self.d, "ledger_close.json")
        with io.open(pp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"counts": {"foundLog": 445, "setPieces": 129}, "allStores": {}}))
        os.utime(pp, (now - 600.0, now - 600.0))          # ten minutes before
        got, why = CA.ledger_counts_before(now * 1000.0, bdir=self.d)
        self.assertIsInstance(got, dict, why)
        self.assertIn("min before the loss", why, "a close snapshot does not state its gap: %r" % why)
        self.assertNotIn("UNDERSTATED", why,
                         "a snapshot 10 minutes before the loss was flagged as understating, which "
                         "makes the real warning noise: %r" % why)

    def test_an_unusable_timestamp_is_UNKNOWN_not_an_exception(self):
        """⚠ v3032 — the contract says '(dict|None, why)'. getmtime and float() sat OUTSIDE the
        try, so a file deleted between the glob and the compare, or an at_ms that will not parse,
        raised straight out of a function every caller reads as total. A helper whose failure mode
        is an exception is one every caller must wrap."""
        got, why = CA.ledger_counts_before("not a number", bdir=self.d)
        self.assertIsNone(got)
        self.assertIn("UNKNOWN", why, "an unparseable timestamp did not report UNKNOWN: %r" % why)

    def test_a_backup_NEWER_than_the_loss_is_never_used_as_the_before(self):
        """⚠ A snapshot taken AFTER the store emptied holds the EMPTIED state. Using it would make
        'you had almost nothing' the denominator, and any recovery would look total."""
        now = self.PINNED_NOW
        pp = os.path.join(self.d, "ledger_after.json")
        with io.open(pp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"counts": {"foundLog": 1, "setPieces": 0}, "allStores": {}}))
        os.utime(pp, (now - 1 * DAY, now - 1 * DAY))
        loss_at = (now - 3 * DAY) * 1000.0          # the loss PREDATES the only snapshot
        got, why = CA.ledger_counts_before(loss_at, bdir=self.d)
        self.assertIsNone(got,
                          "a backup NEWER than the loss was used as the before-picture (%r) — the "
                          "emptied state would become the denominator" % (got,))
        self.assertIn("UNKNOWN", why, "the refusal must say UNKNOWN, not imply an empty store: %r" % why)

    def test_a_backup_with_NO_counts_is_UNKNOWN_not_an_empty_store(self):
        """⚠ 'I cannot say what you had' must never render as 'you had nothing'."""
        now = self.PINNED_NOW
        pp = os.path.join(self.d, "ledger_nocounts.json")
        with io.open(pp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"allStores": {}}))
        os.utime(pp, (now - 4 * DAY, now - 4 * DAY))
        got, why = CA.ledger_counts_before((now - 1 * DAY) * 1000.0, bdir=self.d)
        self.assertIsNone(got, "a countless backup produced a counts dict: %r" % (got,))
        self.assertIn("UNKNOWN", why)

    def test_the_failsafe_cap_can_never_bind_before_the_policy(self):
        """⚠⚠ THE DEFECT THIS FILE EXISTED THROUGH. v3009 shipped a 48h + 90-day retention policy
        that was DEAD ON ARRIVAL: a 60-file count cap inside `_ledger_snapshot_once` ran on every
        write, before the prune, deleting oldest-first. Measured on his live dir: 60 files spanning
        20.8 HOURS against a policy advertising 48h + 90 days.

        This pins the RELATIONSHIP, not the number — raising the write cadence is exactly what
        broke it in v2050 (1800s -> 600s), and a law pinned to `60` or to `2000` would have gone on
        passing. [[regression-guard]] [[feedback-threshold-above-the-ceiling]]"""
        rolling_needs = CA._LEDGER_ROLLING_S / CA._LEDGER_MIN_CADENCE_S
        keeper_needs = CA._LEDGER_KEEPER_S / 86400.0
        need = rolling_needs + keeper_needs
        self.assertGreater(
            CA._LEDGER_BACKUP_KEEP, need,
            "the failsafe cap (%d) is at or below what the POLICY itself needs (%.0f = %.0f "
            "rolling snapshots at the %.0fs cadence floor + %.0f daily keepers). The cap will "
            "delete what the policy promised to keep, and the prune will never see those files."
            % (CA._LEDGER_BACKUP_KEEP, need, rolling_needs, CA._LEDGER_MIN_CADENCE_S, keeper_needs))

    def test_the_guard_reads_the_shape_the_writer_actually_writes(self):
        """⚠⚠ THE BLIND FIXTURE, MADE INTO ITS OWN LAW.

        The open-episode guard read `doc.get("d2r_storeEmptied")` at the TOP LEVEL for its whole
        life. `_ledger_snapshot_once` nests every store key under "allStores". MEASURED on a real
        snapshot: top-level keys are ['allStores','counts','ledger','route','source','takenAt'] and
        the top-level lookup is None, while allStores["d2r_storeEmptied"] carries the episode. The
        guard that protects the one backup predating an OPEN loss had never once engaged.

        Twenty laws and nine red-proofs stayed green because the fixture INVENTED a top-level dict
        the writer never produces. So this law does not hand-write the shape: it PARSES the
        writer's own `json.dump` dict literal and builds the fixture from those keys. Change the
        writer's nesting and this goes red rather than drifting quietly.
        [[feedback-blind-fixture-green-gate]] [[source-reading-guard]]"""
        import ast as _ast
        src = io.open(os.path.join(os.path.dirname(os.path.abspath(CA.__file__)),
                                   "control_app.py"), encoding="utf-8").read()
        keys = None
        for fn in _ast.walk(_ast.parse(src)):
            if isinstance(fn, _ast.FunctionDef) and fn.name == "_ledger_snapshot_once":
                for node in _ast.walk(fn):
                    if (isinstance(node, _ast.Call) and isinstance(node.func, _ast.Attribute)
                            and node.func.attr == "dump" and node.args
                            and isinstance(node.args[0], _ast.Dict)):
                        keys = [k.value for k in node.args[0].keys
                                if isinstance(k, _ast.Constant)]
        self.assertIsNotNone(
            keys, "could not PARSE the writer's json.dump dict — this law cannot derive the shape "
                  "it is supposed to pin, so it must fail rather than assume one")
        self.assertIn("allStores", keys,
                      "the writer no longer nests stores under 'allStores' (keys now %s); the "
                      "guard's lookup must be updated to match" % sorted(keys))

        # build the fixture from the PARSED keys, with the episode where the writer puts it —
        # nested, and JSON-ENCODED, because allStores values are serialised strings not dicts
        loss_at = (self.now - 7 * DAY) * 1000.0
        episode = {"at": loss_at, "why": "measured", "restore": "..."}   # OPEN: no recoveredAt
        for name, age in (("ledger_predates.json", 10 * DAY), ("ledger_after.json", 5 * DAY)):
            body = dict((k, None) for k in keys)
            body["allStores"] = {"d2r_storeEmptied": json.dumps(episode)}
            body["counts"] = {}
            pp = os.path.join(self.d, name)
            with io.open(pp, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(body))
            os.utime(pp, (self.now - age, self.now - age))

        r = CA._ledger_backup_prune(self.d, now=self.now)
        self.assertEqual(
            r.get("protected"), "ledger_predates.json",
            "the guard did not find an OPEN episode written in the writer's own shape — it "
            "protected %r. The one backup that answers 'which predates the loss' is deletable."
            % (r.get("protected"),))
        self.assertTrue(os.path.exists(os.path.join(self.d, "ledger_predates.json")),
                        "the predating backup was DELETED while a loss was open")

    def test_an_empty_dir_is_measured_empty_not_an_error(self):
        r = CA._ledger_backup_prune(self.d, now=self.now)
        self.assertEqual(r["pruned"], 0)
        self.assertIn("measured-empty", r["why"])

    def test_a_missing_dir_deletes_nothing_and_says_so(self):
        r = CA._ledger_backup_prune(os.path.join(self.d, "nope"), now=self.now)
        self.assertEqual(r["pruned"], 0)
        self.assertIn("nothing measured", r["why"])


RED_PROOF = [
    {
        #: ⚠ WITHOUT THE GAP the denominator degrades in silence: a keeper hours older than the
        #: loss answers exactly like the true newest-before, and "440 of 400" reads as a complete
        #: recovery.
        "why": "dropping the distance-from-the-loss qualifier lets a degraded older keeper stand "
               "in for the true before-picture with nothing on screen to say so",
        "file": "control_app.py",
        "find": "                  \"\" if _gap_s < 7200 else",
        "replace": "                  \"\" if True else",
        "matches": 1,
    },
    {
        #: ⚠ TAKING THE OLDEST PREDATING BACKUP INSTEAD OF THE NEWEST understates what was lost and
        #: flatters the recovery — the direction that must never be allowed to be wrong.
        "why": "using the oldest snapshot before the loss as the before-picture makes the store "
               "look smaller than it was, so a partial recovery reads as a complete one",
        "file": "control_app.py",
        "find": "    newest = max(older, key=os.path.getmtime)",
        "replace": "    newest = min(older, key=os.path.getmtime)",
        "matches": 1,
    },
    {
        #: ⚠ DROPPING THE PREDATES TEST lets a snapshot taken AFTER the emptying become the
        #: denominator, so "you had almost nothing" and every recovery looks total.
        "why": "comparing against snapshots newer than the loss makes the EMPTIED state the "
               "before-picture, and any recovery then looks complete",
        "file": "control_app.py",
        #: ⚠ v3032 — RE-ANCHORED. v3032 moved this line INSIDE the try (so a file deleted between
        #: the glob and the compare answers UNKNOWN instead of raising) and renamed float(at_ms) to
        #: _at, which left this proof matching 0 and measuring INVALID on the very next drill. The
        #: law was never wrong; the sabotage pointed at bytes that had moved.
        "find": "        older = [x for x in snaps if os.path.getmtime(x) * 1000.0 < _at]",
        "replace": "        older = list(snaps)",
        "matches": 1,
    },
    {
        "why": "dropping the keeper branch deletes every daily save past 48h — the exact 'noticed "
               "days late with no predating backup' failure the policy exists to end",
        "file": "control_app.py",
        "find": "        if pp in keepers and age <= KEEPER_S:",
        "replace": "        if False:",
        "matches": 1,
    },
    {
        "why": "dropping the episode guard lets the prune eat the one backup that answers 'which "
               "backup predates the loss' while the loss is still open",
        "file": "control_app.py",
        "find": "        if isinstance(ev, dict) and ev.get(\"at\") and not ev.get(\"recoveredAt\"):",
        "replace": "        if False:",
        "matches": 1,
    },
    {
        "why": "a zero rolling window prunes snapshots minutes old — the corpus can no longer "
               "answer even a same-day question",
        "file": "control_app.py",
        #: ⚠ v3015 — RE-ANCHORED. This pointed at the local `ROLLING_S = 48 * 3600.0`, which v3015
        #: replaced with a read of the module constant. The proof matched 0 the moment the refactor
        #: landed and would have reported INVALID on the next census. Anchored to the policy
        #: constant itself now, which is where the number actually lives.
        "find": "_LEDGER_ROLLING_S = 48 * 3600.0",
        "replace": "_LEDGER_ROLLING_S = 0.0",
        "matches": 1,
    },
    {
        #: ⚠ THIS PROOF EXISTS BECAUSE THE HOUR-SWEEP LAW WAS BLIND TO IT. Bucketing every file
        #: under TODAY keeps one global oldest instead of one per day, so every older day loses its
        #: keeper — the 90-day corpus silently collapses to a single file. With a one-day fixture
        #: the broken and correct policies returned the IDENTICAL (1, 1, True); it took a two-day
        #: fixture to separate them. Measured tampered: (3, 1, True, False).
        "why": "keying the day bucket off `now` instead of each file's own mtime collapses the "
               "whole corpus into one bucket — every day but the newest loses its keeper",
        "file": "control_app.py",
        "find": '        d = _dt.datetime.utcfromtimestamp(os.path.getmtime(pp)).strftime("%Y-%m-%d")',
        "replace": '        d = _dt.datetime.utcfromtimestamp(now).strftime("%Y-%m-%d")',
        "matches": 1,
    },
    {
        #: ⚠ THE REAL DEFECT, RESTORED. 60 was the shipped value and it strangled the whole v3009
        #: policy for its entire life — measured 20.8h of history against a 48h + 90-day promise.
        "why": "putting the count cap back under what the policy needs makes the cap the deleter "
               "again; the retention prune never sees the files it promised to keep",
        "file": "control_app.py",
        "find": "_LEDGER_BACKUP_KEEP = 2000",
        "replace": "_LEDGER_BACKUP_KEEP = 60",
        "matches": 1,
    },
    {
        #: ⚠ THE BLIND LOOKUP, RESTORED. Deleting the nested read returns the guard to reading only
        #: the top level — where a real snapshot never carries the episode.
        "why": "without the allStores lookup the open-episode guard reads a level the writer never "
               "writes to, and the one backup predating an OPEN loss becomes deletable",
        "file": "control_app.py",
        "find": '            _al = doc.get("allStores")',
        "replace": '            _al = None',
        "matches": 1,
    },
]

if __name__ == "__main__":
    try:
        from console_safe import enable
        enable()
    except Exception:
        pass
    unittest.main(verbosity=2)
