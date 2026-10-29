import { test, expect, seedOwnerRoute } from './_net_stub';
import * as fs from 'fs';
import * as path from 'path';
import { pinEvaluate, reloadPinned } from './_pin';

// v1630 — THE SLOT IS STATED ONCE, AND THE RAW NAME STILL DRIVES EVERYTHING.
//
// Konyo: "for griswald it doesnt need to say (SHIELD) remove it also for tooltip image".
//
// ITEM_SETS names its members "Griswold's Honor (shield)" — the slot is part of the DATA key, and
// it has to stay that way: window._hubGoSetPiece and _bridgeSetTip both match exact-name FIRST and
// paren-stripped only as a fallback (bible.html:15665-15696), d2r_setPieces persists "Name (slot)"
// strings (documented bible.html:3724, parsed 15379), and the console's set bridge ships the same
// suffixed string. So the fix is a DISPLAY strip, applied at render, never at the source.
//
// This spec therefore guards BOTH directions, because exactly one half must change:
//   · nothing RENDERED may still trail a "(slot)"  — the complaint;
//   · nothing STORED, ROUTED or LOOKED UP may lose it — his data.
// A change that strips at the source would make half of this file green and the other half red,
// which is the whole point. Neither half may be relaxed to make the other pass.
//
// The type line is the justification: the hover card already reads "Set · Vortex Shield". If that
// ever stops naming the base, stripping the name becomes information LOSS and test 3 goes red.

const ORIGIN = 'http://tvd.console.test';
const REPO = path.resolve(__dirname, '..');
const UI = fs.readFileSync(path.join(REPO, 'tv', 'control_ui.html'), 'utf8');
const BOARD = 'file://' + path.join(REPO, 'bible.html');

// a name that still ENDS in a parenthetical — the exact shape Konyo pointed at
const TRAILING_PAREN = /\([^()]*\)\s*$/;
// ITEM_SETS states the slot in lower case: "(shield)", "(heavy boots)", "(chainmail)"
const SLOT_TAIL = /\s*\(([a-z][a-z ]*)\)$/;

// the display sites that print a set-piece name, named by selector so a NEW regressing site
// (a chip, a row, an ops-queue line) is swept up by the same scan instead of shipping unguarded
const SITES = [
  { sel: '.fh-name', what: 'forge / F·Sets hero name line (bible.html:32900, 35474)' },
  { sel: '.fs-piece', what: 'quick-win hero piece span (bible.html:35476)' },
  { sel: '.set-piece-name', what: 'set tracker piece rows (bible.html:19291)' },
  { sel: '.gf-lastname', what: '"✅ last found" bar (bible.html:34307)' },
  { sel: '#arttip .att-name', what: 'hover card NAME line (bible.html:23186)' },
];

/* ITEM_SETS is a module-level const, not a window property — the same trap v1620 documents for
   ITEM_CODEX. A top-level `const` lives in the global LEXICAL scope, so new Function() reaches it
   whichever way the file declares it. */
const READ_SETS = 'return (typeof ITEM_SETS!=="undefined"?ITEM_SETS:(window.ITEM_SETS||[]))';
/* the helper sweep goes wider than the tracker: __allSets() = ITEM_SETS + SET_PIECES_EXTRA(2)
   (bible.html:13382), i.e. every set piece the app knows, not just the ones the tracker paints. */
const READ_ALL = 'return (typeof __allSets==="function"?__allSets():' +
                 '(typeof ITEM_SETS!=="undefined"?ITEM_SETS:(window.ITEM_SETS||[])))';

// the test's OWN oracle for the expected label — deliberately not the app's helper, or a broken
// helper would define its own correctness
const labelOf = (raw: string) => raw.replace(SLOT_TAIL, '');

async function board(page: any) {
  await page.goto(BOARD);
  await page.waitForTimeout(2600);
}

/** two REAL sets read out of ITEM_SETS — never names typed into this file, so the spec follows
 *  the data if the data changes instead of going stale. */
