import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v604 — FORGE COVERAGE INVARIANT (Konyo 2026-07-07: "I don't see the katara 3 sockets in my forge…
// I want simulations and checking and full auditing for this type of thing not happening").
// The incident: his in-game Katar (3os) was never scanned → the vault had no claw → Pattern sat in the
// "go get a base" one-steps instead of a make-now on HIS base. The ENGINE was right; the failure class
// to guard is silence: an unmade word missing from the Forge entirely, or an owned exact-fit base the
// Forge doesn't assign. Two permanent locks:
//   (1) INVARIANT — every unmade, non-ladder-blocked runeword has a forgeScan task (now/pipeline/onestep
//       incl. get-base) AND its name renders in the Forge tab's real DOM. No silent words, ever.
//   (2) UX SIM — registering an exact-fit base (the Katar scenario) must move its word from a get-base
//       one-step to a task ON that base, visible in the rendered DOM next to the base's name.

test('every unmade non-ladder word is tasked in forgeScan AND rendered in the Forge DOM', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {   // v674 — the live Chronicle is COMPLETE (99/99): open a 2-word window so the invariant has subjects
    const m = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}'); delete m['Wrath']; delete m['Peace'];
    localStorage.setItem('d2r_rwMade', JSON.stringify(m));
    localStorage.setItem('d2r_rwUnmade', JSON.stringify({ Wrath: 1, Peace: 1 }));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    w.switchTab && w.switchTab('forge');
    try { w.renderForge && w.renderForge(); } catch (e) {}
    const md = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
    const sc = w.forgeScan();
    const tasked = new Set([].concat(sc.now || [], sc.pipeline || [], sc.onestep || [], sc.farm || []).map((t: any) => t.rw));
    const unmade = Object.keys(w.RUNEWORD_TIP || {}).filter((n) => !md[n]);
    const live = unmade.filter((n) => !(typeof w._rwLadderBlocked === 'function' && w._rwLadderBlocked(n)));
    const dom = (document.getElementById('forge-body') || document.body).textContent || '';
    return {
      liveCount: live.length,
      farmCount: (sc.farm || []).length,
      missingFromScan: live.filter((n) => !tasked.has(n)),
      missingFromDom: live.filter((n) => !dom.includes(n)),
    };
  });
  expect(r.liveCount).toBeGreaterThan(0);       // the pinned 2-word window
  expect(r.farmCount).toBeGreaterThan(0);       // fresh profile (no bases, no runes) → the catch-all fires
  expect(r.missingFromScan).toEqual([]);        // no word may silently vanish from the engine
  await page.evaluate(() => { localStorage.removeItem('d2r_rwUnmade'); });   // v674 hygiene
  expect(r.missingFromDom).toEqual([]);         // …or from what Konyo actually SEES
  expect(errors).toEqual([]);
});

test('Katar scenario: registering an owned exact-fit base moves its word onto that base, visibly', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  // v615 — Pattern is in the 66-word owner seed now; a fresh profile is the only way to have it unmade
  await pinEvaluate(page, () => { localStorage.setItem('d2r_rwProfile', 'fresh'); localStorage.setItem('d2r_rwMade', JSON.stringify({})); });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const before = await page.evaluate(() => {
    const w: any = window;
    const sc = w.forgeScan();
    const pat = [].concat(sc.now || [], sc.pipeline || [], sc.onestep || [], sc.farm || []).find((t: any) => t.rw === 'Pattern');
    return { kind: pat && pat.kind, sub: pat && pat.sub, base: (pat && pat.base && pat.base.name) || null };
  });
  // no claw owned → Pattern must still be SURFACED: a get-base one-step (runes ready, Konyo's browser)
  // or the 🌾 farm catch-all (fresh profile, no runes) — but NEVER absent, and never on a base
  expect(['onestep', 'farm']).toContain(before.kind);
  if (before.kind === 'onestep') expect(before.sub).toBe('base');
  expect(before.base).toBeNull();
  const after = await pinEvaluate(page, () => {
    const w: any = window;
    w._ensureSocketBaseEntry('Katar (3os)', true);
    (w.owned || null); // page-scope `owned` isn't on window — persist via localStorage like the intake does
    const own = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
    if (own.indexOf('Katar (3os)') < 0) own.push('Katar (3os)');
    localStorage.setItem('d2r_owned', JSON.stringify(own));
    return true;
  });
  expect(after).toBe(true);
  await reloadPinned(page); await page.waitForTimeout(1800);   // owned set re-inits from localStorage
  const r = await page.evaluate(() => {
    const w: any = window;
    w.switchTab && w.switchTab('forge');
    try { w.renderForge && w.renderForge(); } catch (e) {}
    const sc = w.forgeScan();
    const pat = [].concat(sc.now || [], sc.pipeline || [], sc.onestep || [], sc.farm || []).find((t: any) => t.rw === 'Pattern');
    const dom = (document.getElementById('forge-body') || document.body).textContent || '';
    localStorage.removeItem('d2r_rwMade'); localStorage.removeItem('d2r_owned'); localStorage.removeItem('d2r_rwProfile');
    return {
      base: (pat && pat.base && pat.base.name) || null,
      kind: pat && pat.kind, sub: pat && pat.sub,
      domHasPair: dom.includes('Pattern') && dom.includes('Katar'),
    };
  });
  expect(r.base).toBe('Katar (3os)');           // the word is now assigned to HIS base…
  expect(['now', 'onestep', 'pipeline']).toContain(r.kind);  // now if runes tallied, onestep 'runes' if not
  if (r.kind === 'onestep') expect(r.sub).not.toBe('base');  // …never still a "go get a base"
  expect(r.domHasPair).toBe(true);              // …and the rendered Forge SHOWS Pattern with Katar
});
