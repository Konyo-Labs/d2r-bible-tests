import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v660 — "✓ got the base" ascension (Konyo: 'lets say i did get a runeword base… clicking i have the
// base with a checkmark style and then it automatically ascends to MAKE NOW'). A one-step get-a-base
// card carries a ✓ button that registers the recommended base at the word's exact socket count
// (owned + EXTRA_ITEMS socketed entry — the same registry the AI intake writes) and the word jumps
// straight to ⚒ Make now in the same forge view.

test('one-step base card shows ✓ got the base; clicking registers the base and the word ascends to Make now', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('d2r_rwProfile', 'fresh');           // clean chronicle — the word must be unmade
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_owned', JSON.stringify([]));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Ort: 1, Sol: 1 }));   // Lore = Ort+Sol, 2os helm
    localStorage.setItem('d2r_ladderMode', 'nonladder');
  });
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    const s0 = w.forgeScan();
    const t = (s0.onestep || []).find((x: any) => x.rw === 'Lore' && x.sub === 'base');
    if (!t) return { taskFound: false };
    // the card renders the button
    w.switchTab('forge'); try { w.renderForge && w.renderForge(); } catch (e) {}
    const btn = Array.from(document.querySelectorAll('#tab-forge .f-btn'))
      .find((b) => (b.textContent || '').includes('got the base'));
    const base = String(t.bestStr || '').split(/\s*\/\s*/)[0].trim();
    const need = ((w.RUNEWORD_TIP || {})['Lore'] || {}).rec.length;
    w.forgeGotBase(null, 'Lore', base, need);
    const s1 = w.forgeScan();
    const now = (s1.now || []).find((x: any) => x.rw === 'Lore' && !x.deferred);
    return {
      taskFound: true, btnRendered: !!btn, base, need,
      ascended: !!now, nowBase: now && now.base && now.base.name,
      ownedHasLabel: JSON.parse(w.LSR.getItem('d2r_owned') || '[]').includes(base + ' (' + need + 'os)'),
    };
  });
  expect(r.taskFound).toBe(true);
  expect(r.btnRendered).toBe(true);
  expect(r.ascended).toBe(true);                       // 🟡 one step → ⚒ Make now, one click
  expect(r.ownedHasLabel).toBe(true);                  // registered exactly like an intake read
  expect(r.nowBase).toBe(r.base + ' (' + r.need + 'os)');
});

test('REG-016 — grimoire/voodoo-head offhands register and ascend too (they had NO slot mapping)', async ({ page }) => {
  await page.addInitScript(() => { localStorage.setItem('d2r_rwProfile', 'fresh'); });
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    const w: any = window;
    const made: any = {}; Object.keys(w.RUNEWORD_TIP).forEach((n: string) => { if (n !== 'Vigilance') made[n] = 'x'; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ El: 9, Eld: 9, Tir: 9, Nef: 9, Eth: 9, Ith: 9, Tal: 9, Ral: 9, Ort: 9, Thul: 9, Amn: 9, Sol: 9, Shael: 9, Dol: 9, Hel: 9, Io: 9, Lum: 9, Ko: 9, Fal: 9, Lem: 9, Pul: 9, Um: 9, Mal: 9, Ist: 9, Gul: 9, Vex: 9, Ohm: 9, Lo: 9, Sur: 9, Ber: 9, Jah: 9, Cham: 9, Zod: 9 }));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    w._ensureSocketBaseEntry('Blasphemous Grimoire (2os)');
    w._ensureSocketBaseEntry('Bloodlord Skull (2os)');
    const grim = !!(w.EXTRA_ITEMS && w.EXTRA_ITEMS['Blasphemous Grimoire (2os)']);
    const head = !!(w.EXTRA_ITEMS && w.EXTRA_ITEMS['Bloodlord Skull (2os)']);
    const t = (w.forgeScan().onestep || []).find((x: any) => x.rw === 'Vigilance' && x.sub === 'base');
    const osBase = t ? String(t.bestStr || '').split(/\s*\/\s*/)[0].trim() : '';
    if (t) w.forgeGotBase(null, 'Vigilance', osBase, 2);
    const now = (w.forgeScan().now || []).find((x: any) => x.rw === 'Vigilance' && !x.deferred);
    return { grim, head, task: !!t, ascended: !!now };
  });
  expect(r.grim).toBe(true);        // the grimoire class registers (was silently refused — no slot)
  expect(r.head).toBe(true);        // voodoo heads too
  expect(r.task).toBe(true);
  expect(r.ascended).toBe(true);    // ✓ got the base → ⚒ Make now, the v660 contract, offhands included
});
