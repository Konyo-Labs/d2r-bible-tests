import { test, expect } from './_net_stub';
import * as path from 'path';

// v1810 — THE FLOATING TRAY RODE UP INTO THE TAB STRIP.
//
// The tray is a bottom-anchored COLUMN — help at calc(var(--dock-h) + 14px), the nav compass at
// +66, the forge legend at +118 — while the header and tab strip are top-anchored. On a tall
// window the two never meet, which is why this survived every gate: the render widths were
// 375/640/701/901/1440 and the HEIGHT was always whatever the runner defaulted to.
//
// Measured at 640x400 before the fix: the strip occupied y 240-271 and the 44px compass y 250-294,
// so the `session` tab hit-tested to #nav-fab and could not be clicked at all. At 844x390 — an
// iPhone in landscape, not a stress test — the HELP orb overlapped the strip by 42x44px, and at
// 640x400 it sat on #gsearch-input and clipped the placeholder.
//
// WHY THIS ASSERTS RECTANGLES AND NOT A HIT TEST, which is the opposite of what v1800 concluded.
// The strip scrolls horizontally, so WHICH tab is buried under an orb depends on scroll offset.
// Hit-testing found `session` blocked on one load and reported everything clear on the next, with
// no code change in between — a witness that appears and vanishes is not a guard. The invariant
// that holds at every scroll position: a fixed orb must not intersect the strip's BAND. If it
// does, some tab is unreachable at some offset. [[feedback-suspect-the-instrument]]
//
// PROVEN RED: with the @media (max-height:480px) rule defeated by a body-appended override, this
// reports overlaps at 844x390, 640x400 and 375x400, and stays clear at 640x481 and 1440x900 — so
// it fails for its own reason and the threshold acts only where it is meant to.

const FILE = 'file://' + path.resolve(__dirname, '..', 'bible.html');

const ORBS = [
  { sel: '.help-btn',          name: 'S0 help' },
  { sel: '.nav-widget',        name: 'S1 compass' },
  { sel: '.forge-legend-fab',  name: 'S2 forge legend' },
];

const VICTIMS = [
  { sel: '.tabs',           name: 'tab strip' },
  { sel: '.tabs-workshop',  name: 'workshop row' },
  { sel: '#gsearch-input',  name: 'search field' },
];

// Short enough that the tray and the strip compete for the same band, plus two controls above the
// threshold to prove the rule does not reach where it should not.
const SIZES = [
  { w: 844, h: 390, short: true },   // iPhone landscape
  { w: 640, h: 400, short: true },   // the render gate's narrow width, at a short height
  { w: 375, h: 400, short: true },
  { w: 640, h: 481, short: false },  // one pixel above the threshold
  { w: 1440, h: 900, short: false },
];

for (const s of SIZES) {
  test(`v1810 — no tray orb intersects the tab strip or search at ${s.w}x${s.h}`, async ({ page }) => {
    await page.setViewportSize({ width: s.w, height: s.h });
    await page.goto(FILE);
    await page.waitForSelector('.tabs .tab', { state: 'attached' });
    await page.waitForFunction(() => {
      const v = getComputedStyle(document.documentElement).getPropertyValue('--dock-h').trim();
      return v !== '' && v !== '0px';
    }, null, { timeout: 15000 });

    const overlaps = await page.evaluate(({ orbs, victims }) => {
      const hits: string[] = [];
      for (const o of orbs) {
        const e = document.querySelector(o.sel) as HTMLElement | null;
        if (!e) continue;
        const cs = getComputedStyle(e);
        if (cs.display === 'none' || cs.visibility === 'hidden') continue;
        const a = e.getBoundingClientRect();
        if (a.width < 2) continue;
        for (const v of victims) {
          const t = document.querySelector(v.sel) as HTMLElement | null;
          if (!t) continue;
          if (getComputedStyle(t).display === 'none') continue;
          const b = t.getBoundingClientRect();
          if (b.width < 2 || b.height < 2) continue;
          const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (ox > 0 && oy > 0) {
            hits.push(`${o.name} x ${v.name} (${Math.round(ox)}x${Math.round(oy)}px)`);
          }
        }
      }
      return hits;
    }, { orbs: ORBS, victims: VICTIMS });

    expect(overlaps, `tray overlaps at ${s.w}x${s.h}`).toEqual([]);
  });
}

test('v1810 — above the threshold the tray is still THERE', async ({ page }) => {
  // The fix hides chrome. A rule that hid the tray everywhere would satisfy every assertion above
  // and quietly delete three controls — so the threshold gets its own witness on the other side.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(FILE);
  await page.waitForSelector('.help-btn', { state: 'attached' });
  for (const sel of ['.help-btn', '.nav-widget']) {
    const shown = await page.evaluate((s) => {
      const e = document.querySelector(s) as HTMLElement | null;
      if (!e) return 'absent';
      return getComputedStyle(e).display;
    }, sel);
    expect(shown, `${sel} at 1440x900`).not.toBe('none');
    expect(shown, `${sel} at 1440x900`).not.toBe('absent');
  }
});

