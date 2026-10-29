import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v632 — LADDER-LOCKED VISIBILITY + the FULL-REMAINDER demonstration on Konyo's REAL live state
// (snapshot 2026-07-09: 13 owned bases, full rune ledger, 74 made). His ask: "make sure all the
// remaining runewords have tasks created to how to get to the endpoint within forge — reverse
// engineered, no more bugs. Do a proper simulation and check physically that it works."

const LIVE_OWNED = ["Superior Executioner Sword (6os)","Superior Champion Axe (5os)","Death Mask (Larzuk base)","Pluckeye","Sacred Rondache (Larzuk base)","Zweihander (5os)","Grim Scythe (6os)","Spetum (6os)","War Scythe (6os)","Grim Scythe (4os low base)","Flail (5os)","Great Axe (6os)","War Staff (6os)"];
const LIVE_RUNES = {"El":21,"Eld":33,"Tir":36,"Nef":41,"Eth":14,"Ith":13,"Tal":22,"Ral":68,"Ort":21,"Thul":36,"Amn":36,"Sol":25,"Shael":24,"Dol":20,"Hel":17,"Io":25,"Lum":17,"Ko":17,"Fal":21,"Lem":15,"Pul":18,"Um":9,"Mal":17,"Ist":14,"Gul":10,"Vex":10,"Ohm":10,"Lo":9,"Sur":4,"Ber":7,"Jah":8,"Cham":4,"Zod":2};

