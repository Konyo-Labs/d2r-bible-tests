import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v629 — CHRONICLE ⇄ VAULT ⇄ FORGE host awareness (Konyo's Stiletto/Ritual: 'back-engineer it,
// flag it in the Chronicle, genius smart synchronization'). One host map, both directions.

test("Stiletto case: bare read → Chronicle flags 'possible host — set its sockets' AND the Forge task says 'you may already own a host'", async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_unknownReads', JSON.stringify(['Stiletto']));   // the AI's name-only read
    // Ritual's runes in hand → the word becomes a get-a-base one-step (not farm)
    const st: any = {};
    ['El','Eld','Tir','Nef','Eth','Ith','Tal','Ral','Ort','Thul','Amn','Sol','Shael','Dol','Hel','Io','Lum','Ko','Fal','Lem','Pul','Um','Mal','Ist','Gul','Vex','Ohm','Lo','Sur','Ber','Jah','Cham','Zod'].forEach((n) => (st[n] = 4));
    localStorage.setItem('d2r_runeStash', JSON.stringify(st));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    // find a word Stiletto can host (Ritual-class) that is unmade
    const hostable = (w._baseRunewords('Stiletto') || []).map((x: any) => x.n);
    const hm = w._vaultHostMap();
    // Chronicle side
    w.switchTab('runes');   // wherever the chronicle lives, render it directly:
    try { w.renderRunewordChronicle(); } catch (e) {}
    try { w.rwcSetFilter && w.rwcSetFilter('all'); } catch (e) {}
    const chron = (document.getElementById('rwc-list') || {}).innerHTML || '';
    // Forge side
    w.switchTab('forge'); try { w.renderForge(); } catch (e) {}
    const forge = (document.getElementById('forge-body') || document.body).innerHTML;
    ['d2r_rwProfile', 'd2r_rwMade', 'd2r_unknownReads', 'd2r_runeStash'].forEach((k) => localStorage.removeItem(k));
    return {
      hostable: hostable.slice(0, 6),
      mapHasStiletto: Object.keys(hm.maybe).some((wd: string) => (hm.maybe[wd] || []).includes('Stiletto')),
      chronFlags: /possible host: Stiletto/.test(chron),
      forgeFlags: /you may already own a host/.test(forge) && /Stiletto/.test(forge),
    };
  });
  expect(r.hostable.length).toBeGreaterThan(0);
  expect(r.mapHasStiletto).toBe(true);
  expect(r.chronFlags).toBe(true);
  expect(r.forgeFlags).toBe(true);
});

test('exact-fit owned host: the Chronicle row wears the green host-in-vault badge; made rows never badge', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({ Zephyr: 'x' }));
    localStorage.setItem('d2r_owned', JSON.stringify(['Katar (3os)']));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    try { w.renderRunewordChronicle(); w.rwcSetFilter && w.rwcSetFilter('all'); } catch (e) {}
    const html = (document.getElementById('rwc-list') || {}).innerHTML || '';
    ['d2r_rwProfile', 'd2r_rwMade', 'd2r_owned'].forEach((k) => localStorage.removeItem(k));
    const rows = html.split('rwc-row');
    const patternRow = rows.find((x: string) => /data-arttip="Pattern"|>Pattern</.test(x)) || '';
    const zephyrRow = rows.find((x: string) => /data-arttip="Zephyr"|>Zephyr</.test(x)) || '';
    return { patternHosted: /host in vault: Katar \(3os\)/.test(patternRow), madeClean: !/host in vault/.test(zephyrRow) };
  });
  expect(r.patternHosted).toBe(true);
  expect(r.madeClean).toBe(true);
});
