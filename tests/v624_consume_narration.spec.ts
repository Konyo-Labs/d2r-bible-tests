import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v624 — CONSUME NARRATION (Konyo: 'how can it propose Phoenix in the 4os Phase Blade I just used
// for Kingslayer?'). The consume HAD fired on one copy of his ×2 stack — the card just never said
// so. A task whose base label has consumed siblings now narrates them.

test('a task on a label with a consumed twin says so on the card', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({ Kingslayer: 'Jul 9' }));
    localStorage.setItem('d2r_owned', JSON.stringify(['Phase Blade (4os)']));
    localStorage.setItem('d2r_rwBaseUsed', JSON.stringify({ Kingslayer: { l: 'Phase Blade (4os)', copy: true } }));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Vex: 2, Lo: 1, Jah: 1 }));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    w.switchTab('forge'); try { w.renderForge(); } catch (e) {}
    const dom = (document.getElementById('forge-body') || document.body).innerHTML;
    ['d2r_rwProfile', 'd2r_rwMade', 'd2r_owned', 'd2r_rwBaseUsed', 'd2r_runeStash'].forEach((k) => localStorage.removeItem(k));
    return { narrated: /already became <b>Kingslayer<\/b>/.test(dom), remaining: /REMAINING/.test(dom) };
  });
  expect(r.narrated).toBe(true);
  expect(r.remaining).toBe(true);
});

// v625 — chain continuity: after a sibling word consumes the shared base, the chain's Larzuk step
// NAMES the consumed word (no more 'it just disappeared'); farm rows name the gamble path for
// sub-max words (the idle-time doctrine).
test('chain Larzuk step narrates the consumed sibling; farm rows name the gamble path', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    // BotD consumed one Larzuk Phase Blade; Silence still pipelines on the remaining copy
    localStorage.setItem('d2r_rwMade', JSON.stringify({ 'Breath of the Dying': 'Jul 9' }));
    localStorage.setItem('d2r_owned', JSON.stringify(['Phase Blade (Larzuk base)']));
    localStorage.setItem('d2r_rwBaseUsed', JSON.stringify({ 'Breath of the Dying': { l: 'Phase Blade (Larzuk base)', copy: true } }));
    // every rune ×4 — recipe-independent (window.RUNES isn't exposed; use the canonical 33 names)
    const st: any = {};
    ['El','Eld','Tir','Nef','Eth','Ith','Tal','Ral','Ort','Thul','Amn','Sol','Shael','Dol','Hel','Io','Lum','Ko','Fal','Lem','Pul','Um','Mal','Ist','Gul','Vex','Ohm','Lo','Sur','Ber','Jah','Cham','Zod'].forEach((n) => (st[n] = 4));
    localStorage.setItem('d2r_runeStash', JSON.stringify(st));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    w.switchTab('forge'); try { w.renderForge(); } catch (e) {}
    const dom = (document.getElementById('forge-body') || document.body).innerHTML;
    ['d2r_rwProfile', 'd2r_rwMade', 'd2r_owned', 'd2r_rwBaseUsed', 'd2r_runeStash'].forEach((k) => localStorage.removeItem(k));
    return {
      chainNarrates: /already became <b>Breath of the Dying<\/b>/.test(dom),
      gambleNamed: /gamble a plain white for \d+os/.test(dom) || !/Furthest out/.test(dom),   // farm rows may be empty in this state
    };
  });
  expect(r.chainNarrates).toBe(true);
  expect(r.gambleNamed).toBe(true);
});

// v626 — CONSUME FIDELITY: the ✓-created click consumes the base its card DISPLAYED (a click is a
// physical fact), never a re-scanned re-ranked pick; Larzuk steps name their words.
test('the clicked card base is what gets consumed, even if the planner would re-rank', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    // two hosts for one word class: consume must eat the HINTED one regardless of ranking
    localStorage.setItem('d2r_owned', JSON.stringify(['Katar (3os)', 'Suwayyah (3os)']));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Tal: 2, Ort: 2, Thul: 2 }));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    // simulate clicking the card that displayed the KATAR (whatever the planner now prefers)
    w.rwToggleMade('Pattern', 'Katar (3os)');
    const own = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
    const used = JSON.parse(localStorage.getItem('d2r_rwBaseUsed') || '{}');
    ['d2r_rwProfile', 'd2r_rwMade', 'd2r_owned', 'd2r_runeStash', 'd2r_rwBaseUsed', 'd2r_rwUnmade'].forEach((k) => localStorage.removeItem(k));
    return { katarGone: own.indexOf('Katar (3os)') < 0, suwayyahKept: own.indexOf('Suwayyah (3os)') >= 0, used: used['Pattern'] && used['Pattern'].l };
  });
  expect(r.katarGone).toBe(true);       // the card the user clicked
  expect(r.suwayyahKept).toBe(true);    // never the re-ranked alternative
  expect(r.used).toBe('Katar (3os)');
});

test('Larzuk step 1 names the words it serves (no ghost chains)', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_owned', JSON.stringify(['Phase Blade (Larzuk base)']));
    const st: any = {};
    ['El','Eld','Tir','Nef','Eth','Ith','Tal','Ral','Ort','Thul','Amn','Sol','Shael','Dol','Hel','Io','Lum','Ko','Fal','Lem','Pul','Um','Mal','Ist','Gul','Vex','Ohm','Lo','Sur','Ber','Jah','Cham','Zod'].forEach((n) => (st[n] = 4));
    localStorage.setItem('d2r_runeStash', JSON.stringify(st));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    w.switchTab('forge'); try { w.renderForge(); } catch (e) {}
    const dom = (document.getElementById('forge-body') || document.body).textContent || '';
    ['d2r_rwProfile', 'd2r_rwMade', 'd2r_owned', 'd2r_runeStash'].forEach((k) => localStorage.removeItem(k));
    const m = dom.match(/Larzuk-socket your\s*Phase Blade[^—]*—\s*for\s+(.{0,60})/);
    return { named: !!m, ctx: m ? m[1] : dom.slice(dom.indexOf('Larzuk-socket'), dom.indexOf('Larzuk-socket') + 120) };
  });
  expect(r.named).toBe(true);           // "…→ 6os — for <word>, <word>" — never an anonymous Larzuk quest
});
