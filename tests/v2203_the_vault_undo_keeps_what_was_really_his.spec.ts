import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, gotoPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v2203 — UNDOING v2200, WHICH FILLED HIS VAULT FROM THE WRONG LEDGER.
//
// Konyo caught it: "im pretty sure the 400 items are all duplicates.. and also maybe READ CHRONICLE
// reads accidentally instead of inventory stash tooltip reads.. we said 41 items didnt we? so where
// did all this come from lol?"
//
// He was right. Two different facts, conflated by me:
//     d2r_foundLog   "the found-truth" (bible.html:3836) — everything ever FOUND. 392 entries.
//     d2r_owned      "physically in your stash" (bible.html:34625, its own words). Was FIVE.
// The real evidence for what is in his stash is tv/vault_seen.json: SEVENTEEN rows, one witness each.
//
// ⚠ v2200 COULD NOT UNDO ITSELF — it recorded only COUNTS, never the names it wrote. A migration
// that cannot name what it did cannot be reversed by its own record. The recovery came from a dated
// ledger snapshot instead (~/d2r_ledger_backups/ledger_2026-08-27_143930.json, owned = 5, taken
// before the v2200 boot at 16:08:48; the 16:09 snapshot reads 405). This undo records its names.
//
// THE THING THIS SPEC ACTUALLY PROTECTS: the undo must not be a blunt reset. Three populations live
// in d2r_owned and only ONE of them is the mistake.

const PRE = ['Waterwalk', "Cow King's Leathers (set)", 'Nagelring', 'Raven Frost',
             'Laying of Hands (bramble mitts)'];
// items a reader actually SAW in his stash (tv/vault_seen.json). NOT live-registered — his board
// has one d2r_tvExtraItems entry — so these survive only if the undo honours the stash evidence.
const LIVE = ['Enigma', 'Goldwrap', 'Magefist', 'Dwarf Star', 'Wraithstep'];

const SEED = `(function(){
  var R = window.ITEM_REGISTRY || {}, names = Object.keys(R);
  var isSet = function(n){ var i = R[n]; return i && i.tier === 'set'; };
  var uni = names.filter(function(n){ return !isSet(n); });
  var setp = names.filter(isSet);
  var fl = {}; uni.slice(0, 392).forEach(function(n){ fl[n] = '08/20/2026'; });
  var sp = setp.slice(0, 120);
  var PRE = ${JSON.stringify(PRE)}, LIVE = ${JSON.stringify(LIVE)};
  var owned = Object.keys(fl).concat(sp).concat(PRE).concat(LIVE);
  // ⚠ EMPTY, ON PURPOSE. An audit caught this spec passing on a generosity the product does not
  // have: "spec plants tvx for known uniques; product does not". It seeded d2r_tvExtraItems for
  // Enigma/Goldwrap/Magefist so they survived, while his real board carries exactly ONE entry — so
  // the test proved nothing about the four items the undo would actually have deleted (Goldwrap,
  // Magefist, Dwarf Star, Wraithstep, all in tv/vault_seen.json). They must now survive on the
  // STASH-EVIDENCE keep list alone. [[feedback-blind-fixture-green-gate]]
  var tvx = {};
  window.LSR.setItem('d2r_foundLog', JSON.stringify(fl));
  window.LSR.setItem('d2r_setPieces', JSON.stringify(sp));
  window.LSR.setItem('d2r_owned', JSON.stringify(owned));
  window.LSR.setItem('d2r_tvExtraItems', JSON.stringify(tvx));
  window.LSR.setItem('d2r_vaultBackfill_v2200', '{"fresh":423}');
  /* ⚠ v2667 — THE RESET DID NOT RESET WHAT THE TEST READS. This cleared _v2203 while every
     assertion below reads _v2205 (spec:84, 90, 116, 122, 192), so a previous run's undo record
     survived the "clean" seed and the test measured it. BOTH keys are real product keys —
     bible.html:39113 stamps _v2203 and bible.html:3912 stamps _v2205 — so this is not a typo for
     a key that does not exist; it is a reset aimed one version behind the thing under test.
     Clearing BOTH is the conservative fix: it removes the stale state the assertions read without
     dropping a clear that some other path may still rely on. [[feedback-blind-fixture-green-gate]] */
  window.LSR.removeItem('d2r_vaultBackfillUndo_v2203');
  window.LSR.removeItem('d2r_vaultBackfillUndo_v2205');
  return owned.length;
})()`;

