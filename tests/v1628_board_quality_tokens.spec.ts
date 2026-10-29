import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';

/* v1628 — ONE PALETTE, READ AT RUNTIME.  (owner: this spec file only; bible.html is owner A's)
 *
 * Konyo: "fix the console color wise any where for the relevant keywords related to the color it
 *         should be related too tooltips images too.. full audit it."
 *
 * v1625 proved individual SURFACES wear the right quality. This file proves the SOURCE OF TRUTH is
 * single, and that the three concepts the board keeps fusing render apart:
 *
 *   a completed RUNEWORD's name  = the unique gold (--q-unique)
 *   a RUNE item (El, Eld)        = --rune
 *   a CRAFTED item              = --q-orange
 *
 * THE CENTRAL LAW — no hex is ever restated in an expectation. Every expected colour is resolved
 * from the live document's own custom property and painted onto a throwaway probe, so the
 * expectation is whatever the palette says today, in the exact rgb() form getComputedStyle returns.
 * WHY: v1621 pinned rgb(0,255,0) literally and went RED the day the palette became CORRECT; v1622
 * shipped a wrong gold that three tests passed over because they only asserted a class existed.
 * The two literal hexes below are the DUPLICATE palette this file exists to ban — a guard rail has
 * to name the thing it guards, and these are compared against, never asserted as correct.
 *
 * WHAT v1625 ALREADY OWNS (this file EXTENDS, it does not duplicate):
 *   ITEM 2  .forge-tab.ft-craft is --q-orange resting+lit; the four CRAFT GEM colours frozen
 *   ITEM 3  Chronicle Sealed buttons; F-Uniques FOUND-log rows; F-Sets piece names vs set TITLES
 *   ITEM 5  F-Sets piece anchors: green · role · tabindex · ≤430×120 · Enter==click · hover card
 *   ITEM 6  .forge-title on F-Sets/F-Uniques: token colour + a real decoding <img>; last-found
 * Nothing here re-measures those. This file adds: the token/JS-map/legend AGREEMENT layer, the
 * runeword/rune/crafted three-way split, an <img> DECODE sweep across four surfaces, the
 * no-arbitrary-picture rule on quick-win thumbnails, and the F-UNIQUES (not F-Sets) hover binding.
 */

const URL = 'file://' + path.resolve(__dirname, '..', process.env.BIBLE_FILE || 'bible.html');

/* The second palette. bible.html:3772 declares :root{--d2-unique/--d2-set/--d2-magic} and the codex
   card paints from it. Literal by design — this is the thing being banned, not the thing asserted. */
const DUPLICATE_TOKENS = ['--d2-unique', '--d2-set', '--d2-magic'] as const;
const DUPLICATE_OF: Record<string, string> = {
  '--d2-unique': '--q-unique',
  '--d2-set': '--q-set',
  '--d2-magic': '--q-magic',
};

/* ── page-side toolkit (shape copied from v1625) ──────────────────────────────────────────────
   paint(v)      resolve a :root custom property to the rgb() the browser would actually paint
   paintRaw(css) resolve ANY css colour string the same way — used to normalise a JS-map hex so a
                 '#00ff00' vs '#00fc00' mismatch is caught in the same colour space as the render  */
const TOOLKIT = `
  window.__q28 = (function(){
    var probe = document.createElement('div');
    probe.style.cssText = 'position:absolute;left:-9999px;top:-9999px';
    document.body.appendChild(probe);
    function paintRaw(css){
      probe.style.color = 'rgb(1,2,3)';
      probe.style.color = css;
      var out = getComputedStyle(probe).color;
      return (out === 'rgb(1, 2, 3)' && String(css).replace(/\\s/g,'') !== 'rgb(1,2,3)') ? '' : out;
    }
    function raw(v){ return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
    function paint(v){ var r = raw(v); return r ? paintRaw(r) : ''; }
    return { paint:paint, paintRaw:paintRaw, raw:raw,
             colorOf:function(el){ return getComputedStyle(el).color; } };
  })();
`;

async function board(page: any, tab?: string) {
  await page.goto(URL);
  await page.waitForTimeout(2800);
  await page.evaluate(TOOLKIT);
  if (tab) {
    await page.evaluate((t: string) => { try { (window as any).switchTab(t); } catch (e) {} }, tab);
    await page.waitForTimeout(1800);
  }
}

/* Some quality-bearing rows (rune saver, runeword rows, craft workshop) live on a tab this spec
   should not have to hard-code. Find the tab that OWNS a selector, activate it, re-query. */
