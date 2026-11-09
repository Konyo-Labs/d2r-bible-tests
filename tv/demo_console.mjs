// demo_console.mjs — STANDALONE scripted DEMONSTRATION journeys.
// NOT a Playwright test-runner spec. Run:  node tv/demo_console.mjs   (from repo root).
// REG-2275 (#18 / #73). Boots a private control_app on two free ports and drives that page.
// It never opens 17772 or 17771, even when the shell inherited those ports.
// REG-2278. Pre-push sets TV_DEMO_OWNED and unsets TV_DEMO_PORT, so that route always
// spawns a console this process owns. A hand run may still set TV_DEMO_PORT to a console
// it started (not 17771 or 17772); that server is not started here and is not killed.
// Own headless chromium — never his tab, never the repo suite. Each
// journey prints one ✅/❌ line; the process exits non-zero if any journey fails.
//
// The journeys mirror the console architecture (control_ui.html):
//   header tabs #head-tabs .ht[data-tab] → shellOpen() adds body.shell-open and routes the
//   same-origin engine iframe #tvd-eng (its .tab.active gains the matching data-tab);
//   the TV·D tab calls shellHome() back to the .stage. Tally chip .hd-chip.tly-btn opens
//   #tly-ov with .tly-tab filters. Three eyes = #eye-live/#eye-second/#eye-kai + status spans.
//   The shelf (#btn-shelf → thOpen+thShelf) renders one .sh-card per /api/sessions run,
//   each sealed reel carrying a .sh-verdict line.

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HIS_PORTS = new Set([17771, 17772]);
const DEMO_DIR = path.dirname(fileURLToPath(import.meta.url));
let _private = null;
let _sand = null;
// REG-2276. The same 8x8 still render_check seeds. Synthetic. Never a copy of his journal.
const SHELF_STILL_B64 = (
  '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABsSFBcUERsXFhceHBsgKEIrKCUlKFE6PTBCYFVlZF9VXVtqeJmBanGQ'
  + 'c1tdhbWGkJ6jq62rZ4C8ybqmx5moq6T/2wBDARweHigjKE4rK06kbl1upKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSk'
  + 'pKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKT/wAARCAAIAAgDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAA'
  + 'AAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFAEBAAAAAAAAAAAAAAAAAAAAAf/EABQRAQAAAAAAAAAAAAAAAAAA'
  + 'AAD/2gAMAwEAAhEDEQA/AIAAL//Z');

let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch (e) {
  // fallback: resolve via CommonJS require if the bare ESM import ever fails
  const { createRequire } = await import('node:module');
  const require = createRequire(import.meta.url);
  ({ chromium } = require('playwright'));
}

const PANE_TABS = ['forge', 'crafts', 'funi', 'fsets', 'tools', 'vault', 'd2jsp'];  // REG-3285 - the D2JSP tab (v3858) shipped with J1 never walking it; his console's eagle row 'surfaces agree' said so  // v1377 — 'session' removed: Sessions is now console-native (data-view=sessions), no longer opens a bible pane
// v2092 — 'vault' added. The console got a Vault tab between Tools and TV·D this ship, and this
// list is what J1 SHELL MATRIX actually walks — so without it the new tab would have shipped
// with the matrix reporting a confident green about the four tabs it already knew.
// A gate is blind to what its fixture never exercises. [[gate-blind-to-unexercised-input]]

const results = [];
function record(name, ok, detail) {
  results.push({ name, ok, detail });
  const mark = ok ? '✅' : '❌';
  console.log(`${mark} ${name}${detail ? ' — ' + detail : ''}`);
}

// ── browser-side helpers (stringified into evaluate/waitForFunction) ──────────────
// The engine iframe is same-origin, so page context can read its contentDocument directly.
async function activeBoardTab(page) {
  return page.evaluate(() => {
    const f = document.getElementById('tvd-eng');
    const d = f && f.contentDocument;
    const a = d && d.querySelector('.tab.active');
    return a ? (a.dataset.tab || null) : null;
  });
}
function shellOpen(page) {
  return page.evaluate(() => document.body.classList.contains('shell-open'));
}
function headRect(page) {
  return page.evaluate(() => {
    const r = document.getElementById('head-tabs').getBoundingClientRect();
    return { top: r.top, left: r.left };
  });
}
async function goHome(page) {
  if (await shellOpen(page)) {
    await page.click('#head-tabs .ht[data-tab="tvd"]');
    await page.waitForFunction(() => !document.body.classList.contains('shell-open'), null, { timeout: 8000 });
  }
  /* REG-2129 - AND LEAVE THE SESSIONS VIEW. Sessions is console-native (data-view=sessions, no shell-open), and his console
     opens on it, so this returned on the Sessions view: the TV.D home dash stayed hidden and J3's tally chip measured 0x0 -
     "page.click: Timeout 30000ms exceeded" refused the v3632 and v3633 pushes. A private console that opened on TV.D passed
     the same journey. Leave it the way J8 does: the TV.D tab, then wait for the view to change. */
  if (await page.evaluate(() => document.body.getAttribute('data-view') === 'sessions')) {
    await page.click('#head-tabs .ht[data-tab="tvd"]');
    await page.waitForFunction(() => document.body.getAttribute('data-view') !== 'sessions', null, { timeout: 8000 });
  }
}

// Warm up: give the engine iframe a chance to boot bible JS so the first pane route is snappy
// (best-effort — shellOpen() retries switchTab for ~4s anyway, so this is never fatal).
async function warmEngine(page) {
  /* v2112 — WAIT FOR WHAT J1 ACTUALLY ASSERTS, AND SAY SO IF IT NEVER ARRIVES.
     This waited only for `switchTab` to be a function, then swallowed its own timeout with
     "the click retry loop will cover it". On a COLD console — a gate run seconds after a
     relaunch — switchTab exists while the board's tab markup does not, so J1 clicked six
     panes and timed out waiting for `.tab.active` to follow. The run reported
     `j1_shellMatrix — page.waitForFunction: Timeout 12000ms exceeded`, which names the
     symptom and hides the cause; the same journey then passed twice in a row at 5.7s
     against a warm console.
     Silence is not evidence: a warm-up that gives up quietly turns a boot race into a
     mystery failure in an unrelated journey. [[feedback-silence-is-not-evidence]] */
  try {
    await page.waitForFunction(() => {
      const f = document.getElementById('tvd-eng');
      const w = f && f.contentWindow;
      if (!w || typeof w.switchTab !== 'function') return false;
      const d = f.contentDocument;
      // the tab strip is what every pane journey steers by — an engine with no tabs is not warm
      return !!(d && d.querySelector('.tab.active'));
    }, null, { timeout: 25000 });
  } catch (_) {
    console.log('⚠ BOOT — the board engine did not finish loading in 25s. The pane journeys '
      + 'below steer by its tab strip, so treat any J1/J2 failure as THIS, not as a routing bug.');
  }
}

// ── the six journeys ──────────────────────────────────────────────────────────────
async function j1_shellMatrix(page) {
  const name = 'J1 SHELL MATRIX';
  await goHome(page);
  for (const tab of PANE_TABS) {
    await page.click(`#head-tabs .ht[data-tab="${tab}"]`);
    try {
      await page.waitForFunction((t) => {
        if (!document.body.classList.contains('shell-open')) return false;
        const f = document.getElementById('tvd-eng');
        const d = f && f.contentDocument;
        const a = d && d.querySelector('.tab.active');
        return !!(a && a.dataset.tab === t);
        /* v2112 — 30s, not 12s. This gate runs INSIDE hooks/pre-push, immediately after the
           full tv suite and alongside the Playwright smoke, so the machine is loaded and the
           board is promoting a 5.9MB document into an iframe. Measured: 8/9 at ~17s during the
           gate, 9/9 five times in a row at ~6s standalone, with no product difference between
           them. The budget was the failure, and a per-pane budget that only holds on an idle
           machine is a race the gate loses at exactly the moment it matters. */
      }, tab, { timeout: 30000 });
    } catch (e) {
      /* v2112 — NAME THE PANE. This threw `page.waitForFunction: Timeout 12000ms exceeded`,
         which says a wait expired and nothing about WHICH of six panes, what the board was
         showing instead, or whether the shell had even opened — so the same message covers a
         routing bug, a cold engine and a click that missed. Report the state at the moment it
         gave up. [[feedback-verify-not-proxy]] */
      const st = await page.evaluate(() => {
        const f = document.getElementById('tvd-eng');
        let d = null; try { d = f && f.contentDocument; } catch (_) {}
        const a = d && d.querySelector('.tab.active');
        return {
          shell: document.body.classList.contains('shell-open'),
          doc: !!d,
          active: a ? a.dataset.tab : null,
          tabs: d ? d.querySelectorAll('.tabs .tab').length : -1,
        };
      }).catch(() => null);
      /* v2112 — AND ASK WHETHER THE ROUTE ITSELF STILL WORKS. "the pane did not activate"
         covers two opposite causes: the click never reached the router, or the router ran and
         the board refused. Calling switchTab directly separates them — if the board moves when
         asked in-process, the defect is upstream of the board, and if it does not, it is the
         board. Suspect the instrument before the subject. [[feedback-suspect-the-instrument]] */
      const probe = await page.evaluate((t) => {
        const f = document.getElementById('tvd-eng');
        const w = f && f.contentWindow;
        const out = { hasSwitch: !!(w && typeof w.switchTab === 'function'), threw: null, after: null };
        if (!out.hasSwitch) return out;
        try { w.switchTab(t); } catch (e) { out.threw = String((e && e.message) || e); }
        try {
          const a = f.contentDocument.querySelector('.tab.active');
          out.after = a ? a.dataset.tab : null;
        } catch (e) { out.after = '(unreadable)'; }
        return out;
      }, tab).catch(() => null);
      throw new Error(`pane "${tab}" never activated — shell-open=${st && st.shell}, `
        + `board doc=${st && st.doc}, board shows="${st && st.active}", `
        + `board tab count=${st && st.tabs} · direct switchTab: exists=${probe && probe.hasSwitch}`
        + `, threw=${probe && probe.threw}, board then showed="${probe && probe.after}"`);
    }
  }
  // then TV·D → shell closes and the stage is visible
  await page.click('#head-tabs .ht[data-tab="tvd"]');
  await page.waitForFunction(() => {
    if (document.body.classList.contains('shell-open')) return false;
    const s = document.getElementById('stage');
    return !!(s && s.getClientRects().length);
  }, null, { timeout: 8000 });
  record(name, true, `${PANE_TABS.length} panes routed [${PANE_TABS.join(', ')}] + tvd→stage`);
}

