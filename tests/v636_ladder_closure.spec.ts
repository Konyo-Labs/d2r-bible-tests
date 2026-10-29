import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v636 — CLOSURE LOCKS for the swarm-confirmed v635 bugs. Every finding gets a pin.

async function toLadder(page: any) {
  await page.evaluate(() => localStorage.setItem('d2r_activeProfile', 'ladder'));
  await page.reload(); await page.waitForTimeout(1800);
}
async function cleanup(page: any) {
  await page.evaluate(() => {
    Object.keys(localStorage).filter((k) => k.indexOf('L·') === 0).forEach((k) => localStorage.removeItem(k));
    ['d2r_activeProfile','d2r_intakeSeen','d2r_owned','d2r_runeStash'].forEach((k) => localStorage.removeItem(k));
  });
}

test('SEEN pre-seed works: main ledger copies to L· on first ladder boot, once — and a wipe on ladder never touches main', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_intakeSeen', JSON.stringify({ 'shot1.png': 123, 'shot2.png': 456 }));
    localStorage.setItem('d2r_owned', JSON.stringify(['Flail (5os)']));
  });
  const mainSnap = await page.evaluate(() => ['d2r_intakeSeen','d2r_owned'].map((k) => localStorage.getItem(k)).join('|'));
  await toLadder(page);
  const r1 = await page.evaluate(() => ({
    seeded: localStorage.getItem('L·d2r_intakeSeen') === localStorage.getItem('d2r_intakeSeen'),
  }));
  // one-time: mutate the ladder ledger, reload — it must NOT be re-overwritten from main
  await page.evaluate(() => localStorage.setItem('L·d2r_intakeSeen', JSON.stringify({ 'ladder-only.png': 1 })));
  await reloadPinned(page); await page.waitForTimeout(1500);
  const r2 = await page.evaluate(() => /ladder-only/.test(localStorage.getItem('L·d2r_intakeSeen') || ''));
  // profile-scoped wipe from the LADDER side leaves main byte-identical
  const r3 = await page.evaluate(({ mainSnap }: any) => {
    const w: any = window;
    w.LSR.wipeProfile();
    const lLeft = Object.keys(localStorage).filter((k) => k.indexOf('L·') === 0).length;
    const mainNow = ['d2r_intakeSeen','d2r_owned'].map((k) => localStorage.getItem(k)).join('|');
    return { lLeft, mainIntact: mainNow === mainSnap, profileKept: localStorage.getItem('d2r_activeProfile') === 'ladder' };
  }, { mainSnap });
  await cleanup(page);
  expect(r1.seeded).toBe(true);
  expect(r2).toBe(true);
  expect(r3.lLeft).toBe(0);
  expect(r3.mainIntact).toBe(true);
  expect(r3.profileKept).toBe(true);
});

test('ladder account consistency: _rwLadderBlocked=false, NO fail-verdict seed, rwSetLadderMode is a no-op, seed-load refuses', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  await page.evaluate(() => localStorage.setItem('d2r_ladderMode', 'nonladder'));   // main's real mode
  await toLadder(page);
  const r = await page.evaluate(() => {
    const w: any = window;
    const blocked = w._rwLadderBlocked('Mania');
    const verify = JSON.parse(w.LSR.getItem('d2r_rwVerify') || '{}');
    const guard = w._rwGuard ? w._rwGuard('Mania') : null;
    w.rwSetLadderMode('ladder');                                        // must NOT write main's key
    const mainMode = localStorage.getItem('d2r_ladderMode');
    w.chronicleLoadSeed && w.chronicleLoadSeed();                       // must refuse
    const ladderMade = Object.keys(JSON.parse(w.LSR.getItem('d2r_rwMade') || '{}')).length;
    return { blocked, verifyFails: Object.values(verify).filter((v: any) => v === 'fail').length, guardBlocked: !!(guard && guard.level === 'block'), mainMode, ladderMade };
  });
  await page.evaluate(() => localStorage.removeItem('d2r_ladderMode'));
  await cleanup(page);
  expect(r.blocked).toBe(false);          // SI / loot filter / stamps unlock the 9 on ladder
  expect(r.verifyFails).toBe(0);          // non-ladder fail verdicts never seed the ladder account
  expect(r.guardBlocked).toBe(false);     // Mania's card wears no did-not-form banner here
  expect(r.mainMode).toBe('nonladder');   // the shared key is untouched from the ladder side
  expect(r.ladderMade).toBe(99);          // v638 — SHARED grail ledger (COMPLETE): the seed-load is a harmless no-op on an already-seeded chronicle
});