const FIND_TAB = `
  window.__tabOf = function(sel){
    var el = document.querySelector(sel);
    if (!el) return null;
    var host = el.closest('[id^="tab-"]');
    return host ? host.id.replace(/^tab-/, '') : null;
  };
`;

/* Board art is loading="lazy". An <img> that is in the DOM and laid out but below the fold has
   naturalWidth 0 for a reason that has nothing to do with its path being right — measuring it
   would report a HARNESS artifact as a broken picture. (First run of this file did exactly that:
   the "Andariel" thumbnail, 12 cards down, read as undecodable while its path was fine.)
   Force every img in scope eager and give the loads a beat, THEN measure. What survives is a
   genuinely unresolvable path. */
async function eagerLoadArt(page: any, rootSel: string) {
  const n = await page.evaluate((sel: string) => {
    const root: any = document.querySelector(sel) || document;
    const imgs = Array.from(root.querySelectorAll('img'));
    imgs.forEach((i: any) => { if (i.loading === 'lazy') i.loading = 'eager'; });
    return imgs.length;
  }, rootSel);
  await page.waitForTimeout(2600);
  return n;
}

/* ════════════════════════════════════════════════════════════════════════════════════════════
   1 — NO SECOND PALETTE.  The root-cause guard.
   ════════════════════════════════════════════════════════════════════════════════════════════ */
test.describe('v1628 · 1 — one palette, not two', () => {
  test('★★★ --d2-* either does not exist or resolves IDENTICAL to its --q-* counterpart', async ({ page }) => {
    await board(page);
    const r = await page.evaluate((names: readonly string[]) => {
      const Q: any = (window as any).__q28;
      const out: any[] = [];
      for (const n of names) {
        const map: any = { '--d2-unique': '--q-unique', '--d2-set': '--q-set', '--d2-magic': '--q-magic' };
        out.push({ name: n, declared: Q.raw(n), got: Q.paint(n), want: Q.paint(map[n]), wantName: map[n] });
      }
      return out;
    }, DUPLICATE_TOKENS as any);
    console.log('1 · duplicate-palette probe: %s', JSON.stringify(r, null, 1));
    for (const t of r) {
      /* declared === '' is the CLEAN outcome: the duplicate was deleted. */
      if (!t.declared) continue;
      expect(t.want, `${t.wantName} does not resolve — the real palette is missing`).toBeTruthy();
      expect(t.got,
        `${t.name} is declared as "${t.declared}" and DISAGREES with ${t.wantName}. ` +
        `Two tokens for one quality is how a wrong colour survives a rename: delete ${t.name} ` +
        `and paint from ${t.wantName}, or make it var(${t.wantName}).`).toBe(t.want);
    }
    /* non-vacuity: the counterpart tokens must actually exist, or this whole test measured air */
    const live = await page.evaluate(() => {
      const Q: any = (window as any).__q28;
      return ['--q-unique', '--q-set', '--q-magic', '--q-rare', '--q-orange', '--rune']
        .map((v) => ({ v, c: Q.paint(v) }));
    });
    console.log('1 · live palette: %s', JSON.stringify(live));
    for (const t of live) expect(t.c, `${t.v} must be defined on :root`).toBeTruthy();

    /* --q-runeword is the token a completed runeword's NAME paints from. The game gives it the
       SAME gold as a unique, so it must resolve identically — a token that merely LOOKS related is
       the second-palette bug wearing a new name. */
    const rw = await page.evaluate(() => {
      const Q: any = (window as any).__q28;
      return { declared: Q.raw('--q-runeword'), got: Q.paint('--q-runeword'), gold: Q.paint('--q-unique') };
    });
    console.log('1 · --q-runeword: %s', JSON.stringify(rw));
    if (rw.declared) {
      expect(rw.got, '--q-runeword must resolve to the same gold as --q-unique — a runeword name ' +
        'is painted exactly like a unique in game').toBe(rw.gold);
    }
  });
});

/* ════════════════════════════════════════════════════════════════════════════════════════════
   2 — THE JS MAP MATCHES THE CSS.  _Q_HEX paints inline styles all over the board; when it drifts
       from :root the SAME item is one colour in a table cell and another in a tile.
   ════════════════════════════════════════════════════════════════════════════════════════════ */