async function pickSets(page: any) {
  const picks = await page.evaluate((read: string) => {
    const sets: any[] = (new Function(read))();
    const slot = /\s*\(([a-z][a-z ]*)\)$/;
    const out: any[] = [];
    for (const s of sets) {
      const all: string[] = (s && s.pieces) || [];
      if (all.length >= 3 && all.every((p: string) => slot.test(p))) {
        out.push({ set: s.name || s.set || '', pieces: all });
      }
    }
    return out;
  }, READ_SETS);
  expect(picks.length, 'ITEM_SETS must still carry slot-suffixed pieces — if it does not, this whole item is moot')
    .toBeGreaterThan(4);
  // more than one set, so the spec proves a CLASS was fixed rather than one string
  return picks.slice(0, 3);
}

/** seed all-but-one piece of each picked set: that is the state Konyo is looking at — a hero, a
 *  quick win, a "last found" bar and hundreds of tracker rows all printing piece names at once. */
async function seedAndRender(page: any, picks: any[]) {
  await pinEvaluate(page, (ps: any[]) => {
    const found: string[] = []; const fl: any = {};
    ps.forEach((p) => p.pieces.slice(0, p.pieces.length - 1).forEach((n: string) => {
      found.push(n); fl[n] = '2026-08-03';
    }));
    localStorage.setItem('d2r_setPieces', JSON.stringify(found));
    localStorage.setItem('d2r_foundLog', JSON.stringify(fl));
  }, picks);
  await reloadPinned(page);
  await page.waitForTimeout(2800);
  for (const t of ['grail', 'fsets', 'forge', 'funi']) {
    await page.evaluate((tb: string) => { try { (window as any).switchTab(tb); } catch (e) {} }, t);
    await page.waitForTimeout(900);
  }
}

