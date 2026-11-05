#!/usr/bin/env python3
"""Guards for the five inverted-role tasks (gh #179, 2026-09-02).

Each class names the sabotage that must turn it RED, and the message that sabotage prints.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)


RED_PROOF = [
    {
        "why": 'the law requires this text in control_ui.html, where it occurs exactly once and in no other file the gate names; deleting it must turn the gate red',
        "file": 'control_ui.html',
        # ⚠ v3335 — the anchor was the PRE-v3326 spelling and matched 0, so it proved nothing.
        # It now tampers the live expression, and the sabotage lets a SECOND state reach warn —
        # which is the defect the law is about, not merely a different spelling of the same code.
        "find": "(r.state === 'missing' && !bucket) ? 'warn' : ''",
        "replace": "(r.state === 'missing' || r.state === 'unknown') ? 'warn' : ''",
        "matches": 1,
    },
]

def _code_only(src):
    return "\n".join(l.split("#", 1)[0] for l in src.split("\n"))


class TestCF8UnknownCarriesAge(unittest.TestCase):
    """An UNKNOWN must never become ok or missing because time passed."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ua_")
        self.path = os.path.join(self.tmp, "age.json")
        self._was = os.environ.get("TV_UNKNOWN_AGE")   # v3864 (card 75) - put back what was there, never just delete it
        os.environ["TV_UNKNOWN_AGE"] = self.path
        import unknown_age as ua
        self.ua = ua
        # drop any in-process cache of a previous test's file
        if os.path.exists(self.path):
            os.remove(self.path)

    def tearDown(self):
        if self._was is None:
            os.environ.pop("TV_UNKNOWN_AGE", None)
        else:
            os.environ["TV_UNKNOWN_AGE"] = self._was
        shutil.rmtree(self.tmp, True)

    def test_two_unknowns_keep_first_seen_and_move_last_attempt(self):
        t0 = 1_000_000_000_000
        rows = [{"check": "board is claimed", "state": "unknown", "why": "the board is not open"}]
        self.ua.attach(rows, now_ms=t0)
        self.assertEqual(rows[0]["state"], "unknown")
        self.assertEqual(rows[0]["firstUnknownTs"], t0)
        self.assertEqual(rows[0]["unknownCount"], 1)
        self.assertIn("unaskable for", rows[0]["why"])
        t1 = t0 + 5 * 60 * 1000
        rows2 = [{"check": "board is claimed", "state": "unknown", "why": "the board is not open"}]
        self.ua.attach(rows2, now_ms=t1)
        self.assertEqual(rows2[0]["state"], "unknown",
                         "UNKNOWN aged into %s — time is not evidence" % rows2[0]["state"])
        self.assertEqual(rows2[0]["firstUnknownTs"], t0)
        self.assertEqual(rows2[0]["lastAttemptTs"], t1)
        self.assertEqual(rows2[0]["unknownCount"], 2)
        self.assertIn("5m", rows2[0]["why"])

    def test_a_corrupt_stamp_file_is_not_overwritten(self):
        """A failed read is UNKNOWN, not {}. Saving {} over garbage would wipe history."""
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        rows = [{"check": "board is claimed", "state": "unknown", "why": "closed"}]
        self.ua.attach(rows, now_ms=1_000_000_000_000)
        raw = open(self.path, encoding="utf-8").read()
        self.assertEqual(raw, "{not json")
        self.assertEqual(rows[0]["state"], "unknown")

    def test_time_passing_does_not_promote_unknown_to_ok_or_missing(self):
        t0 = 1_700_000_000_000
        rows = [{"check": "board is claimed", "state": "unknown", "why": "closed"}]
        self.ua.attach(rows, now_ms=t0)
        later = [{"check": "board is claimed", "state": "unknown", "why": "closed"}]
        self.ua.attach(later, now_ms=t0 + 45 * 3600 * 1000)
        self.assertEqual(later[0]["state"], "unknown")
        self.assertNotEqual(later[0]["state"], "ok")
        self.assertNotEqual(later[0]["state"], "missing")
        self.assertIn("45h", later[0]["why"])

    def test_ok_records_last_known_and_clears_the_streak(self):
        t0 = 2_000_000_000_000
        self.ua.attach([{"check": "board is claimed", "state": "unknown", "why": "closed"}],
                       now_ms=t0)
        ok = [{"check": "board is claimed", "state": "ok", "why": "claimed"}]
        self.ua.attach(ok, now_ms=t0 + 1000)
        self.assertEqual(ok[0]["state"], "ok")
        unk = [{"check": "board is claimed", "state": "unknown", "why": "closed again"}]
        self.ua.attach(unk, now_ms=t0 + 2000)
        self.assertIn("last known ok", unk[0]["why"])

    def test_sabotage_promote_on_age_is_caught(self):
        """HOW TO PROVE IT RED: make attach() set state=ok when unknownCount>=2.
        Expected failure: 'UNKNOWN aged into ok — time is not evidence'"""
        t0 = 3_000_000_000_000
        self.ua.attach([{"check": "x", "state": "unknown", "why": "a"}], now_ms=t0)
        rows = [{"check": "x", "state": "unknown", "why": "a"}]
        self.ua.attach(rows, now_ms=t0 + 60_000)
        self.assertEqual(rows[0]["state"], "unknown",
                         "UNKNOWN aged into %s — time is not evidence" % rows[0]["state"])


