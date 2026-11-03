import { test, expect } from '@playwright/test';
import * as path from 'path';
import { CALC_ITEMS_TOTAL } from './_data_locks';

const BIBLE = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v144 — site-wide art-coverage floor + legitimate-gap allowlist lockdown.
// The calc grid (#item-grid, default filter "all") is the canonical item universe.
// This spec ratchets two things so a central-helper regression (artOr / artUrl /
// nameLogo / decorateItemLogos — the REG-001 blast-radius class) can't silently
// drop art coverage:
//   1. >= 297 of 312 grid items resolve a verified diablo2.io art URL.
//   2. EVERY unmapped item is on the KNOWN allowlist — 12 set-aggregate pseudo
//      entries (no single-item art), 1 runeword/parenthetical name, and the 2
//      diablo2.io-index-skipped uniques (Polaris Spear, The Scourge). Adding a
//      brand-new unmapped item fails this test (forces a deliberate decision).

// These 15 are legitimately art-less or intentionally skipped (ZERO fabrication —
// none of them have a confidently-verified single diablo2.io graphic URL).
const KNOWN_UNMAPPED = [
  // set-aggregate pseudo entries (a "set (any piece)" has no one item image)
  'Cow King\'s Leathers (set)',
  'Sigon\'s Complete Steel',
  'Sazabi\'s Grand Tribute',
  'Naj\'s Ancient Vestige',
  'Orphan\'s Call (set)',
  'Tal Rasha set (any piece)',
  'Trang-Oul set (any piece)',
  'Immortal King set (any)',
  'Griswold\'s Legacy (any)',
  'Aldur\'s Watchtower (any)',
  'M\'avina\'s Battle Hymn (any)',
  'Natalya\'s Odium (any)',
  // runeword / parenthetical-named entries (route via openDrop, no item thumb)
  'Crescent Moon (sword)',
  // v3859 — 'Polaris Spear' (not a unique) and 'The Scourge' (Stormlash's base) left the grid by his ruling.
];

test.describe('v144 art coverage floor', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BIBLE);
    await page.waitForTimeout(800);
  });

  test('>=296/312 grid items resolve verified art; every gap is on the known allowlist', async ({ page }) => {
    const r = await page.evaluate((known) => {
      const tiles = [...document.querySelectorAll('#item-grid .item-tile')] as HTMLElement[];
      const names = tiles.map((t) => t.getAttribute('data-name') || '');
      const mapped = names.filter((n) => !!(window as any).artUrl(n)).length;
      const unmapped = names.filter((n) => !(window as any).artUrl(n));
      const knownSet = new Set(known);
      const unexpected = unmapped.filter((n) => !knownSet.has(n));
      return { total: names.length, mapped, unmappedCount: unmapped.length, unexpected };
    }, KNOWN_UNMAPPED);
    expect(r.total).toBe(CALC_ITEMS_TOTAL);
    expect(r.mapped).toBeGreaterThanOrEqual(297);
    expect(r.unexpected).toEqual([]);          // no NEW unmapped item slipped in
    expect(r.unmappedCount).toBeLessThanOrEqual(KNOWN_UNMAPPED.length);
  });

  test('every mapped grid item renders a real .d2art-wrap thumbnail with the dup-safe alt', async ({ page }) => {
    const r = await page.evaluate(() => {
      const tiles = [...document.querySelectorAll('#item-grid .item-tile')] as HTMLElement[];
      let checked = 0, badAlt = 0, missingWrap = 0, missingAria = 0;
      for (const t of tiles) {
        const nm = t.getAttribute('data-name') || '';
        if (!(window as any).artUrl(nm)) continue;
        checked++;
        const wrap = t.querySelector('.d2art-wrap');
        if (!wrap) { missingWrap++; continue; }
        if (wrap.getAttribute('aria-label') !== nm) missingAria++;
        const img = wrap.querySelector('img');
        if (img && img.getAttribute('alt') !== '') badAlt++;   // decorative — must be ""
      }
      return { checked, badAlt, missingWrap, missingAria };
    });
    expect(r.checked).toBeGreaterThanOrEqual(297);
    expect(r.missingWrap).toBe(0);
    expect(r.missingAria).toBe(0);
    expect(r.badAlt).toBe(0);
  });
});
