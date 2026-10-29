import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';

/* v1625 — THE IN-GAME QUALITY PALETTE, ON THE BOARD.  (owner A = bible.html; this file proves it)
 *
 * Konyo, from live screenshots:
 *   ITEM 2 "for crafts inpurple it can be changed to match the orange line ingame in diablo ii"
 *   ITEM 3 the Chronicle Sealed buttons / the F-Uniques FOUND log / F-Sets names vs titles
 *   ITEM 5 "the item needs to be matching the ingame green set colored.. and clickable and
 *          routable and tooltip floating image HD art0r ... just like the rest of the console is"
 *   ITEM 6 "the title name itself needs the image art0r too within and next to the title name"
 *
 * TWO RULES THIS FILE EXISTS TO ENFORCE, both paid for already:
 *
 *  (a) EVERY expected colour is resolved from the LIVE document's own :root --q-* custom property
 *      and painted onto a probe node, so the expectation is whatever the palette says today.
 *      v1622 shipped --rar-unique as #f0c060 (the console's own chrome gold) and three tests waved
 *      it through because they asserted a CLASS EXISTED. Nothing here asserts a class. The only
 *      literal hexes in this file are the two purples we are BANNING and the four v1621 CRAFT GEM
 *      colours we are FREEZING — a guard rail has to name the thing it guards.
 *
 *  (b) The 430px hover guard (bible.html:23040 — `if (_rr.width > 430 || _rr.height > 120) return`)
 *      silently REFUSES to bind a card to an oversized anchor. Wrap a whole row and you do not get
 *      an error, you get no hover card at all. Every anchor this file blesses is measured.
 */

const URL = 'file://' + path.resolve(__dirname, '..', process.env.BIBLE_FILE || 'bible.html');

/* the two purples ITEM 2 must move OFF — .ft-craft .ft-ct #c79ce6 and the --acc-rotw #b58cff */
const PURPLE_CT   = 'rgb(199, 156, 230)';
const PURPLE_ROTW = 'rgb(181, 140, 255)';

/* v1621 CRAFT GEM colours. These are the GEMS (amethyst/ruby/emerald/sapphire), NOT the craft
   quality — the one thing the purple sweep must not touch. Literal by design: this assertion's
   whole job is to notice if someone edits them. */
const GEM = {
  Caster:      'rgb(180, 140, 224)',   // #b48ce0 amethyst
  Blood:       'rgb(224, 85, 106)',    // #e0556a ruby
  Safety:      'rgb(95, 208, 122)',    // #5fd07a emerald
  'Hit Power': 'rgb(91, 143, 240)',    // #5b8ff0 sapphire
};

/* ── page-side toolkit, installed once per page ───────────────────────────────────────────────
   paint(v)   resolve a :root custom property to the rgb() string the browser would actually paint
   bgOf(el)   first non-transparent painted background walking up the tree
   ratio(a,b) WCAG contrast, so a "readable" claim carries a number instead of an adjective       */