async function j2_alignment(page) {
  const name = 'J2 ALIGNMENT INVARIANT';
  await goHome(page);
  const home1 = await headRect(page);
  await page.click('#head-tabs .ht[data-tab="forge"]');
  await page.waitForFunction(() => document.body.classList.contains('shell-open'), null, { timeout: 8000 });
  // ⚠⚠ `await page.waitForFunction(() => true)` STOOD HERE AND WAITED FOR NOTHING. It resolves on
  // its first poll, so the comment above it ("let the fixed-topbar layout settle a paint") described
  // an intention the code never carried out — every rect below was read off possibly-unsettled
  // layout. That is why this gate can report `home↔home Δ(top 0.92)`: home measured against ITSELF,
  // twice, disagreeing. It blocked a push on 2026-09-03 and did not reproduce in three consecutive
  // local runs (10/10, Δ 0.00 each time).
  //
  // A double requestAnimationFrame is an actual settle: the first frame flushes the pending style
  // and layout, the second runs after that frame has been painted.
  //
  // ⚠ THE TOLERANCE IS UNTOUCHED, DELIBERATELY. Widening TOL would have made the symptom go away
  // and made the gate weaker — a real 0.92px drift would then pass forever. This makes the
  // measurement honest and leaves the bar exactly where it was, so a genuine misalignment still
  // fails. [[feedback-blind-fixture-green-gate]] [[regression-guard]]
  const settle = () => page.evaluate(
    () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  await settle();
  const pane = await headRect(page);
  await goHome(page);
  await settle();                    // home2 is the half that actually disagreed; settle it too
  const home2 = await headRect(page);
  const dTop1 = Math.abs(pane.top - home1.top), dLeft1 = Math.abs(pane.left - home1.left);
  const dTop2 = Math.abs(home2.top - home1.top), dLeft2 = Math.abs(home2.left - home1.left);
  const TOL = 0.5;
  const ok = dTop1 <= TOL && dLeft1 <= TOL && dTop2 <= TOL && dLeft2 <= TOL;
  const detail = `home↔pane Δ(top ${dTop1.toFixed(2)}, left ${dLeft1.toFixed(2)}) · home↔home Δ(top ${dTop2.toFixed(2)}, left ${dLeft2.toFixed(2)})`;
  if (!ok) throw new Error(detail);
  record(name, true, detail);
}

async function j14_outputPanesStayBounded(page) {
  const name = 'J14 AN OUTPUT PANE MAY NOT BURY THE PANEL';
  await goHome(page);
  // ⚠ REPORTED FROM HIS SCREEN, NOT BY A GATE. Konyo: "i clicked on ledger under advanced..
  // something traps me in the settings and is bugged.. now it suddenly not rendering the advanced".
  // MEASURED: #ledger-out rendered 3224px into a rail whose visible height is 705px, taking the
  // rail's scrollHeight to 5114 — 4.6 screens of output between him and every control below it,
  // ADVANCED's own included. The rail scrolls, so he was not frozen; he was buried.
  //
  // This asserts the LAW — a pane that overflows carries its own scroll and does not push its
  // container past a sane height — over EVERY *-out pane in the rail, not just the one he clicked.
  // All five declared neither max-height nor overflow; ledger was only the loudest.
  const before = await page.evaluate(() => {
    const rail = document.querySelector('aside.rail');
    return rail ? Math.round(rail.scrollHeight) : null;
  });
  if (before == null) { record(name, true, 'no rail on this view'); return; }

  const clicked = await page.evaluate(() => {
    const b = document.getElementById('btn-ledger');
    if (!b) return false;
    b.click();
    return true;
  });
  if (!clicked) { record(name, true, 'no ledger button on this view'); return; }
  await page.waitForTimeout(6000);

  const got = await page.evaluate(() => {
    const rail = document.querySelector('aside.rail');
    const panes = Array.from(document.querySelectorAll('aside.rail [id$="-out"]')).map((p) => {
      const cs = getComputedStyle(p);
      return {
        id: p.id,
        shown: cs.display !== 'none',
        clientH: Math.round(p.clientHeight),
        scrollH: Math.round(p.scrollHeight),
        overflows: p.scrollHeight > p.clientHeight + 1,
        scrolls: /auto|scroll/.test(cs.overflowY),
        capped: cs.maxHeight !== 'none',
      };
    });
    return { railScrollH: Math.round(rail.scrollHeight), vh: window.innerHeight, panes };
  });

  // ⚠⚠ THE FIRST VERSION OF THIS CHECK COULD NOT FAIL, AND ONLY THE RED PROOF SAID SO.
  // It flagged panes where `scrollHeight > clientHeight && !scrolls`. But an UNBOUNDED pane does
  // not overflow — it GROWS to fit, so scrollHeight === clientHeight and the filter never fired.
  // Measured with the fix removed: "0/4 panes bounded" and the journey still passed. I was testing
  // the symptom of the FIXED state (a scrollable pane) instead of the law.
  // The law is about SIZE RELATIVE TO THE PANEL: a pane taller than half the viewport that cannot
  // scroll itself is one that pushes everything below it away. [[sabotage-is-usually-the-wrong-one]]
  const unbounded = got.panes.filter((p) => p.shown && !p.scrolls && p.clientH > got.vh * 0.55);
  if (unbounded.length) {
    throw new Error(`${unbounded.map((p) => '#' + p.id + ' (' + p.clientH + 'px tall in a '
      + got.vh + 'px viewport, no scroll of its own)').join(', ')} — a pane that tall with nowhere `
      + `to go pushes every control below it off the panel, which is what "trapped in the `
      + `settings" looks like`);
  }
  // and the rail itself must not have become absurd. MEASURED both ways on his console so the
  // threshold sits between two real states rather than being guessed: fixed 2.6 screens, broken
  // 5.8. A cap of 6 was ABOVE the broken value and let it through — a threshold above the ceiling
  // is an absent one. 4 separates them with room either side.
  // [[feedback-threshold-above-the-ceiling]]
  const cap = got.vh * 4;
  if (got.railScrollH > cap) {
    throw new Error(`the rail grew to ${got.railScrollH}px (${(got.railScrollH / got.vh).toFixed(1)}`
      + ` screens) after one click; anything below the output is now unreachable in practice`);
  }
  record(name, true, `rail ${before} -> ${got.railScrollH}px `
    + `(${(got.railScrollH / got.vh).toFixed(1)} screens), `
    + `${got.panes.filter((p) => p.capped).length}/${got.panes.length} panes bounded`);
}

async function j15_heartArithmeticIsTrue(page) {
  const name = 'J15 THE HEART MAY NOT PRINT FALSE ARITHMETIC';
  await goHome(page);
  // ⚠⚠ FOUND ON REAL PIXELS, NOT BY A GATE. The heart printed, under a CORRECT verdict:
  //     prune.arm   42/42 refused · 0.916 < 0.839
  // 0.916 is not less than 0.839. The sign came from `(open ? ' ≥ ' : ' < ')` — derived from the
  // lock's STATE rather than from the two numbers beside it — and prune.arm is LOCKED for a
  // reason that has nothing to do with its score: it clears the bar (0.916 ≥ 0.839) and is held
  // by CONFLUENCE, its evidence being all one kind (1.00 against a kinds bar of 1.80). A right
  // conclusion with a false number under it is the exact shape he keeps catching.
  //
  // This asserts the LAW over every lock the heart draws: if the panel prints "a ≥ b" then a ≥ b,
  // and if it prints "a < b" then a < b. It does not care which locks exist or what they score.
  const rows = await page.evaluate(async () => {
    if (typeof window._heartOpen !== 'function') return null;
    window._heartOpen();
    await new Promise(r => setTimeout(r, 2500));
    const ov = document.getElementById('heart-ov');
    if (!ov || ov.hidden) return null;
    return [].slice.call(ov.querySelectorAll('svg text'))
      .map(t => (t.textContent || '').trim())
      .filter(s => / [≥<] /.test(s));
  });
  if (rows == null) { record(name, true, 'the heart did not open on this view'); return; }
  if (!rows.length) { record(name, true, 'no lock printed an inequality'); return; }
  const bad = [];
  for (const line of rows) {
    const m = line.match(/([0-9]*\.?[0-9]+)\s+([≥<])\s+([0-9]*\.?[0-9]+)/);
    if (!m) continue;
    const a = parseFloat(m[1]), sign = m[2], b = parseFloat(m[3]);
    const claimed = sign === '≥' ? (a >= b) : (a < b);
    if (!claimed) bad.push(line);
  }
  if (bad.length) {
    throw new Error(`the heart printed arithmetic that is not true: ${bad.join(' | ')}`);
  }
  record(name, true, `${rows.length} inequality line(s), all true`);
}

async function j16_twoCountsMustNameTheirQuantity(page) {
  const name = 'J16 TWO NUMBERS FOR ONE TAB MUST SAY WHAT EACH COUNTS';
  await goHome(page);
  // ⚠⚠ CF-16, FOUND BY A COLD CROSS-FAMILY READ OF THE PIXELS. The heart showed
  //     runeword · 105 names          (chronicle routes — the names in that route's ROSTER)
  //     runewords · 99 reported as the total   (fleet lanes — the CHRONICLE TOTAL, his v2192 ruling)
  // and the eye called it a contradiction. It was reading fairly: sets agree at 135, so the odd
  // one out looks like a bug. Both numbers are right; the panel just never said they measure
  // different things. Uniques does the same, 398 against 403.
  //
  // The law: if two route sets print DIFFERENT numbers for the same tab, they must not print them
  // under the SAME unit word. It does not pin any count — the rosters and the rulings are free to
  // move — only that a reader can tell which quantity each number is.
  const rows = await page.evaluate(async () => {
    if (typeof window._heartOpen !== 'function') return null;
    window._heartOpen();
    await new Promise(r => setTimeout(r, 2500));
    const ov = document.getElementById('heart-ov');
    if (!ov || ov.hidden) return null;
    return [].slice.call(ov.querySelectorAll('.hrt-sec')).flatMap(sec => {
      const head = (sec.querySelector('.hrt-h') || {}).textContent || '';
      return [].slice.call(sec.querySelectorAll('*'))
        .map(e => (e.childElementCount === 0 ? (e.textContent || '').trim() : ''))
        .filter(t => /^(runeword|runewords|set|sets|unique|uniques)\s*·\s*\d+/.test(t))
        .map(t => ({ head, t }));
    });
  });
  if (rows == null) { record(name, true, 'the heart did not open on this view'); return; }
  if (rows.length < 2) { record(name, true, `only ${rows.length} counted row(s) on screen`); return; }

  // group by the tab CONCEPT, not its spelling — runeword and runewords are one thing
  const seen = new Map();
  for (const { t } of rows) {
    const m = t.match(/^(runewords?|sets?|uniques?)\s*·\s*(\d+)\s*(.*)$/);
    if (!m) continue;
    const concept = m[1].replace(/s$/, '');
    const count = parseInt(m[2], 10);
    const unit = (m[3] || '').trim();
    if (!seen.has(concept)) seen.set(concept, []);
    seen.get(concept).push({ count, unit, t });
  }
  // ⚠⚠ THE FIRST VERSION OF THIS CHECK COULD NOT FAIL, and it took feeding it the shipped rows
  // to find that out. It asserted the two units must DIFFER — but they already did:
  // "runeword · 105 names" against "runewords · 99 reported as the total". Different words, and
  // still unreadable, because "names" never says WHOSE names. Testing for difference tested a
  // condition the defect already satisfied. What actually goes wrong is a unit that does not
  // IDENTIFY its quantity, so that is what is checked. [[source-reading-guard]]
  const VAGUE = new Set(['', 'names', 'items', 'rows', 'entries', 'total', 'counted']);
  const bad = [];
  for (const [concept, entries] of seen) {
    const counts = new Set(entries.map(e => e.count));
    if (counts.size < 2) continue;                    // they agree; nothing to disambiguate
    for (const e of entries) {
      if (VAGUE.has(e.unit.toLowerCase())) {
        bad.push(`${concept}: "${e.t}" — the unit ${JSON.stringify(e.unit)} does not say which `
          + `quantity this is, and another surface reports a different number for the same tab `
          + `(${[...counts].join(' vs ')})`);
      }
    }
  }
  if (bad.length) {
    throw new Error(`two different numbers for one tab, under the same unit word — a reader `
      + `cannot tell these are different quantities: ${bad.join(' | ')}`);
  }
  record(name, true, `${seen.size} tab concept(s), every differing pair names its quantity`);
}

async function j13_overflowSaysSo(page) {
  const name = 'J13 OVERFLOW SAYS SO';
  await goHome(page);
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  const got = await page.evaluate(() => {
    const b = document.querySelector('.brain, #brain');
    if (!b) return { skip: 'no AI READS strip on this view' };
    const cs = getComputedStyle(b);
    const mask = (cs.maskImage && cs.maskImage !== 'none') ? cs.maskImage
      : (cs.webkitMaskImage && cs.webkitMaskImage !== 'none') ? cs.webkitMaskImage : '';
    return {
      overflows: b.scrollHeight > b.clientHeight + 1,
      boxH: Math.round(b.clientHeight), scrollH: Math.round(b.scrollHeight),
      hasMask: !!mask,
    };
  });
  if (got.skip) { record(name, true, got.skip); return; }
  // ⚠ the law is CONDITIONAL: only a strip that actually hides content owes an affordance. A
  // strip showing everything it has must NOT be faded — that would dim a complete list for no
  // reason, which is the mirror defect.
  if (got.overflows && !got.hasMask) {
    throw new Error(`the strip hides content (${got.scrollH}px of rows in ${got.boxH}px) and its `
      + `edge gives no sign of it — a half-drawn row with no affordance reads as a rendering bug`);
  }
  record(name, true, got.overflows
    ? `hides content (${got.scrollH}px in ${got.boxH}px) and its edge says so`
    : `shows everything it has (${got.scrollH}px in ${got.boxH}px), no affordance owed`);
}

async function j12_heartNoEcho(page) {
  const name = 'J12 HEART · NO ECHOED ROWS';
  await goHome(page);
  // ⚠ calls the RENDER SEAM directly with synthetic vessels. Opening the real heart costs an
  // /api/heart derivation (seconds) and would make this journey depend on his live census — the
  // law under test is about the RENDERER, so it is fed rows chosen to exercise it.
  const got = await page.evaluate(() => {
    if (typeof window._heartRender !== 'function') return { skip: 'no _heartRender seam' };
    const mk = (n, state, why, watcher) => ({ name: n, state, why, watcher, score: null });
    const SHARED = 'it runs and NOTHING watches it.';
    const d = {
      ok: true, counts: { FLOWING: 0, WATCHED: 2, DARK: 3, UNKNOWN: 0 }, locks: [], vessels: [
        mk('a_loop', 'DARK', SHARED), mk('b_loop', 'DARK', SHARED), mk('c_loop', 'DARK', SHARED),
        mk('d_loop', 'WATCHED', 'watched, but nothing has tried to break it', 'w-one'),
        mk('e_loop', 'WATCHED', 'watched, but nothing has tried to break it', 'w-two'),
      ],
    };
    const box = document.createElement('div');
    box.innerHTML = window._heartRender(d);
    const rows = [...box.querySelectorAll('.hrt-row')].map(r => {
      const w = r.querySelector('.hrt-w');
      return (w ? w.textContent : '').trim();
    }).filter(Boolean);
    const seen = {};
    rows.forEach(t => { seen[t] = (seen[t] || 0) + 1; });
    const echoed = Object.keys(seen).filter(t => seen[t] > 1);
    const groups = [...box.querySelectorAll('.hrt-grp')].length;
    return { rows: rows.length, echoed, groups, sample: rows.slice(0, 3) };
  });
  if (got.skip) { record(name, true, got.skip); return; }
  if (got.echoed && got.echoed.length) {
    throw new Error(`a row explanation is repeated verbatim: "${got.echoed[0].slice(0, 60)}"`);
  }
  if (!got.groups) {
    throw new Error('no group header rendered — the shared sentence was dropped instead of hoisted');
  }
  record(name, true, `${got.groups} group header(s), ${got.rows} detail row(s), none echoed`);
}

async function j11_receiptVerbs(page) {
  const name = 'J11 RECEIPT VERBS';
  await goHome(page);
  // the AI READS feed lives on the console shell; give it a beat to fill
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  const got = await page.evaluate(() => {
    const ts = [...document.querySelectorAll('.rcpt-t')];
    const doubled = [];
    for (const t of ts) {
      const s = (t.textContent || '').trim();
      // "routed · ROUTED personal" — the same verb twice, once as the kind and once inside the
      // backend's own label. Compare the first two words case-insensitively, ignoring separators.
      const w = s.split(/[\s·]+/).filter(Boolean);
      if (w.length >= 2 && w[0].toLowerCase() === w[1].toLowerCase()) doubled.push(s.slice(0, 70));
    }
    return { n: ts.length, doubled };
  });
  if (!got.n) { record(name, true, 'no receipt lines rendered — nothing to check'); return; }
  if (got.doubled.length) {
    throw new Error(`${got.doubled.length}/${got.n} receipt line(s) print their verb twice: `
      + got.doubled.slice(0, 2).join(' | '));
  }
  record(name, true, `${got.n} receipt line(s), none printing its verb twice`);
}

async function j3_tally(page) {
  const name = 'J3 TALLY ENGINE';
  await goHome(page);
  // v1380.5 — TALLIES lives in the off-air RECORD zone; if a prior journey left ON AIR,
  // home-dash is hidden and the chip never appears. End the session first.
  const st = await page.evaluate(() => document.body.getAttribute('data-state'));
  if (st === 'on' || st === 'sim' || st === 'stopping') {
    try {
      await page.click('#btn-on');
      await page.waitForFunction(
        () => document.body.getAttribute('data-state') === 'off',
        null,
        { timeout: 20000 }
      );
    } catch (_) { /* best-effort; selector wait below is the real gate */ }
  }
  // also leave Theatre if open (stage exclusivity)
  await page.evaluate(() => {
    try { if (window.TH && TH.open && typeof thClose === 'function') thClose(); } catch (e) {}
  });
  await page.waitForSelector('.hd-chip.tly-btn', { timeout: 12000 });
  await page.click('.hd-chip.tly-btn');
  await page.waitForFunction(() => {
    const ov = document.getElementById('tly-ov');
    if (!ov || ov.hidden) return false;
    return getComputedStyle(ov).display !== 'none';
  }, null, { timeout: 8000 });
  // filter tabs render from /api/tallies (works even with zero shots — counts show · 0)
  await page.waitForSelector('#tly-tabs .tly-tab', { timeout: 8000 });
  await page.locator('#tly-tabs .tly-tab', { hasText: 'RUNES' }).click();
  await page.waitForFunction(() => {
    const on = document.querySelector('#tly-tabs .tly-tab.on');
    return !!(on && /RUNES/.test(on.textContent || ''));
  }, null, { timeout: 5000 });
  const wasShellOpen = await shellOpen(page);
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => {
    const ov = document.getElementById('tly-ov');
    return !ov || ov.hidden;
  }, null, { timeout: 5000 });
  const nowShellOpen = await shellOpen(page);
  // Esc that closed the overlay must not have leaked a shell toggle (opened from home).
  if (!wasShellOpen && nowShellOpen) throw new Error('Esc closing the tally overlay leaked into shell-open');
  record(name, true, 'chip→overlay, 🪨 RUNES active moved, Esc closed clean (no shell side-effect)');
}

