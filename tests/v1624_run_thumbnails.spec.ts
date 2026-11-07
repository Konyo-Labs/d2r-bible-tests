import { test, expect } from './_net_stub';
import * as path from 'path';

// v1624 — THE RUN'S PICTURE IS THE RUN.
//
// Konyo: "the item logos on the left for each Hell mephisto and the pindleskin.. like what are they
// representing? ... something might be not coded properly and its confusing fix it please too".
//
// The thumbnail was art(r.items[0].n) — whichever unique happened to sort FIRST in that run's drop
// list, with a target glyph when that item had no art. Not the boss, not the fastest drop, not the
// level: an arbitrary picture that changed as his grail changed. Pindleskin rendered a bare emoji
// for no reason a reader could infer.
//
// His call: "for best runs it shows us the boss as a main.. and for quick wins we dont touch and
// leave it as is which is the item as the main" — both clickable, both with the hover card.
//
// v1643 — WHY THIS SPEC WAS RED FROM ~v1634 AND WHAT IT NOW MEASURES (REG-129).
// v1636 (d200b7b) deliberately replaced data-art-logo with data-boss-tip on the best-run
// .f-runart span, because data-art-logo resolves through the ITEM art map and so hovering
// Mephisto's correct PORTRAIT opened his SOULSTONE card. The app was right; this spec kept
// reading the attribute that no longer exists and failed on a NULL — and a null is never a
// passing result, so the suite stayed red for nine versions with nobody reading the message.
//
// The naive fix (s/data-art-logo/data-boss-tip/) would have made the containment assertion
// compare a title against an ID ("Hell TZ Pindleskin" vs "pindle"), which happens to pass for
// four ids and is nonsense for the rest ("Hell Bovines" does not contain "cows"). What is
// asserted instead is the thing the assertion was always REACHING for: the id is resolved
// through BOSSES to that boss's NAME, and the row's title must name that boss. That is the
// check that catches the real defect underneath — a best-run row titled Pindleskin carrying
// bossId 'nihl', which opens Nihlathak's card and portrait under Pindleskin's name.

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

async function funi(page: any) {
  await page.goto(URL);
  await page.waitForTimeout(2800);
  await page.evaluate(() => { try { (window as any).switchTab('funi'); } catch (e) {} });
  await page.waitForTimeout(1800);
}

/* One measurement, three assertions. Reads the DOM the user actually gets AND the two maps the
   app builds it from, so every row is checked against what the app itself believes rather than
   against a hardcoded table this file would have to keep in sync. */
