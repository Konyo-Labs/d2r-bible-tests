import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v597 — CHAIN-STEP SANITY (Konyo's stale "step 2/2 Forge Wisdom" mystery). Three fixes:
// (1) the FINAL step of a pipeline chain names its BASE (step 1 named it, step 2 didn't — "which item
//     is this exactly referencing?"), (2) a chain past step 1 renders a "↺ back" control so a
//     mis-clicked "did it" is recoverable, (3) a freshly-REGISTERED read resets any step memory left
//     by a previous copy of the same label (covered here via forgeStepBack; the intake hook shares
//     the same store).

test('step-2 chain card names its base; ↺ back walks the chain back to step 1', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('d2r_owned', JSON.stringify(['Colossus Voulge (Larzuk base)']));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Ral: 1, Tir: 1, Tal: 1, Sol: 1 }));
    // stale step memory from a "previous copy" of the same base label (the Bone Visage scenario)
    localStorage.setItem('d2r_forgeStep', JSON.stringify({ 'chain|Colossus Voulge (Larzuk base)|4|l': 1 }));   // v693.3 — v684 chain keys carry |need|mode (base+need+Larzuk/gamble) so mixed-socket groups split
    localStorage.setItem('d2r_ladderMode', 'nonladder');
  });
  await page.goto(URL); await page.waitForTimeout(1500);
  await pinEvaluate(page, () => {
    const w: any = window;
    const made: any = {}; Object.keys(w.RUNEWORD_TIP || {}).forEach((n) => { if (n !== 'Insight') made[n] = 'x'; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    localStorage.setItem('d2r_rwProfile', 'fresh');
  });
  await reloadPinned(page); await page.waitForTimeout(1500);
  const r = await page.evaluate(async () => {
    const w: any = window;
    w._ensureSocketBaseEntry('Colossus Voulge (Larzuk base)');
    w.switchTab('forge'); w.renderForge();
    await new Promise((res) => setTimeout(res, 300));
    const card = () => [...document.querySelectorAll('#tab-forge .f-atom')]
      .find((c) => /Insight|Larzuk-socket/.test(c.textContent || ''));
    const c1 = card();
    const step2 = {
      text: (c1?.textContent || '').replace(/\s+/g, ' '),
      hasBack: !!c1?.querySelector('button[onclick*="forgeStepBack"]'),
    };
    w.forgeStepBack('chain|Colossus Voulge (Larzuk base)|4|l');   // v696 — the v684 key format, same as the seed
    await new Promise((res) => setTimeout(res, 300));
    const c2 = card();
    const step1 = {
      text: (c2?.textContent || '').replace(/\s+/g, ' '),
      hasBack: !!c2?.querySelector('button[onclick*="forgeStepBack"]'),
      store: JSON.parse(localStorage.getItem('d2r_forgeStep') || '{}'),
    };
    return { step2, step1 };
  });
  // stale memory put the chain at its FINAL step — the card must name BOTH the word and the base
  expect(r.step2.text).toContain('Forge');
  expect(r.step2.text).toContain('Insight');
  expect(r.step2.text).toContain('Colossus Voulge');   // v597 — step 2 names its base
  expect(r.step2.text).toContain('step 2 / 2');
  expect(r.step2.hasBack).toBe(true);                  // v597 — the ↺ back control renders past step 1
  // walking back lands on the Larzuk step, and step 1 has no back control
  expect(r.step1.text).toContain('Larzuk-socket');
  expect(r.step1.text).toContain('step 1 / 2');
  expect(r.step1.hasBack).toBe(false);
  expect(r.step1.store['chain|Colossus Voulge (Larzuk base)|4|l'] || 0).toBe(0);
});