async function j4_escDiscipline(page) {
  const name = 'J4 ESC DISCIPLINE';
  await goHome(page);
  // open a pane
  await page.click('#head-tabs .ht[data-tab="forge"]');
  await page.waitForFunction(() => document.body.classList.contains('shell-open'), null, { timeout: 8000 });
  // Escape with no overlays up → back home (stage visible)
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => {
    if (document.body.classList.contains('shell-open')) return false;
    const s = document.getElementById('stage');
    return !!(s && s.getClientRects().length);
  }, null, { timeout: 8000 });
  // reopen a pane (best-effort; no forced board overlays / game data)
  await page.click('#head-tabs .ht[data-tab="forge"]');
  await page.waitForFunction(() => document.body.classList.contains('shell-open'), null, { timeout: 8000 });
  await goHome(page); // leave clean
  record(name, true, 'Escape (no overlay) returned home; pane reopened cleanly');
}

async function j5_threeEyes(page) {
  const name = 'J5 THREE EYES';
  const r = await page.evaluate(() => {
    const ids = ['eye-live', 'eye-second', 'eye-kai'];
    const eyes = ids.map((id) => !!document.getElementById(id));
    const status = ids.map((id) => {
      const s = document.getElementById(id + '-s');
      return s ? (s.textContent || '').trim() : '';
    });
    const det = document.querySelector('details.sig-adv');
    return {
      eyes, status,
      detailsExists: !!det,
      detailsClosed: det ? det.open === false : null,
      // v2192 — the SHIPPED default, read off the markup rather than the live node, so a stored
      // preference from a previous run cannot make this pass or fail by accident.
      detailsOpenDefault: det ? det.hasAttribute('open') : null,
    };
  });
  if (!r.eyes.every(Boolean)) throw new Error(`missing eye element(s): ${JSON.stringify(r.eyes)}`);
  if (!r.status.every((t) => t.length > 0)) throw new Error(`empty eye status text: ${JSON.stringify(r.status)}`);
  if (!r.detailsExists) throw new Error('⚙ advanced <details> missing');
  // ⚠ v2192 — THE RULING FLIPPED, AND IT IS HIS RULING BOTH TIMES. This asserted the panel
  // defaults CLOSED. Konyo, 2026-08-27: "the advanced settings keep vanishing.. needs to be
  // hardcodded." A bare <details> has no memory, so every page load closed it — and v2180 made
  // auto-relaunch actually work, so the window now reloads itself whenever a build lands and the
  // panel shut every single time. The law this guards is not "closed", it is "the console does
  // what he last told it to": OPEN by default, and a deliberate close still persists.
  if (r.detailsOpenDefault !== true) {
    throw new Error('⚙ advanced <details> does not default OPEN — it will vanish on every '
      + 'auto-relaunch, which is what he reported');
  }
  record(name, true, `3 eyes present, status=[${r.status.join(' | ')}], ⚙ advanced open by default`);
}

