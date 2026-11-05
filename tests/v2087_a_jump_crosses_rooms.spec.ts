import { test, expect } from './_net_stub';
import * as path from 'path';
const URL = 'file://' + path.resolve(__dirname, '..', 'bible.html');

// v2087 — TWO SITES STILL NAMED THE ROOM THE VAULT CARD HAD LEFT.
//
// v2085 moved #mule-vault-card out of #tab-tools into its own #tab-vault. That ship swept the
// two obvious callers — vaultJump() and quickIntake's CARD_TAB — and MISSED two more. Neither
// threw, neither logged, and every source guard that asked "does the element exist" said yes,
// because getElementById still finds a node inside a display:none pane.
//
// MEASURED before the fix, standing on Tools and clicking "⚡ do now → 🏦 vault":
//     chip exists          true ("🏦 vault")
//     #tab-vault display   none
//     card rect            0x0        <- never laid out, so scrollIntoView is a silent no-op
//     active tab after     tools      <- unchanged
//     scrollY moved        false
//     card expanded        false
//   → the chip did nothing whatsoever.
//
// And the v735.1 courtesy that expands the card when the TV registers a pickup was gated on
// `curV === 'tools'`, which after v2085 is exactly inverted:
//     standing on vault → expanded false   <- while you are WATCHING the vault
//     standing on tools → expanded true    <- in a room the card is not in
//
// THE FIX IS THE GENERAL ONE: ask the element which pane it is in. 17 of the 18 _toolJump
// chips are already home, so it is inert for them, and no future card move can re-break it.
//
// ⚠ A SOURCE GUARD CANNOT PROVE THIS. The old code's text ("mule-vault-card", "switchTab",
// "scrollIntoView") is all still present in the broken version — the defect is which ROOM the
// string names, and a grep cannot see a room. Only a real click across a real pane can.
//
// VENUE: a browser spec. Runs on GitHub CI, never on his Mac. [[test-venue]]

async function world(page: any) {
  await page.goto(URL);
  await page.waitForTimeout(1500);
  // v2144 (#151) — SUPPRESS THE OWNER SEED, then reload so the suppression is in force at boot.
  // bible.html:3793 treats navigator.webdriver + file:// as an "automated" world and seeds it with
  // ALL 99 RUNEWORDS FORGED. Two of the three names this spec applies below — Monarch and Phase
  // Blade — are WHITE BASES, and in that world they are correctly __throwout, so vaultAutoAssign
  // files nothing and every door reports ".vm-cell visible 0". The doors were fine; the world was
  // wrong. Measured in exactly CI's world: rwMade 99 without the flag, 0 with it.
  // ⚠ CLEAR FIRST, THEN FLAG. The load above already ran as an "automated" world and PERSISTED
  // its seed; setting the flag afterwards only stops the world being seeded AGAIN — it does not
  // undo what localStorage already holds. Reproduced locally at 1440x1000 and at Playwright's
  // 1280x720 default and it came back clean both times, while CI stayed red on the same commit.
  // An ordering difference I cannot reproduce is not something to reason about when it can be
  // REMOVED: wipe every d2r_ key, set the flag, then reload into a world with one possible state.
  await page.evaluate(() => {
    const ks: string[] = [];
    for (let i = 0; i < localStorage.length; i++) ks.push(localStorage.key(i) as string);
    ks.forEach((k) => { if (/d2r_/.test(k)) localStorage.removeItem(k); });
    localStorage.setItem('d2r_rwProfile', 'fresh');
  });
  await page.goto(URL);
  await page.waitForTimeout(1500);
}

test('the do-now vault chip lands him in the room the card actually lives in', async ({ page }) => {
  await world(page);

  const r = await page.evaluate(() => {
    (document.querySelector('[data-tab=tools]') as HTMLElement).click();
    const chip = Array.from(document.querySelectorAll('#tools-index .ti-chip'))
      .find((b) => /mule-vault-card/.test(b.getAttribute('onclick') || '')) as HTMLElement;
    if (!chip) return { found: false } as any;
    chip.click();
    const card = document.getElementById('mule-vault-card')!;
    const pane = card.closest('.tab-content') as HTMLElement;
    return {
      found: true,
      // the chip must take him to whichever room the card is in — named by the CARD, not by us,
      // so this stays true if it ever moves again
      room: pane ? pane.id.replace(/^tab-/, '') : '',
      active: (document.querySelector('.tab.active') as HTMLElement).getAttribute('data-tab'),
      laidOut: card.getBoundingClientRect().height > 0,
      paneShown: getComputedStyle(pane).display !== 'none',
    };
  });

  expect(r.found, 'the ⚡ do now → 🏦 vault chip must exist in the Tools index').toBe(true);
  expect(r.active, 'the chip must switch to the card’s own room').toBe(r.room);
  expect(r.paneShown, 'and that pane must actually be displayed').toBe(true);
  expect(r.laidOut, 'a card in a hidden pane measures 0x0 — scrollIntoView on it is a no-op').toBe(true);
});

test('a TV pickup expands the vault card in the room he is watching, and not elsewhere', async ({ page }) => {
  await world(page);

  const r = await page.evaluate(() => {
    const card = () => document.getElementById('mule-vault-card')!;
    const room = (card().closest('.tab-content') as HTMLElement).id.replace(/^tab-/, '');
    const other = room === 'tools' ? 'vault' : 'tools';
    const run = (where: string) => {
      (document.querySelector('[data-tab=' + where + ']') as HTMLElement).click();
      const c = card();
      if (!c.classList.contains('collapsed')) (window as any).toggleCardCollapse('mule-vault-card');
      if ((window as any).LSR) (window as any).LSR.setItem('d2r_vaultAutoIntake', 'on'); /* Elad 2026-10-18: a TV pickup registers only while AUTO INTAKE is on */
      (window as any).tvVaultRegister && (window as any).tvVaultRegister('Harlequin Crest');
      return !c.classList.contains('collapsed');
    };
    return { room, inRoom: run(room), inOther: run(other) };
  });

  expect(r.inRoom, `standing in #tab-${r.room} — where the card lives — a pickup must open it`).toBe(true);
  expect(r.inOther, 'but it must not expand a card in a room he is not standing in').toBe(false);
});