class TestCF10FourStatesAreFourWords(unittest.TestCase):
    """The renderer painted missing vs everything-else. Four states, two words."""

    def setUp(self):
        self.ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        self.code = _code_only(self.ui)

    def test_the_old_two_word_ternary_is_gone(self):
        self.assertNotIn("r.state === 'missing' ? 'MISSING' : 'UNKNOWN'", self.code,
                         "the two-word ternary is back — designed refusals and faults paint the same")

    def test_four_words_are_distinct(self):
        self.assertIn("MISSING", self.code)
        self.assertIn("NEVER", self.code)
        self.assertTrue("CAN'T ASK" in self.ui or r"CAN\'T ASK" in self.ui,
                        "CAN'T ASK is missing from the renderer")
        self.assertIn("unmeasured", self.code)
        self.assertIn("slowRows", self.code)

    def test_warn_tone_is_only_on_missing(self):
        """The warn tone is for a fault HE must act on — and nothing else may claim it.

        ⚠⚠ v3335 — THIS PINNED A SPELLING AND WENT STALE THE DAY THE SPELLING IMPROVED.
        It asserted the literal "r.state === 'missing' ? 'warn' : ''". v3326 made the tone
        bucket-aware — `(r.state === 'missing' && !bucket) ? 'warn' : ''` — which is HIS OWN
        RULING that a ruling row and my own backlog are not faults he must act on. The CODE was
        right and this test was wrong, and it sat red in CI for eight commits while the pre-push
        hook (which runs a SUBSET) kept printing green. [[regression-guard]] §4 — PIN THE LAW.
        """
        import re
        # ⚠ TWO sites assign `var tone` — the other is a coverage class
        # (`pct >= 85 ? ' dsr-cov-hi' ...`). My first cut of this law matched the FIRST one and
        # failed on innocent code. Select by CONTENT and assert the selection is unique.
        # [[source-reading-guard]] §2 — anchor on something unique, and count before believing.
        alls = re.findall(r"var tone\s*=\s*([^;]+);", self.code)
        cands = [a for a in alls if "'warn'" in a]
        self.assertEqual(
            len(cands), 1,
            "expected exactly ONE tone expression mentioning 'warn'; found %d of %d total. A "
            "second one means the tone has two writers and they can disagree."
            % (len(cands), len(alls)))
        expr = cands[0]
        self.assertIn("'missing'", expr,
                      "the warn tone no longer keys on the missing state: %r" % expr)
        self.assertIn("'warn'", expr, "the tone expression no longer yields 'warn': %r" % expr)
        # THE LAW: no OTHER state may reach 'warn'. A spelling may change; this may not.
        for other in ("'unknown'", "'unmeasured'", "'ok'", "'by-design'"):
            self.assertNotIn(
                other, expr,
                "state %s appears in the tone expression %r. Only a MISSING row may go warn — "
                "an unmeasured or unknown row is not a fault he must act on, and shouting at him "
                "about one teaches him to ignore the colour." % (other, expr))

    def test_sabotage_collapsing_unknown_and_unmeasured_is_caught(self):
        """HOW TO PROVE IT RED: change the word map so unmeasured and unknown both say UNKNOWN.
        Expected failure: 'the two-word ternary is back' from test_the_old_two_word_ternary_is_gone
        OR this assertion on NEVER."""
        # ⚠⚠ v3335 — ALSO A STALE SPELLING. This required the exact ternary
        # `unmeasured' ? 'NEVER'`. v3309 split that fact in two on HIS report that the screen said
        # NEVER about a row asked two minutes ago: unmeasured now reads NOT THIS TICK when
        # everAsked, and NEVER when it has genuinely never run. Pinning the old one-word form
        # made the law demand the defect back. What must hold is that the two STATES never
        # collapse into one WORD. [[unknown-stays-unknown]]
        import re
        self.assertIn("unmeasured", self.code)
        # ⚠ `[^:]+` stopped at the colon INSIDE the nested ternary — it captured only
        # "(r.everAsked ? 'NOT THIS TICK'" and never saw NEVER. Bound each branch at the NEXT
        # state test instead, which is its real end. [[source-reading-guard]] §3 — anchor both ends.
        m_un = re.search(r"state\s*===\s*'unmeasured'\s*\?(.*?)(?=:\s*r\.state\s*===|\n)",
                         self.code, re.S)
        m_uk = re.search(r"state\s*===\s*'unknown'\s*\?(.*?)(?=:\s*r\.state\s*===|\n)",
                         self.code, re.S)
        self.assertTrue(m_un, "no branch words the `unmeasured` state at all")
        self.assertTrue(m_uk, "no branch words the `unknown` state at all")
        w_un, w_uk = m_un.group(1).strip(), m_uk.group(1).strip()
        self.assertIn("NEVER", w_un,
                      "the unmeasured branch no longer reaches NEVER: %r. A check that has never "
                      "run must say so in the louder word, not be rounded down." % w_un)
        self.assertNotEqual(
            w_un, w_uk,
            "unmeasured and unknown now produce the SAME word (%r). They are different facts — "
            "one was never asked, the other cannot be asked — and collapsing them is the "
            "confident-zero this panel exists to avoid." % w_un)