async function j6_signalPanel(page) {
  const name = 'J6 SIGNAL PANEL';
  const r = await page.evaluate(() => {
    const panel = document.querySelector('.signal');
    const panelText = panel ? (panel.textContent || '') : '';
    const rows = panel ? Array.from(panel.querySelectorAll('.row')) : [];
    // case-sensitive: 'BRIDGE' must not appear as a signal ROW label anymore
    const bridgeRow = rows.some((el) => (el.textContent || '').indexOf('BRIDGE') !== -1);
    return {
      hasPanel: !!panel,
      hasSignal: panelText.indexOf('Signal') !== -1,
      hasWatching: panelText.indexOf('Watching') !== -1,
      bridgeRow,
    };
  });
  if (!r.hasPanel) throw new Error('.signal panel missing');
  if (!r.hasSignal) throw new Error("humanized 'Signal' label not found in panel");
  if (!r.hasWatching) throw new Error("humanized 'Watching' label not found in panel");
  if (r.bridgeRow) throw new Error("'BRIDGE' still present as a signal row label");
  record(name, true, "'Signal' + 'Watching' present, no 'BRIDGE' row label");
}

async function j7_shelfStory(page) {
  const name = 'J7 SHELF STORY';
  await goHome(page);
  const shellBefore = await shellOpen(page); // home → false
  /* REG-1916 — TWO WAITS, TWO BOUNDS. This journey refused the v3597 and v3601 pushes (and 2 of 13 over 09-27..29) at
     the 15 s wait below. MEASURED on his console mid chronicle sweep, 2026-10-07: GET /api/sessions answered in 9.2 s
     cold and 1.1 s warm (663 KB). The 15 s bound was paying for the SERVER's cold answer and the shelf's render at once,
     on a console the hook itself says is loaded. So the server is asked first, under its own measured 60 s bound and
     with the time printed, and the 15 s bound below covers the render alone. A server that does not answer in 60 s is
     still a refusal - and now one that names which half was slow. */
  const warm = await page.evaluate(async () => {
    const t0 = Date.now();
    const bound = new Promise((res) => setTimeout(() => res({ ok: false, why: 'no answer in 60 s' }), 60000));
    const ask = fetch('/api/sessions', { cache: 'no-store' })
      .then(async (r) => { await r.text(); return { ok: r.ok, why: r.ok ? '' : ('HTTP ' + r.status) }; })
      .catch((e) => ({ ok: false, why: String(e && e.message || e) }));
    const got = await Promise.race([ask, bound]);
    return Object.assign({ ms: Date.now() - t0 }, got);
  });
  if (!warm.ok) throw new Error(`/api/sessions did not answer (${warm.why}, ${warm.ms} ms) - the server half, not the shelf`);
  // 📚 The Shelf console button: thOpen() (loads TH.sessions from /api/sessions) then thShelf(true)
  await page.click('#btn-shelf');
  // the shelf overlay #th-shelfov renders one .sh-card per recorded session
  await page.waitForFunction(() => {
    const ov = document.getElementById('th-shelfov');
    if (!ov || ov.hidden) return false;
    return ov.querySelectorAll('.sh-card').length > 0;
  }, null, { timeout: 15000 });
  const r = await page.evaluate(() => {
    // seal-verdict markers + the v940 REGRET ENGINE's two (💔 regrets / 🔬 judged). ⚠ 2026-09-29: the list
    // predated v940, and his shelf never showed a card whose ONLY verdict was the judge until today -
    // v3523's push #4 was refused at 113m by "🔬 2 judged", a verdict the page has rendered since July.
    // The markers are the ones control_ui.html pushes into vparts; nothing else is admitted.
    const glyphs = ['🛡', '🚨', '🧠', '📸', '💔', '🔬'];
    const cards = document.querySelectorAll('#th-shelfov .sh-card');
    const verdicts = Array.from(document.querySelectorAll('#th-shelfov .sh-verdict'));
    // any rendered verdict line must carry at least one verdict glyph; zero-verdict
    // (unsealed) cards simply have no .sh-verdict span and are tolerated.
    const bad = verdicts.find((v) => {
      const t = v.textContent || '';
      return !glyphs.some((g) => t.indexOf(g) !== -1);
    });
    return {
      cards: cards.length,
      verdicts: verdicts.length,
      bad: bad ? (bad.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60) : null,
    };
  });
  if (r.cards < 1) throw new Error('shelf rendered zero .sh-card');
  if (r.bad) throw new Error(`.sh-verdict missing a 🛡/🚨/🧠/📸 glyph: "${r.bad}"`);
  // ⚠ REG-1944 (v3603) - THE SHELF OPENED FROM THE CONSOLE'S SHELF BUTTON IS THE DOOR, AND HIDING IT CLOSES EVERYTHING.
  // This journey used to hide the overlay with #th-shelf and then fold the theatre with #th-close. Since REG-1944
  // (a door shelf hidden bare left an empty black stage captioned 'the shelf') #th-shelf on a door closes the theatre
  // too, so #th-close was hidden and the click waited 30 s for a button that can no longer be there - the v3603 push
  // was refused on it. The journey now ASSERTS the rule: one #th-shelf, and the console is home.
  await page.click('#th-shelf');
  await page.waitForFunction(() => {
    const ov = document.getElementById('th-shelfov');
    return !ov || ov.hidden;
  }, null, { timeout: 5000 });
  await page.waitForFunction(() => {
    const th = document.getElementById('theatre');
    if (!th || !th.hidden) return false;
    if (document.body.classList.contains('shell-open')) return false;
    const s = document.getElementById('stage');
    return !!(s && s.getClientRects().length);
  }, null, { timeout: 6000 });
  const shellAfter = await shellOpen(page);
  if (shellBefore !== shellAfter) throw new Error('shelf journey left the shell state changed');
  record(name, true, `${r.cards} .sh-card, ${r.verdicts} verdict line(s) all glyph-tagged, closed → home (sessions answered in ${warm.ms} ms)`);
}

// v1378 — J8: the console-native Sessions flagship. 'session' nav sets data-view=sessions and
// shows the hunt hub as the console home (NO bible pane / shell-open); TV·D restores the cockpit.
async function j8_sessionsFlagship(page) {
  const name = 'J8 SESSIONS FLAGSHIP';
  await goHome(page);
  await page.click('#head-tabs .ht[data-tab="session"]');
  await page.waitForFunction(() => {
    if (document.body.classList.contains('shell-open')) return false;          // console-native, not a bible pane
    if (document.body.getAttribute('data-view') !== 'sessions') return false;
    const hunt = document.querySelector('.zone-hunt'), stage = document.getElementById('stage');
    return hunt && getComputedStyle(hunt).display !== 'none' && (!stage || getComputedStyle(stage).display === 'none');
  }, null, { timeout: 8000 });
  await page.click('#head-tabs .ht[data-tab="tvd"]');
  await page.waitForFunction(() => {
    if (document.body.getAttribute('data-view') === 'sessions') return false;
    const s = document.getElementById('stage');
    return !!(s && s.getClientRects().length);
  }, null, { timeout: 8000 });
  record(name, true, 'session→data-view=sessions (hunt shown, stage hidden, no shell) · tvd→cockpit');
}