test.describe('v1628 · 2 — _Q_HEX agrees with the CSS tokens', () => {
  test('★★★ every _Q_HEX entry resolves to its token — rw is the unique gold, rune is --rune', async ({ page }) => {
    await board(page);
    const r = await page.evaluate(() => {
      const Q: any = (window as any).__q28;
      let M: any = null;
      try { M = (0, eval)('_Q_HEX'); } catch (e) { M = (window as any)._Q_HEX || null; }
      if (!M) return { missing: true, rows: [] as any[] };
      /* rw = a COMPLETED RUNEWORD's NAME, which the game paints the same gold as a unique.
         rune = a RUNE ITEM (El, Eld), which is --rune. They are different concepts. */
      const WANT: Record<string, string> = {
        unique: '--q-unique', set: '--q-set', rare: '--q-rare', magic: '--q-magic',
        crafted: '--q-orange', rune: '--rune', rw: '--q-unique',
      };
      const rows = Object.keys(WANT).map((k) => ({
        key: k, token: WANT[k], declared: M[k] || '',
        got: M[k] ? Q.paintRaw(M[k]) : '', want: Q.paint(WANT[k]),
      }));
      return { missing: false, rows };
    });
    console.log('2 · _Q_HEX vs tokens: %s', JSON.stringify(r.rows, null, 1));
    expect(r.missing, '_Q_HEX is not reachable — the map that paints half the board vanished').toBe(false);
    expect(r.rows.length, 'nothing measured').toBeGreaterThan(5);
    for (const row of r.rows) {
      expect(row.declared, `_Q_HEX.${row.key} is missing`).toBeTruthy();
      expect(row.got,
        `_Q_HEX.${row.key} = "${row.declared}" but var(${row.token}) paints ${row.want}. ` +
        `Paint from the token (getComputedStyle(root).getPropertyValue('${row.token}')), never a ` +
        `typed hex — that is exactly how set green sat one point off for months.`).toBe(row.want);
    }
  });
});

/* ════════════════════════════════════════════════════════════════════════════════════════════
   3 — THE THREE-WAY SPLIT RENDERS.  Runeword name / rune item / crafted item are three colours.
   ════════════════════════════════════════════════════════════════════════════════════════════ */
test.describe('v1628 · 3 — runeword ≠ rune ≠ crafted, on screen', () => {
  test('★★★ a runeword NAME is unique gold, a RUNE is --rune, a CRAFTED item is --q-orange, pairwise different', async ({ page }) => {
    /* .arw-name = an "all runewords" row name · .rs-name = a rune-saver rune · .cw-out-name = the
       craft workshop's OUTPUT item. All three currently share one class colour; that fusion is the
       finding. Each is located by whichever tab owns it, so no tab id is hard-coded here. */
    await board(page);
    await page.evaluate(FIND_TAB);
    const probe = await page.evaluate(async () => {
      const Q: any = (window as any).__q28;
      const W: any = window;
      const SPEC = [
        { what: 'runeword name', sel: '.arw-name', token: '--q-unique' },
        { what: 'rune item',     sel: '.rs-name',  token: '--rune' },
        { what: 'crafted item',  sel: '.cw-out-name', token: '--q-orange' },
      ];
      const out: any[] = [];
      for (const s of SPEC) {
        const tab = W.__tabOf(s.sel);
        if (tab) { try { W.switchTab(tab); } catch (e) {} await new Promise((r) => setTimeout(r, 700)); }
        const el: any = document.querySelector(s.sel);
        out.push({ ...s, tab, found: !!el, text: el ? (el.textContent || '').trim().slice(0, 40) : '',
                   got: el ? Q.colorOf(el) : '', want: Q.paint(s.token) });
      }
      return out;
    });
    console.log('3 · three-way split: %s', JSON.stringify(probe, null, 1));
    for (const p of probe) {
      expect(p.found, `no ${p.what} rendered anywhere (${p.sel}) — nothing measured`).toBe(true);
      expect(p.got,
        `${p.what} "${p.text}" computes ${p.got} but must be var(${p.token}) = ${p.want}`).toBe(p.want);
    }
    /* the outcome Konyo sees: three DIFFERENT colours. Asserted on the tokens too, so a future
       palette edit that collapses two of them into one also goes red here. */
    const [rw, rune, craft] = probe.map((p: any) => p.want);
    expect(rw, 'runeword gold and rune orange collapsed into one colour').not.toBe(rune);
    expect(rw, 'runeword gold and crafted orange collapsed into one colour').not.toBe(craft);
    expect(rune, 'rune orange and crafted orange collapsed into one colour').not.toBe(craft);
  });
});

/* ════════════════════════════════════════════════════════════════════════════════════════════
   4 — LEGEND CHIPS.  The legend is the board's own claim about the palette; if it lies, every
       reader learns the wrong colour. bible.html:8348 ships six chips with TYPED hexes, one of
       which fuses "runeword · rune · crafted" into a single swatch.
   ════════════════════════════════════════════════════════════════════════════════════════════ */