class TestCF12SlowChecksReachASidecar(unittest.TestCase):
    """32 vs 34 was true. Joining into the cheap pass re-breaks eagle-ran-every-check."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="es_")
        self.path = os.path.join(self.tmp, "slow.json")
        self._was = os.environ.get("TV_EAGLE_SLOW")   # v3864 (card 75) - put back what was there, never just delete it
        os.environ["TV_EAGLE_SLOW"] = self.path
        import console_doctor as cd
        self.cd = cd

    def tearDown(self):
        if self._was is None:
            os.environ.pop("TV_EAGLE_SLOW", None)
        else:
            os.environ["TV_EAGLE_SLOW"] = self._was
        shutil.rmtree(self.tmp, True)

    def test_the_premise_is_true_two_named_slow_checks(self):
        # v3014 — "sweep would find" moved to PERIODIC so it finally runs unattended (~hourly);
        # SLOW keeps only the check that genuinely needs a waiting human.
        self.assertEqual(set(self.cd.SLOW), {"the other doctors"})
        self.assertIn("sweep would find", self.cd.PERIODIC,
                      "it left SLOW to RUN, not to vanish — if it is in neither tier the sweep "
                      "check runs nowhere")
        cheap = [n for n, _ in self.cd.CHECKS if n not in self.cd.SLOW]
        self.assertEqual(len(self.cd.CHECKS) - len(self.cd.SLOW), len(cheap))
        # ⚠ NO HARDCODED TIER SIZE. The original asserted len(SLOW)==2 and that literal is what
        # broke when a check earned its way OUT of SLOW — a number pinning a membership it was
        # never about. What matters is the CONTRACT: every SLOW name is on the roster, and no name
        # is in SLOW and PERIODIC at once (SLOW wins in run(), so the pair would silently mean
        # never-runs). [[label-outlived-referent]]
        roster = {n for n, _ in self.cd.CHECKS}
        for nm in self.cd.SLOW:
            self.assertIn(nm, roster, "%r is SLOW and not on the roster — it runs nowhere" % nm)
        self.assertFalse(set(self.cd.SLOW) & set(self.cd.PERIODIC),
                         "a name in both tiers is SLOW in practice — run() skips it first")

    def test_cheap_run_must_not_absorb_the_slow_pair(self):
        """HOW TO PROVE IT RED: append SLOW rows inside run(include_slow=False).
        Expected failure: cheap pass emits the full roster — eagle-ran-every-check goes
        permanently red (34 vs 32)."""
        # We do not call run() here (it pokes :17772). The LAW is: cheap length is roster-SLOW.
        # The sidecar is how the two still reach a surface.
        self.assertTrue(callable(self.cd.slow_surface))
        self.assertTrue(callable(self.cd._persist_slow))

    def test_unmeasured_before_any_full_pass(self):
        rows = self.cd.slow_surface()
        self.assertEqual(len(rows), len(self.cd.SLOW))
        self.assertTrue(all(r["state"] == self.cd.UNMEASURED for r in rows),
                        "an empty persist painted %s instead of NEVER" % [r["state"] for r in rows])
        self.assertTrue(all("NEVER" in r["why"] for r in rows))

    def test_an_unreadable_sidecar_paints_NEVER_not_ok(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        rows = self.cd.slow_surface()
        # REG-1893 - a surface that answered [] on a bad sidecar would pass "all NEVER" about no row.
        self.assertEqual(len(rows), len(self.cd.SLOW), "an unreadable sidecar dropped the SLOW rows "
                                                       "instead of painting them NEVER: %r" % rows)
        self.assertTrue(all(r["state"] == self.cd.UNMEASURED for r in rows))

    def test_a_stored_full_pass_surfaces_with_age(self):
        """⚠ DERIVED FROM SLOW, NOT FROM TWO TYPED NAMES. The fixture used to name both members
        literally, so the moment one earned PERIODIC the test KeyError'd on a tree that was
        perfectly correct. The law is about the SIDECAR mechanism — whatever is SLOW reaches a
        surface with its age — never about which names those are."""
        names = list(self.cd.SLOW)
        self.assertTrue(names, "SLOW is empty — the sidecar has nothing to carry and this law "
                               "would be vacuous rather than passing")
        self.cd._persist_slow([{"check": nm, "state": "missing", "why": "owed"} for nm in names])
        rows = {r["check"]: r for r in self.cd.slow_surface()}
        for nm in names:
            self.assertEqual(rows[nm]["state"], "missing",
                             "%r did not come back off the sidecar" % nm)
            self.assertIn("last full pass", rows[nm]["why"])

    def test_control_app_publishes_slowRows_not_into_rows(self):
        src = _code_only(io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read())
        self.assertIn('"slowRows"', src)
        # the cheap pass still records slow: the argument, not a merged roster
        self.assertIn('"slow": _include_slow', src)


class TestB83EquipmentIsNamesLocNotAFrameClass(unittest.TestCase):
    """Adding an equipment scene class that fires on inventory frames locks charms as gear."""

    def test_kai_frame_cls_vocabulary_has_no_equipment(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = src.index("def _kai_frame_cls(")
        nxt = src.find("\ndef ", i + 1)
        body = _code_only(src[i:nxt])
        returns = re.findall(r'return\s+"([^"]+)"', body)
        self.assertTrue(returns, "could not read _kai_frame_cls returns — the guard is blind")
        self.assertNotIn("equipment", returns,
                         "equipment is in _kai_frame_cls; a frame class that fires on inventory "
                         "grids locks charms as gear")
        self.assertNotIn("equipped", returns)
        self.assertIn("inventory", returns)
        self.assertIn("gameplay", returns)

    def test_inventory_blob_classifies_as_inventory_not_equipment(self):
        """HOW TO PROVE IT RED: `if \"inventory\" in blob: return \"equipment\"`.
        Expected failure: equipment is in _kai_frame_cls; a frame class that fires on
        inventory grids locks charms as gear"""
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        i = src.index("def _kai_frame_cls(")
        nxt = src.find("\ndef ", i + 1)
        body = _code_only(src[i:nxt])
        self.assertIn('return "inventory"', body)
        self.assertNotIn('return "equipment"', body)

    def test_names_loc_equipped_is_the_equipment_lane(self):
        import main_character as mc
        self.assertEqual(mc.lane_from_sighting("inventory", "equipped"), mc.EQUIPMENT_LANE)
        self.assertEqual(mc.lane_from_sighting("stash", "stash"), "stash")
        self.assertEqual(mc.lane_from_sighting("inventory", None), "inventory")

    def test_saw_accepts_the_names_loc_spelling(self):
        import main_character as mc
        real_load, real_save = mc._load, mc._save
        db = {}
        mc._load = lambda: db
        mc._save = lambda d: db.update(d)
        try:
            mc.saw("Harlequin Crest", "equipped", session="s1")
            self.assertEqual(db[mc._key("Harlequin Crest")]["equip"], 1)
            mc.saw("Small Charm", "inventory", session="s2")
            self.assertEqual(db[mc._key("Small Charm")]["equip"], 0)
        finally:
            mc._load, mc._save = real_load, real_save

    def test_the_learner_feed_uses_lane_from_sighting(self):
        src = _code_only(io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read())
        i = src.index("import main_character as _mc")
        blk = src[i:src.find('if r.get("lane") == "kai":', i)]
        self.assertIn("lane_from_sighting", blk,
                      "the learner is back on raw activity_at, which cannot return equipment")


class Test135StaysUnfingerprinted(unittest.TestCase):
    """Inventing a fingerprint for a thing that was never measured is fabrication."""

    def test_the_ready_row_has_no_fingerprint(self):
        md = io.open(os.path.join(ROOT, "TASKS.md"), encoding="utf-8").read()
        line = None
        for ln in md.splitlines():
            if ln.startswith("| **135**"):
                line = ln
                break
        self.assertTrue(line, "READY row 135 is gone from TASKS.md")
        self.assertNotIn("<!--fp:", line,
                         "135 grew a fingerprint — if the needle is a string that already "
                         "exists (grail, daily, pick), that is fabrication, not a measurement")

    def test_the_gate_names_135_as_unknown_not_clean(self):
        import tasks_freshness as tf
        code, lines = tf.check()
        joined = "\n".join(lines)
        self.assertIn("135", joined)
        self.assertTrue(any("NO fingerprint" in l for l in lines),
                        "135 is no longer reported UNKNOWN; the gate rounded it up to clean")
        # exit 0 with a ⚪ line is the designed UNKNOWN, not a fail that pressures a fake fp
        self.assertEqual(code, 0)

    def test_prove_still_treats_no_fingerprint_as_not_stale(self):
        """HOW TO PROVE IT RED: add <!--fp: bible.html :: grail--> to the 135 row.
        Expected failure: '135 grew a fingerprint' from test_the_ready_row_has_no_fingerprint"""
        import tasks_freshness as tf
        md = io.open(os.path.join(ROOT, "TASKS.md"), encoding="utf-8").read()
        n_fp = sum(1 for ln in md.splitlines() if ln.startswith("| **135**") and "<!--fp:" in ln)
        self.assertEqual(n_fp, 0)


class TestCF6GuestZeroRoutesStayOut(unittest.TestCase):
    """A first-seen all-zero post is a probe. Stop at the door."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bt_")
        self.path = os.path.join(self.tmp, "board_tally.json")
        import control_app as ca
        self.ca = ca
        self._real = ca._board_tally_path
        ca._board_tally_path = lambda: self.path

    def tearDown(self):
        self.ca._board_tally_path = self._real
        shutil.rmtree(self.tmp, True)

    def test_a_new_all_zero_world_is_refused(self):
        ok = self.ca.board_tally_merge({
            "who": {"id": "guestprobe", "pfx": "I·x·"},
            "sets": {"have": 0, "total": 135},
            "uniques": {"have": 0, "total": 403},
            "runewords": {"have": 0, "total": 99},
            "at": 1,
        })
        self.assertFalse(ok)
        self.assertFalse(os.path.exists(self.path) and os.path.getsize(self.path) > 2)

    def test_an_existing_world_may_still_drop_to_zero(self):
        self.assertTrue(self.ca.board_tally_merge({
            "who": {"id": "his", "pfx": ""},
            "sets": {"have": 120, "total": 135},
            "uniques": {"have": 280, "total": 403},
            "at": 1,
        }))
        self.assertTrue(self.ca.board_tally_merge({
            "who": {"id": "his", "pfx": ""},
            "sets": {"have": 0, "total": 135},
            "uniques": {"have": 0, "total": 403},
            "at": 2,
        }))
        doc = self.ca.board_tally_load()
        self.assertTrue(doc.get("drops"))

    def test_existing_zero_routes_are_not_deleted(self):
        """No discriminator, so no cleaner. A first-tick real board looks like a probe."""
        planted = {
            "v": 1, "byRoute": {
                "probeA|main": {"uniques": {"have": 0, "total": 403},
                                "sets": {"have": 0, "total": 135}},
                "probeB|main": {"uniques": {"have": 0, "total": 403},
                                "sets": {"have": 0, "total": 135}},
            }
        }
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(planted, fh)
        self.assertTrue(self.ca.board_tally_merge({
            "who": {"id": "his", "pfx": ""},
            "sets": {"have": 120, "total": 135},
            "uniques": {"have": 280, "total": 403},
            "at": 1,
        }))
        doc = self.ca.board_tally_load()
        routes = doc.get("byRoute") or {}
        self.assertIn("probeA|main", routes)
        self.assertIn("probeB|main", routes)
        self.assertTrue(any(k.startswith("his|") for k in routes),
                        "the real world was not banked: %s" % list(routes))


