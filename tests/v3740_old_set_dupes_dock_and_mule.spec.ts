import { test, expect } from '@playwright/test';
import * as path from 'path';
import { pinEvaluate, gotoPinned } from './_pin';

// REG-2229 (#11) — OLD SET-PIECE DOUBLE-ROWS: owned in BOTH the Unsorted dock AND the set mule.
//
// Before v3716 the hand/planner door owned the SHOWN set-piece name ("Tal Rasha's Horadric Crest")
// while the vault filed that same piece under its slot key ("Tal Rasha's Horadric Crest (helm)"), so
// `owned` carried BOTH forms — one filed in the set mule (assign === 'sets-major'), one left loose in
// the Unsorted dock (assign == null). bible.html:45127 names the bug: "Routing the shown name beside
// that key owned both, one filed and one left in Unsorted." v3716 resolves the name before owning +
// filing, so no NEW add double-files — but the rows written before it were never migrated, and his
// helms (Tal Rasha, Immortal King, Natalya, +1) still showed in both places.
//
// THE MIGRATION (window._vaultDedupeOldSetRows, once per world, run from renderVaultDraw): a LOOSE
// owned set piece whose SAME canonical piece (findSetPiece().piece) is already filed in a real mule is
// the stray shown-name copy — removed through the vaultRemove door (dated, journalled, undoable). His
// testimony is kept: the FILED copy and its filing stay, the Sets chronicle (d2r_setPieces) is untouched.
//
// RED without the fix: nothing removes the stray, so the bare name is still owned AND in the dock.
// GREEN with the fix: the stray bare copies are gone from owned and the dock, the filed slot copies and
// their set-mule assignments remain, and a genuinely loose set piece with no filed twin is left alone.

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// the exact piece strings __allSets / _SET_SEED use (slot suffix, lower case) — verified in the repo
const BARE_TAL = "Tal Rasha's Horadric Crest";   const SLOT_TAL = "Tal Rasha's Horadric Crest (helm)";
const BARE_IK  = "Immortal King's Will";          const SLOT_IK  = "Immortal King's Will (helm)";
const LONE_EYE = "Tal Rasha's Lidless Eye";       // a loose set piece with NO filed twin — must STAY
const STAMP = 'd2r_setDupeMigrate_v2227';

