# -*- coding: utf-8 -*-
"""#161 (REG-3077) - NO SPEC PINS A STORE THE BOARD WRITES BACK BETWEEN TWO LOADS.

A spec that writes `localStorage.setItem('d2r_rwMade', ...)` through page.evaluate and then loads the board again
writes over a first page that keeps rwMade, owned, runeStash and eighteen more stores in memory, and persist() writes
them back whole. v527's spec failed that way on CI twice (v3818, v3839) before REG-3059 moved its pin into an init
script by hand. WHICH writer put Insight back there is UNMEASURED: a node replay of the whole sequence does not
reproduce persist() as the writer (REG-3059, corrected in v3840), so it is a Chrome-only path.
Measured at v3839, 90 more such pins in 54 specs:
  - 75 followed by page.reload(), in 45 specs (rwMade 46, owned 35, runeStash 23, setPieces 8, unknownReads 5,
    copies 2, wishlist 2 - a pin often sets several). The first count was 66: a scanner that did not skip comments
    read "main's" as a quote and lost 8 (this law's scanner skips them, and a case holds it). One more, v637's
    'L·d2r_rwMade', is a store under a world prefix: agent-guide's list of 52 (REG-3059) had it and this scan did not;
  - 8 followed by page.goto(URL) - the same second load, reached by navigating - in 7 specs;
  - 3 seeding helpers whose key is an ARGUMENT (setItem(p, b)), so no literal names the store - in reg2410 it is
    d2r_owned, in v1625 rwMade and setPieces. A computed key cannot be shown to miss persist()'s stores, so it is
    pinned too;
  - 4 that pass a named constant - v2200's and v2203's SEED, an expression string that writes owned and setPieces -
    so the pin is not inside the call at all. Found by v2200:53 itself: flaky on b26d0cbec, red on main 014d4fc3d.
REG-3076 moved every one onto tests/_pin.ts: pinEvaluate() runs the spec's own function, records the writes it made and
replays them in a one-shot init script before the next document's boot; reloadPinned() / gotoPinned() load the board
again and check each pin's mark, naming the pin's file:line and keys if it never reached the boot.

This law holds the class on the specs it names: the stores persist() writes are READ from bible.html (never a hand
list); each spec in PINNED is scanned for a page.evaluate that sets one of them, or sets a computed key, and is followed
by a reload or goto in the same test - none may remain; every pinEvaluate reaches reloadPinned or gotoPinned before any
plain reload or goto (a plain one would skip the premise); and the helper keeps its one-shot mark and its named premise.
PINNED is literal so heart2 keys this law on those files' bytes. The same scan over EVERY tests/*.spec.ts - so a new
spec is held too - is TestReg3077NoSpecInTheFolderPinsBetweenLoads in test_folder_scans.py, which lists the folder and
is unkeyable on purpose. The specs themselves run on CI (Routine I). RED_PROOF below.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

BIBLE = os.path.join(ROOT, "bible.html")
PIN = os.path.normpath(os.path.join(ROOT, "tests/_pin.ts"))
#: every spec REG-3076 moved onto tests/_pin.ts. Literal on purpose: each name is a file heart2 keys this law on.
PINNED = (
    "tests/reg2410_stores_never_bricked.spec.ts",
    "tests/reg2414_a_removed_store_reads_as_its_default.spec.ts",
    "tests/reg2522_reg2523_a_bad_store_never_costs_his_good_copy.spec.ts",
    "tests/v1625_board_quality_surfaces.spec.ts",
    "tests/v1628_board_quality_tokens.spec.ts",
    "tests/v1630_sealed_stamp.spec.ts",
    "tests/v1630_set_piece_slot_suffix.spec.ts",
    "tests/v1712_onestep_host_bases.spec.ts",
    "tests/v1737_ladder_toggle_and_proven_bases.spec.ts",
    "tests/v1739_shopping_list_art.spec.ts",
    "tests/v1938_remaining_repair_outcome.spec.ts",
    "tests/v1939_surfaces_agree.spec.ts",
    "tests/v203_mule_vault.spec.ts",
    "tests/v2200_the_vault_backfill_runs_once_and_his_hand_wins.spec.ts",
    "tests/v2203_the_vault_undo_keeps_what_was_really_his.spec.ts",
    "tests/v2205_a_set_piece_in_the_vault_survives_the_load_prune.spec.ts",
    "tests/v3734_shared_stash_caps_copies.spec.ts",
    "tests/v3740_old_set_dupes_dock_and_mule.spec.ts",
    "tests/v3742_set_dupe_migration_survives_a_failed_persist.spec.ts",
    "tests/v3743_set_dupe_copies_fold_confirmed_before_stamp.spec.ts",
    "tests/v425_vault_simulation.spec.ts",
    "tests/v43_editorial_audit.spec.ts",
    "tests/v465_socketed_persist.spec.ts",
    "tests/v557_forge_card_recipe.spec.ts",
    "tests/v562_chronicle_sync_filter_throwout.spec.ts",
    "tests/v563_spare_base_sync.spec.ts",
    "tests/v565_forge_all_words_sim.spec.ts",
    "tests/v587_spare_base_capacity.spec.ts",
    "tests/v588_premium_trade_bases.spec.ts",
    "tests/v592_socketed_only_filter.spec.ts",
    "tests/v597_chain_step_sanity.spec.ts",
    "tests/v602_wrong_socket_honesty.spec.ts",
    "tests/v603_ux_audit_sim.spec.ts",
    "tests/v604_forge_coverage_invariant.spec.ts",
    "tests/v606_finish_ascend_fx.spec.ts",
    "tests/v609_artshot_fallback.spec.ts",
    "tests/v615_chronicle_lockdown.spec.ts",
    "tests/v615_consume_lockdown.spec.ts",
    "tests/v617_smart_insights_flagship.spec.ts",
    "tests/v618_hero_create_first_forge.spec.ts",
    "tests/v619_grail_forges_sync.spec.ts",
    "tests/v621_lockdown_e2e_journey.spec.ts",
    "tests/v622_art_fidelity.spec.ts",
    "tests/v624_consume_narration.spec.ts",
    "tests/v628_exact_fit_gate.spec.ts",
    "tests/v629_chronicle_vault_sync.spec.ts",
    "tests/v630_exclusivity_reservation.spec.ts",
    "tests/v631_promote_unknown_bases.spec.ts",
    "tests/v632_ladder_visibility.spec.ts",
    "tests/v634_ladder_preview.spec.ts",
    "tests/v635_ladder_profile.spec.ts",
    "tests/v636_ladder_closure.spec.ts",
    "tests/v637_oneway_inheritance.spec.ts",
    "tests/v660_got_base_ascend.spec.ts",
)
#: the pins REG-3076 moved, so a scan that silently finds fewer is a premise failure, not a pass
MOVED = 90

#: a literal key, under a world prefix too (L·, I·<id>·, IL·<id>· - LSR's forks): v637 pins 'L·d2r_rwMade'
_LIT = re.compile(r"(?<!sessionStorage)\.setItem\(\s*['\"](?:[^'\"\s]{1,16}?)?(d2r_[A-Za-z0-9_]+)['\"]")
_COMPUTED = re.compile(r"(?<!sessionStorage)\.setItem\(\s*(?!['\"`])[^,)]{1,60},")


def persisted_stores():
    """The stores persist() writes back, read from the shipped page. -> set"""
    with io.open(BIBLE, encoding="utf-8") as fh:
        b = fh.read()
    i = b.index("const persist = () => {")
    return set(re.findall(r"setItem\('(d2r_[A-Za-z0-9_]+)'", b[i:b.index("\n};", i)]))


def _close(s, j):
    """s[j] == '(' -> the index of its matching ')', skipping strings. -1 when it never closes."""
    d, q, k = 0, None, j
    while k < len(s):
        c = s[k]
        if q:
            if c == "\\":
                k += 2
                continue
            if c == q:
                q = None
        elif s.startswith("//", k):                      # a line comment: "main's vault" is prose, not a quote
            k = s.find("\n", k)
            if k < 0:
                return -1
            continue
        elif s.startswith("/*", k):
            k = s.find("*/", k)
            if k < 0:
                return -1
            k += 2
            continue
        elif c in "'\"`":
            q = c
        elif c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                return k
        k += 1
    return -1


def _definition(text, name):
    """The text of a top-level `const|let|var|function <name>` in this file, up to the next top-level statement. -> str"""
    d = re.search(r"(?m)^(?:const|let|var|function)\s+%s\b" % re.escape(name), text)
    if not d:
        return ""
    n = re.compile(r"\n(?:const|let|var|async function|function|test|export|/\*|//)\b").search(text, d.end())
    return text[d.end():n.start() if n else len(text)]


def scan(text, stores):
    """-> (raw pins [(line, keys)], pinEvaluate sites whose next load is a plain reload or goto [line])"""
    starts = [m.start() for m in re.finditer(r"(?m)^\s*test(?:\.only|\.skip)?\(", text)] + [len(text)]
    raw, unchecked = [], []
    for m in re.finditer(r"\.evaluate\(", text):
        e = _close(text, m.end() - 1)
        if e < 0:
            continue
        body = text[m.end():e]
        named = re.match(r"\s*([A-Za-z_$][\w$]*)\s*(?:,|$)", body)    # page.evaluate(SEED): the pin is the constant
        if named:
            body += _definition(text, named.group(1))
        keys = sorted(set(_LIT.findall(body)) & stores) + (["<computed key>"] if _COMPUTED.search(body) else [])
        if not keys:
            continue
        nxt = min(x for x in starts if x > m.start())
        if re.compile(r"\.(?:reload|goto)\(").search(text, e, nxt):
            raw.append((text.count("\n", 0, m.start()) + 1, keys))
    for m in re.finditer(r"\bpinEvaluate\(", text):
        nxt = min(x for x in starts if x > m.start())
        a = re.compile(r"\b(?:reloadPinned|gotoPinned)\(").search(text, m.end(), nxt)
        b = re.compile(r"\bpage\.(?:reload|goto)\(").search(text, m.end(), nxt)
        if b and (not a or b.start() < a.start()):
            unchecked.append(text.count("\n", 0, m.start()) + 1)
    return raw, unchecked


def verdict(paths, stores):
    """The scan over spec files. -> (raw ["file:line keys"], unchecked ["file:line"], pinEvaluate sites seen)"""
    raw_all, unchecked_all, n_pin = [], [], 0
    for f in paths:
        with io.open(f, encoding="utf-8", errors="replace") as fh:
            t = fh.read()
        n_pin += len(re.findall(r"\bpinEvaluate\(", t))
        raw, unchecked = scan(t, stores)
        raw_all += ["%s:%d %s" % (os.path.basename(f), ln, ",".join(k)) for ln, k in raw]
        unchecked_all += ["%s:%d" % (os.path.basename(f), ln) for ln in unchecked]
    return raw_all, unchecked_all, n_pin


class NoSpecPinsAWrittenBackStoreBetweenLoads(unittest.TestCase):

    def test_the_written_back_stores_are_read_from_the_page(self):
        s = persisted_stores()
        for k in ("d2r_rwMade", "d2r_owned", "d2r_runeStash", "d2r_setPieces"):
            self.assertIn(k, s, "PREMISE: persist() no longer writes %s, or this law can no longer read it" % k)

    def test_the_scan_sees_the_shape(self):
        """PREMISE: the scanner finds a raw pin (by reload, by goto, by a computed key), and a pin whose load skips
        the premise."""
        stores = persisted_stores()
        raw, unchecked = scan(
            "test('a', async ({ page }) => {\n  await page.evaluate(() => { localStorage.setItem('d2r_rwMade', '{}'); });\n"
            "  await page.reload();\n});\n"
            "test('b', async ({ page }) => {\n  await pinEvaluate(page, () => { localStorage.setItem('d2r_owned', '[]'); });\n"
            "  await page.reload();\n});\n", stores)
        self.assertEqual((raw, unchecked), ([(2, ["d2r_rwMade"])], [6]))
        self.assertEqual(scan("test('c', async ({ page }) => {\n  await page.evaluate(() => localStorage.setItem('d2r_x', '1'));"
                              "\n  await page.reload();\n});\n", stores), ([], []),
                         "a pin on a store the board never writes back was counted")
        raw, _u = scan("test('d', async ({ page }) => {\n  await page.evaluate(() => {\n"
                       "    localStorage.setItem('d2r_owned', '[]');   // main's vault - an apostrophe in prose\n  });\n"
                       "  await page.reload();\n});\n", stores)
        self.assertEqual(raw, [(2, ["d2r_owned"])], "a comment's apostrophe hid a pin from the scan (it did, 8 times)")
        raw, unchecked = scan("test('e', async ({ page }) => {\n  await page.evaluate(() => { w.LSR.setItem('d2r_copies', '{}'); });\n"
                              "  await page.goto(URL);\n});\n"
                              "test('f', async ({ page }) => {\n  await pinEvaluate(page, () => { w.LSR.setItem('d2r_copies', '{}'); });\n"
                              "  await page.goto(URL);\n});\n", stores)
        self.assertEqual((raw, unchecked), ([(2, ["d2r_copies"])], [6]), "a pin that loads again by page.goto hid")
        raw, _u = scan("async function seed(page, k, b) {\n  await page.evaluate(([k, b]) => { localStorage.setItem(k, b); }, [k, b]);\n"
                       "  await page.reload();\n}\ntest('g', async ({ page }) => {\n  await seed(page, 'd2r_owned', '[]');\n});\n",
                       stores)
        self.assertEqual(raw, [(2, ["<computed key>"])], "a pin whose store is an argument hid from the scan")
        raw, _u = scan("const SEED = `(function(){\n  window.LSR.setItem('d2r_owned', '[]');\n})()`;\n\n"
                       "test('h', async ({ page }) => {\n  await page.evaluate(SEED);\n  await page.goto(URL);\n});\n", stores)
        self.assertEqual(raw, [(6, ["d2r_owned"])], "a pin held in a named constant hid from the scan")
        raw, _u = scan("test('i', async ({ page }) => {\n  await page.evaluate(() => localStorage.setItem('L\u00b7d2r_rwMade', '{}'));"
                       "\n  await page.reload();\n});\n", stores)
        self.assertEqual(raw, [(2, ["d2r_rwMade"])], "a store pinned under a world prefix hid from the scan (v637 did)")

    def test_no_pinned_spec_does_it_again(self):
        paths = [os.path.normpath(os.path.join(ROOT, p)) for p in PINNED]
        gone = [p for p, q in zip(PINNED, paths) if not os.path.isfile(q)]
        self.assertEqual(gone, [], "PREMISE: a spec REG-3076 moved is gone - rename it in PINNED: %s" % gone)
        raw, unchecked, n_pin = verdict(paths, persisted_stores())
        self.assertGreaterEqual(n_pin, MOVED, "PREMISE: the pins REG-3076 moved are no longer found (%d)" % n_pin)
        self.assertEqual(raw, [], "a spec pins a store the board writes back between two loads - use pinEvaluate: %s"
                         % "; ".join(raw[:8]))
        self.assertEqual(unchecked, [], "a pin reaches a plain reload or goto, which never checks it arrived: %s"
                         % "; ".join(unchecked[:8]))


class TheHelperKeepsItsPromise(unittest.TestCase):

    def test_one_shot_and_a_named_premise(self):
        with io.open(PIN, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count("if (sessionStorage.getItem(id) !== null) return;   // one-shot: the next document only"), 1,
                         "the pin replays on every later load, not only the next one")
        self.assertEqual(src.count("await page.addInitScript(({ id, rec }) => {"), 1, "the pin is no longer an init script")
        self.assertIn("'REG-3076 premise: the pin at ' + p.label + ' (' + (p.keys.join(', ')", src,
                      "a pin that never reached the boot is not named")
        self.assertIn("value = expr ? (0, eval)(src) : (0, eval)('(' + src + ')')(arg);", src,
                      "the spec's own function or expression is no longer what runs")
        self.assertEqual(src.count("    if (value && typeof value.then === 'function') {\n"), 1,
                         "an async pin is recorded only up to its first await and replays without the rest")
        for door in ("  const res = await page.reload(opts);\n  await premise(page, pins);\n",
                     "  const res = await page.goto(url, opts);\n  await premise(page, pins);\n"):
            self.assertEqual(src.count(door), 1, "a pinned load no longer checks its pins arrived: %r" % door)


RED_PROOF = [
    {"why": "REG-3077 - the scan reads a comment's apostrophe as a quote again, and a pin hides from it",
     "file": "test_a_spec_pin_rides_the_reloads_boot.py",
     "find": "        elif s.startswith(\"//\", k):                      # a line comment: \"main's vault\" is prose, not a quote\n",
     "replace": "        elif False:\n",
     "matches": 1},
    {"why": "REG-3077 - a spec pins rwMade between two loads again",
     "file": "../tests/v615_consume_lockdown.spec.ts",
     "find": "pinEvaluate(page, ",
     "replace": "page.evaluate(",
     "matches": 3},
    {"why": "REG-3077 - a pin reaches a plain reload, skipping its premise",
     "file": "../tests/v630_exclusivity_reservation.spec.ts",
     "find": "  await reloadPinned(page); await page.waitForTimeout(1800);\n  const r = await page.evaluate(() => {\n    const w: any = window;\n    const sc = w.forgeScan();",
     "replace": "  await page.reload(); await page.waitForTimeout(1800);\n  const r = await page.evaluate(() => {\n    const w: any = window;\n    const sc = w.forgeScan();",
     "matches": 1},
    {"why": "REG-3077 - a pin loads the board again by a plain page.goto, skipping its premise",
     "file": "../tests/v2200_the_vault_backfill_runs_once_and_his_hand_wins.spec.ts",
     "find": "  });\n  await gotoPinned(page, URL);\n  await ready(page);\n  await page.waitForTimeout(1500);\n",
     "replace": "  });\n  await page.goto(URL);\n  await ready(page);\n  await page.waitForTimeout(1500);\n",
     "matches": 1},
    {"why": "REG-3077 - a seeding helper whose store is an argument pins between two loads again",
     "file": "../tests/reg2410_stores_never_bricked.spec.ts",
     "find": "pinEvaluate(page, ([k, b]) =>",
     "replace": "page.evaluate(([k, b]) =>",
     "matches": 1},
    {"why": "REG-3077 - a pin held in a named constant (v2200's SEED) runs between two loads again",
     "file": "../tests/v2200_the_vault_backfill_runs_once_and_his_hand_wins.spec.ts",
     "find": "  const seed = await pinEvaluate(page, SEED);\n",
     "replace": "  const seed = await page.evaluate(SEED);\n",
     "matches": 1},
    {"why": "REG-3077 - v637 pins its ladder-prefixed rwMade between two loads again",
     "file": "../tests/v637_oneway_inheritance.spec.ts",
     "find": "  await pinEvaluate(page, () => {\n    localStorage.setItem('L\u00b7d2r_rwMade',",
     "replace": "  await page.evaluate(() => {\n    localStorage.setItem('L\u00b7d2r_rwMade',",
     "matches": 1},
    {"why": "REG-3076 - the pin replays on every later load",
     "file": "../tests/_pin.ts",
     "find": "      if (sessionStorage.getItem(id) !== null) return;   // one-shot: the next document only\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-3076 - a pin that never reached the boot is not named",
     "file": "../tests/_pin.ts",
     "find": "'REG-3076 premise: the pin at ' + p.label + ' (' + (p.keys.join(', ')",
     "replace": "'premise: ' + (p.keys.join(', ')",
     "matches": 1},
    {"why": "REG-3076 - an async pin is recorded only up to its first await, silently",
     "file": "../tests/_pin.ts",
     "find": "    if (value && typeof value.then === 'function') {\n",
     "replace": "    if (false) {\n",
     "matches": 1},
    {"why": "REG-3076 - a pin that loads the board by gotoPinned is never checked",
     "file": "../tests/_pin.ts",
     "find": "  const res = await page.goto(url, opts);\n  await premise(page, pins);\n",
     "replace": "  const res = await page.goto(url, opts);\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