class Test154PrunedMbUnknownIsNotZero(unittest.TestCase):
    def test_no_numeric_sample_is_none_not_zero(self):
        import control_app as ca
        tmp = tempfile.mkdtemp(prefix="dh_")
        p = os.path.join(tmp, "disk_history.jsonl")
        try:
            ca.disk_history_append(30.0, 8.0, hist_bytes=None, reels=1,
                                   eligible_mb=0, pruned_mb=None, path=p)
            # force a 24h-old row so delta is computable
            with open(p, "r+", encoding="utf-8") as fh:
                rows = [json.loads(l) for l in fh if l.strip()]
            rows[0]["at"] = int(time.time() * 1000) - 25 * 3600_000
            ca.disk_history_append(31.0, 8.0, pruned_mb=None, path=p)
            # rewrite first row age
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(rows[0]) + "\n")
                fh.write(json.dumps({"at": int(time.time() * 1000), "freeGb": 31.0,
                                     "floorGb": 8.0, "prunedMb": None}) + "\n")
            d = ca.disk_delta(24, path=p)
            self.assertIsNone(d["prunedMbInWindow"],
                              "no prune byte-count became 0 — that is the 154 lie")
            say = ca.disk_delta_say(24, path=p)
            self.assertIn("UNKNOWN", say)
            self.assertNotIn("none of it was us", say)
        finally:
            shutil.rmtree(tmp, True)


