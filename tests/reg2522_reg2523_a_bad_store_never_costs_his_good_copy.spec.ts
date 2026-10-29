import { test, expect, Page } from '@playwright/test';
import { boardReady } from './_board_ready';
import { pinEvaluate, reloadPinned } from './_pin';

// REG-2522 + REG-2523 (V1 round 3) — A ROSTER SAVED AS "[]" IS UNKNOWN, AND ANOTHER PAGE'S BAD WRITE NEVER COSTS THIS PAGE'S
// GOOD COPY. (Fix round: a roster that only lacks a core locker it had deleted before REG-2195 reads, and gets it back -
// tv/test_a_roster_this_board_wrote_is_read_and_keeps_his_mules.py; "[]" stays held, as here.)
//
// The node laws (tv/test_a_roster_without_its_core_lockers_is_unknown.py, tv/test_this_tabs_last_good_copy_can_be_kept.py)
// drive the shipped pieces one by one. What only a browser can show is the WHOLE page booting over a roster saved as "[]"
// (the bytes REG-2414's merge bug stored), and a REAL storage event carrying another page's bad bytes into this one. That
// is this spec. CI runs it; the Mac never does (test-venue).
//
// RED (before): the "[]" roster is read as a roster, the migrations save three lockers over it and the paint's prune drops
// every filing on the other eight; another page's bad write leaves a notice that says "runs on a default" and offers only
// exits that drop this page's good copy - afterwards no key in storage holds the good list.
// GREEN (after): the roster is quarantined (its bytes kept aside, the vault held, every filing stays); the notice says
// "This tab still holds your last good copy", and keeping it writes the good list back with the bad bytes kept aside.

const BOARD = 'file://' + process.cwd() + '/bible.html';
const FILED = { Grief: 'uni-weap', 'Harlequin Crest (Shako)': 'uni-armor', Enigma: 'runewords' };
const READY = ['LSR', 'renderVault', 'vaultFile', '_TAB_SYNC', '_storeKeepThisTab'];

async function boot(page: Page) {
  await page.goto(BOARD);
  await page.waitForLoadState('load');
  await boardReady(page, READY);
}

test('a roster saved as "[]" is quarantined, the vault is held, and the paint drops no filing', async ({ page }) => {
  await boot(page);
  await pinEvaluate(page, (filed) => {
    const w = window as any;
    w.LSR.setItem('d2r_owned', JSON.stringify(Object.keys(filed)));
    w.LSR.setItem('d2r_muleAssign', JSON.stringify(filed));
    localStorage.setItem(w.LSR.key('d2r_muleRoster'), '[]');
  }, FILED);
  await reloadPinned(page);
  await page.waitForLoadState('load');
  await boardReady(page, READY);
  const got = await page.evaluate(() => {
    const w = window as any, q = w.LSR.quarantined('d2r_muleRoster');
    try { w.renderVault(); } catch (e) {}                                          // the paint and its W6 prune, now
    return { reason: q && q.reason, kept: q && q.aside ? localStorage.getItem(q.aside) : null,
             held: w._vaultBasisHeld(), raw: localStorage.getItem(w.LSR.key('d2r_muleRoster')),
             map: JSON.parse(JSON.stringify(w._TAB_SYNC.d2r_muleAssign.get())),
             stored: JSON.parse(localStorage.getItem(w.LSR.key('d2r_muleAssign')) || '{}'),
             notice: (document.getElementById('store-quarantine') || {} as any).innerHTML || '' };
  });
  expect(got.reason || '', 'a roster that holds no mules was read as a roster').toContain('holds no mules at all');
  expect(got.kept, 'the roster bytes are kept aside').toBe('[]');
  expect(got.held || '', 'the vault is not held while its roster is UNKNOWN').toContain('d2r_muleRoster');
  expect(got.raw, 'a roster was saved over the bytes that would not read').toBe('[]');
  expect(got.map, 'the paint dropped his filings against a roster that would not read').toEqual(FILED);
  expect(got.stored, 'the saved mule map lost his filings').toEqual(FILED);
  expect(got.notice).toContain('d2r_muleRoster');
});

test("another page's bad write offers this page's good copy back, and keeping it writes it with the bad bytes aside", async ({ page, context }) => {
  await boot(page);
  const good = ['Grief', 'Enigma', 'Harlequin Crest (Shako)'];
  await pinEvaluate(page, (names) => {
    const w = window as any;
    w.LSR.setItem('d2r_owned', JSON.stringify(names));
  }, good);
  await reloadPinned(page);
  await page.waitForLoadState('load');
  await boardReady(page, READY);
  const BAD = '["Grief","Eni';
  await page.evaluate((bad) => {
    const w = window as any, phys = w.LSR.key('d2r_owned');
    w.__heard = false;          /* only the bad write itself - the other page's boot may write the good list first */
    window.addEventListener('storage', (ev: StorageEvent) => { if (ev.key === phys && ev.newValue === bad) w.__heard = true; });
  }, BAD);
  const other = await context.newPage();
  await boot(other);
  await other.evaluate((bad) => { const w = window as any; localStorage.setItem(w.LSR.key('d2r_owned'), bad); }, BAD);
  const heard = await page.waitForFunction(() => (window as any).__heard === true, null, { timeout: 8000 }).then(() => true, () => false);
  test.skip(!heard, 'UNMEASURED: this venue delivered no storage event between two pages of the board (not a pass)');
  const held = await page.evaluate(() => {
    const w = window as any, q = w.LSR.quarantined('d2r_owned');
    return { lastGood: !!(q && q.lastGood), notice: (document.getElementById('store-quarantine') || {} as any).innerHTML || '' };
  });
  expect(held.lastGood, "this page's good copy is not recognised as the last good copy").toBe(true);
  expect(held.notice).toContain('This tab still holds your last good copy');
  expect(held.notice).toContain('_storeKeepThisTab');
  expect(held.notice).not.toContain('runs on a default');
  const kept = await page.evaluate(async (bad) => {
    const w = window as any;
    const r = await w._storeKeepThisTab('d2r_owned', true);                       // his answer to the question is yes
    const asideHolds = Object.keys(localStorage).filter((k) => k.indexOf('d2r_quarantine~d2r_owned~') >= 0 && localStorage.getItem(k) === bad);
    return { r, raw: localStorage.getItem(w.LSR.key('d2r_owned')), held: w.LSR.quarantined('d2r_owned'), asideHolds: asideHolds.length };
  }, BAD);
  expect(kept.r.ok, 'Keep this tab’s copy failed: ' + JSON.stringify(kept.r)).toBe(true);
  expect(JSON.parse(kept.raw || '[]').sort(), "this page's copy was not written back").toEqual(good.slice().sort());
  expect(kept.held, 'the hold was not lifted').toBeNull();
  expect(kept.asideHolds, "the other page's bad bytes were not kept aside").toBeGreaterThanOrEqual(1);
  await other.close();
});
