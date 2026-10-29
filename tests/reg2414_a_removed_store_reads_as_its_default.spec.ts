import { test, expect, Page } from '@playwright/test';
import { boardReady } from './_board_ready';
import { pinEvaluate, reloadPinned } from './_pin';

// REG-2414..REG-2417 (review of REG-2410..REG-2413) — A STORE ANOTHER PAGE REMOVED READS AS ITS DEFAULT, AND A VAULT
// STORE THAT WILL NOT READ HOLDS THE VAULT IN WORDS.
//
// The review drove both in node: another document REMOVING d2r_muleRoster made this tab's roster [] (the W6 prune then
// dropped every filing and the other tab's next filing wiped the map), and a d2r_vaultProv / d2r_mulePos cut short
// mid-write read as {} and the next filing or drop wrote over every row he had.
//
// The node laws (tv/test_a_store_another_tab_removed_reads_as_its_default.py, test_a_witness_store_that_will_not_read_
// holds_the_vault.py, test_his_hand_spots_that_will_not_read_are_kept_aside.py, test_what_a_mule_wears_that_will_not_
// read_is_kept_aside.py) drive the shipped pieces one by one. What only a browser can show is a REAL removal event
// travelling between two pages of the board, and the WHOLE page booting over a vault store cut short. That is this
// spec. CI runs it; the Mac never does (test-venue).
//
// RED (before): this page's roster is [] after the other page removes it, the prune drops his filings, and the other
// page's next filing leaves the stored map with its own row only; a reader filing writes over the witness rows.
// GREEN (after): the roster is the default lockers, every filing stays and the stored map keeps all four; the witness
// rows and the hand spots stay byte for byte, kept aside, named on the board, and the doors refuse in words.

const BOARD = 'file://' + process.cwd() + '/bible.html';
const FILED = { Grief: 'uni-weap', 'Harlequin Crest (Shako)': 'uni-armor', Enigma: 'runewords' };

async function boot(page: Page) {
  await page.goto(BOARD);
  await page.waitForLoadState('load');
  await boardReady(page, ['LSR', 'renderVault', 'vaultFile', '_TAB_SYNC', '_mpUnlock']);
}

/** seed `bytes` under the store's key in this world, then reload. Every inline script has run (or thrown) by 'load'. */
async function seedAndReload(page: Page, key: string, bytes: string): Promise<string> {
  await boot(page);
  const phys = await pinEvaluate(page, ([k, b]) => {
    const p = (window as any).LSR.key(k);
    localStorage.setItem(p, b);
    return p;
  }, [key, bytes]);
  await reloadPinned(page);
  await page.waitForLoadState('load');
  await boardReady(page, ['LSR', 'renderVault', 'vaultFile', '_TAB_SYNC', '_mpUnlock']);
  return phys;
}

test('a roster another page removes reads as the default lockers here, and every filing stays', async ({ page, context }) => {
  await boot(page);
  await pinEvaluate(page, (filed) => {
    const w = window as any;
    w.LSR.setItem('d2r_owned', JSON.stringify(Object.keys(filed)));
    w.LSR.setItem('d2r_muleAssign', JSON.stringify(filed));
  }, FILED);
  await reloadPinned(page);
  await page.waitForLoadState('load');
  await boardReady(page, ['LSR', 'renderVault', 'vaultFile', '_TAB_SYNC', '_mpUnlock']);
  const before = await page.evaluate(() => {
    const w = window as any, sync = w._TAB_SYNC;
    w.LSR.setItem('d2r_muleRoster', JSON.stringify(sync.d2r_muleRoster.get()));   // his roster, saved as this page holds it
    const phys = w.LSR.key('d2r_muleRoster');
    w.__removed = false;
    window.addEventListener('storage', (ev: StorageEvent) => { if (ev.key === phys && ev.newValue === null) w.__removed = true; });
    return sync.d2r_muleRoster.get().map((m: any) => m.id);
  });
  const other = await context.newPage();
  await boot(other);
  await other.evaluate(() => { (window as any).LSR.removeItem('d2r_muleRoster'); });
  const heard = await page.waitForFunction(() => (window as any).__removed === true, null, { timeout: 8000 }).then(() => true, () => false);
  test.skip(!heard, 'UNMEASURED: this venue delivered no storage event between two pages of the board (not a pass)');
  const got = await page.evaluate(() => {
    const w = window as any, sync = w._TAB_SYNC;
    try { w.renderVault(); } catch (e) {}                                          // the paint and its W6 prune, now
    return { ids: sync.d2r_muleRoster.get().map((m: any) => m.id), held: w.LSR.quarantined('d2r_muleRoster'),
             map: JSON.parse(JSON.stringify(sync.d2r_muleAssign.get())) };
  });
  expect(got.ids, 'a roster another page removed must read as the default lockers, never []').toEqual(before);
  expect(got.held).toBeNull();
  expect(got.map, 'the prune dropped his filings against an emptied roster').toEqual(FILED);
  // the other page, which still holds his map, files one more item: this page merges it and the store keeps all four.
  // 2026-10-24 - it OWNS that item first, as a real filing does. Filing a name that is in neither d2r_owned nor the
  // witness store made it a filing the W6 prune drops on this page's next paint (renderVault: an unwitnessed filing
  // whose name left the pool goes), so the wait below raced that paint and lost about 1 run in 7 (main v3792 Routine I
  // shard 1, red twice). The merge was never wrong; the test filed an item nobody owned.
  await other.evaluate(() => {
    const w = window as any, own = JSON.parse(w.LSR.getItem('d2r_owned') || '[]');
    if (own.indexOf('Arachnid Mesh') < 0) own.push('Arachnid Mesh');
    w.LSR.setItem('d2r_owned', JSON.stringify(own));
  });
  await page.waitForFunction(() => { const o = (window as any)._TAB_SYNC.d2r_owned.get(); return !!o && (o.has ? o.has('Arachnid Mesh') : o.indexOf('Arachnid Mesh') >= 0); }, null, { timeout: 8000 });
  await other.evaluate(() => {
    const w = window as any, m = JSON.parse(w.LSR.getItem('d2r_muleAssign') || '{}');
    m['Arachnid Mesh'] = 'uni-armor';
    w.LSR.setItem('d2r_muleAssign', JSON.stringify(m));
  });
  await page.waitForFunction(() => !!(window as any)._TAB_SYNC.d2r_muleAssign.get()['Arachnid Mesh'], null, { timeout: 8000 });
  // and it stays through this page's next paint and its W6 prune: an owned filing is never dropped by it
  const kept = await page.evaluate(() => { const w = window as any; w.renderVault(); return !!w._TAB_SYNC.d2r_muleAssign.get()['Arachnid Mesh']; });
  expect(kept, "this page's paint dropped the other page's filing of an item he owns").toBe(true);
  const stored = await page.evaluate(() => JSON.parse((window as any).LSR.getItem('d2r_muleAssign') || '{}'));
  expect(Object.keys(stored).sort(), "the other page's filing came back as a map with only its own row")
    .toEqual(['Arachnid Mesh', 'Enigma', 'Grief', 'Harlequin Crest (Shako)']);
  await other.close();
});