// REG-2862 — THE TAB-SCOPED ORBS. The cases above load the default tab, where the Tools map, the Vault guide and
// MOVE TASKS are never displayed, so they skipped those three by construction and the inbox only when its queue was
// empty. These open the tab each orb belongs to. On a short screen every orb in the column must clear the strip; on
// the vault tab MOVE TASKS must still open, through its toolbar door, because its orb is the one that yields.
const TAB_ORBS = [
  ...ORBS,
  { sel: '.tools-legend-fab', name: 'S2 tools map' },
  { sel: '.vault-guide-fab',  name: 'S2 vault guide' },
  { sel: '.inbox-fab',        name: 'S3 inbox' },
  { sel: '.vault-tasks-fab',  name: 'S4 MOVE TASKS' },
];

// The tall case is 1440x900 only. Between 481 and ~655px tall the inbox (+170) and MOVE TASKS (+222) orbs sit
// higher than the S2 orb the 480px threshold was measured for, and where they land against the strip there has not
// been measured - a geometry this file does not know is left out rather than asserted (REG-2862, NEEDS MEASURE).
for (const tab of ['vault', 'tools']) {
  for (const s of SIZES.filter((z) => z.short || z.w >= 1440)) {
    test(`REG-2862 — no tray orb intersects the tab strip or search on the ${tab} tab at ${s.w}x${s.h}`, async ({ page }) => {
      await page.setViewportSize({ width: s.w, height: s.h });
      await page.goto(FILE);
      await page.waitForSelector('.tabs .tab', { state: 'attached' });
      await page.evaluate((t) => { (window as any).switchTab(t); }, tab);
      await page.waitForFunction(() => {
        const v = getComputedStyle(document.documentElement).getPropertyValue('--dock-h').trim();
        return v !== '' && v !== '0px';
      }, null, { timeout: 15000 });
      await page.waitForTimeout(400);
      const r = await page.evaluate(({ orbs, victims }) => {
        const hits: string[] = []; const shown: string[] = [];
        for (const o of orbs) {
          const e = document.querySelector(o.sel) as HTMLElement | null;
          if (!e) continue;
          const cs = getComputedStyle(e);
          if (cs.display === 'none' || cs.visibility === 'hidden') continue;
          const a = e.getBoundingClientRect();
          if (a.width < 2) continue;
          shown.push(o.name);
          for (const v of victims) {
            const t = document.querySelector(v.sel) as HTMLElement | null;
            if (!t || getComputedStyle(t).display === 'none') continue;
            const b = t.getBoundingClientRect();
            if (b.width < 2 || b.height < 2) continue;
            const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
            const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
            if (ox > 0 && oy > 0) hits.push(`${o.name} x ${v.name} (${Math.round(ox)}x${Math.round(oy)}px)`);
          }
        }
        return { hits, shown };
      }, { orbs: TAB_ORBS, victims: VICTIMS });
      expect(r.hits, `tray overlaps on the ${tab} tab at ${s.w}x${s.h}`).toEqual([]);
      if (!s.short) {
        // above the threshold the tab's own orbs are there - so a green here is not a column that drew nothing
        const own = tab === 'vault' ? ['S2 vault guide', 'S4 MOVE TASKS'] : ['S2 tools map'];
        for (const n of own) expect(r.shown, `${n} is not drawn on the ${tab} tab at ${s.w}x${s.h}`).toContain(n);
      }
    });
  }
}

test('REG-2862 — on a short screen MOVE TASKS opens from the vault toolbar, where its orb has yielded', async ({ page }) => {
  await page.setViewportSize({ width: 640, height: 400 });
  await page.goto(FILE);
  await page.waitForSelector('.tabs .tab', { state: 'attached' });
  await page.evaluate(() => { (window as any).switchTab('vault'); });
  await page.waitForTimeout(400);
  const fab = await page.evaluate(() => getComputedStyle(document.getElementById('vault-tasks-fab')!).display);
  expect(fab, 'the 📦 orb is still drawn at 640x400 - this case is not testing the short screen').toBe('none');
  const chip = page.locator('#vault-chip-tasks');
  await chip.scrollIntoViewIfNeeded({ timeout: 15000 });
  await expect(chip).toBeVisible();
  await chip.click({ timeout: 10000 });
  const open = await page.evaluate(() => !(document.getElementById('vault-tasks') as HTMLElement).hidden);
  expect(open, 'the toolbar door did not open MOVE TASKS').toBe(true);
});

test('REG-2862 — on an ordinary screen the toolbar door stays hidden and the 📦 orb is the door', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(FILE);
  await page.waitForSelector('.tabs .tab', { state: 'attached' });
  await page.evaluate(() => { (window as any).switchTab('vault'); });
  await page.waitForTimeout(400);
  const d = await page.evaluate(() => ({
    chip: getComputedStyle(document.getElementById('vault-chip-tasks')!).display,
    fab: getComputedStyle(document.getElementById('vault-tasks-fab')!).display,
  }));
  expect(d.chip).toBe('none');
  expect(d.fab).not.toBe('none');
});
