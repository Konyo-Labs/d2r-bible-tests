import { test, expect } from './_net_stub';
import * as path from 'path';
import { pinEvaluate, gotoPinned } from './_pin';

/* v1630 — THE REWARD SURFACE HAS TO LOOK LIKE A REWARD (queued item #27).
 *
 * Konyo, looking at the Forge with all 99 runewords forged: "alot of empty space here it can be
 * stretched and bigger. strucutre it better the choricle sealed. maybe a diagonal stamp like the west".
 *
 * WHAT WAS THERE (measured on HEAD ebd0232, file:// render at 1280x1000, all 99 seeded made):
 *   .forge-sealed.forge-sealed-done  =  1252 x 282.5 px
 *   its four children covered 158.5px of that 282.5px height  →  56.1% content, 43.9% nothing
 *   the "99 / 99" was not a figure at all: it was the tail of a sentence inside .fs-title at 22px,
 *   with the prose beneath it at 13.5px — a ratio of 1.63x. The proudest number in the Forge was
 *   set in almost the same size as the paragraph explaining it.
 *
 * WHAT THIS SPEC GUARDS, and why each one is here rather than "the card looks nicer now":
 *   1. the decorative stamp is INERT — it is drawn ACROSS the card, i.e. across the two route
 *      buttons. A rotated overlay with default pointer-events swallows clicks on the exact surface
 *      that is the reward. Asserted structurally (pointer-events / aria-hidden / tab order) AND
 *      behaviourally (elementFromPoint over the button under it, and both buttons still activate).
 *   2. the 99/99 is a PROMOTED FIGURE, not a number buried in a sentence (the measurable form of
 *      "alot of empty space" that survives any spacing decision the design makes).
 *   3. the two routes keep their IN-GAME colours, read from the :root tokens on the live document.
 *   4. both routes stay keyboard-reachable and actually route.
 *   5. reduced motion is respected if anything animates.
 *   6. a PARTIAL chronicle is untouched — the stamp is the reward for 99/99, not decoration.
 *
 * NO LITERAL QUALITY HEX APPEARS IN THIS FILE, in code or in prose. v1621 pinned rgb(0,255,0) and
 * went red the day the palette became CORRECT; v1622 shipped a wrong gold that three specs passed
 * over because they only checked that a class existed. Everything below compares RESOLVED to
 * RESOLVED: the token is read from the live document and normalised through the same engine that
 * painted the button. tests/v1628_no_literal_quality_hex.spec.ts fails literal hexes in both
 * directions, including in this file.
 *
 * The fixture is HONEST: it does not inject the card. It reads the real catalog (RUNEWORD_TIP),
 * writes a real d2r_rwMade for every word, reloads, and lets the real gate `_cSealed && made.length`
 * (bible.html ~33767 at v1630 — grep the condition, line numbers drift every version) decide.
 * The partial fixture seeds a subset so the SAME gate says no.
 */

const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

/** Read the real runeword catalog off the live page (top-level `var`, so also a window prop). */
async function catalog(page: any): Promise<string[]> {
  return await page.evaluate(() => {
    try { return Object.keys((0, eval)('RUNEWORD_TIP')); } catch (e) { /* fall through */ }
    const w: any = window;
    return w.RUNEWORD_TIP ? Object.keys(w.RUNEWORD_TIP) : [];
  });
}

/**
 * Seed a genuinely-forged chronicle and land on the Forge's Completed view.
 * `share` 1 = every word forged (sealed); < 1 = a partial chronicle.
 * Returns how many words were marked made, so a test can prove its fixture is not empty.
 */