test.describe('v1628 · 4 — the legend tells the truth', () => {
  test('★★★ each legend chip paints its own token, and runeword/rune/crafted are THREE chips', async ({ page }) => {
    await board(page);
    const r = await page.evaluate(() => {
      const Q: any = (window as any).__q28;
      /* getComputedStyle resolves `color` on a display:none subtree, so the legend does not have to
         be popped open for this measurement — but read the chips wherever they live. */
      const chips = Array.from(document.querySelectorAll<any>('.tlg-chip')).map((c: any) => ({
        text: (c.textContent || '').trim().toLowerCase(),
        color: getComputedStyle(c).color,
        cvar: (c.style.getPropertyValue('--c') || '').trim(),
      }));
      const T = (v: string) => Q.paint(v);
      return { chips, tok: {
        unique: T('--q-unique'), set: T('--q-set'), magic: T('--q-magic'), rare: T('--q-rare'),
        crafted: T('--q-orange'), rune: T('--rune'), base: T('--q-normal'),
      } };
    });
    console.log('4 · legend chips: %s\n4 · tokens: %s', JSON.stringify(r.chips, null, 1), JSON.stringify(r.tok));
    expect(r.chips.length, 'no legend chips found — nothing measured').toBeGreaterThan(3);

    const find = (re: RegExp) => r.chips.filter((c: any) => re.test(c.text));
    const one = (re: RegExp, label: string) => {
      const hits = find(re);
      expect(hits.length, `expected exactly one "${label}" chip, got ${hits.length}: ${JSON.stringify(hits.map((h: any) => h.text))}`).toBe(1);
      return hits[0];
    };

    /* (a) every chip that names a quality paints that quality's TOKEN */
    const PAIRS: Array<[RegExp, string, keyof typeof r.tok]> = [
      [/^unique$/, 'unique', 'unique'],
      [/^set$/, 'set', 'set'],
      [/^magic$/, 'magic', 'magic'],
      [/^rare$/, 'rare', 'rare'],
      [/^base$/, 'base', 'base'],
    ];
    for (const [re, label, key] of PAIRS) {
      const c = one(re, label);
      expect(c.color, `legend chip "${label}" paints ${c.color} (declared --c:${c.cvar}) but the ` +
        `board paints that quality ${r.tok[key]} — the legend must read the token, not a typed hex`).toBe(r.tok[key]);
    }

    /* (b) THREE chips, not one fused swatch. The fused chip reads "runeword · rune · crafted". */
    const fused = find(/runeword.*rune.*crafted|rune.*·.*crafted/);
    expect(fused.length,
      `the legend fuses runeword/rune/crafted into ONE swatch (${JSON.stringify(fused.map((f: any) => f.text))}). ` +
      `They are three different in-game colours — a completed runeword's name is the unique gold, ` +
      `a rune item is --rune, a crafted item is --q-orange. Split it into three chips.`).toBe(0);
    const rwChip = one(/^runeword$/, 'runeword');
    const runeChip = one(/^rune$/, 'rune');
    const craftChip = one(/^crafted$/, 'crafted');
    expect(rwChip.color, 'the runeword legend chip must be the unique gold').toBe(r.tok.unique);
    expect(runeChip.color, 'the rune legend chip must be --rune').toBe(r.tok.rune);
    expect(craftChip.color, 'the crafted legend chip must be --q-orange').toBe(r.tok.crafted);
  });
});

/* ════════════════════════════════════════════════════════════════════════════════════════════
   5 — ICONS DECODE.  Every <img> carries onerror="this.remove()", so a wrong path fails SILENTLY
       as a tidy label: an existence assertion proves NOTHING. Measure naturalWidth.
   ════════════════════════════════════════════════════════════════════════════════════════════ */
