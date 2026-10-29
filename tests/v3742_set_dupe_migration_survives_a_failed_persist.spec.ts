import { test, expect } from '@playwright/test';
import * as path from 'path';
import { pinEvaluate, gotoPinned } from './_pin';

// REG-2240 (#11) — THE SET-DUPE MIGRATION MUST NOT STAMP ITSELF DONE BEFORE THE REMOVAL REACHES DISK.
//
// window._vaultDedupeOldSetRows (REG-2229) removes the stray Unsorted copy of a set piece already filed
// in its mule. Before this fix it wrote the once-per-world stamp d2r_setDupeMigrate_v2227 AND folded the
// stray's copy count onto its twin BEFORE calling vaultRemove — and vaultRemove's persistOwned() wraps
// each setItem in its own try/catch, so a quota/private-mode throw on the d2r_owned write is SWALLOWED
// and vaultRemove still returns removed:[...]. So a failed owned write left the stamp set: the next
// reload saw "already run", skipped the migration, and the stray dock copy was stranded for good — with
// its copy count already moved onto the twin (a half-state).
//
// This test drives that exact failure by making ONLY the d2r_owned write throw during the migration.
//   RED (pre-fix): the stamp is written anyway (and the count folded), so a healthy reload never retries
//                  and the stray stays stranded.
//   GREEN (fixed): no confirmed remove => no stamp and no fold; a healthy reload migrates and the stray
//                  leaves, its count folded onto the surviving filed copy, his testimony untouched.

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

const BARE_TAL = "Tal Rasha's Horadric Crest";   const SLOT_TAL = "Tal Rasha's Horadric Crest (helm)";
const BARE_IK  = "Immortal King's Will";          const SLOT_IK  = "Immortal King's Will (helm)";
const LONE_EYE = "Tal Rasha's Lidless Eye";       // a loose set piece with NO filed twin — must STAY
const STAMP = 'd2r_setDupeMigrate_v2227';

