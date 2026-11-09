import { test, expect } from './_net_stub'; // diablo2.io art stubbed — flaked on the 2026-06-12 backstop run
import * as path from 'path';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v149 — TZ zone titles adopt the Bosses-tab header-bar STRUCTURE (Konyo: identical in
// structure & font to RoTW / Runes / Bosses). Each .tz-zone-header is now a full-width
// gradient bar across the card top (mirrors .boss-header): bold 19px serif name + emblem
// + tier + chevron, pulled to the card edges. Parity is asserted against a real RoTW
// .sec-h-t (same Cinzel family + bold weight) so the two tabs can't drift apart.
test.describe('v149 TZ titles match the Bosses/RoTW header bar', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.waitForTimeout(1000);
  });

  test('the TZ zone header is a full-width gradient bar (not a bare flex row)', async ({ page }) => {
    await page.evaluate(() => (window as any).switchTab && (window as any).switchTab('tz'));
    await page.waitForTimeout(300);
    const r = await page.evaluate(() => {
      const hdr = document.querySelector('#tz-zones-container .tz-zone-card > .tz-zone-header') as HTMLElement;
      const cs = getComputedStyle(hdr);
      return {
        hasBar: !!hdr,
        hasGradient: /gradient/.test(cs.backgroundImage),
        borderBottom: parseFloat(cs.borderBottomWidth) >= 1,
        // pulled to the card edges via negative margin (mirrors .boss-header spanning the card top)
        negTopMargin: parseFloat(cs.marginTop) < 0,
        padded: parseFloat(cs.paddingTop) >= 10,
      };
    });
    expect(r.hasBar).toBe(true);
    expect(r.hasGradient).toBe(true);
    expect(r.borderBottom).toBe(true);
    expect(r.negTopMargin).toBe(true);
    expect(r.padded).toBe(true);
  });

  // v3889 (#23, his theme pass, REG-3490) - a terror zone's NAME wears the game's own face ("D2 Exocet", his 11-08 "just
  // ingame related stuff"), falling back to the RoTW title's serif; the bar, the weight and the size stay the RoTW title's
  test('the TZ title is the game face over the RoTW .sec-h-t serif (bold, >=19px)', async ({ page }) => {
    // RoTW reference
    await page.evaluate(() => (window as any).switchTab && (window as any).switchTab('rotw'));
    await page.waitForTimeout(250);
    const rotw = await page.evaluate(() => {
      const t = document.querySelector('#tab-rotw .sec-h .sec-h-t') as HTMLElement;
      const cs = getComputedStyle(t);
      return { fam: cs.fontFamily.split(',')[0].replace(/["']/g, ''), weight: cs.fontWeight };
    });
    // TZ title
    await page.evaluate(() => (window as any).switchTab && (window as any).switchTab('tz'));
    await page.waitForTimeout(250);
    const tz = await page.evaluate(() => {
      const t = document.querySelector('#tz-zones-container .tz-zone-card .tz-zone-name') as HTMLElement;
      const cs = getComputedStyle(t);
      const fams = cs.fontFamily.split(',').map((f) => f.trim().replace(/["']/g, ''));
      return { fam: fams[0], fallback: fams[1], weight: cs.fontWeight, size: parseFloat(cs.fontSize) };
    });
    expect(tz.fam).toBe('D2 Exocet');         // the game's own face (--ff-game)
    expect(tz.fallback).toBe(rotw.fam);       // then the same serif-display (Cinzel) the RoTW title wears
    expect(tz.weight).toBe(rotw.weight);      // same bold weight (700)
    expect(tz.weight).toBe('700');
    expect(tz.size).toBeGreaterThanOrEqual(19);
  });

  test('the Pit cross-link card carries the same header bar', async ({ page }) => {
    await page.evaluate(() => (window as any).switchTab && (window as any).switchTab('tz'));
    await page.waitForTimeout(300);
    const r = await page.evaluate(() => {
      const hdr = document.querySelector('.tz-crosslink-card > .tz-zone-header') as HTMLElement;
      if (!hdr) return { found: false };
      const cs = getComputedStyle(hdr);
      const name = hdr.querySelector('.tz-zone-name') as HTMLElement;
      return {
        found: true,
        hasGradient: /gradient/.test(cs.backgroundImage),
        nameWeight: name ? getComputedStyle(name).fontWeight : '',
      };
    });
    expect(r.found).toBe(true);
    expect(r.hasGradient).toBe(true);
    expect(r.nameWeight).toBe('700');
  });

  test('RoTW section headers also get the prominent Bosses/Runes bar (gradient + bold 19px)', async ({ page }) => {
    await page.evaluate(() => (window as any).switchTab && (window as any).switchTab('rotw'));
    await page.waitForTimeout(300);
    const r = await page.evaluate(() => {
      const h = document.querySelector('#tab-rotw .sec-h') as HTMLElement;
      const t = h?.querySelector('.sec-h-t') as HTMLElement;
      const cs = getComputedStyle(h);
      const tcs = getComputedStyle(t);
      return {
        hasGradient: /gradient/.test(cs.backgroundImage),
        padTop: parseFloat(cs.paddingTop),
        titleSize: parseFloat(tcs.fontSize),
        titleWeight: tcs.fontWeight,
      };
    });
    expect(r.hasGradient).toBe(true);
    expect(r.padTop).toBeGreaterThanOrEqual(13);
    expect(r.titleSize).toBeGreaterThanOrEqual(19);
    expect(r.titleWeight).toBe('700');
  });

  test('the shared .sec-h bars are now globally enriched on EVERY tab (Reference too)', async ({ page }) => {
    // v150 — the header-bar look was promoted from #tab-rotw-scoped to a global
    // .sec-h:not(.tier-header) so every collapsible section title across every tab
    // (Reference, Main, Binds class-groups, RoTW) reads as the same prominent bar.
    await page.evaluate(() => (window as any).switchTab && (window as any).switchTab('ref'));
    await page.waitForTimeout(300);
    const r = await page.evaluate(() => {
      const h = document.querySelector('#tab-ref .sec-h.collapsed:not(.tier-header)') as HTMLElement;
      const t = h?.querySelector('.sec-h-t') as HTMLElement;
      const cs = getComputedStyle(h);
      const tcs = getComputedStyle(t);
      return {
        hasGradient: /gradient/.test(cs.backgroundImage),
        titleSize: parseFloat(tcs.fontSize),
        titleWeight: tcs.fontWeight,
      };
    });
    expect(r.hasGradient).toBe(true);
    expect(r.titleSize).toBeGreaterThanOrEqual(19);
    expect(r.titleWeight).toBe('700');
  });

  test('the deliberate flat Binds .tier-header stacks are NOT enriched (excluded by :not)', async ({ page }) => {
    await page.evaluate(() => (window as any).switchTab && (window as any).switchTab('binds'));
    await page.waitForTimeout(300);
    const r = await page.evaluate(() => {
      const h = document.querySelector('.tier-header.sec-h') as HTMLElement;
      if (!h) return { found: false };
      const cs = getComputedStyle(h);
      return { found: true, hasGradient: /gradient/.test(cs.backgroundImage), display: cs.display };
    });
    expect(r.found).toBe(true);
    // tier-headers stay flat block — no gradient bar leaked onto the stacked-bind design
    expect(r.hasGradient).toBe(false);
  });

  test('no console errors rendering the restyled TZ tab', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
    await page.goto(URL);
    await page.waitForTimeout(1000);
    await page.evaluate(() => (window as any).switchTab && (window as any).switchTab('tz'));
    await page.waitForTimeout(300);
    expect(errors).toEqual([]);
  });
});
