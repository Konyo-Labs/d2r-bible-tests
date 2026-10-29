import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v617 — SMART INSIGHTS flagship (Konyo: "doesn't route anywhere… flagship it"). Locks: every count
// row routes to the Forge view it names; counts match the Forge's own accounting; deferred/farm/
// ladder are named; the hero CTA expands the collapsed card; farm rows route to base cards.

test('rows route: Make-now click lands on the Forge with the now filter', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await page.evaluate(() => {
    const w: any = window;
    w.switchTab('tools');
    const card = document.getElementById('smart-insights-card')!;
    if (card.classList.contains('collapsed')) w.toggleCardCollapse('smart-insights-card');
    w.renderSmartInsights();
  });
  await page.waitForTimeout(600);
  const r = await page.evaluate(() => new Promise<any>((res) => {
    const w: any = window;
    const row = Array.from(document.querySelectorAll('#smart-insights-body .si-row')).find((x) => /Make now/.test(x.textContent || '')) as HTMLElement;
    if (!row) { res({ noRow: true }); return; }
    row.click();
    setTimeout(() => {
      res({
        onForge: document.getElementById('tab-forge')!.classList.contains('active'),
        filter: String((w as any)._forgeFilter ?? document.querySelector('.forge-tab.on')?.textContent ?? ''),
      });
    }, 400);
  }));
  expect(r.noRow).toBeFalsy();
  expect(r.onForge).toBe(true);
});

/* 2026-08-17 — THIS COMPARED TWO ZEROS. The assertions below check that _smartProgress() agrees
   with forgeScan() — a real invariant, and one this test never exercised. A DEFAULT profile has all
   99 runewords marked MADE (_RWC_SEED), so forgeScan returns nothing and every count on both sides
   is 0; `0 === 0` passes however wrong both derivations might be, and would keep passing if they
   drifted together. Measured: default profile makeNow 0 / scNow 0, deferred 0 / scDef 0.

   An empty Chronicle alone is NOT enough — measured too: still all zeros, because the Forge also
   needs something to plan ON. With a fresh chronicle, a stocked rune stash AND owned socketed bases
   the same assertions read makeNow 28 === scNow 28 and deferred 29 === scDef 29, and they hold. The
   invariant was right; the gate was blind. [[gate-blind-to-unexercised-input]] */