const TOOLKIT = `
  window.__q = (function(){
    var probe = document.createElement('div');
    probe.style.cssText = 'position:absolute;left:-9999px;top:-9999px';
    document.body.appendChild(probe);
    function paintRaw(css){ probe.style.color='rgb(1,2,3)'; probe.style.color = css; return getComputedStyle(probe).color; }
    function paint(v){ return paintRaw(getComputedStyle(document.documentElement).getPropertyValue(v).trim()); }
    function parse(c){ var m=String(c).match(/-?[\\d.]+/g)||[]; return [ +m[0]||0, +m[1]||0, +m[2]||0, m.length>3?+m[3]:1 ]; }
    function bgOf(el){
      for (var n=el; n && n.nodeType===1; n=n.parentElement){
        var b = getComputedStyle(n).backgroundColor, p = parse(b);
        if (p[3] > 0.5) return b;
      }
      return getComputedStyle(document.body).backgroundColor || 'rgb(10,8,5)';
    }
    function lum(c){
      var p = parse(c);
      var f = p.slice(0,3).map(function(v){ v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055,2.4); });
      return 0.2126*f[0] + 0.7152*f[1] + 0.0722*f[2];
    }
    function ratio(a,b){ var x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); }
    return { paint:paint, paintRaw:paintRaw, bgOf:bgOf, ratio:ratio,
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

/* Re-seed a namespaced localStorage key. _D2R_PFX is '' for Konyo's own machine but 'I·<id>·' for a
   never-chosen profile like this one (bible.html:3526) — write BOTH or the seed lands in a world the
   app never reads, and every colour assertion downstream passes over an empty bar. */
async function seedAndReload(page: any, entries: Record<string, any>, tab: string) {
  await pinEvaluate(page, (e: any) => {
    const pfx = (window as any)._D2R_PFX || '';
    for (const k of Object.keys(e)) {
      const v = JSON.stringify(e[k]);
      try { localStorage.setItem(k, v); } catch (err) {}
      if (pfx) { try { localStorage.setItem(pfx + k, v); } catch (err) {} }
    }
  }, entries);
  await reloadPinned(page);
  await page.waitForTimeout(2800);
  await page.evaluate(TOOLKIT);
  await page.evaluate((t: string) => { try { (window as any).switchTab(t); } catch (e) {} }, tab);
  await page.waitForTimeout(1800);
}

/* ════════════════════════════════════════════════════════════════════════════════════════════
   ITEM 2 — CRAFTS ARE ORANGE, NOT PURPLE
   ════════════════════════════════════════════════════════════════════════════════════════════ */
test.describe('v1625 · ITEM 2 — the CRAFTS chip is D2 orange', () => {
  /* v2094 MOVED THE CHIP, NOT THE COLOUR. Crafts left the Forge for a room of their own, and v2096
     stopped the Forge drawing a ⚗️ chip for crafts it no longer holds (bible.html:38102 renders it
     only when `_isCrafts`). So the element this test measures now exists at #tab-crafts, reached by
     switchTab('crafts') — which renders on entry via window.renderCrafts (bible.html:26762).
     The stylesheet never forked: every rule below is scoped
     `:is(#tab-forge,#tab-crafts,#tab-funi,#tab-fsets) .forge-tab.ft-craft` (bible.html:7745-7763),
     so the orange this test pins is the same declaration it always was. */
  test('★★★ .forge-tab.ft-craft computes --q-orange, resting AND lit, and has left the purple family', async ({ page }) => {
    await board(page, 'crafts');
    const r = await page.evaluate(() => {
      const Q: any = (window as any).__q;
      const chip: any = document.querySelector('#tab-crafts .forge-tab.ft-craft');
      if (!chip) return { missing: true };
      const ct: any = chip.querySelector('.ft-ct');
      const rest = { chip: Q.colorOf(chip), ct: ct ? Q.colorOf(ct) : null };
      /* read the .on rule off the LIVE element — the filter may or may not be selectable
         depending on whether crafts are queued, and the CSS is what we are asserting about */
      const had = chip.classList.contains('on');
      chip.classList.add('on');
      const lit = { chip: Q.colorOf(chip), ct: ct ? Q.colorOf(ct) : null,
                    bg: Q.bgOf(chip), border: getComputedStyle(chip).borderTopColor };
      if (!had) chip.classList.remove('on');
      return { missing: false, orange: Q.paint('--q-orange'), rest, lit,
               litRatio: Q.ratio(lit.chip, lit.bg) };
    });
    expect(r.missing, 'no CRAFTS chip rendered in the Crafts room — nothing to colour').toBe(false);
    console.log('ITEM 2 · resting chip=%s ct=%s | lit chip=%s ct=%s border=%s | --q-orange=%s | lit contrast=%s:1',
      r.rest!.chip, r.rest!.ct, r.lit!.chip, r.lit!.ct, r.lit!.border, r.orange, r.litRatio!.toFixed(2));

    // resting: the chip label and its count badge both carry the craft quality
    expect(r.rest!.chip, 'resting CRAFTS chip label').toBe(r.orange);
    expect(r.rest!.ct,   'resting CRAFTS count badge (.ft-ct — the purple at bible.html:7393)').toBe(r.orange);

    // lit: .on whitens the badge by design (7396), so the QUALITY lives on the chip + its border
    expect(r.lit!.chip,   'lit CRAFTS chip label (.ft-craft.on — bible.html:7401)').toBe(r.orange);
    expect(r.lit!.border, 'lit CRAFTS chip border must carry the quality too').not.toBe('rgba(0, 0, 0, 0)');

    // and explicitly OFF the two purples
    for (const [where, c] of [['resting chip', r.rest!.chip], ['resting badge', r.rest!.ct],
                              ['lit chip', r.lit!.chip], ['lit badge', r.lit!.ct]] as any[]) {
      expect(c, `${where} still purple (#c79ce6)`).not.toBe(PURPLE_CT);
      expect(c, `${where} still purple (--acc-rotw #b58cff)`).not.toBe(PURPLE_ROTW);
    }
    expect(r.litRatio, 'the lit CRAFTS chip must stay legible').toBeGreaterThanOrEqual(4.5);
  });

  test('★★ GUARD RAIL — the four v1621 CRAFT GEM colours are untouched by the purple sweep', async ({ page }) => {
    await board(page, 'forge');
    const g = await page.evaluate((GEMS: any) => {
      const Q: any = (window as any).__q;
      /* the gems are painted through --cw-c on every craft surface (#arttip .att-craft, the
         workshop tiles, the forge craft atoms). Resolve each craft's colour the way the page
         does, then paint it, so we compare rgb to rgb. */
      const out: any = {};
      const src = document.documentElement.innerHTML;
      for (const name of Object.keys(GEMS)) out[name] = null;
      /* every node that carries an explicit --cw-c, grouped by the craft it names */
      const nodes = Array.from(document.querySelectorAll<any>('[style*="--cw-c"]'));
      for (const n of nodes) {
        const c = Q.paintRaw(n.style.getPropertyValue('--cw-c').trim());
        const txt = (n.textContent || '') + ' ' + (n.getAttribute('title') || '');
        for (const name of Object.keys(GEMS)) if (txt.indexOf(name) >= 0 && !out[name]) out[name] = c;
      }
      return { out, litNodes: nodes.length, hasSrc: src.length > 0 };
    }, GEM);
    const found = Object.entries(g.out).filter(([, v]) => v);
    console.log('GUARD RAIL · %d nodes carry --cw-c; resolved %d/4 craft gems: %s',
      g.litNodes, found.length, JSON.stringify(g.out));
    /* NON-VACUOUS: if the Forge is rendering no craft surfaces at all this proves nothing, and
       saying so is the honest outcome — but at least one must resolve or the guard is asleep. */
    expect(found.length, 'no craft surface carried --cw-c — the gem guard rail measured nothing').toBeGreaterThan(0);
    for (const [name, c] of found) expect(c, `${name} craft GEM colour changed`).toBe((GEM as any)[name]);
  });
});