// v1578 — J9: the TERROR ZONE flagship. Three things had to become true at once and each one was
// invisible on its own: the art has to come from the GAME (not the diablo2.io act pictures that
// covered 13 of 67 zones), a three-zone rotation must not render a chip called "and <Zone>", and a
// weak zone must LOOK weak. The route is stubbed with a rotation chosen to exercise all three:
// a dense prime, a boss-prime that density alone would have greyed, and two thin Act 1 zones.
async function j9_terrorZoneFlagship(page) {
  const name = 'J9 TERROR ZONE FLAGSHIP';
  await page.route('**/api/tz', (r) => r.fulfill({
    status: 200, contentType: 'application/json',
    /* v1641 — THE ROTATION NOW CONTAINS THE CASE KONYO SCREENSHOTTED, WHICH IT NEVER DID.
       The defect is a card carrying an optional `why` subtitle standing taller than one without,
       so LIVE NOW and UP NEXT stop lining up. The old stub could not produce it across the two
       slots: every slot had a why-bearing zone in it (Travincal · The Pit), so both grids grew by
       the same line and the mismatch cancelled out. A gate whose fixture cannot express the bug
       passes for the same reason an empty list passes every assertion about its members.
       LIVE NOW now carries BOTH kinds of why — a TZ_NOTABLE boss line (Travincal · "the Council")
       and a TZ_HINT adjacency line (Ancient's Way · "next door to the Ancient Tunnels") — beside
       two zones with no why at all. UP NEXT carries NONE: Cold Plains (520) and Outer Cloister
       (600) are both in TZ_INFO, both thin, and in neither TZ_NOTABLE nor TZ_HINT. So the two
       slots are asymmetric exactly as he photographed them, and `whyNow`/`whyNext` below assert
       that asymmetry is still there — deleting the why zone to make the gate green now FAILS. */
    body: JSON.stringify({ current: "Stony Tomb, Travincal, Ancient's Way, and Blood Moor",
                           next: 'Cold Plains and Outer Cloister', ts: Date.now() }) }));
  await goHome(page);
  await page.click('#head-tabs .ht[data-tab="session"]');
  /* REG-1998 (the same push, the first rotation) - ">= 5 cards" was already true of the LIVE zones the console painted at
     boot, so after the hour turned (14:00) the journey measured the real terror zones instead of this stub: "no LIVE NOW
     card carries a why", "Travincal was not PRIME". It waits for THIS stub's own zone names now, pressing refresh up to
     3 times, and a stub that never paints is said as that. */
  const _stubNames = ['Stony Tomb', 'Travincal', "Ancient's Way", 'Blood Moor', 'Cold Plains', 'Outer Cloister'];
  let _first = false;
  for (let _try = 0; _try < 3 && !_first; _try++) {
    await page.evaluate(() => { const b = document.getElementById('tz-refresh'); if (b) b.click(); });
    _first = await page.waitForFunction((names) => {
      const shown = [...document.querySelectorAll('#tz-body .tzz b')].map((b) => (b.textContent || '').trim());
      return names.every((n) => shown.includes(n));
    }, _stubNames, { timeout: 10000 }).then(() => true, () => false);
  }
  if (!_first) throw new Error('the stub rotation never painted in 30 s (3 refreshes) - the live zones were on screen, '
                               + 'so nothing below is measured');
  const out = await page.evaluate(() => [...document.querySelectorAll('#tz-body .tzz')].map((z) => ({
    n: (z.querySelector('b') || {}).textContent || '',
    t: [...z.classList].find((c) => ['tzz-prime', 'tzz-good', 'tzz-thin'].includes(c)) || '',
    art: ((z.querySelector('.tzz-art') || {}).style || {}).backgroundImage || '',
    /* v3879 #108 (REG-3358) - a zone may wear ITS OWN MONSTER instead of its zone art: the sprite named for it in TZ_MONSTER
       (each pick sourced in tv/data/monster_art_arreat.json). An <img> whose file is missing removes itself (onerror). */
    mon: (z.querySelector('.tzz-art-mon img.tzz-mon') || { getAttribute: () => '' }).getAttribute('src') || '',
    grey: getComputedStyle(z).filter })));
  const by = (n) => out.find((o) => o.n === n);
  const fail = [];
  // v1580 — PLACEMENT, pinned. Konyo asked twice for this panel at the top of Sessions. v1573
  // answered with `order:-1`, which only sorts a card WITHIN its own zone — and the card was in
  // Ⅲ THE RECORD, so it was hoisted to the top of the BOTTOM zone and rendered at y=613 under
  // three empty placeholders. The CSS said yes and the page said no, and nothing caught it.
  const place = await page.evaluate(() => {
    const el = document.getElementById('hd-tz');
    if (!el) return { missing: true };
    const zone = el.closest('section.zone');
    const ban = zone && zone.querySelector('.zone-banner');
    /* v1641 — MEASURE BOTH SLOTS. Konyo's complaint is "this needs to be symmetric and aligned
       to the other acts at LIVE. you see how its off" — a comparison BETWEEN LIVE NOW and UP
       NEXT. This measured only `.tz-zones-hero`, i.e. LIVE NOW alone, so the one relationship he
       was pointing at was the one thing never looked at. Inside a single grid the v1640 rule
       (`grid-auto-rows:1fr`) really does equalise the rows even though the container is
       auto-height — per CSS Grid §12.7.1 an indefinite container sizes every 1fr track to the
       largest track's max-content — which is why the old one-slot measurement stayed green while
       the panel was visibly uneven. What 1fr can never do is reach ACROSS two sibling grids. */
    const boxes = (sel) => [...document.querySelectorAll(sel)].map((c) => {
      const r = c.getBoundingClientRect();
      return { n: ((c.querySelector('b') || {}).textContent || '').trim(),
               w: Math.round(r.width), h: Math.round(r.height), y: Math.round(r.y),
               /* v1641 — the .tzz-why ELEMENT is now always emitted (it reserves its line even
                  when empty, which is the fix), so its PRESENCE means nothing. A card carries a
                  why only if that line has TEXT — the proxy and the thing are different here. */
               why: !!((c.querySelector('.tzz-why') || {}).textContent || '').trim() };
    });
    const cards = boxes('#tz-body .tz-zones-hero .tzz');
    const nextCards = boxes('#tz-body .tz-slot.next .tzz');
    const all = cards.concat(nextCards);
    const hs = all.map((c) => c.h);
    return {
      /* the fixture guard: if the rotation under test stops containing a why-bearing card beside
         a why-less one, this gate is measuring nothing and must say so rather than pass. */
      whyNow: cards.filter((c) => c.why).length,
      whyNext: nextCards.filter((c) => c.why).length,
      slotSpread: hs.length ? Math.max(...hs) - Math.min(...hs) : 0,
      allBoxes: all.map((c) => (c.why ? '★' : '·') + c.n + ' ' + c.w + 'x' + c.h + '@y' + c.y),
      numeral: ban ? (ban.querySelector('.zb-no') || {}).textContent : null,
      /* v1930 — "FIRST CARD" MEANS FIRST CARD, NOT FIRST CHILD. This asserted
         `zone.children[1] === el`, which silently assumed nothing would ever sit between the zone
         banner and the flagship. v1914 put `#chron-waiting` there — a one-line notice that appears
         only when a sweep is waiting on him, and which he asked for on the tab he lives on. The
         flagship is still the first CARD; it is no longer the second CHILD.
         Measured: children are [zone-banner, chron-waiting, hd-tz, hd-taskforce].
         Compare against the cards, so a notice line cannot fail a layout gate. */
      firstCard: zone
        ? [...zone.children].filter((c) => c.classList.contains('hd-col'))[0] === el
        : false,
      bannerAbove: ban ? ban.getBoundingClientRect().y < el.getBoundingClientRect().y : false,
      fullWidth: Math.round(el.getBoundingClientRect().width)
                 >= Math.round(el.parentElement.getBoundingClientRect().width) - 24,
      equalW: new Set(all.map((c) => c.w)).size === 1,
      equalH: new Set(all.map((c) => c.h)).size === 1,
      /* v1639 — ONE ROW WAS A PROXY, AND IT BECAME A FALSE ONE. This asserted every zone card
         shared a single y, which was right while the hero held all four zones across a ~1400px
         card. v1637/v1639 split the card into LIVE NOW + UP NEXT slots of ~682px each, and four
         cards in one 682px row is exactly what produced the defect Konyo screenshotted: tiles at
         157.75px with THIRTEEN clipped text nodes, zone names rendered at 0px wide ("T a." /
         "O u."). So the honest invariant is not "one row" — it is EVEN rows and NOTHING CLIPPED.
         rowsEven keeps the alignment guarantee (cards sharing a y must share a width and height,
         and there are at most two rows); clipped is the property that actually matters and was
         never asserted at all, which is how the crammed row passed this gate for two versions. */
      /* v1640 — THE SECOND ATTEMPT AT THIS WAS ALSO A LAYOUT ASSUMPTION. `oneRow` was wrong once
         the card split into two slots; the replacement capped rows at TWO, and that failed on a
         perfectly even stack — measured ["484x139@y456","484x139@y604","484x139@y752"], three
         IDENTICAL cards in a 484px slot that fits one column. How many rows the zones land in is
         the browser's business and changes with the slot width and the size of the rotation. What
         must hold is that the cards agree with each other and nothing is clipped. So: every row's
         cards share a width and a height — no cap on the number of rows. */
      rowsEven: (() => {
        const rows = new Map()
        for (const c of all) { if (!rows.has(c.y)) rows.set(c.y, []); rows.get(c.y).push(c) }
        for (const row of rows.values()) {
          if (new Set(row.map((c) => c.w)).size !== 1) return false
          if (new Set(row.map((c) => c.h)).size !== 1) return false
        }
        return true
      })(),
      cardBoxes: all.map((c) => c.w + 'x' + c.h + '@y' + c.y),
      /* ══ v1679 · THE ROWS INSIDE THE CARD, WHICH NOTHING HERE HAS EVER MEASURED ═══════════════
         Konyo: "tz tracker i want aligned the sections/acts within it they are like not syymetric".
         Every assertion above is about the CARD — its width, its height, its y. All of them were
         GREEN on the rotation he screenshotted, because the cards really were even; what was
         crooked was the type INSIDE them. The zone name wraps to two lines for "Worldstone Keep"
         and one for "Black Marsh", so ACT sat 28px lower in UP NEXT than in LIVE NOW, and the
         density line's optional `→ 96 terrorized` moved it another 14px between UP NEXT's own two
         rows. Measured before the v1679 fix at 1920px: three distinct offset sets — ACT at +40,
         +68 and +83 from the card top on five cards in one panel.
         So this measures each line's offset FROM ITS OWN CARD and demands one answer across every
         card in BOTH slots. Offsets are fractional (grid tracks land on half pixels), so the
         invariant is a 1px spread, not equality — rounding each side separately manufactured a
         1px "failure" on a panel that was in fact aligned to 0.01px. */
      rowSpread: (() => {
        const rows = ['.tzz-art', '.tzz-txt i', '.tzz-why', '.tzz-den'];
        const cards = [...document.querySelectorAll('#tz-body .tz-slot .tzz')];
        const out = {};
        for (const sel of rows) {
          const offs = cards.map((c) => {
            const e = c.querySelector(sel);
            return e ? e.getBoundingClientRect().y - c.getBoundingClientRect().y : null;
          }).filter((v) => v !== null);
          out[sel] = offs.length ? +(Math.max(...offs) - Math.min(...offs)).toFixed(2) : null;
        }
        return out;
      })(),
      clipped: [...document.querySelectorAll('#tz-body .tz-slot .tzz *')]
        .filter((n) => n.childElementCount === 0 && (n.textContent || '').trim())
        .filter((n) => n.scrollWidth > n.clientWidth + 1)
        .map((n) => ((n.textContent || '').trim().slice(0, 24) + ' @' + Math.round(n.getBoundingClientRect().width) + 'px')),
      // v1588 — the prose legend was REMOVED on purpose; the treatment carries the verdict now.
      // v1801 — and the LOCK was removed on purpose too. Dropping the meaningless level term from
      // both tzTiers takes thin from 15 zones to 40, so Konyo chose greyed-and-cancelled but still
      // clickable: a lock over most of the map punishes him for a ranking instead of reporting it.
      // What this now checks is the pair that can go wrong — the verdict must survive undimmed AND
      // the card must route. Checking only one half is how a card ends up bright and clickable, or
      // grey and dead.
      thinGrey: [...document.querySelectorAll('#tz-body .tzz-thin')]
        .every((c) => parseFloat(getComputedStyle(c).opacity) <= 0.35
                   && getComputedStyle(c).filter.includes('grayscale')),
      /* ⚠ v1930 — THIS ASSERTED A DECISION HE HAS SINCE REVERSED, FOR THE THIRD TIME.
         v1588 made a thin zone inert. v1801 undid it: dropping the meaningless level term took
         thin from 15 zones to 40, and "a lock over most of the map stops informing him of a
         ranking and starts overruling him with one". v1915 reversed it again, in his own words:
         "the mouse cursor for TZ ZONES that arent worth farming at all i want a CANCELLED sign on
         it so i know i cant click them. only the TZ ZONES worth farming should be clickable and
         routable."
         So a thin card must now be INERT and SAY SO: role=button for the screen reader, explicitly
         aria-disabled, no click handler, cursor:not-allowed. The old assertion is not a bug that
         appeared — it is a recorded expectation that his instruction superseded, and updating it is
         the honest move rather than reverting a feature he asked for twice.
         The pair that can still go wrong is unchanged in spirit: the verdict must survive undimmed
         AND the card must be honestly inert. Checking one half is how a card ends up bright and
         dead, or grey and secretly clickable. */
      thinRoutes: [...document.querySelectorAll('#tz-body .tzz-thin')]
        .every((c) => c.getAttribute('role') === 'button'
                   && c.getAttribute('aria-disabled') === 'true'
                   && !c.hasAttribute('onclick')
                   && getComputedStyle(c).cursor === 'not-allowed'),
      thinSeen: document.querySelectorAll('#tz-body .tzz-thin').length,
      routes: [...document.querySelectorAll('#tz-body .tzz-prime, #tz-body .tzz-good')]
        .every((c) => c.getAttribute('role') === 'button'),
    };
  });
  if (place.missing) fail.push('the TZ panel is gone from Sessions');
  else {
    if (place.numeral !== 'Ⅰ') fail.push(`the rotation is filed under ${place.numeral}, not Ⅰ THE HUNT`);
    if (!place.firstCard) fail.push('it is not the first card in its zone');
    if (!place.bannerAbove) fail.push('the card jumped above its own zone banner');
    if (!place.fullWidth) fail.push('it is not stretched left to right');
    /* v1640 — A GATE THAT SAYS "not evenly placed" AND NOTHING ELSE COSTS A DEBUG CYCLE EVERY
       TIME IT FIRES. Carry the geometry it just measured. */
    if (!place.equalW || !place.equalH || !place.rowsEven) {
      fail.push('the zone cards are not evenly placed (spread ' + place.slotSpread + 'px) — '
                + JSON.stringify(place.allBoxes || []));
    }
    /* v1641 — NON-VACUITY, ASSERTED. The height invariant above is only worth anything while the
       rotation actually contains a card with a `why` subtitle standing beside cards without one;
       with a uniform fixture it is true for free. So the fixture itself is now under test: LIVE
       NOW must render at least one .tzz-why and UP NEXT must render none. Making this gate green
       by deleting the why zone is the one cheat this assertion exists to refuse. */
    if (!place.whyNow) {
      fail.push('FIXTURE IS BLIND — no LIVE NOW card carries a `why` subtitle, so the equal-height '
                + 'assertion above cannot fail; restore a why-bearing zone to the stub rotation');
    }
    if (place.whyNext) {
      fail.push(`FIXTURE IS BLIND — ${place.whyNext} UP NEXT card(s) carry a \`why\` subtitle, so both `
                + 'slots grow by the same line and a cross-slot mismatch cannot show');
    }
    // v1639 — the assertion that would have caught the crammed row on day one, instead of two
    // versions later from a screenshot. A label the user cannot read is a broken card, whatever
    // its geometry says.
    if (place.clipped && place.clipped.length) {
      fail.push(`${place.clipped.length} clipped label(s) in the zone cards: ${place.clipped.slice(0, 4).join(' · ')}`);
    }
    // the stub rotation deliberately contains a thin zone, so seeing none means the tiering
    // stopped working rather than that this window happened to be all good
    if (!place.thinSeen) fail.push('no thin zone rendered — the tiering is not running');
    if (!place.thinGrey) fail.push('a thin zone is not greyed out — the verdict stopped being visible');
    if (!place.thinRoutes) fail.push('a thin zone is not honestly inert — it must be role=button, aria-disabled, no onclick, cursor:not-allowed (v1915, his words)');
    if (!place.routes) fail.push('a zone worth running does not route anywhere');
  }
  if (out.some((o) => /^and /i.test(o.n))) fail.push('a chip is labelled "and <Zone>" — the Oxford-comma split is back');
  // v3879 #108 - a face is the zone's game-extracted art OR its own monster sprite from TZ_MONSTER; anything else (an act
  // picture from the web, a guessed sprite, a sprite whose file is missing) is still a zone with no verified face.
  // The sourced picks live in tv/data/monster_art_arreat.json "zones" (TZ_MONSTER is built from it, and is private to the
  // painter), so a card's monster must be the one its own zone was given there - never just any sprite.
  let _tzPicks = {};
  try { _tzPicks = JSON.parse(fs.readFileSync(path.join(DEMO_DIR, 'data', 'monster_art_arreat.json'), 'utf8')).zones || {}; } catch (_e) { _tzPicks = {}; }
  const _pickOf = (n) => ((_tzPicks[n] || {}).file ? '/art/' + _tzPicks[n].file : null);
  const _faced = (o) => o.art.includes('/art/tz_') || (/^\/art\/d2(?:fam|mon)_[A-Za-z0-9_]+\.gif$/.test(o.mon) && o.mon === _pickOf(o.n));
  if (!Object.keys(_tzPicks).length) fail.push('the monster picks (tv/data/monster_art_arreat.json zones) could not be read - no face can be checked');
  if (!out.every(_faced)) fail.push('a zone has no verified face (neither its game zone art nor its own monster sprite): '
                                   + out.filter((o) => !_faced(o)).map((o) => o.n + ' [' + (o.mon || o.art || 'none') + ']').join(' · '));
  if ((by('Travincal') || {}).t !== 'tzz-prime') fail.push('Travincal (density 325, the Council) was not PRIME');
  if ((by('Blood Moor') || {}).t !== 'tzz-thin') fail.push('Blood Moor was not greyed');
  if (!((by('Blood Moor') || {}).grey || '').includes('grayscale')) fail.push('the THIN treatment is not visually distinct');
  /* v3889 (#133, REG-3495) - a zone is graded by the uniques he still needs when the board can be asked: Stony Tomb's tier is
     the board's own answer (its density, 2200, decides only when no board answers - the density grade, said in the hover) */
  const _stony = await page.evaluate(() => { try { const w = document.getElementById('tvd-eng').contentWindow;
    return (w && typeof w.tzZoneGrade === 'function') ? (w.tzZoneGrade('Stony Tomb', '') || {}).tier || null : null; } catch (e) { return null; } });
  const _stonyWant = _stony ? 'tzz-' + _stony : 'tzz-prime';
  if ((by('Stony Tomb') || {}).t !== _stonyWant) fail.push('Stony Tomb was ' + ((by('Stony Tomb') || {}).t || 'not drawn') + ', not '
                                                           + _stonyWant + (_stony ? ' (the board\u2019s grade by his items)' : ' (density 2200, no board)'));

  /* ══ v1679 · A SECOND ROTATION, BECAUSE THE ONE ABOVE CANNOT FAIL THIS ═══════════════════════
     Konyo: "tz tracker i want aligned the sections/acts within it they are like not syymetric" —
     the lines INSIDE the cards, not the cards. Every assertion above is about card geometry and
     all of them were green on the panel he photographed.

     I wrote the offset check against the fixture above first and it passed with the fix REMOVED —
     measured, not assumed: 484x139 cards, spread 0px, gate green, defect fully present on his
     screen. None of Stony Tomb / Travincal / Ancient's Way / Blood Moor / Cold Plains / Outer
     Cloister wraps its name at 484px and all six carry the same density shape, so the fixture is
     blind to this the same way the pre-v1641 one was blind to the `why` line. That is the exact
     failure mode the two FIXTURE IS BLIND guards above exist to name, so the answer is a fixture
     that CAN express it, not a softer assertion.

     HIS ROTATION, verbatim from the 01:34 screenshot. It carries both triggers at once:
       · "Worldstone Keep" wraps to two lines where "Black Marsh" does not — and the two slots are
         sibling grids, so `grid-auto-rows:1fr` cannot equalise across them (:2664).
       · "Worldstone Chamber" has density but no alvl, so it renders no `→ 96 terrorized` verdict
         row while its neighbours do.
     Before v1679 this produced ACT at +40 / +68 / +83 from the card top on five cards in one
     panel; after, one offset for every line on every card in both slots.
     Kept as a SEPARATE pass rather than by editing the rotation above, because that one is
     load-bearing for the tier, art, oxford-comma and why/no-why assertions. */
  await page.unroute('**/api/tz');
  await page.route('**/api/tz', (r) => r.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ current: 'Black Marsh and The Hole',
                           next: 'Worldstone Keep, Throne of Destruction, and Worldstone Chamber',
                           ts: Date.now() }) }));
  /* v1682 — WIDEN THE WINDOW, OR THE SQUEEZE CANNOT HAPPEN. The suite runs at 1470px, where the
     TZ slot fits ONE 484px column and every zone name has room to spare. The mid-word break needs
     the TWO-column layout: at 1920px the slot is 682px, `.tz-zones` auto-fit puts two ~325px cards
     side by side, and the name column drops to 134px against a 139px "Worldstone". I wrote this
     assertion at 1470 first and it passed with the fix REMOVED — measured, not assumed. A wider
     window is the fixture, exactly as the second rotation is. Restored below so nothing after this
     inherits it. */
  await page.setViewportSize({ width: 1920, height: 1200 });
  /* REG-1998 - THE WAIT FOR THE SECOND ROTATION WAS SWALLOWED. It ended `.catch(() => {})`, so a refresh that had not
     painted in 9 s left the FIRST rotation on screen and the checks below measured it - every one of those cards carries
     a verdict, and the v3603 push #9 was refused with "FIXTURE IS BLIND" for a fixture that was never shown. A re-run a
     minute later was 16/16. Now: up to 30 s, the refresh pressed again at 10 s, and a second rotation that never paints
     fails with THAT reason - never measured as if it had. */
  const _sawSecond = () => page.waitForFunction(() => [...document.querySelectorAll('#tz-body .tzz b')]
    .some((b) => /Worldstone/.test(b.textContent)), null, { timeout: 10000 }).then(() => true, () => false);
  let _second = false;
  for (let _try = 0; _try < 3 && !_second; _try++) {
    await page.evaluate(() => { const b = document.getElementById('tz-refresh'); if (b) b.click(); });
    _second = await _sawSecond();
  }
  if (!_second) throw new Error('the second rotation never painted in 30 s (3 refreshes) - its checks would have '
                                + 'measured the FIRST rotation, so nothing below is run');
  const rows = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('#tz-body .tz-slot .tzz')];
    /* offset FROM ITS OWN CARD, subtracted before rounding: grid tracks land on half pixels, and
       rounding each side separately manufactures a 1px "failure" on a panel aligned to 0.01px. */
    const spread = (sel) => {
      const offs = cards.map((c) => {
        const e = c.querySelector(sel);
        return e ? e.getBoundingClientRect().y - c.getBoundingClientRect().y : null;
      }).filter((v) => v !== null);
      return offs.length ? +(Math.max(...offs) - Math.min(...offs)).toFixed(2) : null;
    };
    /* v1682 — NO NAME MAY BE FORCED TO BREAK INSIDE A WORD. `.tzz-top` is a flex row shared with
       the PRIME/GOOD badge, and `.tzz-top b { min-width: 0 }` licensed the name to shrink below
       its own longest word — measured at 1920px, a 134px box against a 139px "Worldstone", which
       rendered "Worldston / e Keep" on three of five cards. Compared against the CANVAS-measured
       width of the longest word in the name's own computed font, so this asks whether a break is
       FORCED rather than trying to read the rendered line boxes. */
    const midWord = cards.map((c) => {
      const nm = c.querySelector('.tzz-top b');
      if (!nm) return null;
      const cs = getComputedStyle(nm);
      const ctx = document.createElement('canvas').getContext('2d');
      ctx.font = cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
      const words = (nm.textContent || '').trim().split(/\s+/);
      const need = Math.max(...words.map((w) => ctx.measureText(w).width));
      return nm.getBoundingClientRect().width + 1 < need
        ? (nm.textContent || '').trim() + ' (' + Math.round(nm.getBoundingClientRect().width)
          + 'px box vs ' + Math.ceil(need) + 'px word)' : null;
    }).filter(Boolean);
    return { n: cards.length, midWord,
             wrapped: cards.some((c) => { const b = c.querySelector('.tzz-top b');
               return b && b.getBoundingClientRect().height > parseFloat(getComputedStyle(b).lineHeight) * 1.5; }),
             noVerdict: cards.some((c) => !c.querySelector('.tzz-terr')),
             art: spread('.tzz-art'), act: spread('.tzz-txt i'),
             why: spread('.tzz-why'), den: spread('.tzz-den') };
  });
  if (rows.n < 5) fail.push(`the second rotation rendered ${rows.n} zone cards, expected 5`);
  if (rows.midWord && rows.midWord.length) {
    fail.push('a zone name is squeezed narrower than its own longest word, so it breaks mid-word — '
              + rows.midWord.join(' · '));
  }
  /* NON-VACUITY, same discipline as whyNow/whyNext: this fixture is only worth running while it
     still contains a wrapped name AND a card with no verdict row. Lose either and it goes blind. */
  if (!rows.wrapped) fail.push('FIXTURE IS BLIND — no zone name wraps to two lines, so a cross-slot '
                               + 'name-height mismatch cannot show; restore a long-named zone');
  if (!rows.noVerdict) fail.push('FIXTURE IS BLIND — every card carries a `→ 96 terrorized` verdict, '
                                 + 'so a missing-verdict height mismatch cannot show');
  {
    const crooked = ['art', 'act', 'why', 'den'].filter((k) => rows[k] !== null && rows[k] > 1);
    if (crooked.length) {
      fail.push('the lines inside the zone cards do not line up across the two slots — '
                + crooked.map((k) => k + ' varies by ' + rows[k] + 'px').join(', '));
    }
  }
  await page.unroute('**/api/tz');
  await page.setViewportSize({ width: 1470, height: 920 });   // v1682 — hand the suite back its window
  record(name, fail.length === 0,
         fail.length ? fail.join(' · ')
                     : `${out.length} zones · every face is its zone art or its own sourced monster · PRIME/THIN separated (Travincal kept by boss override)`
                       + ` · cards level across BOTH slots, spread ${place.slotSpread}px `
                       + `(${place.whyNow} why live / ${place.whyNext} up next): ${JSON.stringify(place.allBoxes)}`);
}

