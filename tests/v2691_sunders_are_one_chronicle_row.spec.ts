import { test, expect } from '@playwright/test';
import path from 'path';

/* v2691 — HIS SUNDER RULING, AND THE HALF THAT BROKE LAST TIME.
 *
 * Konyo, with a screenshot of "Latent Bone Break" as its own chronicle row: "this is not a
 * duplicate.. yes we have latent of bone break but the chronicle itself is not latent thats just
 * the upgraded version of it after we upgrade in hordaic cube.. so for the chronicle all sunders
 * 6 of them need to be counted in the chronicle specifically as 1 tally for each.. and for the
 * vault that a different story the entire item database should be there regardless."
 *
 * ⚠⚠ THIS SPEC EXISTS BECAUSE THE FIRST ATTEMPT WAS REVERTED. v2680 filtered `_roster()`, which is
 * ALSO what makes an item findable and openable, so it removed the Latent charms from the HUNT as
 * well as the tally — breaking his earlier v1720 ruling ("add the 11 rotw items to the roster")
 * and silently subtracting from his found count. Eight failures, all mine, reverted in v2685.
 * So this asserts BOTH directions: the chronicle lists one row per sunder, AND nothing his ledger
 * holds stopped counting. A green on the first alone is the exact regression that shipped before.
 */
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');
const BASES = ['Bone Break', 'Cold Rupture', 'Crack of the Heavens',
               'Flame Rift', 'Rotting Fissure', 'Black Cleft'];

async function boot(page: any) {
  await page.goto(URL);
  await page.waitForTimeout(2500);
}

test('the chronicle lists ONE row per sunder, and the roster still holds every form', async ({ page }) => {
  await boot(page);
  const r = await page.evaluate((bases: string[]) => {
    const w: any = window;
    const roster = w._gUniqueRoster ? w._gUniqueRoster() : null;
    const rnames: string[] = roster ? Object.keys(roster).map((k) => roster[k]) : [];
    const scan = w.funiScan();
    const missing = (scan.missing || []).map((x: any) => x.n);
    const hit = (list: string[]) =>
      list.filter((nm) => bases.some((b) => String(nm).indexOf(b) >= 0));
    return {
      rosterSize: rnames.length,
      rosterSunders: hit(rnames).length,
      chronicleTotal: scan.found + (scan.missing || []).length,
      found: scan.found,
      missingSunders: hit(missing),
      upgradedInMissing: hit(missing).filter(
        (n: string) => n.indexOf('Latent ') === 0 || n.indexOf('Renewed ') === 0).length,
    };
  }, BASES);

  /* A SAMPLE OF ZERO PASSES EVERYTHING BELOW — refuse rather than report clean. */
  expect(r.rosterSize, 'the roster did not build — this test measured NOTHING').toBeGreaterThan(300);

  expect(r.upgradedInMissing,
    `the chronicle is still asking him to find upgraded spellings: ${JSON.stringify(r.missingSunders)}`)
    .toBe(0);

  /* THE ROSTER KEEPS EVERY FORM — his v1720 ruling, and the half v2680 broke. The vault reads the
     roster, and he asked for "the entire item database" there regardless. */
  expect(r.rosterSunders,
    'the roster lost a sunder spelling — that is v2680s regression returning: the item stops being '
    + 'openable and the vault stops holding it')
    .toBeGreaterThanOrEqual(12);

  /* The hunt cards are 397. The file count stays 403 because six quest rows sit in it
     and are not cards. The roster is a different surface and still keeps the Latent
     spellings, so chronicleTotal is no longer rosterSize - 6. */
  expect(r.chronicleTotal,
    'the hunt cards are 397; the six quest rows stay off this list')
    .toBe(397);
});

test('an upgraded sunder in his ledger still counts as found', async ({ page }) => {
  /* THE SUBTRACTION GUARD, AND THE REASON THIS FILE EXISTS. A ledger tick on "Latent Bone Break"
     must satisfy the base chronicle row, or dropping that row silently deletes one of his own
     finds — which is exactly what v2680 did to four of them (236 -> 232).
     [[d2r-ladder-doctrine]]: a display rule must never change a count.
     ⚠ Driven through the REAL path — a ledger seed and funiScan's own missing list — rather than
     through a window export invented for the test. A probe that only the test can call proves the
     probe. */
  await page.addInitScript(() => {
    try {
      if (localStorage.getItem('__v2691_seeded') === '1') return;
      localStorage.clear();
      localStorage.setItem('d2r_ownerClaim', '*');
      localStorage.setItem('d2r_foundLog', JSON.stringify({ 'Latent Bone Break': '2026-08-01' }));
      localStorage.setItem('__v2691_seeded', '1');
    } catch (e) {}
  });
  await page.goto(URL);
  await page.waitForTimeout(2800);

  const r = await page.evaluate(() => {
    const w: any = window;
    const scan = w.funiScan();
    const missing = (scan.missing || []).map((x: any) => x.n);
    return {
      found: scan.found,
      total: scan.found + missing.length,
      baseIsMissing: missing.indexOf('Bone Break') >= 0,
      latentIsMissing: missing.indexOf('Latent Bone Break') >= 0,
      upgradedFn: typeof w._isUpgradedSunder,
    };
  });

  expect(r.upgradedFn, 'the sunder alias helper is absent — the fix is not present at all').toBe('function');
  expect(r.total, 'the chronicle universe is empty, so nothing below is being measured')
    .toBeGreaterThan(300);
  expect(r.latentIsMissing,
    'the chronicle is still listing the upgraded spelling as its own row to hunt').toBe(false);
  expect(r.baseIsMissing,
    'he holds "Latent Bone Break" — the cube-upgraded form of the same item — and the board is '
    + 'still asking him to find "Bone Break". Dropping the upgraded row without aliasing it is the '
    + 'silent subtraction v2685 reverted.').toBe(false);
});
