import { test, expect } from './_net_stub'; // diablo2.io art stubbed — kills net-flake (audit 2026-06-12)
import * as path from 'path';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v123 — inline item-logo rollout (continuation of the emoji→artOr propagation). The
// Uber Tristram / Diablo Clone event-card BODIES referenced their grail items by a bare
// emoji + name (🔥 Hellfire Torch, 🔑 Key of Terror, 🔱 Annihilus, the 3 organs). They now
// carry data-art-logo="<Item>" and the generic decorateItemLogos() decorator injects the
// verified D2IO_ART graphic via the artOr single-source helper (emoji kept as fallback).
// Only names resolving in D2IO_ART get a logo → unmapped tags are a silent no-op. Routing
// (openDrop) is untouched. Headers were already arted in v79; this is the body backlog.
test.describe('v123 inline item logos (decorateItemLogos)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.waitForTimeout(1200);
  });

  const EXPECT: Record<string, string> = {
    'Hellfire Torch': 'mr_hellfiretorch.png',
    'Key of Terror': 'hd_mephisto_key.png',
    'Key of Hate': 'hd_mephisto_key.png',
    'Key of Destruction': 'hd_mephisto_key.png',
    "Mephisto's Brain": 'hd_brain.png',
    "Diablo's Horn": 'hd_horn.png',
    "Baal's Eye": 'hd_eye.png',
    'Annihilus': 'mr_annihilus.png',
    'Colossal Ancient Statue': 'd2mon_Talic.gif',   // REG-3321 (v3877 #102/#91): one picture per monster - the boss's own animated sprite, never a stone-backed render
    'Colossal Ancient Jewels': 'colossal_jewel1_graphic.png',
  };

  test('decorateItemLogos is exposed and idempotent', async ({ page }) => {
    const r = await page.evaluate(() => {
      const first = (window as any).decorateItemLogos();
      const second = (window as any).decorateItemLogos();
      return {
        hasFn: typeof (window as any).decorateItemLogos === 'function',
        first,
        second, // re-run must add nothing (guard against double-decorate)
      };
    });
    expect(r.hasFn).toBe(true);
    expect(r.first).toBe(0); // already ran on load — nothing left to do
    expect(r.second).toBe(0);
  });

  test('every tagged cell carries its verified D2IO_ART logo with emoji fallback', async ({ page }) => {
    for (const [name, slug] of Object.entries(EXPECT)) {
      const r = await page.evaluate((n) => {
        const el = document.querySelector(`[data-art-logo="${n.replace(/"/g, '\\"')}"]`);
        if (!el) return { present: false };
        const img = el.querySelector(':scope > .d2art-wrap .d2art-img') as HTMLImageElement | null;
        const fb = el.querySelector(':scope > .d2art-wrap .d2art-fallback');
        return {
          present: true,
          src: img?.getAttribute('src') || '',
          lazy: img?.getAttribute('loading') === 'lazy',
          fallback: (fb?.textContent || '').trim(),
          routed: (el.getAttribute('onclick') || '').includes('openDrop('),
        };
      }, name);
      expect(r.present, `${name} cell present`).toBe(true);
      expect(r.src, `${name} src`).toContain(slug);
      expect(r.src, `${name} items path`).toContain('art/');
      expect(r.lazy, `${name} lazy-loaded`).toBe(true);
      expect(r.fallback.length, `${name} has emoji fallback`).toBeGreaterThan(0);
      expect(r.routed, `${name} openDrop routing preserved`).toBe(true);
    }
  });

  test('an unmapped data-art-logo tag is a silent no-op (no empty wrap)', async ({ page }) => {
    const r = await page.evaluate(() => {
      const el = document.createElement('span');
      el.setAttribute('data-art-logo', '__NoSuchItem__');
      el.setAttribute('data-art-glyph', '❓');
      el.textContent = 'ghost';
      document.body.appendChild(el);
      const added = (window as any).decorateItemLogos();
      const wrap = el.querySelector(':scope > .d2art-wrap');
      el.remove();
      return { added, hasWrap: !!wrap };
    });
    expect(r.added).toBe(0); // unmapped name decorated nothing
    expect(r.hasWrap).toBe(false);
  });

  test('clicking a tagged cell still routes to its material card', async ({ page }) => {
    const src = await page.evaluate(() => {
      const el = document.querySelector('[data-art-logo="Hellfire Torch"]') as HTMLElement;
      el.click();
      const card = document.getElementById('item-detail');
      const img = card?.querySelector('.material-card .d2art-img') as HTMLImageElement | null;
      return img?.getAttribute('src') || '';
    });
    expect(src).toContain('hellfiretorch');   // v350.1 swapped to HD art/mr_hellfiretorch.png; routing intact
  });

  test('no console errors decorating + opening the tagged items', async ({ page }) => {
    const errs: string[] = [];
    page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
    await page.evaluate(() => (window as any).decorateItemLogos());
    for (const name of Object.keys({
      'Hellfire Torch': 1, 'Key of Terror': 1, 'Annihilus': 1, "Baal's Eye": 1,
    })) {
      await page.evaluate((n) => (window as any).openDrop(n), name);
      await page.waitForTimeout(30);
    }
    expect(errs).toEqual([]);
  });
});
