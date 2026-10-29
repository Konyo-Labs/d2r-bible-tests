import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned, gotoPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v631 — a '<known base> (Nos)' read stuck in unknownReads whose sockets exact-fit an unmade word
// gets PROMOTED to an owned socketed base at boot (Konyo's Heavy Crossbow (5os) → Mist: the v629
// host map saw it, but the Forge planner could not task it). Junk reads stay put.

test("Heavy Crossbow (5os) in unknownReads + Mist unmade + runes ready → promoted at boot, Mist becomes a MAKE-NOW forge in HIS crossbow", async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_owned', JSON.stringify([]));
    localStorage.setItem('d2r_unknownReads', JSON.stringify(['Heavy Crossbow (5os)', 'Weird Trinket Xyz', 'Buckler (1os)']));
    const st: any = {};
    ['El','Eld','Tir','Nef','Eth','Ith','Tal','Ral','Ort','Thul','Amn','Sol','Shael','Dol','Hel','Io','Lum','Ko','Fal','Lem','Pul','Um','Mal','Ist','Gul','Vex','Ohm','Lo','Sur','Ber','Jah','Cham','Zod'].forEach((n) => (st[n] = 6));
    localStorage.setItem('d2r_runeStash', JSON.stringify(st));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    const ownedNow = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
    const unkNow = JSON.parse(localStorage.getItem('d2r_unknownReads') || '[]');
    const sc = w.forgeScan();
    const mist = [].concat(sc.now || [], sc.pipeline || [], sc.onestep || []).find((t: any) => t.rw === 'Mist');
    ['d2r_rwProfile','d2r_rwMade','d2r_owned','d2r_unknownReads','d2r_runeStash'].forEach((k) => localStorage.removeItem(k));
    return {
      promoted: ownedNow.includes('Heavy Crossbow (5os)'),
      unkKeptTrinket: unkNow.includes('Weird Trinket Xyz'),
      mistKind: mist && mist.kind, mistBase: mist && mist.base && mist.base.base,
    };
  });
  expect(r.promoted).toBe(true);              // capability surfaced
  expect(r.unkKeptTrinket).toBe(true);        // non-base reads untouched
  expect(r.mistKind).toBe('now');             // and the Forge tasks it as make-NOW
  expect(r.mistBase).toBe('Heavy Crossbow');  // in HIS crossbow, not a go-shopping wishlist
});

test('a socket-known base that fits NOTHING unmade stays in the needs-a-look ledger (no junk promotion)', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    // mark every word a 3os short bow could host as MADE → nothing unmade fits
    localStorage.setItem('d2r_owned', JSON.stringify([]));
    localStorage.setItem('d2r_unknownReads', JSON.stringify(['Short Bow (3os)']));
  });
  await gotoPinned(page, URL.replace('bible.html', 'bible.html') + '?x=1'); await page.waitForTimeout(1500);
  const r = await pinEvaluate(page, () => {
    const w: any = window;
    const made: any = {};
    (w._baseRunewords('Short Bow') || []).filter((x: any) => x.s === 3).forEach((x: any) => (made[x.n] = 'x'));
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    return Object.keys(made).length;
  });
  expect(r).toBeGreaterThan(0);
  await reloadPinned(page); await page.waitForTimeout(1800);
  const after = await page.evaluate(() => {
    const unkNow = JSON.parse(localStorage.getItem('d2r_unknownReads') || '[]');
    const ownedNow = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
    ['d2r_rwProfile','d2r_rwMade','d2r_owned','d2r_unknownReads'].forEach((k) => localStorage.removeItem(k));
    return { stays: unkNow.includes('Short Bow (3os)'), notOwned: !ownedNow.includes('Short Bow (3os)') };
  });
  expect(after.stays).toBe(true);
  expect(after.notOwned).toBe(true);
});
