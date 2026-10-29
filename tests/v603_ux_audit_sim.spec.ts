import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

test('v603.1 UX audit sim: Konyo screenshot state — rendered Throw-Out + Socketed Review, honest everywhere', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.goto(URL); await page.waitForTimeout(1500);
  // seed Konyo's screenshot state: throw-out reads + registered socketed bases (Chronicle = live seed 57)
  await pinEvaluate(page, () => {
    localStorage.setItem('d2r_rwProfile', 'fresh'); localStorage.setItem('d2r_rwMade', JSON.stringify({}));   // v621.1 — 66-seed floors claw words; the sim premises them unmade
    localStorage.setItem('d2r_unknownReads', JSON.stringify([
      'Suwayyah (1os low base)', 'Grim Scythe (4os low base)', 'Small Crescent (3os low base)',
    ]));
    localStorage.setItem('d2r_owned', JSON.stringify([
      'Bone Visage (3os)', 'Monarch (4os)', 'Suwayyah (3os)',
    ]));
  });
  await reloadPinned(page); await page.waitForTimeout(1800);
  await page.evaluate(() => {
    const w: any = window;
    ['Bone Visage (3os)', 'Monarch (4os)', 'Suwayyah (3os)'].forEach((n) => w._ensureSocketBaseEntry && w._ensureSocketBaseEntry(n, true));
    w.switchTab && w.switchTab('tools');
    w.renderVault && w.renderVault();
  });
  await page.waitForTimeout(1200);
  const audit = await page.evaluate(() => {
    const w: any = window;
    const to = document.getElementById('vault-throwout');
    const so = document.getElementById('vault-socketed');
    const cardText = (root: Element | null, name: string) => {
      if (!root) return '';
      const cards = Array.from(root.querySelectorAll('.to-card'));
      const c = cards.find((x) => (x.textContent || '').includes(name));
      return c ? (c.textContent || '') : '';
    };
    return {
      toCount: to ? to.querySelectorAll('.to-card').length : 0,
      soCount: so ? so.querySelectorAll('.to-card').length : 0,
      suw1: cardText(to, 'Suwayyah'),
      grim4: cardText(to, 'Grim Scythe') || cardText(so, 'Grim Scythe'),   // v631 — promoted to Socketed Review
      cres3: cardText(to, 'Small Crescent') || cardText(so, 'Small Crescent'),
      suw3so: cardText(so, 'Suwayyah'),
      bone3so: cardText(so, 'Bone Visage'),
      // helper truth for cross-checking the rendered text
      suwWrong: (w._baseUnmadeWrongSock('Suwayyah', 1) || []).map((r: any) => r.n + ':' + r.s),
      suw3un: (w._baseUnmadeRunewords('Suwayyah', 3) || []).map((r: any) => r.n),
      grimWrong: (w._baseUnmadeWrongSock('Grim Scythe', 4) || []).map((r: any) => r.n + ':' + r.s),
    };
  });
  console.log('AUDIT', JSON.stringify(audit, null, 1).slice(0, 3000));
  console.log('ERRORS', JSON.stringify(errors));
  expect(errors).toEqual([]);
  // v631 — capability PROMOTION now lifts '(Nos)' reads that exact-fit unmade words out of the
  // throw-out ledger at boot (Grim Scythe 4os + Small Crescent 3os here); only the 1os Suwayyah
  // (no 1os word exists) stays behind. The review split is the NEW honest state this sim locks.
  expect(audit.toCount).toBeGreaterThanOrEqual(1);
  expect(audit.soCount).toBeGreaterThanOrEqual(5);   // 3 registered + 2 promoted
  // 1os Suwayyah card: names the unmade wrong-sock word, no "✓ forged" lie, no Larzuk/cube socket guide
  if (audit.suwWrong.length) {
    expect(audit.suw1).toContain('STILL UNMADE');
    expect(audit.suw1).toContain('hunt');
    expect(audit.suw1).not.toContain('guaranteed max');
  }
  expect(audit.suw1).not.toContain('its runewords are ✓ forged');
  // 3os Suwayyah in Socketed Review: Pattern unmade at 3os → still-needed card, never "free to throw"
  if (audit.suw3un.length) expect(audit.suw3so).not.toContain('Free to throw out');
  // no already-socketed card anywhere offers the cube socket recipe
  expect(audit.grim4).not.toContain('guaranteed max');
  expect(audit.cres3).not.toContain('guaranteed max');
});