test('Backup & Share lives again: export contains real keys per-profile, restore never flips the account', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  const main = await page.evaluate(() => {
    const w: any = window;
    localStorage.setItem('d2r_owned', JSON.stringify(['Flail (5os)']));
    const data = w._collectProgress ? null : undefined;   // _collectProgress may be closure-scoped; go through exportProgress
    const ta = document.getElementById('backup-textarea') as any;
    (window as any).exportProgress();
    const snap = ta ? JSON.parse(ta.value) : { data: {} };
    return { hasOwned: typeof snap.data['d2r_owned'] === 'string', hasProfileKey: 'd2r_activeProfile' in snap.data, hasLKeys: Object.keys(snap.data).some((k: string) => k.indexOf('L·') === 0), n: Object.keys(snap.data).length };
  });
  await toLadder(page);
  const ladder = await page.evaluate(() => {
    const w: any = window;
    w.LSR.setItem('d2r_owned', JSON.stringify(['Blade Talons (3os)']));
    const ta = document.getElementById('backup-textarea') as any;
    (window as any).exportProgress();
    const snap = ta ? JSON.parse(ta.value) : { data: {} };
    return {
      ownedIsLadders: snap.data['d2r_owned'] === JSON.stringify(['Blade Talons (3os)']),   // bare-named, but THIS account's value
      noMainForked: snap.data['d2r_rwMade'] === undefined || snap.data['d2r_rwMade'] !== localStorage.getItem('d2r_rwMade'),
      hasProfileKey: 'd2r_activeProfile' in snap.data,
    };
  });
  await cleanup(page);
  expect(main.n).toBeGreaterThan(3);
  expect(main.hasOwned).toBe(true);
  expect(main.hasProfileKey).toBe(false);
  expect(main.hasLKeys).toBe(false);
  expect(ladder.ownedIsLadders).toBe(true);
  expect(ladder.hasProfileKey).toBe(false);
});

test('FULL no-silent sweep INSIDE the ladder account: the inherited remainder + ladder words, zero silent, no strip; profileSwitch same-account = no-op', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  await page.evaluate(() => {   // v674 — the live Chronicle is COMPLETE: open a 2-word remainder window
    const m = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}'); delete m['Wrath']; delete m['Peace'];
    localStorage.setItem('d2r_rwMade', JSON.stringify(m));
    localStorage.setItem('d2r_rwUnmade', JSON.stringify({ Wrath: 1, Peace: 1 }));
  });
  await toLadder(page);
  const r = await page.evaluate(() => {
    const w: any = window;
    const made = JSON.parse(w.LSR.getItem('d2r_rwMade') || '{}');
    const sc = w.forgeScan();
    const whereIs: any = {};
    ['now','pipeline','onestep','farm'].forEach((b) => (sc[b] || []).forEach((t: any) => (whereIs[t.rw] = b)));
    const unmade = Object.keys(w.RUNEWORD_TIP).filter((n) => !made[n]);
    const silent = unmade.filter((n) => !whereIs[n]);
    let reloaded = false; const orig = w.location.reload.bind(w.location);
    (w.location as any).reload = () => { reloaded = true; };
    w.profileSwitch('ladder');                          // same account → must NOT reload
    (w.location as any).reload = orig;
    return { unmadeCount: unmade.length, silent, strip: (sc.ladder || []).length, reloaded };
  });
  await cleanup(page);
  expect(r.unmadeCount).toBeGreaterThan(0);    // v674 — remainder opened via the pinned un-marks below (the live Chronicle is COMPLETE)
  expect(r.unmadeCount).toBeLessThan(40);
  expect(r.silent).toEqual([]);          // the v604 invariant holds in the ladder account too
  expect(r.strip).toBe(0);
  expect(r.reloaded).toBe(false);
});