// ── private console ─────────────────────────────────────────────────────────────
// REG-2275. The path set matches test_button_matrix._boot_control. A private app must
// not write his hist, sessions, frames, or chronicle stores, and must not inherit his ports.
function freePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.once('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const addr = srv.address();
      const port = addr && addr.port;
      srv.close(() => resolve(port));
    });
  });
}

async function twoPrivatePorts() {
  let port = await freePort();
  let agent = await freePort();
  for (let i = 0; i < 50; i++) {
    if (port !== agent && !HIS_PORTS.has(port) && !HIS_PORTS.has(agent)) {
      return { port, agent };
    }
    port = await freePort();
    agent = await freePort();
  }
  throw new Error('no private console ports (refusing 17771 and 17772)');
}

function stopPrivate() {
  const child = _private;
  _private = null;
  if (child && child.pid) {
    try { process.kill(child.pid, 'SIGTERM'); } catch (e) { /* already gone */ }
    try { child.unref(); } catch (e) {}
  }
  const sand = _sand;
  _sand = null;
  const root = path.resolve(os.tmpdir()) + path.sep;
  if (sand && path.resolve(sand).startsWith(root)) {
    try { fs.rmSync(sand, { recursive: true, force: true }); } catch (e) {}
  }
}

process.on('exit', () => {
  if (_private && _private.pid) {
    try { process.kill(_private.pid, 'SIGTERM'); } catch (e) {}
  }
});