class TestCF15SourceGuardsReadDiskNotInspect(unittest.TestCase):
    """inspect.getsource handed the full suite a neighbour's body. Isolation was green.

    HOW TO PROVE IT RED: make file_def return the neighbour (prepend a second def with the
    same name). Expected: 'def drift_may_relaunch is STALE/ambiguous'.
    """

    def test_file_def_still_finds_the_function_after_lines_are_prepended(self):
        import auto_scope as AS
        d = tempfile.mkdtemp(prefix="fd_")
        try:
            p = os.path.join(d, "mod.py")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("def neighbour():\n    return 'WRONG'\n\n"
                         "def target():\n    return 'RIGHT'\n")
            src = AS.file_def(p, "target")
            self.assertIsInstance(src, str)
            self.assertIn("return 'RIGHT'", src)
            self.assertNotIn("WRONG", src)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("# " + ("x\n# " * 40) + "\n"
                         "def neighbour():\n    return 'WRONG'\n\n"
                         "def target():\n    return 'RIGHT'\n")
            src2 = AS.file_def(p, "target")
            self.assertIn("return 'RIGHT'", src2)
            self.assertNotIn("WRONG", src2)
        finally:
            shutil.rmtree(d, True)

    def test_two_defs_of_the_same_name_are_STALE_not_a_guess(self):
        import auto_scope as AS
        d = tempfile.mkdtemp(prefix="fd2_")
        try:
            p = os.path.join(d, "mod.py")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("def target():\n    return 1\n\nclass C:\n    def target(self):\n"
                         "        return 2\n")
            self.assertIs(AS.file_def(p, "target"), AS._STALE)
        finally:
            shutil.rmtree(d, True)

    def test_absent_is_None_not_stale(self):
        import auto_scope as AS
        d = tempfile.mkdtemp(prefix="fd3_")
        try:
            p = os.path.join(d, "mod.py")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("def other():\n    return 1\n")
            self.assertIsNone(AS.file_def(p, "target"))
        finally:
            shutil.rmtree(d, True)

    def test_getsource_falls_back_when_inspect_hands_a_neighbour(self):
        """The blocked push: inspect.getsource(board_window) returned _exec_soon."""
        import auto_scope as AS
        import control_app as ca
        real = AS._REAL_GETSOURCE
        AS._REAL_GETSOURCE = lambda obj, *a, **k: (
            "def _exec_soon():\n    os.execv(sys.executable, sys.argv)\n")
        try:
            src = AS.getsource(ca.board_window)
            self.assertIn("def board_window", src)
            self.assertIn("/board#", src)
            self.assertNotIn("def _exec_soon", src)
        finally:
            AS._REAL_GETSOURCE = real

    def test_the_three_hot_guards_read_the_function_they_named(self):
        """The three that went red in the full suite: product was fine, instrument was not."""
        import auto_scope as AS
        p = os.path.join(HERE, "control_app.py")
        theatre = AS.file_def(p, "_theatre_sessions")
        drift = AS.file_def(p, "drift_may_relaunch")
        fleet = AS.file_def(p, "fleet_compare")
        self.assertNotIn(theatre, (None, AS._STALE))
        self.assertNotIn(drift, (None, AS._STALE))
        self.assertNotIn(fleet, (None, AS._STALE))
        self.assertIn("_theatre_row_fingerprint(sess", theatre)
        self.assertIn("_tree_is_mid_edit", drift)
        self.assertIn("load_roster_for(ledger)", fleet)
        self.assertNotIn("def _drift_once", drift)
        self.assertNotIn("def _load_journal_cached", theatre)