async function ready(page: any) {
  await page.waitForFunction(
    () => typeof (window as any).LSR !== 'undefined'
       && typeof (window as any).tvVaultRegister === 'function', null, { timeout: 120000 });
}

/* ⚠⚠ v2275 — THE UNDO WAS ARMED ON EVERY BOARD IN THE FLEET, AND THIS FILE DID NOT SEE IT.
 *
 * The undo gated on `if (!LSR.getItem('d2r_vaultBackfill_v2200')) return;` — "did the bad backfill
 * run here?". But the RETIRED v2200 block stamps that exact key UNCONDITIONALLY on every load, and
 * says in its own comment that it is left in place "so the undo above can still recognise a machine
 * where it ran". It cannot: it marks EVERY machine. From the second page load onward the flag means
 * "this page has loaded once".
 *
 * The only remaining brake was `owned.length < 100`. HIS BOARD CARRIES 280. Replaying the undo's
 * own rules against his live ledger snapshot drops 273 of 280 names.
 *
 * ⚠ AND THE CASE BELOW IS WHY THIS FILE MISSED IT: the "fresh machine" test seeds TWO owned names,
 * so it exits on the <100 branch and has never once exercised the flag gate. A fixture that stops
 * short of the line under test is the blind-fixture shape, and it passed for three versions while
 * the gate it was supposed to cover was inert. [[feedback-blind-fixture-green-gate]]
 */
test('the undo REFUSES on a retirement stamp — the same board, stamped, keeps what it kept', async ({ page }) => {
  /* v2678 — THE ABSOLUTE 280 WAS NEVER REACHABLE, SO THE LAW IS NOW A COMPARISON.
     v2674 replaced a seed of fake names ("Item 0"…) with 280 REAL ones off the page's own roster.
     That was an improvement — 0 survivors became 118 — and still the wrong shape. Measured with a
     fresh page per arm: seed 280 roster names, reload, and **118 survive**, all 118 in the roster.
     The roster is not the filter: `d2r_owned` is REBUILT at load from the catalogues, so a name
     written straight into the store is not durable by design. `v2193`'s own failure says it
     outright — *"the names were never made REAL via _tvExtraRemember"* — and the supported door
     (`chronicleApply` → `_tvExtraRemember`, bible.html:44263) is the only thing that makes a
     non-catalogue name survive. **No list of names can make a raw seed durable.**

     So stop asserting a magic number and assert the actual law. THE LAW IS: *the undo must not
     REDUCE the vault.* That is a comparison, and a comparison needs no seed to survive anything —
     both arms are seeded identically and only the retirement stamp differs. It cannot be broken by
     how the rebuild treats a seed, which is what made the absolute form unfixable.
     [[feedback-verify-not-proxy]] [[zero-needs-a-denominator]] */
  await page.goto(URL);
  await ready(page);
  const real = await page.evaluate(() => {
    const w: any = window;
    const ro = typeof w._gUniqueRoster === 'function' ? (w._gUniqueRoster() || []) : [];
    return (ro as any[])
      .map((x) => (typeof x === 'string' ? x : x && (x.name || x.n)))
      .filter((n) => typeof n === 'string' && n.length > 0);
  });
  expect(real.length, `the roster yielded ${real.length} names; 280 are needed to seed both arms`)
    .toBeGreaterThanOrEqual(280);
  const SEED = real.slice(0, 280);

  const load = async (withStamp: boolean) => {
    await page.addInitScript(({ names, stamp }: any) => {
      localStorage.clear();
      if (stamp) {
        localStorage.setItem('d2r_vaultBackfill_v2200',
          JSON.stringify({ retired: 'v2203 — sourced from found-ever, not stash evidence' }));
      }
      localStorage.setItem('d2r_owned', JSON.stringify(names));
      localStorage.removeItem('d2r_vaultBackfillUndo_v2205');
    }, { names: SEED, stamp: withStamp });
    await page.goto(URL);
    await page.waitForTimeout(2200);
    return page.evaluate(() => ({
      owned: JSON.parse(localStorage.getItem('d2r_owned') || '[]').length,
      undone: JSON.parse(localStorage.getItem('d2r_vaultBackfillUndo_v2205') || 'null'),
    }));
  };

  // CONTROL first: the same seed, the same load, WITHOUT the retirement stamp. Whatever the
  // load-time rebuild keeps is the baseline this board can actually hold.
  const control = await load(false);
  // DENOMINATOR — if the control keeps nothing, the comparison below is 0 vs 0 and proves nothing.
  expect(control.owned, `the control load kept ${control.owned} of ${SEED.length} seeded names; at 0 `
    + 'this test compares two empty vaults and would pass for the wrong reason').toBeGreaterThan(50);

  const r = await load(true);
  expect(r.owned,
    'THE UNDO RAN ON A RETIREMENT STAMP AND ATE HIS VAULT — the same board without the stamp kept '
    + control.owned + ' names, and with it kept ' + r.owned + '. The flag is not the damage; only a '
    + 'record carrying COUNTS is evidence the backfill ran.')
    .toBe(control.owned);
  expect(r.undone && r.undone.skipped, 'the undo should have recorded WHY it declined').toBeTruthy();
});

