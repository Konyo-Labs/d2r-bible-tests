import { test, expect, Page } from '@playwright/test';
import { boardReady } from './_board_ready';
import { pinEvaluate, reloadPinned } from './_pin';

// REG-2410..REG-2413 (#152 items 2-3, #153 item 11) — THE STORES ARE NEVER BRICKED, AND ANOTHER TAB'S WRITE IS MERGED.
//
// GrokBot's sweep (#230, 10-21, cov*.py), unchanged on v3784:
//   · d2r_muleRoster saved as {} stopped the vault script before renderVault and vaultHandAdd existed, on every reload;
//   · d2r_owned saved as {"a":1} threw at `new Set(...)`, and `owned`, `multiKeep` and the rest never existed;
//   · two tabs: another tab's owned write was lost on this tab's next add (no storage listener).
//
// The node laws (tv/test_a_store_that_will_not_read_is_kept_aside.py and its three siblings) drive the shipped pieces
// one by one. What only a browser can show is the WHOLE page booting over a bad store, and a real storage event
// travelling from one page to another. That is this spec. CI runs it; the Mac never does (test-venue).
//
// RED (before): after the reload renderVault / vaultHandAdd are undefined, or `owned` is; the other page's write is
// gone from d2r_owned after this page's next write.
// GREEN (after): the page boots on a default, the bad bytes stay byte for byte (and kept aside), the notice names the
// store, + Add an item refuses in words, and both pages' items are in the store.

const BOARD = 'file://' + process.cwd() + '/bible.html';

async function boot(page: Page) {
  await page.goto(BOARD);
  await page.waitForLoadState('load');
  await boardReady(page, ['LSR', 'renderVault', 'vaultHandAdd', 'persistOwned']);
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
  return phys;
}

test('a mule roster saved as {} no longer stops the vault script', async ({ page }) => {
  const phys = await seedAndReload(page, 'd2r_muleRoster', '{}');
  const got = await page.evaluate((p) => {
    const w = window as any;
    const q = w.LSR && w.LSR.quarantined ? w.LSR.quarantined('d2r_muleRoster') : null;
    const el = document.getElementById('store-quarantine');
    return {
      renderVault: typeof w.renderVault, vaultHandAdd: typeof w.vaultHandAdd,
      raw: localStorage.getItem(p), reason: q && q.reason, kept: q && q.aside ? localStorage.getItem(q.aside) : null,
      notice: !!el && !el.hidden ? (el.textContent || '') : '',
    };
  }, phys);
  expect(got.renderVault, 'the vault script stopped before renderVault').toBe('function');
  expect(got.vaultHandAdd, 'the vault script stopped before vaultHandAdd').toBe('function');
  expect(got.reason).toBe('is not a list of mules');
  expect(got.notice).toContain('d2r_muleRoster');
  expect(got.kept, 'the roster bytes are kept aside').toBe('{}');
  expect(got.raw, 'the roster that would not read was written over').toBe('{}');
});

test('owned saved as {"a":1} keeps the page alive and holds the vault in words', async ({ page }) => {
  const phys = await seedAndReload(page, 'd2r_owned', '{"a":1}');
  const got = await page.evaluate((p) => {
    const w = window as any;
    let ownedSize = -1;
    try { ownedSize = (0, eval)('owned').size; } catch (e) { ownedSize = -2; }
    const r = typeof w.vaultHandAdd === 'function' ? w.vaultHandAdd('Harlequin Crest') : null;
    const el = document.getElementById('store-quarantine');
    return {
      ownedSize, refused: r ? r.refused : null, ok: r ? r.ok : null, why: r ? String(r.why || '') : '',
      raw: localStorage.getItem(p), notice: !!el && !el.hidden ? (el.textContent || '') : '',
    };
  }, phys);
  expect(got.refused, '+ Add an item must refuse while the vault is held').toBe('held');
  expect(got.why).toContain('d2r_owned');
  expect(got.notice).toContain('what you own');
  expect(got.raw, 'd2r_owned was written over').toBe('{"a":1}');
  expect(got.ok).toBe(false);
  expect(got.ownedSize, '`owned` must exist (the boot used to throw at new Set)').toBeGreaterThanOrEqual(0);
});

test("another page's owned write survives this page's next write", async ({ page, context }) => {
  await boot(page);
  const other = await context.newPage();
  await boot(other);
  await page.evaluate(() => { (window as any).__heard = 0; window.addEventListener('storage', () => { (window as any).__heard++; }); });
  // the other page adds through its own door
  await other.evaluate(() => { (0, eval)('owned').add('Arachnid Mesh'); (window as any).persistOwned(); });
  const heard = await page.waitForFunction(() => (window as any).__heard > 0, null, { timeout: 8000 }).then(() => true, () => false);
  test.skip(!heard, 'UNMEASURED: this venue delivered no storage event between two pages of the board (not a pass)');
  await page.waitForFunction(() => (0, eval)('owned').has('Arachnid Mesh'), null, { timeout: 8000 });
  // this page adds next, through the same door
  const stored = await page.evaluate(() => {
    const w = window as any;
    (0, eval)('owned').add('Harlequin Crest (Shako)');
    w.persistOwned();
    return JSON.parse(w.LSR.getItem('d2r_owned') || '[]');
  });
  expect(stored).toContain('Harlequin Crest (Shako)');
  expect(stored, "the other page's item was carried over by this page's stale copy").toContain('Arachnid Mesh');
  await other.close();
});