/* ════════════════════════════════════════════════════════════════════════════════════════════
   ITEM 3 — THE REMAINING QUALITY SURFACES
   ════════════════════════════════════════════════════════════════════════════════════════════ */
test.describe('v1625 · ITEM 3 — sealed card, found log, set names vs set titles', () => {
  test('★★★ the Chronicle Sealed card\'s three buttons carry Crafts=orange, F·Uniques=unique, F·Sets=set — each ≥4.5:1', async ({ page }) => {
    await board(page, 'forge');
    /* The sealed card only exists once every runeword is ✓ created (bible.html:33321 _madeRw).
       A fresh Playwright profile has an empty chronicle, so we SEAL it the way the app does —
       through d2r_rwMade — and reload. Format is an object map (Object.keys(rwMade)); we try the
       map first and fall back to an array so a format drift reports as a format drift. */
    const names = await page.evaluate(() => {
      try { return Object.keys((0, eval)('RUNEWORD_TIP')); } catch (e) { return []; }
    });
    expect(names.length, 'no RUNEWORD_TIP catalog — cannot seal the chronicle').toBeGreaterThan(50);
    const map: any = {}; for (const n of names) map[n] = '2026-08-03';

    await seedAndReload(page, { d2r_rwMade: map }, 'forge');
    let btns = await page.evaluate(() => document.querySelectorAll('#tab-forge .forge-sealed .fs-btn').length);
    if (!btns) { await seedAndReload(page, { d2r_rwMade: names }, 'forge');
                 btns = await page.evaluate(() => document.querySelectorAll('#tab-forge .forge-sealed .fs-btn').length); }
    expect(btns, 'the Chronicle Sealed card did not render after sealing d2r_rwMade — seed format drift').toBeGreaterThanOrEqual(2);

    const r = await page.evaluate(() => {
      const Q: any = (window as any).__q;
      return {
        want: { orange: Q.paint('--q-orange'), unique: Q.paint('--q-unique'), set: Q.paint('--q-set') },
        btns: Array.from(document.querySelectorAll<any>('#tab-forge .forge-sealed .fs-btn')).map((b) => ({
          text: (b.textContent || '').trim(), color: Q.colorOf(b),
          bg: Q.bgOf(b), ratio: Q.ratio(Q.colorOf(b), Q.bgOf(b)),
        })),
      };
    });
    for (const b of r.btns) console.log('ITEM 3 · sealed btn "%s" color=%s on bg=%s → %s:1', b.text, b.color, b.bg, b.ratio.toFixed(2));

    const pick = (frag: string) => r.btns.find((b: any) => b.text.toLowerCase().includes(frag));
    const crafts = pick('craft'), uni = pick('uniques'), sets = pick('sets');
    if (crafts) { expect(crafts.color, 'sealed ⚗️ Crafts button').toBe(r.want.orange);
                  expect(crafts.color, 'sealed Crafts still purple').not.toBe(PURPLE_ROTW); }
    expect(uni,  'sealed card has no F·Uniques button').toBeTruthy();
    expect(sets, 'sealed card has no F·Sets button').toBeTruthy();
    expect(uni!.color,  'sealed 🏆 F·Uniques button').toBe(r.want.unique);
    expect(sets!.color, 'sealed 🧩 F·Sets button').toBe(r.want.set);
    for (const b of r.btns) expect(b.ratio, `"${b.text}" is unreadable on its own painted background`).toBeGreaterThanOrEqual(4.5);
  });

  test('★★ the F-Uniques FOUND log rows carry the unique colour', async ({ page }) => {
    await board(page, 'funi');
    /* seed a real unique into the chronicle so the FOUND ledger is non-empty — a found-log test
       run against an empty ledger is exactly the vacuous proof this project keeps paying for */
    const uniName = await page.evaluate(() => {
      const b: any = document.querySelector('#tab-funi .f-card.f-step b.f-rwbig[data-arttip]')
                  || document.querySelector('#tab-funi b.f-rwbig[data-arttip]');
      return b ? (b.getAttribute('data-arttip') || b.textContent || '').trim() : '';
    });
    expect(uniName, 'could not read a real unique name off the F-Uniques board').toBeTruthy();

    await seedAndReload(page, { d2r_foundLog: { [uniName]: '2026-08-03' } }, 'funi');
    await page.evaluate(() => { try { (window as any).forgeUniSetFilter && (window as any).forgeUniSetFilter('done'); } catch (e) {} });
    await page.waitForTimeout(900);

    const r = await page.evaluate((n: string) => {
      const Q: any = (window as any).__q;
      const rows = Array.from(document.querySelectorAll<any>('#tab-funi .gf-chip[data-arttip]'));
      const hit = rows.find((c) => (c.getAttribute('data-arttip') || '') === n) || rows[0];
      if (!hit) return { rows: 0 };
      /* the chip is [tick button][art][NAME span][qlvl span] (bible.html:34507) — 'span:not(.gq)'
         grabs the tick's own inner span and measures the ✓, not the item. Take the span that
         actually says the item's name. */
      const want = (hit.getAttribute('data-arttip') || '').trim();
      const nameEl: any = Array.from(hit.querySelectorAll<any>('span'))
        .find((s: any) => (s.textContent || '').trim() === want) || hit;
      return { rows: rows.length, name: (nameEl.textContent || '').trim(),
               color: Q.colorOf(nameEl), unique: Q.paint('--q-unique'), ratio: Q.ratio(Q.colorOf(nameEl), Q.bgOf(nameEl)) };
    }, uniName);
    console.log('ITEM 3 · FOUND log: %d chips, "%s" color=%s want --q-unique=%s (%s:1)',
      r.rows, r.name, r.color, r.unique, r.ratio ? r.ratio.toFixed(2) : '-');
    expect(r.rows, 'the FOUND ledger is empty — this assertion would prove nothing').toBeGreaterThan(0);
    expect(r.color, 'FOUND-log unique name must be the in-game unique tan, "like the calculator tab"').toBe(r.unique);
  });

  test('★★★ on F-Sets the PIECE names are set-green and the big TITLE names are NOT — both directions', async ({ page }) => {
    await board(page, 'fsets');
    const r = await page.evaluate(() => {
      const Q: any = (window as any).__q;
      const green = Q.paint('--q-set');
      /* a PIECE is a name with a data-arttip (it resolves to one item); a big TITLE is the SET
         name on a best-run / set card (bible.html:35240 — <b class="f-rwbig"> with no arttip) */
      const all = Array.from(document.querySelectorAll<any>('#tab-fsets b.f-rwbig'));
      const pieces = all.filter((b) => b.hasAttribute('data-arttip'));
      const titles = all.filter((b) => !b.hasAttribute('data-arttip'));
      const chips  = Array.from(document.querySelectorAll<any>('#tab-fsets .gf-chip[data-arttip]'));
      const rd = (b: any) => ({ t: (b.textContent || '').trim().slice(0, 42), c: Q.colorOf(b) });
      return { green, pieces: pieces.slice(0, 6).map(rd), titles: titles.slice(0, 6).map(rd),
               chips: chips.slice(0, 4).map(rd), nP: pieces.length, nT: titles.length };
    });
    console.log('ITEM 3 · --q-set=%s | %d piece names %s | %d title names %s | chips %s',
      r.green, r.nP, JSON.stringify(r.pieces), r.nT, JSON.stringify(r.titles), JSON.stringify(r.chips));
    expect(r.nP, 'no piece names on F-Sets — nothing measured').toBeGreaterThan(0);
    for (const p of r.pieces) expect(p.c, `set PIECE "${p.t}" must be in-game set green`).toBe(r.green);
    for (const c of r.chips)  expect(c.c, `set piece chip "${c.t}" must be in-game set green`).toBe(r.green);
    expect(r.nT, 'no set TITLE names on F-Sets — the second direction measured nothing').toBeGreaterThan(0);
    for (const t of r.titles) expect(t.c, `set TITLE "${t.t}" must move OFF green — that is the confusion he reported`).not.toBe(r.green);
  });
});