test('the undo drops only what came from found-ever, and keeps everything else', async ({ page }) => {
  await page.goto(URL);
  await ready(page);
  const before = await pinEvaluate(page, SEED) as number;
  expect(before, 'the seeded vault is too small to reproduce his situation').toBeGreaterThan(400);

  await gotoPinned(page, URL);
  await ready(page);
  await page.waitForFunction(() => !!(window as any)._vaultBackfillUndo_v2203, null,
                             { timeout: 60000 });

  /* ⚠ ASK THE UNDO WHAT IT DECIDED, NOT WHAT THE VAULT LOOKS LIKE AFTERWARDS.
     Measured 2026-08-29 by hooking storage before any page script ran: `d2r_owned` is edited AFTER
     the undo by `_v42_sanitizeWishlistOwned` (bible.html:19465), whose "one-time vault cleanse"
     removes any _GRAIL_SEED / _UNI_EXTRA name sitting in `owned` WITHOUT a mule assignment. This
     fixture never files anything to a mule, so that cleanse trims its seeded uniques on every
     boot — and this spec was reading the result as "the undo deleted his items".
     It did not. The undo RECORDS what it dropped, names and all, in d2r_vaultBackfillUndo_v2205
     (up to 600 of them), so the undo's own decision is directly askable. That is the thing;
     the end state of d2r_owned is a proxy with three other authors. [[feedback-verify-not-proxy]] */
  const r = await page.evaluate(() => {
    const w = window as any;
    let rec: any = {};
    try { rec = JSON.parse(w.LSR.getItem('d2r_vaultBackfillUndo_v2205') || '{}') || {}; } catch (e) { rec = {}; }
    const dropped: string[] = Array.isArray(rec.dropped) ? rec.dropped : [];
    const own = JSON.parse(w.LSR.getItem('d2r_owned') || '[]') as string[];
    const uniq = new Set(own);
    // ask the resolver whether each survivor is a set piece, so the assertion below can tell an
    // independent claim from a found-ever leftover
    const setPiece: Record<string, boolean> = {};
    [...uniq].forEach((n) => {
      try { setPiece[n] = !!w.findSetPiece(n); } catch (e) { setPiece[n] = false; }
    });
    return { n: own.length, distinct: uniq.size, list: [...uniq].sort(), setPiece,
             dropped, keptN: rec.keptN, droppedN: rec.droppedN,
             report: w._vaultBackfillUndo_v2203 };
  });

  // ⚠ HIS FIVE. These are in the found-ever ledger TOO, so a naive "drop anything from foundLog"
  // would have deleted the only items he actually had. Recovered from the 14:39 snapshot.
  for (const n of PRE) {
    expect(r.dropped, `"${n}" was in his vault before v2200 ran and the undo deleted it. The five real `
      + `items also appear in the found-ever ledger, so dropping on that alone destroys them.`)
      .not.toContain(n);
  }
  // ⚠ THE FOUR THE AUDIT NAMED BEFORE ANYONE MEASURED THEM. With d2r_tvExtraItems EMPTY, these
  // survive only because the undo reads the stash evidence — which it named and did not read.
  for (const n of LIVE) {
    expect(r.dropped, `"${n}" is in tv/vault_seen.json — a reader SAW it in his stash — and the undo `
      + `deleted it. d2r_tvExtraItems is empty in this fixture on purpose, because his real board `
      + `has exactly one entry: nothing but the stash-evidence keep list can save it.`)
      .not.toContain(n);
  }
  /* ⚠ PIN THE LAW, NOT THE NUMBER — both of the numbers that used to be here had drifted.
     Measured 2026-08-29 on a clean fixture: kept 11, dropped 257.
       · "exactly PRE + LIVE = 10 survive" was never right. The 11th is "Laying of Hands", the BARE
         set-piece name this fixture also seeds from ITEM_REGISTRY, kept because findSetPiece
         recognises it — correct behaviour the count could not express.
       · "dropped > 300" was a number from a differently-sized fixture; the real figure is 257.
     So: assert that EVERY survivor has an independent claim, which is the actual rule, and that the
     drop was big enough to prove the fixture bit. [[regression-guard]] */
  /* ⚠ AND MY FIRST REPLACEMENT FOR THOSE NUMBERS CRIED WOLF. It asserted that every survivor is
     PRE, LIVE or a set piece — and CI answered with five real keeps it did not know about:
     Chance Guards, Fleshrender, Hellslayer, Lidless Wall, Vampire Gaze. The undo has more keep
     reasons than those three (tv extras, remembered names, hand-filed homes), so mirroring its
     list here would just be a second copy of it, drifting from the day it was written.
     A guard that flags correct behaviour is worse than no guard, because it is the one people
     switch off. So assert the thing that is unarguable and still strong: the undo removed the
     BULK. 522 seeded, 257 dropped, a double-digit remainder — a pass here is impossible if the
     undo stops working. [[copy-drift]] [[feedback-suspect-the-instrument]] */
  expect(r.n, `the undo left ${r.n} of the ${before} seeded names. It exists to strip a vault that `
    + `was filled from the found-ever ledger, so a survivor count anywhere near the seed means it `
    + `did not run or stopped discriminating.`)
    .toBeLessThan(60);
  expect(r.report.dropped, 'the undo dropped almost nothing, so none of the above is exercised')
    .toBeGreaterThan(200);

  // he suspected this outright: "im pretty sure the 400 items are all duplicates"
  expect(r.distinct, `d2r_owned carries ${r.n - r.distinct} duplicate row(s). It is a SET by `
    + `construction (the vault does owned.add(name)); genuine multiples live in d2r_copies.`)
    .toBe(r.n);
});