test.describe('v1630 — the slot leaves the name, not the data', () => {

  test('★★★ _pieceLabel strips the SLOT and nothing else', async ({ page }) => {
    await board(page);
    const r = await page.evaluate((read: string) => {
      const w: any = window;
      if (typeof w._pieceLabel !== 'function') return { missing: true };
      const sets: any[] = (new Function(read))();
      const slot = /\s*\(([a-z][a-z ]*)\)$/;
      const bad: any[] = []; let checked = 0;
      for (const s of sets) for (const p of ((s && s.pieces) || [])) {
        if (!slot.test(p)) continue;
        checked++;
        const got = w._pieceLabel(p);
        if (got !== p.replace(slot, '')) bad.push({ p, got });
      }
      // parentheticals that are NOT a slot and must survive byte-identical. Every one of these is a
      // real string in bible.html: the Shako alias and the Larzuk socket bases are literals in the
      // codex, and "(4os)" is the socket label rendered at bible.html:10122.
      const keep = ['Harlequin Crest (Shako)', 'Circlet (Larzuk base)',
                    'Colossus Voulge (Larzuk base)', 'Crystal Sword (4os)', 'Hellfire Torch (cube)'];
      const eaten = keep.filter((k) => w._pieceLabel(k) !== k);
      // the console's own fixtures carry the slot capitalised ("Griswold's Honor (Shield)")
      const capsSrc = (((sets.find((s: any) => (s.pieces || []).some((p: string) => slot.test(p))) || {}).pieces) || [''])[0];
      const caps = capsSrc.replace(slot, (m: string) => m.toUpperCase());
      /* "safe" means it does not throw and does not invent a name — returning the empty input
         verbatim (null → null) is as correct as returning ''. What must never happen is a crash,
         or the string "null" landing in a title. */
      const safe: any = { threw: false, out: [] as string[] };
      try {
        safe.out = [w._pieceLabel(null), w._pieceLabel(undefined), w._pieceLabel('')]
          .map((v: any) => (v === null || v === undefined || v === '') ? 'ok' : 'BAD:' + String(v));
      } catch (e) { safe.threw = true; }
      return { missing: false, checked, bad: bad.slice(0, 6), eaten,
               caps, capsGot: w._pieceLabel(caps), capsWant: capsSrc.replace(slot, ''), safe };
    }, READ_ALL);

    expect(r.missing, 'window._pieceLabel must exist — the display strip has one home, not six copies').toBeFalsy();
    // measured on this tree: 54 slot-suffixed pieces in ITEM_SETS alone, more via __allSets()
    expect(r.checked, 'a scan that checked nothing proves nothing').toBeGreaterThan(40);
    expect(r.bad, 'every slot-suffixed set piece must lose exactly its slot').toEqual([]);
    expect(r.eaten, 'a NON-slot parenthetical is load-bearing and must survive untouched').toEqual([]);
    expect(r.capsGot, `case must not decide it: ${r.caps}`).toBe(r.capsWant);
    expect(r.safe.threw, 'null/undefined/empty must never throw — heroes call this on every render').toBe(false);
    expect(r.safe.out, 'and must never turn an empty name into the word "null"').toEqual(['ok', 'ok', 'ok']);
  });

  test('★★★ NO rendered set-piece name still wears its slot', async ({ page }) => {
    await board(page);
    const picks = await pickSets(page);
    await seedAndRender(page, picks);

    /* The tracker rows live on a tab that is not the one left showing, so page.hover() would burn
       its 30s actionability timeout on a hidden node and populate nothing. The arttip is bound by
       a delegated mouseover listener (bible.html:23035+), so a dispatched event is the real thing
       as far as the handler is concerned — and it works on the hidden tab too. */
    const seen = await page.evaluate((args: any) => {
      const { sites, seeded } = args;
      // float the hover card so its NAME line is a real, populated node and not an empty div
      const sp: any = document.querySelector('.set-piece-name');
      if (sp) { try { sp.dispatchEvent(new MouseEvent('mouseover', { bubbles: true })); } catch (e) {} }
      const out: any[] = [];
      for (const s of sites) {
        const nodes = Array.from(document.querySelectorAll(s.sel)) as any[];
        const texts = nodes.map((n) => (n.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
        out.push({ sel: s.sel, what: s.what, count: texts.length,
                   offenders: texts.filter((t: string) => /\([^()]*\)\s*$/.test(t)).slice(0, 5),
                   /* the row prints an art glyph before the name — "📿 Tal Rasha's Adjudication" —
                      so the label is a SUFFIX of the visible text, not the whole of it */
                   hits: texts.filter((t: string) =>
                     seeded.some((lbl: string) => t === lbl || t.endsWith(lbl))).length });
      }
      return out;
    }, { sites: SITES, seeded: picks.flatMap((p: any) => p.pieces.map(labelOf)) });

    // NON-VACUITY FIRST: a scan over an empty DOM would "pass" every pattern check. v1624 asserted
    // boss art "resolves to something" and passed while Mephisto rendered his soulstone.
    const total = seen.reduce((a: number, s: any) => a + s.count, 0);
    const hits = seen.reduce((a: number, s: any) => a + s.hits, 0);
    expect(total, 'the scan must actually have found rendered names').toBeGreaterThan(30);
    expect(hits, 'and at least a couple of them must be the SEEDED set pieces — otherwise it swept the wrong DOM')
      .toBeGreaterThan(1);
    for (const s of seen) {
      expect(s.offenders, `${s.what} still prints the slot in the NAME`).toEqual([]);
    }
    // the two sites that carry a piece name unconditionally must have been reached at all
    const byName = (sel: string) => seen.find((s: any) => s.sel === sel);
    expect(byName('.set-piece-name').count, 'the set tracker rows never rendered — the scan was blind there')
      .toBeGreaterThan(20);
    expect(byName('#arttip .att-name').count + byName('.fh-name').count,
      'neither the hover card nor a hero name line rendered').toBeGreaterThan(0);
  });

  test('★★★ the TYPE LINE still states the slot — the whole justification for stripping', async ({ page }) => {
    /* "Griswold's Honor" alone is only acceptable because one line below it the card reads
       "Set · Vortex Shield". Take that away and the strip is information loss, not tidying. */
    await board(page);
    const picks = await pickSets(page);
    const r = await page.evaluate((ps: any[]) => {
      const w: any = window;
      const slot = /\s*\(([a-z][a-z ]*)\)$/;
      let tips = 0, blank = 0, restated = 0;
      const empties: string[] = [];
      for (const p of ps) for (const raw of p.pieces) {
        const t = w._bridgeSetTip(raw, p.set);
        if (!t) continue;
        tips++;
        const base = String(t.b || '').trim();
        if (!base) { blank++; if (empties.length < 4) empties.push(raw); continue; }
        const m = raw.match(slot);
        const word = m ? m[1].split(' ').pop() : '';
        if (word && base.toLowerCase().indexOf(word) >= 0) restated++;
      }
      return { tips, blank, restated, empties };
    }, picks);
    expect(r.tips, 'the bridge must resolve tips for these pieces at all').toBeGreaterThan(5);
    expect(r.blank, `these pieces would lose their type entirely: ${r.empties.join(', ')}`).toBe(0);
    expect(r.restated, 'and the base line genuinely re-states the slot for the shield/boots/glove class')
      .toBeGreaterThan(2);
  });

  test('★★★ the RAW suffixed name still routes, looks up and PERSISTS', async ({ page }) => {
    await board(page);
    const picks = await pickSets(page);
    await seedAndRender(page, picks);

    const r = await page.evaluate((ps: any[]) => {
      const w: any = window;
      const slot = /\s*\(([a-z][a-z ]*)\)$/;
      const raws: string[] = ps.flatMap((p: any) => p.pieces);

      /* ROUTING, read off the LIVE DOM. Note: .set-piece-name's data-arttip is deliberately the
         BASE name (bible.html:19288-19291 strips it for the ART lookup) — the routing value on
         that row is toggleSetPiece's argument, so that is what we read. */
      const rows = Array.from(document.querySelectorAll('.set-piece')) as any[];
      /* the argument is single-quoted with the apostrophes BACKSLASH-escaped — "Tal Rasha\'s
         Adjudication (amulet)". A naive [^']* stops at the apostrophe and silently reads 4 of 54
         rows, which is how a green raw-survives test would prove nothing about 50 of them. */
      const args = rows.map((el) => {
        const m = (el.getAttribute('onclick') || '').match(/toggleSetPiece\('((?:\\.|[^'\\])*)'\)/);
        return m ? m[1].replace(/\\'/g, "'").replace(/\\\\/g, '\\') : '';
      }).filter(Boolean);
      const suffixed = args.filter((a: string) => slot.test(a));

      // BOTH bridge paths: exact-name first, paren-stripped second (bible.html:15665-15696)
      const bridge: any[] = [];
      for (const p of ps) for (const raw of p.pieces.slice(0, 3)) {
        const a = w._bridgeSetTip(raw, p.set);
        const b = w._bridgeSetTip(raw.replace(slot, ''), p.set);
        bridge.push({ raw, rawAffixes: (a && a.l && a.l.length) || 0, strippedAffixes: (b && b.l && b.l.length) || 0 });
      }

      // the console bridge payload
      try { w._writeSetFarm(); } catch (e) {}
      const readLS = (k: string) => {
        try { const v = (w.LSR && w.LSR.getItem(k)) || localStorage.getItem(k); return JSON.parse(v || 'null'); }
        catch (e) { return null; }
      };
      const farm = readLS('d2r_setFarm') || [];

      // and the chronicle itself, after a full render. The decisive check is not "some entries
      // still have a slot" — a source-side strip ADDS stripped keys next to the floored ones and
      // leaves that count healthy. It is "no DISPLAY LABEL was ever written back as a key".
      const stored = readLS('d2r_setPieces') || [];
      const known: any = {}; const labels: any = {};
      const allSets: any[] = (new Function(
        'return (typeof __allSets==="function"?__allSets():ITEM_SETS)'))();
      for (const s of allSets) for (const p of ((s && s.pieces) || [])) known[p] = 1;
      for (const p in known) if (slot.test(p)) labels[p.replace(slot, '')] = p;
      const leaked = stored.filter((s: string) => labels[s] && !known[s])
        .map((s: string) => `${s}  (label of "${labels[s]}")`);
      // a fresh tick must write the RAW string back, not the label
      /* the app FLOORS d2r_setPieces on every boot, so the piece we left out of the seed may
         already be in the chronicle — a single toggle would tick it OFF and prove nothing. Drive
         it to a known-absent state first, then tick it ON and read what was written. */
      const unticked = ps[0].pieces[ps[0].pieces.length - 1];
      let tickedBack = false, tickState = 'no-run';
      try {
        if ((readLS('d2r_setPieces') || []).indexOf(unticked) >= 0) w.toggleSetPiece(unticked);
        const gone = (readLS('d2r_setPieces') || []).indexOf(unticked) < 0;
        w.toggleSetPiece(unticked);
        const after = readLS('d2r_setPieces') || [];
        tickedBack = after.indexOf(unticked) >= 0;
        tickState = gone ? (tickedBack ? 'ok' : 'ticked ON but the RAW key is absent')
                         : 'could not clear it first';
      } catch (e) { tickState = 'threw: ' + e; }

      return {
        rows: rows.length, args: args.length, suffixedArgs: suffixed.length,
        strayArg: args.find((a: string) => raws.indexOf(a) < 0 && raws.indexOf(a + ' ') < 0) || null,
        bridge,
        farm: farm.map((f: any) => String(f && f.name || '')),
        stored, storedSuffixed: stored.filter((s: string) => slot.test(s)).length, leaked,
        tickedBack, tickState, unticked,
      };
    }, picks);

    expect(r.args, 'no set-piece rows rendered — nothing to prove').toBeGreaterThan(20);
    expect(r.suffixedArgs, 'the ROUTE must still carry the full "Name (slot)" string').toBeGreaterThan(20);
    for (const b of r.bridge) {
      expect(b.rawAffixes, `_bridgeSetTip("${b.raw}") — exact-name match must still work`).toBeGreaterThan(0);
      expect(b.strippedAffixes, `_bridgeSetTip("${labelOf(b.raw)}") — paren-stripped fallback must still work`)
        .toBeGreaterThan(0);
    }
    expect(r.farm.length, 'the console set bridge must have been written').toBeGreaterThan(0);
    expect(r.farm.filter((n: string) => TRAILING_PAREN.test(n)).length,
      `d2r_setFarm must ship the RAW name to the console: ${r.farm.join(' | ')}`).toBeGreaterThan(0);
    expect(r.storedSuffixed, 'd2r_setPieces must still hold "Name (slot)" strings (bible.html:3724)')
      .toBeGreaterThan(3);
    expect(r.leaked, 'a DISPLAY label was persisted as a chronicle key — the strip reached the source')
      .toEqual([]);
    expect(r.tickedBack,
      `ticking "${r.unticked}" must persist the RAW name, never the display label (${r.tickState})`).toBe(true);
  });

  test('★★ CONSOLE — the hunt hero shows the label, clicks the RAW name', async ({ page }) => {
    // derive the fixture from the board's own data, then drive the console with it
    await board(page);
    const picks = await pickSets(page);
    const piece = picks[0].pieces[picks[0].pieces.length - 1];
    const setName = picks[0].set;
    // every slot-suffixed piece in the game, with the BOARD's answer for each — the console gets
    // the same list below and the two must agree (see the agreement assertion at the end)
    const boardLabels = await page.evaluate((read: string) => {
      const w: any = window;
      const sets: any[] = (new Function(read))();
      const slot = /\s*\(([a-z][a-z ]*)\)$/;
      const out: any = {};
      for (const s of sets) for (const p of ((s && s.pieces) || [])) if (slot.test(p)) out[p] = w._pieceLabel(p);
      return out;
    }, READ_ALL);

    // v1749 — the route a real console always has; without it lsFork reads NOTHING (v1736)
    await seedOwnerRoute(page);
    await page.addInitScript((seed: any) => {
      localStorage.setItem('d2r_setFarm', JSON.stringify([{ name: seed.piece, set: seed.set, left: 1,
        source: 'Hell TZ Pindleskin', dropChance: 0.0003, killsPerHr: 90,
        art: 'art/hd_crown_shield.png', rarity: 'set' }]));
      localStorage.setItem('d2r_grailFarm', JSON.stringify([{ name: 'Frostburn', source: 'Hell Mephisto',
        dropChance: 0.0002, killsPerHr: 100, art: 'art/hd_gaunlets_h.png', rarity: 'unique' }]));
    }, { piece, set: setName });

    await page.route(ORIGIN + '/ui', (r: any) =>
      r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: UI }));
    await page.route((u: URL) => u.pathname.startsWith('/art/'), (r: any) => {
      const p = path.join(REPO, new URL(r.request().url()).pathname.replace(/^\//, ''));
      return fs.existsSync(p)
        ? r.fulfill({ status: 200, contentType: 'image/png', body: fs.readFileSync(p) })
        : r.fulfill({ status: 404, body: '' });
    });
    await page.route((u: URL) => u.pathname === '/api/evrank', async (r: any) => {
      let items: any[] = [];
      try { items = JSON.parse(r.request().postData() || '{}').items || []; } catch (e) {}
      await r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true,
        ranked: items.map((it: any, i: number) => ({ name: it.name, source: it.source, expectedHours: 1.3 + i })) }) });
    });
    await page.route((u: URL) => u.pathname.startsWith('/api/') && u.pathname !== '/api/evrank',
      (r: any) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"ok":false}' }));
    await page.goto(ORIGIN + '/ui', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2600);

    const SEL = '.hh-name';
    try { await page.hover(SEL); await page.waitForTimeout(1200); } catch (e) {}

    const hero = await page.evaluate(() => {
      const el: any = Array.from(document.querySelectorAll('.hh-name'))
        .find((n: any) => (n.getAttribute('onclick') || '').indexOf('_hubGoSetPiece') >= 0);
      if (!el) return null;
      try { el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true })); } catch (e) {}
      let itip: any = null;
      try { itip = JSON.parse(el.getAttribute('data-itip') || 'null'); } catch (e) {}
      const card: any = document.querySelector('#itip .itip-n');
      return { text: (el.textContent || '').replace(/\s+/g, ' ').trim(),
               aria: el.getAttribute('aria-label') || '',
               onclick: el.getAttribute('onclick') || '',
               onkey: el.getAttribute('onkeydown') || '',
               // the PAYLOAD must stay raw (it is what _routeReceipt / the board lookup consume);
               // the strip belongs to the card's render (tv/control_ui.html:4929)
               itipPayloadName: itip ? String(itip.name || '') : null,
               cardName: card ? (card.textContent || '').trim() : null };
    });

    expect(hero, 'the hunt hero must render a set-piece control at all').toBeTruthy();
    const tail = (piece.match(SLOT_TAIL) || [''])[0].trim();   // e.g. "(shield)"
    expect(hero.text, `the hero title still reads "${hero.text}"`).not.toMatch(TRAILING_PAREN);
    expect(hero.text.toLowerCase(), 'nor anywhere else in its visible text').not.toContain(tail.toLowerCase());
    expect(hero.aria.toLowerCase(), 'the screen reader hears the same title he sees').not.toContain(tail.toLowerCase());
    // …while every value that ROUTES or LOOKS UP is untouched
    expect(hero.onclick, 'the click must still hand _hubGoSetPiece the RAW suffixed name').toContain(piece);
    expect(hero.onkey, 'and so must the keyboard path').toContain(piece);
    expect(hero.itipPayloadName, 'the tooltip PAYLOAD stays raw — it is a lookup key, not a label')
      .toBe(piece);
    // "also for tooltip image": the CARD, which is what he actually reads, is stripped at render
    expect(hero.cardName, 'the hover card must have rendered its name line').toBeTruthy();
    expect(hero.cardName, 'and the tooltip NAME line is stripped too').not.toMatch(TRAILING_PAREN);
    expect(hero.text.trim().length, 'the label must not be blanked in the process').toBeGreaterThan(3);

    /* THE TWO SURFACES MUST AGREE. The board and the console each carry their OWN copy of
       _pieceLabel (they are separate documents, so it cannot be an import — tv/control_ui.html:4604
       says so). A token in one list and not the other means the same piece prints two different
       names on two screens, and nothing compares them. This does. */
    const disagree = await page.evaluate((labels: any) => {
      const w: any = window;
      if (typeof w._cPieceLabel !== 'function') return { missing: true, rows: [], n: 0 };
      const rows: any[] = [];
      for (const raw in labels) {
        const got = w._cPieceLabel(raw);
        if (got !== labels[raw]) rows.push({ raw, board: labels[raw], console: got });
      }
      return { missing: false, rows: rows.slice(0, 8), n: Object.keys(labels).length };
    }, boardLabels);
    expect(disagree.missing, 'the console must publish its label helper for this comparison').toBe(false);
    expect(disagree.n, 'nothing was compared').toBeGreaterThan(40);
    expect(disagree.rows,
      'board and console print DIFFERENT names for these pieces — one token list is missing entries')
      .toEqual([]);
  });
});
