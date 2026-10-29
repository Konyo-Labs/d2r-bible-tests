import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v619 — GRAIL FORGES found-sync + completion seals (Konyo: 'same smart automated logic… cancels
// out and stamps when completely finished'). (a) funiScan groups the FULL verified pool per run:
// all-found runs earn the 🏆 Sealed-grounds band; quick-wins all found → the seal, not an empty tab.
// (b) F·Sets: completed sets wear the seal band; toggles from EITHER surface re-scan the other.
// (c) toggleOwned live-syncs an open grail-forge tab both ways.

test('sealed grounds: a run whose whole verified pool is found earns the band and leaves Best runs', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  const r = await pinEvaluate(page, () => {
    const w: any = window;
    // v1717 — ASK THE ENGINE, NOT A LIST THAT NO LONGER MATCHES IT.
    // This rebuilt the run grouping itself out of `ITEMS`, then owned that pool and expected
    // funiScan to seal the run. After the silospen pull ITEMS is the CALCULATOR's curated 322
    // while funiScan groups the 387-name roster through ITEM_REGISTRY — so the pool computed
    // here could miss items the engine counts, and a run that was "fully owned" by this test's
    // arithmetic was still missing one by the engine's. Sealing is the engine's own verdict, so
    // the setup now reads the engine's own runs: own every MISSING item of its smallest run, and
    // everything else in that run's pool is already found by definition.
    const fu = w.funiScan();
    const run = (fu.runs || [])
      .filter((g: any) => g.bossId && (g.items || []).length >= 2)
      .sort((a: any, b: any) => a.items.length - b.items.length)[0];
    const target = run.boss;
    localStorage.setItem('d2r_owned', JSON.stringify(run.items.map((x: any) => x.n)));
    return { target, n: run.items.length };
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r2 = await page.evaluate((target: string) => {
    const w: any = window;
    const s = w.funiScan();
    w.switchTab('funi');
    const dom = (document.getElementById('funi-body') || document.body).textContent || '';
    localStorage.removeItem('d2r_owned');
    return {
      sealed: (s.sealed || []).some((g: any) => g.boss === target),
      inRuns: (s.runs || []).some((g: any) => g.boss === target),
      bandInDom: dom.includes('grounds sealed') && dom.includes(target),
    };
  }, r.target);
  expect(r2.sealed).toBe(true);     // the full pool is found → sealed
  expect(r2.inRuns).toBe(false);    // …and it left the farm list (cancel-out sync)
  expect(r2.bandInDom).toBe(true);  // …wearing the horizontal seal in the rendered tab
});

test('completed sets wear the seal band; checklist⇄fsets sync both ways', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  const r = await pinEvaluate(page, () => {
    const w: any = window;
    const sets = (typeof w.__allSets === 'function') ? w.__allSets() : [];
    const small = sets.slice().sort((a: any, b: any) => a.pieces.length - b.pieces.length)[0];
    localStorage.setItem('d2r_setPieces', JSON.stringify(small.pieces));
    return { set: small.name, n: small.pieces.length };
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r2 = await page.evaluate((setName: string) => {
    const w: any = window;
    w.switchTab('fsets');
    const dom1 = (document.getElementById('fsets-body') || document.body).textContent || '';
    // v693.2 recalibration — v693 collapsed the per-set seals into ONE summary band on ▦ All
    // ('✓ N sets complete'); assert the aggregate count instead of per-set text.
    const m1 = dom1.match(/(\d+) sets? complete/);
    const hadBand = !!m1;
    const n1 = m1 ? parseInt(m1[1], 10) : 0;
    // un-tick one piece from the CHECKLIST side while fsets is the active tab → the band must leave live
    const s = w.fsetsScan();
    const done = s.done[0];
    w.toggleSetPiece(done.pieces[0].name);
    const dom2 = (document.getElementById('fsets-body') || document.body).textContent || '';
    localStorage.removeItem('d2r_setPieces');
    const m2 = dom2.match(/(\d+) sets? complete/);
    const n2 = m2 ? parseInt(m2[1], 10) : 0;
    return { hadBand, n1, n2 };
  }, r.set);
  expect(r2.hadBand).toBe(true);      // the summary band wears the aggregate seal
  expect(r2.n2).toBe(r2.n1 - 1);      // checklist un-tick re-scanned the open fsets tab live (count fell)
});

test('toggleOwned live-syncs an open F·Uniques tab', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => new Promise<any>((res) => {
    const w: any = window;
    w.switchTab('funi');
    setTimeout(() => {
      const s = w.funiScan();
      const target = s.missing[0].n;
      const before = (document.getElementById('funi-body')!.textContent || '').includes(target);
      w.toggleOwned(target);   // found via ANY surface while funi is open
      setTimeout(() => {
        const s2 = w.funiScan();
        const gone = !s2.missing.some((x: any) => x.n === target);
        w.toggleOwned(target);   // restore
        res({ before, gone });
      }, 400);
    }, 500);
  }));
  expect(r.gone).toBe(true);
});