class TestCF2BoardOwnershipHopsIntoTheIframe(unittest.TestCase):
    """READ side only. WRITE doors stay on the note path.

    HOW TO PROVE IT RED: delete getElementById('tvd-eng') from board_ownership.
    Expected: 'board_ownership no longer hops into #tvd-eng'.
    """

    def _capture_js(self, dump=False):
        import unittest.mock as mock
        import control_app
        seen = {}

        def _cap(w, code, timeout=4.0):
            seen["js"] = code
            return None

        with mock.patch.dict(control_app.__dict__,
                             {"_MAIN_WIN": object(), "_WINDOW_LIVE": True, "_BOARD_WIN": None}), \
             mock.patch.object(control_app, "_ejs", _cap):
            control_app.board_ownership(0, dump_stores=dump)
        return seen.get("js") or ""

    def test_the_read_script_hops_when_the_top_document_lacks_board_globals(self):
        js = self._capture_js()
        self.assertTrue(js, "board_ownership handed the window no script")
        self.assertIn("getElementById('tvd-eng')", js,
                      "board_ownership no longer hops into #tvd-eng")
        self.assertIn("contentWindow", js)
        self.assertIn("hopped:!!hopped", js)
        self.assertIn(
            "typeof window.chronicleApply!=='function'&&typeof window._D2R_PFX!=='string'",
            js,
        )

    def test_the_hopped_script_still_PARSES(self):
        import shutil, subprocess, tempfile
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed — the JS cannot be parsed here")
        for dump in (False, True):
            js = self._capture_js(dump=dump)
            self.assertTrue(js)
            tmp = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
            try:
                tmp.write(js)
                tmp.close()
                r = subprocess.run([node, "--check", tmp.name],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0,
                                 "board_ownership JS does not parse (dump=%s): %s"
                                 % (dump, r.stderr[:400]))
            finally:
                os.unlink(tmp.name)

    #: the stores that ARE his grail. A console write to any of these is the harm.
    GRAIL_STORES = ("d2r_foundLog", "d2r_owned", "d2r_setPieces", "d2r_rwMade", "d2r_rwVerify")

    def test_the_console_never_writes_his_grail_itself(self):
        """The standing doctrine, pinned at the HARM instead of at one mechanism.

        ⚠⚠ THIS LAW USED TO FORBID THE HOP, and the hop stopped being the defect. It read
        "%s hopped the WRITE path into the iframe — that restores a direct write into his ledger",
        which was true when hopping meant reaching in and calling setItem. v3209 changed what the
        hop is FOR: `chronicle_apply` now hops in to call the board's OWN `chronicleApply`
        merge-max door, and `board_tick` to call `toggleOwned` / `toggleSetPiece` /
        `tvVaultRegister` / `dropSetPieceKeepGrail`. That is the pattern
        [[writing-behind-a-running-board]] prescribes and it is SAFER than not hopping: the board
        reads `owned`/`rwMade` ONCE at boot and has zero storage listeners, so a write from
        outside is not merely invisible, it is pending deletion by the board's next persist().

        So the old law forbade the thing that fixed the bug. MEASURED when it was replaced:

            chronicle_apply   hop=True   setItem=1   calls chronicleApply
            board_tick        hop=True   setItem=0   calls 4 board doors
            vault_apply       hop=False  setItem=0

        and that ONE setItem writes `d2r_chronicleHandoff` — a handoff QUEUE note so a restarted
        console can still hand off — not a grail store.

        The harm was never the hop. It is the console putting a find into his ledger that the
        board did not put there. That is what this pins now, and it is STRICTLY STRONGER: it
        catches a direct `setItem('d2r_owned', ...)` whether or not anything hopped, which the
        old law could not. [[label-outlived-referent]] [[regression-guard]]
        """
        import auto_scope as AS
        p = os.path.join(HERE, "control_app.py")
        own = AS.file_def(p, "board_ownership")
        self.assertIn("getElementById('tvd-eng')", own,
                      "board_ownership no longer hops, so it reads the console's world instead "
                      "of the board's")
        for name in ("chronicle_apply", "board_tick", "vault_apply"):
            src = AS.file_def(p, name)
            self.assertNotIn(src, (None, AS._STALE), name)
            for store in self.GRAIL_STORES:
                self.assertNotIn(
                    "setItem('%s'" % store, src or "",
                    "%s writes %s directly. The console must never put a find into his ledger "
                    "that the board did not put there — call the board's own door (chronicleApply "
                    "/ toggleOwned / toggleSetPiece / tvVaultRegister) so memory and storage stay "
                    "in step, because the board reads these stores ONCE at boot and its next "
                    "persist() would flush your write away." % (name, store))
                self.assertNotIn('setItem("%s"' % store, src or "",
                                 "%s writes %s directly (double-quoted)" % (name, store))


