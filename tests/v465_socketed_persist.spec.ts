// v465 — ACCUMULATION BUG: per-base socketed/Larzuk items (e.g. "Champion Axe (5os)") are registered at runtime
// by _ensureSocketBaseEntry, so they weren't in the static _EXTRA_ITEM_SET when the load-time sanitize prune ran
// → every reload silently DROPPED them, making a later intake batch look like it "didn't build on top" of the
// earlier one. The prune now keeps the socketed-base label suffix. Also: Flail base/art/max-socket fix.
import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

test.describe('v465 socketed bases survive reload (accumulation)', () => {
  test('per-base socketed + Larzuk items survive a fresh load (not pruned)', async ({ page }) => {
    await page.addInitScript(() => {
      // as if a PRIOR intake batch registered these, then the page is reloaded
      localStorage.setItem('d2r_owned', JSON.stringify([
        'Champion Axe (5os)', 'Monarch (4os)', 'Crystal Sword (Larzuk base)',
        'Superior Executioner Sword (6os)', 'Windforce',
      ]));
    });
    await page.goto(URL);
    await page.waitForFunction(() => (window as any).EXTRA_ITEMS && (window as any)._ensureSocketBaseEntry);
    await page.waitForTimeout(1500);   // let the load-time sanitize + _ensureSocketBaseEntry pass run
    const r = await page.evaluate(() => {
      const o = eval('owned');
      return {
        championAxe: o.has('Champion Axe (5os)'),
        monarch: o.has('Monarch (4os)'),
        crystalLarzuk: o.has('Crystal Sword (Larzuk base)'),
        execSword: o.has('Superior Executioner Sword (6os)'),
        windforce: o.has('Windforce'),   // a normal grail item — must also survive (control)
      };
    });
    expect(r.championAxe).toBe(true);
    expect(r.monarch).toBe(true);
    expect(r.crystalLarzuk).toBe(true);
    expect(r.execSword).toBe(true);
    expect(r.windforce).toBe(true);
  });

  test('a SECOND batch builds on top of the first across a reload (no reset)', async ({ page }) => {
    await page.addInitScript(() => {
      // seed batch 1 ONLY on the first load — addInitScript re-runs on reload, so guard it or it would
      // overwrite the batch-2 additions we make below (test artifact, not an app behaviour).
      if (!localStorage.getItem('d2r_owned')) localStorage.setItem('d2r_owned', JSON.stringify(['Monarch (4os)', 'Windforce']));
    });
    await page.goto(URL);
    await page.waitForFunction(() => (window as any)._ensureSocketBaseEntry);
    await page.waitForTimeout(1200);
    // batch 2 — add more socketed bases as a later intake would, persist, then reload
    await pinEvaluate(page, () => {
      const o = eval('owned');
      o.add('Grim Scythe (6os)'); o.add('Spetum (6os)');
      localStorage.setItem('d2r_owned', JSON.stringify([...o]));
    });
    await reloadPinned(page);
    await page.waitForFunction(() => (window as any)._ensureSocketBaseEntry);
    await page.waitForTimeout(1200);
    const r = await page.evaluate(() => {
      const o = eval('owned');
      return { monarch: o.has('Monarch (4os)'), grim: o.has('Grim Scythe (6os)'),
               spetum: o.has('Spetum (6os)'), windforce: o.has('Windforce'), size: o.size };
    });
    expect(r.monarch).toBe(true);   // batch-1 item still there
    expect(r.grim).toBe(true);      // batch-2 item present
    expect(r.spetum).toBe(true);    // batch-2 item present
    expect(r.windforce).toBe(true);
  });
});

test.describe('v465 Flail base + art + max sockets', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.waitForFunction(() => (window as any)._socketMaxFor && (window as any).artUrl);
  });

  test('Flail HotO entry base is Flail (not Mace) → resolves a flail sprite, not a hammer', async ({ page }) => {
    const r = await page.evaluate(() => {
      const w = window as any;
      return {
        base: (w.EXTRA_ITEMS['Flail (Heart of the Oak base)'] || {}).base,
        baseArt: w.artUrl('Flail'),
        desc: (w.EXTRA_ITEMS['Flail (Heart of the Oak base)'] || {}).desc,
      };
    });
    expect(r.base).toBe('Flail');
    expect(r.baseArt).toMatch(/flail/i);          // flail sprite, not maul/mace
    expect(r.baseArt).not.toMatch(/maul|mace/i);
  });

  test('Flail max sockets = 5 and the card states it + the HotO-needs-4 nuance', async ({ page }) => {
    const r = await page.evaluate(() => {
      const w = window as any;
      return { max: w._socketMaxFor('Flail'), desc: (w.EXTRA_ITEMS['Flail (Heart of the Oak base)'] || {}).desc };
    });
    expect(r.max).toBe(5);
    expect(r.desc).toContain('5 sockets');
    expect(r.desc).toMatch(/needs exactly <b>4<\/b>|cube it/i);
  });
});