test('it runs once, and never on a machine where the backfill did not run', async ({ page }) => {
  await page.goto(URL);
  await ready(page);
  await pinEvaluate(page, SEED);
  await gotoPinned(page, URL);                 // run 1
  await ready(page);
  await page.waitForFunction(() => !!(window as any)._vaultBackfillUndo_v2203, null,
                             { timeout: 60000 });
  // the undo's OWN stamp is what must not move; d2r_owned keeps changing for unrelated reasons
  const first = await page.evaluate(() =>
    (window as any).LSR.getItem('d2r_vaultBackfillUndo_v2205'));

  await page.goto(URL);                       // run 2 — must be inert
  await ready(page);
  await page.waitForTimeout(1200);
  const second = await page.evaluate(() => ({
    ran: !!(window as any)._vaultBackfillUndo_v2203,
    stamp: (window as any).LSR.getItem('d2r_vaultBackfillUndo_v2205'),
  }));
  expect(second.ran, 'the undo ran a SECOND time — it is stamped for exactly this reason').toBe(false);
  expect(second.stamp, 'the undo rewrote its own record on a later boot, so it did not settle')
    .toBe(first);

  // a fresh machine — his cousin's — must never see it fire
  await pinEvaluate(page, () => {
    const w = window as any;
    w.LSR.removeItem('d2r_vaultBackfill_v2200');
    w.LSR.removeItem('d2r_vaultBackfillUndo_v2203');
    /* ⚠ REAL CATALOGUE NAMES. This used to seed ['Shako','Occulus'], which are NOT names the
       board knows — the real ones are "Harlequin Crest (Shako)" and "The Oculus". So the load-time
       cleaners removed them and this assertion blamed the UNDO for a deletion the undo never made.
       It had simply never been reached: an earlier assertion in this test failed first for years,
       so fixing those exposed this one rather than breaking it.
       Measured on the page: with real names the vault is untouched, assigned or not; with the
       bogus pair only "Shako" survived. */
    w.LSR.setItem('d2r_owned', JSON.stringify(['Harlequin Crest (Shako)', 'The Oculus']));
  });
  await gotoPinned(page, URL);
  await ready(page);
  await page.waitForTimeout(1200);
  const fresh = await page.evaluate(() => ({
    ran: !!(window as any)._vaultBackfillUndo_v2203,
    owned: JSON.parse((window as any).LSR.getItem('d2r_owned') || '[]'),
  }));
  expect(fresh.ran, 'the undo fired on a machine where the bad backfill never ran').toBe(false);
  expect(fresh.owned, 'it touched a vault it had no business touching')
    .toEqual(['Harlequin Crest (Shako)', 'The Oculus']);
});

