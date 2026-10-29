import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v557 — Fable-5 clarity pass on the Forge cards: the #1 action card (Make-now atomic) is now a layered layout —
// big action line (.f-atomact) → the RUNE RECIPE IN ORDER (.f-atomrecipe, previously missing from the very card
// you act on in-game) → dim sub-hints on their own row (.f-atomsubrow). The hero shows the recipe chips too.

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_owned', JSON.stringify(['Colossus Voulge (4os)']));   // Insight base, exact 4os
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Ral: 2, Tir: 2, Tal: 2, Sol: 2 }));
    localStorage.setItem('d2r_rwMade', '{}');
    localStorage.setItem('d2r_ladderMode', 'nonladder');
  });
  await page.goto(URL); await page.waitForTimeout(1400);
  await page.evaluate(() => { const w: any = window; w._ensureSocketBaseEntry('Colossus Voulge (4os)'); w.switchTab('forge'); w.forgeSetFilter('now'); w.renderForge(); });
});

test('the make-now atomic card is layered: action line + rune recipe in order', async ({ page }) => {
  const r = await page.evaluate(() => {
    const card = document.querySelector('#tab-forge .f-card.f-now.f-atom');
    const act = card?.querySelector('.f-atomact');
    const rec = card?.querySelector('.f-atomrecipe');
    return {
      card: !!card,
      act: (act?.textContent || '').replace(/\s+/g, ' ').trim(),
      recipeLabel: (rec?.querySelector('.f-reclbl')?.textContent || ''),
      recipeText: (rec?.textContent || '').replace(/\s+/g, ' '),
    };
  });
  expect(r.card).toBe(true);
  expect(r.act).toMatch(/Forge Insight in your 4os Colossus Voulge/);
  expect(r.recipeLabel).toMatch(/socket in order/i);
  expect(r.recipeText).toMatch(/Ral/);   // Insight = Ral Tir Tal Sol
  expect(r.recipeText).toMatch(/Sol/);
});

test('the hero shows the rune recipe chips (not just "runes in hand" prose)', async ({ page }) => {
  const r = await page.evaluate(() => {
    const w: any = window; w.forgeSetFilter('all'); w.renderForge();
    const hero = document.querySelector('#tab-forge .forge-hero');
    const rec = hero?.querySelector('.fh-recipe');
    return { hero: !!hero, recipe: (rec?.textContent || '').replace(/\s+/g, ' '), body: (hero?.querySelector('.fh-body')?.textContent || '') };
  });
  expect(r.hero).toBe(true);
  expect(r.recipe).toMatch(/Ral/);
  expect(r.body).toMatch(/4os Colossus Voulge/);   // names the exact owned base
});

test('a pipeline chain final step also carries the recipe row', async ({ page }) => {
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_owned', JSON.stringify(['Colossus Voulge (Larzuk base)']));
  });
  await reloadPinned(page); await page.waitForTimeout(1400);
  const r = await page.evaluate(() => {
    const w: any = window; w._ensureSocketBaseEntry('Colossus Voulge (Larzuk base)');
    w.switchTab('forge'); w.forgeSetFilter('now'); w.renderForge();
    // the chain card: advance to the final "Forge X" step
    const chain = [...document.querySelectorAll('#tab-forge .f-card.f-pipe.f-atom')][0];
    if (!chain) return { chain: false };
    const btn = chain.querySelector('.f-btn-go') as HTMLElement; btn?.click();   // "did it → next"
    const chain2 = [...document.querySelectorAll('#tab-forge .f-card.f-pipe.f-atom')][0];
    return { chain: true, hasRecipe: !!chain2?.querySelector('.f-atomrecipe') };
  });
  if (r.chain) expect(r.hasRecipe).toBe(true);
});
