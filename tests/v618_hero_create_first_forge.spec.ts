import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v618 — (a) the hero MAKE-NOW card carries the same one-click '✓ created' as the list cards
// (identical rwToggleMade sync: Chronicle tally + vault consume); (b) the FIRST runeword ever
// forged fires its own extra-colorful onboarding epic, once, on 0→1.

test('hero ✓ created ticks the word through the full sync path', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_owned', JSON.stringify(['Katar (3os)']));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Tal: 1, Ort: 1, Thul: 1 }));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => new Promise<any>((res) => {
    const w: any = window;
    w.switchTab('forge'); try { w.renderForge(); } catch (e) {}
    setTimeout(() => {
      const btn = document.querySelector('.forge-hero .fh-done') as HTMLElement;
      if (!btn) { res({ noBtn: true, heroTxt: (document.querySelector('.forge-hero')?.textContent || '').slice(0, 120) }); return; }
      btn.click();
      setTimeout(() => {
        const md = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
        const own = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
        ['d2r_rwProfile', 'd2r_rwMade', 'd2r_owned', 'd2r_runeStash', 'd2r_rwBaseUsed', 'd2r_rwUnmade'].forEach((k) => localStorage.removeItem(k));
        res({ noBtn: false, made: !!md['Pattern'], consumed: own.indexOf('Katar (3os)') < 0 });
      }, 900);
    }, 400);
  }));
  expect(r.noBtn).toBe(false);          // the hero for a make-now task carries ✓ created
  expect(r.made).toBe(true);            // Chronicle tallied
  expect(r.consumed).toBe(true);        // vault consumed — the identical sync path
});

test('FIRST forge fires the extra-colorful onboarding epic exactly once', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, 'webdriver', { get: () => false }));
  // v1518 — CLAIM THE WORLD BACK. v1499 made an unclaimed browser a GUEST, and it identifies the
  // suite by navigator.webdriver + file://. This spec spoofs webdriver to unmask the motion effects,
  // which also unmasks it as a guest — so every bare key it seeds lands in a world the app does not
  // read, and the app sees an empty chronicle. The claim says "this browser is the owner", which is
  // what it actually is: the suite testing Konyo's own world.
  await page.addInitScript(() => localStorage.setItem('d2r_ownerClaim', '*'));
  await page.goto(URL); await page.waitForTimeout(1800);
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => new Promise<any>((res) => {
    const w: any = window;
    w.switchTab('forge'); try { w.renderForge(); } catch (e) {}
    const all = Object.keys(w.RUNEWORD_TIP || {});
    w.rwToggleMade(all[0]);   // 0 → 1: THE first forge
    const first = document.querySelector('.forge-epic-first');
    const firstTxt = first ? (first.textContent || '') : '';
    setTimeout(() => {
      document.querySelectorAll('.forge-epic').forEach((e) => e.remove());
      w.rwToggleMade(all[1]);   // 1 → 2: NOT the first — no first-forge epic
      const again = !!document.querySelector('.forge-epic-first');
      ['d2r_rwProfile', 'd2r_rwMade', 'd2r_rwUnmade'].forEach((k) => localStorage.removeItem(k));
      res({ fired: !!first, text: firstTxt.slice(0, 60), again });
    }, 400);
  }));
  expect(r.fired).toBe(true);
  expect(r.text).toContain('FIRST RUNEWORD');
  expect(r.again).toBe(false);
});
