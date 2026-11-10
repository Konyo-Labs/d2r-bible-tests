// REG-2094 (#231 eye on v43 0133be32 / 113be899) — navigateToItem must clear the material latch.
// A material card sets window.__activeMaterial so Escape can close it; navigateToItem (a grail chip, a search
// pick) used to paint an item card over it and leave the latch set, so Escape "closed the material" and wiped
// the item he had just opened. The latch must still clear. v3891 (#191, REG-3530) then made Escape peel the
// visible #item-detail.show card itself, so after the latch is cleared one Esc closes that item card on purpose.
// The baseline asserts Escape still closes a material card, so this spec cannot pass by Escape doing nothing.
import { test, expect } from './_net_stub';
import * as path from 'path';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

test.describe('REG-2094 Escape and the card latch', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.waitForFunction(() => typeof (window as any).openDrop === 'function' && typeof (window as any).navigateToItem === 'function');
  });

  test('baseline: Escape closes an open material card', async ({ page }) => {
    await page.evaluate(() => (window as any).openDrop('Key of Terror'));
    await expect(page.locator('#item-detail')).toHaveClass(/\bshow\b/);
    await page.keyboard.press('Escape');
    await expect(page.locator('#item-detail')).not.toHaveClass(/\bshow\b/);
  });

  test('an item card opened after a material card clears the latch, then Escape peels it', async ({ page }) => {
    const name = await page.evaluate(() => {
      const w = window as any;
      w.openDrop('Key of Terror');
      const nm = ((w.ITEMS || []).find((i: any) => /Harlequin/.test(i.n)) || (w.ITEMS || [])[0]).n;
      w.navigateToItem(nm, null);
      return nm;
    });
    expect(await page.evaluate(() => (window as any).__activeMaterial)).toBeNull();
    await expect(page.locator('#item-detail')).toHaveClass(/\bshow\b/);
    await expect(page.locator('#item-detail')).toContainText(name);
    await page.keyboard.press('Escape');
    await expect(page.locator('#item-detail')).not.toHaveClass(/\bshow\b/);
  });
});
