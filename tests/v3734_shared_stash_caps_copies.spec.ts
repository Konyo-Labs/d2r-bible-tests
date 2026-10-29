import { test, expect } from '@playwright/test';
import { pinEvaluate, reloadPinned } from './_pin';

// v3767 (Elad 2026-10-18 13:18 IDT) — every physical copy sits on the shared stash; the old cap of 2 is retired.
// L1 (Elad 2026-10-20 22:05) then capped the WAR STASH by footprint: rings/amulets every copy, other small gear 4, big gear
// 1 — the copies over it go to WAR1, WAR2 ... #144.10 shared half (REG-2801, his ruling 2026-10-28: "the war stash is
// basically the shared stash with those 5 pages + the extra war mules") makes the shared stash window draw what that plan
// keeps there - the count its shelf card already drew. A 7-copy Grief draws min(7, its cap) cells; measured in node it is
// 4 (no stored base, so its footprint is the 1x2 guess - small gear); a stored 2x3 base makes it big gear and 1.

const NM = 'Grief';

test.beforeEach(async ({ page }) => {
  await page.goto('file://' + process.cwd() + '/bible.html');
  // seed 7 owned copies through the real store, then reload so the module loads them into copies[]
  await pinEvaluate(page, (nm) => {
    try {
      localStorage.setItem('d2r_ownerClaim', '*');
      localStorage.setItem('d2r_copies', JSON.stringify({ [nm]: 7 }));
      const owned = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
      if (owned.indexOf(nm) < 0) owned.push(nm);
      localStorage.setItem('d2r_owned', JSON.stringify(owned));
    } catch (e) {}
  }, NM);
  await reloadPinned(page);
  await page.waitForFunction(() => typeof (window as any)._sharedLayout === 'function');
});

test('the shared stash draws the copies its war cap keeps; the rest are the WAR mules\' (REG-2801)', async ({ page }) => {
  const r = await page.evaluate((nm) => {
    const w = window as any;
    const seeded = (JSON.parse(localStorage.getItem('d2r_copies') || '{}'))[nm];
    const lay = w._sharedLayout([nm]);
    const cells = ((lay && lay.pages) || []).reduce((a: number, p: any[]) => a + p.filter((q: any) => q && q.n === nm).length, 0);
    return { seeded, cells, cap: w._vaultWarCap(nm) };
  }, NM);
  // the seed took: 7 copies owned; the war cap bites (fewer than 7), and the stash draws exactly what it keeps
  expect(r.seeded).toBe(7);
  expect(r.cap, 'PREMISE: Grief is not capped below 7 in the war stash').toBeLessThan(7);
  expect(r.cells, 'the shared stash draws other than the copies its war cap keeps').toBe(Math.min(7, r.cap));
});