async function liveState(page: any) {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, ({ owned, runes }: any) => {
    localStorage.setItem('d2r_owned', JSON.stringify(owned));
    localStorage.setItem('d2r_runeStash', JSON.stringify(runes));
    localStorage.removeItem('d2r_ladderMode');   // his live state: unset → nonladder
    // v663 — the live seed moved on (88, ladder set complete); PIN the 2026-07-09 snapshot instead:
    // exactly the seed minus the 9 mod-ladder words minus tonight's 5 forges = his 74 that day.
    localStorage.setItem('d2r_rwProfile', 'fresh');
    const SEED = (window as any)._RWC_SEED || {};
    const POST = ['Cure','Ground','Hearth','Hysteria','Mania','Temper','Eternity','Metamorphosis','Bulwark','Silence','Exile','Radiance','Ritual','Rain','Vigilance','Ice','Faith','Enlightenment','Lionheart','Wealth','Myth','Unbending Will','Bramble','Peace','Wrath'];   // v674 — keeps the pinned Jul-9 snapshot at exactly 74
    const made: any = {}; Object.keys(SEED).forEach((n) => { if (POST.indexOf(n) < 0) made[n] = SEED[n]; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
  }, { owned: LIVE_OWNED, runes: LIVE_RUNES });
  await reloadPinned(page); await page.waitForTimeout(1800);
}
async function cleanup(page: any) {
  await page.evaluate(() => ['d2r_owned','d2r_runeStash','d2r_ladderMode','d2r_rwMade','d2r_rwBaseUsed','d2r_forgeStep','d2r_rwProfile'].forEach((k) => localStorage.removeItem(k)));
}

test('FULL REMAINDER (his live state): every unmade word is tasked OR in the ladder strip — zero silent words', async ({ page }) => {
  await liveState(page);
  const r = await page.evaluate(() => {
    const w: any = window;
    const made = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
    const sc = w.forgeScan();
    const whereIs: any = {};
    ['now','pipeline','onestep','farm'].forEach((b) => (sc[b] || []).forEach((t: any) => (whereIs[t.rw] = b)));
    (sc.ladder || []).forEach((t: any) => (whereIs[t.rw] = 'ladder'));
    const unmade = Object.keys(w.RUNEWORD_TIP).filter((n) => !made[n]);
    const silent = unmade.filter((n) => !whereIs[n]);
    // the forge DOM agrees: the ladder strip renders every ladder word by name
    w.switchTab('forge'); try { w.renderForge(); } catch (e) {}
    const strip = document.getElementById('forge-ladder-strip');
    const stripText = strip ? strip.textContent || '' : '';
    const stripMissing = (sc.ladder || []).filter((t: any) => stripText.indexOf(t.rw) < 0).map((t: any) => t.rw);
    // v1492 — WHICH HOME depends on the v1475 setting, so read it instead of assuming.
    const includeLadder = !!(w._forgeIncludeLadder && w._forgeIncludeLadder());
    const ladderOnly = Object.keys(w.RUNEWORD_TIP).filter((n: string) =>
      w._rwIsLadderOnly && w._rwIsLadderOnly(n) && !made[n]);
    const tasked = ladderOnly.filter((n: string) => ['now','pipeline','onestep','farm'].indexOf(whereIs[n]) >= 0);
    return { unmadeCount: unmade.length, silent, ladderCount: (sc.ladder || []).length,
             stripRendered: !!strip, stripMissing, includeLadder, ladderOnly, tasked };
  });
  await cleanup(page);
  expect(r.silent).toEqual([]);              // THE invariant: nothing hidden, ever
  // v1492 — v1475 answered Konyo's "we need it for forge... only for the forge specifically those
  // 8-9 runewords" by PLANNING the ladder-only words in the Forge lane instead of parking them in a
  // read-only strip. So the home changed, and the strip is empty BY DESIGN whenever that setting is
  // on (its default). This spec asserts the invariant first and then the home for the SETTING THAT
  // IS ACTUALLY SET — it used to hardcode the pre-v1475 answer, which is why it survived the change
  // on CI only: the cousin world has no owner seed, so nothing was unmade to place either way.
  if (r.includeLadder) {
    expect(r.tasked, 'ladder-only words must be REAL forge tasks when the Forge plans them')
      .toEqual(r.ladderOnly);
    expect(r.ladderCount).toBe(0);           // nothing left to park
    expect(r.stripRendered).toBe(false);     // and no strip to render
  } else {
    expect(r.ladderCount).toBeGreaterThan(0);  // the 9 mod-ladder words are visibly parked
    expect(r.stripRendered).toBe(true);
    expect(r.stripMissing).toEqual([]);
  }
});

test('ladder-mode flip demo: the strip empties and every former ladder word becomes a REAL task — still zero silent', async ({ page }) => {
  await liveState(page);
  const r = await page.evaluate(() => {
    const w: any = window;
    // v1492 — this demo needs words PARKED in the strip to then watch them become tasks, and since
    // v1475 the Forge plans them by default so the strip starts empty. Turn that setting off first
    // (the product's own switch) instead of relying on a default that has since changed sides.
    try { w._forgeSetIncludeLadder(false); } catch (e) {}
    const before = (w.forgeScan().ladder || []).map((t: any) => t.rw);
    w.rwSetLadderMode('ladder');
    const sc = w.forgeScan();
    const whereIs: any = {};
    ['now','pipeline','onestep','farm'].forEach((b) => (sc[b] || []).forEach((t: any) => (whereIs[t.rw] = b + (t.base && t.base.name ? ' @' + t.base.name : ''))));
    const nowTasked = before.map((n: string) => n + ' → ' + (whereIs[n] || 'SILENT'));
    const made = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
    const unmade = Object.keys(w.RUNEWORD_TIP).filter((n) => !made[n]);
    const silent = unmade.filter((n) => !whereIs[n] && !(sc.ladder || []).some((t: any) => t.rw === n));
    w.rwSetLadderMode('nonladder');
    try { w._forgeSetIncludeLadder(true); } catch (e) {}   // v1492 — restore the shipped default
    return { before, nowTasked, silent, ladderAfter: (sc.ladder || []).length };
  });
  await cleanup(page);
  expect(r.before.length).toBeGreaterThan(0);
  expect(r.nowTasked.every((x: string) => !/SILENT/.test(x))).toBe(true);   // all 9 get real paths on ladder
  expect(r.ladderAfter).toBe(0);
  expect(r.silent).toEqual([]);
});

test('lifecycle demo to the ENDPOINT (his real Death Mask): Radiance pipeline → ✓ created → Chronicle 75, task gone, invariant still holds', async ({ page }) => {
  await liveState(page);
  const r = await page.evaluate(() => {
    const w: any = window;
    const sc0 = w.forgeScan();
    const rad0 = [].concat(sc0.now || [], sc0.pipeline || []).find((t: any) => t.rw === 'Radiance');
    const before = { kind: rad0 && rad0.kind, base: rad0 && rad0.base && rad0.base.name };
    w.rwToggleMade('Radiance', rad0 && rad0.base && rad0.base.name);      // what "✓ created" calls
    const made = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
    const sc1 = w.forgeScan();
    const whereIs: any = {};
    ['now','pipeline','onestep','farm'].forEach((b) => (sc1[b] || []).forEach((t: any) => (whereIs[t.rw] = b)));
    (sc1.ladder || []).forEach((t: any) => (whereIs[t.rw] = 'ladder'));
    const unmade = Object.keys(w.RUNEWORD_TIP).filter((n) => !made[n]);
    const silent = unmade.filter((n) => !whereIs[n]);
    const stillTasked = [].concat(sc1.now || [], sc1.pipeline || [], sc1.onestep || [], sc1.farm || []).some((t: any) => t.rw === 'Radiance');
    return { before, madeCount: Object.keys(made).length, stillTasked, silent };
  });
  await cleanup(page);
  expect(r.before.kind).toBe('pipeline');
  expect(r.before.base).toBe('Death Mask (Larzuk base)');   // HIS helm hosts it
  expect(r.madeCount).toBe(75);                             // v663 — 74 pinned (the Jul-9 snapshot) + Radiance
  expect(r.stillTasked).toBe(false);                        // task evaporated at the endpoint
  expect(r.silent).toEqual([]);                             // coverage never breaks mid-journey
});