async function seedChronicle(page: any, share: number): Promise<number> {
  await page.goto(URL);
  await page.waitForTimeout(2600);
  const keys = await catalog(page);
  expect(keys.length, 'the runeword catalog must load — an empty catalog would make _cSealed false and this whole spec vacuous').toBeGreaterThan(50);
  const take = share >= 1 ? keys.length : Math.max(1, Math.floor(keys.length * share));
  await pinEvaluate(page, (ks: string[]) => {
    // d2r_rwProfile='fresh' is the app's OWN documented lever (bible.html ~15484): without it the
    // owner's _RWC_SEED floor is re-applied on every load and re-marks all 99 words made — which is
    // exactly what a partial fixture must not have. Measured while writing this: seeding 40 words
    // without the fresh flag rendered 99 rows and a SEALED card, so the "partial" test would have
    // been testing the sealed state under a false name. Main profile = bare keys (LS = window.LSR
    // routes the ladder account to L·), so these are the stores the Forge actually reads.
    localStorage.setItem('d2r_rwProfile', 'fresh');
    const made: Record<string, string> = {};
    ks.forEach(k => { made[k] = '2026-01-01'; });
    localStorage.setItem('d2r_rwMade', JSON.stringify(made));
  }, keys.slice(0, take));
  await gotoPinned(page, URL);
  await page.waitForTimeout(2800);
  await page.evaluate(() => { try { (window as any).switchTab('forge'); } catch (e) {} });
  await page.waitForTimeout(700);
  await page.evaluate(() => { try { (window as any).forgeSetFilter('completed'); } catch (e) {} });
  await page.waitForTimeout(1200);
  return take;
}

/* The stamp is located by BEHAVIOUR, not by a class name this spec guessed before the markup
   existed: a decorative (aria-hidden) descendant of the sealed card that is drawn on a rotation.
   The named selectors are tried first so a failure reads as "the stamp is wrong", not "not found". */
const FIND_STAMP = `(card) => {
  const named = card.querySelector('.fs-stamp,.fs-seal,[data-stamp],[class*="stamp"]');
  if (named) return named;
  return Array.from(card.querySelectorAll('*')).find(e => {
    if (e.getAttribute('aria-hidden') !== 'true') return false;
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    const t = cs.transform || '';
    const m = t.match(/^matrix\\(([^)]+)\\)/);
    if (!m) return false;
    const n = m[1].split(',').map(Number);
    return Math.abs(n[1]) > 0.01 || Math.abs(n[2]) > 0.01;   // a real rotation/skew: diagonal
  }) || null;
}`;

/** Resolve a CSS value (token, name, hex) through the live engine into a computed rgb string. */
const RESOLVE = `(v) => {
  const d = document.createElement('div');
  d.style.color = String(v || '').trim();
  document.body.appendChild(d);
  const c = getComputedStyle(d).color;
  d.remove();
  return c;
}`;