/* ════════════════════════════════════════════════════════════════════════════════════════════
   ITEM 6 — PAGE TITLES (colour + real HD art, not an emoji glyph) and LAST FOUND
   ════════════════════════════════════════════════════════════════════════════════════════════ */
test.describe('v1625 · ITEM 6 — the titles wear their quality and their art', () => {
  for (const [tab, label, tokenVar] of [
    ['fsets', 'Forge · Sets', '--q-set'],
    ['funi',  'Forge · Uniques', '--q-unique'],
  ] as const) {
    test(`★★★ "${label}" computes ${tokenVar} and carries a real <img>, not a glyph`, async ({ page }) => {
      await board(page, tab);
      const r = await page.evaluate((t: string) => {
        const Q: any = (window as any).__q;
        const title: any = document.querySelector('#tab-' + t + ' .forge-title');
        if (!title) return { missing: true };
        const head: any = title.closest('.forge-head') || title.parentElement;
        const imgs = Array.from(head.querySelectorAll<any>('img'))
          .map((i: any) => ({ src: i.getAttribute('src') || '', w: i.naturalWidth, h: i.naturalHeight }));
        return { missing: false, text: (title.textContent || '').trim(), color: Q.colorOf(title),
                 want: { set: Q.paint('--q-set'), unique: Q.paint('--q-unique') },
                 bg: Q.bgOf(title), ratio: Q.ratio(Q.colorOf(title), Q.bgOf(title)), imgs };
      }, tab);
      expect(r.missing, `#tab-${tab} has no .forge-title`).toBe(false);
      const want = tokenVar === '--q-set' ? r.want!.set : r.want!.unique;
      console.log('ITEM 6 · "%s" color=%s want %s=%s (%s:1) imgs=%s',
        r.text, r.color, tokenVar, want, r.ratio!.toFixed(2), JSON.stringify(r.imgs));
      expect(r.text).toContain('Forge');
      expect(r.color, `${label} must wear its in-game quality colour`).toBe(want);
      expect(r.ratio, `${label} must stay legible on its own background`).toBeGreaterThanOrEqual(4.5);
      expect(r.imgs!.length, `${label} has no <img> beside it — "image art0r HD also for the title", not a bare emoji`).toBeGreaterThan(0);
      const real = r.imgs!.filter((i: any) => i.src && i.w > 0);
      expect(real.length, `${label}'s title art did not resolve (src present but nothing decoded): ${JSON.stringify(r.imgs)}`).toBeGreaterThan(0);
    });
  }

  test('★★ the plain Forge title wears its TAB\'s rune colour (2026-08-13 ruling) — not repainted globally', async ({ page }) => {
    await board(page, 'forge');
    const r = await page.evaluate(() => {
      const Q: any = (window as any).__q;
      const t: any = document.querySelector('#tab-forge .forge-title');
      if (!t) return { missing: true };
      return { missing: false, text: (t.textContent || '').trim(), color: Q.colorOf(t),
               gold: Q.paint('--gold-bright'), set: Q.paint('--q-set'), unique: Q.paint('--q-unique'),
               rune: Q.paint('--rune') };
    });
    expect(r.missing, '#tab-forge has no .forge-title').toBe(false);
    console.log('ITEM 6 · plain Forge title "%s" color=%s want --rune=%s', r.text, r.color, r.rune);
    expect(r.text).toBe('Forge');
    /* 2026-08-13 — KONYO RULED (bible.html:7924 ruling block): the Forge room wears its TAB'S RUNE
       colour, not the runeword/unique gold. "these two colors cant be the same... RUNEWORD is
       separate from the F-UNIQUES" (v1631) — an item NAME obeys the game, but A TAB IS A LABEL FOR
       A ROOM. This assertion used to demand chrome gold, then the runeword/unique gold (v1707);
       his 2026-08-13 ruling supersedes both. What this test still guards is the thing it was
       actually written for — that the SHARED .forge-title rule was not repainted globally: set
       green and unique gold must never appear here, and the title must still be the deliberate
       per-page override rather than the family accent. */
    expect(r.color, 'the plain Forge title is not wearing --rune (his 2026-08-13 ruling)').toBe(r.rune);
    expect(r.color, 'the plain Forge title leaked set green').not.toBe(r.set);
    expect(r.color, 'the plain Forge title leaked unique gold — it should be RUNE, distinct from F·Uniques')
      .not.toBe(r.unique);
    expect(r.color, 'the shared .forge-title rule was repainted globally — Forge fell back to the family accent')
      .not.toBe(r.gold);
  });

  /* TWO PASSES ON PURPOSE. A last-found test that only ever seeds a unique would sail straight over
     a hardcoded tan. One pass seeds a KNOWN SET piece and demands green; the other seeds a KNOWN
     UNIQUE and demands tan. Both names are read off the live board first, so neither is a guess. */
  for (const kind of ['set', 'unique'] as const) {
    test(`★★★ "last found" is painted to the item's OWN rarity — ${kind} pass`, async ({ page }) => {
      const tab = kind === 'set' ? 'fsets' : 'funi';
      await board(page, tab);
      const name = await page.evaluate((k: string) => {
        const sel = '#tab-' + (k === 'set' ? 'fsets' : 'funi') + ' b.f-rwbig[data-arttip]';
        const pref: any = Array.from(document.querySelectorAll<any>(sel))
          .find((b) => /Cow King|Aldur/.test(b.getAttribute('data-arttip') || ''));
        const b: any = pref || document.querySelector(sel)
                    || document.querySelector('#tab-' + (k === 'set' ? 'fsets' : 'funi') + ' .gf-chip[data-arttip]');
        return b ? (b.getAttribute('data-arttip') || b.textContent || '').trim() : '';
      }, kind);
      expect(name, `could not read a real ${kind} name off the board`).toBeTruthy();

      /* v1759 — SEED A DATE THAT IS NEWEST BY CONSTRUCTION, not a literal that any real find can
         overtake. This pinned '2026-08-03', and it worked only for as long as nothing newer existed
         in _GRAIL_SEED. v1757/v1758 added two finds read off his own Chronicle film — Baranar's
         Star at Aug 10 02:25 and Atma's Wail at Aug 10 00:52 — and Baranar's Star is now genuinely
         the most recent thing he owns, the next being Lidless Wall on Jul 13. So the "last found"
         bar correctly showed Baranar's Star and this test failed for being right.
         The claim here is "the bar paints the item's OWN rarity", which needs the seeded item to BE
         the last found; it never needed a particular date. Derived from the seed's own maximum, so
         the next real find cannot break it either. */
      const newest = await page.evaluate(() => {
        const seed: Record<string, string> = (window as any)._GRAIL_SEED || {};
        let best = 0;
        Object.values(seed).forEach((v) => {
          const t = Date.parse(String(v).replace(' · ', ' '));
          if (!isNaN(t) && t > best) best = t;
        });
        return new Date((best || Date.now()) + 86400000).toISOString().slice(0, 10);
      });
      const seed: any = { d2r_foundLog: { [name]: newest } };
      if (kind === 'set') seed.d2r_setPieces = { [name]: newest };
      await seedAndReload(page, seed, tab);

      const r = await page.evaluate((n: string) => {
        const Q: any = (window as any).__q;
        const bars = Array.from(document.querySelectorAll<any>('.gf-undo-bar b[data-arttip]'))
          .filter((b) => b.offsetParent !== null);
        const hit = bars.find((b) => (b.getAttribute('data-arttip') || '') === n) || bars[0];
        if (!hit) return { found: false, bars: bars.length };
        return { found: true, bars: bars.length, text: (hit.textContent || '').trim(),
                 color: Q.colorOf(hit), set: Q.paint('--q-set'), unique: Q.paint('--q-unique'),
                 imgs: hit.parentElement ? hit.parentElement.querySelectorAll('img').length : 0 };
      }, name);
      console.log('ITEM 6 · last-found (%s) seeded "%s" → bar "%s" color=%s  [set=%s unique=%s]',
        kind, name, r.text, r.color, r.set, r.unique);
      expect(r.found, `no visible .gf-undo-bar after seeding "${name}" — the seed never reached the ledger`).toBe(true);
      expect(r.text, 'the bar must be showing the item we seeded').toBe(name);
      if (kind === 'set') {
        expect(r.color, 'a SET piece in "last found" must be set green').toBe(r.set);
        expect(r.color, 'a SET piece must not be painted unique tan').not.toBe(r.unique);
      } else {
        expect(r.color, 'a UNIQUE in "last found" must be unique tan').toBe(r.unique);
        expect(r.color, 'a UNIQUE must not be painted set green').not.toBe(r.set);
      }
    });
  }
});

