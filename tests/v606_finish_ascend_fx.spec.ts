import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v606/v607 — finish & ascend choreography (Konyo: "cool animated effects for endgame finishes…
// ascending from task to task… polish the site visually"). Structural UX locks, not pixel tests:
// forging a word pops the toast, milestone counts (every 10th) raise the golden epic overlay with
// falling runes, the next make-now cards get the f-ascend stagger, tab switches glide in, and ALL
// of it stays silent under prefers-reduced-motion (the _motionOK gate).

test('milestone forge → toast + epic overlay + ascend stagger; overlay self-removes', async ({ page }) => {
  // _motionOK() is silent under automation (navigator.webdriver) — unmask it so the fx are observable
  await page.addInitScript(() => Object.defineProperty(navigator, 'webdriver', { get: () => false }));
  // v1518 — CLAIM THE WORLD BACK. v1499 made an unclaimed browser a GUEST, and it identifies the
  // suite by navigator.webdriver + file://. This spec spoofs webdriver to unmask the motion effects,
  // which also unmasks it as a guest — so every bare key it seeds lands in a world the app does not
  // read, and the app sees an empty chronicle. The claim says "this browser is the owner", which is
  // what it actually is: the suite testing Konyo's own world.
  await page.addInitScript(() => localStorage.setItem('d2r_ownerClaim', '*'));
  await page.goto(URL); await page.waitForTimeout(1800);
  // seed the Chronicle to 59 made (next forge = 60 → a %10 milestone) — pick unmade words dynamically
  await pinEvaluate(page, () => {
    const w: any = window;
    localStorage.setItem('d2r_rwProfile', 'fresh');   // v663 — the 88-seed floor pushed the next %10 milestone to 100, unreachable in the 99 catalog
    const all = Object.keys(w.RUNEWORD_TIP || {});
    const made: any = {}; all.slice(0, 59).forEach((n) => (made[n] = 'x'));
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
    // an owned exact-fit base so the make-now section has cards to ascend
    w._ensureSocketBaseEntry && w._ensureSocketBaseEntry('Katar (3os)', true);
    const own = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
    if (own.indexOf('Katar (3os)') < 0) own.push('Katar (3os)');
    localStorage.setItem('d2r_owned', JSON.stringify(own));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  const r = await page.evaluate(() => {
    const w: any = window;
    w.switchTab && w.switchTab('forge');
    try { w.renderForge && w.renderForge(); } catch (e) {}
    const all = Object.keys(w.RUNEWORD_TIP || {});
    // the load-time seed force re-adds Konyo's seeded words, so the count is NOT 59 — walk it to one
    // below the next multiple of 10, then the final toggle lands exactly on the milestone
    let made = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
    let n = Object.keys(made).length;
    const goal = (Math.floor(n / 10) + 1) * 10;
    while (n < goal - 1) { const t = all.find((x) => !made[x]); if (!t) break; w.rwToggleMade(t); made = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}'); n = Object.keys(made).length; }
    document.querySelectorAll('.forge-epic,.forge-toast').forEach((e) => e.remove());
    const target = all.find((x) => !made[x]);
    w.rwToggleMade(target);   // → exactly the multiple-of-10 milestone
    const epic = document.querySelector('.forge-epic');
    const toast = document.querySelector('.forge-toast');
    const runes = epic ? epic.querySelectorAll('.fe-rune').length : 0;
    const ascended = document.querySelectorAll('#forge-body .forge-sec-now .f-card.f-ascend').length;
    const nowCards = document.querySelectorAll('#forge-body .forge-sec-now .f-card').length;
    return { epic: !!epic, epicText: epic ? (epic.textContent || '').slice(0, 30) : '', runes, toast: !!toast, ascended, nowCards };
  });
  expect(r.epic).toBe(true);                       // the golden moment fires on the 60th forge
  expect(r.epicText).toContain('FORGED');
  expect(r.runes).toBeGreaterThanOrEqual(10);      // falling rune glyphs
  expect(r.toast).toBe(true);                      // the ✨ Forged! toast rides along
  if (r.nowCards > 0) expect(r.ascended).toBeGreaterThanOrEqual(1);   // the next task rises to meet you
  await page.waitForTimeout(2600);
  const gone = await page.evaluate(() => !document.querySelector('.forge-epic'));
  expect(gone).toBe(true);                         // overlay cleans itself up — no DOM litter
});

test('non-milestone forge → toast but NO epic; reduced motion → neither', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(navigator, 'webdriver', { get: () => false }));
  // v1518 — CLAIM THE WORLD BACK. v1499 made an unclaimed browser a GUEST, and it identifies the
  // suite by navigator.webdriver + file://. This spec spoofs webdriver to unmask the motion effects,
  // which also unmasks it as a guest — so every bare key it seeds lands in a world the app does not
  // read, and the app sees an empty chronicle. The claim says "this browser is the owner", which is
  // what it actually is: the suite testing Konyo's own world.
  await page.addInitScript(() => localStorage.setItem('d2r_ownerClaim', '*'));
  // v693.2 recalibration — at the 99/99 seal there is no unmade word to forge; pin fresh. (Also fixed
  // the spec's own const-reassign that only fired when n1+1 hit a %10 milestone — dormant until 99.)
  await page.addInitScript(() => { localStorage.setItem('d2r_rwProfile', 'fresh'); /* v693.3 — profile pin ONLY: addInitScript re-runs on reload and a rwMade={} here stomped this spec's own mid-test writes (the v578.1 trap); fresh flag alone makes boot init rwMade={} */ });
  await page.goto(URL); await page.waitForTimeout(1800);
  const r1 = await page.evaluate(async () => {
    const w: any = window;
    // NOTE: do NOT reset localStorage here — the in-memory Chronicle keeps the seed, and a mismatched
    // target would UN-make a word (count drops → no toast). The live seed state is the test state.
    w.switchTab && w.switchTab('forge');
    try { w.renderForge && w.renderForge(); } catch (e) {}
    const all = Object.keys(w.RUNEWORD_TIP || {});
    let made = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
    let n1 = Object.keys(made).length;
    // v696 — a FRESH chronicle's FIRST forge fires the v618 first-forge epic BY DESIGN (CI caught it;
    // fast local runs read the DOM before it mounted). Burn word #1 quietly and let its fx clear, so
    // the tested forge is #2 — a plain non-milestone toast.
    if (n1 === 0) {
      w.rwToggleMade(all[0]);
      await new Promise((res) => setTimeout(res, 3000));
      document.querySelectorAll('.forge-epic,.forge-toast').forEach((el) => el.remove());
      made = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
      n1 = Object.keys(made).length;
    }
    if ((n1 + 1) % 10 === 0) { const t0 = all.find((x) => !made[x]); w.rwToggleMade(t0); made = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}'); n1 = Object.keys(made).length; document.querySelectorAll('.forge-epic,.forge-toast').forEach((e) => e.remove()); }
    const target = all.find((x) => !made[x]);
    w.rwToggleMade(target);
    const wouldBeMilestone = (n1 + 1) % 10 === 0;
    return { epic: !!document.querySelector('.forge-epic'), toast: !!document.querySelector('.forge-toast'), wouldBeMilestone };
  });
  if (!r1.wouldBeMilestone) expect(r1.epic).toBe(false);   // epic is milestone-only
  expect(r1.toast).toBe(true);
  // reduced motion: the whole celebration block is gated off
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.reload(); await page.waitForTimeout(1800);
  const r2 = await page.evaluate(() => {
    const w: any = window;
    w.switchTab && w.switchTab('forge');
    try { w.renderForge && w.renderForge(); } catch (e) {}
    const all = Object.keys(w.RUNEWORD_TIP || {});
    const made = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
    const target = all.find((n) => !made[n]);
    w.rwToggleMade(target);
    const out = { epic: !!document.querySelector('.forge-epic'), toast: !!document.querySelector('.forge-toast') };
    localStorage.removeItem('d2r_rwMade'); localStorage.removeItem('d2r_owned');
    return out;
  });
  expect(r2.epic).toBe(false);
  expect(r2.toast).toBe(false);
});

test('tab switch glides in (tab-in class pulses on the activated tab)', async ({ page }) => {
  await page.goto(URL); await page.waitForTimeout(1500);
  const r = await page.evaluate(() => {
    const w: any = window;
    w.switchTab('tools');
    const during = document.getElementById('tab-tools')!.classList.contains('tab-in');
    return { during };
  });
  expect(r.during).toBe(true);
  await page.waitForTimeout(600);
  const after = await page.evaluate(() => document.getElementById('tab-tools')!.classList.contains('tab-in'));
  expect(after).toBe(false);   // self-removes so the next entry replays
});
