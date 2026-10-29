import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v635 — TIER-2 LADDER PROFILE (Konyo: "a smooth polished toggle that ascends perfectly from
// non-ladder to ladder. make sure nothing bleeds"). One storage router (window.LSR): the main
// profile keeps its unprefixed d2r_* keys byte-for-byte; the ladder profile lives under 'L·'.
// Switching = a full reload. The engine is IDENTICAL — it just reads the active account's stash.

// v636 — the snapshot derives from the SOURCE OF TRUTH (_LP_FORKED, all 37 keys) + the shared
// d2r_ladderMode canary, so un-forking ANY account key or a raw-write regression fails the gate.
const SNAP_JS = `[...(window)._LP_FORKED, 'd2r_ladderMode'].sort().map((k) => k + '=' + (localStorage.getItem(k) || '')).join('|')`;

test('BLEED-PROOF: forge/tally/create in the LADDER profile — the main profile stays byte-identical (and vice versa)', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  // arrange a recognizable MAIN state — then RELOAD before snapshotting, so the v659 grail
  // found-seed floor (which rewrites d2r_owned/d2r_foundLog on a main boot) is already baked
  // into the baseline; otherwise the round-trip's re-boot makes main look changed when it isn't.
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_owned', JSON.stringify(['Flail (5os)']));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ El: 3 }));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const mainBefore = await page.evaluate(({ SNAP_JS }: any) => eval(SNAP_JS), { SNAP_JS });
  // ascend to ladder
  await page.evaluate(() => { localStorage.setItem('d2r_activeProfile', 'ladder'); });
  await page.reload(); await page.waitForTimeout(1800);
  const ladder = await pinEvaluate(page, () => {
    const w: any = window;
    // fresh account: nothing of main's is visible
    const cleanStart = {
      owned: JSON.parse(w.LSR.getItem('d2r_owned') || '[]').length,
      made: Object.keys(JSON.parse(w.LSR.getItem('d2r_rwMade') || '{}')).length,
      runes: Object.keys(JSON.parse(w.LSR.getItem('d2r_runeStash') || '{}')).length,
    };
    // live a whole ladder life: own a 4os bow, tally Wrath's runes, forge it
    // (v674 — 99/99: NO unseeded word exists. The journey opens its own window: Wrath is pinned
    // un-made via d2r_rwUnmade (the floor honors user un-marks), forged in the journey, resealing 99.)
    w.LSR.setItem('d2r_owned', JSON.stringify(['Blade Bow (4os)']));
    // v674 — open the journey window: the initial seed-fill ignores rwUnmade, so Wrath must also
    // leave the STORED chronicle; the honored un-mark then keeps the floor from re-adding it.
    const _sm = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}'); delete _sm['Wrath'];
    localStorage.setItem('d2r_rwMade', JSON.stringify(_sm));
    localStorage.setItem('d2r_rwUnmade', JSON.stringify({ Wrath: 1 }));
    const _rec = ((w.RUNEWORD_TIP['Wrath'] || {}).rec || []); const _st: any = {}; _rec.forEach((rn: string) => (_st[rn] = (_st[rn] || 0) + 1));
    w.LSR.setItem('d2r_runeStash', JSON.stringify(_st));
    return cleanStart;
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const ladderLife = await page.evaluate(() => {
    const w: any = window;
    const sc = w.forgeScan();
    const mania = [].concat(sc.now || [], sc.pipeline || [], sc.onestep || []).find((t: any) => t.rw === 'Wrath');
    const laddered = (sc.ladder || []).length;                       // ladder profile: NO locked strip
    w.rwToggleMade('Wrath', mania && mania.base && mania.base.name); // ✓ created — the REAL engine
    const made = Object.keys(JSON.parse(w.LSR.getItem('d2r_rwMade') || '{}'));
    return { maniaKind: mania && mania.kind, maniaBase: mania && mania.base && mania.base.base, laddered, madeN: made.length, hasMania: made.includes('Wrath') };
  });
  // descend to main — byte-identical
  await page.evaluate(() => { localStorage.setItem('d2r_activeProfile', 'main'); });
  await page.reload(); await page.waitForTimeout(1800);
  const mainAfter = await page.evaluate(({ SNAP_JS }: any) => eval(SNAP_JS), { SNAP_JS });
  // ladder data SURVIVES the round-trip
  await page.evaluate(() => { localStorage.setItem('d2r_activeProfile', 'ladder'); });
  await page.reload(); await page.waitForTimeout(1800);
  const ladderPersist = await page.evaluate(() => {
    const w: any = window;
    // creating Wrath CONSUMED the Blade Bow (the real engine ran) — assert the consume trail
    const used = JSON.parse(w.LSR.getItem('d2r_rwBaseUsed') || '{}');
    const made = Object.keys(JSON.parse(w.LSR.getItem('d2r_rwMade') || '{}'));
    return { madeN: made.length, hasMania: made.includes('Wrath'), owned: JSON.parse(w.LSR.getItem('d2r_owned') || '[]'),
             consumed: used['Wrath'] && used['Wrath'].l };
  });
  // cleanup: back to main, wipe ladder keys + test main keys
  await page.evaluate(() => {
    Object.keys(localStorage).filter((k) => k.indexOf('L·') === 0).forEach((k) => localStorage.removeItem(k));
    localStorage.removeItem('d2r_activeProfile'); localStorage.removeItem('d2r_owned'); localStorage.removeItem('d2r_runeStash'); localStorage.removeItem('d2r_rwUnmade');
  });
  expect(ladder.owned).toBe(0);           // fresh account: no bases bleed in
  expect(ladder.made).toBe(99);           // v674 — the COMPLETE shared chronicle is visible on ladder at first read; the Wrath window applies on the next reload
  expect(ladder.runes).toBe(0);           // no rune tallies bleed in (physical stash stays separate)
  expect(ladderLife.laddered).toBe(0);    // ladder profile: the 9 are UNLOCKED (no strip)
  expect(ladderLife.maniaKind).toBe('now');
  expect(ladderLife.maniaBase).toBe('Blade Bow');
  expect(ladderLife.madeN).toBe(99);           // the journey re-forges Wrath → the Chronicle re-seals at 99
  expect(ladderLife.hasMania).toBe(true);
  expect(mainAfter).toBe(mainBefore);     // ★ NOTHING BLEEDS — byte-identical main
  expect(ladderPersist.madeN).toBe(99);                       // sealed at 99 after the journey
  expect(ladderPersist.hasMania).toBe(true);
  expect(ladderPersist.owned).not.toContain('Blade Bow (4os)');   // the forge CONSUMED it — full engine, ladder-side
  expect(ladderPersist.consumed).toBe('Blade Bow (4os)');         // and the consume trail says so
});

test('main profile is untouched-by-default: no L· keys exist until ladder is ever used; boot count stays 99', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    return {
      profile: w.D2R_PROFILE,
      made: Object.keys(JSON.parse(localStorage.getItem('d2r_rwMade') || '{}')).length,
      lKeys: Object.keys(localStorage).filter((k) => k.indexOf('L·') === 0).length,
      routerSame: w.LSR.getItem('d2r_rwMade') === localStorage.getItem('d2r_rwMade'),   // main routes to bare keys
    };
  });
  expect(r.profile).toBe('main');
  expect(r.made).toBe(99);
  expect(r.lKeys).toBe(0);
  expect(r.routerSame).toBe(true);
});