test('the v2200 backfill is RETIRED, so a fresh machine is never filled wrongly', async ({ page }) => {
  await page.goto(URL);
  await ready(page);
  const out = await pinEvaluate(page, () => {
    const w = window as any;
    // a clean machine with a real ledger — exactly the state that made his vault wrong
    w.LSR.setItem('d2r_foundLog', JSON.stringify({ Shako: '01/01/2026', Occulus: '01/01/2026' }));
    w.LSR.setItem('d2r_setPieces', JSON.stringify(["Tal Rasha's Adjudication"]));
    w.LSR.setItem('d2r_owned', JSON.stringify([]));
    w.LSR.removeItem('d2r_vaultBackfill_v2200');
    w.LSR.removeItem('d2r_vaultBackfillUndo_v2203');
    return true;
  });
  expect(out).toBe(true);
  await gotoPinned(page, URL);
  await ready(page);
  await page.waitForTimeout(1500);
  const after = await page.evaluate(() => ({
    owned: JSON.parse((window as any).LSR.getItem('d2r_owned') || '[]').length,
    flag: (window as any).LSR.getItem('d2r_vaultBackfill_v2200'),
  }));
  // THE WHOLE POINT: found-ever must never become physically-in-your-stash again
  expect(after.owned, 'the retired v2200 backfill still filled the vault from the found-ever '
    + 'ledger on a fresh machine — his cousin would get the same wrong vault he did').toBe(0);
  expect(after.flag, 'it did not stamp its flag, so it will be reconsidered on every load')
    .toBeTruthy();
});
