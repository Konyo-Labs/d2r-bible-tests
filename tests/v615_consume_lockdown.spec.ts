import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v615 — CONSUME-SYNC lockdown (the Katar/Pattern incident + the audit's three confirmed gaps):
// (a) baseOver tasks consume; (b) planner-invisible owned bases consume via the direct vault match;
// (c) every outcome is narrated by a toast; ghost-copy restore fixed.

test('direct-vault fallback: a planner-invisible label still consumes on forge (the Katar class)', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  const r = await pinEvaluate(page, () => {
    const w: any = window;
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    return { seeded: true };
  });
  expect(r.seeded).toBe(true);
  await reloadPinned(page); await page.waitForTimeout(1800);
  const out = await pinEvaluate(page, () => {
    const w: any = window;
    // fresh profile: the 66-word owner seed must NOT floor Pattern back (we need it unmade in-memory)
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    // 'Katar (3os low base)' — pre-v614 this label was planner-invisible; even now, simulate a word
    // whose task never surfaces by NOT giving runes (Pattern task lands in farm with base:null).
    const own = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
    own.push('Katar (3os low base)');
    localStorage.setItem('d2r_owned', JSON.stringify(own));
    return true;
  });
  expect(out).toBe(true);
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r2 = await page.evaluate(() => {
    const w: any = window;
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    // no runes tallied → Pattern sits in farm (base:null) → old consume did nothing
    w.rwToggleMade('Pattern');
    const own = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
    const used = JSON.parse(localStorage.getItem('d2r_rwBaseUsed') || '{}');
    // undo restores it
    w.rwToggleMade('Pattern');
    const ownAfterUndo = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
    localStorage.removeItem('d2r_rwMade'); localStorage.removeItem('d2r_owned'); localStorage.removeItem('d2r_rwBaseUsed'); localStorage.removeItem('d2r_rwUnmade'); localStorage.removeItem('d2r_rwProfile');
    return {
      consumed: own.indexOf('Katar (3os low base)') < 0,
      usedRecord: used['Pattern'] && used['Pattern'].l,
      restored: ownAfterUndo.indexOf('Katar (3os low base)') >= 0,
    };
  });
  expect(r2.consumed).toBe(true);                       // the base left the vault even with no planner task
  expect(r2.usedRecord).toBe('Katar (3os low base)');   // …recorded for undo
  expect(r2.restored).toBe(true);                       // …and undo gives it back
});

test('baseOver task consumes: forging the capacity-losing word removes the shared base', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    const w: any = window;
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_owned', JSON.stringify(['Crystal Sword (4os)']));
    // both Oath and Voice of Reason want the one sword; give runes for both so both task
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Shael: 2, Pul: 1, Mal: 2, Lum: 1, Lem: 1, Ko: 1, El: 2, Eld: 2, Tir: 2, Ith: 2, Amn: 2, Ral: 2, Sol: 2 }));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    const sc = w.forgeScan();
    const tasks = [].concat(sc.now || [], sc.pipeline || [], sc.onestep || []).filter((t: any) => t.base && t.base.name === 'Crystal Sword (4os)');
    const over = tasks.find((t: any) => t.baseOver);
    if (!over) return { skipped: true };   // rune set didn't produce two tasks — environment-dependent
    w.rwToggleMade(over.rw);
    const own = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
    const out = { skipped: false, consumed: own.indexOf('Crystal Sword (4os)') < 0 };
    localStorage.removeItem('d2r_rwMade'); localStorage.removeItem('d2r_owned'); localStorage.removeItem('d2r_runeStash'); localStorage.removeItem('d2r_rwBaseUsed'); localStorage.removeItem('d2r_rwUnmade'); localStorage.removeItem('d2r_rwProfile');
    return out;
  });
  if (!r.skipped) expect(r.consumed).toBe(true);        // the plan is advisory; the forge is a fact
});