test('a witness store cut short mid-write holds the vault in words and is never written over', async ({ page }) => {
  const CUT = '{"Grief":{"mule":"uni-weap","source":"hand","by":"hand","at":"2026-10-01"},"Shako":{"mule":"uni-armor","source":"stash"';
  const phys = await seedAndReload(page, 'd2r_vaultProv', CUT);
  const got = await page.evaluate((p) => {
    const w = window as any;
    const q = w.LSR.quarantined('d2r_vaultProv');
    const r = w.vaultFile('Enigma', { by: 'hand', at: new Date().toISOString(), where: 'the vault manager' }, { mule: 'runewords' });
    const el = document.getElementById('store-quarantine');
    return { reason: q && q.reason, kept: q && q.aside ? localStorage.getItem(q.aside) : null, refused: r && r.refused,
             why: r ? String(r.why || '') : '', held: typeof w._vaultBasisHeld === 'function' ? w._vaultBasisHeld() : null,
             raw: localStorage.getItem(p), notice: !!el && !el.hidden ? (el.textContent || '') : '' };
  }, phys);
  expect(got.reason, 'the witness store must be quarantined as the page loads').toBe('will not parse');
  expect(got.kept, 'the witness rows are kept aside byte for byte').toBe(CUT);
  expect(got.refused, 'a filing over witness rows that will not read must be refused').toBe('prov-unreadable');
  expect(got.why).toContain('d2r_vaultProv');
  expect(got.held || '', 'the vault stands on its witness rows, so it is held').toContain('d2r_vaultProv');
  expect(got.notice).toContain('d2r_vaultProv');
  expect(got.raw, 'the witness store was written over').toBe(CUT);
});

test('hand spots cut short mid-write are kept aside and every spot door refuses in words', async ({ page }) => {
  const CUT = '{"uni-armor":{"Harlequin Crest (Shako)":{"tab":"personal","page":0,"x":3,"y":2,"at":"2026-10-01"},"Arkaine\'s Valor":{"tab"';
  const phys = await seedAndReload(page, 'd2r_mulePos', CUT);
  const got = await page.evaluate((p) => {
    const w = window as any;
    const u = w._mpUnlock('uni-armor', 'Harlequin Crest (Shako)');
    const q = w.LSR.quarantined('d2r_mulePos');
    const el = document.getElementById('store-quarantine');
    return { refused: u && u.refused, why: u ? String(u.why || '') : '', reason: q && q.reason,
             kept: q && q.aside ? localStorage.getItem(q.aside) : null, raw: localStorage.getItem(p),
             notice: !!el && !el.hidden ? (el.textContent || '') : '' };
  }, phys);
  expect(got.refused, 'an unlock over spots that will not read must be refused').toBe('held');
  expect(got.why).toContain('d2r_mulePos');
  expect(got.reason).toBe('will not parse');
  expect(got.kept, 'his spots are kept aside byte for byte').toBe(CUT);
  expect(got.notice).toContain('d2r_mulePos');
  expect(got.raw, 'his spots were written over').toBe(CUT);
});