test('every quick-jump chip points at a target it can actually reach', async ({ page }) => {
  await world(page);

  const strays = await page.evaluate(() => {
    const out: any[] = [];
    Array.from(document.querySelectorAll('.ti-chip')).forEach((b) => {
      const m = /_toolJump\('([a-z0-9-]+)'\)/.exec(b.getAttribute('onclick') || '');
      if (!m) return;
      const el = document.getElementById(m[1]);
      // a chip aimed at an id that is not on the page can never do anything
      if (!el) { out.push({ id: m[1], why: 'no such element' }); return; }
      if (!el.closest('.tab-content')) out.push({ id: m[1], why: 'not inside any tab pane' });
    });
    return out;
  });

  expect(strays, 'a jump chip whose target does not exist is dead on click: ' + JSON.stringify(strays)).toEqual([]);
});

// ── and the room itself must not open as a closed drawer ──────────────────────────────────
//
// v2085 gave the vault a room where its card is the ONLY occupant. A collapsed card in Tools sat
// among a dozen others and read as "click to open"; alone in its own room it reads as an EMPTY
// PAGE. MEASURED on entry, three doors in:
//     clicking the VAULT tab   collapsed=YES  body 0px     .vm-cell visible 0
//     via the do-now chip      collapsed=YES  body 0px     .vm-cell visible 0
//     via vaultJump()          collapsed=no   body 1027px  .vm-cell visible 3
// Only the purpose-built path worked. Shown the region cold with no hint of what it should be, a
// different model family reported: "no item grids, thumbnails, or stored-item content is visible
// ... heading with nothing beneath it, and dead space filling most of the frame."
//
// ⚠ A COUNTER CANNOT CATCH THIS. querySelectorAll('.vm-cell').length returns the same number
// whether the card is open or closed — the cells exist in the DOM either way. That count passed
// while the page showed nothing. Assert on VISIBLE height, which is the thing he actually gets.

test('every door into the vault opens it, not just the purpose-built one', async ({ page }) => {
  await world(page);

  const r = await page.evaluate(() => {
    /* #246 — the vault files only on a witness now, so the three are registered WITH one (two independent
       stash looks, each with its own frame and conf); the doors under test need filed cells to show. */
    const LOOKS = [{ session: 's_a', frame: 'f_a.jpg', conf: 0.9 }, { session: 's_b', frame: 'f_b.jpg', conf: 0.85 }];
    /* REG-3086 (db037ec1f) — a read's row now ticks the grail only (toggleOwned grailOnly); possession is
       tvVaultRegister's alone, and it refuses a frame while AUTO INTAKE is off. world() wiped every d2r_ key,
       so AUTO INTAKE is absent = off and the three were never owned: 0 cells at every door. Turned on exactly
       as the TV-pickup test above does. */
    if ((window as any).LSR) (window as any).LSR.setItem('d2r_vaultAutoIntake', 'on');
    (window as any).chronicleApply({ wouldAdd: { uniques: ['Shako', 'Monarch', 'Phase Blade']
      .map((n) => ({ name: n, loc: 'stash', witnesses: LOOKS })), sets: [] } });
    try { (window as any).vaultAutoAssign && (window as any).vaultAutoAssign(); } catch (e) {}

    const enter = (how: string) => {
      (document.querySelector('[data-tab=main]') as HTMLElement).click();
      /* v2120 (#58) — AND PUT THE CARD BACK. Leaving the vault is not the same as closing it:
         nothing re-collapses #mule-vault-card, so after the FIRST door the next two measured a
         card door one had already opened — `collapsed:false` was inherited, not earned.
         (The sibling visible-cell assertion is NOT vacuous: cell height is 0 while #tab-vault is
         display:none, so a chip that fails to switch rooms does go red.)
         [[feedback-blind-fixture-green-gate]] */
      const _vc = document.getElementById('mule-vault-card');
      if (_vc && !_vc.classList.contains('collapsed')) _vc.classList.add('collapsed');
      if (how === 'tab') {
        (document.querySelector('[data-tab=vault]') as HTMLElement).click();
      } else if (how === 'chip') {
        (document.querySelector('[data-tab=tools]') as HTMLElement).click();
        const chip = Array.from(document.querySelectorAll('#tools-index .ti-chip'))
          .find((b) => /mule-vault-card/.test(b.getAttribute('onclick') || '')) as HTMLElement;
        chip && chip.click();
      } else {
        (window as any).vaultJump();
      }
      const card = document.getElementById('mule-vault-card')!;
      return {
        collapsed: card.classList.contains('collapsed'),
        // VISIBLE cells — a closed card still holds them all in the DOM
        cells: Array.from(document.querySelectorAll('.vm-cell'))
          .filter((e) => e.getBoundingClientRect().height > 0).length,
      };
    };
    return { tab: enter('tab'), chip: enter('chip'), jump: enter('jump') };
  });

  for (const door of ['tab', 'chip', 'jump'] as const) {
    expect(r[door].collapsed, `entering the vault via ${door} left the card collapsed — an empty room`).toBe(false);
    expect(r[door].cells, `entering the vault via ${door} showed no visible cells`).toBeGreaterThan(0);
  }
});
