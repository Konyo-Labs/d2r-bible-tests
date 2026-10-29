import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v634 — TIER-1 LADDER PREVIEW: a pure VIEW toggle on the 🪜 strip. Expanded, each ladder word
// shows a full read-only plan (recipe · base to farm · ladder-economy note). ZERO writes to game
// state — the exact anti-messiness contract Konyo asked for after the live-flip incident.

test('v655 — at the owner seed (all 9 ladder words made) the strip and pill are GONE: nothing left to preview', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    w.switchTab('forge'); try { w.renderForge(); } catch (e) {}
    const forge = document.getElementById('tab-forge')!;
    return { strip: !!document.getElementById('forge-ladder-strip'),
             pill: [...forge.querySelectorAll('.forge-restore-top button')].some((b) => /ladder plans/i.test(b.textContent || '')),
             ladder: (w.forgeScan().ladder || []).length };
  });
  expect(r.ladder).toBe(0);
  expect(r.strip).toBe(false);
  expect(r.pill).toBe(false);
});

test('toggle expands the 8 plan cards (fresh chronicle) (recipe + base + 🪜 ribbon), collapses back — and game state is BYTE-IDENTICAL', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  // v655 — the ladder set is COMPLETE at the owner seed; pin a FRESH chronicle so the strip exists to test
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    // v1492 — turn OFF the v1475 "plan the ladder words in the Forge" setting. That feature is what
    // Konyo asked for ("only for the forge specifically those 8-9 runewords") and it empties this
    // strip BY DESIGN, so the preview covered here only has content with the setting off. Drive the
    // product's own switch instead of depending on which side its default sits.
    try { (window as any)._forgeSetIncludeLadder(false); } catch (e) {}
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    const KEYS = ['d2r_owned','d2r_unknownReads','d2r_rwMade','d2r_ladderMode','d2r_rwBaseUsed','d2r_copies','d2r_runeStash'];
    const snap = () => KEYS.map((k) => k + '=' + (localStorage.getItem(k) || '')).join('|');
    const before = snap();
    w.switchTab('forge'); try { w.renderForge(); } catch (e) {}
    const strip0 = document.getElementById('forge-ladder-strip')!;
    const collapsed = strip0.querySelectorAll('.forge-ladder-plan').length === 0 && strip0.querySelectorAll('.f-getchip').length >= 8;
    (document.getElementById('forge-ladder-preview-btn') as any).click();          // 🪜 show ladder plans
    const strip1 = document.getElementById('forge-ladder-strip')!;
    const plans = [...strip1.querySelectorAll('.forge-ladder-plan')];
    const byTitle = (n: string) => plans.find((c) => c.querySelector('.f-cardtitle [data-arttip="' + n + '"]'));
    const mania = byTitle('Metamorphosis');   // v651 — the last remaining ladder word
    const expanded = {
      count: plans.length,
      allRibboned: plans.every((c) => /ladder-only/.test(c.textContent || '')),
      maniaRecipe: !!(mania && mania.querySelector('.f-atomrecipe')),
      maniaBase: !!(mania && /base:/.test(mania.textContent || '')),
      maniaBaseHover: !!(mania && mania.querySelector('.f-getchip-base[data-arttip]')),   // v634.2 — HD floating card on the base chip
      wordHover: !!(mania && mania.querySelector('.f-cardtitle [data-arttip]')),

      noButtons: plans.every((c) => c.querySelectorAll('button').length === 0),     // read-only: no ✓ created
    };
    (document.getElementById('forge-ladder-preview-btn') as any).click();          // hide again
    const strip2 = document.getElementById('forge-ladder-strip')!;
    const recollapsed = strip2.querySelectorAll('.forge-ladder-plan').length === 0;
    const after = snap();
    localStorage.removeItem('d2r_ladderPreview'); localStorage.removeItem('d2r_rwProfile'); localStorage.removeItem('d2r_rwMade');
    return { collapsed, expanded, recollapsed, stateIdentical: before === after };
  });
  expect(r.collapsed).toBe(true);
  expect(r.expanded.count).toBe(8);   // fresh chronicle: all 8 real ladder words (Hustle is out of the catalog)
  expect(r.expanded.allRibboned).toBe(true);
  expect(r.expanded.maniaRecipe).toBe(true);
  expect(r.expanded.maniaBase).toBe(true);
  expect(r.expanded.maniaBaseHover).toBe(true);
  expect(r.expanded.wordHover).toBe(true);
  expect(r.expanded.noButtons).toBe(true);
  expect(r.recollapsed).toBe(true);
  expect(r.stateIdentical).toBe(true);   // THE contract: previewing never touches the account
});

test('v634.2 — the TOP-of-forge 🪜 pill exists, names the remaining count, and toggles the same preview', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    // v1492 — turn OFF the v1475 "plan the ladder words in the Forge" setting. That feature is what
    // Konyo asked for ("only for the forge specifically those 8-9 runewords") and it empties this
    // strip BY DESIGN, so the preview covered here only has content with the setting off. Drive the
    // product's own switch instead of depending on which side its default sits.
    try { (window as any)._forgeSetIncludeLadder(false); } catch (e) {}
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    w.switchTab('forge'); try { w.renderForge(); } catch (e) {}
    const forge = document.getElementById('tab-forge')!;
    const pill = [...forge.querySelectorAll('.forge-restore-top button')].find((b) => /ladder plans/i.test(b.textContent || ''));
    const pillRow = pill && pill.closest('.forge-restore-top');
    const stripCount = (w.forgeScan().ladder || []).length;
    const countShown = !!(pillRow && new RegExp('\\b' + stripCount + '\\b').test(pillRow.textContent || ''));
    // the pill sits ABOVE the strip in DOM order (top placement)
    const strip = document.getElementById('forge-ladder-strip');
    const above = !!(pillRow && strip && (pillRow.compareDocumentPosition(strip) & Node.DOCUMENT_POSITION_FOLLOWING));
    (pill as any).click();
    const plans = document.querySelectorAll('.forge-ladder-plan').length;
    // v634.3 — EXPANDED, the plan section renders at the TOP of the forge (above 🌾 Furthest out);
    // collapsing locks it back to the bottom chip strip. Pure render-order, zero state.
    const stripUp = document.getElementById('forge-ladder-strip');
    const farmSec = [...document.querySelectorAll('#tab-forge .forge-sec')].find((x) => /Furthest out/.test(x.textContent || ''));
    const expandedOnTop = !!(stripUp && farmSec && (stripUp.compareDocumentPosition(farmSec) & Node.DOCUMENT_POSITION_FOLLOWING));
    localStorage.removeItem('d2r_ladderPreview'); try { w.renderForge(); } catch (e) {}
    const backDown = (() => { const st = document.getElementById('forge-ladder-strip'); const f2 = [...document.querySelectorAll('#tab-forge .forge-sec')].find((x) => /Furthest out/.test(x.textContent || '')); return !!(st && f2 && (f2.compareDocumentPosition(st) & Node.DOCUMENT_POSITION_FOLLOWING) && st.querySelectorAll('.forge-ladder-plan').length === 0); })();
    return { pillThere: !!pill, countShown, above, plansAfterClick: plans, stripCount, expandedOnTop, backDown };
  });
  expect(r.pillThere).toBe(true);
  expect(r.countShown).toBe(true);
  expect(r.above).toBe(true);
  expect(r.plansAfterClick).toBe(r.stripCount);
  expect(r.expandedOnTop).toBe(true);   // toggled ON → plans flood the TOP of the forge
  expect(r.backDown).toBe(true);        // toggled OFF → locked back to the bottom chips
});