test('UX — the header account pill switches profiles; the ladder account wears the 🪜 cue everywhere', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  const main = await page.evaluate(() => {
    const pill = document.getElementById('profile-pill');
    return { pill: !!pill, text: pill ? pill.textContent || '' : '', ribbon: document.body.classList.contains('ladder-profile') };
  });
  await page.evaluate(() => { localStorage.setItem('d2r_activeProfile', 'ladder'); });
  await page.reload(); await page.waitForTimeout(1800);
  const ladder = await page.evaluate(() => {
    const pill = document.getElementById('profile-pill');
    const rb = document.getElementById('ladder-ribbon');
    const thin = rb ? rb.getBoundingClientRect().height < 40 : false;   // a slim banner, never a content wash
    const aboveHeader = rb ? parseInt(getComputedStyle(rb).zIndex || '0', 10) > 100 : false;   // header is sticky z:100 — the cue must outrank it
    return { text: pill ? pill.textContent || '' : '', ribbon: document.body.classList.contains('ladder-profile') && !!rb && thin && aboveHeader };
  });
  await page.evaluate(() => {
    Object.keys(localStorage).filter((k) => k.indexOf('L·') === 0).forEach((k) => localStorage.removeItem(k));
    localStorage.removeItem('d2r_activeProfile');
  });
  expect(main.pill).toBe(true);
  expect(/MAIN/i.test(main.text)).toBe(true);
  expect(main.ribbon).toBe(false);
  expect(/LADDER/i.test(ladder.text)).toBe(true);
  expect(ladder.ribbon).toBe(true);       // unmistakable account cue
});
