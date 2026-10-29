import { test, expect } from '@playwright/test';
import * as path from 'path';
import { BOSS_CHIPS_TOTAL, CALC_ITEMS_TOTAL } from './_data_locks';
import { pinEvaluate, reloadPinned } from './_pin';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

test.describe('v43 editorial — regression check against v42 audit floor', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.evaluate(() => window.switchTab('bosses'));
    await page.waitForTimeout(3000);
  });

  test(`boot integrity — all module symbols + ${CALC_ITEMS_TOTAL} items + 13 boss chips`, async ({ page }) => {
    const state = await page.evaluate(() => ({
      items: typeof ITEMS !== 'undefined' ? ITEMS.length : 0,
      bossChips: document.querySelectorAll('.boss-chip').length,
      jumpToBossItem: typeof window.jumpToBossItem === 'function',
      navigateToItem: typeof window.navigateToItem === 'function',
      openBossDetail: typeof window.openBossDetail === 'function',
    }));
    expect(state.items).toBe(CALC_ITEMS_TOTAL);
    expect(state.bossChips).toBe(BOSS_CHIPS_TOTAL); // 11 farmable bosses + 2 event drops (Summoner=Key of Hate, Dclone=Annihilus)
    expect(state.jumpToBossItem).toBe(true);
    expect(state.navigateToItem).toBe(true);
    expect(state.openBossDetail).toBe(true);
  });

  test('editorial masthead present', async ({ page }) => {
    // v61: the "Vol. XLIII · Spring 2026 · The Sanctuary Codex" kicker was removed at
    // Konyo's request — masthead now leads with title + tagline. Assert those.
    const masthead = await page.evaluate(() => ({
      mastheadEl: !!document.querySelector('.masthead'),
      title: document.querySelector('.masthead .h-title')?.textContent,
      tagline: !!document.querySelector('.masthead-tagline'),
    }));
    expect(masthead.mastheadEl).toBe(true);
    expect(masthead.title).toContain('Konyo');
    expect(masthead.tagline).toBe(true);
  });

  test('navigateToItem syncs active-item-bar (Bug #5 regression test)', async ({ page }) => {
    await page.evaluate(() => { localStorage.clear(); });
    await page.reload();
    await page.waitForTimeout(3000);
    await page.evaluate(() => { if (typeof navigateToItem === 'function') navigateToItem('Harlequin Crest (Shako)'); });
    await page.waitForTimeout(1200);
    const result = await page.evaluate(() => ({
      tab: document.querySelector('.tab.active')?.dataset.tab,
      activeItem: eval('typeof activeItem !== "undefined" ? activeItem : null'),
      aibShown: document.getElementById('active-item-bar')?.classList.contains('show'),
    }));
    expect(result.tab).toBe('calc');
    expect(result.activeItem).toBe('Harlequin Crest (Shako)');
    expect(result.aibShown).toBe(true);
  });

  test('palette item action uses navigateToItem (Bug D)', async ({ page }) => {
    await page.evaluate(() => { localStorage.clear(); });
    await page.reload();
    await page.waitForTimeout(3000);
    await page.evaluate(() => { if (window._v42_openPalette) window._v42_openPalette(); });
    await page.waitForTimeout(200);
    await page.locator('#v42-palette-input').fill('harlequin');
    await page.waitForTimeout(300);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(600);
    const result = await page.evaluate(() => ({
      tab: document.querySelector('.tab.active')?.dataset.tab,
      selectedItem: eval('typeof selectedItem !== "undefined" ? selectedItem : null'),
      aibShown: document.getElementById('active-item-bar')?.classList.contains('show'),
    }));
    expect(result.tab).toBe('calc');
    expect(result.selectedItem).toContain('Harlequin');
    expect(result.aibShown).toBe(true);
  });

  test('setActiveBoss intent disambiguation (Bug H)', async ({ page }) => {
    // chip click = toggle
    await page.locator('.boss-chip[data-boss-id="diablo"]').click();
    await page.waitForTimeout(300);
    let bossId = await page.evaluate(() => activeBossId);
    expect(bossId).toBe('diablo');
    await page.locator('.boss-chip[data-boss-id="diablo"]').click();
    await page.waitForTimeout(300);
    bossId = await page.evaluate(() => activeBossId);
    expect(bossId).toBe(null);
    // openBossDetail = stays open on double-call (intent: open)
    await page.evaluate(() => window.openBossDetail('mephisto'));
    await page.waitForTimeout(300);
    await page.evaluate(() => window.openBossDetail('mephisto'));
    await page.waitForTimeout(300);
    bossId = await page.evaluate(() => activeBossId);
    expect(bossId).toBe('mephisto');
  });

  test('goBackFromAid no longer null.bossId (Bug E)', async ({ page }) => {
    await page.evaluate(() => {
      if (typeof aidCardOrigin !== 'undefined') aidCardOrigin = { tab: 'bosses', bossId: 'andariel' };
    });
    const result = await page.evaluate(async () => {
      if (typeof window.goBackFromAid !== 'function') return { error: 'no goBackFromAid' };
      window.goBackFromAid();
      await new Promise(r => setTimeout(r, 200));
      return {
        activeBossId: eval('typeof activeBossId !== "undefined" ? activeBossId : null'),
      };
    });
    expect(result.activeBossId).toBe('andariel');
  });

  test('localStorage corruption recovery (safe JSON parse)', async ({ page }) => {
    await pinEvaluate(page, () => {
      localStorage.setItem('d2r_wishlist', 'GARBAGE {{{');
      localStorage.setItem('d2r_owned', 'NOT_JSON');
    });
    await reloadPinned(page);
    await page.waitForTimeout(3000);
    const state = await page.evaluate(() => ({
      itemTiles: document.querySelectorAll('.item-tile').length,
      bossChips: document.querySelectorAll('.boss-chip').length,
      wishlistSize: typeof wishlist !== 'undefined' ? wishlist.size : -1,
    }));
    expect(state.itemTiles).toBe(CALC_ITEMS_TOTAL);
    expect(state.bossChips).toBe(BOSS_CHIPS_TOTAL); // 11 farmable bosses + 2 event drops (Summoner=Key of Hate, Dclone=Annihilus)
    expect(state.wishlistSize).toBe(0);
  });

  test('stale wishlist sanitization (Finding N)', async ({ page }) => {
    await pinEvaluate(page, () => {
      localStorage.setItem('d2r_wishlist', JSON.stringify([
        'Harlequin Crest (Shako)', 'Phantom Item X', 'Old Item Y', '', null
      ]));
    });
    await reloadPinned(page);
    await page.waitForTimeout(3000);
    const after = await page.evaluate(() => ({
      wishlistSize: wishlist.size,
      persisted: JSON.parse(localStorage.getItem('d2r_wishlist')),
    }));
    expect(after.wishlistSize).toBe(1);
    expect(after.persisted).toEqual(['Harlequin Crest (Shako)']);
  });

  test('keyboard shortcuts 1-8 switch tabs', async ({ page }) => {
    const tabs = ['1','2','3','4','5','6','7','8'];
    // v282: digits follow the visual tab order — 7=endgame, 8=binds (was 7=binds, 8=ref)
    const expected = ['bosses','calc','tz','runes','rotw','ancients','endgame','binds'];
    for (let i = 0; i < tabs.length; i++) {
      await page.keyboard.press(tabs[i]);
      await page.waitForTimeout(150);
      const active = await page.evaluate(() => document.querySelector('.tab.active')?.dataset.tab);
      expect(active).toBe(expected[i]);
    }
  });

  test('memory: 30× boss detail open/close — no DOM growth', async ({ page }) => {
    // 30 open/close cycles, each two page.evaluate round-trips — slower on the
    // 2-core CI runner. Headroom above the 180s global ceiling.
    test.setTimeout(360000);
    const startDom = await page.evaluate(() => document.querySelectorAll('*').length);
    for (let i = 0; i < 30; i++) {
      await page.evaluate(() => { if (window.openBossDetail) window.openBossDetail('mephisto'); });
      await page.waitForTimeout(20);
      // Close deterministically via evaluate — keyboard.press('Escape') can hang on
      // actionability at the tail of a long suite run. clearActiveBoss is the close fn;
      // fall back to dispatching the Escape keydown the handler listens for.
      await page.evaluate(() => {
        if (window.clearActiveBoss) window.clearActiveBoss();
        else document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
      });
      await page.waitForTimeout(20);
    }
    const endDom = await page.evaluate(() => document.querySelectorAll('*').length);
    // Tolerate small growth from notifications, sparklines, etc.
    expect(Math.abs(endDom - startDom)).toBeLessThan(50);
  });

  test('script tag leak fix (Bug I) — _v41_refreshStatus cleans up', async ({ page }) => {
    const before = await page.evaluate(() => document.head.querySelectorAll('script').length);
    for (let i = 0; i < 8; i++) {
      await page.evaluate(() => { if (typeof _v41_refreshStatus === 'function') _v41_refreshStatus(); });
      await page.waitForTimeout(80);
    }
    await page.waitForTimeout(400);
    const after = await page.evaluate(() => document.head.querySelectorAll('script').length);
    expect(after - before).toBeLessThan(5);
  });
});
