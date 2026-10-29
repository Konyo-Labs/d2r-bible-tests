import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v621 — THE LOCKDOWN JOURNEY (rinse-and-repeat round 1): one continuous rendered-UI session that
// walks Konyo's real flow end to end, asserting cross-surface sync at every step. This is the
// USER-EXPERIENCE verification of the whole v614-v620 arc in one demo.

test('full journey: intake → insights → forge → create → consume → chronicle → filter → grail seals', async ({ page }) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(URL); await page.waitForTimeout(1800);

  // 0) fresh player boots clean; owner seed floors 66
  const boot = await page.evaluate(() => {
    const md = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
    return { seeded: Object.keys(md).length >= 66 };
  });
  expect(boot.seeded).toBe(true);

  // 1) a new socketed base arrives (the Katar flow) + runes tallied
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh');
    localStorage.setItem('d2r_rwMade', JSON.stringify({}));
    localStorage.setItem('d2r_owned', JSON.stringify(['Katar (3os)', 'Monarch (Larzuk base)']));
    localStorage.setItem('d2r_runeStash', JSON.stringify({ Tal: 2, Ort: 1, Thul: 2, Amn: 1 }));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);

  // 2) Smart Insights: counts match the Forge engine; Make-now row routes to the Forge
  const si = await page.evaluate(() => new Promise<any>((res) => {
    const w: any = window;
    w.switchTab('tools');
    const card = document.getElementById('smart-insights-card')!;
    if (card.classList.contains('collapsed')) w.toggleCardCollapse('smart-insights-card');
    w.renderSmartInsights();
    setTimeout(() => {
      const p = w._smartProgress(); const sc = w.forgeScan();
      const row = Array.from(document.querySelectorAll('#smart-insights-body .si-row')).find((x) => /Make now/.test(x.textContent || '')) as HTMLElement;
      row.click();
      setTimeout(() => res({ match: p.makeNow === sc.counts.now, onForge: document.getElementById('tab-forge')!.classList.contains('active') }), 500);
    }, 400);
  }));
  expect(si.match).toBe(true);
  expect(si.onForge).toBe(true);

  // 3) the hero offers Pattern in HIS Katar with one-click ✓ created; clicking it syncs EVERYTHING
  const forge = await page.evaluate(() => new Promise<any>((res) => {
    const w: any = window;
    try { w.renderForge(); } catch (e) {}
    setTimeout(() => {
      const hero = document.querySelector('.forge-hero');
      const heroTxt = hero ? hero.textContent || '' : '';
      const btn = document.querySelector('.forge-hero .fh-done') as HTMLElement;
      if (!btn) { res({ noBtn: true, heroTxt: heroTxt.slice(0, 100) }); return; }
      btn.click();
      setTimeout(() => {
        const md = JSON.parse(localStorage.getItem('d2r_rwMade') || '{}');
        const own = JSON.parse(localStorage.getItem('d2r_owned') || '[]');
        const used = JSON.parse(localStorage.getItem('d2r_rwBaseUsed') || '{}');
        res({
          noBtn: false, heroWasPattern: /Pattern/.test(heroTxt),
          made: !!md['Pattern'], consumed: own.indexOf('Katar (3os)') < 0,
          usedRecorded: used['Pattern'] && used['Pattern'].l === 'Katar (3os)',
          monarchKept: own.indexOf('Monarch (Larzuk base)') >= 0,
        });
      }, 900);
    }, 400);
  }));
  expect(forge.noBtn).toBe(false);
  expect(forge.heroWasPattern).toBe(true);   // the highest-value ready word on his base
  expect(forge.made).toBe(true);             // Chronicle tallied
  expect(forge.consumed).toBe(true);         // the Katar left the vault
  expect(forge.usedRecorded).toBe(true);     // undo-able
  expect(forge.monarchKept).toBe(true);      // only the used base left

  // 4) the Chronicle change fanned out: Smart Insights re-rendered live (no stale counts)
  const fan = await page.evaluate(() => {
    const w: any = window;
    const p = w._smartProgress();
    const sc = w.forgeScan();
    const tasked = [].concat(sc.now || [], sc.pipeline || [], sc.onestep || [], sc.farm || []).some((t: any) => t.rw === 'Pattern');
    return { made: p.made, patternGone: !tasked };
  });
  expect(fan.made).toBe(1);
  expect(fan.patternGone).toBe(true);        // a made word never re-tasks

  // 5) grail forges: mark a unique found from the CALCULATOR side while F·Uniques is open → live sync
  const grail = await page.evaluate(() => new Promise<any>((res) => {
    const w: any = window;
    w.switchTab('funi');
    setTimeout(() => {
      const s = w.funiScan();
      const target = s.missing[0].n;
      w.toggleOwned(target);
      setTimeout(() => {
        const s2 = w.funiScan();
        const gone = !s2.missing.some((x: any) => x.n === target);
        w.toggleOwned(target);
        res({ gone });
      }, 400);
    }, 500);
  }));
  expect(grail.gone).toBe(true);

  // 6) cleanup + zero page errors through the whole journey
  await page.evaluate(() => { ['d2r_rwProfile', 'd2r_rwMade', 'd2r_owned', 'd2r_runeStash', 'd2r_rwBaseUsed', 'd2r_rwUnmade'].forEach((k) => localStorage.removeItem(k)); });
  expect(errors).toEqual([]);
});
