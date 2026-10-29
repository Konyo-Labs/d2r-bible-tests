import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v630 — EXCLUSIVITY RESERVATION (Konyo's Exile-vs-Phoenix): a class-locked word (auric shields,
// claws, orbs…) gets first claim on its owned host copy; broad words must not burn it, they
// re-task as get-ANOTHER-base with an honest 'earmarked for X' narration. Plus the Mist pin:
// an owned exact-fit bow IS the task's base (not just the meta wishlist).

const PINS = (extra: any = {}) => ({ ...extra });

async function fresh(page: any, owned: string[], runes: 'full' | 'none') {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, ({ owned, runes }: any) => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_owned', JSON.stringify(owned));
    const st: any = {};
    if (runes === 'full') ['El','Eld','Tir','Nef','Eth','Ith','Tal','Ral','Ort','Thul','Amn','Sol','Shael','Dol','Hel','Io','Lum','Ko','Fal','Lem','Pul','Um','Mal','Ist','Gul','Vex','Ohm','Lo','Sur','Ber','Jah','Cham','Zod'].forEach((n) => (st[n] = 6));
    localStorage.setItem('d2r_runeStash', JSON.stringify(st));
  }, { owned, runes });
  await reloadPinned(page); await page.waitForTimeout(1800);
}
async function cleanup(page: any) {
  await page.evaluate(() => ['d2r_rwProfile','d2r_rwMade','d2r_owned','d2r_runeStash','d2r_copies'].forEach((k) => localStorage.removeItem(k)));
}

test('breadth truth: Exile is class-locked (auric shields only), Phoenix is broad', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    return { exile: w._rwBreadth('Exile'), phoenix: w._rwBreadth('Phoenix'), exLocked: w._rwClassLocked('Exile'), phLocked: w._rwClassLocked('Phoenix'), prideLocked: w._rwClassLocked('Pride'), insightLocked: w._rwClassLocked('Insight') };
  });
  expect(r.exLocked).toBe(true);
  expect(r.phLocked).toBe(false);
  expect(r.prideLocked).toBe(false);   // polearms are narrow but NOT class-exclusive gear — no queue-jump
  expect(r.insightLocked).toBe(false);
  expect(r.exile).toBeLessThan(r.phoenix);
});

test('runes ready: the one Sacred Rondache goes to EXILE; Phoenix defers with the earmark narration; Mist forges in the OWNED bow', async ({ page }) => {
  await fresh(page, ['Sacred Rondache (4os)', 'Crusader Bow (5os)'], 'full');
  const r = await page.evaluate(() => {
    const w: any = window;
    const sc = w.forgeScan();
    const all: any[] = [].concat(sc.now || [], sc.pipeline || [], sc.onestep || []);
    const get = (n: string) => all.find((t: any) => t.rw === n) || null;
    const exile = get('Exile'), phoenix = get('Phoenix'), mist = get('Mist');
    w.switchTab('forge'); try { w.renderForge(); } catch (e) {}
    const body = (document.getElementById('forge-body') || document.body).innerHTML;
    return {
      exileBase: exile && exile.base && exile.base.base, exileDef: !!(exile && exile.deferred),
      phoenixDef: !!(phoenix && (phoenix.deferred || phoenix.baseOver)), phoenixRsv: phoenix && phoenix.rsvFor,
      mistBase: mist && mist.base && mist.base.base, mistKind: mist && mist.kind,
      earmarkShown: /earmarked for/i.test(body) && /Exile/.test(body),
    };
  });
  await cleanup(page);
  expect(r.exileBase).toBe('Sacred Rondache');
  expect(r.exileDef).toBe(false);
  expect(r.phoenixDef).toBe(true);
  expect(r.phoenixRsv).toBe('Exile');
  expect(r.mistBase).toBe('Crusader Bow');
  expect(r.mistKind).toBe('now');
  expect(r.earmarkShown).toBe(true);
});

test('no runes (his live shape): both words are one-steps, Exile HOLDS the copy, Phoenix wears baseOver + earmark', async ({ page }) => {
  await fresh(page, ['Sacred Rondache (4os)'], 'none');
  const r = await page.evaluate(() => {
    const w: any = window;
    const sc = w.forgeScan();
    const all: any[] = [].concat(sc.now || [], sc.pipeline || [], sc.onestep || []);
    const get = (n: string) => all.find((t: any) => t.rw === n) || null;
    const exile = get('Exile'), phoenix = get('Phoenix');
    return {
      exileOver: !!(exile && exile.baseOver), phoenixOver: !!(phoenix && phoenix.baseOver),
      phoenixRsv: phoenix && phoenix.rsvFor,
    };
  });
  await cleanup(page);
  expect(r.exileOver).toBe(false);
  expect(r.phoenixOver).toBe(true);
  expect(r.phoenixRsv).toBe('Exile');
});

test('spare copies stay generous: TWO rondache copies → Exile takes one, the broad word may use the other', async ({ page }) => {
  await fresh(page, ['Sacred Rondache (4os)'], 'full');
  await pinEvaluate(page, () => { localStorage.setItem('d2r_copies', JSON.stringify({ 'Sacred Rondache (4os)': 2 })); });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    const sc = w.forgeScan();
    const all: any[] = [].concat(sc.now || [], sc.pipeline || [], sc.onestep || []);
    const exile = all.find((t: any) => t.rw === 'Exile');
    const others = all.filter((t: any) => t.rw !== 'Exile' && t.base && /Sacred Rondache/.test(t.base.name || '') && !t.deferred && !t.baseOver);
    return { exileHas: !!(exile && exile.base && !exile.deferred && !exile.baseOver), spareUsed: others.length >= 1 };
  });
  await cleanup(page);
  expect(r.exileHas).toBe(true);
  expect(r.spareUsed).toBe(true);
});