/* ════════════════════════════════════════════════════════════════════════════════════════════
   ITEM 5 — F-SETS HERO + QUICK-WIN ROWS: green, routable, keyboard-operable, hover-carded
   ════════════════════════════════════════════════════════════════════════════════════════════ */
test.describe('v1625 · ITEM 5 — "Find Cow King\'s Hooves" is a real, green, operable control', () => {
  test('★★★ hero + quick-win piece names: set green · role=button · tabindex 0 · data-arttip · anchor ≤430×120', async ({ page }) => {
    await board(page, 'fsets');
    const r = await page.evaluate(() => {
      const Q: any = (window as any).__q;
      const green = Q.paint('--q-set');
      const read = (el: any, what: string) => {
        const rect = el.getBoundingClientRect();
        return { what, text: (el.textContent || '').trim().slice(0, 48),
                 color: Q.colorOf(el), role: el.getAttribute('role'),
                 tabIndex: el.tabIndex, arttip: el.getAttribute('data-arttip'),
                 w: Math.round(rect.width), h: Math.round(rect.height) };
      };
      const out: any[] = [];
      /* the hero only names a PIECE on the quick-win branch (bible.html:35327); on the best-farm
         branch (35334) .fh-name is a BOSS, and demanding set green there would be wrong */
      /* ASSERTION FIX (v1625) — this probe originally measured the .fh-name CONTAINER and reported
         "role=null, tabIndex=-1, 1017px wide". That is the wrong DOM: HOUSE RULE 7 says wrap the
         NAME, never the row, because the board's hover binding refuses anchors wider than 430px.
         The product does exactly that (bible.html:35383 puts role/tabindex/data-arttip/onkeydown on
         a .fs-piece span INSIDE .fh-name), so measuring the container was demanding the one shape
         we must NOT ship. Measure the control; fall back to the container if it is missing, so a
         product that really did drop the control still fails. */
      const hero: any = document.querySelector('#tab-fsets .fh-name .fs-piece')
                     || document.querySelector('#tab-fsets .fh-name');
      const lead = (document.querySelector('#tab-fsets .fh-lead') as any)?.textContent || '';
      const heroIsPiece = /quick win/i.test(lead);
      if (hero && heroIsPiece) out.push(read(hero, 'hero'));
      Array.from(document.querySelectorAll<any>('#tab-fsets .f-card.f-step b.f-rwbig[data-arttip]'))
        .slice(0, 3).forEach((b) => out.push(read(b, 'quickwin')));
      return { green, out, heroLead: lead.trim(), heroIsPiece };
    });
    console.log('ITEM 5 · --q-set=%s · hero lead "%s" (piece=%s) · anchors: %s',
      r.green, r.heroLead, r.heroIsPiece, JSON.stringify(r.out, null, 1));
    expect(r.out.length, 'no F-Sets piece anchors found — nothing measured').toBeGreaterThan(0);
    expect(r.out.some((o: any) => o.what === 'quickwin'), 'no Quick wins row measured').toBe(true);
    /* COLLECT every sub-failure instead of dying on the first. (a)…(d) are four independent
       requirements; a spec that stops at (a) can NEVER report on (d), and (d) — the 430px hover
       guard — is the one that fails silently in the product. Proven: with (a) satisfied and the
       anchor forced to 100% width, an early-exit loop still reported only (b). */
    const bad: string[] = [];
    for (const o of r.out) {
      if (o.color !== r.green) bad.push(`(a) "${o.text}" is ${o.color}, must be in-game set green ${r.green}`);
      if (o.role !== 'button') bad.push(`(b) "${o.text}" role=${o.role} — must be a control for a keyboard user`);
      if (o.tabIndex !== 0)    bad.push(`(b) "${o.text}" tabIndex=${o.tabIndex} — must be tab-reachable`);
      if (!o.arttip)           bad.push(`(c) "${o.text}" has no data-arttip`);
      else if (!(o.text.includes(String(o.arttip)) || String(o.arttip).includes(o.text.replace(/^Find\s+/, ''))))
                               bad.push(`(c) data-arttip "${o.arttip}" does not name the piece in "${o.text}"`);
      /* (d) THE SILENT KILLER. bible.html:23040 refuses to bind a hover card to an anchor wider
             than 430px or taller than 120px. Wrap the row instead of the name and you disable the
             very card you were adding — with no error anywhere. */
      if (o.w > 430) bad.push(`(d) "${o.text}" anchor is ${o.w}px wide — the 430px hover guard will REFUSE it`);
      if (o.h > 120) bad.push(`(d) "${o.text}" anchor is ${o.h}px tall — the 120px hover guard will REFUSE it`);
    }
    expect(bad, 'F-Sets piece anchors are not yet the control Konyo asked for:\n  ' + bad.join('\n  ')).toEqual([]);
  });

  test('★★★ ENTER fires the SAME route as CLICK — a real keydown, not an attribute read', async ({ page }) => {
    await board(page, 'fsets');
    const RECORDER = `
      window.__route = [];
      ['navigateToItem','openItemDetail','openBossDetail','switchTab','grailTogglePiece','_openArtTip']
        .forEach(function(fn){
          var orig = window[fn];
          if (typeof orig !== 'function') return;
          window[fn] = function(){ window.__route.push(fn + '(' + String(arguments[0]).slice(0,60) + ')');
                                   return orig.apply(this, arguments); };
        });`;
    const SEL = '#tab-fsets .f-card.f-step b.f-rwbig[data-arttip]';
    const exists = await page.evaluate((s: string) => !!document.querySelector(s), SEL);
    expect(exists, 'no Quick wins piece name to operate').toBe(true);

    // pass 1 — CLICK
    await page.evaluate(RECORDER);
    await page.evaluate((s: string) => { (document.querySelector(s) as any).click(); }, SEL);
    await page.waitForTimeout(800);
    const clickLog = await page.evaluate(() => (window as any).__route.slice());

    // pass 2 — a REAL Enter keydown on the FOCUSED node
    await board(page, 'fsets');
    await page.evaluate(RECORDER);
    const focused = await page.evaluate((s: string) => {
      const el: any = document.querySelector(s); if (!el) return false;
      el.focus(); return document.activeElement === el;
    }, SEL);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(800);
    const keyLog = await page.evaluate(() => (window as any).__route.slice());

    console.log('ITEM 5 · focused=%s · click route=%s · Enter route=%s',
      focused, JSON.stringify(clickLog), JSON.stringify(keyLog));
    expect(focused, 'the piece name did not take focus — tabindex is missing or it is not focusable').toBe(true);
    expect(clickLog.length, 'clicking the piece name routed nowhere at all').toBeGreaterThan(0);
    expect(keyLog.length, 'Enter on the focused piece name routed nowhere — no keydown handler').toBeGreaterThan(0);
    expect(keyLog, 'Enter must fire the SAME route as click, not a different one').toEqual(clickLog);
  });

  test('★★ hovering a quick-win piece actually raises the in-game card', async ({ page }) => {
    await board(page, 'fsets');
    const SEL = '#tab-fsets .f-card.f-step b.f-rwbig[data-arttip]';
    const before = await page.evaluate(() => {
      const t: any = document.getElementById('arttip');
      return t ? t.classList.contains('on') : false;
    });
    expect(before, 'the hover card was already up before we hovered — the measurement would be vacuous').toBe(false);
    await page.locator(SEL).first().hover();
    /* v1717 — WAIT FOR THE CARD, DO NOT SNAPSHOT AT A FIXED 900ms.
       The card is raised by a delegated hover handler and `.on` is a transition class; a single
       read at 900ms passed in one run and failed in the next with the card's own name already
       rendered inside it ("Aldur's Deception"), which is the signature of a race rather than a
       dead control. Polling keeps the assertion exactly as strict — if the card never comes up,
       this still goes red. */
    /* 2026-08-19 — 4s was not enough on a loaded CI runner. This test failed on two consecutive
       shard-3 runs and then PASSED on a re-run with no code change between, which is the
       definition of a flake and cost two full suite cycles to establish. The assertion is
       untouched and exactly as strict: if the card never comes up, this still goes red. Only the
       patience changes — the same argument v1717 made when it replaced a fixed 900ms snapshot
       with polling in the first place. A gate that cries wolf is on its way to being ignored. */
    await page.waitForFunction(() => {
      const t: any = document.getElementById('arttip');
      return !!t && t.classList.contains('on');
    }, null, { timeout: 12000 }).catch(() => {});
    const after = await page.evaluate(() => {
      const t: any = document.getElementById('arttip');
      if (!t) return { exists: false };
      return { exists: true, on: t.classList.contains('on'),
               name: (t.querySelector('.att-name') as any)?.textContent?.trim() || '',
               desc: ((t.querySelector('.att-desc') as any)?.textContent || '').trim().length,
               img: (t.querySelector('img') as any)?.getAttribute('src') || '' };
    });
    console.log('ITEM 5 · hover card: %s', JSON.stringify(after));
    expect(after.exists, 'no #arttip element was ever created').toBe(true);
    expect(after.on, 'hovering the piece name raised no card — check the 430px anchor guard').toBe(true);
    expect(after.name, 'the card came up nameless').toBeTruthy();
  });
});
