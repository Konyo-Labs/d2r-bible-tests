import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

/**
 * v1840 — REG-145's consequence, closed. A boss-difficulty cell declares a `tcMax`, and 39 of 66
 * cells carried drop rows ABOVE it at v1715 (48 of 66 after the v1716 pull) — e.g. Normal Mephisto
 * declares TC40 and carries Bverrit Keep, TC60, at 1:289. The blocked-reason strings are built from
 * that field, so a cell could print "TC 60 > Normal Mephisto TC 40" with the table underneath it
 * saying otherwise.
 *
 * v1722 had already established the rule for the OTHER reason — the qlvl one is suppressed in any
 * cell whose own data breaks it, "no reason beats a false reason" — and the TC branch never got it.
 * Measured before and after: TC-cited entries 2687 -> 1211, "not in ... drop pool" 3250 -> 4726,
 * total blocked entries 5937 -> 5937.
 *
 * That last number is the point of the second assertion: v1723 found that removing a false reason
 * removes the FACT, because a row with no reason gets no source entry at all. The count must not move.
 *
 * NOT tested here, deliberately: the 66 tcMax values themselves. REG-145 says correcting them
 * changes what the calculator calls impossible and is HIS call.
 */
test('a TC ceiling is never cited in a cell whose own rows exceed it', async ({ page }) => {
  await page.goto(URL);
  await page.waitForFunction(() => !!(window as any)._allDropItems || !!(window as any).ITEMS);
  const bad = await page.evaluate(() => {
    const items = (window as any)._allDropItems ? (window as any)._allDropItems() : ((window as any).ITEMS || []);
    const out: string[] = [];
    (items || []).forEach((it: any) => {
      (it.sources || []).forEach((s: any) => {
        const m = /^TC (\d+) > (.+) TC (\d+)$/.exec(s.blocked || '');
        if (!m) return;
        // the cell quoted a ceiling; find whether anything that DOES drop there beats it
        const ceiling = Number(m[3]);
        const cell = s.boss;
        (items || []).forEach((o: any) => {
          (o.sources || []).forEach((os: any) => {
            if (os.boss === cell && os.chance !== null && (o.tc || 0) > ceiling) {
              out.push(`${cell} cites TC${ceiling} but drops ${o.name} (TC${o.tc})`);
            }
          });
        });
      });
    });
    return Array.from(new Set(out)).slice(0, 8);
  });
  expect(bad, 'a blocked reason names a ceiling the same cell demonstrably ignores').toEqual([]);
});

test('suppressing the reason does not delete the cannot-drop fact', async ({ page }) => {
  await page.goto(URL);
  await page.waitForFunction(() => !!(window as any)._allDropItems || !!(window as any).ITEMS);
  const counts = await page.evaluate(() => {
    const items = (window as any)._allDropItems ? (window as any)._allDropItems() : ((window as any).ITEMS || []);
    let total = 0, pool = 0, tc = 0, qlvl = 0;
    (items || []).forEach((it: any) => (it.sources || []).forEach((s: any) => {
      if (!s.blocked) return;
      total++;
      if (/not in /.test(s.blocked)) pool++;
      else if (/^TC \d+ > /.test(s.blocked)) tc++;
      else if (/^qlvl \d+ > /.test(s.blocked)) qlvl++;
    }));
    return { total, pool, tc, qlvl };
  });
  // v1723: a row whose reason was suppressed keeps its entry with a reason true by construction
  expect(counts.total).toBeGreaterThan(5000);
  // v3884 (REG-3440, every qlvl is silospen's) - PIN THE LAW, NOT THE NUMBER. This said pool > 4000. Measured 11-08 in headless
  // Chrome: v3883 total 6462 = pool 5259 + TC 1203 + qlvl 0; v3884 total 8794 = pool 3275 + TC 22 + qlvl 5497. With 366 wrong
  // quality levels every cell's own rows broke the qlvl rule, so v1722 suppressed that reason everywhere; with silospen's levels
  // it holds and is cited ("qlvl 20 > Normal mlvl 12"), so rows moved from the fallback "not in ... drop pool" to their real
  // reason and none was deleted (the total grew). The law: every blocked row still carries one of the three true reasons.
  expect(counts.pool + counts.tc + counts.qlvl, `a blocked row lost its reason: ${JSON.stringify(counts)}`).toBe(counts.total);
  expect(counts.pool).toBeGreaterThan(0);
});
