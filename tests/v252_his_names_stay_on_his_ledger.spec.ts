import { test, expect } from '@playwright/test';
import path from 'path';

/* #252 (REG-2920..2923) — HIS NAMES, HIS MF AND HIS BRAND ARE HIS ONLY ON HIS LEDGER, IN A REAL DOM.
 *
 * His rule (2026-09-27): every personal surface is per-PC. The node laws (tv/test_a_recommendation_names_this_pcs_
 * characters.py, test_his_advice_boxes_and_marks_stay_on_his_ledger.py, test_an_unset_mf_is_never_his_699.py,
 * test_his_logger_wishlist_and_filter_names_stay_his.py) prove each renderer; three things need the real document:
 *   - the boot walker (_charSayStatic) rewriting the markup's own text nodes - the TZ tab's zone cards and the nine
 *     "For Konyo" guide boxes;
 *   - the two starred MF presets (553 / 699) losing the star, the "mine" look and his name in their titles;
 *   - the loot filter card's labels after the filter engine's own repaint (refreshLootFilterCount).
 *
 * ⚠ BOTH DIRECTIONS, as v2692 asserts its seeds: "another board sees none of it" is satisfiable by stripping him
 * everywhere, and "his board keeps it" by never stripping. Only the pair is the law. The automated file:// world is
 * HIS ledger by design (v2694), so the other board is a claimed store with its own ledger name, set before a reload.
 */
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

async function readBoard(page: any) {
  return page.evaluate(() => {
    const w: any = window;
    const names = /Konyo(?:lock|din|ress|ssin)/gi, forKonyo = /For Konyo/g;
    let nameHits = 0, forHits = 0;
    const samples: string[] = [];
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
    let t: any;
    while ((t = tw.nextNode())) {
      const p = t.parentNode && t.parentNode.nodeName;
      if (p === 'SCRIPT' || p === 'STYLE' || p === 'TEXTAREA') continue;
      const v = String(t.nodeValue || '');
      const a = (v.match(names) || []).length, b = (v.match(forKonyo) || []).length;
      if ((a || b) && samples.length < 4) samples.push(v.trim().slice(0, 120));
      nameHits += a; forHits += b;
    }
    const chip = (v: string) => {
      const c = document.getElementById('mf-preset-mine-' + v);
      return c ? { mine: c.classList.contains('mf-preset-chip-mine'), text: (c.textContent || '').trim(), title: c.getAttribute('title') || '' } : null;
    };
    return {
      seeds: w._seedsBelongHere === true,
      nameHits, forHits, samples,
      chips: { '553': chip('553'), '699': chip('699') },
      mfVal: (document.getElementById('mf-val') || {} as any).textContent || '',
    };
  });
}

async function filterLabels(page: any) {
  await page.evaluate(() => { const w: any = window; if (typeof w.refreshLootFilterCount === 'function') w.refreshLootFilterCount(); });
  await page.waitForTimeout(1500);
  return page.evaluate(() => {
    const nm = document.querySelector('.lf-b-name');
    const btn = document.querySelector('.lf-copy-btn[onclick*="copyLootFilter(\'endgame\')"]');
    return { name: nm ? (nm.textContent || '').trim() : null, btn: btn ? (btn.textContent || '').trim() : null };
  });
}

test('another board: no name of his in the markup, his presets are plain, MF not set, the filter is its own', async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(2500);
  await page.evaluate(() => {
    try {
      localStorage.clear();
      localStorage.setItem('d2r_ownerClaim', '*');
      localStorage.setItem('d2r_ledgerName', 'Deans-Own-Ledger');
    } catch (e) {}
  });
  await page.reload();
  await page.waitForTimeout(2800);

  const b = await readBoard(page);
  expect(b.seeds, 'PREMISE: this board reads as his ledger - nothing below would mean anything').toBe(false);
  expect(b.nameHits, 'the markup still names his characters on another board: ' + JSON.stringify(b.samples)).toBe(0);
  expect(b.forHits, 'a guide box still says "For Konyo" on another board: ' + JSON.stringify(b.samples)).toBe(0);
  for (const v of ['553', '699']) {
    const c: any = (b.chips as any)[v];
    expect(c, 'PREMISE: preset chip ' + v + ' is not on the page').not.toBeNull();
    expect(c.mine, 'preset ' + v + ' keeps his "mine" look on another board').toBe(false);
    expect(c.text, 'preset ' + v + ' still wears his star').toBe(v);
    expect(c.title).not.toContain('Konyo');
  }
  expect(b.mfVal, 'an MF this board never set is shown as a number').toBe('not set');

  const f = await filterLabels(page);
  expect(f.name, 'PREMISE: the loot filter card is not on the page').not.toBeNull();
  expect(f.name!.startsWith('DeansOwnLedger'), 'the filter card is named ' + f.name).toBe(true);
  expect(f.btn || '', 'the copy button names his filter').not.toContain('KonyoEndgame');
});

test("HIS board keeps all of it — the half a naive fix breaks", async ({ page }) => {
  await page.goto(URL);
  await page.waitForTimeout(2800);

  const b = await readBoard(page);
  expect(b.seeds, 'PREMISE: the automated world is not his ledger (v2694)').toBe(true);
  expect(b.nameHits, 'his own board lost his character names in the markup').toBeGreaterThan(0);
  expect(b.forHits, 'his own board lost the boxes written to him').toBeGreaterThan(0);
  for (const v of ['553', '699']) {
    const c: any = (b.chips as any)[v];
    expect(c.mine, 'his preset ' + v + ' lost its look on his own board').toBe(true);
    expect(c.text).toContain('⭐');
  }
  expect(b.mfVal).toBe('699%');

  const f = await filterLabels(page);
  expect((f.name || '').startsWith('KonyoEndgame'), 'his filter card is named ' + f.name).toBe(true);
});
