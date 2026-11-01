import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v644 — THE GRAIL LEDGER (Konyo: "how do i mark a found item? it needs found/created — forge
// same logic that gets tallied back and forth! synced smart logic. flagship style").
// Every missing unique/piece is one-click tickable EVERYWHERE, every found gets a DATED ledger
// entry (d2r_foundLog — the found-chronicle), undo-last, and the tallies sync both directions.

async function cleanup(page: any) {
  await page.evaluate(() => {
    ['Nagelring', 'Manald Heal'].forEach((n) => {
      const o = JSON.parse(localStorage.getItem('d2r_foundLog') || '{}'); delete o[n];
      localStorage.setItem('d2r_foundLog', JSON.stringify(o));   // v677 — un-find = ledger removal
    });
    const sp = new Set(JSON.parse(localStorage.getItem('d2r_setPieces') || '[]'));
    [...sp].filter((p: any) => /Hsarus/.test(p)).forEach((p) => sp.delete(p));
    localStorage.setItem('d2r_setPieces', JSON.stringify([...sp]));
    localStorage.removeItem('d2r_foundLog');
  });
}

test('F·Uniques: every missing unique is tickable in ALL MISSING; ticking dates the ledger, tallies the calc, arms undo — and undo restores', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(2000);
  await cleanup(page);
  await page.evaluate(() => { (window as any).switchTab('funi'); });
  await page.waitForTimeout(700);
  const r1 = await page.evaluate(() => {
    const w: any = window; const box = document.getElementById('tab-funi')!;
    const wallTicks = (title: string) => {
      const wall = [...box.querySelectorAll('.gf-wall')].find((el) => (el.querySelector('.gf-wall-t') as HTMLElement | null)?.textContent === title);
      return wall ? wall.querySelectorAll('.gf-allgrid [data-gf-tick]').length : 0;
    };
    const gridTicks = wallTicks('Every missing unique — tick as you find');
    const colTicks = wallTicks('Colossal jewels — tick as you find');
    const chipTicks = box.querySelectorAll('.gf-chip .gf-tick').length;
    return { missingCount: w.funiScan().total - w.funiScan().found, gridTicks, chipTicks, colTicks };
  });
  expect(r1.gridTicks).toBe(r1.missingCount);       // EVERY missing unique has a one-click tick
  expect(r1.colTicks).toBe(6);                      // the six colossal jewels are their own wall, outside the hunt list
  expect(r1.chipTicks).toBeGreaterThan(10);         // run-card chips carry the tick too
  const r2 = await page.evaluate(async () => {
    const w: any = window; const box = document.getElementById('tab-funi')!;
    // v679 — Nagelring joined the seed (Konyo-confirmed gap find): target the FIRST missing unique dynamically
    const targetName = w.funiScan().missing[0].n;
    const tick = [...box.querySelectorAll('.gf-allgrid [data-gf-tick]')].find((t: any) => t.getAttribute('data-gf-tick') === targetName) as any;
    tick.click();
    await new Promise((res) => setTimeout(res, 700));
    const log = JSON.parse(localStorage.getItem('d2r_foundLog') || '{}');
    const ownedNow = !!JSON.parse(localStorage.getItem('d2r_foundLog') || '{}')[targetName];   // v677
    const undoBar = box.querySelector('.gf-undo-bar');
    const undoNames = undoBar ? undoBar.textContent || '' : '';
    // FOUND view shows the dated entry, newest first
    w.funiSetFilter('found');
    await new Promise((res) => setTimeout(res, 400));
    const foundView = box.querySelector('.forge-sec-now .gf-chips');
    const firstFound = foundView ? (foundView.querySelector('.gf-piece') as any) : null;
    return {
      targetName,
      dated: !!log[targetName], ownedNow, undoShows: undoNames.includes(targetName),
      newestFirst: firstFound ? (firstFound.textContent || '').includes(targetName) : false,
      dateShown: firstFound ? /·|20\d\d|Jul|Jan/.test((firstFound.querySelector('.gp-date') || {} as any).textContent || '') : false,
    };
  });
  expect(r2.dated).toBe(true);
  expect(r2.ownedNow).toBe(true);                   // tallied to the Calculator's store
  expect(r2.undoShows).toBe(true);
  expect(r2.newestFirst).toBe(true);
  expect(r2.dateShown).toBe(true);
  const r3 = await page.evaluate(async (targetName: string) => {
    const w: any = window; const box = document.getElementById('tab-funi')!;
    (box.querySelector('.gf-undo-bar button') as any).click();
    await new Promise((res) => setTimeout(res, 600));
    return {
      restored: !JSON.parse(localStorage.getItem('d2r_foundLog') || '{}')[targetName],   // v677
      logCleared: !JSON.parse(localStorage.getItem('d2r_foundLog') || '{}')[targetName],
    };
  }, r2.targetName);
  await cleanup(page);
  expect(r3.restored).toBe(true);
  expect(r3.logCleared).toBe(true);
});

test('F·Sets: pieces tick with the same ledger — dated, undoable, synced to the Set Tracker store', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(2000);
  await cleanup(page);
  await page.evaluate(() => { (window as any).switchTab('fsets'); });
  await page.waitForTimeout(700);
  const r = await page.evaluate(async () => {
    const w: any = window; const box = document.getElementById('tab-fsets')!;
    const gridTicks = box.querySelectorAll('.gf-allgrid [data-gf-tick]').length;
    const roster: string[] = []; (w.__allSets() || []).forEach((s: any) => (s.pieces || []).forEach((p: string) => roster.push(p)));
    const held = new Set(JSON.parse(localStorage.getItem('d2r_setPieces') || '[]'));
    const missingN = roster.filter((n) => !held.has(n)).length;
    const anyTick = [...box.querySelectorAll('.gf-allgrid [data-gf-tick]')][0] as any;
    const pieceName = anyTick.getAttribute('data-gf-tick');
    anyTick.click();
    await new Promise((res) => setTimeout(res, 700));
    const log = JSON.parse(localStorage.getItem('d2r_foundLog') || '{}');
    const have = JSON.parse(localStorage.getItem('d2r_setPieces') || '[]').includes(pieceName);
    const undoBar = box.querySelector('.gf-undo-bar');
    (undoBar!.querySelector('button') as any).click();
    await new Promise((res) => setTimeout(res, 600));
    const haveAfter = JSON.parse(localStorage.getItem('d2r_setPieces') || '[]').includes(pieceName);
    return { gridTicks, missingN, dated: !!log[pieceName], have, undone: !haveAfter };
  });
  await cleanup(page);
  // v3525 — the LAW, not a count: every missing piece is tickable. '> 20' was v682 arithmetic (seed 108/135); the seed
  // is 118 now, and REG-1548 rightly stopped the Aug-21 reading from un-ticking the two pieces the seed itself dates
  // after it (Laying of Hands, Taebaek's Glory) — which took the old count from 22 to 20.
  expect(r.gridTicks, 'a missing piece has no tick in the grid').toBe(r.missingN);
  expect(r.gridTicks).toBeGreaterThan(0);
  expect(r.dated).toBe(true);
  expect(r.have).toBe(true);
  expect(r.undone).toBe(true);
});