test.describe('v1628 · 5 — markup does not count, decoding does', () => {
  /* funi + fsets paint art on plain tab activation, so they can be demanded. #tab-forge renders
     ZERO <img> from a bare switchTab (measured: 0 visible images, 0 broken) — it needs a sub-view
     driven first. Demanding art there would be a red about this harness, not about the product,
     and passing on zero images would be a vacuous green. It is measured and reported as NOT
     ESTABLISHED below rather than asserted either way. */
  for (const tab of ['funi', 'fsets'] as const) {
    test(`★★★ every rendered <img> on #tab-${tab} decodes (naturalWidth > 0)`, async ({ page }) => {
      await board(page, tab);
      await eagerLoadArt(page, '#tab-' + tab);
      const r = await page.evaluate((t: string) => {
        const host = document.getElementById('tab-' + t);
        if (!host) return { missing: true, total: 0, bad: [] as any[] };
        const imgs = Array.from(host.querySelectorAll<any>('img'))
          .filter((i: any) => i.offsetParent !== null || i.getClientRects().length > 0);
        return { missing: false, total: imgs.length,
          bad: imgs.filter((i: any) => !(i.naturalWidth > 0))
                   .slice(0, 12)
                   .map((i: any) => ({ src: i.getAttribute('src'), alt: i.getAttribute('alt') || '',
                                       onerr: !!i.getAttribute('onerror') })) };
      }, tab);
      console.log('5 · #tab-%s: %d visible imgs, %d broken %s', tab, r.total, r.bad.length, JSON.stringify(r.bad));
      expect(r.missing, `#tab-${tab} does not exist`).toBe(false);
      expect(r.total, `#tab-${tab} rendered ZERO images — this assertion would prove nothing`).toBeGreaterThan(0);
      expect(r.bad, `broken art on #tab-${tab}. onerror="this.remove()" hides these from any ` +
        `existence check; only naturalWidth catches them.`).toEqual([]);
    });
  }

  test('★★ #tab-forge art decodes — the view is DRIVEN so this cannot skip', async ({ page }) => {
    await board(page, 'forge');
    /* v1723 — WAS "IF it renders any", AND IT NEVER RENDERED ANY. His chronicle is complete
       (all 99 runewords seeded made), so forgeScan returns zero tiles and a bare switchTab draws
       no art at all — the check printed NOT ESTABLISHED and asserted nothing, in either
       direction, on every run. Drive an EMPTY chronicle so the Forge actually has cards to draw,
       which is the only state where "does the art decode" is a question with an answer. */
    await pinEvaluate(page, () => {
      const w: any = window;
      w.LSR.setItem('d2r_rwProfile', 'fresh');
      w.LSR.setItem('d2r_rwMade', '{}');
      w.LSR.setItem('d2r_rwUnmade', '{}');
    });
    await reloadPinned(page);
    await page.waitForTimeout(1800);
    await page.evaluate(() => {
      const w: any = window;
      w.switchTab && w.switchTab('forge');
      w._FORGE_VIEW = 'onestep';
      try { w.renderForge && w.renderForge(); } catch (e) {}
    });
    await page.waitForTimeout(600);
    await eagerLoadArt(page, '#tab-forge');
    const r = await page.evaluate(() => {
      const host = document.getElementById('tab-forge');
      if (!host) return { total: 0, bad: [] as any[] };
      const imgs = Array.from(host.querySelectorAll<any>('img')).filter((i: any) => i.getClientRects().length > 0);
      return { total: imgs.length,
        bad: imgs.filter((i: any) => !(i.naturalWidth > 0)).slice(0, 12).map((i: any) => i.getAttribute('src')) };
    });
    console.log('5 · #tab-forge: %d visible imgs, %d broken %s', r.total, r.bad.length, JSON.stringify(r.bad));
    expect(r.total, 'the Forge drew no art even with an empty chronicle — the view was not driven, ' +
      'so this check would be asserting nothing').toBeGreaterThan(0);
    expect(r.bad, 'broken art on #tab-forge').toEqual([]);
  });

  test('★★ boss-card art on the calculator decodes too', async ({ page }) => {
    await board(page);
    /* v1723 — a boss card is not on screen from a bare load, so this printed NOT ESTABLISHED and
       asserted nothing. Open one; then the question has an answer. */
    await page.evaluate(() => {
      const w: any = window;
      w.switchTab && w.switchTab('bosses');
      try { w.openBossDetail && w.openBossDetail('mephisto'); } catch (e) {}
    });
    await page.waitForTimeout(800);
    await eagerLoadArt(page, 'body');
    const r = await page.evaluate(() => {
      const imgs = Array.from(document.querySelectorAll<any>('.boss-card img, .boss-art img, [data-art-logo] > img'))
        .filter((i: any) => i.getClientRects().length > 0);
      return { total: imgs.length,
        bad: imgs.filter((i: any) => !(i.naturalWidth > 0)).slice(0, 10)
                 .map((i: any) => i.getAttribute('src')) };
    });
    console.log('5 · boss/anchor art: %d visible, %d broken %s', r.total, r.bad.length, JSON.stringify(r.bad));
    expect(r.total, 'no boss-card art visible even after opening Mephisto — subject not established')
      .toBeGreaterThan(0);
    expect(r.bad, 'boss art that does not decode').toEqual([]);
  });
});

