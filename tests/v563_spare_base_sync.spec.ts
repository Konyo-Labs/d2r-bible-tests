import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v563 — SPARE-BASE sync (the vault-side twin of the loot filter's v536.2 Forge sync): a scanned base whose
// every still-unmade runeword is ALREADY COVERED by a socket-correct base you own routes to __throwout as a
// "spare — you already hold a base for X". Self-exclusion by registered label: the covering base itself never
// flags as its own spare, so with two copies exactly one stays kept and one flags.

test('spare base → __throwout ("you already hold a base for it"); the covering base itself stays kept', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('d2r_owned', JSON.stringify(['Colossus Voulge (4os)']));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Ral: 1, Tir: 1, Tal: 1, Sol: 1 }));
    // NOTE: rwMade is deliberately NOT set here — addInitScript re-runs on reload and would stomp the
    // pinned Chronicle written below (the v578.1 lesson).
    localStorage.setItem('d2r_ladderMode', 'nonladder');
  });
  await page.goto(URL); await page.waitForTimeout(1500);
  // v578.1 — pin the Chronicle BEFORE the scan-relevant load (forgeScan reads the BOOT-loaded chronicle,
  // and Insight joined the durable seed): every word made EXCEPT Insight, fresh profile, then reload.
  await pinEvaluate(page, () => {
    const w: any = window;
    const made: any = {}; Object.keys(w.RUNEWORD_TIP || {}).forEach((n) => { if (n !== 'Insight') made[n] = 'x'; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    localStorage.setItem('d2r_rwProfile', 'fresh');
  });
  await reloadPinned(page); await page.waitForTimeout(1500);
  await page.evaluate(() => { (window as any).switchTab && (window as any).switchTab('tools'); (window as any).renderVault && (window as any).renderVault(); });
  const r = await page.evaluate(async () => {
    const w: any = window;
    w._ensureSocketBaseEntry('Colossus Voulge (4os)');
    await new Promise((res) => setTimeout(res, 500));       // let the 400ms _spareBaseInfo forgeScan memo expire
    const dup = w.suggestMule('Thresher (4os)');            // different 4os polearm, same one unmade word
    const keeper = w.suggestMule('Colossus Voulge (4os)');  // the covering base itself (self-exclusion)
    return {
      dupId: dup && dup.id, dupWhy: String((dup && dup.why) || ''),
      keeperId: keeper && keeper.id, keeperWhy: String((keeper && keeper.why) || ''),
    };
  });
  expect(r.dupId).toBe('__throwout');
  expect(r.dupWhy).toContain('spare');
  expect(r.dupWhy).toContain('Colossus Voulge (4os)');      // names the base you already hold
  expect(r.keeperId).toBe('bases');                         // the assigned base never flags as its own spare
  expect(r.keeperWhy).toContain('Insight');
});

test('no owned coverage → the same base stays a keeper (spare logic only fires on real duplication)', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('d2r_owned', JSON.stringify([]));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Ral: 1, Tir: 1, Tal: 1, Sol: 1 }));
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_ladderMode', 'nonladder');
  });
  await page.goto(URL); await page.waitForTimeout(1500);
  await page.evaluate(() => { (window as any).switchTab && (window as any).switchTab('tools'); (window as any).renderVault && (window as any).renderVault(); });
  const r = await page.evaluate(() => {
    const w: any = window;
    const made: any = {}; Object.keys(w.RUNEWORD_TIP || {}).forEach((n) => { if (n !== 'Insight') made[n] = 'x'; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    const sg = w.suggestMule('Thresher (4os)');
    return { id: sg && sg.id, why: String((sg && sg.why) || '') };
  });
  expect(r.id).toBe('bases');
  expect(r.why).toContain('Insight');
});
