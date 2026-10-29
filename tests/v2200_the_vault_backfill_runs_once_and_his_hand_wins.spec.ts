import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, gotoPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v2200 → RETIRED IN v2203, AND THIS SPEC NOW GUARDS THE RETIREMENT.
//
// What v2200 did: it filled the vault from `d2r_foundLog` — "everything ever FOUND" — and wrote it
// into `d2r_owned`, which means "physically in your stash". Finding an item once does not mean you
// still hold it. On his board that took the vault 5 → 405 while the actual stash evidence
// (tv/vault_seen.json) was SEVENTEEN rows.
//
// v2203 retired it. The block stamps its flag with the reason and returns; everything below the
// return is `eslint-disable no-unreachable` dead code, INCLUDING the line that used to publish
// `window._vaultBackfill_v2200`. It is left in place rather than deleted so the v2203 undo can
// still recognise a machine where it ran.
//
// ⚠ WHY THIS SPEC WAS RED FOR MONTHS, AND WHAT THAT COST. Its three tests all waited up to 60s for
// `window._vaultBackfill_v2200` — a report that is now deliberately never produced. Three timeouts
// per run inside `Routine I`, a suite that has been red long enough to stop being read. A spec
// asserting a design that has since changed does not just fail; it hides the failures around it.
// [[regression-guard]] [[label-outlived-referent]]
//
// ⚠ AND THE PROTECTION IS KEPT, NOT DELETED. Deleting the file would leave nothing standing
// between his vault and a re-enable of the wrong-source fill. So the assertions moved from the
// MECHANISM (did the migration run, how fast, how many rows) to the LAW: the physical vault is
// never populated from the found-ever ledger, and his own placements are never overwritten.

const SEED = `(function(){
  var R = window.ITEM_REGISTRY || {};
  var names = Object.keys(R);
  var isSet = function(n){ var i = R[n]; return i && i.tier === 'set'; };
  var uni = names.filter(function(n){ return !isSet(n); });
  var setp = names.filter(isSet);
  var fl = {}; uni.slice(0, 392).forEach(function(n){ fl[n] = '08/20/2026'; });
  var sp = setp.slice(0, 120);            // ARRAY — the shape the board actually writes
  var own = uni.slice(0, 5);
  var asg = {}; own.slice(0, 4).forEach(function(n){ asg[n] = '__keep'; });
  window.LSR.setItem('d2r_foundLog', JSON.stringify(fl));
  window.LSR.setItem('d2r_setPieces', JSON.stringify(sp));
  window.LSR.setItem('d2r_owned', JSON.stringify(own));
  window.LSR.setItem('d2r_muleAssign', JSON.stringify(asg));
  window.LSR.removeItem('d2r_vaultBackfill_v2200');
  return { ledger: Object.keys(fl).length + sp.length, manual: own.slice(0, 4) };
})()`;

async function ready(page: any) {
  await page.waitForFunction(
    () => typeof (window as any).tvVaultRegister === 'function'
       && typeof (window as any).LSR !== 'undefined', null, { timeout: 120000 });
}

test('the found-ever ledger never becomes the physical vault', async ({ page }) => {
  await page.goto(URL);
  await ready(page);
  const seed = await pinEvaluate(page, SEED);

  // the fixture must actually EXERCISE the gap, or every assertion below is vacuous
  expect(seed.ledger, 'the seeded ledger is too small to reproduce his situation')
    .toBeGreaterThan(400);
  expect(seed.manual.length, 'no manual placements were seeded, so "his hand wins" is untested')
    .toBe(4);

  await gotoPinned(page, URL);                  // the migration would run at boot, if it still ran
  await ready(page);
  await page.waitForTimeout(2000);

  const r = await page.evaluate(() => {
    const w = window as any;
    return {
      published: (w as any)._vaultBackfill_v2200,
      flag: w.LSR.getItem('d2r_vaultBackfill_v2200'),
      owned: JSON.parse(w.LSR.getItem('d2r_owned') || '[]').length,
      assign: JSON.parse(w.LSR.getItem('d2r_muleAssign') || '{}'),
    };
  });

  // THE LAW. 512 ledger names must not become 512 items he is told he is holding.
  expect(r.owned, `the vault holds ${r.owned} items from a ${seed.ledger}-name ledger — the `
    + 'found-ever fill is back, and it tells him he owns things he sold months ago')
    .toBeLessThan(100);

  // and his own hand is untouched
  for (const n of seed.manual as string[]) {
    expect(r.assign[n], `a migration overwrote his manual placement of "${n}"`).toBe('__keep');
  }
});

test('the retirement is stamped, and says why', async ({ page }) => {
  await page.goto(URL);
  await ready(page);
  await pinEvaluate(page, SEED);
  await gotoPinned(page, URL);
  await ready(page);
  await page.waitForTimeout(2000);

  const out = await page.evaluate(() => {
    const w = window as any;
    return {
      flag: w.LSR.getItem('d2r_vaultBackfill_v2200'),
      published: (w as any)._vaultBackfill_v2200 === undefined ? null : 'present',
    };
  });

  // ⚠ THE FLAG IS STILL WRITTEN ON PURPOSE: the v2203 undo recognises a machine by it, and a
  // FRESH machine — his cousin's — must never get the wrong vault. Stamping it is what guarantees
  // that. A retirement that left no trace would be indistinguishable from a migration that simply
  // never fired.
  expect(out.flag, 'the retirement stamp is gone; the v2203 undo can no longer recognise a '
    + 'machine where the bad migration ran').toBeTruthy();
  expect(String(out.flag), 'the stamp no longer says WHY it is retired, so the next reader has to '
    + 'rediscover that found-ever is not stash evidence').toContain('retired');

  // the report is dead code below a `return`; if it reappears, the migration is live again
  expect(out.published, 'the v2200 backfill is publishing a report again — the retired block is '
    + 'running, and his vault is about to be filled from the wrong ledger').toBeNull();
});

test('it does nothing on an empty ledger either', async ({ page }) => {
  await page.goto(URL);
  await ready(page);
  await pinEvaluate(page, () => {
    const w = window as any;
    w.LSR.setItem('d2r_foundLog', '{}');
    w.LSR.setItem('d2r_setPieces', '[]');
    w.LSR.setItem('d2r_owned', '[]');
    w.LSR.removeItem('d2r_vaultBackfill_v2200');
  });
  await gotoPinned(page, URL);
  await ready(page);
  await page.waitForTimeout(1500);

  const out = await page.evaluate(() => ({
    published: (window as any)._vaultBackfill_v2200 === undefined ? null : 'present',
    owned: JSON.parse((window as any).LSR.getItem('d2r_owned') || '[]').length,
  }));
  expect(out.published, 'the retired migration ran on an empty ledger').toBeNull();
  expect(out.owned, 'items appeared in an empty vault from nowhere').toBe(0);
});