/* ════════════════════════════════════════════════════════════════════════════════════════════
   6 — NO ARBITRARY PICTURE.  v1624's bug was art(items[0].name): whichever item sorted first.
       A thumbnail must name something actually IN its group, or render nothing at all.
   ════════════════════════════════════════════════════════════════════════════════════════════ */
test.describe('v1628 · 6 — a thumbnail names something in its own group', () => {
  test('★★★ every F·Uniques run thumbnail resolves to a name the card itself contains', async ({ page }) => {
    await board(page, 'funi');
    await eagerLoadArt(page, '#tab-funi');
    const r = await page.evaluate(() => {
      const cards = Array.from(document.querySelectorAll<any>('#tab-funi .f-card')).slice(0, 12);
      return cards.map((c: any) => {
        const a: any = c.querySelector('.f-runart');
        const img: any = a?.querySelector('img');
        return {
          kind: c.classList.contains('f-pipe') ? 'best-run' : (c.classList.contains('f-step') ? 'quick-win' : 'other'),
          /* v1636 moved the BOSS thumbnail from `data-art-logo` to `data-boss-tip`, which carries
             the boss ID ("mephisto", "pindle"). Reading only data-art-logo made every run card
             look like it had NO resolvable subject while showing a perfectly correct portrait —
             so this fired the v1624 arbitrary-picture alarm at art that was never arbitrary.
             The identity check below still holds for either: a run card titled "Run Hell
             Mephisto" contains "mephisto", so an arbitrary picture would still be caught. */
          logo: a?.getAttribute('data-art-logo') || a?.getAttribute('data-boss-tip') || null,
          /* v1721 — the BOSSES roster's own display name for that id, so the identity check can
             accept "Uber Diablo (Diablo Clone)" for `dclone` and "Hell Bovines" for `cows`. */
          displayName: (() => {
            const id = a?.getAttribute('data-boss-tip') || '';
            try {
              const w: any = window;
              const b = (w._allDropItems ? null : null);
              const hit = (w.BOSSES || []).find((x: any) => x.id === id);
              if (hit) return hit.name || '';
              const t = a?.getAttribute('title') || '';
              return t.split('—')[0].trim();          // "Mephisto — open the boss card"
            } catch (e) { return ''; }
          })(),
          hasImg: !!img,
          decoded: img ? img.naturalWidth > 0 : false,
          /* the group's own text: title + every item name the card lists */
          text: (c.textContent || '').replace(/\s+/g, ' ').toLowerCase(),
        };
      });
    });
    console.log('6 · %d cards; kinds %s', r.length, JSON.stringify(r.map((x: any) => x.kind)));
    expect(r.length, 'no F·Uniques cards rendered — nothing measured').toBeGreaterThan(2);
    for (const c of r) {
      if (!c.logo) {
        /* honest failure to resolve: render NOTHING, never a placeholder or a guess */
        expect(c.hasImg, 'a card with no resolvable subject still rendered an <img> — that is the ' +
          'arbitrary picture v1624 removed; render nothing instead').toBe(false);
        continue;
      }
      /* v1721 — THE ID IS NOT ALWAYS THE NAME ON THE CARD, and this is the third boss to prove it.
         v1717 already hit it on the sets board, where `cows` renders as "Hell Bovines"; here it is
         `dclone`, whose card reads "Run Normal Uber Diablo (Diablo Clone)". The picture is
         perfectly correct — the card simply never prints the internal id.
         It surfaced only now because v1721's Pindle correction re-ranked the runs and moved that
         card into the measured set for the first time: the gate was blind to input his own data
         had never produced. [[gate-blind-to-unexercised-input]]
         The check keeps its teeth — an arbitrary picture matches NEITHER the id nor the boss's
         display name, so "Run Hell Mephisto" wearing a Countess portrait still fails. */
      const idOrName = [String(c.logo).toLowerCase(), String(c.displayName || '').toLowerCase()]
        .filter(Boolean);
      expect(idOrName.some((v) => c.text.includes(v)),
        `thumbnail names "${c.logo}" (display "${c.displayName}") but neither appears in its own ` +
        `card — an arbitrary picture (the v1624 art(items[0].name) shape)`).toBe(true);
      expect(c.decoded, `"${c.logo}" thumbnail does not decode`).toBe(true);
    }
    /* non-vacuity: at least one card actually carried a thumbnail */
    expect(r.filter((c: any) => c.logo).length, 'not one card had a thumbnail to check').toBeGreaterThan(0);
  });

  test('★★★ the 🎯 give-up placeholder never renders — no card draws a target for "I could not resolve this"', async ({ page }) => {
    /* bible.html:34654 still keeps the v1624 shape as a FALLBACK: when _runBossArt returns null it
       renders art(items[0].name) with a 🎯 target glyph — an arbitrary picture for whichever item
       sorted first. The previous case cannot see it, because that branch emits no .f-runart and so
       no data-art-logo to disagree with. This one measures the give-up marker directly.
       A boss-specific EMOJI is a different thing and is allowed: that is an honest identity for a
       boss with no sprite. 🎯 means only "nothing resolved". */
    await board(page, 'funi');
    const r = await page.evaluate(() => {
      const glyphs = Array.from(document.querySelectorAll<any>('#tab-funi .f-artglyph'))
        .map((g: any) => (g.textContent || '').trim());
      const cards = document.querySelectorAll('#tab-funi .f-card').length;
      const withArt = document.querySelectorAll('#tab-funi .f-runart').length;
      return { cards, withArt, glyphs, targets: glyphs.filter((g: string) => g === '\u{1F3AF}').length };
    });
    console.log('6 · %d cards, %d with a .f-runart wrapper, glyphs %s, 🎯 placeholders %d',
      r.cards, r.withArt, JSON.stringify(r.glyphs), r.targets);
    expect(r.cards, 'no F·Uniques cards rendered — nothing measured').toBeGreaterThan(2);
    expect(r.targets,
      'a run card fell through to the 🎯 give-up placeholder over art(items[0].name) — the v1624 ' +
      'arbitrary picture. If nothing resolves honestly, render NOTHING.').toBe(0);
  });
});