function seedShelf(sand, hist) {
  // v3092 drops a film-less run out of the shelf grid (ghosts default false). J7 waits for one
  // .sh-card. An empty sandbox paints the empty hero and that wait expires. One synthetic run,
  // three stills, written only under the sandbox. The id is not a reel_s_<epoch> fixture.
  const sid = 'demo_shelf';
  const reel = path.join(hist, 'reel_' + sid);
  fs.mkdirSync(reel, { recursive: true });
  const still = Buffer.from(SHELF_STILL_B64, 'base64');
  for (let k = 0; k < 3; k++) {
    fs.writeFileSync(path.join(reel, 'f_' + String(k).padStart(4, '0') + '.jpg'), still);
  }
  const t = 1700000000000;
  const rows = [
    { sessionId: sid, ts: t, lane: 'deep', scene: 'gameplay', area: 'Stony Tomb' },
    { sessionId: sid, ts: t + 1000, lane: 'kai', kai: { missedFrames: 0 } },
  ];
  fs.writeFileSync(path.join(sand, 'sessions.jsonl'), rows.map((r) => JSON.stringify(r)).join('\n') + '\n');
}

async function bootPrivate() {
  const { port, agent } = await twoPrivatePorts();
  _sand = fs.mkdtempSync(path.join(os.tmpdir(), 'demo-console-'));
  const hist = path.join(_sand, 'frames', 'hist');
  fs.mkdirSync(hist, { recursive: true });
  seedShelf(_sand, hist);
  const env = {
    ...process.env,
    TV_CONTROL_PORT: String(port),
    TV_PORT: String(agent),
    TV_ROBOT: '1',
    TV_FLEET_BEHIND_PIN: '0', // L1: the pushing branch's distance from origin/main is not a journey fact
    TV_HIST: hist,
    TV_FRAMES_DIR: path.join(_sand, 'frames'),
    TV_SESSIONS: path.join(_sand, 'sessions.jsonl'),
    TV_CHRON_EVIDENCE: path.join(_sand, 'chron_evidence.json'),
    TV_CHRON_RESULT: path.join(_sand, 'chron_last_result.json'),
    TV_CHRON_SWEPT: path.join(_sand, 'chronicle_swept.json'),
    TV_CHRON_READS: path.join(_sand, 'chron_reads.json'),
    TV_SWEEP_LOCK: path.join(_sand, '.sweep.lock'),
  };
  const py = process.env.PYTHON || 'python3';
  _private = spawn(py, [path.join(DEMO_DIR, 'control_app.py'), '--no-open'], {
    cwd: DEMO_DIR,
    env,
    detached: false,
    stdio: 'ignore',
  });
  _private.on('error', () => { /* the wait below throws if the child never answers */ });
  const base = `http://127.0.0.1:${port}/`;
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (_private.exitCode !== null) {
      throw new Error('private console exited before /api/status');
    }
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), 1500);
    try {
      const r = await fetch(base + 'api/status', { signal: ac.signal });
      if (r.ok) {
        await r.text();
        console.log(`private console ${base} (agent :${agent}) — :17772 and :17771 untouched`);
        return base;
      }
      await r.text();
    } catch (e) {
      // still booting
    } finally {
      clearTimeout(timer);
    }
    await new Promise((res) => setTimeout(res, 250));
  }
  throw new Error('private console did not answer /api/status');
}