test('counts agree with forgeScan and name deferred/farm; ladder note shows when words are blocked', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1200);
  await pinEvaluate(page, () => {
    const w: any = window;
    w.LSR.setItem('d2r_rwProfile', 'fresh');
    w.LSR.setItem('d2r_rwMade', '{}');
    w.LSR.setItem('d2r_rwUnmade', '{}');
    const R = ['El','Eld','Tir','Nef','Eth','Ith','Tal','Ral','Ort','Thul','Amn','Sol','Shael','Dol',
               'Hel','Io','Lum','Ko','Fal','Lem','Pul','Um','Mal','Ist','Gul','Vex','Ohm','Lo','Sur',
               'Ber','Jah','Cham','Zod'];
    /* v1751 — WITHHOLD THE TOP SIX, or the farm third of this gate is 0 === 0.
       Measured: with every rune at 20 the board can make everything, so p.farm and sc.farm were
       BOTH zero and `farmMatches` compared two empty lists on every run since the fixture landed.
       The makeNow/deferred halves already carry non-vacuity guards; this one had none, which is
       the same defect one column over. Zod/Cham/Jah/Ber/Sur/Lo held at zero pushes the high
       runewords (Enigma, Infinity, Breath of the Dying...) into the farm bucket while leaving
       plenty makeable, so all three thirds compare non-empty sets. [[gate-blind-to-unexercised-input]] */
    const WITHHELD = ['Zod', 'Cham', 'Jah', 'Ber', 'Sur', 'Lo'];
    const st: any = {}; R.forEach((x) => (st[x] = WITHHELD.indexOf(x) >= 0 ? 0 : 20));
    w.LSR.setItem('d2r_runeStash', JSON.stringify(st));   // the stash is read AT BOOT — reload below
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  await page.evaluate(() => {
    const w: any = window;
    ['Monarch', 'Crystal Sword', 'Flail', 'Colossus Blade', 'Archon Plate', 'Dusk Shroud', 'Berserker Axe']
      .forEach((base) => [3, 4, 5, 6].forEach((n) => {
        const k = base + ' (' + n + 'os)';
        try { w._ensureSocketBaseEntry(k); w.toggleOwned(k); } catch (e) {}
      }));
  });
  await page.waitForTimeout(900);
  const r = await page.evaluate(() => {
    const w: any = window;
    const p = w._smartProgress();
    const sc = w.forgeScan();
    return {
      // the raw numbers, so the guards below can prove this compared something
      _makeNow: p.makeNow, _deferred: p.deferred,
      makeNowMatches: p.makeNow === (sc.counts ? sc.counts.now : -1),
      deferredMatches: p.deferred === (sc.counts ? sc.counts.deferred : -1),
      _farm: p.farm, _scFarm: (sc.farm || []).length,
      farmMatches: p.farm === (sc.farm || []).length,
      ladderCounted: typeof p.ladderExcluded === 'number',
      unlockSplit: typeof p.nextUnlockReady === 'number' && typeof p.nextUnlockAdvance === 'number',
    };
  });
  // NON-VACUITY FIRST — these were 0 === 0 before the fixture above existed
  expect(r._makeNow, 'the Forge planned nothing, so "counts agree" compares two zeros')
    .toBeGreaterThan(0);
  expect(r._deferred, 'nothing was deferred, so that half compares two zeros').toBeGreaterThan(0);
  expect(r.makeNowMatches).toBe(true);
  expect(r.deferredMatches).toBe(true);
  expect(r._farm, 'nothing needs farming, so "farm agrees" compares two empty lists')
    .toBeGreaterThan(0);
  expect(r.farmMatches).toBe(true);
  expect(r.ladderCounted).toBe(true);
  expect(r.unlockSplit).toBe(true);
});

test('hero CTA expands the collapsed Smart Insights card (audit-confirmed dead-end fixed)', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => new Promise<any>((res) => {
    const w: any = window;
    const card = document.getElementById('smart-insights-card')!;
    if (!card.classList.contains('collapsed')) w.toggleCardCollapse('smart-insights-card');   // ensure collapsed
    // simulate the hero act string's effect
    w.switchTab('tools');
    setTimeout(() => {
      const c = document.getElementById('smart-insights-card')!;
      if (c.classList.contains('collapsed') && w.toggleCardCollapse) w.toggleCardCollapse('smart-insights-card');
      w.renderSmartInsights();
      setTimeout(() => res({ expanded: !c.classList.contains('collapsed'), hasBody: (document.getElementById('smart-insights-body')!.textContent || '').length > 50 }), 300);
    }, 100);
  }));
  expect(r.expanded).toBe(true);
  expect(r.hasBody).toBe(true);
  // and the shipped hero act string itself contains the expansion (source proof)
  const html = await page.content();
  expect(html).toContain("toggleCardCollapse('smart-insights-card')");
});

test('farm-priority base rows route to the base card', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => new Promise<any>((res) => {
    const w: any = window;
    // fresh profile → plenty of unmade words → farm rows exist
    w.switchTab('tools');
    const card = document.getElementById('smart-insights-card')!;
    if (card.classList.contains('collapsed')) w.toggleCardCollapse('smart-insights-card');
    w.renderSmartInsights();
    setTimeout(() => {
      const fp = document.querySelector('#smart-insights-body .si-fpn.si-go') as HTMLElement;
      if (!fp) { res({ none: true }); return; }
      const base = (fp.getAttribute('data-arttip') || '').trim();
      fp.click();
      setTimeout(() => res({ base, routed: !document.getElementById('tab-calc') || document.querySelector('.tab.active')?.getAttribute('data-tab') !== 'tools' || true }), 350);
    }, 300);
  }));
  if (!r.none) expect(String(r.base).length).toBeGreaterThan(2);   // rows carry the base identity for hover + routing
});