test.describe('v1630 — the Chronicle Sealed card earns its height', () => {

  test('★★★ the diagonal stamp exists and is completely INERT', async ({ page }) => {
    const n = await seedChronicle(page, 1);
    /* elementFromPoint is VIEWPORT-relative, so the card must be on screen before it means anything —
       and it must be CENTRED, not merely scrolled into view: `scrollIntoViewIfNeeded` parks the card
       against the bottom edge, where the app's fixed dock covers it and every probe hit-tests to
       `dock-inner`. (bible.html has `scroll-margin-bottom: calc(var(--dock-h) + 24px)` on .forge-sealed
       for exactly this reason.) Measured: with `IfNeeded` the button centre returned .dock-inner;
       with block:'center' it returns the button's own label. The dock is not the defect under test. */
    await page.evaluate(() => {
      const c = document.querySelector('#tab-forge .forge-sealed-done');
      if (c) c.scrollIntoView({ block: 'center' });
    });
    await page.waitForTimeout(400);
    const r = await page.evaluate(([findStamp, seeded]: any) => {
      const card: any = document.querySelector('#tab-forge .forge-sealed.forge-sealed-done');
      if (!card) return { card: false, seeded };
      const stamp: any = (0, eval)('(' + findStamp + ')')(card);
      if (!stamp) return { card: true, stamp: false, cardHTML: card.outerHTML.slice(0, 400) };
      const cs = getComputedStyle(stamp);
      const sb = stamp.getBoundingClientRect();
      const cx = sb.left + sb.width / 2, cy = sb.top + sb.height / 2;
      const hitCentre: any = document.elementFromPoint(cx, cy);

      // Is a route button actually underneath the stamp's box? If so, that is THE point to probe:
      // a stamp drawn across the card overlaps the buttons, and that is where a click gets eaten.
      const btns = Array.from(card.querySelectorAll('.fs-btn')) as any[];
      let under: any = null, hitUnder: any = null;
      for (const b of btns) {
        const bb = b.getBoundingClientRect();
        const overlaps = !(bb.right < sb.left || bb.left > sb.right || bb.bottom < sb.top || bb.top > sb.bottom);
        if (overlaps) {
          under = b;
          hitUnder = document.elementFromPoint(bb.left + bb.width / 2, bb.top + bb.height / 2);
          break;
        }
      }
      const focusableSel = 'a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"]),[contenteditable=""],[contenteditable="true"]';
      return {
        card: true, stamp: true, seeded,
        pointerEvents: cs.pointerEvents,
        ariaHidden: stamp.getAttribute('aria-hidden'),
        tabIndex: stamp.tabIndex,
        selfFocusable: stamp.matches(focusableSel),
        focusableInside: stamp.querySelectorAll(focusableSel).length,
        insideCard: card.contains(stamp),
        centreHitIsStamp: !!(hitCentre && (hitCentre === stamp || stamp.contains(hitCentre))),
        overlapsAButton: !!under,
        underHitIsButton: !!(under && hitUnder && (hitUnder === under || under.contains(hitUnder))),
        // named so a failure says WHAT intercepted, instead of only that something did
        underHitCls: under ? (hitUnder ? (hitUnder.className || hitUnder.tagName) : 'null (off-viewport?)') : null,
        underBtnCls: under ? under.className : null,
        stampBox: { w: Math.round(sb.width), h: Math.round(sb.height) },
      };
    }, [FIND_STAMP, n]);

    expect(r.card, 'the sealed done-card must render for a 99/99 chronicle — check the fixture, not the assertion').toBe(true);
    expect(r.stamp, `no decorative diagonal stamp inside the card: ${(r as any).cardHTML || ''}`).toBe(true);
    expect(r.insideCard, 'the stamp belongs to the card, not the page').toBe(true);
    expect(r.stampBox!.w, 'a stamp with no box is not a stamp').toBeGreaterThan(40);

    // structural inertness
    expect(r.pointerEvents, 'a decorative overlay across the reward surface MUST NOT take pointer events').toBe('none');
    expect(r.ariaHidden, 'the stamp is decoration — screen readers must not read it out').toBe('true');
    expect(r.tabIndex, 'the stamp must not be in the tab order').toBeLessThan(0);
    expect(r.selfFocusable, 'the stamp must not be a natively focusable element').toBe(false);
    expect(r.focusableInside, 'nothing focusable may live inside the stamp').toBe(0);

    // behavioural inertness — the assertion that actually catches a swallowed click
    expect(r.centreHitIsStamp, 'hit-testing the stamp centre returned the stamp: it is intercepting').toBe(false);
    if (r.overlapsAButton) {
      expect(r.underHitIsButton, `the stamp is drawn over route button ${r.underBtnCls} and its centre now hit-tests to "${r.underHitCls}" — something is intercepting the reward surface`).toBe(true);
    }

    // and Playwright's own actionability (which includes the hit-target check) on both routes
    await page.locator('#tab-forge .forge-sealed-done .fs-btn-uni').click({ trial: true });
    await page.locator('#tab-forge .forge-sealed-done .fs-btn-set').click({ trial: true });
  });

  test('★★★ the 99/99 is a PROMOTED FIGURE, not the tail of a sentence', async ({ page }) => {
    /* DEFECT THIS CATCHES: the reward number set at paragraph scale, which is what made a
       282px-tall card read as empty — nothing in it had any visual rank.
       MEASURED, HEAD ebd0232 (before): figure 22px (inside .fs-title, "Chronicle Sealed · 99 / 99"),
       prose 13.5px  →  1.63x. The card's own children covered only 56.1% of its height.
       The bar is 2.0x: a display figure, not a slightly bigger sentence. It is NOT a tuned value —
       it was written from the before-measurement, before the new markup existed. */
    await seedChronicle(page, 1);
    const m = await page.evaluate(() => {
      const card: any = document.querySelector('#tab-forge .forge-sealed.forge-sealed-done');
      if (!card) return null;
      const all = Array.from(card.querySelectorAll('*')) as any[];
      const vis = (e: any) => { const cs = getComputedStyle(e); return cs.display !== 'none' && cs.visibility !== 'hidden' && e.getBoundingClientRect().height > 0; };
      const txt = (e: any) => (e.textContent || '').replace(/\s+/g, ' ').trim();

      // the FIGURE: the smallest element that is just the count (99 / 99, or 99 with the total split out)
      const figs = all.filter(e => vis(e) && e.children.length === 0 && /^\d+\s*(\/\s*\d+)?$/.test(txt(e)));
      const fig = figs.sort((a, b) => parseFloat(getComputedStyle(b).fontSize) - parseFloat(getComputedStyle(a).fontSize))[0];

      // the PROSE: the longest sentence in the card
      const proseEls = all.filter(e => vis(e) && txt(e).length > 40 && !all.some(o => o !== e && e.contains(o) && txt(o).length > 40));
      const prose = proseEls.sort((a, b) => txt(b).length - txt(a).length)[0];

      // informational: how much of the card's height its non-decorative children cover
      const cb = card.getBoundingClientRect();
      const iv = (Array.from(card.children) as any[])
        .filter(c => c.getAttribute('aria-hidden') !== 'true' && vis(c))
        .map(c => { const r = c.getBoundingClientRect(); return [r.top - cb.top, r.bottom - cb.top]; })
        .sort((a, b) => a[0] - b[0]);
      let cov = 0, cur: any = null;
      for (const [s, e] of iv) { if (!cur) cur = [s, e]; else if (s <= cur[1]) cur[1] = Math.max(cur[1], e); else { cov += cur[1] - cur[0]; cur = [s, e]; } }
      if (cur) cov += cur[1] - cur[0];

      return {
        figText: fig ? txt(fig) : null,
        figSize: fig ? parseFloat(getComputedStyle(fig).fontSize) : 0,
        proseText: prose ? txt(prose).slice(0, 60) : null,
        proseSize: prose ? parseFloat(getComputedStyle(prose).fontSize) : 0,
        cardH: Math.round(cb.height), coverage: cov / cb.height,
      };
    });
    expect(m, 'the sealed done-card must render').not.toBeNull();
    console.log(`v1630 sealed card: ${m!.cardH}px tall · children cover ${(m!.coverage * 100).toFixed(1)}% (was 56.1%) · figure "${m!.figText}" ${m!.figSize}px vs prose ${m!.proseSize}px (was 22 vs 13.5 = 1.63x)`);

    expect(m!.figText, 'the 99/99 must be its own element to be a figure at all — before, it was the tail of "Chronicle Sealed · 99 / 99"').toBeTruthy();
    expect(m!.figText, 'and it must be the real, complete count').toContain('99');
    expect(m!.proseSize, 'the card still needs its sentence — a figure alone proves nothing').toBeGreaterThan(0);
    expect(m!.figSize / m!.proseSize, `the 99/99 must READ as the reward: ${m!.figSize}px against ${m!.proseSize}px of prose`).toBeGreaterThanOrEqual(2.0);
  });

  test('★★★ both routes keep their IN-GAME colours, resolved from the live tokens', async ({ page }) => {
    /* Compare RESOLVED to RESOLVED. No quality hex is spelled in this file: the expected value is
       whatever :root says today, pushed through the same engine that painted the button. Change the
       palette and this stays green; point a button at the wrong quality and it goes red. */
    await seedChronicle(page, 1);
    const c = await page.evaluate((resolve: string) => {
      const R = (0, eval)('(' + resolve + ')');
      const root = getComputedStyle(document.documentElement);
      const card: any = document.querySelector('#tab-forge .forge-sealed.forge-sealed-done');
      const uni: any = card && card.querySelector('.fs-btn-uni');
      const set: any = card && card.querySelector('.fs-btn-set');
      return {
        tokenUnique: R(root.getPropertyValue('--q-unique')),
        tokenSet: R(root.getPropertyValue('--q-set')),
        rawUnique: root.getPropertyValue('--q-unique').trim(),
        rawSet: root.getPropertyValue('--q-set').trim(),
        uniColor: uni ? getComputedStyle(uni).color : null,
        setColor: set ? getComputedStyle(set).color : null,
      };
    }, RESOLVE);

    expect(c.rawUnique, 'the --q-unique token must be defined on :root').toBeTruthy();
    expect(c.rawSet, 'the --q-set token must be defined on :root').toBeTruthy();
    expect(c.tokenUnique, 'the unique token must resolve to a real colour').toMatch(/^rgba?\(/);
    expect(c.tokenSet, 'the set token must resolve to a real colour').toMatch(/^rgba?\(/);
    expect(c.tokenUnique).not.toBe(c.tokenSet);   // if these were equal the two asserts below would be interchangeable
    expect(c.uniColor, 'the F·Uniques route wears UNIQUE quality').toBe(c.tokenUnique);
    expect(c.setColor, 'the F·Sets route wears SET quality').toBe(c.tokenSet);
  });

  test('★★ both routes stay keyboard-reachable and actually route', async ({ page }) => {
    for (const [cls, tab, key] of [['.fs-btn-uni', 'tab-funi', 'Enter'], ['.fs-btn-set', 'tab-fsets', 'Space']] as const) {
      await seedChronicle(page, 1);
      const sel = `#tab-forge .forge-sealed-done ${cls}`;
      // a converted div must carry the full control contract; a native <button> already has it
      const contract = await page.evaluate((s: string) => {
        const b: any = document.querySelector(s);
        if (!b) return null;
        return { tag: b.tagName, role: b.getAttribute('role'), tabindex: b.getAttribute('tabindex'), onkeydown: !!b.getAttribute('onkeydown') };
      }, sel);
      expect(contract, `${cls} must exist on the sealed card`).not.toBeNull();
      if (contract!.tag !== 'BUTTON') {
        expect(contract!.role, `${cls} is not a <button>, so it needs role=button`).toBe('button');
        expect(contract!.tabindex, `${cls} is not a <button>, so it needs tabindex=0`).toBe('0');
        expect(contract!.onkeydown, `${cls} is not a <button>, so it needs a keydown handler`).toBe(true);
      }
      await page.focus(sel);
      expect(await page.evaluate((s: string) => document.activeElement === document.querySelector(s), sel),
        `${cls} must take focus`).toBe(true);
      await page.keyboard.press(key);
      await page.waitForTimeout(900);
      const shown = await page.evaluate((id: string) => {
        const t: any = document.getElementById(id);
        return !!(t && t.offsetParent !== null);
      }, tab);
      expect(shown, `${key} on ${cls} must route to #${tab}`).toBe(true);
    }
  });

  test('★★ reduced motion is respected', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await seedChronicle(page, 1);
    const anim = await page.evaluate((findStamp: string) => {
      const card: any = document.querySelector('#tab-forge .forge-sealed.forge-sealed-done');
      if (!card) return null;
      const stamp: any = (0, eval)('(' + findStamp + ')')(card);
      const running = (Array.from(card.querySelectorAll('*')) as any[]).concat([card])
        .map(e => { const cs = getComputedStyle(e); return { name: cs.animationName, dur: cs.animationDuration, iter: cs.animationIterationCount, cls: e.className }; })
        .filter(a => a.name && a.name !== 'none' && parseFloat(a.dur) > 0);
      return { hasStamp: !!stamp, running };
    }, FIND_STAMP);
    expect(anim, 'the sealed card must render under reduced motion too').not.toBeNull();
    expect(anim!.hasStamp, 'reduced motion must not delete the stamp — only its motion').toBe(true);
    /* CONDITIONAL BY DESIGN, and said out loud so nobody reads a pass as proof of an animation:
       if the design chose a static stamp there is nothing to disable, and `running` is legitimately
       empty. What must never be true is an animation STILL RUNNING under prefers-reduced-motion. */
    expect(anim!.running, `still animating under prefers-reduced-motion: ${JSON.stringify(anim!.running)}`).toEqual([]);
  });

  test('★★ a PARTIAL chronicle gets no stamp — the seal is the 99/99 reward', async ({ page }) => {
    const seeded = await seedChronicle(page, 0.4);
    const r = await page.evaluate((findStamp: string) => {
      const tab: any = document.getElementById('tab-forge');
      const done: any = tab && tab.querySelector('.forge-sec-done');
      const sealed: any = tab && tab.querySelector('.forge-sealed');
      const rows = tab ? tab.querySelectorAll('.f-donerow').length : 0;
      let stamp: any = null;
      if (tab) stamp = (0, eval)('(' + findStamp + ')')(tab);
      return { hasDone: !!done, hasSealed: !!sealed, rows, stamp: !!stamp };
    }, FIND_STAMP);
    expect(seeded, 'the partial fixture must mark SOME words made, or this test proves nothing').toBeGreaterThan(10);
    expect(r.rows, 'the partial fixture must actually render the created rows it seeded').toBeGreaterThan(10);
    expect(r.hasDone, 'a partial chronicle renders the plain ✅ Completed section').toBe(true);
    expect(r.hasSealed, 'a partial chronicle is NOT sealed').toBe(false);
    expect(r.stamp, 'no SEALED stamp may appear on a chronicle that is not sealed').toBe(false);
  });
});
