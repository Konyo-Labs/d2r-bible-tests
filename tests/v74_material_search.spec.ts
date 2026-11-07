import { test, expect } from '@playwright/test';
import * as path from 'path';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v74 — every SPECIAL_DROPS material (sunders, essences, worldstone shards, colossal
// statues/jewels, pandemonium keys, uber organs/charms) is now in the global search
// index and routes to its EXISTING material ID card via openDrop. Pure search-wiring:
// the cards already existed; this makes each findable from the search box like an item.
test.describe('v74 materials are searchable + route to their ID card', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.waitForTimeout(1200);
    await page.evaluate(() => (window as any).switchTab('main'));   // v680 — TOOLS is the landing tab now; #event-ref lives on Main
    await page.waitForTimeout(300);
  });

  async function search(page: any, q: string) {
    await page.fill('#gsearch-input', q);
    await page.waitForTimeout(200);
    return page.evaluate(() => [...document.querySelectorAll('#gsearch-results .gsearch-item')]
      .map((el) => ({
        lab: (el.querySelector('.gsearch-lab') as HTMLElement)?.textContent?.trim() || '',
        cat: (el.querySelector('.gsearch-cat') as HTMLElement)?.textContent?.trim() || '',
      })));
  }

  test('each Sunder charm is searchable as a material', async ({ page }) => {
    for (const nm of ['Bone Break', 'Black Cleft', 'Crack of the Heavens', 'Cold Rupture', 'Flame Rift', 'Rotting Fissure']) {
      const hits = await search(page, nm);
      expect(hits.some((h) => h.lab.includes(nm) && /material/i.test(h.cat))).toBe(true);
    }
  });

  test('each Essence is searchable', async ({ page }) => {
    for (const nm of ['Essence of Hatred', 'Essence of Terror', 'Essence of Suffering', 'Essence of Destruction']) {
      const hits = await search(page, nm);
      expect(hits.some((h) => h.lab.includes(nm))).toBe(true);
    }
  });

  test('worldstone shards + colossal statue are searchable', async ({ page }) => {
    const shard = await search(page, 'worldstone shard');
    expect(shard.some((h) => /Worldstone Shard/.test(h.lab))).toBe(true);
    const statue = await search(page, 'colossal ancient statue');
    expect(statue.some((h) => /Colossal Ancient Statue/.test(h.lab))).toBe(true);
  });

  test('searching a Sunder and picking it opens its material card', async ({ page }) => {
    await page.fill('#gsearch-input', 'Bone Break');
    await page.waitForTimeout(220);
    await page.locator('#gsearch-results .gsearch-item').first().click();
    await page.waitForTimeout(250);
    const r = await page.evaluate(() => {
      const panel = document.getElementById('item-detail');
      return {
        shown: panel?.classList.contains('show'),
        name: panel?.querySelector('.material-card .gic-name')?.textContent?.trim() || '',
        hasDoes: !!panel?.querySelector('.material-card .gic-section'),
      };
    });
    expect(r.shown).toBe(true);
    expect(r.name).toMatch(/Bone Break/);
    expect(r.hasDoes).toBe(true);
  });

  test('searching an Essence and picking it opens its material card', async ({ page }) => {
    await page.fill('#gsearch-input', 'Essence of Hatred');
    await page.waitForTimeout(220);
    await page.locator('#gsearch-results .gsearch-item').first().click();
    await page.waitForTimeout(250);
    const name = await page.evaluate(() =>
      document.getElementById('item-detail')?.querySelector('.material-card .gic-name')?.textContent?.trim() || '');
    expect(name).toMatch(/Essence of Hatred/);
  });

  test('the Colossal Ancient Statues header carries real Talic art + collapses like the rest', async ({ page }) => {
    await page.click('.tab[data-tab="rotw"]');
    await page.waitForTimeout(250);
    const art = await page.evaluate(() => {
      const h = document.querySelector('#tab-rotw .statue-head');
      const img = h?.querySelector('.d2art-img') as HTMLImageElement | null;
      const body = h?.nextElementSibling as HTMLElement | null;
      return {
        hasHead: !!h,
        // v82: the header now toggles its sec-body open/closed (like every other section title),
        // it no longer routes straight to the ID card on click
        collapsible: (h?.getAttribute('onclick') || '').includes('toggleSec(this)'),
        startsCollapsed: !!h?.classList.contains('collapsed'),
        bodyHiddenAtStart: !!body?.hasAttribute('hidden'),
        src: img?.getAttribute('src') || '',
        lazy: img?.getAttribute('loading') === 'lazy',
        onerr: (img?.getAttribute('onerror') || '').includes('d2art-failed'),
      };
    });
    expect(art.hasHead).toBe(true);
    expect(art.collapsible).toBe(true);
    expect(art.startsCollapsed).toBe(true);
    expect(art.bodyHiddenAtStart).toBe(true);
    expect(art.src).toMatch(/d2mon_Talic\.gif(?:\?|$)/);   // REG-3321 (v3877 #102/#91): one picture per monster - the boss's own animated sprite, never a stone-backed render
    expect(art.lazy).toBe(true);
    expect(art.onerr).toBe(true);
    // clicking the header expands its body (does NOT open a card)
    await page.click('#tab-rotw .statue-head');
    await page.waitForTimeout(200);
    const expanded = await page.evaluate(() => {
      const h = document.querySelector('#tab-rotw .statue-head');
      const body = h?.nextElementSibling as HTMLElement | null;
      return { bodyVisible: !!body && !body.hasAttribute('hidden'), notCollapsed: !h?.classList.contains('collapsed') };
    });
    expect(expanded.bodyVisible).toBe(true);
    expect(expanded.notCollapsed).toBe(true);
    // the aggregate ID card is still reachable via its in-body link (the lead now ALSO
    // carries a "Colossal Summit →" link, so target the statue-card link specifically)
    await page.click('#tab-rotw .statue-head + .sec-body [onclick*="openDrop(\'Colossal Ancient Statue\')"]');
    await page.waitForTimeout(250);
    const name = await page.evaluate(() =>
      document.getElementById('item-detail')?.querySelector('.material-card .gic-name')?.textContent?.trim() || '');
    expect(name).toMatch(/Colossal Ancient Statue/);
  });

  test('the shards section has a "use it now or save it" explainer', async ({ page }) => {
    await page.click('.tab[data-tab="rotw"]');
    await page.waitForTimeout(250);
    const r = await page.evaluate(() => {
      const box = document.querySelector('#tab-rotw .shard-usesave');
      return { exists: !!box, text: (box as HTMLElement)?.textContent || '' };
    });
    expect(r.exists).toBe(true);
    expect(r.text).toMatch(/Renewed Sunder/);
    expect(r.text).toMatch(/save|hold|spare|surplus/i);
  });

  test('Main-tab "who drops what" rows route to the same material card', async ({ page }) => {
    // expand the cross-link section, then click a key row and confirm it opens an ID card
    await page.evaluate(() => {
      const h = [...document.querySelectorAll('#event-ref .sec-h')]
        .find((e) => /who drops what/i.test(e.textContent || '')) as HTMLElement | undefined;
      if (h && h.classList.contains('collapsed')) h.click();
    });
    await page.waitForTimeout(200);
    const wired = await page.evaluate(() => {
      const cells = [...document.querySelectorAll('#event-ref .er-line-main')];
      return {
        count: cells.length,
        allClickable: cells.length > 0 && cells.every((c) => (c.getAttribute('onclick') || '').includes('openDrop(')),
      };
    });
    expect(wired.count).toBeGreaterThanOrEqual(10);
    expect(wired.allClickable).toBe(true);
    await page.locator('#event-ref .er-line-main').first().click();
    await page.waitForTimeout(250);
    const shown = await page.evaluate(() =>
      document.getElementById('item-detail')?.classList.contains('show') &&
      !!document.getElementById('item-detail')?.querySelector('.material-card .gic-name'));
    expect(shown).toBe(true);
  });

  test('"who drops what" boss source chips carry art + route to the boss detail card', async ({ page }) => {
    await page.evaluate(() => {
      const h = [...document.querySelectorAll('#event-ref .sec-h')]
        .find((e) => /who drops what/i.test(e.textContent || '')) as HTMLElement | undefined;
      if (h && h.classList.contains('collapsed')) h.click();
    });
    await page.waitForTimeout(200);
    const chips = await page.evaluate(() => {
      const c = [...document.querySelectorAll('#event-ref .er-src-boss')];
      return {
        count: c.length,
        allRoute: c.length > 0 && c.every((e) => (e.getAttribute('onclick') || '').includes('openBossDetail(')),
        allArt: c.every((e) => !!e.querySelector('.d2art-wrap')),
        allHover: c.every((e) => !!e.getAttribute('data-art-logo')),
      };
    });
    expect(chips.count).toBeGreaterThanOrEqual(8);
    expect(chips.allRoute).toBe(true);
    expect(chips.allArt).toBe(true);
    expect(chips.allHover).toBe(true);
    // clicking a boss chip routes to the bosses tab + opens that boss detail
    await page.locator('#event-ref .er-src-boss').first().click();
    await page.waitForTimeout(400);
    const routed = await page.evaluate(() => {
      const ov = document.getElementById('boss-detail-overlay');
      return !!ov && !ov.classList.contains('hidden');
    });
    expect(routed).toBe(true);
  });
});