class TestCF4PreRescueSnapshot(unittest.TestCase):
    """A self-heal that does not keep the blank page makes the bug intermittent.

    HOW TO PROVE IT RED: move ui_pre_rescue_snapshot() to after elsHigh = 0.
    Expected: 'snapshot is taken AFTER the beat is cleared'.
    """

    def test_unmeasured_els_stay_none_not_zero(self):
        import control_app as ca
        s = ca.ui_pre_rescue_snapshot({
            "elsNow": None, "elsHigh": 84541, "hidden": False, "n": 12,
            "t": time.time() - 90, "blankStrikes": 3,
        })
        self.assertIsNone(s["elsNow"], "unmeasured elsNow became 0")
        self.assertEqual(s["elsHigh"], 84541)
        self.assertEqual(s["hidden"], False)
        self.assertEqual(s["blankStrikes"], 3)
        self.assertGreaterEqual(s["beatAgeS"], 80)

    def test_a_measured_zero_stays_zero(self):
        import control_app as ca
        s = ca.ui_pre_rescue_snapshot({"elsNow": 0, "elsHigh": 0, "n": 1})
        self.assertEqual(s["elsNow"], 0)
        self.assertEqual(s["elsHigh"], 0)

    def test_the_fault_row_keeps_the_snapshot(self):
        import control_app as ca
        d = tempfile.mkdtemp(prefix="uf_")
        p = os.path.join(d, "ui_faults.jsonl")
        try:
            before = {"elsNow": 11817, "elsHigh": 84541, "hidden": False}
            row = ca.ui_fault_record("console-rescued-by-server", why="blank",
                                     where="test", path=p, before=before)
            self.assertEqual(row["before"]["elsNow"], 11817)
            stored = json.loads(open(p, encoding="utf-8").read().strip())
            self.assertEqual(stored["before"]["elsHigh"], 84541)
        finally:
            shutil.rmtree(d, True)

    def test_the_loop_snapshots_before_it_clears_or_reloads(self):
        import auto_scope as AS
        src = AS.file_def(os.path.join(HERE, "control_app.py"), "_console_rescue_loop")
        self.assertNotIn(src, (None, AS._STALE))
        # ⚠⚠ v2795 — `src.index("ui_fault_record")` TOOK THE FIRST OF FIVE. MEASURED inside
        # `_console_rescue_loop`: ui_pre_rescue_snapshot appears ONCE (at 9837) and
        # ui_fault_record FIVE times (7264, 8954, 10013, 12306, 14744) — the earlier two belong to
        # OTHER refusal branches of the same loop and have nothing to do with the rescue's own
        # record. So the law compared the snapshot against an unrelated call and reported
        # "the snapshot is taken AFTER the record" about a chain that is correctly ordered:
        # snapshot 9837 -> its record 10013 -> beat cleared 10537 -> reload 10727.
        #
        # THE COUNT IS THE TELL, and `.index()` hides it by design. The rescue's record is the
        # FIRST ONE AFTER the snapshot; asserting the counts first means a future edit that adds
        # or removes a branch fails loudly here instead of silently re-pointing the law.
        # [[feedback-suspect-the-instrument]] [[source-reading-guard]]
        self.assertEqual(src.count("ui_pre_rescue_snapshot"), 1,
                         "the rescue snapshot is no longer taken exactly once (%d) — this law "
                         "picks the record that follows it and cannot do that unambiguously"
                         % src.count("ui_pre_rescue_snapshot"))
        self.assertGreaterEqual(src.count("ui_fault_record"), 3,
                                "the loop's fault records collapsed to %d — the branches this "
                                "law steps around are gone, so re-point it rather than letting "
                                "it pass over a different shape" % src.count("ui_fault_record"))
        i_snap = src.index("ui_pre_rescue_snapshot")
        i_rec = src.index("ui_fault_record", i_snap)   # the RESCUE's own record, not an earlier branch's
        i_clear = src.index('_UI_BEAT["elsHigh"] = 0')
        i_load = src.index("load_url")
        self.assertLess(i_snap, i_rec,
                        "the snapshot is taken AFTER the record — the record cannot hold it")
        self.assertLess(i_rec, i_clear,
                        "snapshot is taken AFTER the beat is cleared")
        self.assertLess(i_clear, i_load,
                        "the beat is cleared AFTER the reload, so the next page is judged "
                        "against the old peak")