async function runRows(page: any) {
  return await page.evaluate(() => {
    const w: any = window;
    let B: any = [];
    try { B = (0, eval)('BOSSES'); } catch (e) { B = w.BOSSES || []; }
    const NAME: any = {};
    for (const b of B) NAME[b.id] = b.name;
    let PORTRAIT: any = {};
    try { PORTRAIT = (0, eval)('BOSS_PORTRAIT') || {}; } catch (e) { PORTRAIT = w.BOSS_PORTRAIT || {}; }
    const read = (sel: string) => Array.from(document.querySelectorAll(sel)).map((c: any, i: number) => {
      const a: any = c.querySelector('.f-runart');
      const img: any = a && a.querySelector('img');
      const src: string | null = img ? String(img.getAttribute('src') || '') : null;
      const id: string | null = (a && a.getAttribute('data-boss-tip')) || null;
      return {
        i,
        title: (c.querySelector('.f-rwbig') as any)?.textContent?.trim() || '',
        bossId: id,
        bossName: id ? (NAME[id] || null) : null,
        // v1636 retired this attribute on best-run rows; if it ever comes back, the hover card
        // resolves through the ITEM map again and Mephisto's soulstone returns.
        legacy: (a && a.getAttribute('data-art-logo')) || null,
        src,
        // the cache-busted URL is art/x.png?v=<build>: shape checks compare the FILE, freshness
        // checks read the QUERY (v1643, REG-128).
        file: src ? src.split('?')[0].replace(/^art\//, '') : null,
        bust: src ? /[?&]v=/.test(src) : false,
        portrait: (id && PORTRAIT[id]) ? String(PORTRAIT[id]) : null,
        loaded: img ? img.naturalWidth > 0 : false,
        click: (a && a.getAttribute('onclick')) || '',
      };
    });
    return { pipe: read('#tab-funi .f-card.f-pipe'), step: read('#tab-funi .f-card.f-step') };
  });
}

test.describe('v1624 — the run wears its boss, the quick win wears its item', () => {
  test('★★★ every BEST RUN thumbnail is its BOSS, and it loads', async ({ page }) => {
    await funi(page);
    const { pipe } = await runRows(page);
    expect(pipe.length).toBeGreaterThan(2);

    // markup + identity on EVERY row: the wrong-boss defect this arc found lived on row 8, and a
    // spec that only ever read the first five would have shipped it again.
    for (const r of pipe) {
      expect(r.bossId, `${r.title} has no boss anchor`).toBeTruthy();
      expect(r.bossName, `${r.title}: data-boss-tip="${r.bossId}" is not an id in BOSSES`).toBeTruthy();
      /* the picture is OF the boss the row is about — the row's title names that boss. Resolved
         id -> name, never id -> title: 'cows' is not in "Hell Bovines" and never will be. */
      expect(r.title.toLowerCase(), `${r.title}: labelled with boss id ${r.bossId} = ${r.bossName}`)
        .toContain(String(r.bossName).toLowerCase());
      expect(r.legacy, `${r.title}: data-art-logo is back — the hover card would resolve this ` +
        'boss through the ITEM art map again (v1636: Mephisto = his soulstone)').toBeNull();
      expect(r.click, 'and open that boss').toContain('openBossDetail');
      expect(r.click, `${r.title}: the click must open the SAME boss the picture is of`)
        .toContain("('" + r.bossId + "')");
      /* if BOSS_PORTRAIT knows this boss, the row must be WEARING that portrait, not the level
         art it used to fall through to. v1643 wired `pindle`; this is what proves the run board
         picked it up, rather than the manifest merely agreeing with itself. */
      if (r.portrait) {
        expect(r.file, `${r.title}: BOSS_PORTRAIT[${r.bossId}] is ${r.portrait} but the row renders ${r.src}`)
          .toBe(r.portrait);
      }
    }

    // decoding is only meaningful above the fold — the thumbnails are loading="lazy", so a row
    // far down the board honestly reports naturalWidth 0 until it scrolls into view.
    for (const r of pipe.slice(0, 5)) {
      expect(r.loaded, `${r.title}: the boss art must actually decode`).toBe(true);
    }
  });

  test('★★ QUICK WINS still shows the ITEM — his explicit call', async ({ page }) => {
    await funi(page);
    const { step } = await runRows(page);
    if (!step.length) return;   // no one-step wins right now is a legitimate state
    for (const r of step.slice(0, 3)) {
      expect(r.legacy, 'the quick win names an ITEM, not a boss').toBeTruthy();
      expect(r.bossId, 'and it must not have picked up a boss anchor').toBeNull();
      expect(r.click, 'and opens that item, not a boss card').toContain('navigateToItem');
    }
  });

  test('★★ every art URL on the run board carries the build id — REG-128', async ({ page }) => {
    /* v1643 — A REPAIRED ASSET IS INVISIBLE UNTIL ITS URL CHANGES. Art URLs were built as
       'art/' + file with no version query, while the page itself is loaded as ?v={app_ver}. So a
       version bump busted the HTML and the JS and never the IMAGES. v269 rewrote ~230 art files
       IN PLACE and v1636 repaired them IN PLACE under the same filenames, so every cached copy
       kept serving the old picture — which is why he re-reported the already-corrected 'Hell TZ
       Diablo' thumbnail as a book. Boss art AND item art, because both were repaired in place. */
    await funi(page);
    const { pipe, step } = await runRows(page);
    const painted = [...pipe, ...step].filter((r: any) => r.src);
    expect(painted.length, 'nothing painted — this assertion would be vacuous').toBeGreaterThan(4);
    for (const r of painted) {
      expect(r.bust, `${r.title}: ${r.src} carries no build id — a repaired file at this URL ` +
        'stays invisible behind the browser cache').toBe(true);
    }
  });

  test('★★ the boss art resolver covers EVERY boss — measured, not hoped', async ({ page }) => {
    /* Written before the change and kept: 13 of 13 resolve — through the zone art the TZ panel
       already paints with, or through their own portrait. A resolver that silently returns null
       for a third of the roster would put the arbitrary-picture problem back under a new name. */
    await page.goto(URL); await page.waitForTimeout(2600);
    const cover = await page.evaluate(() => {
      const w: any = window;
      let B: any = [];
      try { B = (0, eval)('BOSSES'); } catch (e) { B = w.BOSSES || []; }
      let ok = 0;
      for (const b of B) {
        const r = w._runBossArt ? w._runBossArt(b.id, b.name) : null;
        if (r && (r.url || r.emoji)) ok++;
      }
      const rows = B.map((b: any) => {
        const r = w._runBossArt ? w._runBossArt(b.id, b.name) : null;
        // shape is read off the PATH, because v1643 appends ?v=<build> to every art URL
        const url = r && r.url ? String(r.url) : null;
        return { id: b.id, url, path: url ? url.split('?')[0] : null };
      });
      return { total: B.length, ok, rows };
    });
    expect(cover.total).toBeGreaterThan(10);
    /* v1629 — "RESOLVES TO SOMETHING" IS NOT ENOUGH, and this assertion proved it. It passed
       while Mephisto rendered his SOULSTONE and Diablo rendered a BOOK, because v1624 asked
       artUrl() — an ITEM map — for a boss, and an item sprite satisfies "something" perfectly.
       Konyo saw it before any test did. What is asserted now is that the picture is OF a boss or
       its level: a *_graphic.* from the portrait table or the terror-zone art, never an item. */
    expect(cover.ok, 'every boss must resolve to something real').toBe(cover.total);
    for (const r of cover.rows) {
      if (!r.url) continue;   // a boss with no place and no portrait renders nothing, honestly
      /* two legitimate shapes and no others: a boss PORTRAIT (art/<boss>_graphic.png) or the
         LEVEL art the terror-zone cards use (art/tz_<slug>.jpg). Anything else means the resolver
         has wandered back into the item map. */
      expect(r.path, `${r.id}: boss art must be a portrait or the level art`)
        .toMatch(/(_graphic\.(png|gif)|\/tz_[\w-]+\.jpg|\/d2mon_[\w-]+\.gif)$/i);   // REG-3321: or the boss's own D2 sprite
      expect(r.path, `${r.id}: resolved to an ITEM sprite — art/ holds durielsshell_graphic.png, ` +
        'and any fuzzy name match grabs it').not.toMatch(/shell|soul_?stone|_key|charm/i);
    }
    // and the roster must be mostly PICTURED, not mostly blank
    expect(cover.rows.filter((r: any) => r.url).length).toBeGreaterThanOrEqual(cover.total - 1);
  });
});