const fold = (s: string) => String(s || '').replace(/[‘’ʼ´`]/g, "'").trim();

async function ready(page: any) {
  await page.waitForFunction(
    () => typeof (window as any).LSR !== 'undefined'
       && typeof (window as any).findSetPiece === 'function'
       && typeof (window as any)._vaultDockNames === 'function'
       && typeof (window as any).renderVault === 'function', null, { timeout: 120000 });
}

test('a filed set piece no longer shows as unsorted: the stray dock copy is de-duped, the filed set-mule copy and his testimony stay', async ({ page }) => {
  await page.goto(URL);
  await ready(page);

  // seed the OLD (pre-v3716) double-row state and clear the migration stamp, then RELOAD so the stores
  // load from it and the migration runs on a cold boot — the localStorage + reload path, never live data.
  await pinEvaluate(page, (s) => {
    const w = window as any;
    try { localStorage.setItem('d2r_ownerClaim', '*'); } catch (e) {}
    // owned carries BOTH forms of each helm: the bare SHOWN name (loose) and the slot key (filed)
    w.LSR.setItem('d2r_owned', JSON.stringify([s.bareTal, s.slotTal, s.bareIk, s.slotIk, s.loneEye]));
    // the slot keys are FILED in the TAL/IK set mule (sets-major); the bare keys and the lone eye are LOOSE
    w.LSR.setItem('d2r_muleAssign', JSON.stringify({ [s.slotTal]: 'sets-major', [s.slotIk]: 'sets-major' }));
    try { w.LSR.removeItem(s.stamp); } catch (e) {}
  }, { bareTal: BARE_TAL, slotTal: SLOT_TAL, bareIk: BARE_IK, slotIk: SLOT_IK, loneEye: LONE_EYE, stamp: STAMP });

  await gotoPinned(page, URL);
  await ready(page);
  await page.waitForTimeout(1200);
  await page.evaluate(() => { try { (window as any).renderVault(); } catch (e) {} });

  const r = await page.evaluate(() => {
    const w = window as any;
    const f = (n: string) => String(n || '').replace(/[‘’ʼ´`]/g, "'").trim();
    const dock = (w._vaultDockNames() || []).map(f);
    const owned = JSON.parse(w.LSR.getItem('d2r_owned') || '[]') as string[];
    const assign = JSON.parse(w.LSR.getItem('d2r_muleAssign') || '{}') as Record<string, string>;
    const resolves = {
      tal: ((w.findSetPiece("Tal Rasha's Horadric Crest") || {}) as any).piece,
      ik:  ((w.findSetPiece("Immortal King's Will") || {}) as any).piece,
    };
    const eye = "Tal Rasha's Lidless Eye";
    const seamEye = (typeof w._vaultSeamHome === 'function' ? (w._vaultSeamHome(eye) || {}).loc : null) || null;
    return { dock, owned, assign, resolves, seamEye, stamp: w.LSR.getItem('d2r_setDupeMigrate_v2227') };
  });

  // the premise of the bug: the bare and slot forms resolve to the SAME canonical piece, so one is a stray
  expect(r.resolves.tal, 'findSetPiece must canonicalise the bare Tal Rasha helm to its slot key').toBe(SLOT_TAL);
  expect(r.resolves.ik, 'findSetPiece must canonicalise the bare Immortal King helm to its slot key').toBe(SLOT_IK);

  // GREEN discriminator — the stray loose copies are gone from owned AND from the dock
  expect(r.owned, 'the stray bare Tal Rasha copy must be de-duped out of owned').not.toContain(BARE_TAL);
  expect(r.owned, 'the stray bare Immortal King copy must be de-duped out of owned').not.toContain(BARE_IK);
  expect(r.dock.indexOf(fold(BARE_TAL)), 'a filed set piece must not still show in the Unsorted dock').toBe(-1);
  expect(r.dock.indexOf(fold(BARE_IK)), 'a filed set piece must not still show in the Unsorted dock').toBe(-1);

  // TESTIMONY KEPT — the FILED copy and its set-mule filing survive untouched
  expect(r.owned, 'the filed Tal Rasha copy must survive the migration').toContain(SLOT_TAL);
  expect(r.owned, 'the filed Immortal King copy must survive the migration').toContain(SLOT_IK);
  expect(r.assign[SLOT_TAL], 'the Tal Rasha set-mule filing must be untouched').toBe('sets-major');
  expect(r.assign[SLOT_IK], 'the Immortal King set-mule filing must be untouched').toBe('sets-major');

  // NON-REGRESSION — a set piece with no filed twin is NOT removed. Elad 2026-10-18: a name
  // the router already knows is homed at read time and is never an unsorted dock chip. Lidless Eye
  // is a known set piece, so the seam places it without writing assign. The migration's law is that
  // the row survives unfiled; the dock chip is gone because the home is the set mule.
  expect(r.owned, 'a set piece with no filed twin must be kept in owned').toContain(LONE_EYE);
  expect(r.assign[LONE_EYE], 'the migration must not invent a filing for a piece with no twin').toBeUndefined();
  expect(r.seamEye, "Tal Rasha's Lidless Eye is seam-homed onto its set mule").toBe('filed');
  expect(r.dock.indexOf(fold(LONE_EYE)), 'a homed name is not an unsorted dock chip').toBe(-1);

  // the migration stamped itself once, so a later undo of the batch (vaultRestoreLast) will stick
  expect(r.stamp, 'the migration must stamp once per world so it never re-applies over a later undo').toBeTruthy();
});
