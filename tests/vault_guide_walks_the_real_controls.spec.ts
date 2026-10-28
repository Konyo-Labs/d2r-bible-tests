import { test, expect } from './_net_stub';
import * as path from 'path';

// REG-2860 (#230) — THE VAULT GUIDE LIGHTS THE REAL CONTROL, ON SCREEN, WHERE A PERSON CAN PRESS IT.
//
// tv/test_the_vault_guide_walks_the_real_controls.py proves in node that every step names a control that exists, that
// "What you need to do" comes before the folds, and that the guide writes nothing. Node has no layout, so it cannot say
// whether the lit control is on the screen or hidden under the guide's own card, the sticky header or the tray. This is
// that half, measured the way v1800 measures the tray popovers: by a HIT TEST at the control's top band (its label, its
// first row), after the smooth scroll and the card's dodge have settled — not by a rect alone, which reads clean over a
// control something else is painted on.

const FILE = 'file://' + path.resolve(__dirname, '..', 'bible.html');

const SIZES = [
  { w: 1440, h: 900 },
  { w: 901, h: 700 },
  { w: 375, h: 700 },
];

for (const { w, h } of SIZES) {
  test(`REG-2860 the vault guide lights every real control on screen at ${w}x${h}`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h });
    await page.goto(FILE);
    const tab = page.locator('[data-tab="vault"]');
    await tab.scrollIntoViewIfNeeded({ timeout: 15000 });
    await tab.click({ timeout: 15000 });
    const fabUp = await page
      .waitForSelector('#vault-guide-fab', { state: 'visible', timeout: 20000 })
      .then(() => true, () => false);
    expect(fabUp, 'the Vault guide orb never showed on the vault tab').toBe(true);
    await page.click('#vault-guide-fab', { timeout: 10000 });
    await page.waitForTimeout(300);

    // tutorial first: his steps, then the folds, all closed
    const shape = await page.evaluate(() => {
      const p = document.getElementById('vault-guide-pop')!;
      const d = p.querySelector('[data-vgd="do"]'), how = p.querySelector('[data-vgd="how"]');
      return {
        open: getComputedStyle(p).display !== 'none',
        doFirst: !!d && !!how && !!(d.compareDocumentPosition(how) & Node.DOCUMENT_POSITION_FOLLOWING),
        folds: p.querySelectorAll('details.vgd-sec').length,
        openFolds: p.querySelectorAll('details.vgd-sec[open]').length,
      };
    });
    expect(shape.open, 'the guide panel did not open').toBe(true);
    expect(shape.doFirst, '"What you need to do" is not above the explanations').toBe(true);
    expect(shape.folds).toBeGreaterThan(0);
    expect(shape.openFolds, 'a fold opened by itself').toBe(0);

    const vg = await page.evaluate(() => (window as any)._vaultGuide);
    const goes: Array<{ go: number | string; target: string }> =
      vg.steps.map((s: any, i: number) => ({ go: i, target: s.target }))
        .concat(vg.shows.map((s: any) => ({ go: s.key, target: s.target })));
    expect(goes.length).toBeGreaterThan(5);

    for (const g of goes) {
      await page.evaluate((go) => (window as any).vaultGuideGo(go), g.go);
      // the jump is a smooth scroll and the card dodges at 450 ms and 1100 ms: measure after both
      await page.waitForTimeout(1400);
      const m = await page.evaluate((id) => {
        const el = document.getElementById(id) as HTMLElement;
        const r = el.getBoundingClientRect();
        const x = Math.round(r.left + Math.min(r.width, 60) / 2);
        const y = Math.round(r.top + Math.min(r.height, 48) / 2);
        const hit = document.elementFromPoint(x, y) as HTMLElement | null;
        const p = document.getElementById('vault-guide-pop')!;
        return {
          lit: el.classList.contains('vgd-target'),
          walking: p.classList.contains('vgd-walking'),
          w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top), bottom: Math.round(r.bottom),
          vh: innerHeight,
          reach: !!hit && (hit === el || el.contains(hit)),
          hitWas: hit ? (hit.id || String(hit.className || '') || hit.tagName) : 'none',
        };
      }, g.target);
      expect(m.walking, `step ${g.go} did not open its walk card`).toBe(true);
      expect(m.lit, `#${g.target} is not lit while its step is open`).toBe(true);
      expect(m.w > 0 && m.h > 0, `#${g.target} has no box (${m.w}x${m.h}) - the step points at something hidden`).toBe(true);
      expect(m.top >= 0 && m.top < m.vh, `#${g.target} is off screen (top ${m.top}, viewport ${m.vh})`).toBe(true);
      expect(m.reach, `#${g.target} is lit but covered by ${m.hitWas} - a person cannot press it`).toBe(true);
    }

    // back to the list, then closed: nothing stays lit
    await page.evaluate(() => (window as any).vaultGuideTog(false));
    const left = await page.evaluate(() => document.querySelectorAll('.vgd-target').length);
    expect(left, 'a control stayed lit after the guide closed').toBe(0);
  });
}
