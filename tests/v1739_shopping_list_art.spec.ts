import { test, expect } from './_net_stub';
import { ensureCardExpanded } from './_cards';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';

// v1739 — HD ART ON THE SHOPPING LIST, AND THE ANCHOR IS THE KEYWORD.
//
// Konyo: "for shopping list i want it more upgraded with HD art / image cursor floating for the
// items its rendering and the keyword items also."
//
// NOTHING NEW WAS BUILT. The board has carried a cursor-following art card since v283 — `arttip`,
// with the v441 nav-orb that mirrors the hovered sprite — and it fires on any `[data-arttip]`.
// The shopping list simply was not wired to it: runes carried an 18px icon and no hover, BASES
// carried no art at all, and the runeword each base is FOR was inert text. All are now anchors.
// A second floating-preview component would have been `copy-drift` with extra steps.
//
// THE ANCHOR IS THE KEYWORD, NEVER THE CELL — and that is v654, not a detail.
// The obvious wiring is `data-arttip` on the `.shop-name` grid cell. It was done that way first
// and fired NOTHING, because v654 refuses any anchor wider than 430px:
//
//     if (_rr.width > 430 || _rr.height > 120) return;
//
// Konyo asked for that rule in those words — "i dont want it opening when i hit the SECTION
// itself, only over the specific item keyword; it feels random" — and measured here, the cells are
// 480px on a rune row and 600px on a base row. The rule was working. His request this time says
// the same thing again ("the keyword items also"), so the attribute now sits on the `<b>` name and
// the thumbnail: 25px and 18px, comfortably inside the rule that rejected the first attempt.
//
// THREE HARNESS FAULTS ON THE WAY, none of which looked like one:
//   * every anchor measured 0x0 — the card lives on TAB-TOOLS and ships COLLAPSED, so nothing has
//     a box until the tab is switched AND the card opened;
//   * `imgsLoaded: 0` — `loading="lazy"`, and the card was off-screen. Forced eager: 124/124 load,
//     0 broken;
//   * hand-computed hover coordinates landed under the fixed dock (`elementFromPoint` returned
//     `DIV.dock-inner`), so the cursor never reached the anchor. Playwright's `hover()` resolves
//     actionability properly and all six anchor types then opened the card.
// [[feedback-suspect-the-instrument]]

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

async function openShoppingList(page: any) {
  await page.goto(URL);
  await page.waitForTimeout(1200);
  await pinEvaluate(page, () => {
    const w: any = window;
    w.LSR.setItem('d2r_rwProfile', 'fresh');
    w.LSR.setItem('d2r_rwMade', '{}');
    w.LSR.setItem('d2r_rwUnmade', '{}');
    w.LSR.setItem('d2r_runeStash', JSON.stringify({ El: 2, Eld: 2 }));
  });
  await reloadPinned(page);
  await page.waitForTimeout(1800);
  // the card is on tab-tools and ships collapsed — off-tab or collapsed, every rect is 0x0.
  // v1751: opened through the shared helper, because the blind toggle this replaced CLOSED the
  // card on any run where it was already open.
  await ensureCardExpanded(page, 'shopping-list-card');
  await page.evaluate(() => {
    const w: any = window;
    w.renderShoppingList && w.renderShoppingList();
    document.querySelectorAll('.shop-wrap img').forEach((i: any) => (i.loading = 'eager'));
  });
  await p800(page);
}
const p800 = (page: any) => page.waitForTimeout(900);