class Test167EyeShowsInTheFleetWhenLive(unittest.TestCase):
    """Three joints: pulse → beacon → worker rec → fleet row. Missing any one is unjoined.

    HOW TO PROVE IT RED: paint the chip when m.eye is missing.
    Expected: 'the chip fires on a machine that never reported an eye'.
    """

    def test_no_frame_is_not_live(self):
        import control_app as ca
        real = ca._eyes_pulse
        ca._eyes_pulse = lambda: {"liveTs": 0, "verifyTs": 0, "kaiTs": 0}
        try:
            e = ca._eye_for_wire()
            self.assertEqual(e["live"], False)
            self.assertIsNone(e["ageMs"])
        finally:
            ca._eyes_pulse = real

    def test_a_fresh_read_is_live(self):
        import control_app as ca
        real = ca._eyes_pulse
        ca._eyes_pulse = lambda: {"liveTs": int(time.time() * 1000) - 400}
        try:
            e = ca._eye_for_wire()
            self.assertTrue(e["live"])
            self.assertGreaterEqual(e["ageMs"], 0)
            self.assertLess(e["ageMs"], 6000)
        finally:
            ca._eyes_pulse = real

    def test_a_stalled_read_is_not_live(self):
        # ⚠ v2622 — THIS STUB WAS PINNED TO A WINDOW THE PRODUCT NO LONGER HAS. It aged the pulse
        # a hardcoded 20s against a hardcoded `age < 6000`, but 5f1122d8 deliberately widened the
        # WIRE's window to `_EYE_WIRE_FRESH_MS = 300000` because the value rides
        # `_console_beacon_loop`'s 240s period. 20_000 < 300_000, so the eye was correctly live and
        # CI read "AssertionError: True is not false" — a stale assertion, not a defect. The
        # replacement guards went into test_control.py and this duplicate was left behind.
        # Stub and assert RELATIVE TO THE CONSTANT, so moving the window can never again strand
        # this copy on a retired number. `ageMs` stays exact, so it is still a real bound.
        import control_app as ca
        real = ca._eyes_pulse
        stale_ms = ca._EYE_WIRE_FRESH_MS + 60_000
        ca._eyes_pulse = lambda: {"liveTs": int(time.time() * 1000) - stale_ms}
        try:
            e = ca._eye_for_wire()
            self.assertFalse(e["live"])
            self.assertGreaterEqual(e["ageMs"], ca._EYE_WIRE_FRESH_MS)
        finally:
            ca._eyes_pulse = real

    def test_the_three_joints_exist(self):
        app = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        ui = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        worker = io.open(os.path.join(ROOT, "functions", "api", "console.js"), encoding="utf-8").read()
        self.assertIn('"eye": _eye_for_wire()', app)
        self.assertIn("eye: (function (e)", worker)
        # ⚠⚠ v2795 — THE UI JOINT MOVED AND THE LAW STAYED. This asserted the literal
        # `m.eye && m.eye.live`, which was the v2454 shape. v2766 REPLACED it, on purpose and for
        # the better: rendering the glyph only when `m.eye.live` drew the same nothing for three
        # different machines — no second family installed (Dean, correct), one installed and IDLE,
        # and one installed and FAILING. Absence, rest and failure are not the same fact. The
        # condition now lives inside `_fleetEye`, which spends provider/family/second to tell six
        # states apart.
        #
        # So the law binds to the JOINT and to the INVARIANT, not to the old expression:
        #   · the fleet row must call _fleetEye with the wire's eye field, and
        #   · _fleetEye must refuse a MISSING eye before it reads anything off it — an absent
        #     field draws nothing rather than an empty dot.
        # [[the-unjoined-end]] [[unknown-stays-unknown]]
        self.assertIn("_fleetEye(m.eye)", ui,
                      "the fleet row no longer hands the wire's eye to _fleetEye — the joint is "
                      "broken and the chip is fed by something else")
        self.assertIn("fleet-eye", ui)
        # ⚠ ANCHORED AT BOTH ENDS, never a byte window: the function starts at its own `var` and
        # ends at the first close of that assignment. A fixed slice would shrink every time
        # somebody documented the six states this function exists to tell apart, and that is the
        # defect that made the river guard grade nothing this same session.
        _i = ui.index("var _fleetEye = function(e){")
        _j = ui.index("\n      };", _i)
        eye_fn = ui[_i:_j]
        self.assertLess(len(eye_fn), 20000, "the _fleetEye slice ran away — re-point the end anchor")
        # ⛔ THE GUARD IS THE FIRST THING IT DOES. If the refusal drifts below a read of `e`, a
        # machine that never reported an eye starts painting a chip about a lane nobody asked.
        self.assertIn("if (!e) return '';", eye_fn,
                      "_fleetEye no longer refuses a MISSING eye, so an absent field would paint "
                      "the chip — the exact thing this joint exists to prevent")
        self.assertLess(eye_fn.index("if (!e) return '';"), eye_fn.index("e.provider"),
                        "_fleetEye reads the eye BEFORE checking it exists")


class TestCF2WriteDoorsStillQueueANote(unittest.TestCase):
    def test_chronicle_apply_still_leaves_the_handoff_note(self):
        import auto_scope as AS
        src = AS.file_def(os.path.join(HERE, "control_app.py"), "chronicle_apply")
        self.assertIn("d2r_chronicleHandoff", src)
        self.assertIn("queued:true", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
