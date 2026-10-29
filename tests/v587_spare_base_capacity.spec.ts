import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v587 — SPARE-BASE CAPACITY (Konyo's 1× Bone Visage): one physical base hosts ONE runeword. With a single
// owned base and TWO+ still-unmade words that fit it, the old logic marked EVERY word "covered by" that one
// copy and vendored the scanned candidate the other words still need. Now forgeScan runs a capacity ledger
// (t.baseOver on over-subscribed tasks) and _spareBaseInfo / the loot filter / smart insights only count a
// word as base-owned when a real copy is actually planned for it.

test('1 owned base + 2 unmade words → candidate stays a keeper; exactly one scan task flags baseOver', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('d2r_owned', JSON.stringify(['Colossus Voulge (4os)']));
    localStorage.setItem('d2r_runeStash', JSON.stringify({}));
    // NOTE: rwMade deliberately NOT set here — addInitScript re-runs on reload and would stomp the
    // pinned Chronicle written below (the v578.1 lesson).
    localStorage.setItem('d2r_ladderMode', 'nonladder');
  });
  await page.goto(URL); await page.waitForTimeout(1500);
  // Phase 1 — pin an EMPTY Chronicle (the boot seed pre-marks ~52 words made) and, with nothing made,
  // ask forgeScan which words it actually plans on the owned Voulge (survives the hand/endgame/ladder
  // gates), so the pinned pair below is never a gated word.
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_rwProfile', 'fresh');
  });
  await reloadPinned(page); await page.waitForTimeout(1500);
  await page.evaluate(() => { (window as any).switchTab && (window as any).switchTab('tools'); (window as any).renderVault && (window as any).renderVault(); });
  // v1910 — POLL, DO NOT SLEEP. This assertion failed TWICE on one CI runner (retries:1 = two
  // attempts) on v1909 — a commit that changed no page logic at all — and passed on a fresh runner
  // minutes later, same bytes. The spec waited on three fixed `waitForTimeout`s and a 400ms
  // _spareBaseInfo memo; on a loaded runner forgeScan had simply not planned both words yet.
  //
  // A flaky gate is the same defect as a lamp: it stops carrying information, and it trains
  // everyone to re-run instead of read. Polling is strictly MORE patient than a fixed sleep, so it
  // can only remove timing failures, never add one. [[feedback-blind-fixture-green-gate]]
  let hosted: string[] = [];
  const scanHosted = async (): Promise<string[]> => page.evaluate(() => {
    const w: any = window;
    w._ensureSocketBaseEntry('Colossus Voulge (4os)');
    const sc = w.forgeScan();
    const rws: string[] = [];
    [].concat(sc.now || [], sc.pipeline || [], sc.onestep || []).forEach((t: any) => {
      if (t && t.base && t.base.name === 'Colossus Voulge (4os)' && rws.indexOf(t.rw) < 0) rws.push(t.rw);
    });
    return rws;
  });
  await expect.poll(async () => {
    hosted = await scanHosted();
    return hosted.length;
  }, {
    timeout: 20000,
    intervals: [250, 500, 500, 1000, 1000, 2000],
    message: 'forgeScan never planned 2 runewords on the one owned Colossus Voulge (4os)',
  }).toBeGreaterThanOrEqual(2);
  const pair = hosted.slice(0, 2);
  // Phase 2 — pin the Chronicle: everything made EXCEPT the two Voulge-hostable words, then reload.
  await pinEvaluate(page, (keep: string[]) => {
    const w: any = window;
    const made: any = {}; Object.keys(w.RUNEWORD_TIP || {}).forEach((n) => { if (keep.indexOf(n) < 0) made[n] = 'x'; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    localStorage.setItem('d2r_rwProfile', 'fresh');
  }, pair);
  await reloadPinned(page); await page.waitForTimeout(1500);
  await page.evaluate(() => { (window as any).switchTab && (window as any).switchTab('tools'); (window as any).renderVault && (window as any).renderVault(); });
  const readLedger = async (keep: string[]) => page.evaluate(async (k: string[]) => {
    const w: any = window;
    w._ensureSocketBaseEntry('Colossus Voulge (4os)');
    await new Promise((res) => setTimeout(res, 500));       // let the 400ms _spareBaseInfo forgeScan memo expire
    const sc = w.forgeScan();
    const tasks: any[] = [];
    [].concat(sc.now || [], sc.pipeline || [], sc.onestep || []).forEach((t: any) => {
      if (t && t.base && t.base.name === 'Colossus Voulge (4os)' && k.indexOf(t.rw) >= 0) tasks.push({ rw: t.rw, over: !!t.baseOver });
    });
    const overRws = tasks.filter((t) => t.over).map((t) => t.rw);
    const dup = w.suggestMule('Thresher (4os)');            // different 4os polearm, SAME two unmade words
    const smart = (typeof w._smartUnmadeNeedingBase === 'function') ? w._smartUnmadeNeedingBase() : [];
    return {
      tasks, overRws,
      dupId: dup && dup.id, dupWhy: String((dup && dup.why) || ''),
      smartHasOver: overRws.length ? smart.indexOf(overRws[0]) >= 0 : false,
    };
  }, keep);
  // v1910 — the same patience on the second phase, for the same reason.
  let r = await readLedger(pair);
  await expect.poll(async () => {
    r = await readLedger(pair);
    return r.tasks.length;
  }, {
    timeout: 20000,
    intervals: [250, 500, 500, 1000, 1000, 2000],
    message: 'forgeScan never planned both pinned words on the one Voulge after the reload',
  }).toBe(2);
  // the ledger: both words planned on the ONE Voulge copy, exactly one over-subscribed
  expect(r.tasks.length).toBe(2);
  expect(r.overRws.length).toBe(1);
  // the verdict: the candidate is NOT a spare — the over-subscribed word still needs it
  expect(r.dupId).toBe('bases');
  expect(r.dupWhy).toContain(r.overRws[0]);
  // the sweep: smart insights agree the over-subscribed word still needs a base found for it
  expect(r.smartHasOver).toBe(true);
});