test.describe('v1739 — the shopping list carries its art', () => {
  test('★★★ every hover anchor is keyword-sized, so v654 cannot reject it', async ({ page }) => {
    await openShoppingList(page);
    const r = await page.evaluate(() => {
      const anchors = [...document.querySelectorAll('.shop-wrap [data-arttip]')];
      const tooBig = anchors
        .map((el) => ({ el, r: el.getBoundingClientRect() }))
        .filter((x) => x.r.width > 430 || x.r.height > 120)
        .map((x) => `${(x.el as any).tagName}.${(x.el as any).className} ${Math.round(x.r.width)}x${Math.round(x.r.height)}`);
      return { total: anchors.length, tooBig };
    });
    // non-vacuity: the list must actually have rendered anchors to judge
    expect(r.total, 'the shopping list rendered no hover anchors at all').toBeGreaterThan(20);
    expect(r.tooBig, 'anchors v654 will silently refuse (>430x120): ' + r.tooBig.join(' | ')).toEqual([]);
  });

  test('★★★ hovering a rune, a base and a runeword each opens the card with its own art',
    async ({ page }) => {
    await openShoppingList(page);
    const CASES: [string, string][] = [
      ['rune keyword', '.shop-row .shop-name b[data-arttip]'],
      ['rune thumbnail', '.shop-row .shop-name img[data-arttip]'],
      ['base keyword', '.shop-bases .shop-name b[data-arttip]'],
      ['base thumbnail', '.shop-bases .shop-name img[data-arttip]'],
      ['the runeword it is for', '.shop-rw[data-arttip]'],
      ['an alternate base', '.shop-alt[data-arttip]'],
    ];
    const failures: string[] = [];
    for (const [label, sel] of CASES) {
      await page.mouse.move(700, 5);
      await page.waitForTimeout(220);
      const loc = page.locator(sel).first();
      const name = await loc.getAttribute('data-arttip').catch(() => null);
      if (!name) { failures.push(`${label}: no anchor found`); continue; }
      // hand-computed coordinates land under the fixed dock; hover() resolves actionability
      try { await loc.hover({ timeout: 4000 }); } catch (e: any) { failures.push(`${label}: hover failed`); continue; }
      /* v1787 — POLL, DO NOT SNAPSHOT AT A FIXED DELAY. v1717 diagnosed this exact race in
         v1625 and fixed it THERE only: the card is raised by a delegated hover handler and
         `.on` is a transition class, so a single read at a fixed delay passes in one run and
         fails in the next. It cost two consecutive red Routine I runs on shard 3/6, on commits
         that changed no page code at all. Same defect, same remedy, applied to the class. The
         assertion below stays exactly as strict: if the card never comes up, this still goes red. */
      await page.waitForFunction(() => {
            const t = document.getElementById('arttip');
            return !!t && t.classList.contains('on');
          }, null, { timeout: 4000 }).catch(() => {});
      const t = await page.evaluate(() => {
        const tip = document.getElementById('arttip');
        if (!tip) return { on: false, art: null as string | null, label: '' };
        const img = tip.querySelector('img') as HTMLImageElement | null;
        return {
          on: tip.classList.contains('on'),
          art: img && img.style.display !== 'none' && img.naturalWidth > 0 ? img.getAttribute('src') : null,
          label: (tip.textContent || '').replace(/\s+/g, ' ').slice(0, 40),
        };
      });
      if (!t.on) failures.push(`${label} (${name}): card never opened`);
      else if (!t.art) failures.push(`${label} (${name}): card opened with NO art`);
      else if (!t.label.toLowerCase().includes(String(name).toLowerCase().slice(0, 6)))
        failures.push(`${label} (${name}): card opened showing "${t.label}" instead`);
    }
    expect(failures, 'shopping-list hover: ' + failures.join(' | ')).toEqual([]);
  });

  test('★★ every icon the list renders actually loads', async ({ page }) => {
    await openShoppingList(page);
    await page.waitForTimeout(1600);
    const r = await page.evaluate(() => {
      const imgs = [...document.querySelectorAll('.shop-wrap img')] as HTMLImageElement[];
      return {
        total: imgs.length,
        loaded: imgs.filter((i) => i.naturalWidth > 0).length,
        broken: imgs.filter((i) => i.complete && i.naturalWidth === 0)
          .map((i) => i.getAttribute('src') || '').slice(0, 6),
      };
    });
    // non-vacuity — and this is the check that would catch an empty box with a border
    expect(r.total, 'the list rendered no icons at all').toBeGreaterThan(20);
    expect(r.broken, 'icons that resolve to nothing: ' + r.broken.join(', ')).toEqual([]);
    expect(r.loaded, 'some icons never loaded').toBe(r.total);
  });

  test('★★ bases carry art — the row type that had none before', async ({ page }) => {
    await openShoppingList(page);
    const r = await page.evaluate(() => ({
      baseRows: document.querySelectorAll('.shop-bases').length,
      withArt: document.querySelectorAll('.shop-bases .shop-name img').length,
      withKeyword: document.querySelectorAll('.shop-bases .shop-name b[data-arttip]').length,
      runewordLinks: document.querySelectorAll('.shop-bases .shop-rw[data-arttip]').length,
    }));
    expect(r.baseRows, 'no base rows rendered').toBeGreaterThan(5);
    expect(r.withKeyword, 'base names are not hover anchors').toBe(r.baseRows);
    expect(r.runewordLinks, 'the runeword each base is FOR is not an anchor').toBe(r.baseRows);
    // art is best-effort per base (not every base has a sprite), but it must not be zero
    expect(r.withArt, 'not one base row rendered art').toBeGreaterThan(0);
  });
});