const fold = (s: string) => String(s || '').replace(/[‘’ʼ´`]/g, "'").trim();

async function ready(page: any) {
  await page.waitForFunction(
    () => typeof (window as any).LSR !== 'undefined'
       && typeof (window as any).findSetPiece === 'function'
       && typeof (window as any).vaultRemove === 'function'
       && typeof (window as any)._vaultDockNames === 'function'
       && typeof (window as any)._vaultDedupeOldSetRows === 'function'
       && typeof (window as any).renderVault === 'function', null, { timeout: 120000 });
}

test('a failed owned-persist during the set-dupe migration leaves it UNstamped and UNfolded, so a healthy reload retries instead of stranding the stray', async ({ page }) => {
  await page.goto(URL);
  await ready(page);

  // Seed the OLD (pre-v3716) double-row state WITH the migration already stamped, so the auto-run on the
  // next load is a no-op and the strays survive in memory for us to drive the migration by hand. The
  // stray Tal Rasha carries a copy count of 3 so we can watch whether it is folded prematurely.
  await pinEvaluate(page, (s) => {
    const w = window as any;
    try { localStorage.setItem('d2r_ownerClaim', '*'); } catch (e) {}
    w.LSR.setItem('d2r_owned', JSON.stringify([s.bareTal, s.slotTal, s.bareIk, s.slotIk, s.loneEye]));
    w.LSR.setItem('d2r_muleAssign', JSON.stringify({ [s.slotTal]: 'sets-major', [s.slotIk]: 'sets-major' }));
    w.LSR.setItem('d2r_copies', JSON.stringify({ [s.bareTal]: 3 }));
    w.LSR.setItem(s.stamp, String(Date.now()));   // pre-stamp => the load's auto-run skips, strays survive
  }, { bareTal: BARE_TAL, slotTal: SLOT_TAL, bareIk: BARE_IK, slotIk: SLOT_IK, loneEye: LONE_EYE, stamp: STAMP });

  await gotoPinned(page, URL);
  await ready(page);
  await page.waitForTimeout(1200);

  // sanity: the premise of the bug — bare and slot forms canonicalise to the SAME piece, so one is a stray
  const premise = await page.evaluate(() => {
    const w = window as any;
    return { tal: ((w.findSetPiece("Tal Rasha's Horadric Crest") || {}) as any).piece,
             ik:  ((w.findSetPiece("Immortal King's Will") || {}) as any).piece };
  });
  expect(premise.tal, 'findSetPiece must canonicalise the bare Tal Rasha helm to its slot key').toBe(SLOT_TAL);
  expect(premise.ik, 'findSetPiece must canonicalise the bare Immortal King helm to its slot key').toBe(SLOT_IK);

  // PHASE 1 — make ONLY the d2r_owned write throw (quota/private), clear the stamp, run the migration.
  const phase1 = await page.evaluate((s) => {
    const w = window as any;
    const proto: any = (window as any).Storage.prototype;
    const orig = proto.setItem;
    proto.setItem = function (k: string, v: string) {
      if (String(k).endsWith('d2r_owned')) throw new Error('QuotaExceeded (test-injected)');
      return orig.call(this, k, v);
    };
    let ret: any = null, threw: string | null = null;
    try {
      w.LSR.removeItem(s.stamp);              // clear the pre-stamp; a correct migration re-stamps ONLY on a confirmed remove
      ret = w._vaultDedupeOldSetRows();
    } catch (e: any) { threw = String((e && e.message) || e); }
    proto.setItem = orig;                     // restore (the reload below gets a fresh realm anyway)
    return {
      ret, threw,
      stamp: w.LSR.getItem(s.stamp),
      copiesDisk: JSON.parse(w.LSR.getItem('d2r_copies') || '{}'),
      ownedDisk: JSON.parse(w.LSR.getItem('d2r_owned') || '[]'),
      busy: !!w._vaultDedupeBusy,
    };
  }, { stamp: STAMP });

  // the migration must handle the failed persist internally, not throw, and must clear its re-entrancy flag
  expect(phase1.threw, 'the migration must handle a failed owned-persist internally, not throw').toBeNull();
  expect(phase1.busy, 'the in-memory re-entrancy flag must be cleared when the migration returns').toBe(false);

  // DISCRIMINATOR A — a persist that never reached disk must NOT be stamped as done (so a reload can retry)
  expect(phase1.stamp, 'a failed owned-persist must leave the migration UNstamped so the next reload can retry').toBeFalsy();

  // DISCRIMINATOR B (no half-state) — the owned write threw, so the stray is still persisted; its copy
  // count must NOT have been folded onto the twin while the row still stands.
  expect(phase1.ownedDisk, 'the failed remove means the stray is still on disk (storage threw)').toContain(BARE_TAL);
  expect(phase1.copiesDisk[BARE_TAL], 'the stray copy count must not move onto the twin while the remove is unconfirmed').toBe(3);

  // PHASE 2 — a healthy reload (fresh realm, storage works): the now-unstamped migration must RETRY and finish.
  await page.goto(URL);
  await ready(page);
  await page.waitForTimeout(1200);
  await page.evaluate(() => { try { (window as any).renderVault(); } catch (e) {} });

  const phase2 = await page.evaluate(() => {
    const w = window as any;
    const f = (n: string) => String(n || '').replace(/[‘’ʼ´`]/g, "'").trim();
    const eye = "Tal Rasha's Lidless Eye";
    return {
      dock: (w._vaultDockNames() || []).map(f),
      owned: JSON.parse(w.LSR.getItem('d2r_owned') || '[]') as string[],
      assign: JSON.parse(w.LSR.getItem('d2r_muleAssign') || '{}') as Record<string, string>,
      copies: JSON.parse(w.LSR.getItem('d2r_copies') || '{}') as Record<string, number>,
      seamEye: (typeof w._vaultSeamHome === 'function' ? (w._vaultSeamHome(eye) || {}).loc : null) || null,
      stamp: w.LSR.getItem('d2r_setDupeMigrate_v2227'),
    };
  });

  // the stray loose copies are finally gone from owned AND the dock
  expect(phase2.owned, 'after the retry the stray Tal Rasha copy is de-duped out of owned').not.toContain(BARE_TAL);
  expect(phase2.owned, 'after the retry the stray Immortal King copy is de-duped out of owned').not.toContain(BARE_IK);
  expect(phase2.dock.indexOf(fold(BARE_TAL)), 'the stray must not still show in the Unsorted dock').toBe(-1);
  expect(phase2.dock.indexOf(fold(BARE_IK)), 'the stray must not still show in the Unsorted dock').toBe(-1);

  // TESTIMONY KEPT — the filed copies and their set-mule filings survive untouched
  expect(phase2.owned, 'the filed Tal Rasha copy survives the retry').toContain(SLOT_TAL);
  expect(phase2.owned, 'the filed Immortal King copy survives the retry').toContain(SLOT_IK);
  expect(phase2.assign[SLOT_TAL], 'the Tal Rasha set-mule filing is untouched').toBe('sets-major');
  expect(phase2.assign[SLOT_IK], 'the Immortal King set-mule filing is untouched').toBe('sets-major');

  // NO COPY LOST — the stray's count folded onto the surviving filed twin (and only after the real remove)
  expect(phase2.copies[SLOT_TAL], 'the stray copy count folds onto the surviving filed twin (never undercount)').toBe(3);
  expect(phase2.copies[BARE_TAL], 'the stray copy-count entry is gone once the row is removed').toBeUndefined();

  // NON-REGRESSION — a set piece with no filed twin is NOT removed. Elad 2026-10-18: a name
  // the router already knows is homed at read time and is never an unsorted dock chip. Lidless Eye
  // is a known set piece, so the seam places it without writing assign.
  expect(phase2.owned, 'a set piece with no filed twin stays owned').toContain(LONE_EYE);
  expect(phase2.assign[LONE_EYE], 'the migration must not invent a filing for a piece with no twin').toBeUndefined();
  expect(phase2.seamEye, "Tal Rasha's Lidless Eye is seam-homed onto its set mule").toBe('filed');
  expect(phase2.dock.indexOf(fold(LONE_EYE)), 'a homed name is not an unsorted dock chip').toBe(-1);

  // and now it is stamped once — a later undo of the batch will never be re-applied
  expect(phase2.stamp, 'after a confirmed remove the migration stamps once per world').toBeTruthy();
});
