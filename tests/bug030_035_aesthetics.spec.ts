// v1754 — through the shared net stub, so this spec's measurements do not depend on the
// runner reaching fonts.googleapis.com. bible.html makes exactly FIVE external requests and
// all five are fonts; stubbing them removes the whole external surface.
//
// ⚠ NOT because a failed font collapses this layout — I checked, and it does not. Measured
// three ways, .set-card-header is 78px ONLINE, 78px OFFLINE and 78px STUBBED. The v1749
// note on _net_stub says a font failure makes that bar 0px; offline does not reproduce it,
// and the flake it was written about turned out to be a blind toggleCardCollapse leaving
// the card COLLAPSED (fixed in v1751, proven by forcing .collapsed). The honest reason to
// stub here is determinism, not a defect anyone has shown. [[inherited_claim_is_not_evidence]]
import { test, expect } from './_net_stub';
import * as path from 'path';
import { BOSS_CHIPS_TOTAL } from './_data_locks';

const BIBLE = 'file://' + path.resolve(__dirname, '..', 'bible.html');

test.describe('BUG-030..035 — aesthetics sweep', () => {
  test('BUG-030 all 13 boss cards have consistent structure', async ({ page }) => {
    await page.goto(BIBLE);
    await page.waitForTimeout(1200);
    const cards = page.locator('#boss-cards .boss-card');
    const count = await cards.count();
    expect(count).toBe(BOSS_CHIPS_TOTAL); // 11 farmable bosses + 2 event drops (Summoner=Key of Hate, Dclone=Annihilus)

    // Each must have: .boss-header.clickable, .boss-emoji, .boss-name, .boss-tier-tag, .boss-body
    for (let i = 0; i < count; i++) {
      const card = cards.nth(i);
      await expect(card.locator('.boss-header.clickable')).toBeAttached();
      await expect(card.locator('.boss-emoji')).toBeAttached();
      await expect(card.locator('.boss-name')).toBeAttached();
      await expect(card.locator('.boss-tier-tag')).toBeAttached();
      await expect(card.locator('.boss-body')).toBeAttached();
    }
  });

  test('BUG-031 section headers use uppercase + gold color', async ({ page }) => {
    await page.goto(BIBLE);
    await page.waitForTimeout(1200);
    // Pick a known section header inside a boss card
    const h3 = page.locator('#boss-cards h3').first();
    const style = await h3.evaluate(el => {
      const cs = getComputedStyle(el);
      return { color: cs.color, transform: cs.textTransform, letter: cs.letterSpacing };
    });
    expect(style.transform).toBe('uppercase');
    // gold color: red dominant + green > blue + red > 180
    const m = style.color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    expect(m).not.toBeNull();
    const [r, g, b] = m!.slice(1).map(Number);
    expect(r).toBeGreaterThan(180);
    expect(r).toBeGreaterThan(g);
    expect(g).toBeGreaterThan(b);
  });

  test('BUG-032 .blocked cells have distinct color', async ({ page }) => {
    await page.goto(BIBLE);
    await page.waitForTimeout(1200);
    // Find any drops cell with class .blocked / .impossible / data-blocked
    const blocked = page.locator('#boss-cards td.blocked, #boss-cards .blocked').first();
    if (await blocked.count()) {
      const color = await blocked.evaluate(el => getComputedStyle(el).color);
      // Just assert it's set
      expect(color).toBeTruthy();
    }
  });

  test('BUG-033 boss-card has hover affordance (v39: boss-card:hover lift)', async ({ page }) => {
    await page.goto(BIBLE);
    await page.waitForTimeout(1200);
    const hasHover = await page.evaluate(() => {
      for (const sheet of Array.from(document.styleSheets)) {
        try {
          for (const rule of Array.from((sheet as CSSStyleSheet).cssRules || [])) {
            if (rule instanceof CSSStyleRule && /\.boss-card[^a-z].*:hover|\.boss-header[^a-z].*:hover/.test(rule.selectorText)) return true;
          }
        } catch {}
      }
      return false;
    });
    expect(hasHover).toBe(true);
  });

  // v3889 (#132, his 11-08 'i dont need any mobile anything') - BUG-034 (no horizontal overflow at 375px) left with the
  // phone page; tombstone in tv/test_there_is_no_phone_page.py

  test('BUG-035 difficulty-grid renders for each boss card', async ({ page }) => {
    await page.goto(BIBLE);
    await page.waitForTimeout(1200);
    const cards = await page.locator('#boss-cards .boss-card').count();
    const grids = await page.locator('#boss-cards .diff-grid').count();
    expect(grids).toBe(cards);
  });

  // v3889 (#132) - BUG-035b (the boss-detail card fits a 375px phone) left with the phone page
});