async function demoTarget() {
  // REG-2278. TV_DEMO_OWNED means this process must spawn. An inherited port is a
  // listener it did not start. 17771 and 17772 stay refused on the hand-run path too.
  const ownedRoute = String(process.env.TV_DEMO_OWNED || '') === '1';
  const explicit = ownedRoute ? '' : String(process.env.TV_DEMO_PORT || '').trim();
  const n = Number(explicit);
  if (!ownedRoute && explicit && Number.isInteger(n) && !HIS_PORTS.has(n)) {
    return { base: `http://127.0.0.1:${explicit}/`, owned: false };
  }
  return { base: await bootPrivate(), owned: true };
}

// ── runner ──────────────────────────────────────────────────────────────────────
async function main() {
  const t0 = Date.now();
  let URL = '';
  try {
    const target = await demoTarget();
    URL = target.base;
  } catch (e) {
    console.log(`❌ BOOT — ${e.message}`);
    console.log('DEMOS: 0/0 ✅  (boot failed)');
    process.exitCode = 1;
    stopPrivate();
    return;
  }
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1470, height: 920 } });
  const page = await context.newPage();

  try {
    const resp = await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 20000 });
    if (!resp || !resp.ok()) throw new Error(`console did not load OK (status ${resp && resp.status()}) — is it running?`);
    await page.waitForSelector('#head-tabs .ht', { timeout: 15000 });
    await warmEngine(page);
  } catch (e) {
    console.log(`❌ BOOT — ${e.message}`);
    console.log('DEMOS: 0/0 ✅  (boot failed)');
    await browser.close();
    process.exitCode = 1;
    stopPrivate();
    return;
  }

// v2130 — J10: THE HEADER, AT THE WIDTHS THAT DECIDE IT. #85 — v2100 shipped one-row-at-his-width,
// the grid identity column and the 1100px icon yield with NO gate at all: `ls tests/ | grep v21..`
// was empty and `grep head-tabs tv/test_control.py` returned nothing, so every one of those was
// unpinned. The only harness touching the strip measured {top,left} and nothing else.
//
// It lives HERE and not in tests/ because the strip is control_ui.html — the console — and this is
// the gate that runs on every UI change.
//
// ⚠ THE ROW COUNT IS COMPARED AS HEIGHTS, NEVER AS Math.round(top). v2100's own comment records
// four failed "fixes" chasing a phantom second row that was really Tools/TV·D sitting 2px taller.
// ⚠ AND `overflow-x:auto` WITH `scrollbar-width:none` IS ITSELF THE DEFECT (#66): a tab that runs
// out of room does not shrink or hint, it is simply NOT THERE. That pair is asserted absent.
async function j10_headerGeometry(page) {
  const name = 'J10 HEADER GEOMETRY';
  const widths = [1920, 1650, 1440, 1280, 1200, 1120, 1000, 900];
  const bad = [];
  const seen = [];
  for (const w of widths) {
    await page.setViewportSize({ width: w, height: 660 });
    await page.waitForTimeout(220);
    const r = await page.evaluate(() => {
      const s = document.getElementById('head-tabs');
      if (!s) return { err: 'no #head-tabs' };
      const t0 = s.querySelector('.ht');
      if (!t0) return { err: 'no tabs' };
      const cs = getComputedStyle(s);
      const sr = s.getBoundingClientRect();
      const tabs = Array.from(s.querySelectorAll('.ht'));
      const offscreen = tabs.filter((b) => {
        const r = b.getBoundingClientRect();
        return r.width < 1 || r.right <= sr.left + 0.5 || r.left >= sr.right - 0.5;
      }).length;
      const icon = s.querySelector('.ht-i');
      return {
        rows: Math.max(1, Math.round(s.clientHeight / t0.offsetHeight)),
        clipped: s.scrollWidth > s.clientWidth + 1,
        silent: (cs.overflowX === 'auto' || cs.overflowX === 'scroll') && cs.scrollbarWidth === 'none',
        tabs: tabs.length,
        offscreen,
        icons: !!(icon && icon.getBoundingClientRect().width > 0),
      };
    });
    if (r.err) { record(name, false, `${w}px — ${r.err}`); return; }
    seen.push(`${w}:${r.rows}r${r.icons ? '+i' : ''}`);
    // REG-2187 — THE TENTH DOOR MOVES THE ONE-ROW LINE. v3694's D2JSP made TEN doors. Measured on
    // the isolated console: ten icon+word tabs need ~1606px and could not fit one row at 1120/1200,
    // and v1614 forbids the other way out ("the WORD is the tab ... No label is ever hidden at any
    // width"). So the ornament now yields at 1280 (ten WORD tabs are ~604px and hold ONE row from
    // 1000 up — the widths he opens the console at). Below 1000 ten words no longer fit ~546px and
    // the strip wraps to a SECOND row rather than hide a word — the v2093 safety net — so a second
    // row is allowed there, while clip / silent-scroll / offscreen stay forbidden at every width
    // (a door must never vanish). A THIRD row is still a defect.
    if (r.rows !== 1 && w >= 1000) bad.push(`${w}px wraps to ${r.rows} rows`);
    if (r.rows > 2) bad.push(`${w}px wraps to ${r.rows} rows (two is the floor the safety net allows)`);
    if (r.clipped) bad.push(`${w}px clips the strip`);
    if (r.silent) bad.push(`${w}px has overflow-x:${'auto'} with no scrollbar — a tab can vanish silently`);
    if (r.offscreen) bad.push(`${w}px pushes ${r.offscreen} tab(s) out of reach`);
    // 2026-09-27 — 8 -> 9: his ruling added the 👤 Characters door (v3518, "yea do it").
    // 2026-10-12 — 9 -> 10: D2JSP is a door on this strip, after the Vault. A NEW tab must move
    // this number on purpose; a tab that silently leaves the DOM still reads short here.
    if (r.tabs !== 10) bad.push(`${w}px shows ${r.tabs} tabs, not 10`);
    // the icon yield is a DESIGN line, not an accident: they hold to 1120; below 1100 the LABELLED tabs drop
    // their art, while an icon-only chip (Tools) keeps its picture, because its picture is the tab (v3519)
    if (w > 1280 && !r.icons) bad.push(`${w}px lost its tab art above the 1280px yield`);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  record(name, bad.length === 0, bad.length ? bad.join(' · ') : `one row at ${seen.join(' ')}`);
}

  const journeys = [j10_headerGeometry, j1_shellMatrix, j2_alignment, j3_tally, j4_escDiscipline, j5_threeEyes, j6_signalPanel, j7_shelfStory, j8_sessionsFlagship, j9_terrorZoneFlagship, j11_receiptVerbs, j12_heartNoEcho, j13_overflowSaysSo,
    j14_outputPanesStayBounded, j15_heartArithmeticIsTrue, j16_twoCountsMustNameTheirQuantity];
  for (const j of journeys) {
    try {
      await j(page);
    } catch (e) {
      // name is derivable from the first record miss; print explicit failure line
      record(j.name || 'journey', false, (e && e.message) ? e.message.split('\n')[0] : String(e));
    }
  }

  await browser.close();
  const pass = results.filter((r) => r.ok).length;
  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`DEMOS: ${pass}/${results.length} ✅  (${secs}s)`);
  /* v2112 — AND THE FAILURES AGAIN, AFTER THE SUMMARY. hooks/pre-push shows only the TAIL of
     this output, so a failure printed at the top — where it happens — is cut off, and the gate
     reports "DEMOS: 8/9" with no way to tell WHICH journey or why. I chased one of these three
     times reading a truncated log. The line costs nothing when everything passes. */
  const failed = results.filter((r) => !r.ok);
  if (failed.length) {
    console.log('── what failed (repeated here because the gate only shows the tail) ──');
    for (const r of failed) console.log(`   ❌ ${r.name} — ${r.detail || '(no detail)'}`);
  }
  // v2131 — DERIVED, NOT HARDCODED. This read `pass === 9`, so adding J10 made a 10/10 run exit 1
  // and the pre-push gate refused a push whose own summary said every journey passed. The count of
  // journeys is not the contract; "none of them failed" is.
  process.exitCode = (results.length && pass === results.length) ? 0 : 1;
  stopPrivate();
}

main().catch((e) => {
  console.log(`❌ FATAL — ${e && e.stack ? e.stack : e}`);
  stopPrivate();
  process.exitCode = 1;
});
