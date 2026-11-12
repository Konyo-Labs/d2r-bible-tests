import { test, expect } from '@playwright/test';
import * as path from 'path';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v53 — rune sources as droppable cards. Travincal / Hellforge / Cow / LK
// previously rendered as static (always-open) .boss-card blocks with no grid.
// This converts them to the droppable expanding-card pattern the TZ zones use
// (header click -> toggle a detail box), matching the Countess template.
// HONEST-ODDS RULE: only Countess has true per-rune 1:N odds. Travincal shows
// the bible's existing APPROXIMATE high-rune rates (Lo/Ohm/Vex), clearly caveated;
// Hellforge shows a DETERMINISTIC guaranteed tier pool (not 1:N); Cow + LK get
// caveated cards with NO grid. No new odds are fabricated.
test.describe('v53 rune sources — droppable cards', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.waitForTimeout(1200);
    await page.evaluate(() => (window as any).switchTab('runes'));
  });

  test('renders exactly 4 droppable rune-source cards', async ({ page }) => {
    const target = page.locator('#rune-sources-target');
    await expect(target).toBeVisible();
    await expect(target.locator('.rune-src-card')).toHaveCount(4);
    for (const name of ['Travincal Council', 'Hellforge', 'Hell Bovines', 'Lower Kurast Chests']) {
      await expect(target.locator('.rune-src-card', { hasText: name })).toBeVisible();
    }
  });

  test('Travincal expands to exact high-rune grid (v699 pulled odds, no caveat needed)', async ({ page }) => {
    const detail = page.locator('#rune-src-detail-travincal');
    await expect(detail).toBeHidden();
    await page.locator('.rune-src-card', { hasText: 'Travincal Council' }).click();
    await expect(detail).toBeVisible();
    await expect(detail).toContainText('Lo #28');
    await expect(detail).toContainText('Ohm #27');
    await expect(detail).toContainText('Vex #26');
    // v708 recal — v699 replaced the "pending silospen pull" caveat with EXACT pulled council
    // odds (e.g. Vex → 1:14,489). Honesty is now a real 1:N figure, never a fake, never "pending".
    await expect(detail).toContainText('1:');
    await expect(detail).not.toContainText('pending silospen pull');
  });

  test('Hellforge expands to a deterministic guaranteed tier pool', async ({ page }) => {
    await page.locator('.rune-src-card', { hasText: 'Hellforge' }).click();
    const detail = page.locator('#rune-src-detail-hellforge');
    await expect(detail).toBeVisible();
    await expect(detail).toContainText('Guaranteed rune pool');
    await expect(detail).toContainText('Gul');
    await expect(detail).not.toContainText('1:');
  });

  test('Cow is droppable but carries no fabricated rune grid', async ({ page }) => {
    await page.locator('.rune-src-card', { hasText: 'Hell Bovines' }).click();
    const cow = page.locator('#rune-src-detail-cow');
    await expect(cow).toBeVisible();
    await expect(cow).toContainText('No dedicated rune table');
    await expect(cow.locator('table.drops')).toHaveCount(0);
  });

  test('only one rune-source detail open at a time', async ({ page }) => {
    await page.locator('.rune-src-card', { hasText: 'Travincal Council' }).click();
    await expect(page.locator('#rune-src-detail-travincal')).toBeVisible();
    await page.locator('.rune-src-card', { hasText: 'Hellforge' }).click();
    await expect(page.locator('#rune-src-detail-hellforge')).toBeVisible();
    await expect(page.locator('#rune-src-detail-travincal')).toBeHidden();
  });

  test('rune-source detail has the editorial frame (parity with zone/SU)', async ({ page }) => {
    await page.locator('.rune-src-card', { hasText: 'Travincal Council' }).click();
    const detail = page.locator('#rune-src-detail-travincal');
    await expect(detail).toBeVisible();
    // v93: the frame now lives on the inner golden .gbc-card (wrapper is stripped),
    // matching how the TZ-zone / super-unique details carry the editorial frame.
    const card = detail.locator('.gbc-card');
    await expect(card).toBeVisible();
    const f = await card.evaluate((el) => { const cs = getComputedStyle(el as Element); return { bw: cs.borderTopWidth, sh: cs.boxShadow }; });
    expect(parseInt(f.bw)).toBeGreaterThanOrEqual(1);
    expect(f.sh).not.toBe('none');
  });

  test('v93: rune-source detail adopts the golden .gbc-card banner (emblem + name + tier + close)', async ({ page }) => {
    await page.locator('.rune-src-card', { hasText: 'Travincal Council' }).click();
    const detail = page.locator('#rune-src-detail-travincal');
    await expect(detail).toBeVisible();
    const head = detail.locator('.gbc-card > .gbc-header');
    await expect(head).toBeVisible();
    // artOr emblem (routes through the helper -> .d2art-wrap with img/fallback). v3902 REG-3782 - his 11-12 ruling "show
    // their own sprites": the Council is a GROUP, one .d2art-group holding the three priests' own wraps, each through the
    // helper (img + fallback), and the caller's emoji fallback carried once
    const emblem = head.locator('.d2art-group');
    await expect(emblem).toBeVisible();
    await expect(emblem.locator('.d2art-wrap')).toHaveCount(3);
    await expect(emblem.locator('.d2art-wrap .d2art-fallback')).toHaveCount(3);
    await expect(head.locator('.gbc-name')).toHaveText('Travincal Council');
    await expect(head.locator('.gbc-tier .gbc-tier-val')).toHaveText('S');
    await expect(head.locator('.gbc-close')).toBeVisible();
    // close button collapses the detail (collapse contract preserved)
    await head.locator('.gbc-close').click();
    await expect(detail).toBeHidden();
  });

});
