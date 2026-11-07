import { test, expect } from './_net_stub'; // diablo2.io art stubbed — kills net-flake (audit 2026-06-12)
import * as path from 'path';

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v71 — d2art: real item/boss/rune artwork hotlinked from diablo2.io's avatar gallery, with a
// guaranteed emoji fallback so a card can NEVER render a broken-image box.
//   1. D2IO_ART is a top-level global map {name -> diablo2.io gallery URL}. Every URL was probed
//      live (HTTP 200 + image content-type) before shipping — zero fabricated/guessed URLs.
//   2. artOr(name, fallbackHtml, size) returns an <img> when we have a verified URL, else the
//      fallback markup verbatim. The <img> has an onerror that swaps to the emoji on load failure.
//   3. The item ID-card, boss ID-card, and rune-stash cells render the art (or fall back cleanly).
test.describe('v71 d2art artwork layer', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(URL);
    await page.waitForTimeout(1200);
  });

  test('D2IO_ART is a verified global map and artUrl/artOr are exposed helpers', async ({ page }) => {
    const r = await page.evaluate(() => {
      const m = (window as any).D2IO_ART;
      const names = m ? Object.keys(m) : [];
      return {
        type: typeof m,
        len: names.length,
        allDiablo2io: names.every((n) => /^art\//.test(m[n])),
        allImageExt: names.every((n) => /\.(png|gif|jpe?g)(?:\?|$)/i.test(m[n])),
        encoded: names.every((n) => !/ /.test(m[n])),           // spaces URL-encoded, no raw spaces
        hasItem: !!m['Arachnid Mesh'],
        hasRune: !!m['Ist'],
        hasBoss: !!m['The Countess'],
        fns: ['artUrl', 'artOr'].map((f) => typeof (window as any)[f]),
        // artUrl returns null for an unknown name, the URL for a known one
        unknownNull: (window as any).artUrl('Totally Not A Real Item ZZZ') === null,
        knownUrl: (window as any).artUrl('Ist'),
      };
    });
    expect(r.type).toBe('object');
    expect(r.len).toBeGreaterThanOrEqual(150);
    expect(r.allDiablo2io).toBe(true);
    expect(r.allImageExt).toBe(true);
    expect(r.encoded).toBe(true);
    expect(r.hasItem).toBe(true);
    expect(r.hasRune).toBe(true);
    expect(r.hasBoss).toBe(true);
    expect(r.fns.every((t) => t === 'function')).toBe(true);
    expect(r.unknownNull).toBe(true);
    expect(r.knownUrl).toMatch(/(hd_ist_rune|runeIst_icon)\.png(?:\?|$)/);
  });

  test('artOr emits an <img> with onerror fallback for mapped names, raw fallback for unmapped', async ({ page }) => {
    const r = await page.evaluate(() => ({
      mapped: (window as any).artOr('Ist', '<span class="x">FB</span>', 'sm'),
      unmapped: (window as any).artOr('No Such Thing 999', '<span class="x">FB</span>', 'lg'),
    }));
    // mapped → real <img> from diablo2.io, carries the alt + an onerror that (after a single
    // retry) reveals the fallback span, plus an onload that clears a transient failed state
    expect(r.mapped).toMatch(/<img[^>]+class="d2art-img"/);
    expect(r.mapped).toMatch(/src="art\//);
    expect(r.mapped).toMatch(/onerror="[^"]*this\.parentNode\.classList\.add\('d2art-failed'\)/);
    expect(r.mapped).toMatch(/onload="this\.parentNode\.classList\.remove\('d2art-failed'\)"/);
    expect(r.mapped).toContain('d2art-fallback');
    expect(r.mapped).toContain('FB');                    // fallback still embedded for the error path
    // unmapped → a consistent d2art-failed wrapper around the fallback (no <img>), so the
    // emoji/raw fallback renders via CSS just like a mapped name whose image fails to load
    expect(r.unmapped).toContain('d2art-wrap');
    expect(r.unmapped).toContain('d2art-failed');
    expect(r.unmapped).toContain('<span class="x">FB</span>');
    expect(r.unmapped).not.toContain('<img');
  });

  test('the item ID-card renders real artwork for a mapped item', async ({ page }) => {
    await page.evaluate(() => (window as any).renderItemDetailCard('Arachnid Mesh'));
    await page.waitForTimeout(150);
    const r = await page.evaluate(() => {
      const panel = document.getElementById('item-detail-panel');
      const img = panel?.querySelector('.gic-header .d2art-img') as HTMLImageElement | null;
      return {
        hasImg: !!img,
        src: img?.getAttribute('src') || '',
        // a fallback emoji span is present (revealed by onerror only if the image fails to load)
        hasFallback: !!img?.parentElement?.querySelector('.d2art-fallback'),
      };
    });
    expect(r.hasImg).toBe(true);
    expect(r.src).toMatch(/^art\//);
    expect(r.hasFallback).toBe(true);
  });

  test('an UNmapped item keeps its emoji (no broken image)', async ({ page }) => {
    // find an UNmapped item that renders a real gic item-card (skip keys/organs that route to
    // material cards), then assert it falls back to the emoji with no <img> element at all
    const r = await page.evaluate(() => {
      const m = (window as any).D2IO_ART;
      const panel = document.getElementById('item-detail-panel');
      let unmapped = '', emoji = false, hasImg = true;
      for (const n of (ITEMS as any[]).map((x) => x.n)) {
        if (m[n]) continue;
        (window as any).renderItemDetailCard(n);
        const e = !!panel?.querySelector('.gic-header .gic-emoji');
        if (e) { unmapped = n; emoji = true; hasImg = !!panel?.querySelector('.gic-header .d2art-img'); break; }
      }
      return { unmapped, emoji, hasImg };
    });
    expect(r.unmapped).toBeTruthy();
    expect(r.emoji).toBe(true);      // emoji still shown
    expect(r.hasImg).toBe(false);    // and no image element at all
  });

  test('the boss ID-card renders artwork for a mapped boss (The Countess)', async ({ page }) => {
    const r = await page.evaluate(() => {
      const b = (BOSSES as any[]).find((x) => x.name === 'The Countess');
      (window as any).renderBossDetailCard(b.id);
      const panel = document.getElementById('boss-detail-panel');
      const img = panel?.querySelector('.gbc-header .d2art-img') as HTMLImageElement | null;
      return { hasImg: !!img, src: img?.getAttribute('src') || '' };
    });
    expect(r.hasImg).toBe(true);
    expect(r.src).toContain('art/');
    expect(r.src).toMatch(/countess/i);
  });

  test('rune-stash cells show rune icons for mapped runes (incl. Jah=runeJo, now verified)', async ({ page }) => {
    await page.click('.tab[data-tab="runes"]');
    await page.waitForTimeout(200);
    const r = await page.evaluate(() => {
      const istCell = document.querySelector('.rune-stash-cell[data-rune="Ist"]');
      const jahCell = document.querySelector('.rune-stash-cell[data-rune="Jah"]');
      return {
        istImg: !!istCell?.querySelector('.d2art-img'),
        istSrc: (istCell?.querySelector('.d2art-img') as HTMLImageElement)?.getAttribute('src') || '',
        jahImg: !!jahCell?.querySelector('.d2art-img'),   // v139: Jah now mapped (runeJo, curl-verified 200)
        jahSrc: (jahCell?.querySelector('.d2art-img') as HTMLImageElement)?.getAttribute('src') || '',
      };
    });
    expect(r.istImg).toBe(true);
    expect(r.istSrc).toMatch(/(hd_ist_rune|runeIst_icon)\.png(?:\?|$)/);
    expect(r.jahImg).toBe(true);
    expect(r.jahSrc).toMatch(/(hd_jah_rune|runeJo_icon)\.png(?:\?|$)/);
  });

  test('the material detail card renders artwork for a mapped sunder (Bone Break)', async ({ page }) => {
    const r = await page.evaluate(() => {
      (window as any).openDrop('Bone Break');
      const panel = document.getElementById('item-detail');
      const img = panel?.querySelector('.material-card .gic-header .d2art-img') as HTMLImageElement | null;
      return { hasImg: !!img, src: img?.getAttribute('src') || '' };
    });
    expect(r.hasImg).toBe(true);
    expect(r.src).toContain('art/');
    expect(r.src).toMatch(/bonebreakcharm/);
  });

  test('the rune detail card renders the rune icon for a mapped rune (Ist)', async ({ page }) => {
    const r = await page.evaluate(() => {
      (window as any).openDrop('Ist');
      const panel = document.getElementById('item-detail');
      const img = panel?.querySelector('.rune-card .gic-header .d2art-img') as HTMLImageElement | null;
      return { hasImg: !!img, src: img?.getAttribute('src') || '' };
    });
    expect(r.hasImg).toBe(true);
    expect(r.src).toMatch(/(hd_ist_rune|runeIst_icon)\.png(?:\?|$)/);
  });

  test('the calc grid tiles show art thumbnails for mapped items', async ({ page }) => {
    await page.click('.tab[data-tab="calc"]');
    await page.waitForTimeout(200);
    const r = await page.evaluate(() => {
      const tile = document.querySelector('#item-grid .item-tile[data-name="Arachnid Mesh"]');
      const img = tile?.querySelector('.item-tile-row .d2art-img') as HTMLImageElement | null;
      // tiles still hold their name+tc text alongside the art
      return {
        hasImg: !!img,
        src: img?.getAttribute('src') || '',
        name: tile?.querySelector('.item-tile-name')?.textContent?.trim() || '',
        lazy: img?.getAttribute('loading') || '',
      };
    });
    expect(r.hasImg).toBe(true);
    expect(r.src).toContain('art/');
    expect(r.name).toBe('Arachnid Mesh');
    expect(r.lazy).toBe('lazy');     // grid art is lazy-loaded, not a load-time storm
  });

  test('calc grid tiles are flat siblings — no recursive nesting (regression)', async ({ page }) => {
    // the art-thumbnail wrapper once dropped a </div>, so every .item-tile nested
    // inside the previous one (cascading card-in-card). Each tile must be a DIRECT
    // child of #item-grid, and no tile may contain another .item-tile.
    await page.click('.tab[data-tab="calc"]');
    await page.waitForTimeout(250);
    const r = await page.evaluate(() => {
      const grid = document.getElementById('item-grid')!;
      const tiles = [...grid.querySelectorAll('.item-tile')];
      const directChildren = [...grid.children].filter((c) => c.classList.contains('item-tile')).length;
      const nested = tiles.filter((t) => t.querySelector('.item-tile')).length;
      return { total: tiles.length, directChildren, nested };
    });
    expect(r.total).toBeGreaterThan(50);
    expect(r.directChildren).toBe(r.total); // every tile is a direct grid child
    expect(r.nested).toBe(0);               // no tile swallows another
  });

  test('the boss ID-card renders artwork for Baal and Pindleskin (newly mapped)', async ({ page }) => {
    const r = await page.evaluate(() => {
      const out: any = {};
      for (const nm of ['Baal', 'Pindleskin']) {
        const b = (BOSSES as any[]).find((x) => x.name === nm);
        (window as any).renderBossDetailCard(b.id);
        const panel = document.getElementById('boss-detail-panel');
        const img = panel?.querySelector('.gbc-header .d2art-img') as HTMLImageElement | null;
        out[nm] = img?.getAttribute('src') || '';
      }
      return out;
    });
    expect(r.Baal).toMatch(/d2mon_Baal\.gif(?:\?|$)/);   // REG-3321 (v3877 #102/#91): one picture per monster - the boss's own animated sprite, never a stone-backed render
    expect(r.Pindleskin).toMatch(/d2mon_Pindleskin\.gif(?:\?|$)/);
  });

  test('the boss-nav chips show verified portrait art for every boss (incl. Andariel)', async ({ page }) => {
    await page.click('.tab[data-tab="bosses"]');
    await page.waitForTimeout(200);
    const r = await page.evaluate(() => {
      const chipFor = (name: string) => {
        const b = (BOSSES as any[]).find((x) => x.name === name);
        return document.querySelector(`#boss-nav .boss-chip[data-boss-id="${b.id}"]`);
      };
      const meph = chipFor('Mephisto');
      const baal = chipFor('Baal');
      const anda = chipFor('Andariel');
      return {
        mephImg: !!meph?.querySelector('.d2art-img'),
        mephSrc: (meph?.querySelector('.d2art-img') as HTMLImageElement)?.getAttribute('src') || '',
        mephLazy: (meph?.querySelector('.d2art-img') as HTMLImageElement)?.getAttribute('loading') || '',
        mephText: meph?.textContent?.trim() || '',
        baalImg: !!baal?.querySelector('.d2art-img'),
        baalSrc: (baal?.querySelector('.d2art-img') as HTMLImageElement)?.getAttribute('src') || '',
        // Andariel's case-sensitive portrait (Andariel_graphic.png) was verified live on
        // diablo2.io — every boss now carries real art, so her chip has an <img> too.
        andaImg: !!anda?.querySelector('.d2art-img'),
        andaSrc: (anda?.querySelector('.d2art-img') as HTMLImageElement)?.getAttribute('src') || '',
        andaText: anda?.textContent?.trim() || '',
      };
    });
    expect(r.mephImg).toBe(true);
    expect(r.mephSrc).toContain('art/');
    expect(r.mephLazy).toBe('lazy');
    expect(r.mephText).toContain('Mephisto');   // name still rendered alongside the art
    expect(r.baalImg).toBe(true);
    expect(r.baalSrc).toMatch(/d2mon_Baal\.gif(?:\?|$)/);   // REG-3321 (v3877 #102/#91): one picture per monster - the boss's own animated sprite, never a stone-backed render
    expect(r.andaImg).toBe(true);
    expect(r.andaSrc).toMatch(/d2mon_Andariel\.gif(?:\?|$)/);
    expect(r.andaText).toContain('Andariel');
  });

  test('every super-unique resolves verified art (full SU coverage, no emoji-only)', async ({ page }) => {
    // v108: the whole SUPER_UNIQUES roster (incl. Lister the Tormentor) carries real art - each
    // URL was probed live (200 + image content-type) before shipping. v3876 (REG-3315, his 11-06
    // ask: one HD picture per monster, platform-wide) moved the monsters onto their animated
    // in-game sprites, shipped as art/d2mon_<Name>.gif (sources in tv/data/monster_art_fandom.json).
    // This locks the coverage so a future entry can't silently regress to an emoji-only card.
    const r = await page.evaluate(() => {
      const sus = (SUPER_UNIQUES as any[]);
      const missing = sus.filter((s) => !(window as any).artUrl(s.name)).map((s) => s.name);
      return {
        total: sus.length,
        missing,
        lister: (window as any).artUrl('Lister the Tormentor') || '',
      };
    });
    expect(r.total).toBeGreaterThanOrEqual(18);
    expect(r.missing).toEqual([]);                       // EVERY super-unique has real art
    expect(r.lister).toMatch(/d2mon_Lister_the_Tormentor\.gif(?:\?|$)/);    // the MONSTER's sprite, not the item
  });

  test('the new Lister super-unique card renders its verified portrait art', async ({ page }) => {
    // jumpToSuperUniqueByName switches to the tz tab + toggles the detail open on a 110ms timer,
    // so split the call from the query (mirrors the v83 entity-sync test).
    await page.evaluate(() => (window as any).jumpToSuperUniqueByName('Lister the Tormentor'));
    await page.waitForTimeout(300);
    const r = await page.evaluate(() => {
      const card = document.querySelector('.su-card-rich') as HTMLElement | null;
      const img = card?.querySelector('.gbc-header .d2art-img') as HTMLImageElement | null;
      return {
        hasCard: !!card,
        name: card?.querySelector('.gbc-name')?.textContent?.trim() || '',
        src: img?.getAttribute('src') || '',
        lazy: img?.getAttribute('loading') || '',
      };
    });
    expect(r.hasCard).toBe(true);
    expect(r.name).toMatch(/Lister the Tormentor/);
    expect(r.src).toMatch(/d2mon_Lister_the_Tormentor\.gif(?:\?|$)/);   // the same picture artUrl answers (REG-3315)
    expect(r.lazy).toBe('lazy');
  });

  test('no console errors when opening art-bearing cards', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
    await page.goto(URL);
    await page.waitForTimeout(1200);
    await page.evaluate(() => {
      (window as any).renderItemDetailCard('Arachnid Mesh');
      const b = (BOSSES as any[]).find((x) => x.name === 'The Countess');
      (window as any).renderBossDetailCard(b.id);
    });
    await page.click('.tab[data-tab="runes"]');
    await page.waitForTimeout(200);
    // network 404s on hotlinked images are NOT console errors; assert no JS errors
    expect(errors).toEqual([]);
  });
});