/* ════════════════════════════════════════════════════════════════════════════════════════════
   7 — THE HOVER CARD IS BOUND.  bible.html:23040 refuses to bind an anchor wider than 430px (or
       taller than 120px). Wrap a whole row and there is no error — there is just no card.
       v1625 ITEM 5 measures this on F-SETS. This measures F-UNIQUES, the other half.
   ════════════════════════════════════════════════════════════════════════════════════════════ */
test.describe('v1628 · 7 — hovering a name raises its real card', () => {
  test('★★★ an F·Uniques item name is ≤430×120 and raises #arttip with its name and real stat text', async ({ page }) => {
    await board(page, 'funi');
    const SEL = '#tab-funi [data-arttip]';
    const before = await page.evaluate(() => {
      const t: any = document.getElementById('arttip');
      return { exists: !!t, on: t ? t.classList.contains('on') : false,
               n: document.querySelectorAll('#tab-funi [data-arttip]').length };
    });
    console.log('7 · %d hover anchors on F·Uniques; card up before hover = %s', before.n, before.on);
    expect(before.n, 'no [data-arttip] anchors on F·Uniques — nothing measured').toBeGreaterThan(0);
    expect(before.on, 'the card was already up before we hovered — the measurement would be vacuous').toBe(false);

    /* (a) the anchor is inside the binder's size gate — measure BEFORE hovering, so a "wrap the
           whole row" regression is reported as itself rather than as a mysterious missing card */
    const geom = await page.evaluate((sel: string) => {
      const els = Array.from(document.querySelectorAll<any>(sel))
        .filter((e: any) => e.getClientRects().length > 0).slice(0, 8);
      return els.map((e: any) => { const r = e.getBoundingClientRect();
        return { name: e.getAttribute('data-arttip'), w: Math.round(r.width), h: Math.round(r.height) }; });
    }, SEL);
    console.log('7 · anchor geometry: %s', JSON.stringify(geom));
    expect(geom.length, 'no VISIBLE hover anchor to measure').toBeGreaterThan(0);
    for (const g of geom) {
      expect(g.w, `anchor for "${g.name}" is ${g.w}px wide; the board's hover binding REFUSES ` +
        `anything over 430px, so this card is silently disabled. Wrap the NAME, not the row.`).toBeLessThanOrEqual(430);
      expect(g.h, `anchor for "${g.name}" is ${g.h}px tall; the binding refuses over 120px`).toBeLessThanOrEqual(120);
    }

    /* (b) it actually opens, carrying that item's own name and a real stat block */
    const want = geom[0].name;
    await page.locator(SEL).first().hover();
    /* v1787 — POLL, DO NOT SNAPSHOT AT A FIXED DELAY. v1717 diagnosed this exact race in
       v1625 and fixed it THERE only: the card is raised by a delegated hover handler and
       `.on` is a transition class, so a single read at a fixed delay passes in one run and
       fails in the next. It cost two consecutive red Routine I runs on shard 3/6, on commits
       that changed no page code at all. Same defect, same remedy, applied to the class. The
       assertion below stays exactly as strict: if the card never comes up, this still goes red. */
    /* 2026-08-19 — 4s was not enough on a loaded CI runner. This test failed on two consecutive
       shard-3 runs and then PASSED on a re-run with no code change between, which is the
       definition of a flake and cost two full suite cycles to establish. The assertion is
       untouched and exactly as strict: if the card never comes up, this still goes red. Only the
       patience changes — the same argument v1717 made when it replaced a fixed 900ms snapshot
       with polling in the first place. A gate that cries wolf is on its way to being ignored. */
    await page.waitForFunction(() => {
          const t = document.getElementById('arttip');
          return !!t && t.classList.contains('on');
        }, null, { timeout: 12000 }).catch(() => {});
    const after = await page.evaluate(() => {
      const t: any = document.getElementById('arttip');
      if (!t) return { exists: false, on: false, name: '', desc: 0, imgDecoded: null as any };
      const img: any = t.querySelector('img');
      return { exists: true, on: t.classList.contains('on'),
               name: (t.querySelector('.att-name') as any)?.textContent?.trim() || '',
               desc: ((t.textContent || '').trim().length),
               imgDecoded: img ? img.naturalWidth > 0 : null };
    });
    console.log('7 · after hovering "%s": %s', want, JSON.stringify(after));
    expect(after.exists, 'no #arttip element exists at all').toBe(true);
    expect(after.on, `hovering "${want}" raised no card — check the 430px anchor guard`).toBe(true);
    expect(after.name.toLowerCase(), `the card came up naming something other than "${want}"`)
      .toContain(String(want).toLowerCase().slice(0, 12));
    expect(after.desc, 'the card came up with no stat text — an empty tooltip is a missing tooltip').toBeGreaterThan(40);
    if (after.imgDecoded !== null) {
      expect(after.imgDecoded, 'the hover card rendered an <img> that does not decode').toBe(true);
    }
  });

  test('★★★ a BOSS name wears boss art that decodes, and routes to its boss card', async ({ page }) => {
    await board(page, 'funi');
    const r = await page.evaluate(() => {
      const W: any = window;
      /* v1723 — THIS SELECTOR WENT STALE AT v1636 AND THE TEST HAS BEEN VACUOUS EVER SINCE.
         v1636 gave the run thumbnail `data-boss-tip` (the boss id) in place of `data-art-logo`
         (the display name) — the sibling spec v1625 documents exactly that swap. This one kept
         querying the old attribute, found nothing, printed "NOT ESTABLISHED" and RETURNED, so
         every assertion below it has been unreached for ~90 versions. A gate that always skips is
         a gate that never runs. Accept either attribute, and make absence a FAILURE. */
      const a: any = document.querySelector(
        '#tab-funi .f-card.f-pipe .f-runart[data-art-logo], #tab-funi .f-card.f-pipe .f-runart[data-boss-tip]');
      if (!a) return { found: false };
      const img: any = a.querySelector('img');
      const rect = a.getBoundingClientRect();
      const name = a.getAttribute('data-art-logo') || a.getAttribute('data-boss-tip');
      /* the resolver must answer for this boss honestly, not fall back to a glyph-for-anything */
      let resolved: any = null;
      try { resolved = W._runBossArt ? W._runBossArt(null, name) : null; } catch (e) {}
      return { found: true, name, hasImg: !!img, decoded: img ? img.naturalWidth > 0 : false,
               w: Math.round(rect.width), h: Math.round(rect.height),
               route: a.getAttribute('onclick') || '',
               routable: typeof W.openBossDetail === 'function',
               resolvedUrl: resolved ? (resolved.url || '') : '' };
    });
    console.log('7 · boss anchor: %s', JSON.stringify(r));
    /* v1723 — was `return` (a silent pass). The board always renders best-run cards on his data,
       so an absent anchor means the selector has drifted again, which is the very thing that hid
       this check for ~90 versions. Fail, and say what to look at. */
    expect(r.found, 'no best-run boss anchor rendered — has the thumbnail attribute changed again? ' +
      '(v1636 moved data-art-logo -> data-boss-tip; this test read the old one until v1723)').toBe(true);
    expect(r.hasImg, `boss "${r.name}" renders no art`).toBe(true);
    expect(r.decoded, `boss "${r.name}" art does not decode — onerror hid it as a tidy label`).toBe(true);
    expect(r.w, 'the boss anchor is over the 430px hover gate').toBeLessThanOrEqual(430);
    expect(r.routable, 'openBossDetail is not a function — the boss name routes nowhere').toBe(true);
    expect(r.route, `boss "${r.name}" must open its boss card`).toContain('openBossDetail');
  });
});
